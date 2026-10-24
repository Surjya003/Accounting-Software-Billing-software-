"""
Tax Invoice & Quotation PDF Generator
Routes to dedicated template modules in app.services.pdf.templates.
"""
import os
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.pdf.templates.tax_invoice import render_tax_invoice_pdf
from app.services.pdf.templates.quotation import render_quotation_pdf


class InvoicePDFGenerator:
    """
    Professional Tax Invoice PDF Generator.
    Delegates to dedicated tax_invoice.py template matching reference 12-signed.pdf.
    """

    def __init__(self):
        pass

    def generate_invoice(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Tax Invoice PDF matching full-page layout."""
        if not filename:
            from app.config import EXPORTS_DIR
            safe_num = str(data.get("invoice_number", "DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"invoice_{safe_num}.pdf")

        filepath = str(filename)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        doc_title = str(data.get("document_title", "")).upper()
        if "QUOTATION" in doc_title:
            return render_quotation_pdf(data, filepath)

        return render_tax_invoice_pdf(data, filepath)

    def generate_quotation(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a Quotation / Estimate PDF."""
        if not filename:
            from app.config import EXPORTS_DIR
            q_num = str(data.get("invoice_number", "DRAFT")).replace("/", "-").replace("\\", "-")
            filename = os.path.join(str(EXPORTS_DIR), f"quotation_{q_num}.pdf")

        return render_quotation_pdf(data, str(filename))


def generate_invoice_pdf(inv_data: Dict[str, Any], comp_data: Optional[Dict[str, Any]] = None, output_path: Optional[str] = None) -> str:
    """
    Generate an invoice PDF from invoice dictionary and optional company profile dictionary.
    Called by QA tests and application billing services.
    """
    generator = InvoicePDFGenerator()

    if comp_data is None:
        try:
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                comp_data = comp.to_dict() if comp else {}
        except Exception:
            comp_data = {}

    company_info = {
        "name": comp_data.get("name", ""),
        "address": comp_data.get("address", ""),
        "city": comp_data.get("city", ""),
        "state": comp_data.get("state", ""),
        "state_code": comp_data.get("state_code", ""),
        "pincode": comp_data.get("pincode", ""),
        "gstin": comp_data.get("gstin", ""),
        "pan": comp_data.get("pan", ""),
        "phone": comp_data.get("phone", ""),
        "email": comp_data.get("email", ""),
        "bank_name": comp_data.get("bank_name", ""),
        "bank_account_no": comp_data.get("bank_account_no", "") or comp_data.get("account_no", ""),
        "bank_ifsc": comp_data.get("bank_ifsc", "") or comp_data.get("ifsc", ""),
        "bank_branch": comp_data.get("bank_branch", ""),
        "terms_conditions": comp_data.get("terms_conditions", ""),
        "declaration": comp_data.get("declaration", ""),
        "signature_path": comp_data.get("signature_path"),
        "seal_path": comp_data.get("seal_path"),
        "number_format": comp_data.get("number_format", "Indian"),
        "print_hsn_summary": comp_data.get("print_hsn_summary", True),
        "print_all_copies": comp_data.get("print_all_copies", False),
    }

    is_interstate = inv_data.get("is_interstate", False)
    tax_mode_str = "inter_state" if is_interstate else "intra_state"

    inv_date = inv_data.get("invoice_date")
    date_str = inv_date.strftime("%d-%m-%Y") if hasattr(inv_date, "strftime") else str(inv_date or "")

    pdf_data = {
        "invoice_number": inv_data.get("invoice_number", "DRAFT"),
        "date": date_str,
        "tax_mode": tax_mode_str,
        "po_number": inv_data.get("po_number", ""),
        "pi_number": inv_data.get("pi_number", ""),
        "company": company_info,
        "customer": {
            "name": inv_data.get("party_name", ""),
            "address": inv_data.get("party_address", ""),
            "gstin": inv_data.get("party_gstin", ""),
            "state": inv_data.get("party_state", ""),
            "state_code": inv_data.get("party_state_code", ""),
            "phone": inv_data.get("party_phone", "")
        },
        "shipping": {
            "name": inv_data.get("shipping_name") or inv_data.get("party_name", ""),
            "address": inv_data.get("shipping_address") or inv_data.get("party_address", ""),
            "gstin": inv_data.get("shipping_gstin") or inv_data.get("party_gstin", ""),
            "state": inv_data.get("shipping_state") or inv_data.get("party_state", ""),
            "state_code": inv_data.get("shipping_state_code") or inv_data.get("party_state_code", ""),
            "pincode": inv_data.get("shipping_pincode", "")
        },
        "logistics": {
            "dispatch_doc_no": inv_data.get("dispatch_doc_no") or inv_data.get("lr_no", ""),
            "waybill_no": inv_data.get("eway_bill_no", ""),
            "dispatched_through": inv_data.get("dispatched_through") or inv_data.get("transporter_name", ""),
            "destination": inv_data.get("destination", ""),
            "buyer_order_no": inv_data.get("buyers_order_no") or inv_data.get("po_number", ""),
            "buyer_order_date": inv_data.get("buyers_order_date"),
            "payment_terms": inv_data.get("mode_terms_of_payment", ""),
            "terms_delivery": inv_data.get("terms_of_delivery", ""),
            "delivery_note": inv_data.get("delivery_note", ""),
            "reference_no_date": inv_data.get("reference_no_date", ""),
            "other_references": inv_data.get("other_references", ""),
        },
        "delivery_note": inv_data.get("delivery_note", ""),
        "mode_terms_of_payment": inv_data.get("mode_terms_of_payment", ""),
        "reference_no_date": inv_data.get("reference_no_date", ""),
        "other_references": inv_data.get("other_references", ""),
        "buyers_order_no": inv_data.get("buyers_order_no") or inv_data.get("po_number", ""),
        "buyers_order_date": inv_data.get("buyers_order_date"),
        "dispatch_doc_no": inv_data.get("dispatch_doc_no") or inv_data.get("lr_no", ""),
        "eway_bill_no": inv_data.get("eway_bill_no", ""),
        "dispatched_through": inv_data.get("dispatched_through") or inv_data.get("transporter_name", ""),
        "destination": inv_data.get("destination", ""),
        "terms_of_delivery": inv_data.get("terms_of_delivery", ""),
        "place_of_supply": inv_data.get("place_of_supply", ""),
        "reverse_charge": inv_data.get("reverse_charge", False),
        "copy_label": inv_data.get("copy_label", "ORIGINAL FOR RECIPIENT"),
        "items": [],
        "totals": {
            "taxable_amount": float(inv_data.get("subtotal", 0)),
            "cgst_amount": float(inv_data.get("cgst_total", 0)),
            "sgst_amount": float(inv_data.get("sgst_total", 0)),
            "igst_amount": float(inv_data.get("igst_total", 0)),
            "grand_total": float(inv_data.get("total_amount", 0)),
        }
    }

    for item in inv_data.get("items", []):
        qty = float(item.get("quantity", 0))
        unit_price = float(item.get("unit_price", 0))
        gst_rate = float(item.get("gst_rate_pct", 0) or item.get("tax_rate", 0))
        cgst_amt = float(item.get("cgst_amount", 0))
        sgst_amt = float(item.get("sgst_amount", 0))
        igst_amt = float(item.get("igst_amount", 0))
        item_tax_amount = cgst_amt + sgst_amt + igst_amt

        pdf_data["items"].append({
            "item_description": item.get("item_description", "") or item.get("product_name", ""),
            "hsn_code": item.get("hsn_code", ""),
            "quantity": qty,
            "unit": item.get("unit", "PCS"),
            "unit_price": unit_price,
            "tax_rate": gst_rate,
            "total_item_amount": float(item.get("total_amount") or ((qty * unit_price) + item_tax_amount)),
        })

    return generator.generate_invoice(pdf_data, filename=output_path)
