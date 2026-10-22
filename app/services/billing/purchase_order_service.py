"""
Purchase Order Service
CRUD operations for Purchase Orders with stock receipt tracking.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import PurchaseOrder, PurchaseOrderItem, Product, Party, CompanyProfile
from app.config import get_financial_year


def generate_po_number(session, po_date: date) -> str:
    """Generate next PO number: PO/24-25/0001"""
    fy = get_financial_year(po_date)
    pattern = f"PO/{fy}/%"
    last = session.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(pattern)
    ).order_by(desc(PurchaseOrder.id)).first()
    if last and last.po_number:
        try:
            seq = int(last.po_number.split("/")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"PO/{fy}/{seq:04d}"


def create_purchase_order(po_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> PurchaseOrder:
    """Create a new purchase order with items."""
    if not items_data:
        raise ValueError("Purchase order must have at least one item.")
    
    with get_session() as session:
        party = session.query(Party).filter(Party.id == po_data.get("party_id")).first()
        if not party:
            raise ValueError("Selected supplier/party does not exist.")
        
        po_date = po_data.get("po_date", date.today())
        po_number = po_data.get("po_number") or generate_po_number(session, po_date)
        
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        
        for item in items_data:
            qty = Decimal(str(item.get("quantity", "1")))
            rate = Decimal(str(item.get("unit_price", "0")))
            tax_rate = Decimal(str(item.get("tax_rate", "0")))
            taxable = (qty * rate).quantize(Decimal("0.01"))
            tax_amt = (taxable * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            item["taxable_value"] = taxable
            item["tax_amount"] = tax_amt
            item["total_amount"] = taxable + tax_amt
            subtotal += taxable
            tax_total += tax_amt
        
        po = PurchaseOrder(
            po_number=po_number,
            po_date=po_date,
            party_id=party.id,
            subtotal=subtotal,
            tax_amount=tax_total,
            total_amount=subtotal + tax_total,
            status=po_data.get("status", "draft"),
            notes=po_data.get("notes", ""),
        )
        session.add(po)
        session.flush()
        
        for it in items_data:
            item = PurchaseOrderItem(
                po_id=po.id,
                product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                tax_amount=it.get("tax_amount", Decimal("0")),
                total_amount=it.get("total_amount", Decimal("0")),
            )
            session.add(item)
        
        session.flush()
        session.refresh(po)
        return po


def receive_goods(po_id: int, received_quantities: Optional[Dict[int, float]] = None) -> Dict[str, Any]:
    """
    Receives goods against a Purchase Order, supporting partial receipt.
    Updates product stock and posts purchase voucher to supplier ledger.
    """
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise ValueError("Purchase Order not found.")
        if po.status == "received":
            raise ValueError("PO is already marked as received.")

        received_total = Decimal("0.00")
        received_tax = Decimal("0.00")

        for item in po.items:
            if not item.product_id:
                continue
            ordered_qty = Decimal(str(item.quantity))
            cur_rcv = getattr(item, 'received_quantity', None)
            cur_rcv = Decimal(str(cur_rcv)) if cur_rcv is not None else Decimal("0.000")

            if received_quantities and (item.id in received_quantities or item.product_id in received_quantities):
                rcv_qty = Decimal(str(received_quantities.get(item.id, received_quantities.get(item.product_id, 0))))
            else:
                rcv_qty = max(Decimal("0.000"), ordered_qty - cur_rcv)

            if cur_rcv + rcv_qty > ordered_qty:
                raise ValueError(
                    f"Cannot receive more than ordered quantity for item '{item.item_description}'. "
                    f"Ordered: {ordered_qty}, Already received: {cur_rcv}, Attempted: {rcv_qty}"
                )

            item.received_quantity = cur_rcv + rcv_qty

            if rcv_qty > Decimal("0"):
                product = session.query(Product).filter(Product.id == item.product_id).first()
                if product:
                    product.stock_quantity += rcv_qty

                unit_pr = Decimal(str(item.unit_price or "0"))
                tx_rt = Decimal(str(item.tax_rate or "0"))
                taxable = (rcv_qty * unit_pr).quantize(Decimal("0.01"))
                tax_amt = (taxable * tx_rt / Decimal("100")).quantize(Decimal("0.01"))
                received_total += (taxable + tax_amt)
                received_tax += tax_amt

        # Check if all items are fully received
        all_fully_received = True
        for it in po.items:
            if it.product_id:
                tot_it_rcv = getattr(it, 'received_quantity', None)
                tot_it_rcv = Decimal(str(tot_it_rcv)) if tot_it_rcv is not None else Decimal("0.000")
                if tot_it_rcv < Decimal(str(it.quantity)):
                    all_fully_received = False
                    break

        is_partial = not all_fully_received
        po.status = "partially_received" if is_partial else "received"

        # Post Credit Voucher (Purchase: Cr Supplier)
        if received_total > Decimal("0"):
            from app.database.models import Voucher
            v_num = f"PUR/{po.po_number.split('/', 1)[-1]}" if "/" in po.po_number else f"PUR-{po.po_number}"
            existing = session.query(Voucher).filter(Voucher.voucher_number == v_num).first()
            if existing:
                v_num = f"{v_num}-{int(datetime.now().timestamp())}"
            v = Voucher(
                voucher_number=v_num,
                voucher_type="Credit",
                voucher_date=po.po_date,
                party_id=po.party_id,
                reference_no=po.po_number,
                reference_date=po.po_date,
                amount_untaxed=received_total - received_tax,
                total_tax=received_tax,
                total_amount=received_total,
                debit_amount=Decimal("0.00"),
                credit_amount=received_total,
                narration=f"Goods Receipt for PO #{po.po_number} ({'Partial' if is_partial else 'Full'})",
            )
            session.add(v)

        return {"status": po.status, "received_amount": float(received_total)}


def mark_as_received(po_id: int) -> bool:
    """Mark PO as fully received and update inventory stock."""
    res = receive_goods(po_id, received_quantities=None)
    return res["status"] in ("received", "partially_received")


def get_all_purchase_orders(
    from_date: date = None, to_date: date = None,
    party_id: int = None, status: str = None,
    search: str = None, limit: int = 200
) -> List[Dict[str, Any]]:
    """Fetch POs with filters."""
    with get_session() as session:
        query = session.query(PurchaseOrder).join(Party, PurchaseOrder.party_id == Party.id)
        if from_date:
            query = query.filter(PurchaseOrder.po_date >= from_date)
        if to_date:
            query = query.filter(PurchaseOrder.po_date <= to_date)
        if party_id:
            query = query.filter(PurchaseOrder.party_id == party_id)
        if status and status != "All":
            query = query.filter(PurchaseOrder.status == status)
        if search:
            p = f"%{search.strip()}%"
            query = query.filter(or_(PurchaseOrder.po_number.ilike(p), Party.name.ilike(p)))
        pos = query.order_by(desc(PurchaseOrder.po_date), desc(PurchaseOrder.id)).limit(limit).all()
        return [po.to_dict() for po in pos]


def get_purchase_order_by_id(po_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single PO with items."""
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return None
        d = po.to_dict()
        d["items"] = [it.to_dict() for it in po.items]
        return d


def delete_purchase_order(po_id: int) -> bool:
    """Delete a PO."""
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return False
        session.delete(po)
        return True


def get_po_count() -> int:
    """Get total PO count."""
    with get_session() as session:
        return session.query(PurchaseOrder).count()
