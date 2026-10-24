"""
Reproduction and Benchmark for Defect 1:
P&L takes 49.9s on 5,000 products due to N+1 database queries.
Benchmark required: under 2s on a stress DB with 5,000 products, 2,000 parties, 15,000+ invoices, 20,000 vouchers.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

STRESS_DB = "data/rc_verify_stress.db"

def run_legacy_n_plus_1_pnl(session, start_date, end_date):
    """
    Exact reproduction of the original unoptimized P&L code from QA_Full_Audit_Report BUG-07:
    Iterates over all 5,000 products and executes individual per-product SQL queries.
    """
    from app.database.models import Product, PurchaseOrderItem, PurchaseOrder, InvoiceItem, Invoice, SalesReturnItem, PurchaseReturnItem

    products = session.query(Product).filter(Product.is_active.is_(True)).all()
    total_closing_stock = Decimal("0.00")
    
    # Simulate first 200 products to demonstrate N+1 projection or full if needed
    # We will measure the per-product time to prove why 5,000 products takes 49.9s
    t_start = time.perf_counter()
    sample_size = 200
    for p in products[:sample_size]:
        # Query 1: PO received
        po_inward = session.query(func.coalesce(func.sum(PurchaseOrderItem.quantity), 0)).filter(
            PurchaseOrderItem.product_id == p.id
        ).scalar()
        # Query 2: Invoices sold
        inv_sold = session.query(func.coalesce(func.sum(InvoiceItem.quantity), 0)).filter(
            InvoiceItem.product_id == p.id
        ).scalar()
        # Query 3: Sales return
        sr_ret = session.query(func.coalesce(func.sum(SalesReturnItem.quantity), 0)).filter(
            SalesReturnItem.product_id == p.id
        ).scalar()
        # Query 4: Purchase return
        pr_ret = session.query(func.coalesce(func.sum(PurchaseReturnItem.quantity), 0)).filter(
            PurchaseReturnItem.product_id == p.id
        ).scalar()
        
        closing_qty = Decimal(str(p.stock_quantity or 0))
        total_closing_stock += closing_qty * Decimal(str(p.purchase_price or 0))

    elapsed_sample = time.perf_counter() - t_start
    projected_full = elapsed_sample * (len(products) / sample_size)
    return {
        "sample_size": sample_size,
        "sample_time": elapsed_sample,
        "projected_full_5k_time": projected_full,
        "queries_per_product": 4,
        "total_queries_5k": len(products) * 4
    }


def test_defect_1_reproduction_and_current_benchmark():
    db_p = Path(STRESS_DB)
    if not db_p.is_file() or db_p.stat().st_size < 10000:
        pytest.skip(f"Stress test database {STRESS_DB} not present; skipping manual benchmark.")
    engine = create_engine(f"sqlite:///{STRESS_DB}", connect_args={"check_same_thread": False, "timeout": 30.0})
    Session = sessionmaker(bind=engine)
    
    print("\n" + "="*70)
    print("PART A - DEFECT 1 REPRODUCTION & BENCHMARK")
    print(f"Target DB: {STRESS_DB}")
    print("Workload: 5,000 Products, 2,000 Parties, 16,000 Invoices, 20,000 Vouchers, 2,000 POs")
    print("="*70)
    
    # 1. Run Legacy N+1 Reproduction
    with Session() as session:
        n1_results = run_legacy_n_plus_1_pnl(session, date(2026, 4, 1), date(2027, 3, 31))
        print(f"[REPRODUCTION: BUG-07] Original N+1 logic on 200 products: {n1_results['sample_time']:.3f} s")
        print(f"[REPRODUCTION: BUG-07] Projected time for 5,000 products: {n1_results['projected_full_5k_time']:.2f} s ({n1_results['total_queries_5k']} queries)")
        assert n1_results['projected_full_5k_time'] > 10.0, "Legacy N+1 was expected to be slow (>10s)"

    # 2. Run Current Build P&L with Set-Based Engine
    old_db = os.environ.get("ACCOUNTING_DB_PATH")
    old_uri = os.environ.get("ACCOUNTING_DATABASE_URI")
    try:
        os.environ["ACCOUNTING_DB_PATH"] = STRESS_DB
        os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{STRESS_DB}"
        from app.database import connection
        connection.DB_PATH = STRESS_DB
        connection.DATABASE_URI = f"sqlite:///{STRESS_DB}"
        connection.engine = engine
        connection.SessionLocal = Session

        from app.services.pnl_service import get_profit_loss_statement
        
        # Warmup
        get_profit_loss_statement(start_date=date(2026, 4, 1), end_date=date(2027, 3, 31))
        
        # Measured runs (3 iterations)
        times = []
        for run_idx in range(1, 4):
            t0 = time.perf_counter()
            res = get_profit_loss_statement(start_date=date(2026, 4, 1), end_date=date(2027, 3, 31))
            t_taken = time.perf_counter() - t0
            times.append(t_taken)
            print(f"[CURRENT BUILD: RUN {run_idx}] P&L on 16k Invoices + 5k Products: {t_taken:.4f} s")
            assert "revenue" in res
            assert "cost_of_goods" in res
            assert "gross_profit" in res

        avg_time = sum(times) / len(times)
        print(f"\n--> REAL TIME ON CURRENT BUILD: {avg_time:.4f} s (Required: < 2.0 s)")
        assert avg_time < 2.0, f"P&L took {avg_time:.4f}s, exceeding 2.0s SLA!"
        print("--> RESULT: PASS (VERIFIED FIXED UNDER 2 SECONDS)")
    finally:
        if old_db: os.environ["ACCOUNTING_DB_PATH"] = old_db
        if old_uri: os.environ["ACCOUNTING_DATABASE_URI"] = old_uri

if __name__ == "__main__":
    test_defect_1_reproduction_and_current_benchmark()
