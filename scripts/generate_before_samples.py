"""
Generate baseline 'before' samples of the four target documents:
Tax Invoice, Proforma Invoice, Quotation, Delivery Challan.
Saves PDF and rasterized PNG images into docs/pdf_samples/before/.
"""
import sys
from pathlib import Path
from decimal import Decimal
import pypdfium2

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
from app.services.billing.challan_pdf_generator import ChallanPDFGenerator

OUT_DIR = ROOT_DIR / "docs" / "pdf_samples" / "before"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COMPANY = {
    "name": "Binapani Automation & Controls",
    "trade_name": "Binapani Controls",
    "address": "12/4 Industrial Estate, Phase II, Taratala Road",
    "city": "Kolkata",
    "state": "West Bengal",
    "state_code": "19",
    "pincode": "700088",
    "gstin": "19AABCB1234F1Z5",
    "pan": "AABCB1234F",
    "phone": "+91 98300 12345",
    "email": "sales@binapanicontrols.com",
    "bank_name": "State Bank of India",
    "bank_account_no": "34981029384",
    "bank_ifsc": "SBIN0001234",
    "bank_branch": "Taratala Commercial Branch",
    "number_format": "Indian"
}

CUSTOMER = {
    "name": "Tata Advanced Systems Ltd",
    "address": "Survey No 42, Hitech Defence Park, Adibatla",
    "city": "Hyderabad",
    "state": "Telangana",
    "state_code": "36",
    "gstin": "36AAACT2841M1ZP",
    "pincode": "501510"
}

ITEMS_SAMPLE = [
    {
        "item_description": "Variable Frequency Drive 15kW 415V Heavy Duty IP54",
        "hsn_code": "85044090",
        "quantity": 2.0,
        "unit": "PCS",
        "unit_price": 42500.0,
        "discount_pct": 5.0,
        "tax_rate": 18.0,
        "gst_rate_pct": 18.0,
        "taxable_value": 80750.0,
        "igst_amount": 14535.0,
        "total_item_amount": 95285.0
    },
    {
        "item_description": "Programmable Logic Controller CPU 24VDC 16DI/16DO Transistor",
        "hsn_code": "85371090",
        "quantity": 3.0,
        "unit": "PCS",
        "unit_price": 28000.0,
        "discount_pct": 0.0,
        "tax_rate": 18.0,
        "gst_rate_pct": 18.0,
        "taxable_value": 84000.0,
        "igst_amount": 15120.0,
        "total_item_amount": 99120.0
    },
    {
        "item_description": "Shielded Twisted Pair Communication Cable Belden 9841",
        "hsn_code": "85444990",
        "quantity": 100.0,
        "unit": "MTR",
        "unit_price": 125.0,
        "discount_pct": 10.0,
        "tax_rate": 18.0,
        "gst_rate_pct": 18.0,
        "taxable_value": 11250.0,
        "igst_amount": 2025.0,
        "total_item_amount": 13275.0
    }
]

def rasterize_pdf(pdf_path: Path, dpi: int = 80):
    doc = pypdfium2.PdfDocument(str(pdf_path))
    png_paths = []
    for i, page in enumerate(doc):
        scale = dpi / 72.0
        pil_img = page.render(scale=scale).to_pil()
        out_png = pdf_path.parent / f"{pdf_path.stem}_page_{i+1}.png" if len(doc) > 1 else pdf_path.parent / f"{pdf_path.stem}.png"
        pil_img.save(out_png)
        png_paths.append(out_png)
    return png_paths

def generate_samples():
    print("Generating 'before' samples...")
    
    # 1. Tax Invoice
    tot_taxable = sum(it["taxable_value"] for it in ITEMS_SAMPLE)
    tot_igst = sum(it["igst_amount"] for it in ITEMS_SAMPLE)
    tot_amt = sum(it["total_item_amount"] for it in ITEMS_SAMPLE)
    
    inv_data = {
        "invoice_number": "INV/2026-27/0042",
        "date": "24-10-2026",
        "company": COMPANY,
        "customer": CUSTOMER,
        "items": ITEMS_SAMPLE,
        "tax_mode": "inter_state",
        "totals": {
            "subtotal": tot_taxable, "taxable_amount": tot_taxable,
            "cgst_amount": 0.0, "cgst_total": 0.0,
            "sgst_amount": 0.0, "sgst_total": 0.0,
            "igst_amount": tot_igst, "igst_total": tot_igst,
            "tax_amount": tot_igst, "total_tax": tot_igst,
            "grand_total": tot_amt, "total_amount": tot_amt,
            "round_off": 0.0
        }
    }
    p_inv = OUT_DIR / "before_tax_invoice_3items.pdf"
    InvoicePDFGenerator().generate_invoice(inv_data, filename=str(p_inv))
    rasterize_pdf(p_inv)
    print("Saved:", p_inv)

    # 2. Proforma Invoice
    pf_data = dict(inv_data)
    pf_data["invoice_number"] = "PF/2026-27/0018"
    pf_data["proforma_number"] = "PF/2026-27/0018"
    pf_data["valid_until"] = "24-11-2026"
    p_pf = OUT_DIR / "before_proforma_3items.pdf"
    ProformaPDFGenerator().generate_proforma(pf_data, filename=str(p_pf))
    rasterize_pdf(p_pf)
    print("Saved:", p_pf)

    # 3. Quotation
    qt_data = dict(inv_data)
    qt_data["invoice_number"] = "QT/2026-27/0089"
    qt_data["quotation_number"] = "QT/2026-27/0089"
    qt_data["valid_until"] = "24-11-2026"
    qt_data["price_basis"] = "Ex-Works Kolkata / GST 18% extra"
    p_qt = OUT_DIR / "before_quotation_3items.pdf"
    QuotationPDFGenerator().generate_quotation(qt_data, filename=str(p_qt))
    rasterize_pdf(p_qt)
    print("Saved:", p_qt)

    # 4. Delivery Challan
    ch_data = dict(inv_data)
    ch_data["invoice_number"] = "DC/2026-27/0025"
    ch_data["challan_number"] = "DC/2026-27/0025"
    ch_data["reason_for_transportation"] = "Delivery (invoice to follow)"
    p_ch = OUT_DIR / "before_delivery_challan_3items.pdf"
    ChallanPDFGenerator().generate_challan(ch_data, filename=str(p_ch))
    rasterize_pdf(p_ch)
    print("Saved:", p_ch)

if __name__ == "__main__":
    generate_samples()
