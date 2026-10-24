import pytest
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.database.connection import get_session
from app.database.models import Party, Voucher, CompanyProfile, VoucherAllocation
from app.config import VOUCHER_DEBIT, VOUCHER_CREDIT
from app.services.report_service import get_outstanding_report


def test_ageing_fifo_oldest_first_hand_calculation():
    """
    Defect 7 Hand Test:
    - 45-day invoice 10,000
    - payment 10,000 today
    - new invoice 5,000 today
    
    Hand Expected:
    Oldest-first allocates 10,000 payment to the 45-day invoice (clearing it to 0).
    The remaining outstanding is 5,000 for today's invoice.
    Bucket 0-30: 5,000.00
    Bucket 31-60: 0.00
    Total Outstanding: 5,000.00
    """
    today = date.today()
    date_45d_ago = today - timedelta(days=45)
    party_name = f"Customer Ageing FIFO {uuid.uuid4().hex[:6]}"

    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        if not comp:
            comp = CompanyProfile(company_name="Test Co", state="Maharashtra", gstin="27AAPFU0939L1ZV")
            session.add(comp)
        comp.ageing_allocation_method = "Oldest first"
        
        party = Party(
            name=party_name,
            party_type="Customer",
            is_active=True,
            credit_period_days=30
        )
        session.add(party)
        session.flush()
        party_id = party.id

        # 1. 45-day invoice (Voucher Debit / Sales)
        v1 = Voucher(
            voucher_number=f"INV-FIFO-01-{party_id}",
            voucher_type=VOUCHER_DEBIT,
            voucher_date=date_45d_ago,
            party_id=party_id,
            debit_amount=Decimal("10000.00"),
            total_amount=Decimal("10000.00"),
            reference_no="INV-FIFO-01"
        )
        session.add(v1)

        # 2. Payment today (Voucher Credit / Receipt)
        p1 = Voucher(
            voucher_number=f"REC-FIFO-01-{party_id}",
            voucher_type=VOUCHER_CREDIT,
            voucher_date=today,
            party_id=party_id,
            credit_amount=Decimal("10000.00"),
            total_amount=Decimal("10000.00"),
            reference_no=""
        )
        session.add(p1)

        # 3. New invoice today (Voucher Debit / Sales)
        v2 = Voucher(
            voucher_number=f"INV-FIFO-02-{party_id}",
            voucher_type=VOUCHER_DEBIT,
            voucher_date=today,
            party_id=party_id,
            debit_amount=Decimal("5000.00"),
            total_amount=Decimal("5000.00"),
            reference_no="INV-FIFO-02"
        )
        session.add(v2)
        session.commit()

    # Run get_outstanding_report
    rep = get_outstanding_report(report_type="Receivables", as_of_date=today)
    
    party_data = [p for p in rep["party_rows"] if p["party_id"] == party_id]
    assert len(party_data) == 1, "Party should be present in outstanding report"
    row = party_data[0]

    assert row["total_outstanding"] == 5000.00
    assert row["bucket_0_30"] == 5000.00
    assert row["bucket_31_60"] == 0.00
    assert row["bucket_61_90"] == 0.00
    assert row["bucket_90_plus"] == 0.00
    print(f"\n[VERIFIED Defect 7 FIFO] Total={row['total_outstanding']}, 0-30={row['bucket_0_30']}, 31-60={row['bucket_31_60']}")


def test_ageing_against_reference_allocation():
    """
    Test Against-Reference allocation:
    - 45-day invoice 10,000 (INV-REF-01)
    - new invoice 5,000 today (INV-REF-02)
    - payment 5,000 today referencing 'INV-REF-02'
    
    Under Against-Reference:
    Payment of 5,000 pays INV-REF-02 first.
    Remaining unpaid is INV-REF-01 (10,000) which is 45 days old.
    Bucket 0-30: 0.00
    Bucket 31-60: 10,000.00
    Total Outstanding: 10,000.00
    """
    today = date.today()
    date_45d_ago = today - timedelta(days=45)
    party_name = f"Customer Ageing REF {uuid.uuid4().hex[:6]}"

    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        if not comp:
            comp = CompanyProfile(company_name="Test Co", state="Maharashtra", gstin="27AAPFU0939L1ZV")
            session.add(comp)
        comp.ageing_allocation_method = "Against reference"
        
        party = Party(
            name=party_name,
            party_type="Customer",
            is_active=True,
            credit_period_days=30
        )
        session.add(party)
        session.flush()
        party_id = party.id

        ref1 = f"INV-REF01-{party_id}"
        ref2 = f"INV-REF02-{party_id}"

        # 1. 45-day invoice (Voucher Debit / Sales)
        v1 = Voucher(
            voucher_number=ref1,
            voucher_type=VOUCHER_DEBIT,
            voucher_date=date_45d_ago,
            party_id=party_id,
            debit_amount=Decimal("10000.00"),
            total_amount=Decimal("10000.00"),
            reference_no=ref1
        )
        session.add(v1)

        # 2. New invoice today (Voucher Debit / Sales)
        v2 = Voucher(
            voucher_number=ref2,
            voucher_type=VOUCHER_DEBIT,
            voucher_date=today,
            party_id=party_id,
            debit_amount=Decimal("5000.00"),
            total_amount=Decimal("5000.00"),
            reference_no=ref2
        )
        session.add(v2)

        # 3. Payment today specifically referencing INV-REF02
        p1 = Voucher(
            voucher_number=f"REC-REF01-{party_id}",
            voucher_type=VOUCHER_CREDIT,
            voucher_date=today,
            party_id=party_id,
            credit_amount=Decimal("5000.00"),
            total_amount=Decimal("5000.00"),
            reference_no=ref2
        )
        session.add(p1)
        session.commit()

    rep = get_outstanding_report(report_type="Receivables", as_of_date=today)
    party_data = [p for p in rep["party_rows"] if p["party_id"] == party_id]
    row = party_data[0]

    assert row["total_outstanding"] == 10000.00
    assert row["bucket_0_30"] == 0.00
    assert row["bucket_31_60"] == 10000.00
    print(f"\n[VERIFIED Defect 7 Against Reference] Total={row['total_outstanding']}, 0-30={row['bucket_0_30']}, 31-60={row['bucket_31_60']}")
