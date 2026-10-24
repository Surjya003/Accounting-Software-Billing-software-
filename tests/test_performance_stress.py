"""
Performance & Stress Test Suite: 32,000+ Record Database Latency & Export Benchmarks.
Validates:
- List & report queries complete in < 2.0 seconds.
- PDF and Excel exports complete in < 5.0 seconds.
- NEVER touches data/accounting.db; uses isolated data/test_stress_perf.db.
"""
import os
import sys
import time
import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import pytest

from app.config import BASE_DIR, EXPORTS_DIR
from app.database.connection import init_db
from app.database.models import (
    Base, Party, Product, Invoice, InvoiceItem, Voucher, VoucherItem, CompanyProfile
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = BASE_DIR / "data" / "test_stress_perf.db"
TOTAL_RECORDS_TARGET = 32000


@pytest.fixture(scope="module")
def stress_db():
    """Sets up an isolated 32k+ record SQLite database with WAL and pragmas."""
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False, "timeout": 30.0})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # 1. Company Profile
    with Session() as session:
        comp = CompanyProfile(
            name="Stress Test Enterprise Pvt Ltd",
            trade_name="StressCorp",
            gstin="19AABCS1429B1Z2",
            state="West Bengal",
            state_code="19",
            address="100 Tech Park, Kolkata",
            phone="9876543210",
            email="stress@example.com"
        )
        session.add(comp)
        session.commit()

    # Fast bulk insertion using raw sqlite3 connection with WAL & synchronous=OFF
    raw_conn = sqlite3.connect(str(TEST_DB_PATH))
    try:
        cur = raw_conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL")
        cur.execute("PRAGMA synchronous = OFF")
        cur.execute("BEGIN TRANSACTION")

        # Insert 1,000 Parties
        parties_data = [
            (
                f"Party #{i:04d}",
                "Customer" if i % 2 == 0 else "Supplier",
                "9876500000",
                f"party{i}@example.com",
                f"19AAACB{i:04d}A1Z1" if i % 3 != 0 else "",
                f"Address {i}, Kolkata",
                "West Bengal",
                "19",
                0.0,
                "Dr",
                100000.0,
                1,
                "2026-04-01"
            )
            for i in range(1, 1001)
        ]
        cur.executemany(
            """INSERT INTO parties (name, party_type, phone, email, gstin, address, state, state_code,
               opening_balance, opening_balance_type, credit_limit, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            parties_data
        )

        # Insert 1,000 Products
        products_data = [
            (
                f"Industrial Component {i}",
                f"{8400 + (i % 50):04d}",
                f"Description {i}",
                "PCS",
                150.0 + (i % 750),
                100.0 + (i % 500),
                140.0 + (i % 700),
                18.0 if i % 2 == 0 else 12.0,
                100.0,
                10.0,
                1,
                "2026-04-01 10:00:00"
            )
            for i in range(1, 1001)
        ]
        cur.executemany(
            """INSERT INTO products (name, hsn_code, description, unit, price, purchase_price,
               wholesale_price, tax_rate, stock_quantity, low_stock_threshold, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            products_data
        )

        # Insert 15,000 Vouchers
        vouchers_data = [
            (
                f"VCH-2026-{i:06d}",
                (date(2026, 4, 1) + timedelta(days=i % 180)).isoformat(),
                "Debit" if i % 2 == 0 else "Credit",
                (i % 1000) + 1,
                1000.0,
                90.0,
                90.0,
                0.0,
                180.0,
                1180.0,
                1180.0 if i % 2 == 0 else 0.0,
                0.0 if i % 2 == 0 else 1180.0,
                "2026-04-01 10:00:00"
            )
            for i in range(1, 15001)
        ]
        cur.executemany(
            """INSERT INTO vouchers (voucher_number, voucher_date, voucher_type, party_id,
               amount_untaxed, cgst_amount, sgst_amount, igst_amount, total_tax,
               total_amount, debit_amount, credit_amount, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            vouchers_data
        )

        # Insert 15,000 Invoices
        invoices_data = [
            (
                f"INV/2026-27/{i:06d}",
                (date(2026, 4, 1) + timedelta(days=i % 180)).isoformat(),
                (i % 1000) + 1,
                1000.0,
                90.0 if (i % 5 != 0) else 0.0,
                90.0 if (i % 5 != 0) else 0.0,
                0.0 if (i % 5 != 0) else 180.0,
                180.0,
                1180.0,
                "final" if i % 3 != 0 else "draft",
                0 if (i % 5 != 0) else 1,
                0,
                "West Bengal",
                "2026-04-01 10:00:00"
            )
            for i in range(1, 15001)
        ]
        cur.executemany(
            """INSERT INTO invoices (invoice_number, invoice_date, party_id,
               subtotal, cgst_total, sgst_total, igst_total, tax_amount,
               total_amount, status, is_interstate, reverse_charge, place_of_supply, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            invoices_data
        )

        raw_conn.commit()
    finally:
        raw_conn.close()

    yield {
        "engine": engine,
        "Session": Session,
        "db_path": str(TEST_DB_PATH)
    }

    # Teardown
    engine.dispose()
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        wal_p = Path(str(TEST_DB_PATH) + "-wal")
        if wal_p.exists():
            wal_p.unlink()
        shm_p = Path(str(TEST_DB_PATH) + "-shm")
        if shm_p.exists():
            shm_p.unlink()
    except Exception:
        pass


def test_stress_record_count(stress_db):
    """Verify test database contains >= 32,000 business entities."""
    Session = stress_db["Session"]
    with Session() as s:
        p_cnt = s.query(Party).count()
        pr_cnt = s.query(Product).count()
        v_cnt = s.query(Voucher).count()
        i_cnt = s.query(Invoice).count()
        total = p_cnt + pr_cnt + v_cnt + i_cnt

    print(f"\n[STRESS TEST] Record Counts: Parties={p_cnt}, Products={pr_cnt}, Vouchers={v_cnt}, Invoices={i_cnt} | Total={total}")
    assert total >= TOTAL_RECORDS_TARGET, f"Expected at least {TOTAL_RECORDS_TARGET} records, got {total}"


def test_stress_invoice_list_query_performance(stress_db):
    """Benchmark: Paginated Invoice listing with party joins across 15k invoices must be < 2.0s."""
    from sqlalchemy.orm import joinedload
    Session = stress_db["Session"]

    t0 = time.perf_counter()
    with Session() as s:
        invoices = (
            s.query(Invoice)
            .options(joinedload(Invoice.party))
            .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
            .limit(100)
            .all()
        )
        count = len(invoices)
    elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] Invoice List (100 rows fetched from 15k with join): {elapsed*1000:.2f} ms")
    assert count == 100
    assert elapsed < 2.0, f"Query took {elapsed:.2f}s, exceeding 2.0s SLA!"


def test_stress_party_outstanding_query_performance(stress_db):
    """Benchmark: Aggregating party balances across 32,000 transactions must be < 2.0s."""
    from sqlalchemy import func
    Session = stress_db["Session"]

    t0 = time.perf_counter()
    with Session() as s:
        results = (
            s.query(
                Invoice.party_id,
                func.sum(Invoice.subtotal).label("total_subtotal"),
                func.sum(Invoice.tax_amount).label("total_tax"),
                func.sum(Invoice.total_amount).label("total_billed"),
                func.count(Invoice.id).label("invoice_count")
            )
            .group_by(Invoice.party_id)
            .all()
        )
        party_count = len(results)
    elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] Party Ledger Aggregation ({party_count} parties across 15k invoices): {elapsed*1000:.2f} ms")
    assert party_count > 0
    assert elapsed < 2.0, f"Party outstanding aggregation took {elapsed:.2f}s, exceeding 2.0s SLA!"


def test_stress_gst_summary_performance(stress_db, monkeypatch):
    """Benchmark: GSTR-1 outward supply classification over monthly period must be < 2.0s."""
    monkeypatch.setattr("app.services.gst_report_service.get_session", stress_db["Session"])
    from app.services.gst_report_service import get_gstr1_data

    from_d = date(2026, 4, 1)
    to_d = date(2026, 4, 30)

    t0 = time.perf_counter()
    data = get_gstr1_data(from_d, to_d)
    elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] GSTR-1 Calculation for 1-month window ({data['invoice_count']} invoices analyzed): {elapsed*1000:.2f} ms")
    assert data["invoice_count"] > 0
    assert elapsed < 2.0, f"GSTR-1 calculation took {elapsed:.2f}s, exceeding 2.0s SLA!"


def test_stress_excel_export_performance(stress_db, monkeypatch):
    """Benchmark: Generating Excel report from 1,000 transaction rows must be < 5.0s."""
    import openpyxl
    from app.services.export_service import sanitize_excel_cell, setup_excel_print_and_freeze, autofit_excel_columns

    Session = stress_db["Session"]
    with Session() as s:
        invoices = s.query(Invoice).limit(1000).all()

    t0 = time.perf_counter()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stress Invoices"
    ws.append(["ID", "Invoice Number", "Date", "Status", "Subtotal", "Tax", "Grand Total"])

    setup_excel_print_and_freeze(ws, freeze_cell="A2", title_rows="1:1")

    for inv in invoices:
        ws.append([
            inv.id,
            sanitize_excel_cell(inv.invoice_number),
            str(inv.invoice_date),
            inv.status,
            float(inv.subtotal),
            float(inv.tax_amount),
            float(inv.total_amount)
        ])

    autofit_excel_columns(ws)
    out_file = EXPORTS_DIR / "stress_invoices_test.xlsx"
    wb.save(str(out_file))
    elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] Excel 1,000-Row Export with Formatting: {elapsed*1000:.2f} ms")
    assert out_file.exists()
    try:
        out_file.unlink()
    except Exception:
        pass
    assert elapsed < 5.0, f"Excel export took {elapsed:.2f}s, exceeding 5.0s SLA!"


def test_stress_reportlab_pdf_export_performance(stress_db):
    """Benchmark: ReportLab PDF generation for 10-item tax invoice must be < 5.0s."""
    from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator

    inv_data = {
        "invoice_number": "INV/2026-27/99999",
        "invoice_date": "15-05-2026",
        "due_date": "30-05-2026",
        "party_name": "Mega Tech Solutions Pvt Ltd",
        "party_gstin": "19AABCS1429B1Z2",
        "party_address": "Salt Lake Sector V, Kolkata, WB",
        "party_state": "West Bengal",
        "party_state_code": "19",
        "items": [
            {
                "description": f"Industrial Heavy Duty Sensor Module Type-{i} (Devanagari: उपकरण {i})",
                "hsn_code": f"8471{i:02d}",
                "quantity": 10 + i,
                "unit": "PCS",
                "rate": 1250.00,
                "gst_rate": 18.0,
                "amount": (10 + i) * 1250.00
            }
            for i in range(1, 11)
        ],
        "subtotal": 150000.0,
        "cgst_amount": 13500.0,
        "sgst_amount": 13500.0,
        "igst_amount": 0.0,
        "round_off": 0.0,
        "grand_total": 177000.0,
        "amount_in_words": "Rupees One Lakh Seventy Seven Thousand Only",
        "notes": "Payment terms: Net 15 days.",
        "company": {
            "name": "Stress Test Enterprise Pvt Ltd",
            "trade_name": "StressCorp",
            "gstin": "19AABCS1429B1Z2",
            "state": "West Bengal",
            "state_code": "19",
            "address": "100 Tech Park, Kolkata",
            "phone": "9876543210"
        }
    }

    gen = InvoicePDFGenerator()
    out_pdf = EXPORTS_DIR / "stress_invoice_perf.pdf"

    t0 = time.perf_counter()
    res = gen.generate_invoice(inv_data, str(out_pdf))
    elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] ReportLab 10-Item Tax Invoice PDF Generation: {elapsed*1000:.2f} ms")
    assert Path(res).exists()
    assert Path(res).stat().st_size > 5000
    try:
        Path(res).unlink()
    except Exception:
        pass
    assert elapsed < 5.0, f"PDF generation took {elapsed:.2f}s, exceeding 5.0s SLA!"
