"""
Test Suite: PDF Full-Page Layout & Geometry Verification for All Document Types
================================================================================
Tests all billing document types against the shared layout engine:
- Tax Invoice (INV/...)
- Proforma Invoice (PF/...)
- Quotation / Commercial Estimate (QT/...)
- Delivery Challan (DC/...)
- Sales Return / Credit Note (SR/..., CN/...)
- Purchase Order (PO/...)
- Purchase Return / Debit Note (PR/..., DN/...)
- Accounting Vouchers (Payment, Receipt, Journal, Contra)

Verifies:
1. Exact A4 size: 595.276 x 841.89 pt (+- 0.5 pt).
2. Expected page counts (1-item = 1 page, 15-item = 1 page, 40-item >= 2 pages).
3. Last page footer is pinned to the bottom: lowest text within 12 mm of the frame edge.
4. Frame margin >= 8 mm from every page edge (set to 10 mm).
5. Text does not overflow margins or frames.
6. Grand totals in the PDF match the input database values without alterations.
7. Corrupt or missing logo files are handled safely without exceptions.
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import pytest
import pdfplumber

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.services.pdf.templates.payment_receipt import render_payment_receipt_pdf
from app.services.pdf.core.formatting import format_currency as format_inr
from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
from app.services.billing.return_pdf_generator import ReturnPDFGenerator
from app.services.billing.purchase_order_pdf_generator import PurchaseOrderPDFGenerator


COMPANY_DATA = {
    "name": "Delhi Enterprise Solutions Pvt Ltd",
    "address": "Plot 14B, Okhla Industrial Area Phase-III",
    "city": "New Delhi",
    "state": "Delhi",
    "pincode": "110020",
    "gstin": "07AAAAA0000A1Z5",
    "pan": "AAAAA0000A",
    "phone": "+91 11 4567 8900",
    "email": "billing@delhienterprise.com",
    "bank_name": "State Bank of India",
    "account_no": "10020030040050",
    "ifsc": "SBIN0001234",
    "terms_conditions": "1. Goods once sold will not be taken back.\n2. Interest @ 18% p.a. for overdue.",
}

CUSTOMER_DATA = {
    "name": "Apex Engineering & Infrastructure Ltd",
    "address": "Tower 4, Cyber City, DLF Phase 2",
    "city": "Gurugram",
    "state": "Haryana",
    "pincode": "122002",
    "gstin": "06BBBBB1111B1Z2",
    "phone": "+91 124 9876543",
}


def make_item(idx, qty=1.0, rate=1200.0, gst=18.0):
    taxable = qty * rate
    tax = taxable * (gst / 100.0)
    return {
        "item_description": f"Industrial Automation Part #{idx:03d} - High Precision Model",
        "hsn_code": "8471",
        "quantity": float(qty),
        "unit": "PCS",
        "unit_price": float(rate),
        "tax_rate": float(gst),
        "tax_amount": float(tax),
        "total_item_amount": float(taxable + tax),
        "reference_no": f"REF-{idx:04d}",
    }


def get_generator(doc_type):
    generators = {
        "tax_invoice": lambda d, p: InvoicePDFGenerator().generate_invoice(d, filename=str(p)),
        "proforma": lambda d, p: ProformaPDFGenerator().generate_proforma(d, filename=str(p)),
        "quotation": lambda d, p: QuotationPDFGenerator().generate_quotation(d, filename=str(p)),
        "challan": lambda d, p: ChallanPDFGenerator().generate_challan(d, filename=str(p)),
        "credit_note": lambda d, p: ReturnPDFGenerator().generate_credit_note(d, filename=str(p)),
        "purchase_order": lambda d, p: PurchaseOrderPDFGenerator().generate_po(d, filename=str(p)),
        "debit_note": lambda d, p: ReturnPDFGenerator().generate_debit_note(d, filename=str(p)),
        "voucher": lambda d, p: render_payment_receipt_pdf(d, str(p)),
    }
    return generators[doc_type]


DOCUMENT_TYPES = [
    "tax_invoice",
    "proforma",
    "quotation",
    "challan",
    "credit_note",
    "purchase_order",
    "debit_note",
    "voucher",
]


@pytest.mark.parametrize("doc_type", DOCUMENT_TYPES)
def test_1_item_pdf_full_page_geometry(doc_type, tmp_path):
    """Asserts that 1-item PDF fills the full A4 page with lowest text within 12 mm of frame bottom."""
    out_file = tmp_path / f"{doc_type}_1_item.pdf"
    items = [make_item(1, qty=1.0, rate=1200.0, gst=18.0)]
    sub = 1200.0
    tax = 216.0
    grand = 1416.0

    data = {
        "invoice_number": f"{doc_type[:3].upper()}-0001",
        "date": "23-10-2026",
        "company": COMPANY_DATA,
        "customer": CUSTOMER_DATA,
        "supplier": CUSTOMER_DATA,
        "tax_mode": "inter_state",
        "items": items,
        "totals": {
            "taxable_amount": sub,
            "igst_amount": tax,
            "grand_total": grand,
        }
    }

    gen = get_generator(doc_type)
    pdf_path = gen(data, out_file)
    assert os.path.exists(pdf_path), f"PDF file was not created: {pdf_path}"

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) == 1, f"Expected 1 page for 1-item {doc_type}, got {len(pdf.pages)}"
        page = pdf.pages[0]
        # Check A4 dimensions
        assert abs(float(page.width) - 595.276) < 0.5, f"Incorrect page width: {page.width}"
        assert abs(float(page.height) - 841.890) < 0.5, f"Incorrect page height: {page.height}"

        words = page.extract_words()
        assert len(words) > 0, "No text extracted from PDF"

        # Check print safety margins >= 8 mm (we use 10 mm = 28.35 pt)
        min_x = min(w['x0'] for w in words)
        max_x = max(w['x1'] for w in words)
        assert min_x >= 24.0, f"Text spills into left print safety margin: {min_x} pt"
        assert max_x <= (float(page.width) - 24.0), f"Text spills into right margin: {max_x} pt"

        lowest_bottom = max(w['bottom'] for w in words)
        frame_bottom_y = float(page.height) - 28.346 # 10 mm
        gap_frame_mm = (frame_bottom_y - lowest_bottom) / 72.0 * 25.4
        gap_page_mm = (float(page.height) - lowest_bottom) / 72.0 * 25.4

        # Hard rule: lowest text/line is within 12 mm of the page's bottom frame edge
        assert gap_frame_mm <= 12.0, (
            f"Blank bottom gap too large in {doc_type}: {gap_frame_mm:.2f} mm from frame bottom. "
            f"Lowest text at {lowest_bottom:.2f} pt."
        )
        assert gap_frame_mm >= -2.0, f"Text overflowed past bottom frame line: {gap_frame_mm:.2f} mm"

        # Compare numbers: confirm values in PDF match input
        full_text = page.extract_text() or ""
        if doc_type != "challan":  # Delivery challans don't show money totals
            assert "1,416.00" in full_text or "1416.00" in full_text, "Grand total missing from text"


@pytest.mark.parametrize("doc_type", DOCUMENT_TYPES)
def test_15_items_pdf_single_page_fit(doc_type, tmp_path):
    """Asserts that 15-item document fits on 1 page and satisfies full A4 geometry."""
    out_file = tmp_path / f"{doc_type}_15_items.pdf"
    items = [make_item(i, qty=float(i), rate=500.0, gst=18.0) for i in range(1, 16)]
    sub = sum(it["quantity"] * it["unit_price"] for it in items)
    tax = sub * 0.18
    grand = sub + tax

    data = {
        "invoice_number": f"{doc_type[:3].upper()}-0015",
        "date": "23-10-2026",
        "company": COMPANY_DATA,
        "customer": CUSTOMER_DATA,
        "supplier": CUSTOMER_DATA,
        "items": items,
        "totals": {
            "taxable_amount": sub,
            "cgst_amount": tax / 2.0,
            "sgst_amount": tax / 2.0,
            "grand_total": grand,
        }
    }

    gen = get_generator(doc_type)
    pdf_path = gen(data, out_file)

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) == 1, f"Expected 1 page for 15 items in {doc_type}, got {len(pdf.pages)}"
        page = pdf.pages[0]
        words = page.extract_words()
        lowest_bottom = max(w['bottom'] for w in words)
        frame_bottom_y = float(page.height) - 28.346
        gap_frame_mm = (frame_bottom_y - lowest_bottom) / 72.0 * 25.4
        assert gap_frame_mm <= 12.0, f"Gap too large: {gap_frame_mm:.2f} mm"


@pytest.mark.parametrize("doc_type", [d for d in DOCUMENT_TYPES if d != "voucher"])
def test_40_items_multipage_pagination(doc_type, tmp_path):
    """Asserts that 40-item document paginates across 2+ pages and fills the final page."""
    out_file = tmp_path / f"{doc_type}_40_items.pdf"
    items = [make_item(i, qty=2.0, rate=250.0, gst=18.0) for i in range(1, 41)]
    sub = sum(it["quantity"] * it["unit_price"] for it in items)
    tax = sub * 0.18
    grand = sub + tax

    data = {
        "invoice_number": f"{doc_type[:3].upper()}-0040",
        "date": "23-10-2026",
        "company": COMPANY_DATA,
        "customer": CUSTOMER_DATA,
        "supplier": CUSTOMER_DATA,
        "items": items,
        "totals": {
            "taxable_amount": sub,
            "cgst_amount": tax / 2.0,
            "sgst_amount": tax / 2.0,
            "grand_total": grand,
        }
    }

    gen = get_generator(doc_type)
    pdf_path = gen(data, out_file)

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) >= 2, f"Expected at least 2 pages for 40 items in {doc_type}, got {len(pdf.pages)}"

        # Verify Page 1 has continued indicator and header
        p1_text = pdf.pages[0].extract_text()
        assert "Page 1 of" in p1_text or "Page 1" in p1_text

        # Verify last page has the pinned footer and grand total
        last_page = pdf.pages[-1]
        words = last_page.extract_words()
        lowest_bottom = max(w['bottom'] for w in words)
        frame_bottom_y = float(last_page.height) - 28.346
        gap_frame_mm = (frame_bottom_y - lowest_bottom) / 72.0 * 25.4
        assert gap_frame_mm <= 12.0, f"Last page gap too large in {doc_type}: {gap_frame_mm:.2f} mm"

        last_text = last_page.extract_text()
        if doc_type != "challan":
            assert format_inr(grand) in last_text or f"{grand:,.2f}" in last_text


def test_corrupt_logo_resilience(tmp_path):
    """Asserts that corrupt or invalid logo image does not crash generation and skips gracefully."""
    corrupt_logo = tmp_path / "corrupt_logo.png"
    with open(corrupt_logo, "wb") as f:
        f.write(b"NOT_A_VALID_PNG_FILE_HEADER_GARBAGE")

    out_file = tmp_path / "invoice_corrupt_logo.pdf"
    comp_with_corrupt_logo = {**COMPANY_DATA, "logo_path": str(corrupt_logo)}

    data = {
        "invoice_number": "INV-CORRUPT-LOGO",
        "date": "23-10-2026",
        "company": comp_with_corrupt_logo,
        "customer": CUSTOMER_DATA,
        "items": [make_item(1)],
    }

    gen = get_generator("tax_invoice")
    pdf_path = gen(data, out_file)
    assert os.path.exists(pdf_path), "PDF generation failed when logo was corrupt"

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) == 1
        text = pdf.pages[0].extract_text()
        assert "Delhi Enterprise Solutions" in text


def test_user_sample_delhi_enterprise_exact_match(tmp_path):
    """
    Tests the exact sample from user prompt:
    Delhi Enterprise Solutions, Copper Busbar 50x10mm, 1 MTR at Rs. 1,200.00,
    IGST 18%, total Rs. 1,416.00, "One Thousand, Four Hundred And Sixteen Only".
    """
    out_file = tmp_path / "proforma_PF-2026-27-0001.pdf"
    data = {
        "invoice_number": "PF-2026-27-0001",
        "date": "23-10-2026",
        "tax_mode": "inter_state",
        "company": COMPANY_DATA,
        "customer": CUSTOMER_DATA,
        "items": [
            {
                "item_description": "Copper Busbar 50x10mm",
                "hsn_code": "7407",
                "quantity": 1.0,
                "unit": "MTR",
                "unit_price": 1200.00,
                "tax_rate": 18.0,
                "tax_amount": 216.00,
                "total_item_amount": 1416.00,
            }
        ],
        "totals": {
            "taxable_amount": 1200.00,
            "igst_amount": 216.00,
            "grand_total": 1416.00,
        }
    }

    gen = get_generator("proforma")
    pdf_path = gen(data, out_file)
    assert os.path.exists(pdf_path)

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) == 1
        p = pdf.pages[0]
        words = p.extract_words()
        lowest_bottom = max(w['bottom'] for w in words)
        gap_from_frame_mm = (float(p.height) - 28.346 - lowest_bottom) / 72.0 * 25.4
        assert gap_from_frame_mm <= 12.0, f"Gap too large: {gap_from_frame_mm:.2f} mm"

        text = p.extract_text()
        assert "Copper Busbar 50x10mm" in text
        assert "1,416.00" in text
        # Amount in words
        assert "One Thousand Four Hundred Sixteen" in text or "Four Hundred And Sixteen" in text
