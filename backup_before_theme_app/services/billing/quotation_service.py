"""
Quotation Service
CRUD and Business Logic for Quotations & Estimates.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import Quotation, QuotationItem, Party, CompanyProfile, Invoice, InvoiceItem, Product, Voucher
from app.services.billing.gst_engine import GSTEngine, TransactionType
from app.config import get_financial_year


def generate_quotation_number(session, q_date: date) -> str:
    """Generate next sequential quotation number: QT/{FY}/{SEQ:04d}."""
    fy = get_financial_year(q_date)
    pattern = f"QT/{fy}/%"
    last = session.query(Quotation).filter(
        Quotation.quotation_number.like(pattern)
    ).order_by(desc(Quotation.id)).first()
    seq = 1
    if last and last.quotation_number:
        try:
            seq = int(last.quotation_number.split("/")[-1]) + 1
        except (ValueError, IndexError):
            pass
    return f"QT/{fy}/{seq:04d}"


def calculate_quotation_totals(items_data: List[Dict[str, Any]], company_sc: str, party_sc: str, tax_mode: int):
    """Calculate quotation totals and GST breakdowns."""
    if tax_mode == 1:
        is_inter = False
    elif tax_mode == 2:
        is_inter = True
    else:
        is_inter = (company_sc.strip() != party_sc.strip()) if company_sc and party_sc else False

    t_type = TransactionType.INTER_STATE if is_inter else TransactionType.INTRA_STATE

    subtotal = Decimal("0.00")
    cgst = Decimal("0.00")
    sgst = Decimal("0.00")
    igst = Decimal("0.00")
    processed = []

    for it in items_data:
        qty = Decimal(str(it.get("quantity", "1") or "1"))
        price = Decimal(str(it.get("unit_price", "0") or "0"))
        disc = Decimal(str(it.get("discount_pct", "0") or "0"))
        tax_pct = Decimal(str(it.get("gst_rate_pct", "0") or "0"))

        r = GSTEngine.calculate_line_item(qty, price, disc, tax_pct, t_type)
        it_copy = dict(it)
        it_copy.update({
            "taxable_value": r["taxable_value"],
            "cgst_amount": r["cgst_amt"],
            "sgst_amount": r["sgst_amt"],
            "igst_amount": r["igst_amt"],
            "total_amount": r["total_amount"],
        })
        processed.append(it_copy)
        subtotal += r["taxable_value"]
        cgst += r["cgst_amt"]
        sgst += r["sgst_amt"]
        igst += r["igst_amt"]

    tax = cgst + sgst + igst
    total = subtotal + tax
    return subtotal, cgst, sgst, igst, tax, total, processed, is_inter


def create_quotation(data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Quotation:
    """Create a new quotation with line items."""
    if not items_data:
        raise ValueError("Quotation must have at least one item.")

    with get_session() as session:
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party:
            raise ValueError("Party not found.")

        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party.state_code else c_sc

        tax_mode = data.get("tax_mode", 0)
        subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_quotation_totals(
            items_data, c_sc, p_sc, tax_mode
        )

        q_date = data.get("quotation_date") or date.today()
        q_num = data.get("quotation_number") or generate_quotation_number(session, q_date)
        valid_until = data.get("valid_until")

        quotation = Quotation(
            quotation_number=q_num,
            quotation_date=q_date,
            valid_until=valid_until,
            party_id=party.id,
            subtotal=subtotal,
            cgst_total=cgst,
            sgst_total=sgst,
            igst_total=igst,
            tax_amount=tax,
            total_amount=total,
            status=data.get("status", "draft"),
            notes=data.get("notes", ""),
            is_interstate=is_inter,
            shipping_address=data.get("shipping_address"),
            transporter_name=data.get("transporter_name"),
            vehicle_no=data.get("vehicle_no"),
            lr_no=data.get("lr_no"),
            lr_date=data.get("lr_date"),
            eway_bill_no=data.get("eway_bill_no"),
            destination=data.get("destination"),
            terms_and_conditions=data.get("terms_and_conditions"),
            bank_name=data.get("bank_name"),
            bank_ac_no=data.get("bank_ac_no"),
            bank_ifsc=data.get("bank_ifsc"),
            po_number=data.get("po_number"),
            reference_number=data.get("reference_number"),
        )
        session.add(quotation)
        session.flush()

        for it in processed:
            session.add(QuotationItem(
                quotation_id=quotation.id,
                product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                taxable_value=it["taxable_value"],
                gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                cgst_amount=it["cgst_amount"],
                sgst_amount=it["sgst_amount"],
                igst_amount=it["igst_amount"],
                total_amount=it["total_amount"],
            ))

        session.flush()
        session.refresh(quotation)
        return quotation


def get_all_quotations(from_date=None, to_date=None, party_id=None, status=None, search=None, limit=200) -> List[Dict[str, Any]]:
    """Retrieve all quotations with optional filters."""
    with get_session() as session:
        q = session.query(Quotation).join(Party, Quotation.party_id == Party.id)
        if from_date:
            q = q.filter(Quotation.quotation_date >= from_date)
        if to_date:
            q = q.filter(Quotation.quotation_date <= to_date)
        if party_id:
            q = q.filter(Quotation.party_id == party_id)
        if status and status.lower() != "all":
            q = q.filter(Quotation.status == status.lower())
        if search:
            p = f"%{search.strip()}%"
            q = q.filter(or_(
                Quotation.quotation_number.ilike(p),
                Party.name.ilike(p),
                Quotation.reference_number.ilike(p)
            ))

        results = []
        for quote in q.order_by(desc(Quotation.quotation_date), desc(Quotation.id)).limit(limit).all():
            d = quote.to_dict()
            results.append(d)
        return results


def get_quotation_by_id(q_id: int) -> Optional[Dict[str, Any]]:
    """Get full quotation details by ID."""
    with get_session() as session:
        quote = session.query(Quotation).filter(Quotation.id == q_id).first()
        if not quote:
            return None
        d = quote.to_dict()
        d["items"] = [it.to_dict() for it in quote.items]
        d["party_gstin"] = quote.party.gstin if quote.party else ""
        d["party_address"] = quote.party.address if quote.party else ""
        d["party_state"] = quote.party.state if quote.party else ""
        d["party_phone"] = quote.party.phone if quote.party else ""
        d["party_name"] = quote.party.name if quote.party else ""
        return d


def update_quotation(q_id: int, q_data: Dict[str, Any], items_data: List[Dict[str, Any]] = None) -> Optional[Quotation]:
    """Update an existing quotation."""
    with get_session() as session:
        quote = session.query(Quotation).filter(Quotation.id == q_id).first()
        if not quote:
            return None

        party = session.query(Party).filter(Party.id == q_data.get("party_id", quote.party_id)).first()
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party and party.state_code else c_sc

        if items_data:
            tax_mode = q_data.get("tax_mode", 0)
            subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_quotation_totals(
                items_data, c_sc, p_sc, tax_mode
            )

            quote.subtotal = subtotal
            quote.cgst_total = cgst
            quote.sgst_total = sgst
            quote.igst_total = igst
            quote.tax_amount = tax
            quote.total_amount = total
            quote.is_interstate = is_inter

            # Replace items
            session.query(QuotationItem).filter(QuotationItem.quotation_id == q_id).delete()
            for it in processed:
                session.add(QuotationItem(
                    quotation_id=q_id,
                    product_id=it.get("product_id"),
                    item_description=it.get("item_description", ""),
                    hsn_code=it.get("hsn_code", ""),
                    quantity=Decimal(str(it.get("quantity", "1"))),
                    unit=it.get("unit", "PCS"),
                    unit_price=Decimal(str(it.get("unit_price", "0"))),
                    discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                    taxable_value=it["taxable_value"],
                    gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                    cgst_amount=it["cgst_amount"],
                    sgst_amount=it["sgst_amount"],
                    igst_amount=it["igst_amount"],
                    total_amount=it["total_amount"],
                ))

        for key in (
            "party_id", "quotation_date", "valid_until", "status", "notes",
            "shipping_address", "transporter_name", "vehicle_no", "lr_no",
            "lr_date", "eway_bill_no", "destination", "terms_and_conditions",
            "bank_name", "bank_ac_no", "bank_ifsc", "po_number", "reference_number"
        ):
            if key in q_data:
                setattr(quote, key, q_data[key])

        session.flush()
        session.refresh(quote)
        return quote


def delete_quotation(q_id: int) -> bool:
    """Delete quotation by ID."""
    with get_session() as session:
        quote = session.query(Quotation).filter(Quotation.id == q_id).first()
        if not quote:
            return False
        session.delete(quote)
        return True


def get_quotation_count() -> int:
    """Get total count of quotations."""
    with get_session() as session:
        return session.query(Quotation).count()


def get_quotation_kpis() -> Dict[str, Any]:
    """Calculate dashboard summary KPIs for quotations."""
    with get_session() as session:
        quotes = session.query(Quotation).all()
        total_count = len(quotes)
        total_val = sum(float(q.total_amount or 0) for q in quotes)
        draft_count = sum(1 for q in quotes if q.status == "draft")
        sent_count = sum(1 for q in quotes if q.status == "sent")
        accepted_count = sum(1 for q in quotes if q.status == "accepted")
        converted_count = sum(1 for q in quotes if q.status == "converted")
        pending_val = sum(float(q.total_amount or 0) for q in quotes if q.status in ("draft", "sent"))

        return {
            "total_count": total_count,
            "total_value": total_val,
            "draft_count": draft_count,
            "sent_count": sent_count,
            "accepted_count": accepted_count,
            "converted_count": converted_count,
            "pending_value": pending_val,
        }


def convert_to_invoice(q_id: int) -> Optional[Invoice]:
    """Convert a quotation into an official Tax Invoice and deduct stock."""
    with get_session() as session:
        quote = session.query(Quotation).filter(Quotation.id == q_id).first()
        if not quote:
            return None

        q_items = session.query(QuotationItem).filter(QuotationItem.quotation_id == q_id).all()
        if not q_items:
            raise ValueError("Quotation has no items to convert.")

        party = session.query(Party).filter(Party.id == quote.party_id).first()
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party and party.state_code else c_sc

        from app.services.billing.invoice_service import generate_invoice_number, calculate_invoice_totals
        inv_date = date.today()
        inv_number = generate_invoice_number(session, inv_date)

        items_data = []
        for it in q_items:
            items_data.append({
                "product_id": it.product_id,
                "item_description": it.item_description,
                "hsn_code": it.hsn_code,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": float(it.unit_price),
                "discount_pct": float(it.discount_pct),
                "gst_rate_pct": float(it.gst_rate_pct),
            })

        subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
            items_data, c_sc, p_sc, 0
        )

        invoice = Invoice(
            invoice_number=inv_number,
            invoice_date=inv_date,
            party_id=quote.party_id,
            subtotal=subtotal,
            cgst_total=cgst,
            sgst_total=sgst,
            igst_total=igst,
            tax_amount=tax,
            total_amount=total,
            status="final",
            notes=quote.notes,
            is_interstate=is_inter,
            shipping_address=quote.shipping_address,
            transporter_name=quote.transporter_name,
            vehicle_no=quote.vehicle_no,
            lr_no=quote.lr_no,
            lr_date=quote.lr_date,
            eway_bill_no=quote.eway_bill_no,
            destination=quote.destination,
            terms_and_conditions=quote.terms_and_conditions,
            bank_name=quote.bank_name,
            bank_ac_no=quote.bank_ac_no,
            bank_ifsc=quote.bank_ifsc,
            po_number=quote.po_number,
            pi_number=quote.quotation_number,  # Link back to quotation number
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

            if it.get("product_id"):
                product = session.query(Product).filter(Product.id == it["product_id"]).first()
                if product:
                    qty = float(it.get("quantity", 0))
                    product.stock_quantity = max(Decimal("0"), product.stock_quantity - Decimal(str(qty)))

        # Post to General Ledger (Voucher)
        from app.services.billing.invoice_service import post_sales_voucher
        post_sales_voucher(
            invoice,
            session=session,
            reference_no=quote.quotation_number,
            narration=f"Tax Invoice #{invoice.invoice_number} (From Quote #{quote.quotation_number})"
        )

        # Mark quotation as converted
        quote.status = "converted"

        session.flush()
        session.refresh(invoice)
        return invoice

