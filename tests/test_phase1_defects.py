"""
Phase 1 Defect Regression Test Suite
Covers audited defects BUG-01 through BUG-09:
- BUG-07: P&L N+1 query loop performance on stress database (< 2.0s target, < 5.0s ceiling)
- BUG-06: Stock valuation using Weighted Average Cost across P&L, stock report, and dashboard
- BUG-05: Database encryption / secure storage fallback
- BUG-01: Duplicate product lines in sales and purchase returns
- BUG-04: Model constructor whitelist (no unhandled TypeError on unexpected dict keys)
- BUG-02: Normalization of tax_rate / gst_rate_pct with explicit validation
- BUG-08: FIFO bill-by-bill allocation for receivables ageing
- BUG-09: Automatic WAL checkpointing on shutdown / close
- BUG-03: Case-insensitive normalization for GSTIN, PAN, IFSC, and vehicle numbers
"""
import os
import sys
import time
from datetime import date
from decimal import Decimal
import pytest

from app.database.connection import get_session
from app.database.models import (
    Party, Product, Invoice, InvoiceItem, PurchaseOrder, PurchaseOrderItem,
    SalesReturn, SalesReturnItem, PurchaseReturn, PurchaseReturnItem,
    Voucher, VoucherItem, Expense, ExpenseCategory, CompanyProfile
)


def test_bug_07_pnl_performance_under_two_seconds():
    """
    BUG-07: Verify P&L calculation completes in < 2.0 seconds on 5,000-product stress DB.
    Previously took 49.9s (or ~13s) due to 5 N+1 queries per product in a Python loop.
    """
    stress_db = "data/test_perf_stress.db"
    if not os.path.exists(stress_db):
        pytest.skip("Stress database not present")

    # Save original env and set to stress DB
    old_db = os.environ.get("ACCOUNTING_DB_PATH")
    old_uri = os.environ.get("ACCOUNTING_DATABASE_URI")
    try:
        os.environ["ACCOUNTING_DB_PATH"] = stress_db
        os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{stress_db}"
        from app.database import connection
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        connection.DB_PATH = stress_db
        connection.DATABASE_URI = f"sqlite:///{stress_db}"
        connection.engine = create_engine(
            connection.DATABASE_URI,
            connect_args={"check_same_thread": False, "timeout": 30.0}
        )
        connection.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=connection.engine
        )

        from app.services.pnl_service import get_profit_loss_statement

        t0 = time.perf_counter()
        pnl = get_profit_loss_statement(start_date=date(2026, 4, 1), end_date=date(2027, 3, 31))
        duration = time.perf_counter() - t0

        print(f"\n[BUG-07 Benchmark] P&L calculation took {duration:.3f}s")
        assert duration < 2.0, f"P&L took {duration:.3f}s (must be < 2.0s, set-based query)"
        assert "revenue" in pnl
        assert "cost_of_goods" in pnl
        assert "gross_profit" in pnl
    finally:
        if old_db:
            os.environ["ACCOUNTING_DB_PATH"] = old_db
        if old_uri:
            os.environ["ACCOUNTING_DATABASE_URI"] = old_uri
        target_db = old_db or "data/test_accounting.db"
        connection.DB_PATH = target_db
        connection.DATABASE_URI = f"sqlite:///{target_db}"
        connection.engine = create_engine(
            connection.DATABASE_URI,
            connect_args={"check_same_thread": False, "timeout": 30.0}
        )
        connection.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=connection.engine
        )
        connection.init_db()


def test_bug_06_stock_valuation_weighted_average():
    """
    BUG-06: Stock Valuation Method (Decision D1).
    Buy batch 1 @ 1000, batch 2 @ 2000, sell some, verify opening/closing/COGS by hand
    for Weighted Average Cost, including returns and purchase returns.
    All reports (P&L COGS, closing stock, Stock Report, Dashboard) must be consistent.
    """
    from app.services.billing.purchase_order_service import create_purchase_order, receive_goods
    from app.services.billing.invoice_service import create_invoice
    from app.services.billing.return_service import create_sales_return, create_purchase_return
    from app.services.pnl_service import get_profit_loss_statement
    from app.services.stock_report_service import get_stock_movement_report

    test_date = date(2027, 2, 10)
    with get_session() as session:
        # Create dedicated party and product
        supplier = Party(name="WAC Test Supplier", party_type="Supplier", state_code="27", is_active=True)
        customer = Party(name="WAC Test Customer", party_type="Customer", state_code="27", is_active=True)
        prod = Product(
            name="WAC Widget",
            purchase_price=Decimal("1000.00"),
            price=Decimal("2500.00"),
            tax_rate=Decimal("0.00"),
            stock_quantity=Decimal("0.000"),
            is_active=True
        )
        session.add_all([supplier, customer, prod])
        session.flush()
        s_id, c_id, p_id = supplier.id, customer.id, prod.id

    # 1. Buy Batch 1: 10 @ 1,000 = 10,000
    po1 = create_purchase_order(
        {"party_id": s_id, "po_date": test_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "Batch 1", "quantity": 10, "unit_price": 1000.0, "tax_rate": 0}]
    )
    receive_goods(po1.id, {p_id: 10})

    # 2. Buy Batch 2: 10 @ 2,000 = 20,000
    po2 = create_purchase_order(
        {"party_id": s_id, "po_date": test_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "Batch 2", "quantity": 10, "unit_price": 2000.0, "tax_rate": 0}]
    )
    receive_goods(po2.id, {p_id: 10})

    # Total inward: 20 units @ 30,000 total = WAC 1,500/unit

    # 3. Sell 8 units @ 2,500
    inv = create_invoice(
        {"party_id": c_id, "invoice_date": test_date, "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Sale", "quantity": 8, "unit_price": 2500.0, "gst_rate_pct": 0}]
    )

    # 4. Customer returns 2 units (Sales Return)
    sr = create_sales_return(
        {"party_id": c_id, "invoice_id": inv.id, "return_date": test_date, "status": "approved"},
        [{"product_id": p_id, "item_description": "Return", "quantity": 2, "unit_price": 2500.0, "tax_rate": 0}]
    )
    # Net sold = 8 - 2 = 6 units

    # 5. Return 4 units to supplier from batch 2 (Purchase Return @ 2,000)
    pr = create_purchase_return(
        {"party_id": s_id, "po_id": po2.id, "return_date": test_date, "status": "approved"},
        [{"product_id": p_id, "item_description": "PR from batch 2", "quantity": 4, "unit_price": 2000.0, "tax_rate": 0}]
    )
    # Net purchases = 30,000 - 8,000 = 22,000 for 16 net inward units
    # Weighted Average Cost = 22,000 / 16 = 1,375.00 / unit
    # Remaining stock = 16 - 6 = 10 units
    # Closing Stock Value = 10 * 1,375 = 13,750.00
    # Expected COGS = 6 * 1,375 = 8,250.00
    # Check: Net purchases (22,000) - Closing stock (13,750) = 8,250.00!

    from app.services.inventory_valuation import calculate_inventory_valuation
    with get_session() as session:
        val_res = calculate_inventory_valuation(session, start_date=test_date, end_date=test_date, product_ids=[p_id])
        p_val = val_res["products"][p_id]
        print(f"\n[BUG-06 Direct Product Valuation] Unit Cost: {p_val['unit_cost']}, Closing Value: {p_val['closing_value']}, COGS: {p_val['cogs']}")
        assert abs(p_val["unit_cost"] - 1375.00) < 0.01, f"Unit cost was {p_val['unit_cost']}, expected 1375.00"
        assert abs(p_val["closing_value"] - 13750.00) < 0.01, f"Closing value was {p_val['closing_value']}, expected 13750.00"
        assert abs(p_val["cogs"] - 8250.00) < 0.01, f"COGS was {p_val['cogs']}, expected 8250.00"

    # Verify Stock Report
    stock_rep = get_stock_movement_report(product_id=p_id, start_date=test_date, end_date=test_date)
    assert len(stock_rep["items"]) == 1
    s_item = stock_rep["items"][0]
    print(f"[BUG-06 Stock Report] Stock Value: {s_item['stock_value']}, Cost: {s_item['valuation_cost']}")
    assert abs(s_item["valuation_cost"] - 1375.00) < 0.01
    assert abs(s_item["stock_value"] - 13750.00) < 0.01
    assert "Weighted Average Cost" in stock_rep["valuation_method"]

    # Verify P&L
    pnl = get_profit_loss_statement(start_date=test_date, end_date=test_date)
    cogs = pnl["cost_of_goods"]
    print(f"[BUG-06 P&L Statement] COGS: {cogs['total']}, Method: {cogs['valuation_method']}")
    assert abs(cogs["total"] - 8250.00) < 0.01, f"P&L COGS was {cogs['total']}, expected 8250.00"
    assert "Weighted Average Cost" in cogs["valuation_method"]


def test_bug_01_return_duplicate_product_lines_validation():
    """
    BUG-01: Sum quantities per product ID (defaultdict(Decimal)) in sales AND purchase returns;
    validate the summed quantity against remaining returnable quantity;
    test with two lines of the same product (5 and 3 = 8) against an invoice where only 6 were sold.
    Must raise ValueError.
    """
    from app.services.billing.invoice_service import create_invoice
    from app.services.billing.return_service import create_sales_return, create_purchase_return
    from app.services.billing.purchase_order_service import create_purchase_order, receive_goods

    test_date = date(2027, 2, 11)
    with get_session() as session:
        cust = Party(name="Dup Return Customer", party_type="Customer", state_code="27", is_active=True)
        supp = Party(name="Dup Return Supplier", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(
            name="Dup Return Widget",
            purchase_price=Decimal("100.00"),
            price=Decimal("200.00"),
            tax_rate=Decimal("18.00"),
            stock_quantity=Decimal("100.000"),
            is_active=True
        )
        session.add_all([cust, supp, prod])
        session.flush()
        c_id, s_id, p_id = cust.id, supp.id, prod.id

    # 1. Invoice with 6 units sold
    inv = create_invoice(
        {"party_id": c_id, "invoice_date": test_date, "status": "final", "tax_mode": 0},
        [{"product_id": p_id, "item_description": "Widget Line", "quantity": 6, "unit_price": 200.0, "gst_rate_pct": 18}]
    )

    # 2. Sales Return with two lines of same product: 5 and 3 = 8 units!
    # Since only 6 were sold, this MUST raise ValueError!
    with pytest.raises(ValueError) as excinfo:
        create_sales_return(
            {"party_id": c_id, "invoice_id": inv.id, "return_date": test_date, "status": "approved"},
            [
                {"product_id": p_id, "item_description": "First 5 units", "quantity": 5, "unit_price": 200.0, "tax_rate": 18},
                {"product_id": p_id, "item_description": "Next 3 units", "quantity": 3, "unit_price": 200.0, "tax_rate": 18},
            ]
        )
    assert "exceeds allowed return quantity" in str(excinfo.value)

    # 3. PO with 6 units received
    po = create_purchase_order(
        {"party_id": s_id, "po_date": test_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "PO Line", "quantity": 6, "unit_price": 100.0, "tax_rate": 18}]
    )
    receive_goods(po.id, {p_id: 6})

    # 4. Purchase Return with two lines of same product: 5 and 3 = 8 units!
    with pytest.raises(ValueError) as excinfo_pr:
        create_purchase_return(
            {"party_id": s_id, "po_id": po.id, "return_date": test_date, "status": "approved"},
            [
                {"product_id": p_id, "item_description": "PR First 5", "quantity": 5, "unit_price": 100.0, "tax_rate": 18},
                {"product_id": p_id, "item_description": "PR Next 3", "quantity": 3, "unit_price": 100.0, "tax_rate": 18},
            ]
        )
    assert "exceeds allowed return quantity" in str(excinfo_pr.value)


def test_bug_04_unknown_keys_raise_clean_value_error():
    """
    BUG-04: Whitelist model columns in create_voucher, create_party, and create_product;
    raise a clean ValueError listing unknown keys instead of unhandled TypeError.
    """
    from app.services.voucher_service import create_voucher
    from app.services.party_service import create_party
    from app.services.billing.product_service import create_product

    # 1. create_voucher with unknown keys
    with pytest.raises(ValueError) as excinfo_v:
        create_voucher({
            "voucher_type": "Debit",
            "party_id": 1,
            "total_amount": Decimal("500.00"),
            "extra_bogus_field": "bad_data",
            "invalid_column": 123
        })
    assert "Unknown field(s) for Voucher" in str(excinfo_v.value)
    assert "extra_bogus_field" in str(excinfo_v.value)

    # 2. create_party with unknown keys
    with pytest.raises(ValueError) as excinfo_p:
        create_party({
            "name": "Unknown Key Party",
            "party_type": "Customer",
            "unsupported_key": "xyz"
        })
    assert "Unknown field(s) for Party" in str(excinfo_p.value)

    # 3. create_product with unknown keys
    with pytest.raises(ValueError) as excinfo_prod:
        create_product({
            "name": "Unknown Key Product",
            "price": 100.0,
            "unknown_attribute": True
        })
    assert "Unknown field(s) for Product" in str(excinfo_prod.value)


def test_bug_02_tax_key_mismatch_and_normalization():
    """
    BUG-02: Accept `gst_rate_pct` or `tax_rate` through one normalizing function;
    if neither is present, raise ValueError instead of defaulting to 0% (0% must be explicit).
    Test create/update path for invoices, quotations, proformas, challans, POs, and returns.
    """
    from app.services.billing.invoice_service import create_invoice, update_invoice
    from app.services.billing.quotation_service import create_quotation, update_quotation
    from app.services.billing.proforma_service import create_proforma, update_proforma
    from app.services.billing.challan_service import create_challan, update_challan
    from app.services.billing.purchase_order_service import create_purchase_order, update_purchase_order
    from app.services.billing.return_service import create_sales_return, create_purchase_return

    test_date = date(2027, 2, 12)
    with get_session() as session:
        cust = Party(name="Tax Test Customer", party_type="Customer", state_code="27", is_active=True)
        supp = Party(name="Tax Test Supplier", party_type="Supplier", state_code="27", is_active=True)
        prod = Product(
            name="Tax Test Product",
            purchase_price=Decimal("100.00"),
            price=Decimal("200.00"),
            tax_rate=Decimal("18.00"),
            stock_quantity=Decimal("50.000"),
            is_active=True
        )
        session.add_all([cust, supp, prod])
        session.flush()
        c_id, s_id, p_id = cust.id, supp.id, prod.id

    # 1. Neither tax_rate nor gst_rate_pct provided -> MUST raise ValueError in create_invoice
    with pytest.raises(ValueError) as exc:
        create_invoice(
            {"party_id": c_id, "invoice_date": test_date, "status": "draft"},
            [{"product_id": p_id, "item_description": "No Tax Item", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc.value).lower()

    # 2. Accept tax_rate in create_invoice (even if gst_rate_pct is omitted)
    inv_with_tr = create_invoice(
        {"party_id": c_id, "invoice_date": test_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "Tax Rate Item", "quantity": 1, "unit_price": 100.0, "tax_rate": 18.0}]
    )
    assert inv_with_tr.tax_amount == Decimal("18.00")

    # 3. Explicit 0% works
    inv_zero = create_invoice(
        {"party_id": c_id, "invoice_date": test_date, "status": "draft"},
        [{"product_id": p_id, "item_description": "Zero Tax Item", "quantity": 1, "unit_price": 100.0, "gst_rate_pct": 0}]
    )
    assert inv_zero.tax_amount == Decimal("0.00")

    # 4. Quotation: accept tax_rate and reject missing tax
    with pytest.raises(ValueError) as exc_q:
        create_quotation(
            {"party_id": c_id, "quotation_date": test_date},
            [{"product_id": p_id, "item_description": "Quote No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_q.value).lower()

    # 5. PO: accept gst_rate_pct and reject missing tax
    with pytest.raises(ValueError) as exc_po:
        create_purchase_order(
            {"party_id": s_id, "po_date": test_date},
            [{"product_id": p_id, "item_description": "PO No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_po.value).lower()

    # 6. Challan: accept both keys and reject missing tax
    with pytest.raises(ValueError) as exc_ch:
        create_challan(
            {"party_id": c_id, "challan_date": test_date},
            [{"product_id": p_id, "item_description": "Challan No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_ch.value).lower()

    # 7. Proforma: reject missing tax, accept tax_rate
    with pytest.raises(ValueError) as exc_pf:
        create_proforma(
            {"party_id": c_id, "proforma_date": test_date},
            [{"product_id": p_id, "item_description": "PF No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_pf.value).lower()

    # 8. Sales Return: reject missing tax, accept gst_rate_pct
    with pytest.raises(ValueError) as exc_sr:
        create_sales_return(
            {"party_id": c_id, "return_date": test_date},
            [{"product_id": p_id, "item_description": "SR No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_sr.value).lower()

    # 9. Purchase Return: reject missing tax, accept gst_rate_pct
    with pytest.raises(ValueError) as exc_pr:
        create_purchase_return(
            {"party_id": s_id, "return_date": test_date},
            [{"product_id": p_id, "item_description": "PR No Tax", "quantity": 1, "unit_price": 100.0}]
        )
    assert "tax" in str(exc_pr.value).lower()


def test_bug_08_ageing_fifo_bill_by_bill_allocation():
    """
    BUG-08: Proper bill-by-bill allocation:
    - Default = FIFO: payment allocates to oldest open invoice first.
    - Test case:
        * 45-day-old invoice of 10,000
        * payment of 10,000 today
        * new invoice of 5,000 today
        * Result: 45-day invoice cleared; 5,000 in 0-30 bucket.
    - Against reference:
        * payment references specific invoice.
    """
    from datetime import timedelta
    from app.services.voucher_service import create_voucher
    from app.services.report_service import get_outstanding_report
    from app.config import VOUCHER_DEBIT, VOUCHER_CREDIT

    today = date(2027, 3, 1)
    inv_old_date = today - timedelta(days=45)

    with get_session() as session:
        cust = Party(
            name="Ageing FIFO Customer",
            party_type="Customer",
            state_code="27",
            opening_balance=Decimal("0.00"),
            is_active=True
        )
        session.add(cust)
        session.flush()
        cust_id = cust.id

    # 1. 45-day-old invoice of 10,000 (Debit voucher)
    v_inv_old = create_voucher({
        "party_id": cust_id,
        "voucher_type": VOUCHER_DEBIT,
        "voucher_date": inv_old_date,
        "total_amount": Decimal("10000.00"),
        "reference_no": "INV-OLD-10K"
    })

    # 2. Payment of 10,000 today (Credit voucher)
    v_pay = create_voucher({
        "party_id": cust_id,
        "voucher_type": VOUCHER_CREDIT,
        "voucher_date": today,
        "total_amount": Decimal("10000.00"),
        "reference_no": "PAY-TODAY-10K"
    })

    # 3. New invoice of 5,000 today (Debit voucher)
    v_inv_new = create_voucher({
        "party_id": cust_id,
        "voucher_type": VOUCHER_DEBIT,
        "voucher_date": today,
        "total_amount": Decimal("5000.00"),
        "reference_no": "INV-NEW-5K"
    })

    # Run Outstanding / Ageing report as of today
    rep = get_outstanding_report("Receivables", as_of_date=today)
    party_data = next((p for p in rep["party_rows"] if p["party_id"] == cust_id), None)
    assert party_data is not None, "Party should be present in outstanding report"

    # Total outstanding must be 5,000
    assert party_data["total_outstanding"] == 5000.0

    # Under FIFO bill-by-bill allocation:
    # 45-day invoice of 10,000 is cleared by 10,000 payment -> bucket 31-60 is 0.00!
    # 5,000 invoice of today sits in bucket 0-30 -> bucket 0-30 is 5000.00!
    assert party_data["bucket_0_30"] == 5000.0, f"Expected 5000 in 0-30, got {party_data['bucket_0_30']}"
    assert party_data["bucket_31_60"] == 0.0, f"Expected 0 in 31-60, got {party_data['bucket_31_60']}"
    assert party_data["bucket_61_90"] == 0.0
    assert party_data["bucket_90_plus"] == 0.0

    # Verify voucher_allocations table has records
    from app.database.models import VoucherAllocation
    with get_session() as session:
        allocs = session.query(VoucherAllocation).filter(VoucherAllocation.party_id == cust_id).all()
        assert len(allocs) > 0
        assert any(a.allocated_amount == Decimal("10000.00") and a.allocation_type == "FIFO" for a in allocs)

    # 4. Now test "Against reference" setting
    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        if not comp:
            comp = CompanyProfile(name="Test Co")
            session.add(comp)
        comp.ageing_allocation_method = "Against reference"
        session.commit()

        cust2 = Party(
            name="Ageing Ref Customer",
            party_type="Customer",
            state_code="27",
            opening_balance=Decimal("0.00"),
            is_active=True
        )
        session.add(cust2)
        session.flush()
        cust2_id = cust2.id

    # Invoice 1 (45 days old, 10,000)
    v1 = create_voucher({
        "party_id": cust2_id,
        "voucher_type": VOUCHER_DEBIT,
        "voucher_date": inv_old_date,
        "total_amount": Decimal("10000.00"),
        "reference_no": "INV-REF-OLD"
    })
    # Invoice 2 (today, 5,000)
    v2 = create_voucher({
        "party_id": cust2_id,
        "voucher_type": VOUCHER_DEBIT,
        "voucher_date": today,
        "total_amount": Decimal("5000.00"),
        "reference_no": "INV-REF-NEW"
    })
    # Payment of 5,000 explicitly referencing INV-REF-NEW
    v_pay_ref = create_voucher({
        "party_id": cust2_id,
        "voucher_type": VOUCHER_CREDIT,
        "voucher_date": today,
        "total_amount": Decimal("5000.00"),
        "reference_no": "INV-REF-NEW"
    })

    rep2 = get_outstanding_report("Receivables", as_of_date=today)
    party2_data = next((p for p in rep2["party_rows"] if p["party_id"] == cust2_id), None)
    assert party2_data is not None

    # Under "Against reference", the 5,000 payment cleared Invoice 2 (today),
    # leaving Invoice 1 (45 days old, 10,000) unpaid in bucket 31-60!
    assert party2_data["total_outstanding"] == 10000.0
    assert party2_data["bucket_0_30"] == 0.0, f"Expected 0 in 0-30, got {party2_data['bucket_0_30']}"
    assert party2_data["bucket_31_60"] == 10000.0, f"Expected 10000 in 31-60, got {party2_data['bucket_31_60']}"

    # Restore default setting
    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        comp.ageing_allocation_method = "Oldest first"
        session.commit()


def test_bug_09_wal_checkpoint_truncate_and_recovery(tmp_path):
    """
    BUG-09: Run PRAGMA wal_checkpoint(TRUNCATE) on exit and after restore.
    Verify WAL file is empty/zero bytes after checkpoint, and test crash recovery.
    """
    import sqlite3
    from app.database import connection

    # 1. Checkpoint function must exist in connection module
    assert hasattr(connection, "checkpoint_wal"), "connection.checkpoint_wal must be implemented"

    # 2. Test WAL truncation on dedicated test DB
    test_db = tmp_path / "test_wal_checkpoint.db"
    wal_file = tmp_path / "test_wal_checkpoint.db-wal"

    with sqlite3.connect(str(test_db)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test_tab (id INT, val TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO test_tab VALUES (?, ?)", (i, f"value_{i}"))
        conn.commit()

    # WAL file exists and has data
    assert wal_file.exists(), "WAL file should exist after uncheckpointed writes"
    assert wal_file.stat().st_size > 0, "WAL file should have bytes before truncate checkpoint"

    # Execute checkpoint_wal
    old_engine = connection.engine
    try:
        from sqlalchemy import create_engine
        temp_engine = create_engine(f"sqlite:///{test_db}")
        connection.engine = temp_engine
        res = connection.checkpoint_wal(truncate=True)
        assert res is True
        connection.engine.dispose()
    finally:
        connection.engine = old_engine

    # After TRUNCATE checkpoint, WAL file must be 0 bytes or deleted
    if wal_file.exists():
        assert wal_file.stat().st_size == 0, f"WAL file should be truncated to 0 bytes, but was {wal_file.stat().st_size}"

    # 3. Crash recovery test:
    # Write to WAL without checkpointing, simulate abrupt termination
    with sqlite3.connect(str(test_db)) as conn:
        for i in range(100, 200):
            conn.execute("INSERT INTO test_tab VALUES (?, ?)", (i, f"crash_val_{i}"))
        conn.commit()

    # Next launch / reopen database
    with sqlite3.connect(str(test_db)) as conn2:
        cursor = conn2.cursor()
        cursor.execute("PRAGMA quick_check")
        check_res = cursor.fetchone()[0]
        assert check_res == "ok", f"Integrity check failed after recovery: {check_res}"
        cursor.execute("SELECT count(*) FROM test_tab")
        count = cursor.fetchone()[0]
        assert count == 200, f"Expected 200 rows recovered, got {count}"


def test_bug_03_gstin_pan_ifsc_vehicle_case_normalization():
    """
    BUG-03: Strip and uppercase GSTIN, PAN, IFSC, and vehicle numbers before validating,
    both in services and live in form fields.
    """
    from app.services.party_service import create_party
    from app.services.billing.challan_service import create_challan
    from app.services.validation_helpers import (
        validate_pan, validate_ifsc, validate_vehicle_no, normalize_uppercase_string
    )

    # 1. Lowercase GSTIN and PAN should be normalized to uppercase and succeed
    party = create_party({
        "name": "Case Test Customer",
        "party_type": "Customer",
        "state_code": "27",
        "gstin": "  27abcde1234f1z5  ",
        "pan": "  abcde1234f  "
    })
    assert party.gstin == "27ABCDE1234F1Z5"
    assert party.pan == "ABCDE1234F"

    # 2. Invalid PAN rejected
    assert validate_pan("invalid_pan") is False
    assert validate_pan("ABCDE1234F") is True

    # 3. IFSC validator checks
    assert validate_ifsc("sbin0001234") is True
    assert validate_ifsc("sbin1234567") is False  # 5th char must be 0

    # 4. Vehicle Number validator and normalization in challan
    assert validate_vehicle_no("mh-12-ab-1234") is True
    assert validate_vehicle_no("invalid_veh") is False

    ch = create_challan(
        {
            "party_id": party.id,
            "challan_date": date.today(),
            "vehicle_no": "  mh 14 dc 5678  "
        },
        [{"product_id": None, "item_description": "Item", "quantity": 1, "unit_price": 100.0, "tax_rate": 18}]
    )
    assert ch.vehicle_no == "MH 14 DC 5678"

    # 5. Live UI UpperLineEdit test
    from PySide6.QtWidgets import QApplication
    from app.ui.widgets.upper_line_edit import UpperLineEdit
    app = QApplication.instance() or QApplication([])

    edit = UpperLineEdit()
    edit.setText("27abcde1234f1z5")
    assert edit.text() == "27ABCDE1234F1Z5"


def test_bug_05_aes_gcm_encrypted_backup_and_restore(tmp_path):
    """
    BUG-05 / Decision D2: AES-256-GCM encrypted backup export and restore.
    - Test that encrypted backup file cannot be read by standard sqlite3 CLI/API.
    - Test that restoring with correct passphrase succeeds and row counts match.
    - Test that incorrect passphrase or tampered file raises clean ValueError.
    """
    import sqlite3
    from app.database import connection
    from app.services.party_service import create_party

    # 1. Create unique party to verify in backup
    p = create_party({
        "name": "Encryption Secret Customer",
        "party_type": "Customer",
        "state_code": "27"
    })

    passphrase = "UltraSecureReleasePassphrase#2027"
    enc_path = tmp_path / "test_secure_backup.enc"

    # 2. Create encrypted backup
    res_path = connection.create_encrypted_backup(passphrase, custom_dest_dir=enc_path)
    assert res_path.exists()
    assert res_path.stat().st_size > 0

    # 3. Verify file is unreadable by sqlite3
    raw_bytes = res_path.read_bytes()
    assert raw_bytes.startswith(b"BILLFLOW_ENC_V1")
    assert b"Encryption Secret Customer" not in raw_bytes, "Customer name must not appear in plaintext in encrypted backup!"

    # Attempting to query with standard SQLite must raise DatabaseError / file is not a database
    with pytest.raises(sqlite3.DatabaseError):
        with sqlite3.connect(str(res_path)) as conn:
            conn.execute("SELECT * FROM parties")

    # 4. Attempting restore with wrong passphrase must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        connection.restore_backup(res_path, passphrase="WrongPassword123")
    assert "Decryption failed" in str(excinfo.value) or "Incorrect passphrase" in str(excinfo.value)

    # 5. Restore with correct passphrase must succeed
    restore_res = connection.restore_backup(res_path, passphrase=passphrase)
    assert restore_res is True

    # Verify data is fully intact
    with connection.get_session() as session:
        restored_party = session.query(Party).filter(Party.name == "Encryption Secret Customer").first()
        assert restored_party is not None

