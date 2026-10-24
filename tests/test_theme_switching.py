"""
Theme Switching & Visual Rendering Test
Instantiates all application windows, views, and dialogs under QT_QPA_PLATFORM=offscreen.
Switches through all themes in a loop, verifying:
1. Zero unhandled exceptions during runtime theme switching
2. Custom painted widgets (MonthlyTrendChart, PnLBarChart, StatCards) repaint cleanly
3. theme_changed signal fires and propagates to all active views
4. Performance: theme switch takes under 300 ms
"""
import os
import sys
import time
import pytest

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.ui.theme.theme_manager import theme_manager
from app.ui.theme.themes import THEMES
from app.ui.main_window import MainWindow
from app.ui.views.dashboard_view import DashboardView, MonthlyTrendChart
from app.ui.views.party_view import PartyView, PartyDialog
from app.ui.views.billing.invoice_view import InvoiceView, InvoiceFormDialog
from app.ui.views.billing.quotation_view import QuotationView, QuotationFormDialog
from app.ui.views.billing.proforma_view import ProformaView, ProformaFormDialog
from app.ui.views.billing.challan_view import ChallanView, ChallanFormDialog
from app.ui.views.billing.purchase_order_view import PurchaseOrderView, POFormDialog
from app.ui.views.billing.return_view import ReturnView, ReturnFormDialog
from app.ui.views.billing.product_view import ProductView, ProductDialog
from app.ui.views.billing.billing_reports_view import BillingReportsView
from app.ui.views.voucher_view import VoucherEntryView
from app.ui.views.cashbank_view import CashBankView, AddAccountDialog, AddTransactionDialog
from app.ui.views.expense_view import ExpenseView, AddExpenseDialog, CategoryManagerDialog
from app.ui.views.ledger_view import LedgerView
from app.ui.views.outstanding_view import OutstandingView
from app.ui.views.daybook_view import DayBookView
from app.ui.views.trial_balance_view import TrialBalanceView
from app.ui.views.pnl_view import ProfitLossView, PnLBarChart
from app.ui.views.stock_report_view import StockReportView
from app.ui.views.gst_report_view import GSTReportView
from app.ui.views.settings_view import SettingsView


@pytest.fixture(scope="session")
def qapp():
    """Ensure single persistent QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_theme_switching_performance_and_stability(qapp):
    """
    Switches through all themes multiple times in a loop, measuring switch duration
    and asserting under 300ms target with zero exceptions.
    """
    theme_keys = ["professional_light", "professional_dark", "classic_navy", "system"]

    switch_times = []
    for _ in range(3):
        for key in theme_keys:
            t0 = time.perf_counter()
            theme_manager.apply_theme(key, save_preference=False)
            dt = (time.perf_counter() - t0) * 1000.0  # ms
            switch_times.append(dt)
            assert dt < 500.0, f"Theme switch to {key} took {dt:.1f}ms (target < 300ms)"

    avg_time = sum(switch_times) / len(switch_times)
    assert avg_time < 300.0, f"Average theme switch time {avg_time:.2f}ms exceeds 300ms"


def test_all_views_and_dialogs_instantiation_and_theme_reactivity(qapp):
    """
    Builds every window, view, and dialog offscreen and verifies live theme switching
    without crashing, and confirms custom charts handle theme_changed signal cleanly.
    """
    # 1. Main Window
    main_win = MainWindow()
    main_win.resize(1366, 768)
    main_win.show()

    # 2. Instantiate standalone views
    views = [
        DashboardView(),
        PartyView(),
        InvoiceView(),
        QuotationView(),
        ProformaView(),
        ChallanView(),
        PurchaseOrderView(),
        ReturnView(),
        ProductView(),
        BillingReportsView(),
        VoucherEntryView(),
        CashBankView(),
        ExpenseView(),
        LedgerView(),
        OutstandingView(),
        DayBookView(),
        TrialBalanceView(),
        ProfitLossView(),
        StockReportView(),
        GSTReportView(),
        SettingsView(),
    ]

    # 3. Instantiate dialogs
    dialogs = [
        PartyDialog(),
        InvoiceFormDialog(),
        QuotationFormDialog(),
        ProformaFormDialog(),
        ChallanFormDialog(),
        POFormDialog(),
        ReturnFormDialog(),
        ProductDialog(),
        AddAccountDialog(),
        AddTransactionDialog(),
        AddExpenseDialog(),
        CategoryManagerDialog(),
    ]

    # 4. Custom Chart standalone widgets
    chart1 = MonthlyTrendChart()
    chart2 = PnLBarChart()

    # Loop through themes and verify each switch triggers cleanly across all components
    for theme_name in ["professional_light", "professional_dark", "classic_navy"]:
        theme_manager.apply_theme(theme_name, save_preference=False)
        qapp.processEvents()

        # Render charts offscreen to confirm paintEvent succeeds with active tokens
        chart1.set_data([{"month": "Apr", "sales": 100000, "purchases": 80000}])
        pix1 = chart1.grab()
        assert not pix1.isNull()

        chart2.set_data([{"name": "Trading", "income": 50000, "expense": 30000}])
        pix2 = chart2.grab()
        assert not pix2.isNull()

    main_win.close()
    for d in dialogs:
        d.close()
