"""
Phase 7: Performance, High-Volume Stress & Responsiveness Benchmark
Tests:
  1. Generate high-volume dataset:
     - 2,000 Parties
     - 5,000 Products
     - 5,000 Invoices (with items)
     - 20,000 Vouchers
  2. Timings & Memory for:
     - Party list query (2,000 records)
     - Party search by name query
     - Product catalog list query (5,000 records)
     - Product search by barcode/name query
     - Invoice list query (5,000 records)
     - Dashboard KPIs calculation
     - Day Book report query
     - Trial Balance calculation
     - Profit & Loss calculation
     - GSTR-1 calculation
     - 150-Item Tax Invoice PDF Generation
     - 5,000-Row Excel Export
     - Database Backup creation
     - Database Restore
  3. Memory Growth Test: 50 open/close/query cycles
  4. Flag operations > 2.0s threshold
"""
import os
import sys
import time
import json
import psutil
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Use dedicated high-volume stress database
PERF_DB = r"c:\Users\surjy\OneDrive\Desktop\Accounting Software\data\test_perf_stress.db"
os.environ["ACCOUNTING_DB_PATH"] = PERF_DB
os.environ["ACCOUNTING_DATABASE_URI"] = "sqlite:///" + PERF_DB.replace("\\", "/")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["HEADLESS_TESTING"] = "1"

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.database.connection import init_db, get_session, create_backup, restore_backup, engine
from app.database.models import Party, Product, Invoice, InvoiceItem, Voucher, VoucherItem
from app.services.party_service import get_all_parties
from app.services.billing.product_service import get_all_products
from app.services.billing.invoice_service import get_all_invoices
from app.services.billing.invoice_pdf_generator import generate_invoice_pdf
from app.services.report_service import (
    get_dashboard_kpis, get_day_book, get_trial_balance, get_gst_summary
)
from app.services.pnl_service import get_profit_loss_statement
from app.services.export_service import export_daybook_excel

perf_results = []

def record_metric(operation, data_size, duration_sec, memory_mb, cpu_pct=0.0, freeze=False):
    flag = "SLOW (>2.0s)" if duration_sec > 2.0 else "NORMAL"
    record = {
        "operation": operation,
        "data_size": str(data_size),
        "time_seconds": round(duration_sec, 3),
        "memory_mb": round(memory_mb, 2),
        "cpu_percent": round(cpu_pct, 1),
        "freeze": "Yes" if freeze else "No",
        "flag": flag
    }
    perf_results.append(record)
    print(f"[{flag}] {operation} ({data_size}) -> {duration_sec:.3f}s | Mem: {memory_mb:.1f} MB | CPU: {cpu_pct:.1f}%")

def generate_high_volume_data():
    print(f"\n--- 1. Generating High-Volume Test Data in {PERF_DB} ---")
    if Path(PERF_DB).exists():
        try:
            Path(PERF_DB).unlink()
        except Exception:
            pass
            
    engine.dispose()
    init_db()
    
    proc = psutil.Process()
    t0 = time.time()
    
    # 1. 2,000 Parties
    print("Generating 2,000 Parties...")
    parties_data = []
    for i in range(1, 2001):
        ptype = "Customer" if i % 2 == 0 else "Supplier"
        st = "27" if i % 3 == 0 else "24"
        parties_data.append((
            f"PRT-{i:05d}", f"Stress Test Party {i:05d}", ptype,
            f"{st}ABCDE{i:04d}F1Z5", f"98200{i:05d}", f"Stress Address line {i}",
            "Mumbai" if st == "27" else "Ahmedabad", "Maharashtra" if st == "27" else "Gujarat",
            st, 0.0, "Dr", 1, datetime.now(), datetime.now()
        ))
        
    # 2. 5,000 Products
    print("Generating 5,000 Products...")
    products_data = []
    gst_slabs = [0.0, 5.0, 12.0, 18.0, 28.0]
    units = ["PCS", "KGS", "MTR", "BOX", "TON"]
    for i in range(1, 5001):
        slab = gst_slabs[i % len(gst_slabs)]
        u = units[i % len(units)]
        products_data.append((
            f"BAR-STRESS-{i:05d}", f"Bulk Test Product Item {i:05d}",
            f"720{i%10}00", u, 750.0 + (i % 300), 500.0 + (i % 200), slab,
            100.0, 10.0, 1, datetime.now(), datetime.now()
        ))
        
    # 3. 5,000 Invoices & Items
    print("Generating 5,000 Invoices & Items...")
    invoices_data = []
    items_data = []
    base_date = date(2025, 4, 1)
    for i in range(1, 5001):
        inv_dt = base_date + timedelta(days=(i % 300))
        party_id = (i % 2000) + 1
        subtotal = 10000.0
        tax = 1800.0
        total = 11800.0
        invoices_data.append((
            i, f"INV/2025-26/STR-{i:05d}", inv_dt, party_id,
            subtotal, 900.0, 900.0, 0.0, tax, total,
            "final", "Regular B2B Sale",
            datetime.now(), datetime.now()
        ))
        items_data.append((
            i, (i % 5000) + 1, f"Bulk Test Product Item {(i % 5000) + 1:05d}",
            "720400", "PCS", 10.0, 1000.0, 0.0, 10000.0, 18.0, 900.0, 900.0, 0.0, 11800.0
        ))
        
    # 4. 20,000 Vouchers
    print("Generating 20,000 Vouchers...")
    vouchers_data = []
    v_types = ["Receipt", "Payment", "Debit", "Credit", "Journal"]
    for i in range(1, 20001):
        v_dt = base_date + timedelta(days=(i % 300))
        vt = v_types[i % len(v_types)]
        party_id = (i % 2000) + 1
        amt = 5000.0 + (i % 1000)
        dr_amt = amt if vt in ["Debit", "Payment"] else 0.0
        cr_amt = amt if vt in ["Credit", "Receipt"] else 0.0
        if vt == "Journal":
            dr_amt = amt
            cr_amt = amt
        vouchers_data.append((
            i, f"VCH-STR-{i:06d}", v_dt, vt, party_id, amt,
            dr_amt, cr_amt, amt, 0.0, 0.0, 0.0, 0.0, f"Voucher entry {i}", datetime.now(), datetime.now()
        ))

    # Direct fast SQLite insert inside single transaction
    raw_conn = sqlite3.connect(PERF_DB)
    cur = raw_conn.cursor()
    cur.execute("PRAGMA synchronous = OFF")
    cur.execute("PRAGMA journal_mode = WAL")
    
    cur.executemany("""
        INSERT INTO parties (code, name, party_type, gstin, phone, address, city, state, state_code, opening_balance, opening_balance_type, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, parties_data)
    
    cur.executemany("""
        INSERT INTO products (barcode, name, hsn_code, unit, price, purchase_price, tax_rate, stock_quantity, low_stock_threshold, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products_data)
    
    cur.executemany("""
        INSERT INTO invoices (id, invoice_number, invoice_date, party_id, subtotal, cgst_total, sgst_total, igst_total, tax_amount, total_amount, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, invoices_data)
    
    cur.executemany("""
        INSERT INTO invoice_items (invoice_id, product_id, item_description, hsn_code, unit, quantity, unit_price, discount_pct, taxable_value, gst_rate_pct, cgst_amount, sgst_amount, igst_amount, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, items_data)
    
    cur.executemany("""
        INSERT INTO vouchers (id, voucher_number, voucher_date, voucher_type, party_id, total_amount, debit_amount, credit_amount, amount_untaxed, cgst_amount, sgst_amount, igst_amount, total_tax, narration, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, vouchers_data)
    
    raw_conn.commit()
    raw_conn.close()
    
    gen_time = time.time() - t0
    mem_info = proc.memory_info().rss / (1024 * 1024)
    print(f"--- Data Generation Complete in {gen_time:.2f}s! Memory: {mem_info:.1f} MB ---\n")
    record_metric("Dataset Generation (32k+ records)", "2k parties, 5k products, 5k invoices, 20k vouchers", gen_time, mem_info)

def benchmark_queries_and_reports():
    proc = psutil.Process()
    print("--- 2. Benchmarking Queries and Reports ---")
    
    # A. Party List (2,000 parties)
    t0 = time.time()
    parties = get_all_parties(active_only=False)
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("List All Parties Query", f"{len(parties)} rows", dur, mem)
    
    # B. Party Search (Substring search across 2,000 parties)
    t0 = time.time()
    found_parties = get_all_parties(search_query="Party 015")
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Search Parties (Substring)", f"{len(found_parties)} matches", dur, mem)
    
    # C. Product List (5,000 products)
    t0 = time.time()
    products = get_all_products(active_only=False)
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("List All Products Query", f"{len(products)} rows", dur, mem)
    
    # D. Invoices List (5,000 invoices)
    t0 = time.time()
    invoices = get_all_invoices(limit=5000)
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("List All Invoices Query", f"{len(invoices)} rows", dur, mem)
    
    # E. Dashboard KPIs (Aggregates across all 5,000 invoices and vouchers)
    t0 = time.time()
    kpis = get_dashboard_kpis()
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Dashboard KPIs Aggregation", "Full Dataset", dur, mem)
    
    # F. Day Book Report (20,000 vouchers date range query)
    t0 = time.time()
    db_report = get_day_book(from_date=date(2025, 4, 1), to_date=date(2025, 4, 30))
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Day Book Report (30-day range)", f"{len(db_report.get('rows', []))} entries", dur, mem)
    
    # G. Trial Balance (Heavy computation across 20,000 voucher lines)
    t0 = time.time()
    tb_data = get_trial_balance(to_date=date(2025, 12, 31))
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Trial Balance Computation", f"{len(tb_data.get('rows', []))} accounts", dur, mem)
    
    # H. Profit & Loss Report
    t0 = time.time()
    pnl = get_profit_loss_statement(start_date=date(2025, 4, 1), end_date=date(2025, 12, 31))
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("P&L Report Calculation", "9-Month FY Period", dur, mem)
    
    # I. GSTR-1 Report (Aggregating 5,000 invoices B2B slabs)
    t0 = time.time()
    gstr1 = get_gst_summary(from_date=date(2025, 4, 1), to_date=date(2025, 12, 31), report_type="Sales")
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("GSTR-1 Report Aggregation", f"{len(gstr1.get('rows', []))} rows", dur, mem)

def benchmark_exports_and_pdf():
    proc = psutil.Process()
    print("\n--- 3. Benchmarking Heavy PDF & Excel Exports ---")
    
    # A. 150-Item Tax Invoice PDF Generation (Stress Document)
    out_pdf = ROOT_DIR / "scratch" / "audit" / "invoice_150_items_stress.pdf"
    out_pdf = ROOT_DIR / "scratch" / "audit" / "invoice_150_items_stress.pdf"
    comp_dict = {
        "name": "BillFlow Test Enterprise Pvt Ltd",
        "legal_name": "BillFlow Test Enterprise Pvt Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "address": "Plot 101, MIDC",
        "city": "Mumbai",
        "state": "Maharashtra",
        "state_code": "27",
        "pincode": "400001",
        "phone": "9820011223"
    }
    party_dict = {
        "name": "Stress Test Client Ltd",
        "gstin": "27XYZAB9876C1Z1",
        "address": "404 Steel Market",
        "city": "Mumbai",
        "state": "Maharashtra",
        "state_code": "27"
    }
    items_list = []
    for idx in range(1, 151):
        items_list.append({
            "product_id": 1,
            "item_name": f"Heavy Industrial Stress Item #{idx:03d} High Strength Steel",
            "hsn_code": "7204",
            "unit": "PCS",
            "quantity": 1.0,
            "unit_price": 1000.0,
            "discount_pct": 0.0,
            "taxable_value": 1000.0,
            "gst_rate": 18.0,
            "cgst_rate": 9.0,
            "cgst_amount": 90.0,
            "sgst_rate": 9.0,
            "sgst_amount": 90.0,
            "igst_rate": 0.0,
            "igst_amount": 0.0,
            "total_amount": 1180.0
        })
    data_payload = {
        "invoice_number": "INV/2025-26/STRESS-150",
        "invoice_date": date.today(),
        "party": party_dict,
        "party_name": party_dict["name"],
        "party_gstin": party_dict["gstin"],
        "party_address": party_dict["address"],
        "items": items_list,
        "subtotal": 150000.0,
        "cgst_total": 13500.0,
        "sgst_total": 13500.0,
        "igst_total": 0.0,
        "total_tax": 27000.0,
        "round_off": 0.0,
        "grand_total": 177000.0
    }
    t_pdf0 = time.time()
    generate_invoice_pdf(data_payload, comp_dict, str(out_pdf))
    pdf_dur = time.time() - t_pdf0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("150-Item Invoice PDF Generation", f"Multi-page PDF ({out_pdf.stat().st_size / 1024:.1f} KB)", pdf_dur, mem)
    
    # B. Day Book Excel Export (Multi-thousand rows)
    out_excel = ROOT_DIR / "scratch" / "audit" / "daybook_export_stress.xlsx"
    t0 = time.time()
    db_exp_data = get_day_book(from_date=date(2025, 4, 1), to_date=date(2025, 6, 30))
    export_daybook_excel(db_exp_data, out_excel)
    excel_dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Day Book Excel Export", f"{len(db_exp_data.get('rows', []))} rows ({out_excel.stat().st_size / 1024:.1f} KB)", excel_dur, mem)

def benchmark_backup_restore():
    proc = psutil.Process()
    print("\n--- 4. Benchmarking Backup & Restore Performance ---")
    
    # A. Backup Database
    backup_dest = ROOT_DIR / "scratch" / "audit" / "perf_stress_backup.db"
    t0 = time.time()
    backup_res = create_backup(str(backup_dest))
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Database Backup (Native SQLite API)", f"32k records ({backup_dest.stat().st_size / (1024*1024):.2f} MB)", dur, mem)
    
    # B. Restore Database
    t0 = time.time()
    restore_res = restore_backup(str(backup_dest))
    dur = time.time() - t0
    mem = proc.memory_info().rss / (1024 * 1024)
    record_metric("Database Restore (Native SQLite API)", f"32k records ({backup_dest.stat().st_size / (1024*1024):.2f} MB)", dur, mem)

def benchmark_memory_growth():
    proc = psutil.Process()
    print("\n--- 5. Benchmarking Memory Growth over 50 Consecutive Cycles ---")
    
    mem_initial = proc.memory_info().rss / (1024 * 1024)
    t0 = time.time()
    for cycle in range(1, 51):
        # Emulate 50 repeated query and view refresh operations
        with get_session() as s:
            _ = s.query(Party).limit(100).all()
            _ = s.query(Product).limit(100).all()
            _ = s.query(Invoice).limit(100).all()
            
    dur = time.time() - t0
    mem_final = proc.memory_info().rss / (1024 * 1024)
    growth = mem_final - mem_initial
    
    record_metric("Memory Growth Test (50 cycles)", f"Initial: {mem_initial:.1f}MB -> Final: {mem_final:.1f}MB (Growth: {growth:+.1f}MB)", dur, mem_final)

def run_phase7():
    print("=======================================================")
    print("--- Phase 7: Performance & Stress Benchmark Starting ---")
    print(f"Active DB: {PERF_DB}")
    print("=======================================================\n")
    
    generate_high_volume_data()
    benchmark_queries_and_reports()
    benchmark_exports_and_pdf()
    benchmark_backup_restore()
    benchmark_memory_growth()
    
    out_file = ROOT_DIR / "scratch" / "audit" / "phase7_perf_results.json"
    with open(out_file, "w") as f:
        json.dump(perf_results, f, indent=2)
        
    print("\n=======================================================")
    print(f"--- Phase 7 Complete: {len(perf_results)} benchmarks recorded. Saved to {out_file} ---")
    print("=======================================================")

if __name__ == "__main__":
    run_phase7()
