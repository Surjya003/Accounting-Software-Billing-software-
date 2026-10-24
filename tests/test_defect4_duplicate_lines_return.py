"""
Test Defect 4: Duplicate product lines in returns.
Test requirement:
- Test 5 + 3 = 8: Two lines of same product ID (5 and 3) must sum to 8.
- When original invoice had 10 sold: return 5 + 3 = 8 succeeds, restores 8 units to stock.
- When original invoice had 6 sold: return 5 + 3 = 8 raises ValueError ('exceeds allowed return quantity').
- Tests both Sales Return (Credit Note) and Purchase Return (Debit Note).
"""
import pytest
from datetime import date
from decimal import Decimal
from app.database.connection import get_session
from app.database.models import Party, Product
from app.services.billing.invoice_service import create_invoice
from app.services.billing.purchase_order_service import create_purchase_order, receive_goods
from app.services.billing.return_service import create_sales_return, create_purchase_return

def test_defect_4_duplicate_lines_success_and_overflow():
    test_d = date(2026, 7, 1)

    with get_session() as s:
        cust = Party(name="Dup Return Customer 2", party_type="Customer", state_code="27", is_active=True)
        supp = Party(name="Dup Return Supplier 2", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(
            name="Dup Return Part",
            purchase_price=Decimal("100.00"),
            price=Decimal("200.00"),
            tax_rate=Decimal("18.00"),
            stock_quantity=Decimal("100.000"),
            is_active=True
        )
        s.add_all([cust, supp, prod])
        s.flush()
        cid, sid, pid = cust.id, supp.id, prod.id

    # CASE A: Sold 10 units. Return 5 + 3 = 8 units. Must succeed and restore 8 units to stock.
    # Initial stock: 100. Sold 10 -> stock becomes 90.
    inv = create_invoice(
        {"party_id": cid, "invoice_date": test_d, "status": "final", "tax_mode": 0},
        [{"product_id": pid, "quantity": 10, "unit_price": 200.0, "gst_rate_pct": 18.0}]
    )
    with get_session() as s:
        p_check = s.query(Product).filter(Product.id == pid).first()
        assert p_check.stock_quantity == Decimal("90.000")

    # Sales return with 2 lines of same product (5 and 3)
    sr = create_sales_return(
        {"party_id": cid, "invoice_id": inv.id, "return_date": test_d, "status": "approved"},
        [
            {"product_id": pid, "item_description": "Batch A return", "quantity": 5, "unit_price": 200.0, "tax_rate": 18.0},
            {"product_id": pid, "item_description": "Batch B return", "quantity": 3, "unit_price": 200.0, "tax_rate": 18.0},
        ]
    )
    sr_id = sr.id

    with get_session() as s:
        from app.database.models import SalesReturnItem, SalesReturn
        sr_db = s.query(SalesReturn).filter(SalesReturn.id == sr_id).first()
        sr_items = s.query(SalesReturnItem).filter(SalesReturnItem.return_id == sr_id).all()
        assert len(sr_items) == 2
        total_qty_returned = sum(Decimal(str(it.quantity)) for it in sr_items)
        assert total_qty_returned == Decimal("8.000")
        assert sr_db.subtotal == Decimal("1600.00") # 8 * 200
        assert sr_db.total_amount == Decimal("1888.00") # 1600 + 18% GST (288)

        # Stock should now be 90 + 8 = 98
        p_check = s.query(Product).filter(Product.id == pid).first()
        assert p_check.stock_quantity == Decimal("98.000")

    # CASE B: Attempting to return 5 + 3 = 8 units against an invoice that only sold 6 units MUST FAIL!
    inv6 = create_invoice(
        {"party_id": cid, "invoice_date": test_d, "status": "final", "tax_mode": 0},
        [{"product_id": pid, "quantity": 6, "unit_price": 200.0, "gst_rate_pct": 18.0}]
    )
    with pytest.raises(ValueError) as excinfo:
        create_sales_return(
            {"party_id": cid, "invoice_id": inv6.id, "return_date": test_d, "status": "approved"},
            [
                {"product_id": pid, "item_description": "Line 1", "quantity": 5, "unit_price": 200.0, "tax_rate": 18.0},
                {"product_id": pid, "item_description": "Line 2", "quantity": 3, "unit_price": 200.0, "tax_rate": 18.0},
            ]
        )
    assert "exceeds allowed return quantity" in str(excinfo.value)

    # CASE C: Purchase return: PO received 6 units, attempting to return 5 + 3 = 8 units MUST FAIL!
    po = create_purchase_order(
        {"party_id": sid, "po_date": test_d, "status": "draft"},
        [{"product_id": pid, "quantity": 6, "unit_price": 100.0, "tax_rate": 18.0}]
    )
    receive_goods(po.id, {pid: 6})

    with pytest.raises(ValueError) as excinfo_pr:
        create_purchase_return(
            {"party_id": sid, "po_id": po.id, "return_date": test_d, "status": "approved"},
            [
                {"product_id": pid, "item_description": "PR Line 1", "quantity": 5, "unit_price": 100.0, "tax_rate": 18.0},
                {"product_id": pid, "item_description": "PR Line 2", "quantity": 3, "unit_price": 100.0, "tax_rate": 18.0},
            ]
        )
    assert "exceeds allowed return quantity" in str(excinfo_pr.value)
    print("\n[VERIFIED] Defect 4: 5 + 3 = 8 lines sum correctly, stock restores 8 units, and > allowed returns raise ValueError.")
