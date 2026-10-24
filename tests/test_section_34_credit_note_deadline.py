import pytest
from datetime import date
from decimal import Decimal
import uuid

from app.database.connection import get_session
from app.database.models import Party, Product, Invoice, InvoiceItem
from app.services.billing.return_service import create_sales_return, get_section_34_deadline

def test_section_34_deadline_calculation():
    # Invoice in FY 2024-25 (e.g. May 2024) -> FY End 31-Mar-2025 -> Deadline 30-Nov-2025
    assert get_section_34_deadline(date(2024, 5, 10)) == date(2025, 11, 30)
    # Invoice in FY 2024-25 (e.g. Jan 2025) -> FY End 31-Mar-2025 -> Deadline 30-Nov-2025
    assert get_section_34_deadline(date(2025, 1, 15)) == date(2025, 11, 30)
    # Invoice in FY 2025-26 (e.g. Aug 2025) -> FY End 31-Mar-2026 -> Deadline 30-Nov-2026
    assert get_section_34_deadline(date(2025, 8, 20)) == date(2026, 11, 30)


def test_section_34_credit_note_enforcement():
    with get_session() as session:
        party = Party(name=f"Sec34 Party {uuid.uuid4().hex[:6]}", party_type="Customer", state="Maharashtra", state_code="27", is_active=True)
        prod = Product(name=f"Sec34 Item {uuid.uuid4().hex[:6]}", unit="PCS", price=Decimal("1000.00"), tax_rate=Decimal("18.00"), is_active=True)
        session.add_all([party, prod])
        session.flush()

        inv = Invoice(
            invoice_number=f"INV-SEC34-{uuid.uuid4().hex[:6]}",
            invoice_date=date(2024, 5, 10),  # FY 2024-25
            party_id=party.id,
            status="final",
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
            total_amount=Decimal("1180.00")
        )
        session.add(inv)
        session.flush()

        item = InvoiceItem(
            invoice_id=inv.id,
            product_id=prod.id,
            item_description=prod.name,
            quantity=Decimal("5.0"),
            unit_price=Decimal("1000.00"),
            taxable_value=Decimal("5000.00"),
            total_amount=Decimal("5900.00")
        )
        session.add(item)
        session.commit()
        party_id = party.id
        prod_id = prod.id
        inv_id = inv.id

    # 1. Credit note within deadline (2025-11-20 <= 2025-11-30) -> Should SUCCEED
    cn_ok = create_sales_return({
        "party_id": party_id,
        "invoice_id": inv_id,
        "return_date": date(2025, 11, 20),
        "return_type": "Sales Return",
        "reason": "Damaged goods",
        "items": [{
            "product_id": prod_id,
            "quantity": Decimal("1.0"),
            "unit_price": Decimal("1000.00"),
            "tax_rate": Decimal("18.00")
        }]
    })
    assert cn_ok.id is not None
    print(f"\n[VERIFIED Sec 34 Within Deadline] Credit note #{cn_ok.return_number} created successfully on {cn_ok.return_date}")

    # 2. Credit note after deadline (2025-12-05 > 2025-11-30) without override -> Must FAIL with clean ValueError
    with pytest.raises(ValueError) as exc:
        create_sales_return({
            "party_id": party_id,
            "invoice_id": inv_id,
            "return_date": date(2025, 12, 5),
            "return_type": "Sales Return",
            "reason": "Late claim",
            "items": [{
                "product_id": prod_id,
                "quantity": Decimal("1.0"),
                "unit_price": Decimal("1000.00"),
                "tax_rate": Decimal("18.00")
            }]
        })
    assert "Statutory Deadline Exceeded (CGST Act Section 34(2))" in str(exc.value)
    print(f"[VERIFIED Sec 34 Post-Deadline Rejection] Blocked: {exc.value}")

    # 3. Credit note after deadline with explicit administrative permission override -> Allowed
    cn_override = create_sales_return({
        "party_id": party_id,
        "invoice_id": inv_id,
        "return_date": date(2025, 12, 5),
        "return_type": "Sales Return",
        "reason": "Department permitted revision",
        "allow_post_deadline_override": True,
        "items": [{
            "product_id": prod_id,
            "quantity": Decimal("1.0"),
            "unit_price": Decimal("1000.00"),
            "tax_rate": Decimal("18.00")
        }]
    })
    assert cn_override.id is not None
    print(f"[VERIFIED Sec 34 Override] Credit note #{cn_override.return_number} issued with permission on {cn_override.return_date}")
