"""
Delivery Challan Service
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_

from app.database.connection import get_session
from app.database.models import DeliveryChallan, ChallanItem, Party, CompanyProfile
from app.config import get_financial_year
from app.services.billing.gst_engine import GSTEngine, TransactionType


def generate_challan_number(session, ch_date: date) -> str:
    fy = get_financial_year(ch_date)
    pattern = f"DC/{fy}/%"
    last = session.query(DeliveryChallan).filter(
        DeliveryChallan.challan_number.like(pattern)
    ).order_by(desc(DeliveryChallan.id)).first()
    seq = 1
    if last and last.challan_number:
        try: seq = int(last.challan_number.split("/")[-1]) + 1
        except ValueError: pass
    return f"DC/{fy}/{seq:04d}"


def calculate_challan_totals(items_data: List[Dict], company_state_code: str, party_state_code: str, tax_mode: int = 0):
    """Calculate GST for all items and return totals + processed items for Delivery Challan."""
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
        rate = Decimal(str(item.get("unit_price", "0")))
        disc = Decimal(str(item.get("discount_pct", "0")))
        from app.services.validation_helpers import normalize_tax_rate
        gst = normalize_tax_rate(item)

        result = GSTEngine.calculate_line_item(qty, rate, disc, gst, t_type)

        item_copy = dict(item)
        item_copy.update({
            "taxable_value": result["taxable_value"],
            "unit_price": rate,
            "quantity": qty,
            "discount_pct": disc,
            "tax_rate": gst,
            "gst_rate_pct": gst,
            "cgst_amount": result["cgst_amt"],
            "sgst_amount": result["sgst_amt"],
            "igst_amount": result["igst_amt"],
            "tax_amount": result["cgst_amt"] + result["sgst_amt"] + result["igst_amt"],
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


def create_challan(data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> DeliveryChallan:
    if not items_data:
        raise ValueError("Challan must have at least one item.")
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        party = session.query(Party).filter(Party.id == data.get("party_id")).first()
        if not party:
            raise ValueError("Party not found.")

        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company and company.state_code else "27"
        if not company_sc and company and company.gstin and len(company.gstin) >= 2 and company.gstin[:2].isdigit():
            company_sc = company.gstin[:2]

        party_sc = party.state_code if party and party.state_code else ""
        if not party_sc and party and party.gstin and len(party.gstin) >= 2 and party.gstin[:2].isdigit():
            party_sc = party.gstin[:2]
        if not party_sc:
            party_sc = company_sc

        ch_date = data.get("challan_date", date.today())
        ch_num = data.get("challan_number") or generate_challan_number(session, ch_date)

        tax_mode = data.get("tax_mode", 0)
        subtotal, cgst_total, sgst_total, igst_total, tax_total, grand_total, processed_items, is_inter = calculate_challan_totals(
            items_data, company_sc, party_sc, tax_mode
        )

        challan = DeliveryChallan(
            challan_number=ch_num,
            challan_date=ch_date,
            party_id=party.id,
            subtotal=subtotal,
            cgst_total=cgst_total,
            sgst_total=sgst_total,
            igst_total=igst_total,
            tax_amount=tax_total,
            total_amount=grand_total,
            status=data.get("status", "sent"),
            is_interstate=is_inter,
            transport_details=data.get("transport_details", ""),
            notes=data.get("notes", ""),
            reason_for_transportation=data.get("reason_for_transportation", "Delivery (invoice to follow)"),
            dispatch_datetime=data.get("dispatch_datetime"),
            transporter_name=data.get("transporter_name"),
            transporter_id=data.get("transporter_id"),
            vehicle_no=str(data["vehicle_no"]).strip().upper() if data.get("vehicle_no") else None,
            driver_name=data.get("driver_name"),
            driver_mobile=data.get("driver_mobile"),
            lr_no=data.get("lr_no"),
            lr_date=data.get("lr_date"),
            eway_bill_no=data.get("eway_bill_no"),
            from_place=data.get("from_place"),
            to_place=data.get("to_place"),
            distance_km=Decimal(str(data["distance_km"])) if data.get("distance_km") is not None and str(data["distance_km"]).strip() != "" else None,
            packages=int(data["packages"]) if data.get("packages") is not None and str(data["packages"]).isdigit() else None,
            weight=Decimal(str(data["weight"])) if data.get("weight") is not None and str(data["weight"]).strip() != "" else None,
            show_value=bool(data.get("show_value", False)),
        )
        session.add(challan)
        session.flush()

        for it in processed_items:
            session.add(ChallanItem(
                challan_id=challan.id,
                product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                qty_ordered=Decimal(str(it["qty_ordered"])) if it.get("qty_ordered") is not None and str(it["qty_ordered"]).strip() != "" else None,
                remarks=it.get("remarks", ""),
                tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                cgst_amount=it["cgst_amount"],
                sgst_amount=it["sgst_amount"],
                igst_amount=it["igst_amount"],
                tax_amount=it["tax_amount"],
                total_amount=it["total_amount"],
            ))

        session.flush()
        session.refresh(challan)
        return challan


def get_all_challans(from_date=None, to_date=None, party_id=None, status=None, search=None, limit=200):
    with get_session() as session:
        q = session.query(DeliveryChallan).join(Party, DeliveryChallan.party_id == Party.id)
        if from_date: q = q.filter(DeliveryChallan.challan_date >= from_date)
        if to_date: q = q.filter(DeliveryChallan.challan_date <= to_date)
        if party_id: q = q.filter(DeliveryChallan.party_id == party_id)
        if status and status != "All": q = q.filter(DeliveryChallan.status == status)
        if search:
            p = f"%{search.strip()}%"
            q = q.filter(or_(DeliveryChallan.challan_number.ilike(p), Party.name.ilike(p)))
        return [c.to_dict() for c in q.order_by(desc(DeliveryChallan.challan_date), desc(DeliveryChallan.id)).limit(limit).all()]


def get_challan_by_id(challan_id: int):
    with get_session() as session:
        ch = session.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id).first()
        if not ch: return None
        d = ch.to_dict()
        items_list = []
        for it in ch.items:
            it_dict = it.to_dict()
            it_dict["gst_rate_pct"] = it_dict.get("tax_rate", 0)
            items_list.append(it_dict)
        d["items"] = items_list
        d["party_gstin"] = ch.party.gstin if ch.party else ""
        d["party_address"] = ch.party.address if ch.party else ""
        d["party_state"] = ch.party.state if ch.party else ""
        d["party_state_code"] = ch.party.state_code if ch.party else ""
        d["party_phone"] = ch.party.phone if ch.party else ""
        d["party_name"] = ch.party.name if ch.party else ""
        d["tax_mode"] = 2 if ch.is_interstate else 1
        return d


def update_challan(challan_id: int, ch_data: Dict, items_data: List[Dict] = None):
    """Update an existing delivery challan."""
    with get_session() as session:
        ch = session.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id).first()
        if not ch:
            return None

        party = session.query(Party).filter(Party.id == ch_data.get("party_id", ch.party_id)).first()
        company = session.query(CompanyProfile).first()
        company_sc = company.state_code if company and company.state_code else "27"
        if not company_sc and company and company.gstin and len(company.gstin) >= 2 and company.gstin[:2].isdigit():
            company_sc = company.gstin[:2]

        party_sc = party.state_code if party and party.state_code else ""
        if not party_sc and party and party.gstin and len(party.gstin) >= 2 and party.gstin[:2].isdigit():
            party_sc = party.gstin[:2]
        if not party_sc:
            party_sc = company_sc

        # Determine tax mode
        tax_mode = ch_data.get("tax_mode", 0)

        if items_data:
            subtotal, cgst_total, sgst_total, igst_total, tax_total, grand_total, processed_items, is_inter = calculate_challan_totals(
                items_data, company_sc, party_sc, tax_mode
            )

            ch.subtotal = subtotal
            ch.cgst_total = cgst_total
            ch.sgst_total = sgst_total
            ch.igst_total = igst_total
            ch.tax_amount = tax_total
            ch.total_amount = grand_total
            ch.is_interstate = is_inter

            # Replace items
            session.query(ChallanItem).filter(ChallanItem.challan_id == challan_id).delete()
            for it in processed_items:
                session.add(ChallanItem(
                    challan_id=challan_id,
                    product_id=it.get("product_id"),
                    item_description=it.get("item_description", ""),
                    hsn_code=it.get("hsn_code", ""),
                    quantity=Decimal(str(it.get("quantity", "1"))),
                    unit=it.get("unit", "PCS"),
                    unit_price=Decimal(str(it.get("unit_price", "0"))),
                    tax_rate=Decimal(str(it.get("tax_rate", "0"))),
                    cgst_amount=it["cgst_amount"],
                    sgst_amount=it["sgst_amount"],
                    igst_amount=it["igst_amount"],
                    tax_amount=it["tax_amount"],
                    total_amount=it["total_amount"],
                ))
        elif "tax_mode" in ch_data:
            if tax_mode == 1:
                ch.is_interstate = False
            elif tax_mode == 2:
                ch.is_interstate = True
            else:
                ch.is_interstate = (party_sc.strip() != company_sc.strip()) if party_sc and company_sc else False

        if "vehicle_no" in ch_data and ch_data["vehicle_no"]:
            ch_data["vehicle_no"] = str(ch_data["vehicle_no"]).strip().upper()

        for key in (
            "party_id", "challan_date", "status", "transport_details", "notes",
            "reason_for_transportation", "dispatch_datetime", "transporter_name",
            "transporter_id", "vehicle_no", "driver_name", "driver_mobile",
            "lr_no", "lr_date", "eway_bill_no", "from_place", "to_place",
            "distance_km", "packages", "weight", "show_value",
        ):
            if key in ch_data and hasattr(ch, key):
                setattr(ch, key, ch_data[key])

        session.flush()
        session.refresh(ch)
        return ch


def delete_challan(challan_id: int) -> bool:
    with get_session() as session:
        ch = session.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id).first()
        if not ch: return False
        session.delete(ch); return True


def get_challan_count() -> int:
    with get_session() as session:
        return session.query(DeliveryChallan).count()


def convert_to_invoice(challan_id: int):
    """Convert a delivery challan into an official Tax Invoice and update stock and ledger."""
    with get_session() as session:
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except Exception:
            pass
        ch = session.query(DeliveryChallan).filter(DeliveryChallan.id == challan_id).first()
        if not ch:
            return None
        if ch.status == "converted":
            raise ValueError(f"Delivery Challan #{ch.challan_number} has already been converted.")
        if ch.status in ("cancelled", "rejected"):
            raise ValueError(f"Cannot convert {ch.status} Delivery Challan #{ch.challan_number}.")

        # Atomic check-and-set to block concurrent double-conversion
        rowcount = session.query(DeliveryChallan).filter(
            DeliveryChallan.id == challan_id,
            DeliveryChallan.status.notin_(["converted", "cancelled", "rejected"])
        ).update({"status": "converted"}, synchronize_session=False)
        if rowcount == 0:
            raise ValueError(f"Delivery Challan #{ch.challan_number} has already been converted.")

        ch_items = session.query(ChallanItem).filter(ChallanItem.challan_id == challan_id).all()
        if not ch_items:
            raise ValueError("Delivery Challan has no items to convert.")

        party = session.query(Party).filter(Party.id == ch.party_id).first()
        company = session.query(CompanyProfile).first()
        c_sc = company.state_code if company and company.state_code else "27"
        p_sc = party.state_code if party and party.state_code else c_sc
        allow_neg = getattr(company, "allow_negative_stock", False) if company else False

        from app.services.billing.invoice_service import generate_invoice_number, calculate_invoice_totals
        from app.database.models import Invoice, InvoiceItem, Product, Voucher
        inv_date = date.today()
        inv_number = generate_invoice_number(session, inv_date)

        items_data = []
        for it in ch_items:
            items_data.append({
                "product_id": it.product_id,
                "item_description": it.item_description,
                "hsn_code": it.hsn_code,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": float(it.unit_price),
                "discount_pct": 0.0,
                "gst_rate_pct": float(it.tax_rate or 0),
            })

        subtotal, cgst, sgst, igst, tax, total, processed, is_inter = calculate_invoice_totals(
            items_data, c_sc, p_sc, tax_mode=0
        )

        invoice = Invoice(
            invoice_number=inv_number,
            invoice_date=inv_date,
            party_id=ch.party_id,
            subtotal=subtotal,
            cgst_total=cgst,
            sgst_total=sgst,
            igst_total=igst,
            tax_amount=tax,
            total_amount=total,
            status="final",
            notes=f"Converted from Delivery Challan #{ch.challan_number}",
            is_interstate=is_inter,
            delivery_note=ch.challan_number,
            transporter_name=getattr(ch, "transporter_name", "") or ch.transport_details or "",
            dispatched_through=getattr(ch, "transporter_name", "") or ch.transport_details or "",
            vehicle_no=getattr(ch, "vehicle_no", "") or "",
            lr_no=getattr(ch, "lr_no", "") or "",
            lr_date=getattr(ch, "lr_date", None),
            eway_bill_no=getattr(ch, "eway_bill_no", "") or "",
            destination=getattr(ch, "to_place", "") or "",
            dispatch_doc_no=getattr(ch, "lr_no", "") or ch.challan_number,
        )
        session.add(invoice)
        session.flush()

        for it in processed:
            session.add(InvoiceItem(
                invoice_id=invoice.id,
                product_id=it.get("product_id"),
                item_description=it.get("item_description", ""),
                hsn_code=it.get("hsn_code", ""),
                quantity=Decimal(str(it.get("quantity", "1"))),
                unit=it.get("unit", "PCS"),
                unit_price=Decimal(str(it.get("unit_price", "0"))),
                discount_pct=Decimal("0.00"),
                taxable_value=it.get("taxable_value", Decimal("0")),
                gst_rate_pct=Decimal(str(it.get("gst_rate_pct", "0"))),
                cgst_amount=it.get("cgst_amount", Decimal("0")),
                sgst_amount=it.get("sgst_amount", Decimal("0")),
                igst_amount=it.get("igst_amount", Decimal("0")),
                total_amount=it.get("total_amount", Decimal("0")),
            ))
            if it.get("product_id"):
                prod = session.query(Product).filter(Product.id == it["product_id"]).first()
                if prod:
                    qty = Decimal(str(it.get("quantity", "0")))
                    if not allow_neg and qty > prod.stock_quantity:
                        raise ValueError(
                            f"Insufficient stock for product '{prod.name}'. Available: {prod.stock_quantity}, Requested: {qty}."
                        )
                    prod.stock_quantity -= qty

        from app.services.billing.invoice_service import post_sales_voucher
        post_sales_voucher(
            invoice,
            session=session,
            reference_no=ch.challan_number,
            narration=f"Tax Invoice from Delivery Challan #{ch.challan_number}"
        )
        session.flush()
        session.refresh(invoice)
        return invoice
