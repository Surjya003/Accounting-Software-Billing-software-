import os
import sys
import time
import shutil
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

STRESS_DB = ROOT_DIR / "data" / "rc_verify_stress.db"
BENCH_DB = ROOT_DIR / "data" / "benchmark_run.db"

if not STRESS_DB.exists():
    raise FileNotFoundError(f"Stress DB not found at {STRESS_DB}. Run scripts/build_stress_db.py first.")

# Copy stress DB to isolated benchmark DB so test runs do not alter original stress DB
for extra in [BENCH_DB, ROOT_DIR / "data" / "benchmark_run.db-wal", ROOT_DIR / "data" / "benchmark_run.db-shm"]:
    if extra.exists():
        try: extra.unlink()
        except: pass
shutil.copy2(STRESS_DB, BENCH_DB)

os.environ["ACCOUNTING_DB_PATH"] = str(BENCH_DB)
os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{BENCH_DB}"

from app.database.connection import init_db, get_session, create_backup, create_encrypted_backup, restore_backup
init_db()

from app.database.models import Invoice, Product, Party, Voucher
from app.services.pnl_service import get_profit_loss_statement
from app.services.report_service import get_trial_balance, get_day_book, get_dashboard_kpis
from app.services.stock_report_service import get_stock_movement_report
from app.services.export_service import export_daybook_excel
from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator

COMPANY_DATA = {
    "name": "Benchmark Enterprise Pvt Ltd",
    "gstin": "27AAPFU0939L1ZV",
    "address": "MIDC Industrial Estate",
    "city": "Mumbai",
    "state": "Maharashtra",
    "state_code": "27",
    "phone": "9876543210"
}

benchmarks = []

def run_bench(name, workload_desc, fn, sla_sec, iterations=3):
    durations = []
    res = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = fn()
        durations.append(time.perf_counter() - t0)
    avg_dur = sum(durations) / len(durations)
    min_dur = min(durations)
    status = "PASSED" if avg_dur <= sla_sec else "FAILED"
    benchmarks.append({
        "benchmark": name,
        "workload": workload_desc,
        "avg_sec": round(avg_dur, 4),
        "min_sec": round(min_dur, 4),
        "sla_sec": sla_sec,
        "status": status
    })
    print(f"| {name} | {workload_desc} | {avg_dur:.4f}s | {min_dur:.4f}s | < {sla_sec:.1f}s | {status} |", flush=True)
    return res

print(f"\n| Benchmark Task | Workload Description | Avg Time (s) | Best Time (s) | SLA Target | Status |", flush=True)
print(f"|:---|:---|:---:|:---:|:---:|:---|", flush=True)

# 1. P&L Statement on 5,000 products & 16,000 invoices
run_bench(
    "Profit & Loss (P&L)",
    "5,000 products, 16,000 invoices, 20,000 vouchers",
    lambda: get_profit_loss_statement(date(2026, 4, 1), date(2027, 3, 31)),
    sla_sec=2.0
)

# 2. Trial Balance
run_bench(
    "Trial Balance",
    "2,000 parties, 20,000 vouchers",
    lambda: get_trial_balance(date(2027, 3, 31)),
    sla_sec=2.0
)

# 3. Day Book
run_bench(
    "Day Book (Monthly)",
    "Full month range across 20k vouchers",
    lambda: get_day_book(date(2026, 6, 1), date(2026, 6, 30)),
    sla_sec=2.0
)

# 4. Stock Movement Report
run_bench(
    "Stock Movement Report",
    "5,000 inventory products & stock levels",
    lambda: get_stock_movement_report(),
    sla_sec=2.0
)

# 5. Dashboard KPIs
run_bench(
    "Dashboard KPIs",
    "Real-time revenue, receivables, stock, P&L",
    lambda: get_dashboard_kpis(),
    sla_sec=2.0
)

# 6. 150-Item Invoice PDF Generation
def generate_150_item_pdf():
    items = []
    for i in range(1, 151):
        items.append({
            "item_description": f"Heavy Duty Industrial Drive Component Assembly Model HDA-{i:03d}",
            "hsn_code": "8481",
            "quantity": 2.0,
            "unit": "NOS",
            "unit_price": 1250.0 + (i * 10),
            "tax_rate": 18.0,
            "gst_rate_pct": 18.0,
            "taxable_value": 2500.0 + (i * 20),
            "cgst_amount": 225.0 + (i * 1.8),
            "sgst_amount": 225.0 + (i * 1.8),
            "igst_amount": 0.0,
            "total_item_amount": 2950.0 + (i * 23.6),
            "total_amount": 2950.0 + (i * 23.6),
        })
    tot_taxable = sum(it["taxable_value"] for it in items)
    tot_cgst = sum(it["cgst_amount"] for it in items)
    tot_sgst = sum(it["sgst_amount"] for it in items)
    tot_grand = sum(it["total_item_amount"] for it in items)
    
    payload = {
        "invoice_number": "INV-BENCH-150",
        "date": "24-10-2026",
        "company": COMPANY_DATA,
        "customer": {"name": "Benchmark Industries Ltd", "gstin": "27AABCB9876P1ZV", "state": "Maharashtra", "state_code": "27"},
        "items": items,
        "totals": {
            "subtotal": tot_taxable, "taxable_amount": tot_taxable,
            "cgst_amount": tot_cgst, "cgst_total": tot_cgst,
            "sgst_amount": tot_sgst, "sgst_total": tot_sgst,
            "igst_amount": 0.0, "igst_total": 0.0,
            "tax_amount": tot_cgst + tot_sgst, "total_tax": tot_cgst + tot_sgst,
            "grand_total": tot_grand, "total_amount": tot_grand
        }
    }
    out_pdf = ROOT_DIR / "exports" / "benchmark_150_items.pdf"
    out_pdf.parent.mkdir(exist_ok=True)
    InvoicePDFGenerator().generate_invoice(payload, filename=str(out_pdf))
    return out_pdf

run_bench(
    "150-Item Invoice PDF",
    "150 distinct line items, full pagination",
    generate_150_item_pdf,
    sla_sec=5.0
)

# 7. 6,000+ Row Excel Export (Day Book spanning full year)
def generate_6000_row_excel():
    out_xl = ROOT_DIR / "exports" / "benchmark_daybook_stress.xlsx"
    out_xl.parent.mkdir(exist_ok=True)
    db_data = get_day_book(date(2026, 4, 1), date(2027, 3, 31))
    return export_daybook_excel(daybook_data=db_data, output_path=out_xl)

run_bench(
    "6,000+ Row Excel Export",
    "Annual Day Book export (16,000+ entries)",
    generate_6000_row_excel,
    sla_sec=5.0
)

# 8. Database Backup (SQLite Online Backup API)
def do_db_backup():
    dest = ROOT_DIR / "data" / "backups"
    dest.mkdir(exist_ok=True)
    return create_backup(custom_dest_dir=dest)

run_bench(
    "Database Backup",
    "Full snapshot of 6.65 MB stress database",
    do_db_backup,
    sla_sec=2.0
)

# 9. AES-256-GCM Encrypted Backup
def do_encrypted_backup():
    dest = ROOT_DIR / "data" / "backups"
    dest.mkdir(exist_ok=True)
    return create_encrypted_backup(passphrase="AuditSecret2026!", custom_dest_dir=dest)

b_enc_file = run_bench(
    "Encrypted Backup (AES-256-GCM)",
    "PBKDF2 100k rounds + AES-GCM 256-bit",
    do_encrypted_backup,
    sla_sec=2.0
)

# 10. Database Restore
def do_restore():
    # Restore from raw backup file
    raw_backup = ROOT_DIR / "data" / "backups" / "benchmark_run.db"
    if not raw_backup.exists():
        raw_backup = create_backup(custom_dest_dir=ROOT_DIR / "data" / "backups")
    return restore_backup(raw_backup)

run_bench(
    "Database Restore",
    "Full stream restore + schema init + WAL truncate",
    do_restore,
    sla_sec=2.0
)

print("\nBenchmark Suite Completed Successfully.")
