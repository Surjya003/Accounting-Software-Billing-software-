import pytest
from decimal import Decimal
from app.services.billing.gst_engine import GSTEngine

# 15 Hand-calculated amounts covering >= .50, < .50, exact .50, zero, and negative (credit notes)
ROUND_OFF_TEST_CASES = [
    # (gross_input, expected_round_off, expected_rounded_total, description)
    (Decimal("124.55"), Decimal("0.45"), Decimal("125.00"), "SC-02 case: gross 124.55 rounds to 125.00 with +0.45"),
    (Decimal("124.50"), Decimal("0.50"), Decimal("125.00"), "Exact .50 positive rounds UP to 125.00 with +0.50"),
    (Decimal("124.49"), Decimal("-0.49"), Decimal("124.00"), ".49 positive rounds DOWN to 124.00 with -0.49"),
    (Decimal("124.01"), Decimal("-0.01"), Decimal("124.00"), ".01 positive rounds DOWN to 124.00 with -0.01"),
    (Decimal("124.99"), Decimal("0.01"), Decimal("125.00"), ".99 positive rounds UP to 125.00 with +0.01"),
    (Decimal("124.00"), Decimal("0.00"), Decimal("124.00"), "Exact integer needs 0.00 round off"),
    (Decimal("0.50"), Decimal("0.50"), Decimal("1.00"), "Small positive 0.50 rounds to 1.00"),
    (Decimal("0.49"), Decimal("-0.49"), Decimal("0.00"), "Small positive 0.49 rounds to 0.00"),
    (Decimal("999.50"), Decimal("0.50"), Decimal("1000.00"), "Boundary 999.50 rounds to 1000.00"),
    (Decimal("999.49"), Decimal("-0.49"), Decimal("999.00"), "Boundary 999.49 rounds to 999.00"),
    (Decimal("-124.55"), Decimal("-0.45"), Decimal("-125.00"), "Credit Note: -124.55 rounds to -125.00 with -0.45"),
    (Decimal("-124.50"), Decimal("-0.50"), Decimal("-125.00"), "Credit Note exact -.50 rounds to -125.00 with -0.50"),
    (Decimal("-124.49"), Decimal("0.49"), Decimal("-124.00"), "Credit Note: -124.49 rounds to -124.00 with +0.49"),
    (Decimal("-124.01"), Decimal("0.01"), Decimal("-124.00"), "Credit Note: -124.01 rounds to -124.00 with +0.01"),
    (Decimal("-100.00"), Decimal("0.00"), Decimal("-100.00"), "Credit Note exact integer needs 0.00 round off"),
]

@pytest.mark.parametrize("gross, exp_round_off, exp_rounded, desc", ROUND_OFF_TEST_CASES)
def test_gst_engine_round_off_table(gross, exp_round_off, exp_rounded, desc):
    round_off, rounded = GSTEngine.calculate_round_off(gross)
    assert rounded == exp_rounded, f"Failed for {desc}: expected rounded={exp_rounded}, got {rounded}"
    assert round_off == exp_round_off, f"Failed for {desc}: expected round_off={exp_round_off}, got {round_off}"
    assert rounded == gross + round_off, f"Mathematical identity failed: {rounded} != {gross} + {round_off}"
