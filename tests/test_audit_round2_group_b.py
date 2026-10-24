import os
import sys
from pathlib import Path
from decimal import Decimal
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = ROOT_DIR / "data" / "test_accounting.db"
os.environ["ACCOUNTING_DB_PATH"] = str(TEST_DB_PATH)
os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"

from app.database.connection import get_session
from app.database.models import Party, Product, CompanyProfile
from app.services.party_service import create_party, update_party, validate_gstin
from app.services.billing.product_service import create_product, update_product
from app.services.validation_helpers import (
    parse_decimal, validate_indian_phone, normalize_name,
    enforce_max_length, validate_and_store_logo
)


@pytest.fixture(autouse=True)
def cleanup_test_b_entities():
    with get_session() as session:
        session.query(Party).filter(Party.name.ilike("Test %")).delete()
        session.query(Party).filter(Party.name.ilike("%Spaced Enterprise%")).delete()
        session.query(Product).filter(Product.name.ilike("Valid Product%")).delete()
        session.query(Product).filter(Product.name.ilike("Another Unique%")).delete()
        session.query(Product).filter(Product.name.ilike("%Clean Space%")).delete()



def test_bug_04_and_05_gstin_validation():
    """BUG-04: Reject invalid state code 99 and state mismatch. BUG-05: Auto-uppercase."""
    # 1. State code 99 rejected for parties
    assert validate_gstin("99AAACR1234A1Z1") is False
    with pytest.raises(ValueError, match="Invalid GSTIN"):
        create_party({"name": "Test Party 99", "gstin": "99AAACR1234A1Z1"})

    # 2. State code mismatch (GSTIN has 27 MH, selected state code is 24 GJ)
    assert validate_gstin("27AAACR1234A1Z1", state_code="24") is False
    with pytest.raises(ValueError, match="does not match"):
        create_party({"name": "Test State Mismatch", "gstin": "27AAACR1234A1Z1", "state_code": "24", "state": "Gujarat"})

    # 3. Lowercase auto-uppercased (BUG-05)
    p = create_party({"name": "Test Lowercase GSTIN", "gstin": "27aaacr1234a1z1", "state_code": "27"})
    assert p.gstin == "27AAACR1234A1Z1"
    assert p.gstin.isupper()


def test_bug_06_and_07_phone_validation():
    """BUG-06 & BUG-07: Strict Indian mobile validation (10 digits starting with 6-9)."""
    # 9 digits - rejected
    with pytest.raises(ValueError, match="Indian mobile"):
        create_party({"name": "Test 9 Digit Phone", "phone": "982001234"})

    # 11 digits - rejected
    with pytest.raises(ValueError, match="Indian mobile"):
        create_party({"name": "Test 11 Digit Phone", "phone": "98200123456"})

    # Starts with 5 - rejected
    with pytest.raises(ValueError, match="Indian mobile"):
        create_party({"name": "Test Invalid Prefix Phone", "phone": "5820012345"})

    # Valid 10 digits with +91 - accepted and cleaned
    p1 = create_party({"name": "Test Valid Mobile +91", "phone": "+91 98200 12345"})
    assert p1.phone == "9820012345"

    # Valid 10 digits with 0 prefix - accepted and cleaned
    p2 = create_party({"name": "Test Valid Mobile 0", "phone": "09820012345"})
    assert p2.phone == "9820012345"


def test_bug_08_negative_credit_limit_and_period():
    """BUG-08: Reject negative credit limit and negative credit period days."""
    with pytest.raises(ValueError, match="Credit limit cannot be negative"):
        create_party({"name": "Test Neg Credit", "credit_limit": -50000.00})

    with pytest.raises(ValueError, match="Credit period days cannot be negative"):
        create_party({"name": "Test Neg Credit Days", "credit_period_days": -15})

    p = create_party({"name": "Test Credit Update", "credit_limit": 50000.00})
    with pytest.raises(ValueError, match="Credit limit cannot be negative"):
        update_party(p.id, {"credit_limit": -100.00})

    with pytest.raises(ValueError, match="Credit period days cannot be negative"):
        update_party(p.id, {"credit_period_days": -5})


def test_bug_09_update_product_validation():
    """BUG-09: update_product must run same validations as create_product."""
    p = create_product({"name": "Valid Product For Edit", "price": 100.00, "stock_quantity": 10.0})

    # Negative price rejected on update
    with pytest.raises(ValueError, match="Selling price cannot be negative"):
        update_product(p.id, {"price": -999.00})

    # Negative purchase price rejected on update
    with pytest.raises(ValueError, match="Purchase price cannot be negative"):
        update_product(p.id, {"purchase_price": -50.00})

    # Negative stock rejected on update
    with pytest.raises(ValueError, match="Stock quantity cannot be negative"):
        update_product(p.id, {"stock_quantity": -5.0})

    # Negative low stock threshold rejected on update
    with pytest.raises(ValueError, match="Low stock threshold cannot be negative"):
        update_product(p.id, {"low_stock_threshold": -1.0})

    # Duplicate name rejected on update
    p2 = create_product({"name": "Another Unique Product", "price": 200.00})
    with pytest.raises(ValueError, match="already exists"):
        update_product(p2.id, {"name": "Valid Product For Edit"})


def test_bug_27_whitespace_in_names():
    """BUG-27: Strip leading/trailing and collapse internal whitespace runs."""
    with get_session() as session:
        session.query(Party).filter(Party.name.ilike("%Spaced Enterprise 99%")).delete()
        session.query(Product).filter(Product.name.ilike("%Clean Space Product 99%")).delete()

    p = create_party({"name": "   Spaced   Enterprise   99   Ltd   "})
    assert p.name == "Spaced Enterprise 99 Ltd"

    # Subsequent duplicate with different whitespace rejected
    with pytest.raises(ValueError, match="already exists"):
        create_party({"name": "  spaced enterprise   99 ltd "})

    prod = create_product({"name": "   Clean   Space   Product   99   ", "price": 50.00})
    assert prod.name == "Clean Space Product 99"

    with pytest.raises(ValueError, match="already exists"):
        create_product({"name": "clean space product 99", "price": 60.00})


def test_bug_28_10000_char_address_and_lengths():
    """BUG-28: Enforce max field lengths in service layer."""
    huge_str = "A" * 10000
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        create_party({"name": "Huge Address Party", "address": huge_str})

    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        create_party({"name": "A" * 250})


def test_bug_29_parse_decimal_indian_format():
    """BUG-29: Parse Indian comma formatted numbers and reject invalid syntax."""
    assert parse_decimal("1,00,000.00") == Decimal("100000.00")
    assert parse_decimal("₹ 1,50,000.50") == Decimal("150000.50")
    assert parse_decimal("  25,000  ") == Decimal("25000")
    assert parse_decimal(1000) == Decimal("1000")
    assert parse_decimal(50.25) == Decimal("50.25")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_decimal("100abc")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_decimal("NaN")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_decimal("Infinity")

    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_decimal("1e5")


def test_bug_03_logo_validation(tmp_path):
    """BUG-03: Validate logo header (magic bytes), 2MB limit, dimension resize, and copy to data folder."""
    # 1. Reject .exe file disguised or real
    bad_file = tmp_path / "fake_logo.exe"
    bad_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")
    with pytest.raises(ValueError, match="Invalid logo image format"):
        validate_and_store_logo(str(bad_file))

    # 2. Reject file > 2MB
    huge_file = tmp_path / "huge_logo.png"
    # Create fake PNG over 2MB
    huge_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024 + 10))
    with pytest.raises(ValueError, match="exceeds maximum allowed size of 2 MB"):
        validate_and_store_logo(str(huge_file))

    # 3. Valid image
    from PIL import Image
    valid_img = tmp_path / "valid_logo.png"
    im = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    im.save(str(valid_img), format="PNG")

    saved_path = validate_and_store_logo(str(valid_img))
    assert Path(saved_path).exists()
    assert "data" in saved_path
