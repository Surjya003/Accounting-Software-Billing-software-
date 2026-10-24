"""
Test Defect 3: Stock Valuation Method (Weighted Average Cost vs Latest Purchase Price).
Hand calculation:
1. Buy Batch 1: 10 units @ 1000 = 10,000.
2. Buy Batch 2: 10 units @ 2000 = 20,000.
   Total Inward = 20 units, Total Cost = 30,000.
   WAC rate = 30,000 / 20 = 1,500.00 / unit.
3. Sell 10 units.
   Remaining units = 10 units.
   Closing stock valuation = 10 * 1,500 = 15,000.00.
   COGS = Opening (0) + Purchases (30,000) - Closing (15,000) = 15,000.00.
(Under latest purchase price bug, closing stock was 10 * 2000 = 20,000, and COGS was 10,000).
"""
import pytest
from datetime import date
from decimal import Decimal
from app.database.connection import get_session
from app.database.models import Party, Product, CompanyProfile
from app.services.billing.purchase_order_service import create_purchase_order, receive_goods
from app.services.billing.invoice_service import create_invoice
from app.services.pnl_service import get_profit_loss_statement
from app.services.stock_report_service import get_stock_movement_report
from app.services.report_service import get_dashboard_kpis
from app.services.inventory_valuation import calculate_inventory_valuation

def test_defect_3_wac_hand_calculation():
    test_d = date(2026, 6, 1)

    with get_session() as s:
        supp = Party(name="WAC Supplier", party_type="Supplier", state_code="27", is_active=True)
        cust = Party(name="WAC Customer", party_type="Customer", state_code="27", is_active=True)
        prod = Product(
            name="WAC Test Component",
            purchase_price=Decimal("1000.00"),
            price=Decimal("2500.00"),
            tax_rate=Decimal("18.00"),
            stock_quantity=Decimal("0.000"),
            is_active=True
        )
        s.add_all([supp, cust, prod])
        s.flush()
        sid, cid, pid = supp.id, cust.id, prod.id

    # 1. Buy Batch 1: 10 @ 1000
    po1 = create_purchase_order(
        {"party_id": sid, "po_date": test_d, "status": "draft"},
        [{"product_id": pid, "quantity": 10, "unit_price": 1000.0, "gst_rate_pct": 18.0}]
    )
    receive_goods(po1.id, {pid: 10})

    # 2. Buy Batch 2: 10 @ 2000
    po2 = create_purchase_order(
        {"party_id": sid, "po_date": test_d, "status": "draft"},
        [{"product_id": pid, "quantity": 10, "unit_price": 2000.0, "gst_rate_pct": 18.0}]
    )
    receive_goods(po2.id, {pid: 10})

    # 3. Sell 10 units
    inv = create_invoice(
        {"party_id": cid, "invoice_date": test_d, "status": "final", "tax_mode": 0},
        [{"product_id": pid, "quantity": 10, "unit_price": 2500.0, "gst_rate_pct": 18.0}]
    )

    # Hand calculation verification
    with get_session() as s:
        val = calculate_inventory_valuation(s, start_date=test_d, end_date=test_d, product_ids=[pid])
        prod_val = val["products"][pid]
        
        # Verify unit cost is 1500.00 (Weighted average: (10*1000 + 10*2000) / 20 = 1500)
        assert prod_val["unit_cost"] == 1500.00, f"Expected 1500.00, got {prod_val['unit_cost']}"
        assert prod_val["stock_at_end"] == 10.0
        assert prod_val["closing_value"] == 15000.00
        assert prod_val["cogs"] == 15000.00

    # Check P&L consistency
    pnl = get_profit_loss_statement(start_date=test_d, end_date=test_d)
    assert pnl["cost_of_goods"]["valuation_method"] == "Weighted Average Cost (WAC)"
    assert pnl["cost_of_goods"]["closing_stock"] >= 15000.00

    # Check Stock Report consistency
    stock_rep = get_stock_movement_report(product_id=pid, start_date=test_d, end_date=test_d)
    item_rep = next(i for i in stock_rep["items"] if i["id"] == pid)
    assert item_rep["current_stock"] == 10.0
    assert item_rep["valuation_cost"] == 1500.00
    assert item_rep["stock_value"] == 15000.00

    # Check Dashboard consistency
    kpis = get_dashboard_kpis()
    assert kpis["stock_valuation_method"] == "Weighted Average Cost (WAC)"
    assert kpis["total_stock_value"] >= 15000.00
    print("\n[VERIFIED] Defect 3: WAC hand calculation passed (COGS=15,000, Closing=15,000) across P&L, Stock Report, and Dashboard.")
