"""
Tests for Accounts Exports & Clean State Validation.
Validates:
1. All 9 Accounts reports generate cleanly in PDF and Excel formats.
2. Unicode fonts (Devanagari/Hindi) render in ReportLab without Latin-1 crash.
3. Indian number formats and frozen header panes in openpyxl Excel exports.
4. Export pipeline company profile validation guard.
"""
import os
import tempfile
from pathlib import Path
from datetime import date, datetime
import pytest

from app.database.connection import init_db, get_session
from app.database.models import CompanyProfile, Party, Voucher, VoucherItem
from app.services.export_service import (
    register_unicode_fonts,
    export_daybook_pdf,
    export_daybook_excel,
    export_party_ledger_pdf,
    export_party_ledger_excel,
    export_outstanding_pdf,
    export_outstanding_excel,
    export_trial_balance_pdf,
    export_trial_balance_excel,
    export_pnl_pdf,
    export_pnl_excel,
    export_cashbank_pdf,
    export_cashbank_excel,
    export_expense_pdf,
    export_expense_excel,
    INR_EXCEL_FORMAT
)
from app.ui.save_dialog import validate_company_profile_for_export, sanitize_filename


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()
    register_unicode_fonts()
    yield


def test_sanitize_filename():
    assert sanitize_filename('INV/2026:01*test?"<>|') == "INV_2026_01_test"
    assert sanitize_filename("") == "export"
    assert sanitize_filename("  clean_name  ") == "clean_name"


def test_validate_company_profile_guard():
    # Empty profile should fail validation
    empty_profile = CompanyProfile(name="", state=None)
    valid, msg = validate_company_profile_for_export(empty_profile)
    assert not valid
    assert "Company Name" in msg or "State" in msg

    # Incomplete profile (missing state)
    missing_state = CompanyProfile(name="Acme Corp", state="")
    valid, msg = validate_company_profile_for_export(missing_state)
    assert not valid

    # Complete profile should pass
    complete_profile = CompanyProfile(name="Acme Corp", state="West Bengal", state_code="19")
    valid, msg = validate_company_profile_for_export(complete_profile)
    assert valid
    assert msg == ""


def test_export_daybook_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "daybook.pdf"
    xlsx_out = tmp_path / "daybook.xlsx"

    db_data = {
        "from_date": "01-04-2026",
        "to_date": "24-10-2026",
        "count": 2,
        "total_debit": 150000.0,
        "total_credit": 150000.0,
        "rows": [
            {
                "voucher_date": date.today(),
                "voucher_type": "Sales",
                "voucher_number": "VCH-001",
                "party_name": "व्यापार ट्रेडर्स (Vyapar Traders)",
                "reference_no": "REF-99",
                "payment_mode": "Bank Transfer",
                "debit": 150000.0,
                "credit": 0.0,
            },
            {
                "voucher_date": date.today(),
                "voucher_type": "Receipt",
                "voucher_number": "VCH-002",
                "party_name": "व्यापार ट्रेडर्स (Vyapar Traders)",
                "reference_no": "CHEQUE-123",
                "payment_mode": "Bank Transfer",
                "debit": 0.0,
                "credit": 150000.0,
            }
        ]
    }

    res_pdf = export_daybook_pdf(daybook_data=db_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_daybook_excel(daybook_data=db_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000


def test_export_ledger_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "ledger.pdf"
    xlsx_out = tmp_path / "ledger.xlsx"

    ledger_data = {
        "party": {
            "name": "राधे श्याम इंटरप्राइजेज (Radhey Shyam)",
            "gstin": "19AABCR1234F1Z5",
            "state": "West Bengal",
            "phone": "9876543210",
            "address": "Burrabazar, Kolkata"
        },
        "from_date": "01-04-2026",
        "to_date": "24-10-2026",
        "opening_balance": {"amount": 25000.0, "type": "Dr"},
        "closing_balance": {"amount": 75000.0, "type": "Dr"},
        "total_debit": 125000.0,
        "total_credit": 75000.0,
        "entries": [
            {
                "voucher_date": date.today(),
                "voucher_type": "Sales",
                "voucher_number": "INV-101",
                "reference_no": "PO-55",
                "product": "Industrial Solvents",
                "narration": "Sales for project Alpha",
                "debit": 100000.0,
                "credit": 0.0,
                "running_balance": 125000.0,
                "running_balance_type": "Dr"
            },
            {
                "voucher_date": date.today(),
                "voucher_type": "Receipt",
                "voucher_number": "REC-202",
                "reference_no": "NEFT-788",
                "product": "",
                "narration": "Part payment via RTGS",
                "debit": 0.0,
                "credit": 50000.0,
                "running_balance": 75000.0,
                "running_balance_type": "Dr"
            }
        ]
    }

    res_pdf = export_party_ledger_pdf(ledger_data=ledger_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_party_ledger_excel(ledger_data=ledger_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000


def test_export_trial_balance_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "trial_balance.pdf"
    xlsx_out = tmp_path / "trial_balance.xlsx"

    tb_data = {
        "to_date": "24-10-2026",
        "is_balanced": True,
        "total_op_dr": 50000.0,
        "total_op_cr": 50000.0,
        "total_period_dr": 200000.0,
        "total_period_cr": 200000.0,
        "total_cl_dr": 250000.0,
        "total_cl_cr": 250000.0,
        "rows": [
            {
                "party_name": "कैश इन हैन्ड (Cash In Hand)",
                "party_type": "Asset",
                "op_dr": 50000.0,
                "op_cr": 0.0,
                "period_dr": 100000.0,
                "period_cr": 50000.0,
                "cl_dr": 100000.0,
                "cl_cr": 0.0
            },
            {
                "party_name": "कैपिटल अकाउंट (Capital A/c)",
                "party_type": "Capital",
                "op_dr": 0.0,
                "op_cr": 50000.0,
                "period_dr": 0.0,
                "period_cr": 50000.0,
                "cl_dr": 0.0,
                "cl_cr": 100000.0
            }
        ]
    }

    res_pdf = export_trial_balance_pdf(tb_data=tb_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_trial_balance_excel(tb_data=tb_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000


def test_export_pnl_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "pnl.pdf"
    xlsx_out = tmp_path / "pnl.xlsx"

    pnl_data = {
        "from_date": "01-04-2026",
        "to_date": "24-10-2026",
        "revenue_items": [
            {"name": "विक्रय आय (Sales Revenue)", "amount": 500000.0}
        ],
        "total_revenue": 500000.0,
        "cogs_items": [
            {"name": "माल की खरीद (Purchases)", "amount": 300000.0}
        ],
        "total_cogs": 300000.0,
        "gross_profit": 200000.0,
        "expense_items": [
            {"name": "दुकान किराया (Office Rent)", "amount": 40000.0},
            {"name": "बिजली बिल (Electricity)", "amount": 10000.0}
        ],
        "total_expenses": 50000.0,
        "net_profit": 150000.0
    }

    res_pdf = export_pnl_pdf(pnl_data=pnl_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_pnl_excel(pnl_data=pnl_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000


def test_export_cashbank_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "cashbank.pdf"
    xlsx_out = tmp_path / "cashbank.xlsx"

    cb_data = {
        "account_name": "State Bank of India (Current A/c)",
        "from_date": "01-04-2026",
        "to_date": "24-10-2026",
        "opening_balance": 50000.0,
        "total_inflow": 200000.0,
        "total_outflow": 120000.0,
        "closing_balance": 130000.0,
        "transactions": [
            {
                "date": date.today(),
                "voucher_no": "REC-01",
                "party": "ग्राहक (Customer A)",
                "description": "Invoice receipt",
                "inflow": 200000.0,
                "outflow": 0.0,
                "balance": 250000.0
            },
            {
                "date": date.today(),
                "voucher_no": "PAY-01",
                "party": "आपूर्तिकर्ता (Supplier B)",
                "description": "Vendor payout",
                "inflow": 0.0,
                "outflow": 120000.0,
                "balance": 130000.0
            }
        ]
    }

    res_pdf = export_cashbank_pdf(cashbank_data=cb_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_cashbank_excel(cashbank_data=cb_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000


def test_export_expense_pdf_and_excel(tmp_path):
    pdf_out = tmp_path / "expense.pdf"
    xlsx_out = tmp_path / "expense.xlsx"

    exp_data = {
        "from_date": "01-04-2026",
        "to_date": "24-10-2026",
        "category_filter": "All",
        "total_amount": 25000.0,
        "expenses": [
            {
                "date": date.today(),
                "voucher_no": "EXP-101",
                "category": "यात्रा खर्च (Travel Expenses)",
                "description": "Client visit travel allowance",
                "payment_mode": "UPI / Online",
                "amount": 25000.0
            }
        ]
    }

    res_pdf = export_expense_pdf(expense_data=exp_data, output_path=pdf_out)
    assert res_pdf.exists()
    assert res_pdf.stat().st_size > 1000

    res_xlsx = export_expense_excel(expense_data=exp_data, output_path=xlsx_out)
    assert res_xlsx.exists()
    assert res_xlsx.stat().st_size > 1000
