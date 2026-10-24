"""
Build dedicated stress database data/rc_verify_stress.db
Exact requirements:
- 5,000 Products
- 2,000 Parties
- 16,000 Invoices (with line items)
- 20,000 Vouchers
- 2,000 Purchase Orders (with line items)
"""
import sqlite3
import time
from pathlib import Path
from datetime import date, timedelta

def build_stress_db():
    db_path = Path("data/rc_verify_stress.db")
    if db_path.exists():
        db_path.unlink()
    for p in [Path("data/rc_verify_stress.db-wal"), Path("data/rc_verify_stress.db-shm")]:
        if p.exists():
            p.unlink()

    print("Building data/rc_verify_stress.db...")
    t0 = time.time()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = OFF")

    ref_conn = sqlite3.connect("data/test_perf_stress.db")
    schema = ref_conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL").fetchall()
    ref_conn.close()

    for (sql,) in schema:
        cur.execute(sql)

    # 1. Company profile
    cur.execute("""INSERT INTO company_profile (id, name, trade_name, gstin, state, state_code, address, phone, email, financial_year, allow_negative_stock)
    VALUES (1, 'RC Stress Test Corp', 'StressCorp', '27AABCS1429B1Z8', 'Maharashtra', '27', '100 Marine Lines, Mumbai', '9820012345', 'stress@test.com', '2026-27', 0)""")

    # 2. 2,000 Parties
    print("Inserting 2,000 parties...")
    parties = [
        (i, f"PRT-{i:05d}", f"Stress Party {i:05d}", "Customer" if i % 2 == 0 else "Supplier",
         f"27ABCDE{i:04d}F1Z5" if i % 3 != 0 else "", "98200" + f"{i:05d}", "Address " + str(i), "Mumbai", "Maharashtra", "27",
         0.0, "Dr", 1, "2026-04-01 10:00:00", "2026-04-01 10:00:00")
        for i in range(1, 2001)
    ]
    cur.executemany("""INSERT INTO parties (id, code, name, party_type, gstin, phone, address, city, state, state_code, opening_balance, opening_balance_type, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", parties)

    # 3. 5,000 Products
    print("Inserting 5,000 products...")
    gst_slabs = [0.0, 5.0, 12.0, 18.0, 28.0]
    products = [
        (i, f"Industrial Product Item {i:05d}", f"84{i%100:02d}00", f"BAR-{i:05d}", "PCS",
         500.0 + (i % 500), 300.0 + (i % 300), gst_slabs[i % len(gst_slabs)], 100.0, 10.0, 1, "2026-04-01 10:00:00", "2026-04-01 10:00:00")
        for i in range(1, 5001)
    ]
    cur.executemany("""INSERT INTO products (id, name, hsn_code, barcode, unit, price, purchase_price, tax_rate, stock_quantity, low_stock_threshold, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", products)

    # 4. 20,000 Vouchers
    print("Inserting 20,000 vouchers...")
    base_d = date(2026, 4, 1)
    v_types = ["Debit", "Credit", "Debit", "Credit", "Journal"]
    vouchers = [
        (i, f"VCH-2026-{i:06d}", v_types[i % len(v_types)], (base_d + timedelta(days=i % 300)).isoformat(),
         (i % 2000) + 1, 1000.0, 90.0, 90.0, 0.0, 180.0, 1180.0,
         1180.0 if v_types[i % len(v_types)] == "Debit" else 0.0,
         1180.0 if v_types[i % len(v_types)] == "Credit" else 0.0,
         f"Stress voucher {i}", 1 if v_types[i % len(v_types)] == "Debit" else 0,
         "2026-04-01 10:00:00", "2026-04-01 10:00:00")
        for i in range(1, 20001)
    ]
    cur.executemany("""INSERT INTO vouchers (id, voucher_number, voucher_type, voucher_date, party_id, amount_untaxed, cgst_amount, sgst_amount, igst_amount, total_tax, total_amount, debit_amount, credit_amount, narration, is_tax_invoice, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", vouchers)

    # 5. 16,000 Invoices (with items)
    print("Inserting 16,000 invoices and items...")
    invoices = []
    items = []
    for i in range(1, 16001):
        inv_d = (base_d + timedelta(days=i % 300)).isoformat()
        pid = (i % 2000) + 1
        sub = 1000.0
        tax = 180.0
        tot = 1180.0
        invoices.append((
            i, f"INV/2026-27/{i:06d}", inv_d, pid, sub, 90.0, 90.0, 0.0, tax, tot, "final", "Standard Sale", 0, "2026-04-01 10:00:00", "2026-04-01 10:00:00"
        ))
        items.append((
            i, i, (i % 5000) + 1, f"Item {(i % 5000) + 1}", "8400", 2.0, "PCS", 500.0, 0.0, 1000.0, 18.0, 90.0, 90.0, 0.0, 1180.0
        ))

    cur.executemany("""INSERT INTO invoices (id, invoice_number, invoice_date, party_id, subtotal, cgst_total, sgst_total, igst_total, tax_amount, total_amount, status, notes, is_interstate, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", invoices)

    cur.executemany("""INSERT INTO invoice_items (id, invoice_id, product_id, item_description, hsn_code, quantity, unit, unit_price, discount_pct, taxable_value, gst_rate_pct, cgst_amount, sgst_amount, igst_amount, total_amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", items)

    # 6. 2,000 Purchase Orders & Items
    print("Inserting 2,000 POs and items...")
    pos = []
    po_items = []
    for i in range(1, 2001):
        po_d = (base_d + timedelta(days=i % 300)).isoformat()
        pos.append((
            i, f"PO/2026-27/{i:05d}", po_d, (i % 2000) + 1, 3000.0, 540.0, 3540.0, "received", "PO notes", "2026-04-01 10:00:00", "2026-04-01 10:00:00"
        ))
        po_items.append((
            i, i, (i % 5000) + 1, f"PO Item {(i % 5000) + 1}", "8400", 10.0, 10.0, "PCS", 300.0, 18.0, 540.0, 3540.0
        ))

    cur.executemany("""INSERT INTO purchase_orders (id, po_number, po_date, party_id, subtotal, tax_amount, total_amount, status, notes, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", pos)

    cur.executemany("""INSERT INTO purchase_order_items (id, po_id, product_id, item_description, hsn_code, quantity, received_quantity, unit, unit_price, tax_rate, tax_amount, total_amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", po_items)

    conn.commit()
    conn.close()
    print(f"Stress database built in {time.time() - t0:.2f}s! Size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    build_stress_db()
