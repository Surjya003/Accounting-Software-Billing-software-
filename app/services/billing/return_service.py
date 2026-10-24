"""
Returns Service — Sales Returns & Purchase Returns
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import (
    SalesReturn, SalesReturnItem, PurchaseReturn, PurchaseReturnItem,
    Product, Party, CompanyProfile, Invoice, PurchaseOrder, Voucher
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


def get_section_34_deadline(supply_date: date) -> date:
    """
    Returns 30th November following the end of the financial year in which the supply was made.
    Per CGST Act Section 34(2): Credit note for tax adjustment must be declared by 30th November
    following the financial year end of the original invoice.
    """
    fy_end_year = supply_date.year if supply_date.month <= 3 else supply_date.year + 1
    return date(fy_end_year, 11, 30)


# --- Sales Returns ---

def create_sales_return(data: Dict, items_data: Optional[List[Dict]] = None) -> SalesReturn:
    if items_data is None:
        items_data = data.get("items", [])
    if not items_data:
        raise ValueError("Return must have at least one item.")
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party:
            raise ValueError("Party not found.")
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party and party.state_code else c_sc

        ret_date = data.get("return_date", date.today())
        ret_num = data.get("return_number") or _gen_number(session, SalesReturn, "SR", "return_date", ret_date)
        
        # Validation: check return quantity against original invoice
        inv = None
        if data.get("invoice_id"):
            inv = session.query(Invoice).filter(Invoice.id == data["invoice_id"]).first()
            if not inv:
                raise ValueError("Invoice not found.")
            if inv.status in ("cancelled", "draft"):
                raise ValueError(f"Cannot create sales return against {inv.status} invoice #{inv.invoice_number}.")

            # Statutory Section 34(2) Deadline Enforcement
            deadline = get_section_34_deadline(inv.invoice_date)
            if ret_date > deadline and not data.get("allow_post_deadline_override", False):
                raise ValueError(
                    f"Statutory Deadline Exceeded (CGST Act Section 34(2)): Credit note date ({ret_date}) "
                    f"is after 30 November ({deadline}) following the financial year of invoice #{inv.invoice_number} ({inv.invoice_date}). "
                    f"GST adjustment is time-barred without explicit administrative permission (pass allow_post_deadline_override=True)."
                )

            inv_items = defaultdict(Decimal)
            for it in inv.items:
                if it.product_id:
                    inv_items[it.product_id] += Decimal(str(it.quantity))

            # BUG-01 Fix: Sum return quantities per product across all input rows
            ret_items_by_prod = defaultdict(Decimal)
            for it in items_data:
                pid = it.get("product_id")
                if pid:
                    ret_items_by_prod[pid] += Decimal(str(it.get("quantity", "1")))

            for pid, ret_qty in ret_items_by_prod.items():
                if pid not in inv_items:
                    raise ValueError(f"Product #{pid} is not present in invoice #{inv.invoice_number}.")
                # Check cumulative returns
                prior_returned = (
                    session.query(func.coalesce(func.sum(SalesReturnItem.quantity), Decimal("0")))
                    .join(SalesReturn, SalesReturnItem.return_id == SalesReturn.id)
                    .filter(
                        SalesReturn.invoice_id == inv.id,
                        SalesReturn.status.in_(["approved", "pending"]),
                        SalesReturnItem.product_id == pid
                    ).scalar() or Decimal("0")
                )
                allowed = inv_items[pid] - Decimal(str(prior_returned))
                if ret_qty > allowed:
                    raise ValueError(
                        f"Return quantity ({ret_qty}) exceeds allowed return quantity ({allowed}) on invoice #{inv.invoice_number}."
                    )

        subtotal = tax = Decimal("0.00")
        for it in items_data:
            qty = Decimal(str(it.get("quantity", "1")))
            rate = Decimal(str(it.get("unit_price", "0")))
            from app.services.validation_helpers import normalize_tax_rate
            tr = normalize_tax_rate(it)
            taxable = (qty * rate).quantize(Decimal("0.01"))
            ta = (taxable * tr / Decimal("100")).quantize(Decimal("0.01"))
            it["tax_amount"] = ta; it["total_amount"] = taxable + ta
            subtotal += taxable
            tax += ta
        orig_inv_no = data.get("original_invoice_no") or (inv.invoice_number if inv else None)
        orig_inv_dt = data.get("original_invoice_date") or (inv.invoice_date if inv else None)
        
        sr = SalesReturn(
            return_number=ret_num, return_date=ret_date, party_id=party.id,
            invoice_id=data.get("invoice_id"), subtotal=subtotal, tax_amount=tax,
            total_amount=subtotal + tax, reason=data.get("reason", ""),
            status=data.get("status", "pending"),
            reason_category=data.get("reason_category", "Sales Return"),
            original_invoice_no=orig_inv_no,
            original_invoice_date=orig_inv_dt,
            adjustment_mode=data.get("adjustment_mode", "Credit Note"),
            adjustment_ref=data.get("adjustment_ref"),
            returned_via=data.get("returned_via"),
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
            cn_num = f"CN/{sr.return_number.split('/', 1)[-1]}" if "/" in sr.return_number else f"CN-{sr.return_number}"
            existing = session.query(Voucher).filter(Voucher.voucher_number == cn_num).first()
            if existing:
                cn_num = f"{cn_num}-{int(ret_date.strftime('%Y%m%d'))}"

            # Calculate GST breakdown
            is_inter = (p_sc != c_sc)
            cgst_amt = Decimal("0.00")
            sgst_amt = Decimal("0.00")
            igst_amt = Decimal("0.00")
            if is_inter:
                igst_amt = sr.tax_amount
            else:
                half = (sr.tax_amount / Decimal("2")).quantize(Decimal("0.01"))
                cgst_amt = half
                sgst_amt = sr.tax_amount - half

            v = Voucher(
                voucher_number=cn_num,
                voucher_type="Credit",
                voucher_date=sr.return_date,
                party_id=sr.party_id,
                reference_no=sr.return_number,
                reference_date=sr.return_date,
                amount_untaxed=sr.subtotal,
                cgst_amount=cgst_amt,
                sgst_amount=sgst_amt,
                igst_amount=igst_amt,
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


def get_purchase_return_by_id(pr_id: int):
    with get_session() as session:
        pr = session.query(PurchaseReturn).filter(PurchaseReturn.id == pr_id).first()
        if not pr: return None
        d = pr.to_dict(); d["items"] = [it.to_dict() for it in pr.items]; return d



# --- Purchase Returns ---

def create_purchase_return(data: Dict, items_data: Optional[List[Dict]] = None) -> PurchaseReturn:
    if items_data is None:
        items_data = data.get("items", [])
    if not items_data:
        raise ValueError("Return must have at least one item.")
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party: raise ValueError("Party not found.")
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party and party.state_code else c_sc
        allow_neg = getattr(company, "allow_negative_stock", False) if company else False

        ret_date = data.get("return_date", date.today())
        ret_num = data.get("return_number") or _gen_number(session, PurchaseReturn, "PR", "return_date", ret_date)

        # Validation: check return quantity against original PO
        if data.get("po_id"):
            po = session.query(PurchaseOrder).filter(PurchaseOrder.id == data["po_id"]).first()
            if not po:
                raise ValueError("Purchase Order not found.")
            if po.status in ("cancelled", "draft"):
                raise ValueError(f"Cannot create purchase return against {po.status} purchase order #{po.po_number}.")

            po_received = defaultdict(Decimal)
            for it in po.items:
                if it.product_id:
                    rcv = getattr(it, 'received_quantity', None)
                    rcv = Decimal(str(rcv)) if rcv is not None else Decimal(str(it.quantity))
                    po_received[it.product_id] += rcv

            # BUG-01 Fix: Sum purchase return quantities per product across all input rows
            pr_items_by_prod = defaultdict(Decimal)
            for it in items_data:
                pid = it.get("product_id")
                if pid:
                    pr_items_by_prod[pid] += Decimal(str(it.get("quantity", "1")))

            for pid, ret_qty in pr_items_by_prod.items():
                if pid not in po_received:
                    raise ValueError(f"Product #{pid} is not present in PO #{po.po_number}.")
                # Check cumulative purchase returns
                prior_returned = (
                    session.query(func.coalesce(func.sum(PurchaseReturnItem.quantity), Decimal("0")))
                    .join(PurchaseReturn, PurchaseReturnItem.return_id == PurchaseReturn.id)
                    .filter(
                        PurchaseReturn.po_id == po.id,
                        PurchaseReturn.status.in_(["approved", "pending"]),
                        PurchaseReturnItem.product_id == pid
                    ).scalar() or Decimal("0")
                )
                allowed = po_received[pid] - Decimal(str(prior_returned))
                if ret_qty > allowed:
                    raise ValueError(
                        f"Return quantity ({ret_qty}) exceeds allowed return quantity ({allowed}) on PO #{po.po_number} (Received: {po_received[pid]}, Already returned: {prior_returned})."
                    )

        subtotal = tax = Decimal("0.00")
        for it in items_data:
            qty = Decimal(str(it.get("quantity", "1")))
            rate = Decimal(str(it.get("unit_price", "0")))
            from app.services.validation_helpers import normalize_tax_rate
            tr = normalize_tax_rate(it)
            taxable = (qty * rate).quantize(Decimal("0.01"))
            ta = (taxable * tr / Decimal("100")).quantize(Decimal("0.01"))
            it["tax_amount"] = ta; it["total_amount"] = taxable + ta
            subtotal += taxable
            tax += ta
        orig_po_no = data.get("original_invoice_no") or (po.po_number if (data.get("po_id") and 'po' in locals() and po) else None)
        orig_po_dt = data.get("original_invoice_date") or (po.po_date if (data.get("po_id") and 'po' in locals() and po) else None)

        pr = PurchaseReturn(
            return_number=ret_num, return_date=ret_date, party_id=party.id,
            po_id=data.get("po_id"), subtotal=subtotal, tax_amount=tax,
            total_amount=subtotal + tax, reason=data.get("reason", ""),
            status=data.get("status", "pending"),
            reason_category=data.get("reason_category", "Purchase Return"),
            original_invoice_no=orig_po_no,
            original_invoice_date=orig_po_dt,
            adjustment_mode=data.get("adjustment_mode", "Debit Note"),
            adjustment_ref=data.get("adjustment_ref"),
            returned_via=data.get("returned_via"),
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
                    ret_q = Decimal(str(it.get("quantity", "0")))
                    if not allow_neg and ret_q > prod.stock_quantity:
                        raise ValueError(
                            f"Insufficient stock for product '{prod.name}' to return. Available: {prod.stock_quantity}, Requested: {ret_q}."
                        )
                    prod.stock_quantity -= ret_q

        # Post Debit Note Voucher to Party Ledger on approval
        if pr.status == "approved":
            dn_num = f"DN/{pr.return_number.split('/', 1)[-1]}" if "/" in pr.return_number else f"DN-{pr.return_number}"
            existing = session.query(Voucher).filter(Voucher.voucher_number == dn_num).first()
            if existing:
                dn_num = f"{dn_num}-{int(ret_date.strftime('%Y%m%d'))}"

            # Calculate GST breakdown
            is_inter = (p_sc != c_sc)
            cgst_amt = Decimal("0.00")
            sgst_amt = Decimal("0.00")
            igst_amt = Decimal("0.00")
            if is_inter:
                igst_amt = pr.tax_amount
            else:
                half = (pr.tax_amount / Decimal("2")).quantize(Decimal("0.01"))
                cgst_amt = half
                sgst_amt = pr.tax_amount - half

            v = Voucher(
                voucher_number=dn_num,
                voucher_type="Debit",
                voucher_date=pr.return_date,
                party_id=pr.party_id,
                reference_no=pr.return_number,
                reference_date=pr.return_date,
                amount_untaxed=pr.subtotal,
                cgst_amount=cgst_amt,
                sgst_amount=sgst_amt,
                igst_amount=igst_amt,
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
