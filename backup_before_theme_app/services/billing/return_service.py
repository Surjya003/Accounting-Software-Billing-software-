"""
Returns Service — Sales Returns & Purchase Returns
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import (
    SalesReturn, SalesReturnItem, PurchaseReturn, PurchaseReturnItem,
    Product, Party
)
from app.config import get_financial_year


def _gen_number(session, model, prefix, date_field, ret_date):
    fy = get_financial_year(ret_date)
    pattern = f"{prefix}/{fy}/%"
    num_col = getattr(model, 'return_number')
    last = session.query(model).filter(num_col.like(pattern)).order_by(desc(model.id)).first()
    seq = 1
    if last and last.return_number:
        try: seq = int(last.return_number.split("/")[-1]) + 1
        except ValueError: pass
    return f"{prefix}/{fy}/{seq:04d}"


# --- Sales Returns ---

def create_sales_return(data: Dict, items_data: List[Dict]) -> SalesReturn:
    if not items_data:
        raise ValueError("Return must have at least one item.")
    with get_session() as session:
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party:
            raise ValueError("Party not found.")
        ret_date = data.get("return_date", date.today())
        ret_num = data.get("return_number") or _gen_number(session, SalesReturn, "SR", "return_date", ret_date)
        
        # Validation: check return quantity against original invoice
        if data.get("invoice_id"):
            from app.database.models import Invoice
            inv = session.query(Invoice).filter(Invoice.id == data["invoice_id"]).first()
            if inv:
                inv_items = {it.product_id: it.quantity for it in inv.items if it.product_id}
                for it in items_data:
                    pid = it.get("product_id")
                    ret_qty = Decimal(str(it.get("quantity", "1")))
                    if pid and pid in inv_items and ret_qty > inv_items[pid]:
                        raise ValueError(f"Return quantity ({ret_qty}) exceeds quantity sold ({inv_items[pid]}) on invoice #{inv.invoice_number}.")

        subtotal = tax = Decimal("0.00")
        for it in items_data:
            qty = Decimal(str(it.get("quantity", "1")))
            rate = Decimal(str(it.get("unit_price", "0")))
            tr = Decimal(str(it.get("tax_rate", "0")))
            taxable = (qty * rate).quantize(Decimal("0.01"))
            ta = (taxable * tr / Decimal("100")).quantize(Decimal("0.01"))
            it["tax_amount"] = ta; it["total_amount"] = taxable + ta
            subtotal += taxable; tax += ta
        
        sr = SalesReturn(
            return_number=ret_num, return_date=ret_date, party_id=party.id,
            invoice_id=data.get("invoice_id"), subtotal=subtotal, tax_amount=tax,
            total_amount=subtotal + tax, reason=data.get("reason", ""),
            status=data.get("status", "pending"),
        )
        session.add(sr); session.flush()
        for it in items_data:
            session.add(SalesReturnItem(
                return_id=sr.id, product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                tax_amount=it["tax_amount"], total_amount=it["total_amount"],
            ))
            # Restore stock on approval
            if sr.status == "approved" and it.get("product_id"):
                prod = session.query(Product).filter(Product.id == it["product_id"]).first()
                if prod:
                    prod.stock_quantity += Decimal(str(it.get("quantity", "0")))

        # Post Credit Note Voucher to Party Ledger on approval
        if sr.status == "approved":
            from app.database.models import Voucher
            cn_num = f"CN/{sr.return_number.split('/', 1)[-1]}" if "/" in sr.return_number else f"CN-{sr.return_number}"
            existing = session.query(Voucher).filter(Voucher.voucher_number == cn_num).first()
            if existing:
                cn_num = f"{cn_num}-{int(ret_date.strftime('%Y%m%d'))}"
            v = Voucher(
                voucher_number=cn_num,
                voucher_type="Credit",
                voucher_date=sr.return_date,
                party_id=sr.party_id,
                reference_no=sr.return_number,
                reference_date=sr.return_date,
                amount_untaxed=sr.subtotal,
                total_tax=sr.tax_amount,
                total_amount=sr.total_amount,
                debit_amount=Decimal("0.00"),
                credit_amount=sr.total_amount,
                narration=f"Credit Note for Sales Return #{sr.return_number} (Ref: {sr.reason or 'Goods Returned'})",
            )
            session.add(v)

        session.flush(); session.refresh(sr)
        return sr


def get_all_sales_returns(from_date=None, to_date=None, status=None, search=None, limit=200):
    with get_session() as session:
        q = session.query(SalesReturn).join(Party, SalesReturn.party_id == Party.id)
        if from_date: q = q.filter(SalesReturn.return_date >= from_date)
        if to_date: q = q.filter(SalesReturn.return_date <= to_date)
        if status and status != "All": q = q.filter(SalesReturn.status == status)
        if search:
            p = f"%{search.strip()}%"
            q = q.filter(or_(SalesReturn.return_number.ilike(p), Party.name.ilike(p)))
        return [r.to_dict() for r in q.order_by(desc(SalesReturn.return_date), desc(SalesReturn.id)).limit(limit).all()]


def get_sales_return_by_id(sr_id: int):
    with get_session() as session:
        sr = session.query(SalesReturn).filter(SalesReturn.id == sr_id).first()
        if not sr: return None
        d = sr.to_dict(); d["items"] = [it.to_dict() for it in sr.items]; return d


# --- Purchase Returns ---

def create_purchase_return(data: Dict, items_data: List[Dict]) -> PurchaseReturn:
    if not items_data:
        raise ValueError("Return must have at least one item.")
    with get_session() as session:
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party: raise ValueError("Party not found.")
        ret_date = data.get("return_date", date.today())
        ret_num = data.get("return_number") or _gen_number(session, PurchaseReturn, "PR", "return_date", ret_date)

        # Validation: check return quantity against original PO
        if data.get("po_id"):
            from app.database.models import PurchaseOrder
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == data["po_id"]).first()
            if po:
                po_items = {it.product_id: it.quantity for it in po.items if it.product_id}
                for it in items_data:
                    pid = it.get("product_id")
                    ret_qty = Decimal(str(it.get("quantity", "1")))
                    if pid and pid in po_items and ret_qty > po_items[pid]:
                        raise ValueError(f"Return quantity ({ret_qty}) exceeds purchased quantity ({po_items[pid]}) on PO #{po.po_number}.")

        subtotal = tax = Decimal("0.00")
        for it in items_data:
            qty = Decimal(str(it.get("quantity", "1")))
            rate = Decimal(str(it.get("unit_price", "0")))
            tr = Decimal(str(it.get("tax_rate", "0")))
            taxable = (qty * rate).quantize(Decimal("0.01"))
            ta = (taxable * tr / Decimal("100")).quantize(Decimal("0.01"))
            it["tax_amount"] = ta; it["total_amount"] = taxable + ta
            subtotal += taxable; tax += ta
        
        pr = PurchaseReturn(
            return_number=ret_num, return_date=ret_date, party_id=party.id,
            po_id=data.get("po_id"), subtotal=subtotal, tax_amount=tax,
            total_amount=subtotal + tax, reason=data.get("reason", ""),
            status=data.get("status", "pending"),
        )
        session.add(pr); session.flush()
        for it in items_data:
            session.add(PurchaseReturnItem(
                return_id=pr.id, product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                tax_amount=it["tax_amount"], total_amount=it["total_amount"],
            ))
            # Deduct stock on approved purchase return
            if pr.status == "approved" and it.get("product_id"):
                prod = session.query(Product).filter(Product.id == it["product_id"]).first()
                if prod:
                    prod.stock_quantity = max(Decimal("0.00"), prod.stock_quantity - Decimal(str(it.get("quantity", "0"))))

        # Post Debit Note Voucher to Party Ledger on approval
        if pr.status == "approved":
            from app.database.models import Voucher
            dn_num = f"DN/{pr.return_number.split('/', 1)[-1]}" if "/" in pr.return_number else f"DN-{pr.return_number}"
            existing = session.query(Voucher).filter(Voucher.voucher_number == dn_num).first()
            if existing:
                dn_num = f"{dn_num}-{int(ret_date.strftime('%Y%m%d'))}"
            v = Voucher(
                voucher_number=dn_num,
                voucher_type="Debit",
                voucher_date=pr.return_date,
                party_id=pr.party_id,
                reference_no=pr.return_number,
                reference_date=pr.return_date,
                amount_untaxed=pr.subtotal,
                total_tax=pr.tax_amount,
                total_amount=pr.total_amount,
                debit_amount=pr.total_amount,
                credit_amount=Decimal("0.00"),
                narration=f"Debit Note for Purchase Return #{pr.return_number} (Ref: {pr.reason or 'Goods Returned to Vendor'})",
            )
            session.add(v)

        session.flush(); session.refresh(pr)
        return pr


def get_all_purchase_returns(from_date=None, to_date=None, status=None, search=None, limit=200):
    with get_session() as session:
        q = session.query(PurchaseReturn).join(Party, PurchaseReturn.party_id == Party.id)
        if from_date: q = q.filter(PurchaseReturn.return_date >= from_date)
        if to_date: q = q.filter(PurchaseReturn.return_date <= to_date)
        if status and status != "All": q = q.filter(PurchaseReturn.status == status)
        if search:
            p = f"%{search.strip()}%"
            q = q.filter(or_(PurchaseReturn.return_number.ilike(p), Party.name.ilike(p)))
        return [r.to_dict() for r in q.order_by(desc(PurchaseReturn.return_date), desc(PurchaseReturn.id)).limit(limit).all()]


def get_pending_returns_count() -> int:
    with get_session() as session:
        sr = session.query(SalesReturn).filter(SalesReturn.status == "pending").count()
        pr = session.query(PurchaseReturn).filter(PurchaseReturn.status == "pending").count()
        return sr + pr
