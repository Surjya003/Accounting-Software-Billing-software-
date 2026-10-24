import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import os
TEST_DB_PATH = ROOT_DIR / "data" / "test_accounting.db"
os.environ["ACCOUNTING_DB_PATH"] = str(TEST_DB_PATH)
os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"

import pytest
from datetime import date, timedelta
from decimal import Decimal
import threading

from app.database.connection import init_db, get_session
from app.database.models import (
    Party, Product, Invoice, Quotation, DeliveryChallan,
    ProformaInvoice, PurchaseOrder, SalesReturn, PurchaseReturn,
    Voucher, BankAccount, Expense, ExpenseCategory, CompanyProfile
)
from app.services.party_service import create_party
from app.services.billing.product_service import create_product, get_product_by_id, update_product
from app.services.billing.invoice_service import (
    create_invoice, update_invoice, cancel_invoice, delete_invoice, get_invoice_by_id
)
from app.services.billing.quotation_service import create_quotation, convert_to_invoice as convert_quote_to_invoice
from app.services.billing.challan_service import create_challan, convert_to_invoice as convert_challan_to_invoice
from app.services.billing.proforma_service import create_proforma, convert_to_invoice as convert_proforma_to_invoice
from app.services.billing.purchase_order_service import (
    create_purchase_order, receive_goods, delete_purchase_order, cancel_purchase_order
)
from app.services.billing.return_service import create_sales_return, create_purchase_return
from app.services.report_service import get_trial_balance
from app.services.pnl_service import get_profit_loss_statement
from app.services.cashbank_service import create_account, create_transaction
from app.services.expense_service import create_expense, create_category
from app.services.voucher_service import create_voucher


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure DB initialized."""
    init_db()


def test_bug_22_trial_balance_equality():
    """BUG-22: Trial Balance must have total_cl_dr == total_cl_cr to the paisa."""
    tb = get_trial_balance()
    dr = Decimal(str(tb["total_cl_dr"]))
    cr = Decimal(str(tb["total_cl_cr"]))
    diff = abs(dr - cr)
    assert diff < Decimal("0.01"), f"Trial Balance out of balance: Dr={dr} vs Cr={cr}, diff={diff}"
    assert tb["is_balanced"] is True


def test_bug_23_pnl_hand_calculated_scenario():
    """
    BUG-23: Test hand-calculated scenario:
    Buy 10 @ 600, sell 4 @ 1,000, return 1, receive part payment of 2,000, add 500 expense.
    Expected:
      Net Sales = 3,000
      COGS = 1,800 (3 units @ 600)
      Gross Profit = 1,200
      Net Profit = 700
      Part payment of 2,000 must NOT change P&L.
    """
    with get_session() as session:
        # Create unique party and product
        supplier = Party(name="P&L Test Supplier", party_type="Supplier", state_code="27", is_active=True)
        customer = Party(name="P&L Test Customer", party_type="Customer", state_code="27", is_active=True)
        product = Product(
            name="P&L Test Widget",
            purchase_price=Decimal("600.00"),
            price=Decimal("1000.00"),
            tax_rate=Decimal("0.00"),  # 0% tax for pure financial verification
            stock_quantity=Decimal("0.000"),
            is_active=True
        )
        session.add_all([supplier, customer, product])
        session.flush()
        s_id, c_id, p_id = supplier.id, customer.id, product.id

    scenario_date = date(2027, 2, 1)
    with get_session() as session:
        session.query(Expense).filter(Expense.expense_date == scenario_date).delete()
        session.query(SalesReturn).filter(SalesReturn.return_date == scenario_date).delete()
        session.query(Invoice).filter(Invoice.invoice_date == scenario_date).delete()
        session.query(PurchaseOrder).filter(PurchaseOrder.po_date == scenario_date).delete()
        session.query(Voucher).filter(Voucher.voucher_date == scenario_date).delete()

    # 1. Buy 10 @ 600
    po = create_purchase_order(
        {"party_id": s_id, "po_date": scenario_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "Widget", "quantity": 10, "unit_price": 600.0, "tax_rate": 0}]
    )
    receive_goods(po.id, {p_id: 10})

    # 2. Sell 4 @ 1,000
    inv = create_invoice(
        {"party_id": c_id, "invoice_date": scenario_date, "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Widget", "quantity": 4, "unit_price": 1000.0, "gst_rate_pct": 0}]
    )

    # 3. Return 1 unit
    sr = create_sales_return(
        {"party_id": c_id, "invoice_id": inv.id, "return_date": scenario_date, "status": "approved"},
        [{"product_id": p_id, "item_description": "Widget", "quantity": 1, "unit_price": 1000.0, "tax_rate": 0}]
    )

    # 4. Add 500 operating expense
    try:
        cat = create_category("P&L Office Expense")
    except ValueError:
        with get_session() as session:
            cat = session.query(ExpenseCategory).filter(ExpenseCategory.name == "P&L Office Expense").first().to_dict()
    create_expense({
        "expense_date": scenario_date,
        "category_id": cat["id"],
        "description": "Office Supplies",
        "amount": 500.00,
        "gst_amount": 0.00,
        "payment_mode": "Cash"
    })

    # Check P&L before customer payment
    pnl1 = get_profit_loss_statement(start_date=scenario_date, end_date=scenario_date)

    # 5. Customer part payment of 2,000
    create_voucher({
        "voucher_type": "Credit",
        "voucher_date": scenario_date,
        "party_id": c_id,
        "reference_no": "REC-TEST-2000",
        "payment_mode": "Cash",
        "total_amount": Decimal("2000.00"),
        "narration": "Customer part payment"
    })

    # Check P&L after customer payment
    pnl2 = get_profit_loss_statement(start_date=scenario_date, end_date=scenario_date)

    # Assertions
    assert float(pnl1["revenue"]["total_sales"]) == 3000.00
    assert float(pnl1["cost_of_goods"]["total_purchases"]) == 1800.00 or float(pnl1["cogs"]["total"]) == 1800.00
    assert float(pnl1["gross_profit"]) == 1200.00
    assert float(pnl1["net_profit"]) == 700.00

    # Payment must not change P&L at all!
    assert float(pnl2["revenue"]["total_sales"]) == float(pnl1["revenue"]["total_sales"])
    assert float(pnl2["cogs"]["total"]) == float(pnl1["cogs"]["total"])
    assert float(pnl2["gross_profit"]) == float(pnl1["gross_profit"])
    assert float(pnl2["net_profit"]) == float(pnl1["net_profit"])


def test_bug_15_editing_finalized_invoice_syncs_voucher_and_stock():
    """BUG-15: Editing a finalized invoice must update stock and ledger voucher in the same transaction."""
    with get_session() as session:
        cust = Party(name="Sync Test Cust", party_type="Customer", state_code="27", is_active=True)
        prod = Product(
            name="Sync Test Item",
            price=Decimal("1000.00"),
            purchase_price=Decimal("500.00"),
            tax_rate=Decimal("18.00"),
            stock_quantity=Decimal("100.000"),
            is_active=True
        )
        session.add_all([cust, prod])
        session.flush()
        c_id, p_id = cust.id, prod.id

    # Create finalized invoice: 10 units @ 1000 + 18% GST = 10,000 + 1,800 = 11,800
    inv = create_invoice(
        {"party_id": c_id, "invoice_date": date.today(), "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Sync Test Item", "quantity": 10, "unit_price": 1000.0, "gst_rate_pct": 18.0}]
    )
    # Check initial stock: 100 - 10 = 90
    prod_data = get_product_by_id(p_id)
    assert prod_data["stock_quantity"] == 90.0

    # Check voucher
    with get_session() as session:
        v = session.query(Voucher).filter(Voucher.voucher_number == inv.invoice_number).first()
        assert v is not None
        assert v.total_amount == Decimal("11800.00")

    # Now edit invoice: change quantity to 15 (stock should become 85, voucher 17,700)
    new_items = [{"product_id": p_id, "item_description": "Sync Test Item", "quantity": 15, "unit_price": 1000.0, "gst_rate_pct": 18.0}]
    updated = update_invoice(inv.id, {"party_id": c_id}, new_items)

    assert updated.total_amount == Decimal("17700.00")

    # Verify stock updated by difference
    prod_data = get_product_by_id(p_id)
    assert prod_data["stock_quantity"] == 85.0

    # Verify voucher updated to 17,700
    with get_session() as session:
        v = session.query(Voucher).filter(Voucher.voucher_number == inv.invoice_number).first()
        assert v.total_amount == Decimal("17700.00")
        assert v.amount_untaxed == Decimal("15000.00")
        assert v.debit_amount == Decimal("17700.00")


def test_bug_17_and_18_double_conversion_blocked():
    """BUG-17 & BUG-18: Converting an already converted quotation or challan must be rejected."""
    with get_session() as session:
        cust = Party(name="Conv Test Cust", party_type="Customer", state_code="27", is_active=True)
        prod = Product(name="Conv Test Item", price=Decimal("100.00"), stock_quantity=Decimal("50.000"), is_active=True)
        session.add_all([cust, prod])
        session.flush()
        c_id, p_id = cust.id, prod.id

    # 1. Quotation
    quote = create_quotation(
        {"party_id": c_id, "quotation_date": date.today(), "status": "draft"},
        [{"product_id": p_id, "item_description": "Conv Item", "quantity": 5, "unit_price": 100.0, "gst_rate_pct": 0}]
    )
    # First conversion succeeds
    inv1 = convert_quote_to_invoice(quote.id)
    assert inv1 is not None

    # Second conversion must raise ValueError
    with pytest.raises(ValueError, match="already been converted"):
        convert_quote_to_invoice(quote.id)

    # 2. Challan
    challan = create_challan(
        {"party_id": c_id, "challan_date": date.today(), "status": "pending"},
        [{"product_id": p_id, "item_description": "Conv Item", "quantity": 5, "unit_price": 100.0, "tax_rate": 0}]
    )
    # First conversion succeeds
    inv2 = convert_challan_to_invoice(challan.id)
    assert inv2 is not None

    # Second conversion must raise ValueError
    with pytest.raises(ValueError, match="already been converted"):
        convert_challan_to_invoice(challan.id)


def test_bug_19_and_20_return_validations():
    """BUG-19 & BUG-20: Cumulative returns cannot exceed original invoice, and returns against cancelled invoices are rejected."""
    with get_session() as session:
        cust = Party(name="Ret Test Cust", party_type="Customer", state_code="27", is_active=True)
        prod = Product(name="Ret Test Item", price=Decimal("100.00"), stock_quantity=Decimal("50.000"), is_active=True)
        session.add_all([cust, prod])
        session.flush()
        c_id, p_id = cust.id, prod.id

    # Sell 10 units
    inv = create_invoice(
        {"party_id": c_id, "invoice_date": date.today(), "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Ret Item", "quantity": 10, "unit_price": 100.0, "gst_rate_pct": 0}]
    )

    # First return: 6 units (allowed)
    r1 = create_sales_return(
        {"party_id": c_id, "invoice_id": inv.id, "return_date": date.today(), "status": "approved"},
        [{"product_id": p_id, "item_description": "Ret Item", "quantity": 6, "unit_price": 100.0, "tax_rate": 0}]
    )
    assert r1.id is not None

    # Second return: 6 units (must fail because 6 + 6 = 12 > 10)
    with pytest.raises(ValueError, match="exceeds"):
        create_sales_return(
            {"party_id": c_id, "invoice_id": inv.id, "return_date": date.today(), "status": "approved"},
            [{"product_id": p_id, "item_description": "Ret Item", "quantity": 6, "unit_price": 100.0, "tax_rate": 0}]
        )

    # Cancel a different invoice and verify return is rejected (BUG-20)
    inv2 = create_invoice(
        {"party_id": c_id, "invoice_date": date.today(), "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Ret Item", "quantity": 5, "unit_price": 100.0, "gst_rate_pct": 0}]
    )
    cancel_invoice(inv2.id)

    with pytest.raises(ValueError, match="cancelled"):
        create_sales_return(
            {"party_id": c_id, "invoice_id": inv2.id, "return_date": date.today(), "status": "approved"},
            [{"product_id": p_id, "item_description": "Ret Item", "quantity": 2, "unit_price": 100.0, "tax_rate": 0}]
        )


def test_bug_13_po_deletion_and_cancel():
    """BUG-13: Block deletion of PO with received quantity > 0, provide cancel path."""
    with get_session() as session:
        supp = Party(name="PO Test Supp", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(name="PO Test Prod", purchase_price=Decimal("100.00"), stock_quantity=Decimal("10.000"), is_active=True)
        session.add_all([supp, prod])
        session.flush()
        s_id, p_id = supp.id, prod.id

    po = create_purchase_order(
        {"party_id": s_id, "po_date": date.today(), "status": "draft"},
        [{"product_id": p_id, "item_description": "PO Prod", "quantity": 20, "unit_price": 100.0, "tax_rate": 0}]
    )
    # Receive 10
    receive_goods(po.id, {p_id: 10})

    # Attempt delete must raise ValueError
    with pytest.raises(ValueError, match="received"):
        delete_purchase_order(po.id)

    # Cancel path must reverse stock
    initial_stock = get_product_by_id(p_id)["stock_quantity"]
    assert initial_stock == 20.0  # 10 initial + 10 received
    cancel_purchase_order(po.id)
    after_cancel_stock = get_product_by_id(p_id)["stock_quantity"]
    assert after_cancel_stock == 10.0  # reversed received 10


def test_bug_14_overselling_and_negative_stock():
    """BUG-14: Block overselling when allow_negative_stock is False; allow honest negative when True."""
    with get_session() as session:
        cust = Party(name="Stock Test Cust", party_type="Customer", state_code="27", is_active=True)
        prod = Product(name="Stock Test Prod", price=Decimal("100.00"), stock_quantity=Decimal("9.000"), is_active=True)
        comp = session.query(CompanyProfile).first()
        comp.allow_negative_stock = False
        session.add_all([cust, prod])
        session.flush()
        c_id, p_id = cust.id, prod.id

    # Attempting to invoice 50 when only 9 in stock must raise ValueError
    with pytest.raises(ValueError, match="Insufficient stock"):
        create_invoice(
            {"party_id": c_id, "invoice_date": date.today(), "status": "final", "tax_mode": 0},
            [{"product_id": p_id, "item_description": "Stock Prod", "quantity": 50, "unit_price": 100.0, "gst_rate_pct": 0}]
        )

    # Stock must NOT be clamped to 0
    p = get_product_by_id(p_id)
    assert p["stock_quantity"] == 9.0


def test_bug_10_11_12_po_receipt_validation():
    """BUG-10, BUG-11, BUG-12: Reject negative/exceeding receipt, reject on cancelled/received, transition to 'received'."""
    with get_session() as session:
        supp = Party(name="Rcpt Test Supp", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(name="Rcpt Test Prod", purchase_price=Decimal("100.00"), stock_quantity=Decimal("0.000"), is_active=True)
        session.add_all([supp, prod])
        session.flush()
        s_id, p_id = supp.id, prod.id

    po = create_purchase_order(
        {"party_id": s_id, "po_date": date.today(), "status": "draft"},
        [{"product_id": p_id, "item_description": "Rcpt Prod", "quantity": 50, "unit_price": 100.0, "tax_rate": 0}]
    )

    # BUG-10: Reject negative receipt (-5)
    with pytest.raises(ValueError, match="greater than zero"):
        receive_goods(po.id, {p_id: -5})

    # BUG-10: Reject receipt > remaining (55 > 50)
    with pytest.raises(ValueError, match="Cannot receive more"):
        receive_goods(po.id, {p_id: 55})

    # Receive partial 20
    r1 = receive_goods(po.id, {p_id: 20})
    assert r1["status"] == "partially_received"

    # BUG-11: Receive remaining 30 -> status must be 'received'
    r2 = receive_goods(po.id, {p_id: 30})
    assert r2["status"] == "received"

    # BUG-12: Reject any further receipt once status is 'received'
    with pytest.raises(ValueError, match="already"):
        receive_goods(po.id, {p_id: 5})
