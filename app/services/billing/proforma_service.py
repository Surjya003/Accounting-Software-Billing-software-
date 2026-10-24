"""
Proforma Invoice Service
CRUD for Proforma Invoices (Quotations).
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_, func

from app.database.connection import get_session
from app.database.models import ProformaInvoice, ProformaItem, Party, CompanyProfile, Invoice, InvoiceItem, Product
from app.services.billing.gst_engine import GSTEngine, TransactionType
from app.config import get_financial_year


def generate_proforma_number(session, pf_date: date) -> str:
    fy = get_financial_year(pf_date)
    pattern = f"PF/{fy}/%"
    last = session.query(ProformaInvoice).filter(
        ProformaInvoice.proforma_number.like(pattern)
    ).order_by(desc(ProformaInvoice.id)).first()
    seq = 1
    if last and last.proforma_number:
        try:
            seq = int(last.proforma_number.split("/")[-1]) + 1
        except ValueError:
            pass
    return f"PF/{fy}/{seq:04d}"


def create_proforma(data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> ProformaInvoice:
    if not items_data:
        raise ValueError("Proforma must have at least one item.")
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party:
            raise ValueError("Party not found.")
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company else "27"
        p_sc = party.state_code if party.state_code else c_sc

        tax_mode = data.get("tax_mode", 0)
        if tax_mode == 1:
            is_inter = False
        elif tax_mode == 2:
            is_inter = True
        else:
            is_inter = (c_sc.strip() != p_sc.strip()) if c_sc and p_sc else False
        t_type = TransactionType.INTER_STATE if is_inter else TransactionType.INTRA_STATE

        pf_date = data.get("proforma_date", date.today())
        pf_num = data.get("proforma_number") or generate_proforma_number(session, pf_date)

        subtotal = cgst = sgst = igst = Decimal("0.00")
        processed = []
        for it in items_data:
            from app.services.validation_helpers import normalize_tax_rate
            tax_rate = normalize_tax_rate(it)
            r = GSTEngine.calculate_line_item(
                Decimal(str(it.get("quantity", "1"))), Decimal(str(it.get("unit_price", "0"))),
                Decimal(str(it.get("discount_pct", "0"))), tax_rate, t_type
            )
            it_copy = dict(it)
            it_copy.update({"taxable_value": r["taxable_value"], "cgst_amount": r["cgst_amt"],
                            "sgst_amount": r["sgst_amt"], "igst_amount": r["igst_amt"], "total_amount": r["total_amount"]})
            processed.append(it_copy)
            subtotal += r["taxable_value"]; cgst += r["cgst_amt"]; sgst += r["sgst_amt"]; igst += r["igst_amt"]

        tax = cgst + sgst + igst
        pf = ProformaInvoice(
            proforma_number=pf_num, proforma_date=pf_date, party_id=party.id,
            subtotal=subtotal, cgst_total=cgst, sgst_total=sgst, igst_total=igst,
            tax_amount=tax, total_amount=subtotal + tax,
            status=data.get("status", "draft"), notes=data.get("notes", ""), is_interstate=is_inter,
            shipping_address=data.get("shipping_address"),
            transporter_name=data.get("transporter_name"),
            vehicle_no=str(data["vehicle_no"]).strip().upper() if data.get("vehicle_no") else None,
            lr_no=data.get("lr_no"),
            lr_date=data.get("lr_date"),
            eway_bill_no=data.get("eway_bill_no"),
            destination=data.get("destination"),
            terms_and_conditions=data.get("terms_and_conditions"),
            bank_name=data.get("bank_name"),
            bank_ac_no=data.get("bank_ac_no"),
            bank_ifsc=str(data["bank_ifsc"]).strip().upper() if data.get("bank_ifsc") else None,
            po_number=data.get("po_number"),
            pi_number=data.get("pi_number"),
            valid_until=data.get("valid_until"),
            advance_percent=Decimal(str(data["advance_percent"])) if data.get("advance_percent") is not None and str(data["advance_percent"]).strip() != "" else Decimal("0.00"),
            advance_received=Decimal(str(data["advance_received"])) if data.get("advance_received") is not None and str(data["advance_received"]).strip() != "" else Decimal("0.00"),
            payment_terms=data.get("payment_terms"),
            delivery_period=data.get("delivery_period"),
            customer_po_no=data.get("customer_po_no"),
            customer_po_date=data.get("customer_po_date"),
            linked_invoice_reference=data.get("linked_invoice_reference"),
        )
        session.add(pf); session.flush()
        for it in processed:
            session.add(ProformaItem(
                proforma_id=pf.id, product_id=it.get("product_id"),
                item_description=it.get("item_description", ""), hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))), unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))), discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                taxable_value=it["taxable_value"], gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                cgst_amount=it["cgst_amount"], sgst_amount=it["sgst_amount"],
                igst_amount=it["igst_amount"], total_amount=it["total_amount"],
            ))
        session.flush(); session.refresh(pf)
        return pf


def get_all_proformas(from_date=None, to_date=None, party_id=None, status=None, search=None, limit=200):
    with get_session() as session:
        q = session.query(ProformaInvoice).join(Party, ProformaInvoice.party_id == Party.id)
        if from_date: q = q.filter(ProformaInvoice.proforma_date >= from_date)
        if to_date: q = q.filter(ProformaInvoice.proforma_date <= to_date)
        if party_id: q = q.filter(ProformaInvoice.party_id == party_id)
        if status and status != "All": q = q.filter(ProformaInvoice.status == status)
        if search:
            p = f"%{search.strip()}%"
            q = q.filter(or_(ProformaInvoice.proforma_number.ilike(p), Party.name.ilike(p)))
        return [pf.to_dict() for pf in q.order_by(desc(ProformaInvoice.proforma_date), desc(ProformaInvoice.id)).limit(limit).all()]


def get_proforma_by_id(pf_id: int):
    with get_session() as session:
        pf = session.query(ProformaInvoice).filter(ProformaInvoice.id == pf_id).first()
        if not pf: return None
        d = pf.to_dict()
        d["items"] = [it.to_dict() for it in pf.items]
        d["party_gstin"] = pf.party.gstin if pf.party else ""
        d["party_address"] = pf.party.address if pf.party else ""
        d["party_state"] = pf.party.state if pf.party else ""
        d["party_phone"] = pf.party.phone if pf.party else ""
        d["party_name"] = pf.party.name if pf.party else ""
        return d


def get_proforma_by_number(pf_num: str):
    """Retrieve proforma invoice by its proforma_number."""
    with get_session() as session:
        pf = session.query(ProformaInvoice).filter(ProformaInvoice.proforma_number == pf_num).first()
        if not pf:
            return None
        d = pf.to_dict()
        d["items"] = [it.to_dict() for it in pf.items]
        d["party_gstin"] = pf.party.gstin if pf.party else ""
        d["party_address"] = pf.party.address if pf.party else ""
        d["party_state"] = pf.party.state if pf.party else ""
        d["party_phone"] = pf.party.phone if pf.party else ""
        d["party_name"] = pf.party.name if pf.party else ""
        return d


def update_proforma(pf_id: int, pf_data: Dict, items_data: List[Dict] = None):
    """Update an existing proforma invoice."""
    with get_session() as session:
        pf = session.query(ProformaInvoice).filter(ProformaInvoice.id == pf_id).first()
        if not pf:
            return None

        party = session.query(Party).filter(Party.id == pf_data.get("party_id", pf.party_id)).first()
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company else "27"
        p_sc = party.state_code if party and party.state_code else c_sc

        if items_data:
            tax_mode = pf_data.get("tax_mode", 0)
            if tax_mode == 1:
                is_inter = False
            elif tax_mode == 2:
                is_inter = True
            else:
                is_inter = (c_sc.strip() != p_sc.strip()) if c_sc and p_sc else False
            t_type = TransactionType.INTER_STATE if is_inter else TransactionType.INTRA_STATE

            subtotal = cgst = sgst = igst = Decimal("0.00")
            processed = []
            for it in items_data:
                from app.services.validation_helpers import normalize_tax_rate
                tax_rate = normalize_tax_rate(it)
                r = GSTEngine.calculate_line_item(
                    Decimal(str(it.get("quantity", "1"))), Decimal(str(it.get("unit_price", "0"))),
                    Decimal(str(it.get("discount_pct", "0"))), tax_rate, t_type
                )
                it_copy = dict(it)
                it_copy.update({"taxable_value": r["taxable_value"], "cgst_amount": r["cgst_amt"],
                                "sgst_amount": r["sgst_amt"], "igst_amount": r["igst_amt"], "total_amount": r["total_amount"]})
                processed.append(it_copy)
                subtotal += r["taxable_value"]; cgst += r["cgst_amt"]; sgst += r["sgst_amt"]; igst += r["igst_amt"]

            tax = cgst + sgst + igst
            pf.subtotal = subtotal
            pf.cgst_total = cgst
            pf.sgst_total = sgst
            pf.igst_total = igst
            pf.tax_amount = tax
            pf.total_amount = subtotal + tax
            pf.is_interstate = is_inter

            # Replace items
            session.query(ProformaItem).filter(ProformaItem.proforma_id == pf_id).delete()
            for it in processed:
                session.add(ProformaItem(
                    proforma_id=pf_id, product_id=it.get("product_id"),
                    item_description=it.get("item_description", ""), hsn_code=it.get("hsn_code", ""),
                    quantity=Decimal(str(it.get("quantity", "1"))), unit=it.get("unit", "PCS"),
                    unit_price=Decimal(str(it.get("unit_price", "0"))), discount_pct=Decimal(str(it.get("discount_pct", "0"))),
                    taxable_value=it["taxable_value"], gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                    cgst_amount=it["cgst_amount"], sgst_amount=it["sgst_amount"],
                    igst_amount=it["igst_amount"], total_amount=it["total_amount"],
                ))

        for key in (
            "party_id", "proforma_date", "status", "notes",
            "shipping_address", "transporter_name", "vehicle_no", "lr_no",
            "lr_date", "eway_bill_no", "destination", "terms_and_conditions",
            "bank_name", "bank_ac_no", "bank_ifsc", "po_number", "pi_number",
            "valid_until", "advance_percent", "advance_received", "payment_terms",
            "delivery_period", "customer_po_no", "customer_po_date", "linked_invoice_reference",
        ):
            if key in pf_data:
                val = pf_data[key]
                if key in ("vehicle_no", "bank_ifsc") and val:
                    val = str(val).strip().upper()
                setattr(pf, key, val)

        # Bidirectional sync: if status changed to converted, create/update linked invoice
        if "status" in pf_data and pf_data["status"] == "converted" and pf.proforma_number:
            # Check if invoice already exists with this pi_number
            existing_inv = session.query(Invoice).filter(Invoice.pi_number == pf.proforma_number).first()
            if not existing_inv:
                # Convert to invoice
                from app.services.billing.invoice_service import generate_invoice_number, calculate_invoice_totals
                inv_date = date.today()
                inv_number = generate_invoice_number(session, inv_date)

                items_data = []
                for it in pf.items:
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

                tax_mode = 0
                subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
                    items_data, c_sc, p_sc, tax_mode
                )

                invoice = Invoice(
                    invoice_number=inv_number,
                    invoice_date=inv_date,
                    party_id=pf.party_id,
                    subtotal=subtotal,
                    cgst_total=cgst,
                    sgst_total=sgst,
                    igst_total=igst,
                    tax_amount=tax,
                    total_amount=total,
                    status="final",
                    notes=pf.notes,
                    is_interstate=is_inter,
                    shipping_address=pf.shipping_address,
                    transporter_name=pf.transporter_name,
                    vehicle_no=pf.vehicle_no,
                    lr_no=pf.lr_no,
                    lr_date=pf.lr_date,
                    eway_bill_no=pf.eway_bill_no,
                    destination=pf.destination,
                    terms_and_conditions=pf.terms_and_conditions,
                    bank_name=pf.bank_name,
                    bank_ac_no=pf.bank_ac_no,
                    bank_ifsc=pf.bank_ifsc,
                    po_number=pf.po_number,
                    pi_number=pf.proforma_number,
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

        session.flush()
        session.refresh(pf)
        return pf


def delete_proforma(pf_id: int) -> bool:
    with get_session() as session:
        pf = session.query(ProformaInvoice).filter(ProformaInvoice.id == pf_id).first()
        if not pf: return False
        session.delete(pf); return True


def get_proforma_count() -> int:
    with get_session() as session:
        return session.query(ProformaInvoice).count()


def convert_to_invoice(pf_id: int) -> Optional[Invoice]:
    """Convert a proforma invoice to a tax invoice and deduct stock."""
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        pf = session.query(ProformaInvoice).filter(ProformaInvoice.id == pf_id).first()
        if not pf:
            return None
        if pf.status == "converted":
            raise ValueError(f"Proforma Invoice #{pf.proforma_number} has already been converted.")
        if pf.status in ("cancelled", "rejected"):
            raise ValueError(f"Cannot convert {pf.status} Proforma Invoice #{pf.proforma_number}.")

        # Atomic check-and-set to block concurrent double-conversion
        rowcount = session.query(ProformaInvoice).filter(
            ProformaInvoice.id == pf_id,
            ProformaInvoice.status.notin_(["converted", "cancelled", "rejected"])
        ).update({"status": "converted"}, synchronize_session=False)
        if rowcount == 0:
            raise ValueError(f"Proforma Invoice #{pf.proforma_number} has already been converted.")

        # Get proforma items
        pf_items = session.query(ProformaItem).filter(ProformaItem.proforma_id == pf_id).all()
        if not pf_items:
            raise ValueError("Proforma has no items to convert.")

        party = session.query(Party).filter(Party.id == pf.party_id).first()
        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company else "27"
        party_sc = party.state_code if party and party.state_code else company_sc
        allow_neg = getattr(company, "allow_negative_stock", False) if company else False

        # Generate invoice number
        from app.services.billing.invoice_service import generate_invoice_number
        inv_date = date.today()
        inv_number = generate_invoice_number(session, inv_date)

        # Prepare items data for invoice
        items_data = []
        for it in pf_items:
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

        # Calculate totals using invoice service logic
        from app.services.billing.invoice_service import calculate_invoice_totals
        tax_mode = 0  # Auto
        subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
            items_data, company_sc, party_sc, tax_mode
        )

        # Create invoice with proforma reference
        invoice = Invoice(
            invoice_number=inv_number,
            invoice_date=inv_date,
            party_id=pf.party_id,
            subtotal=subtotal,
            cgst_total=cgst,
            sgst_total=sgst,
            igst_total=igst,
            tax_amount=tax,
            total_amount=total,
            status="final",  # Auto-finalize on conversion
            notes=pf.notes,
            is_interstate=is_inter,
            shipping_address=pf.shipping_address,
            transporter_name=pf.transporter_name,
            vehicle_no=pf.vehicle_no,
            lr_no=pf.lr_no,
            lr_date=pf.lr_date,
            eway_bill_no=pf.eway_bill_no,
            destination=pf.destination,
            terms_and_conditions=pf.terms_and_conditions,
            bank_name=pf.bank_name,
            bank_ac_no=pf.bank_ac_no,
            bank_ifsc=pf.bank_ifsc,
            po_number=pf.po_number,
            pi_number=pf.proforma_number,  # Link back to proforma
            reference_no_date=f"{pf.proforma_number} dt {pf.proforma_date.strftime('%d-%m-%Y') if hasattr(pf.proforma_date, 'strftime') else str(pf.proforma_date)}",
            other_references=f"Proforma #{pf.proforma_number}",
            buyers_order_no=getattr(pf, "customer_po_no", "") or pf.po_number or "",
            buyers_order_date=getattr(pf, "customer_po_date", None),
            mode_terms_of_payment=getattr(pf, "payment_terms", "") or "",
            terms_of_delivery=getattr(pf, "delivery_period", "") or "",
        )
        pf.linked_invoice_reference = inv_number
        session.add(invoice)
        session.flush()

        # Add invoice items and deduct stock
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

            # Deduct stock for finalized invoice
            if it.get("product_id"):
                product = session.query(Product).filter(Product.id == it["product_id"]).first()
                if product:
                    qty = Decimal(str(it.get("quantity", "0")))
                    if not allow_neg and qty > product.stock_quantity:
                        raise ValueError(
                            f"Insufficient stock for product '{product.name}'. Available: {product.stock_quantity}, Requested: {qty}."
                        )
                    product.stock_quantity -= qty

        # Post sales voucher to ledger
        from app.services.billing.invoice_service import post_sales_voucher
        post_sales_voucher(
            invoice,
            session=session,
            reference_no=pf.proforma_number,
            narration=f"Tax Invoice #{invoice.invoice_number} (From Proforma #{pf.proforma_number})"
        )

        session.flush()
        session.refresh(invoice)
        return invoice
