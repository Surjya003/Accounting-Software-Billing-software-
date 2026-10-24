"""
Purchase Order Service
CRUD operations for Purchase Orders with stock receipt tracking.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import PurchaseOrder, PurchaseOrderItem, Product, Party, CompanyProfile, Voucher, Invoice
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
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
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
            from app.services.validation_helpers import normalize_tax_rate
            tax_rate = normalize_tax_rate(item)
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
            revision=po_data.get("revision", "0"),
            quotation_ref=po_data.get("quotation_ref"),
            quotation_date=po_data.get("quotation_date"),
            delivery_required_by=po_data.get("delivery_required_by"),
            payment_terms=po_data.get("payment_terms"),
            delivery_terms=po_data.get("delivery_terms"),
            mode_of_dispatch=po_data.get("mode_of_dispatch"),
            insurance=po_data.get("insurance"),
            ship_to_address=po_data.get("ship_to_address"),
            special_instructions=po_data.get("special_instructions"),
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
                delivery_date=it.get("delivery_date"),
                item_code=it.get("item_code"),
                tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                tax_amount=it.get("tax_amount", Decimal("0")),
                total_amount=it.get("total_amount", Decimal("0")),
            )
            session.add(item)
        
        session.flush()
        session.refresh(po)
        return po


def update_purchase_order(po_id: int, po_data: Dict[str, Any], items_data: Optional[List[Dict[str, Any]]] = None) -> Optional[PurchaseOrder]:
    """Update an existing purchase order."""
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return None
        for key in (
            "party_id", "po_date", "status", "notes",
            "revision", "quotation_ref", "quotation_date", "delivery_required_by",
            "payment_terms", "delivery_terms", "mode_of_dispatch", "insurance",
            "ship_to_address", "special_instructions"
        ):
            if key in po_data:
                setattr(po, key, po_data[key])
        if items_data:
            session.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po_id).delete()
            subtotal = Decimal("0.00")
            tax_total = Decimal("0.00")
            for it in items_data:
                qty = Decimal(str(it.get("quantity", "1")))
                rate = Decimal(str(it.get("unit_price", "0")))
                from app.services.validation_helpers import normalize_tax_rate
                tax_r = normalize_tax_rate(it)
                taxable = qty * rate
                tax_amt = (taxable * tax_r) / Decimal("100")
                tot = taxable + tax_amt
                subtotal += taxable
                tax_total += tax_amt
                session.add(PurchaseOrderItem(
                    po_id=po.id,
                    product_id=it.get("product_id"),
                    item_description=it.get("item_description", ""),
                    hsn_code=it.get("hsn_code", ""),
                    quantity=qty,
                    unit=it.get("unit", "PCS"),
                    unit_price=rate,
                    delivery_date=it.get("delivery_date"),
                    item_code=it.get("item_code"),
                    tax_rate=tax_r,
                    tax_amount=tax_amt,
                    total_amount=tot,
                ))
            po.subtotal = subtotal
            po.tax_amount = tax_total
            po.total_amount = subtotal + tax_total
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
        if po.status in ("received", "cancelled"):
            raise ValueError(f"Purchase Order #{po.po_number} is already marked as {po.status} and cannot receive goods.")

        received_total = Decimal("0.00")
        received_tax = Decimal("0.00")

        for item in po.items:
            if not item.product_id:
                continue
            ordered_qty = Decimal(str(item.quantity))
            cur_rcv = getattr(item, 'received_quantity', None)
            cur_rcv = Decimal(str(cur_rcv)) if cur_rcv is not None else Decimal("0.000")

            if received_quantities and (item.id in received_quantities or item.product_id in received_quantities):
                val = received_quantities.get(item.id, received_quantities.get(item.product_id, 0))
                rcv_qty = Decimal(str(val))
                if rcv_qty <= Decimal("0"):
                    raise ValueError(f"Received quantity must be greater than zero for item '{item.item_description}'.")
            else:
                rcv_qty = max(Decimal("0.000"), ordered_qty - cur_rcv)

            remaining = ordered_qty - cur_rcv
            if rcv_qty > remaining:
                raise ValueError(
                    f"Cannot receive more than remaining ordered quantity for item '{item.item_description}'. "
                    f"Ordered: {ordered_qty}, Already received: {cur_rcv}, Remaining: {remaining}, Attempted: {rcv_qty}"
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

        # Post Credit Voucher (Purchase: Cr Supplier) with GST breakdown
        if received_total > Decimal("0"):
            from app.database.models import Voucher, CompanyProfile
            company = session.query(CompanyProfile).first()
            c_sc = company.state_code if company and company.state_code else "27"
            p_sc = po.party.state_code if po.party and po.party.state_code else c_sc
            is_inter = (p_sc != c_sc)

            cgst_amt = Decimal("0.00")
            sgst_amt = Decimal("0.00")
            igst_amt = Decimal("0.00")
            if is_inter:
                igst_amt = received_tax
            else:
                half = (received_tax / Decimal("2")).quantize(Decimal("0.01"))
                cgst_amt = half
                sgst_amt = received_tax - half

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
                cgst_amount=cgst_amt,
                sgst_amount=sgst_amt,
                igst_amount=igst_amt,
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
    """Delete a PO only if draft and no goods have been received."""
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return False

        # Check if any received quantity
        total_rcv = sum(Decimal(str(getattr(it, 'received_quantity', 0) or 0)) for it in po.items)
        if total_rcv > Decimal("0") or po.status in ("received", "partially_received"):
            raise ValueError(
                f"Cannot delete Purchase Order #{po.po_number} because goods have already been received. "
                f"Cancel the PO or process a purchase return instead."
            )

        # Check if any vouchers exist for this PO
        v_count = session.query(Voucher).filter(
            or_(Voucher.reference_no == po.po_number, Voucher.voucher_number.like(f"PUR/%{po.po_number}%"))
        ).count()
        if v_count > 0:
            raise ValueError(
                f"Cannot delete Purchase Order #{po.po_number} with existing vouchers. Cancel the PO instead."
            )

        session.delete(po)
        return True


def cancel_purchase_order(po_id: int) -> bool:
    """Cancels a PO, reverses any received product stock, and removes associated vouchers."""
    with get_session() as session:
        po = session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return False
        if po.status == "cancelled":
            return True

        # Reverse received stock
        for it in po.items:
            if it.product_id:
                rcv = Decimal(str(getattr(it, 'received_quantity', 0) or 0))
                if rcv > Decimal("0"):
                    prod = session.query(Product).filter(Product.id == it.product_id).first()
                    if prod:
                        prod.stock_quantity -= rcv
                it.received_quantity = Decimal("0.000")

        # Delete associated vouchers
        vouchers = session.query(Voucher).filter(
            or_(Voucher.reference_no == po.po_number, Voucher.voucher_number.like(f"%{po.po_number}%"))
        ).all()
        for v in vouchers:
            session.delete(v)

        po.status = "cancelled"
        return True


def check_orphaned_vouchers(session=None) -> List[Dict[str, Any]]:
    """Maintenance check: reports vouchers with a source reference that no longer exists in DB."""
    own = False
    if session is None:
        session = get_session().__enter__()
        own = True
    try:
        orphaned = []
        # Check vouchers referencing invoices
        v_inv = session.query(Voucher).filter(Voucher.reference_no.like("INV%")).all()
        for v in v_inv:
            inv_exists = session.query(Invoice).filter(Invoice.invoice_number == v.reference_no).first()
            if not inv_exists:
                orphaned.append({
                    "voucher_id": v.id,
                    "voucher_number": v.voucher_number,
                    "reference_no": v.reference_no,
                    "reason": f"Referenced Invoice #{v.reference_no} does not exist"
                })

        # Check vouchers referencing purchase orders
        v_po = session.query(Voucher).filter(Voucher.reference_no.like("PO%")).all()
        for v in v_po:
            po_exists = session.query(PurchaseOrder).filter(PurchaseOrder.po_number == v.reference_no).first()
            if not po_exists:
                orphaned.append({
                    "voucher_id": v.id,
                    "voucher_number": v.voucher_number,
                    "reference_no": v.reference_no,
                    "reason": f"Referenced Purchase Order #{v.reference_no} does not exist"
                })
        return orphaned
    finally:
        if own:
            session.close()


def get_po_count() -> int:
    """Get total PO count."""
    with get_session() as session:
        return session.query(PurchaseOrder).count()
