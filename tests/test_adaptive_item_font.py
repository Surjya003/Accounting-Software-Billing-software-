"""
BillFlow Suite - Adaptive Item Text Sizing Test Suite
=====================================================
Covers all requirements from the Adaptive Font Specification:
1. Monotonic font sizes: font steps down as items increase on 1 page.
2. Min/Max bounds: sizes stay within [ITEM_FONT_MIN_ONE_PAGE, ITEM_FONT_MAX] (7.5 to 13.0 pt).
3. Pagination threshold: exact boundary where single page transitions to multi-page.
4. Identical font across pages: every page of a multi-page document uses ITEM_FONT_PAGINATED (8.5 pt).
5. Overflow protection: huge amounts (Rs. 99,99,99,999.99) scale down so text never overflows.
6. Auto-size setting OFF: generates exact previous fixed font sizes (7.2 pt / 7.0 pt).
7. High performance: 150 items document generates in under 1 second.
8. Total row unit matching: matches item line unit if uniform, or plain total if mixed.
"""
import time
from pathlib import Path
import pytest
import pypdfium2
import pdfplumber

from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
from app.services.pdf.core.adaptive_table import (
    ITEM_FONT_MAX, ITEM_FONT_MIN_ONE_PAGE, ITEM_FONT_PAGINATED, format_total_quantity
)
from scripts.generate_before_samples import COMPANY, CUSTOMER, ITEMS_SAMPLE

def _build_test_invoice(n, overrides=None, item_overrides=None):
    items = []
    base_n = len(ITEMS_SAMPLE)
    for i in range(n):
        tmpl = dict(ITEMS_SAMPLE[i % base_n])
        desc = tmpl["item_description"]
        tmpl["item_description"] = f"Item {i+1}: {desc}"
        if item_overrides:
            tmpl.update(item_overrides)
        items.append(tmpl)

    tot_taxable = sum(it["taxable_value"] for it in items)
    tot_igst = sum(it["igst_amount"] for it in items)
    tot_amt = sum(it["total_item_amount"] for it in items)

    comp = dict(COMPANY)
    if overrides and "company" in overrides:
        comp.update(overrides["company"])

    data = {
        "invoice_number": f"TEST-ADP-{n}",
        "date": "24-10-2026",
        "company": comp,
        "customer": dict(CUSTOMER),
        "items": items,
        "tax_mode": "inter_state",
        "totals": {
            "subtotal": tot_taxable,
            "taxable_amount": tot_taxable,
            "cgst_amount": 0.0,
            "cgst_total": 0.0,
            "sgst_amount": 0.0,
            "sgst_total": 0.0,
            "igst_amount": tot_igst,
            "igst_total": tot_igst,
            "tax_amount": tot_igst,
            "total_tax": tot_igst,
            "grand_total": tot_amt,
            "total_amount": tot_amt,
            "round_off": 0.0,
        }
    }
    if overrides:
        for k, v in overrides.items():
            if k != "company":
                data[k] = v
    return data

def _extract_body_font_sizes(pdf_path):
    sizes = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size"])
            target = [
                w for w in words
                if w["text"] in ["Variable", "Belden", "Programmable", "Heavy", "Generator"]
            ]
            if target:
                sizes.append(round(target[0]["size"], 2))
            else:
                sizes.append(None)
    return sizes


def test_monotonic_font_sizes(tmp_path):
    """Assert font size is non-increasing as item count rises for 1-page documents."""
    out_pdf = tmp_path / "test_mono.pdf"
    prev_font = ITEM_FONT_MAX + 1.0

    # Counts known to fit on 1 page for tax invoice
    for n in [1, 2, 3, 5, 8, 12, 14]:
        data = _build_test_invoice(n)
        InvoicePDFGenerator().generate_invoice(data, filename=str(out_pdf))
        doc = pypdfium2.PdfDocument(str(out_pdf))
        assert len(doc) == 1, f"Expected 1 page for {n} items, got {len(doc)}"

        sizes = _extract_body_font_sizes(out_pdf)
        assert len(sizes) == 1 and sizes[0] is not None
        curr_font = sizes[0]

        assert curr_font <= prev_font + 0.05, (
            f"Font size increased from {prev_font} to {curr_font} at n={n}"
        )
        assert ITEM_FONT_MIN_ONE_PAGE - 0.05 <= curr_font <= ITEM_FONT_MAX + 0.05, (
            f"Font {curr_font} out of bounds [{ITEM_FONT_MIN_ONE_PAGE}, {ITEM_FONT_MAX}]"
        )
        prev_font = curr_font


def test_pagination_threshold_and_fixed_multipage_font(tmp_path):
    """
    Assert that beyond the single-page boundary (n >= 15 for Tax Invoice),
    the document paginates and EVERY page strictly uses ITEM_FONT_PAGINATED (8.5 pt).
    """
    out_pdf = tmp_path / "test_pag.pdf"

    for n in [15, 20, 30, 40, 60]:
        data = _build_test_invoice(n)
        InvoicePDFGenerator().generate_invoice(data, filename=str(out_pdf))
        doc = pypdfium2.PdfDocument(str(out_pdf))
        assert len(doc) >= 2, f"Expected multi-page for {n} items, got {len(doc)}"

        sizes = _extract_body_font_sizes(out_pdf)
        for p_idx, s in enumerate(sizes):
            assert s is not None, f"Could not find body words on page {p_idx+1}"
            assert abs(s - ITEM_FONT_PAGINATED) <= 0.05, (
                f"Page {p_idx+1} has font {s} != {ITEM_FONT_PAGINATED}"
            )


def test_overflow_protection_huge_amount(tmp_path):
    """Assert huge amount (Rs. 99,99,99,999.99) causes font to step down and fits within cell."""
    out_pdf = tmp_path / "test_huge.pdf"
    data = _build_test_invoice(1, item_overrides={
        "hsn_code": "8504",
        "quantity": 1.0,
        "unit": "SET",
        "unit_price": 999999999.99,
        "taxable_value": 999999999.99,
        "igst_amount": 0.0,
        "total_item_amount": 999999999.99
    })
    InvoicePDFGenerator().generate_invoice(data, filename=str(out_pdf))

    with pdfplumber.open(str(out_pdf)) as pdf:
        p0 = pdf.pages[0]
        words = p0.extract_words(extra_attrs=["size"])
        amt_words = [w for w in words if "99,99,99,999.99" in w["text"]]
        assert len(amt_words) > 0, "Huge amount not found in PDF"
        w = amt_words[0]
        # Frame right boundary is 566.93 pt
        assert w["x1"] <= 567.0, f"Huge amount overflowed frame boundary: x1={w['x1']}"
        assert w["size"] <= 9.0, f"Font size should have scaled down, got {w['size']}"


def test_setting_disabled_produces_legacy_fixed_size(tmp_path):
    """When adaptive_item_font_enabled is False, PDFs use the legacy fixed font size (7.2 pt)."""
    out_pdf = tmp_path / "test_off.pdf"
    data = _build_test_invoice(1, overrides={
        "company": {"adaptive_item_font_enabled": False}
    })
    InvoicePDFGenerator().generate_invoice(data, filename=str(out_pdf))

    sizes = _extract_body_font_sizes(out_pdf)
    assert len(sizes) == 1
    assert abs(sizes[0] - 7.2) <= 0.05, f"Expected legacy fixed 7.2 pt, got {sizes[0]}"


def test_performance_150_items_under_one_second(tmp_path):
    """Assert 150 items document generates in under 1.0 second."""
    out_pdf = tmp_path / "test_perf_150.pdf"
    data = _build_test_invoice(150)

    t0 = time.perf_counter()
    InvoicePDFGenerator().generate_invoice(data, filename=str(out_pdf))
    elapsed = time.perf_counter() - t0

    assert elapsed < 1.0, f"150 items took {elapsed:.3f} s >= 1.0 s"
    doc = pypdfium2.PdfDocument(str(out_pdf))
    assert len(doc) == 7


def test_total_row_quantity_unit_matching():
    """Test format_total_quantity matches units when uniform, omits when mixed."""
    uniform_items = [
        {"unit": "PCS"},
        {"unit": "PCS"},
        {"unit": "PCS"},
    ]
    assert format_total_quantity(uniform_items, 15.0) == "15.00 PCS"

    mixed_items = [
        {"unit": "PCS"},
        {"unit": "MTR"},
    ]
    assert format_total_quantity(mixed_items, 25.0) == "25.00"

    blank_items = [
        {"unit": ""},
        {"unit": None},
    ]
    assert format_total_quantity(blank_items, 10.0) == "10.00"
