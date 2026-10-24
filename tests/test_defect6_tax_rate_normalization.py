"""
Regression and verification tests for Defect 6:
`tax_rate` vs `gst_rate_pct` silently gives 0% GST.
Requires:
- Accepts either key through normalize_tax_rate
- Missing rate must raise ValueError, never default to 0% silently
- Validates every create and update path: invoice, quotation, proforma, challan, PO, returns
"""
import pytest
from datetime import date
from decimal import Decimal
from app.database.connection import get_session
from app.database.models import Party, Product, CompanyProfile
from app.services.billing.invoice_service import create_invoice, update_invoice
from app.services.billing.quotation_service import create_quotation, update_quotation
from app.services.billing.proforma_service import create_proforma, update_proforma
from app.services.billing.challan_service import create_challan, update_challan
from app.services.billing.purchase_order_service import create_purchase_order, update_purchase_order
from app.services.billing.return_service import create_sales_return, create_purchase_return

@pytest.fixture(scope="module")
def sample_entities():
    with get_session() as session:
        cust = Party(name="Tax Norm Customer", party_type="Customer", state_code="27", is_active=True)
        supp = Party(name="Tax Norm Supplier", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(name="Tax Norm Widget", price=Decimal("1000.00"), purchase_price=Decimal("800.00"), tax_rate=Decimal("18.00"), stock_quantity=Decimal("500.000"), is_active=True)
        session.add_all([cust, supp, prod])
        session.flush()
        c_id, s_id, p_id = cust.id, supp.id, prod.id
    return {"cust_id": c_id, "supp_id": s_id, "prod_id": p_id}


def test_missing_tax_rate_raises_error_across_all_services(sample_entities):
    cid = sample_entities["cust_id"]
    sid = sample_entities["supp_id"]
    pid = sample_entities["prod_id"]
    today = date(2026, 5, 1)

    bad_item = {"product_id": pid, "quantity": 1, "unit_price": 1000.0} # Missing tax_rate and gst_rate_pct!

    # 1. Invoice create & update
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_invoice({"party_id": cid, "invoice_date": today, "status": "draft"}, [bad_item])

    # 2. Quotation create
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_quotation({"party_id": cid, "quotation_date": today, "status": "draft"}, [bad_item])

    # 3. Proforma create
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_proforma({"party_id": cid, "proforma_date": today, "status": "draft"}, [bad_item])

    # 4. Challan create
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_challan({"party_id": cid, "challan_date": today, "status": "draft"}, [bad_item])

    # 5. PO create
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_purchase_order({"party_id": sid, "po_date": today, "status": "draft"}, [bad_item])

    # 6. Returns create
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_sales_return({"party_id": cid, "return_date": today, "status": "pending"}, [bad_item])
    with pytest.raises(ValueError, match="Tax rate is missing"):
        create_purchase_return({"party_id": sid, "return_date": today, "status": "pending"}, [bad_item])


def test_either_tax_rate_or_gst_rate_pct_accepted_all_services(sample_entities):
    cid = sample_entities["cust_id"]
    sid = sample_entities["supp_id"]
    pid = sample_entities["prod_id"]
    today = date(2026, 5, 2)

    # Key variant A: 'gst_rate_pct': 18.0
    item_a = {"product_id": pid, "quantity": 2, "unit_price": 1000.0, "gst_rate_pct": 18.0}
    # Key variant B: 'tax_rate': 18.0
    item_b = {"product_id": pid, "quantity": 2, "unit_price": 1000.0, "tax_rate": 18.0}

    # Invoice with variant A
    inv = create_invoice({"party_id": cid, "invoice_date": today, "status": "draft"}, [item_a])
    assert inv.tax_amount == Decimal("360.00")

    # Invoice update with variant B
    inv_up = update_invoice(inv.id, {"status": "draft"}, [item_b])
    assert inv_up.tax_amount == Decimal("360.00")

    # Quotation with variant A & update with variant B
    q = create_quotation({"party_id": cid, "quotation_date": today, "status": "draft"}, [item_a])
    assert q.tax_amount == Decimal("360.00")
    q_up = update_quotation(q.id, {"status": "draft"}, [item_b])
    assert q_up.tax_amount == Decimal("360.00")

    # Proforma with variant A & update with variant B
    pf = create_proforma({"party_id": cid, "proforma_date": today, "status": "draft"}, [item_a])
    assert pf.tax_amount == Decimal("360.00")
    pf_up = update_proforma(pf.id, {"status": "draft"}, [item_b])
    assert pf_up.tax_amount == Decimal("360.00")

    # Challan with variant A & update with variant B
    ch = create_challan({"party_id": cid, "challan_date": today, "status": "draft"}, [item_a])
    assert ch.tax_amount == Decimal("360.00")
    ch_up = update_challan(ch.id, {"status": "draft"}, [item_b])
    assert ch_up.tax_amount == Decimal("360.00")

    # Purchase Order with variant A & update with variant B
    po = create_purchase_order({"party_id": sid, "po_date": today, "status": "draft"}, [item_a])
    assert po.tax_amount == Decimal("360.00")
    po_up = update_purchase_order(po.id, {"status": "draft"}, [item_b])
    assert po_up.tax_amount == Decimal("360.00")
