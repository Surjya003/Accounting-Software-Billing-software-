"""
Unit and Integration Tests for Extended Vyapar & TallyPrime Features:
1. Expense Tracking & Category Management
2. Cash & Bank Book Management with Contra Transfers
3. Profit & Loss Statement Engine
4. Stock Movement & Item-wise Profitability Analysis
5. WhatsApp Payment Reminder Generator
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.database.connection import get_session, init_db
from app.database.models import (
    Party, Product, Invoice, InvoiceItem,
    ExpenseCategory, Expense, BankAccount, CashBankTransaction, CompanyProfile
)
from app.services.expense_service import (
    get_all_categories, create_category, create_expense,
    get_all_expenses, get_expense_summary, delete_expense
)
from app.services.cashbank_service import (
    get_all_accounts, create_account, create_transaction,
    get_transactions, get_account_ledger
)
from app.services.pnl_service import get_profit_loss_statement
from app.services.stock_report_service import get_stock_movement_report


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database schema is up to date before each test."""
    init_db()


def test_expense_categories_seeded_and_crud():
    """Verify default Indian business expense categories are seeded and custom ones can be added."""
    categories = get_all_categories()
    assert len(categories) >= 13
    cat_names = [c["name"] for c in categories]
    assert "Rent" in cat_names
    assert "Salary & Wages" in cat_names
    assert "Transport & Freight" in cat_names

    # Test creating custom category with unique name
    cat_name = f"Hospitality & Snacks"
    existing = [c for c in categories if c["name"] == cat_name]
    if existing:
        custom = existing[0]
    else:
        custom = create_category(cat_name, "Office snacks and hospitality")
    assert custom["name"] == cat_name

    # Test creating an expense
    exp = create_expense({
        "expense_date": date.today(),
        "category_id": custom["id"],
        "description": "Weekly tea and biscuits",
        "amount": 450.0,
        "gst_amount": 0.0,
        "total_amount": 450.0,
        "payment_mode": "Cash"
    })
    assert exp["expense_number"].startswith("EXP-")
    assert exp["amount"] == 450.0

    # Test summary report
    summary = get_expense_summary(start_date=date.today() - timedelta(days=7), end_date=date.today())
    assert summary["grand_total"] >= 450.0
    assert len(summary["categories"]) >= 1

    # Cleanup
    delete_expense(exp["id"])


def test_cashbank_accounts_and_contra():
    """Verify Cash-in-Hand and Bank accounts, receipts, payments, and contra transfers."""
    accounts = get_all_accounts()
    assert len(accounts) >= 1
    cash_acc = next(a for a in accounts if a["account_type"] == "Cash")
    assert cash_acc["account_name"] == "Cash-in-Hand"

    # Create a unique Bank Account
    import uuid
    uniq_name = f"HDFC Current A/C {uuid.uuid4().hex[:6]}"
    bank_acc = create_account({
        "account_name": uniq_name,
        "account_type": "Bank",
        "bank_name": "HDFC Bank",
        "account_number": "50200012345678",
        "ifsc_code": "HDFC0001234",
        "opening_balance": 50000.0,
        "opening_balance_date": date.today()
    })
    assert bank_acc["opening_balance"] == 50000.0

    # Record Receipt into Bank
    rcpt = create_transaction({
        "account_id": bank_acc["id"],
        "txn_date": date.today(),
        "txn_type": "Receipt",
        "description": "Customer NEFT settlement",
        "receipt_amount": 25000.0,
        "payment_amount": 0.0,
        "reference_no": "UTR99887766"
    })
    assert rcpt["receipt_amount"] == 25000.0

    # Record Contra Transfer: Cash Withdrawal from Bank (Receipt in Cash, Payment in Bank)
    contra = create_transaction({
        "account_id": cash_acc["id"],
        "contra_account_id": bank_acc["id"],
        "txn_date": date.today(),
        "txn_type": "Contra",
        "description": "Cash withdrawal from HDFC for petty expenses",
        "receipt_amount": 10000.0,
        "payment_amount": 0.0,
        "reference_no": "CHQ-1002"
    })
    assert contra["txn_type"] == "Contra"

    # Verify updated balances
    updated_accs = {a["id"]: a for a in get_all_accounts()}
    assert updated_accs[bank_acc["id"]]["current_balance"] == 65000.0  # 50k + 25k - 10k
    assert updated_accs[cash_acc["id"]]["current_balance"] >= 10000.0

    # Verify ledger statement
    ledger = get_account_ledger(bank_acc["id"])
    assert ledger["account"]["account_name"] == uniq_name
    assert len(ledger["transactions"]) >= 2


def test_profit_and_loss_engine():
    """Verify Profit & Loss calculation returns structured trading and profit statement."""
    pnl = get_profit_loss_statement()
    assert "revenue" in pnl
    assert "cost_of_goods" in pnl
    assert "gross_profit" in pnl
    assert "operating_expenses" in pnl
    assert "net_profit" in pnl
    assert "monthly_trend" in pnl
    assert len(pnl["monthly_trend"]) == 6


def test_stock_movement_report_engine():
    """Verify item-wise stock movement and profitability analysis."""
    report = get_stock_movement_report()
    assert "items" in report
    assert "totals" in report
    assert "top_sellers" in report
    assert "most_profitable" in report
    assert "low_stock_count" in report
    assert "total_stock_value" in report
    assert report["total_products"] >= 0


def test_whatsapp_reminder_template_generation():
    """Verify WhatsApp payment reminder message formatting and phone sanitization."""
    from app.ui.views.outstanding_view import WhatsAppReminderDialog
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)

    party_sample = {
        "party_id": 999,
        "party_name": "Bharat Traders",
        "phone": "+91 98765-43210",
        "total_outstanding": 125000.50,
        "bucket_0_30": 50000.0,
        "bucket_31_60": 35000.0,
        "bucket_61_90": 25000.0,
        "bucket_90_plus": 15000.50,
    }

    dlg = WhatsAppReminderDialog(party_sample)
    # Check that dialog was initialized and message was pre-filled
    msg_en = dlg.txt_message.toPlainText()
    assert "Bharat Traders" in msg_en
    assert "₹125,000.50" in msg_en
    assert "Overdue Aging Summary" in msg_en

    # Check phone input
    assert "98765" in dlg.inp_phone.text()

    # Switch template to Hindi
    dlg.combo_template.setCurrentIndex(2)
    dlg._update_template()
    msg_hi = dlg.txt_message.toPlainText()
    assert "नमस्ते" in msg_hi
    assert "Bharat Traders" in msg_hi
    assert "₹125,000.50" in msg_hi
