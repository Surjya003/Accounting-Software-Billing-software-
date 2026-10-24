import pytest
from decimal import Decimal
from app.services.billing.invoice_service import calculate_invoice_totals

def test_sc01_mixed_slabs_intrastate_hand_calculation():
    """
    Part B Item 2: Replace impossible SC-01 (taxable 2000, tax 360 with 28% slab)
    with hand-calculated real mixed slab:
    - 1,000 @ 18% -> CGST 90, SGST 90
    - 1,000 @ 28% -> CGST 140, SGST 140
    Total Tax = 460.00 (CGST 230 + SGST 230), Grand Total = 2,460.00
    """
    items = [
        {"quantity": Decimal("1"), "unit_price": Decimal("1000.00"), "gst_rate_pct": Decimal("18.00")},
        {"quantity": Decimal("1"), "unit_price": Decimal("1000.00"), "gst_rate_pct": Decimal("28.00")}
    ]
    # Same state "27" and "27" -> Intra-state
    subtotal, cgst, sgst, igst, tax_total, grand_total, processed, is_inter = calculate_invoice_totals(
        items, company_state_code="27", party_state_code="27"
    )

    assert is_inter is False
    assert subtotal == Decimal("2000.00")
    assert cgst == Decimal("230.00"), f"Expected CGST 230.00, got {cgst}"
    assert sgst == Decimal("230.00"), f"Expected SGST 230.00, got {sgst}"
    assert igst == Decimal("0.00")
    assert tax_total == Decimal("460.00"), f"Expected tax total 460.00, got {tax_total}"
    assert grand_total == Decimal("2460.00"), f"Expected grand total 2460.00, got {grand_total}"
    print(f"\n[VERIFIED SC-01 Mixed Slab Intra-state] Tax={tax_total} (CGST {cgst} + SGST {sgst}), Total={grand_total}")


def test_sc01_mixed_slabs_interstate_hand_calculation():
    """
    Inter-state mixed slab:
    - 1,000 @ 18% -> IGST 180
    - 1,000 @ 28% -> IGST 280
    Total Tax = 460.00 (IGST 460), Grand Total = 2,460.00
    """
    items = [
        {"quantity": Decimal("1"), "unit_price": Decimal("1000.00"), "gst_rate_pct": Decimal("18.00")},
        {"quantity": Decimal("1"), "unit_price": Decimal("1000.00"), "gst_rate_pct": Decimal("28.00")}
    ]
    # Different states "27" and "29" -> Inter-state
    subtotal, cgst, sgst, igst, tax_total, grand_total, processed, is_inter = calculate_invoice_totals(
        items, company_state_code="27", party_state_code="29"
    )

    assert is_inter is True
    assert subtotal == Decimal("2000.00")
    assert cgst == Decimal("0.00")
    assert sgst == Decimal("0.00")
    assert igst == Decimal("460.00"), f"Expected IGST 460.00, got {igst}"
    assert tax_total == Decimal("460.00")
    assert grand_total == Decimal("2460.00")
    print(f"[VERIFIED SC-01 Mixed Slab Inter-state] Tax={tax_total} (IGST {igst}), Total={grand_total}")


def test_three_slab_intrastate_hand_calculation():
    """
    Three-slab intra-state hand calculation:
    - 2,000 @ 5%  -> CGST 50.00, SGST 50.00
    - 1,000 @ 12% -> CGST 60.00, SGST 60.00
    - 3,000 @ 18% -> CGST 270.00, SGST 270.00
    Subtotal = 6,000.00, CGST = 380.00, SGST = 380.00, Tax = 760.00, Grand Total = 6,760.00
    """
    items = [
        {"quantity": Decimal("1"), "unit_price": Decimal("2000.00"), "gst_rate_pct": Decimal("5.00")},
        {"quantity": Decimal("1"), "unit_price": Decimal("1000.00"), "gst_rate_pct": Decimal("12.00")},
        {"quantity": Decimal("1"), "unit_price": Decimal("3000.00"), "gst_rate_pct": Decimal("18.00")},
    ]
    subtotal, cgst, sgst, igst, tax_total, grand_total, processed, is_inter = calculate_invoice_totals(
        items, company_state_code="27", party_state_code="27"
    )

    assert is_inter is False
    assert subtotal == Decimal("6000.00")
    assert cgst == Decimal("380.00")
    assert sgst == Decimal("380.00")
    assert igst == Decimal("0.00")
    assert tax_total == Decimal("760.00")
    assert grand_total == Decimal("6760.00")
    print(f"[VERIFIED 3-Slab Intra-state] Tax={tax_total} (CGST {cgst} + SGST {sgst}), Total={grand_total}")
