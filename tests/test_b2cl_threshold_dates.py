import pytest
from datetime import date
from decimal import Decimal
import uuid
import json
import os

from app.database.connection import get_session
from app.database.models import Party, Product, Invoice, InvoiceItem, CompanyProfile
from app.services.gst_report_service import (
    get_b2cl_threshold,
    get_gstr1_data,
    export_gstr1_offline_json,
    B2CL_THRESHOLD_HISTORY
)

def test_b2cl_threshold_table_dates():
    # Statutory verification:
    # Prior to 1 Aug 2024: 2.5 Lakh (250,000)
    assert get_b2cl_threshold(date(2024, 7, 31)) == Decimal("250000.00")
    assert get_b2cl_threshold(date(2023, 12, 31)) == Decimal("250000.00")

    # On or after 1 Aug 2024: 1.0 Lakh (100,000) per Notification 12/2024
    assert get_b2cl_threshold(date(2024, 8, 1)) == Decimal("100000.00")
    assert get_b2cl_threshold(date(2024, 8, 2)) == Decimal("100000.00")
    assert get_b2cl_threshold(date(2026, 10, 24)) == Decimal("100000.00")
    print("\n[VERIFIED B2CL Statutory Threshold Table]")


def test_b2cl_classification_boundary_post_aug_2024():
    """
    Test 99,999 / 100,000 / 100,001 on or after 1 Aug 2024.
    - 99,999: B2CS
    - 100,000: B2CS (threshold is strictly > 1,00,000)
    - 100,001: B2CL
    """
    post_date = date(2024, 9, 15)

    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        if not comp:
            comp = CompanyProfile(company_name="My Co", state="Maharashtra", gstin="27AAPFU0939L1ZV")
            session.add(comp)
        comp.state = "Maharashtra"
        comp.gstin = "27AAPFU0939L1ZV"

        # Unregistered inter-state customer (Gujarat state code 24)
        party = Party(
            name=f"URP Customer Gujarat {uuid.uuid4().hex[:6]}",
            party_type="Customer",
            state="Gujarat",
            state_code="24",
            gstin=None,
            is_active=True
        )
        session.add(party)
        session.flush()

        prod = session.query(Product).filter(Product.is_active.is_(True)).first()
        if not prod:
            prod = Product(name="Test Item", unit="PCS", price=Decimal("100.00"), tax_rate=Decimal("18.00"), is_active=True)
            session.add(prod)
            session.flush()

        inv_99k = Invoice(
            invoice_number=f"INV-99K-{uuid.uuid4().hex[:6]}",
            invoice_date=post_date,
            party_id=party.id,
            subtotal=Decimal("99999.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("99999.00"),
            status="final",
            is_interstate=True
        )
        inv_100k = Invoice(
            invoice_number=f"INV-100K-{uuid.uuid4().hex[:6]}",
            invoice_date=post_date,
            party_id=party.id,
            subtotal=Decimal("100000.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("100000.00"),
            status="final",
            is_interstate=True
        )
        inv_100k1 = Invoice(
            invoice_number=f"INV-100K1-{uuid.uuid4().hex[:6]}",
            invoice_date=post_date,
            party_id=party.id,
            subtotal=Decimal("100001.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("100001.00"),
            status="final",
            is_interstate=True
        )
        session.add_all([inv_99k, inv_100k, inv_100k1])
        session.commit()

        num_99k = inv_99k.invoice_number
        num_100k = inv_100k.invoice_number
        num_100k1 = inv_100k1.invoice_number

    data = get_gstr1_data(from_date=post_date, to_date=post_date)
    rows_by_num = {r["invoice_number"]: r for r in data["rows"]}

    assert rows_by_num[num_99k]["category"] == "B2CS", f"99,999 should be B2CS, got {rows_by_num[num_99k]['category']}"
    assert rows_by_num[num_100k]["category"] == "B2CS", f"100,000 should be B2CS, got {rows_by_num[num_100k]['category']}"
    assert rows_by_num[num_100k1]["category"] == "B2CL", f"100,001 should be B2CL, got {rows_by_num[num_100k1]['category']}"
    print(f"[VERIFIED Post-Aug-2024 Boundaries] 99,999={rows_by_num[num_99k]['category']}, 100,000={rows_by_num[num_100k]['category']}, 100,001={rows_by_num[num_100k1]['category']}")


def test_b2cl_classification_boundary_pre_aug_2024():
    """
    Test prior to 1 Aug 2024 (e.g. 2024-05-10):
    - 100,001: B2CS (because threshold was 250,000)
    - 250,000: B2CS (not > 250,000)
    - 250,001: B2CL (> 250,000)
    """
    pre_date = date(2024, 5, 10)

    with get_session() as session:
        party = session.query(Party).filter(Party.state_code == "24", Party.gstin == None).first()
        if not party:
            party = Party(name="URP Gujarat Pre", party_type="Customer", state="Gujarat", state_code="24", is_active=True)
            session.add(party)
            session.flush()

        inv_100k1 = Invoice(
            invoice_number=f"INV-PRE100K1-{uuid.uuid4().hex[:6]}",
            invoice_date=pre_date,
            party_id=party.id,
            subtotal=Decimal("100001.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("100001.00"),
            status="final",
            is_interstate=True
        )
        inv_250k = Invoice(
            invoice_number=f"INV-PRE250K-{uuid.uuid4().hex[:6]}",
            invoice_date=pre_date,
            party_id=party.id,
            subtotal=Decimal("250000.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("250000.00"),
            status="final",
            is_interstate=True
        )
        inv_250k1 = Invoice(
            invoice_number=f"INV-PRE250K1-{uuid.uuid4().hex[:6]}",
            invoice_date=pre_date,
            party_id=party.id,
            subtotal=Decimal("250001.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("250001.00"),
            status="final",
            is_interstate=True
        )
        session.add_all([inv_100k1, inv_250k, inv_250k1])
        session.commit()

        num_100k1 = inv_100k1.invoice_number
        num_250k = inv_250k.invoice_number
        num_250k1 = inv_250k1.invoice_number

    data = get_gstr1_data(from_date=pre_date, to_date=pre_date)
    rows_by_num = {r["invoice_number"]: r for r in data["rows"]}

    assert rows_by_num[num_100k1]["category"] == "B2CS", f"Pre-Aug-2024 100,001 should be B2CS, got {rows_by_num[num_100k1]['category']}"
    assert rows_by_num[num_250k]["category"] == "B2CS", f"Pre-Aug-2024 250,000 should be B2CS, got {rows_by_num[num_250k]['category']}"
    assert rows_by_num[num_250k1]["category"] == "B2CL", f"Pre-Aug-2024 250,001 should be B2CL, got {rows_by_num[num_250k1]['category']}"
    print(f"[VERIFIED Pre-Aug-2024 Boundaries] 100,001={rows_by_num[num_100k1]['category']}, 250,000={rows_by_num[num_250k]['category']}, 250,001={rows_by_num[num_250k1]['category']}")
