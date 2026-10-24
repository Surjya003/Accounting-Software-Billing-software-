"""
Invoice Service
CRUD operations for GST Tax Invoices with line items and stock management.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import Invoice, InvoiceItem, Product, Party, CompanyProfile, ProformaInvoice, Voucher
from app.services.billing.gst_engine import GSTEngine, TransactionType
from app.config import get_financial_year


def generate_invoice_number(session, invoice_date: date) -> str:
    """Generate next invoice number: INV/24-25/0001"""
    fy = get_financial_year(invoice_date)
    pattern = f"INV/{fy}/%"
    last = session.query(Invoice).filter(
        Invoice.invoice_number.like(pattern)
    ).order_by(desc(Invoice.id)).first()

    if last and last.invoice_number:
        try:
            seq = int(last.invoice_number.split("/")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"INV/{fy}/{seq:04d}"


def calculate_invoice_totals(items_data: List[Dict], company_state_code: str, party_state_code: str, tax_mode: int = 0):
    """Calculate GST for all items and return totals + processed items."""
    if tax_mode == 1:
        is_interstate = False
    elif tax_mode == 2:
        is_interstate = True
    else:
        is_interstate = (party_state_code.strip() != company_state_code.strip()) if party_state_code and company_state_code else False
        
    t_type = TransactionType.INTER_STATE if is_interstate else TransactionType.INTRA_STATE

    subtotal = Decimal("0.00")
    cgst_total = Decimal("0.00")
    sgst_total = Decimal("0.00")
    igst_total = Decimal("0.00")
    processed = []

    for item in items_data:
        qty = Decimal(str(item.get("quantity", "1")))
        if qty <= Decimal("0"):
            raise ValueError(f"Item quantity must be greater than zero.")
        rate = Decimal(str(item.get("unit_price", "0")))
        if rate < Decimal("0"):
            raise ValueError(f"Unit price cannot be negative.")
        disc = Decimal(str(item.get("discount_pct", "0")))
        if disc < Decimal("0") or disc > Decimal("100"):
            raise ValueError("Discount percentage must be between 0% and 100%.")
        gst = Decimal(str(item.get("gst_rate_pct", "0")))

        result = GSTEngine.calculate_line_item(qty, rate, disc, gst, t_type)

        item_copy = dict(item)
        item_copy.update({
            "taxable_value": result["taxable_value"],
            "cgst_amount": result["cgst_amt"],
            "sgst_amount": result["sgst_amt"],
            "igst_amount": result["igst_amt"],
            "total_amount": result["total_amount"],
        })
        processed.append(item_copy)

        subtotal += result["taxable_value"]
        cgst_total += result["cgst_amt"]
        sgst_total += result["sgst_amt"]
        igst_total += result["igst_amt"]

    tax_total = cgst_total + sgst_total + igst_total
    grand_total = subtotal + tax_total
    return subtotal, cgst_total, sgst_total, igst_total, tax_total, grand_total, processed, is_interstate


def post_sales_voucher(
    invoice,
    session=None,
    reference_no: Optional[str] = None,
    narration: Optional[str] = None
) -> Voucher:
    """Post a sales (debit) voucher for an invoice to the general ledger."""
    from sqlalchemy.orm import Session as SASession, object_session
    if isinstance(invoice, SASession):
        session, invoice = invoice, session

    own_session = False
    if session is None:
        session = object_session(invoice)
        if session is None:
            from app.database.connection import get_session
            session = get_session()
            own_session = True

    try:
        existing_v = session.query(Voucher).filter(Voucher.voucher_number == invoice.invoice_number).first()
        if existing_v:
            return existing_v

        items = session.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).all() if invoice.id else []
        item_desc_summary = ", ".join(it.item_description for it in items[:3] if it.item_description)

        ref = reference_no or invoice.po_number or invoice.invoice_number
        if narration:
            narr = narration
        else:
            is_inter = getattr(invoice, 'is_interstate', False)
            narr = f"Tax Invoice #{invoice.invoice_number} ({'Inter-State' if is_inter else 'Intra-State'})"

        v = Voucher(
            voucher_number=invoice.invoice_number,
            voucher_type="Debit",
            voucher_date=invoice.invoice_date,
            party_id=invoice.party_id,
            product=item_desc_summary[:255] if item_desc_summary else None,
            reference_no=ref,
            reference_date=invoice.invoice_date,
            amount_untaxed=invoice.subtotal,
            cgst_amount=invoice.cgst_total,
            sgst_amount=invoice.sgst_total,
            igst_amount=invoice.igst_total,
            total_tax=invoice.tax_amount,
            total_amount=invoice.total_amount,
            debit_amount=invoice.total_amount,
            credit_amount=Decimal("0.00"),
            narration=narr,
            is_tax_invoice=True,
        )
        session.add(v)
        session.flush()
        return v
    finally:
        if own_session:
            session.commit()
            session.close()


def create_invoice(invoice_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Invoice:
    """Create a new invoice with line items and update stock."""
    if not items_data:
        raise ValueError("Invoice must have at least one line item.")

    with get_session() as session:
        party = session.query(Party).filter(Party.id == invoice_data.get("party_id")).first()
        if not party:
            raise ValueError("Selected party does not exist.")

        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company else "27"
        party_sc = party.state_code if party.state_code else company_sc

        inv_date = invoice_data.get("invoice_date", date.today())
        inv_number = invoice_data.get("invoice_number") or generate_invoice_number(session, inv_date)

        tax_mode = invoice_data.get("tax_mode", 0)
        subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
            items_data, company_sc, party_sc, tax_mode
        )

        invoice = Invoice(
            invoice_number=inv_number,
            invoice_date=inv_date,
            party_id=party.id,
            subtotal=subtotal,
            cgst_total=cgst,
            sgst_total=sgst,
            igst_total=igst,
            tax_amount=tax,
            total_amount=total,
            status=invoice_data.get("status", "draft"),
            notes=invoice_data.get("notes", ""),
            is_interstate=is_inter,
            shipping_address=invoice_data.get("shipping_address"),
            transporter_name=invoice_data.get("transporter_name"),
            vehicle_no=invoice_data.get("vehicle_no"),
            lr_no=invoice_data.get("lr_no"),
            lr_date=invoice_data.get("lr_date"),
            eway_bill_no=invoice_data.get("eway_bill_no"),
            destination=invoice_data.get("destination"),
            terms_and_conditions=invoice_data.get("terms_and_conditions"),
            bank_name=invoice_data.get("bank_name"),
            bank_ac_no=invoice_data.get("bank_ac_no"),
            bank_ifsc=invoice_data.get("bank_ifsc"),
            po_number=invoice_data.get("po_number"),
            pi_number=invoice_data.get("pi_number")
        )
        session.add(invoice)
        session.flush()

        for it in processed:
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                taxable_value=it.get("taxable_value", Decimal("0")),
                gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                cgst_amount=it.get("cgst_amount", Decimal("0")),
                sgst_amount=it.get("sgst_amount", Decimal("0")),
                igst_amount=it.get("igst_amount", Decimal("0")),
                total_amount=it.get("total_amount", Decimal("0")),
            )
            session.add(item)

            # Update stock for finalized invoices
            if invoice.status == "final" and it.get("product_id"):
                product = session.query(Product).filter(Product.id == it["product_id"]).first()
                if product:
                    qty = float(it.get("quantity", 0))
                    product.stock_quantity = max(Decimal("0"), product.stock_quantity - Decimal(str(qty)))

        # Post to General Ledger (Voucher) if finalized
        if invoice.status == "final":
            post_sales_voucher(invoice, session=session)

        # Bidirectional sync: if pi_number is set, update linked proforma status
        if invoice.pi_number:
            pf = session.query(ProformaInvoice).filter(
                ProformaInvoice.proforma_number == invoice.pi_number
            ).first()
            if pf and pf.status != "converted":
                pf.status = "converted"

        session.flush()
        session.refresh(invoice)
        return invoice


def get_invoice_by_id(invoice_id: int) -> Optional[Dict[str, Any]]:
    """Fetch invoice with all details."""
    with get_session() as session:
        inv = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            return None
        d = inv.to_dict()
        d["items"] = [it.to_dict() for it in inv.items]
        d["party_gstin"] = inv.party.gstin if inv.party else ""
        d["party_address"] = inv.party.address if inv.party else ""
        d["party_state"] = inv.party.state if inv.party else ""
        d["party_phone"] = inv.party.phone if inv.party else ""
        d["party_name"] = inv.party.name if inv.party else ""
        return d


def get_all_invoices(
    from_date: date = None,
    to_date: date = None,
    party_id: int = None,
    status: str = None,
    search: str = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """Fetch invoices with filters."""
    with get_session() as session:
        query = session.query(Invoice).join(Party, Invoice.party_id == Party.id)
        if from_date:
            query = query.filter(Invoice.invoice_date >= from_date)
        if to_date:
            query = query.filter(Invoice.invoice_date <= to_date)
        if party_id:
            query = query.filter(Invoice.party_id == party_id)
        if status and status != "All":
            query = query.filter(Invoice.status == status)
        if search:
            p = f"%{search.strip()}%"
            query = query.filter(or_(
                Invoice.invoice_number.ilike(p),
                Party.name.ilike(p),
            ))
        invoices = query.order_by(desc(Invoice.invoice_date), desc(Invoice.id)).limit(limit).all()
        return [inv.to_dict() for inv in invoices]


def update_invoice(invoice_id: int, invoice_data: Dict, items_data: List[Dict] = None) -> Optional[Invoice]:
    """Update an existing invoice."""
    with get_session() as session:
        invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None

        party = session.query(Party).filter(Party.id == invoice_data.get("party_id", invoice.party_id)).first()
        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company else "27"
        party_sc = party.state_code if party and party.state_code else company_sc

        if items_data:
            tax_mode = invoice_data.get("tax_mode", 0)
            subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
                items_data, company_sc, party_sc, tax_mode
            )
            invoice.subtotal = subtotal
            invoice.cgst_total = cgst
            invoice.sgst_total = sgst
            invoice.igst_total = igst
            invoice.tax_amount = tax
            invoice.total_amount = total
            invoice.is_interstate = is_inter

            # Replace items
            session.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
            for it in processed:
                item = InvoiceItem(
                    invoice_id=invoice_id,
                    product_id=it.get("product_id"),
                    item_description=it.get("item_description", ""),
                    hsn_code=it.get("hsn_code", ""),
                    quantity=Decimal(str(it.get("quantity", "1"))),
                    unit=it.get("unit", "PCS"),
                    unit_price=Decimal(str(it.get("unit_price", "0"))),
                    discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                    taxable_value=it.get("taxable_value", Decimal("0")),
                    gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                    cgst_amount=it.get("cgst_amount", Decimal("0")),
                    sgst_amount=it.get("sgst_amount", Decimal("0")),
                    igst_amount=it.get("igst_amount", Decimal("0")),
                    total_amount=it.get("total_amount", Decimal("0")),
                )
                session.add(item)

        for key in (
            "party_id", "invoice_date", "status", "notes",
            "shipping_address", "transporter_name", "vehicle_no", "lr_no",
            "lr_date", "eway_bill_no", "destination", "terms_and_conditions",
            "bank_name", "bank_ac_no", "bank_ifsc", "po_number", "pi_number"
        ):
            if key in invoice_data:
                setattr(invoice, key, invoice_data[key])

        # Bidirectional sync: if pi_number is set, update linked proforma status
        if "pi_number" in invoice_data and invoice_data["pi_number"]:
            pf = session.query(ProformaInvoice).filter(
                ProformaInvoice.proforma_number == invoice_data["pi_number"]
            ).first()
            if pf and pf.status != "converted":
                pf.status = "converted"

        session.flush()
        session.refresh(invoice)
        return invoice


def cancel_invoice(invoice_id: int) -> bool:
    """Cancels an invoice, restores product stock if it was finalized, and removes the ledger voucher."""
    with get_session() as session:
        invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return False
        if invoice.status == "cancelled":
            return True
        if invoice.status == "final":
            for it in invoice.items:
                if it.product_id:
                    prod = session.query(Product).filter(Product.id == it.product_id).first()
                    if prod:
                        prod.stock_quantity += it.quantity
            v = session.query(Voucher).filter(Voucher.voucher_number == invoice.invoice_number).first()
            if v:
                session.delete(v)
        invoice.status = "cancelled"
        return True


def delete_invoice(invoice_id: int) -> bool:
    """Delete an invoice and its items, restoring stock and removing ledger entry if final."""
    with get_session() as session:
        invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return False
        if invoice.status == "final":
            for it in invoice.items:
                if it.product_id:
                    prod = session.query(Product).filter(Product.id == it.product_id).first()
                    if prod:
                        prod.stock_quantity += it.quantity
            v = session.query(Voucher).filter(Voucher.voucher_number == invoice.invoice_number).first()
            if v:
                session.delete(v)
        session.delete(invoice)
        return True


def get_today_sales_total() -> float:
    """Get total sales amount for today."""
    with get_session() as session:
        result = session.query(func.coalesce(func.sum(Invoice.total_amount), 0)).filter(
            Invoice.invoice_date == date.today(),
            Invoice.status == "final"
        ).scalar()
        return float(result or 0)


def get_month_sales_total() -> float:
    """Get total sales for current month."""
    today = date.today()
    month_start = today.replace(day=1)
    with get_session() as session:
        result = session.query(func.coalesce(func.sum(Invoice.total_amount), 0)).filter(
            Invoice.invoice_date >= month_start,
            Invoice.status == "final"
        ).scalar()
        return float(result or 0)


def get_invoice_count() -> int:
    """Get total invoice count."""
    with get_session() as session:
        return session.query(Invoice).count()
