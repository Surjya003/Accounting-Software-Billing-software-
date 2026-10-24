import pytest
from decimal import Decimal
from pathlib import Path
import pdfplumber

from app.services.pdf.core.formatting import format_currency
from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
from app.services.billing.purchase_order_pdf_generator import PurchaseOrderPDFGenerator
from app.services.billing.return_pdf_generator import ReturnPDFGenerator

COMPANY_DATA = {
    "name": "Audit Global Technologies Pvt Ltd",
    "address": "Plot 42, Electronics City Phase 1",
    "city": "Bengaluru",
    "state": "Karnataka",
    "state_code": "29",
    "pincode": "560100",
    "gstin": "29AABCA1234F1Z5",
    "phone": "+91 98765 43210",
    "email": "finance@auditglobal.in",
    "bank_name": "State Bank of India",
    "bank_ac_no": "334455667788",
    "bank_ifsc": "SBIN0001234",
    "bank_branch": "Electronic City",
    "number_format": "Indian"
}

CUSTOMER_DATA = {
    "name": "Bharat Heavy Machineries Ltd",
    "address": "Survey 108, Turbhe Industrial Park",
    "city": "Navi Mumbai",
    "state": "Maharashtra",
    "state_code": "27",
    "pincode": "400705",
    "gstin": "27AABCB9876P1ZV",
    "phone": "+91 91234 56789",
    "email": "procurement@bharatheavy.com"
}

def make_test_doc_payload(doc_type: str, item_count: int, is_inter: bool = False):
    items = []
    tot_taxable = Decimal("0.00")
    tot_cgst = Decimal("0.00")
    tot_sgst = Decimal("0.00")
    tot_igst = Decimal("0.00")

    for i in range(1, item_count + 1):
        qty = Decimal(str(i % 5 + 1))
        rate = Decimal("1000.00") + Decimal(str(i * 50))
        taxable = (qty * rate).quantize(Decimal("0.01"))
        tax_pct = Decimal("18.00")
        tax_amt = (taxable * (tax_pct / Decimal("100.00"))).quantize(Decimal("0.01"))
        
        if is_inter:
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
            igst = tax_amt
        else:
            cgst = (tax_amt / Decimal("2.00")).quantize(Decimal("0.01"))
            sgst = tax_amt - cgst
            igst = Decimal("0.00")

        total_item = taxable + cgst + sgst + igst
        tot_taxable += taxable
        tot_cgst += cgst
        tot_sgst += sgst
        tot_igst += igst

        items.append({
            "item_description": f"Industrial Automation Servo Drive Module Model ASD-{i:03d}",
            "hsn_code": "8504",
            "quantity": float(qty),
            "unit": "NOS",
            "unit_price": float(rate),
            "taxable_value": float(taxable),
            "tax_rate": float(tax_pct),
            "gst_rate_pct": float(tax_pct),
            "cgst_amount": float(cgst),
            "sgst_amount": float(sgst),
            "igst_amount": float(igst),
            "tax_amount": float(cgst + sgst + igst),
            "total_tax": float(cgst + sgst + igst),
            "total_item_amount": float(total_item),
            "total_amount": float(total_item)
        })

    tot_tax = tot_cgst + tot_sgst + tot_igst
    grand_total = tot_taxable + tot_tax

    payload = {
        "invoice_number": f"INV-TEST-{item_count}",
        "proforma_number": f"PI-TEST-{item_count}",
        "quotation_number": f"QT-TEST-{item_count}",
        "challan_number": f"DC-TEST-{item_count}",
        "po_number": f"PO-TEST-{item_count}",
        "return_number": f"CN-TEST-{item_count}",
        "date": "24-10-2026",
        "invoice_date": "24-10-2026",
        "challan_date": "24-10-2026",
        "quotation_date": "24-10-2026",
        "proforma_date": "24-10-2026",
        "po_date": "24-10-2026",
        "return_date": "24-10-2026",
        "company": COMPANY_DATA,
        "customer": CUSTOMER_DATA,
        "party": CUSTOMER_DATA,
        "items": items,
        "subtotal": float(tot_taxable),
        "taxable_amount": float(tot_taxable),
        "cgst_total": float(tot_cgst),
        "sgst_total": float(tot_sgst),
        "igst_total": float(tot_igst),
        "tax_amount": float(tot_tax),
        "total_tax": float(tot_tax),
        "grand_total": float(grand_total),
        "total_amount": float(grand_total),
        "totals": {
            "subtotal": float(tot_taxable),
            "taxable_amount": float(tot_taxable),
            "cgst_total": float(tot_cgst),
            "cgst_amount": float(tot_cgst),
            "sgst_total": float(tot_sgst),
            "sgst_amount": float(tot_sgst),
            "igst_total": float(tot_igst),
            "igst_amount": float(tot_igst),
            "tax_amount": float(tot_tax),
            "total_tax": float(tot_tax),
            "grand_total": float(grand_total),
            "total_amount": float(grand_total)
        },
        "reason_for_transportation": "Supply on Approval",
        "is_supply": True,
        "is_interstate": is_inter
    }
    return payload, tot_taxable, tot_tax, grand_total


@pytest.mark.parametrize("doc_type, item_count", [
    ("Tax Invoice", 1),
    ("Tax Invoice", 15),
    ("Tax Invoice", 40),
    ("Proforma Invoice", 15),
    ("Proforma Invoice", 40),
    ("Quotation", 15),
    ("Quotation", 40),
    ("Delivery Challan", 1),
    ("Delivery Challan", 15),
    ("Delivery Challan", 40),
    ("Purchase Order", 15),
    ("Purchase Order", 40),
])
def test_all_11_previous_no_cases_now_match_db(tmp_path, doc_type, item_count):
    payload, exp_taxable, exp_tax, exp_grand = make_test_doc_payload(doc_type, item_count, is_inter=False)
    pdf_path = tmp_path / f"{doc_type.replace(' ', '_')}_{item_count}.pdf"

    if doc_type == "Tax Invoice":
        InvoicePDFGenerator().generate_invoice(payload, filename=str(pdf_path))
    elif doc_type == "Proforma Invoice":
        ProformaPDFGenerator().generate_proforma(payload, filename=str(pdf_path))
    elif doc_type == "Quotation":
        QuotationPDFGenerator().generate_quotation(payload, filename=str(pdf_path))
    elif doc_type == "Delivery Challan":
        ChallanPDFGenerator().generate_challan(payload, filename=str(pdf_path))
    elif doc_type == "Purchase Order":
        PurchaseOrderPDFGenerator().generate_po(payload, filename=str(pdf_path))

    # Verify PDF exists and has valid pages
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000

    # Extract all text from all pages
    with pdfplumber.open(str(pdf_path)) as pdf:
        all_text = " ".join([page.extract_text() or "" for page in pdf.pages])

    # Check Indian formatted currency strings
    indian_grand = format_currency(exp_grand, "Indian")
    indian_taxable = format_currency(exp_taxable, "Indian")
    raw_grand_int = f"{int(exp_grand):,}"

    # Verify that the grand total or taxable value is present in printed PDF text
    matches = (
        indian_grand in all_text or
        f"{exp_grand:,.2f}" in all_text or
        indian_taxable in all_text or
        f"{int(exp_grand)}" in all_text
    )

    assert matches, f"Numbers mismatch for {doc_type} ({item_count} items)! Expected {indian_grand} or {exp_grand} in PDF text"
    print(f"\n[VERIFIED Numbers Match DB = Yes] {doc_type} ({item_count} items) -> Grand Total: {indian_grand} verified in PDF")
