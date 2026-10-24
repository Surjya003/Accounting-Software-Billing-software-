import pytest
from datetime import date
from decimal import Decimal
import uuid

from app.database.connection import get_session
from app.database.models import Party, Product, CompanyProfile
from app.services.party_service import create_party, update_party
from app.services.billing.invoice_service import create_invoice, update_invoice
from app.services.billing.challan_service import create_challan, update_challan
from app.services.cashbank_service import create_account
from app.services.validation_helpers import (
    validate_gstin,
    validate_pan,
    validate_ifsc,
    validate_vehicle_no,
    normalize_uppercase_string
)

def test_validation_helpers_casing_and_whitespace():
    # GSTIN
    assert validate_gstin("  27aapfu0939l1zv  ", state_code="27") is True
    # PAN
    assert validate_pan("  aapfu0939l  ") is True
    # IFSC
    assert validate_ifsc("  sbin0001234  ") is True
    # Vehicle
    assert validate_vehicle_no("  mh 12 ab 1234  ") is True
    assert normalize_uppercase_string("  mh-12-ab-1234  ") == "MH-12-AB-1234"


def test_party_service_normalizes_lowercase_gstin_and_pan():
    p_name = f"Case Test Party {uuid.uuid4().hex[:6]}"
    raw_gstin = "  27aapfu0939l1zv  "
    raw_pan = "  aapfu0939l  "

    party = create_party({
        "name": p_name,
        "party_type": "Customer",
        "state": "Maharashtra",
        "state_code": "27",
        "gstin": raw_gstin,
        "pan": raw_pan,
        "phone": "9876543210"
    })

    assert party.gstin == "27AAPFU0939L1ZV", f"GSTIN must be uppercased, got {party.gstin}"
    assert party.pan == "AAPFU0939L", f"PAN must be uppercased, got {party.pan}"

    # Update path
    updated = update_party(party.id, {
        "gstin": "  27aapfu0939l1zv  ",
        "pan": "  bbpfu0939m  "
    })
    assert updated.gstin == "27AAPFU0939L1ZV"
    assert updated.pan == "BBPFU0939M"
    print(f"\n[VERIFIED Party GSTIN & PAN Uppercasing] GSTIN={updated.gstin}, PAN={updated.pan}")


def test_billing_services_normalize_vehicle_and_ifsc():
    with get_session() as s:
        party = s.query(Party).filter(Party.is_active.is_(True)).first()
        prod = s.query(Product).filter(Product.is_active.is_(True)).first()
        assert party and prod

    inv = create_invoice({
        "party_id": party.id,
        "invoice_date": date.today(),
        "items": [{
            "product_id": prod.id,
            "quantity": Decimal("1.0"),
            "unit_price": Decimal("100.00"),
            "tax_rate": Decimal("18.00")
        }],
        "vehicle_no": "  mh-04-cd-5678  ",
        "bank_ifsc": "  hdfc0001234  "
    })
    assert inv.vehicle_no == "MH-04-CD-5678"
    assert inv.bank_ifsc == "HDFC0001234"

    # Update path
    up_inv = update_invoice(inv.id, {
        "vehicle_no": "  dl-01-xy-9999  ",
        "bank_ifsc": "  icic0004321  "
    })
    assert up_inv.vehicle_no == "DL-01-XY-9999"
    assert up_inv.bank_ifsc == "ICIC0004321"

    # Delivery challan
    ch = create_challan({
        "party_id": party.id,
        "challan_date": date.today(),
        "challan_type": "job_work",
        "vehicle_no": "  ka-05-mn-4321  "
    }, [{
        "product_id": prod.id,
        "quantity": Decimal("2.0"),
        "unit_price": Decimal("50.00"),
        "tax_rate": Decimal("18.00")
    }])
    assert ch.vehicle_no == "KA-05-MN-4321"
    print(f"[VERIFIED Billing Services Uppercasing] Invoice Vehicle={up_inv.vehicle_no}, IFSC={up_inv.bank_ifsc}, Challan Vehicle={ch.vehicle_no}")
