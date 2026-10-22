"""
Automated UI Form & Dialog Integration Test
Tests all UI dialogs, save handlers, and views in PySide6.
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate

from app.database.connection import init_db
from app.ui.views.party_view import PartyView, PartyDialog
from app.ui.views.voucher_view import VoucherEntryView
from app.ui.views.ledger_view import LedgerView
from app.ui.views.outstanding_view import OutstandingView
from app.ui.views.trial_balance_view import TrialBalanceView
from app.ui.views.gst_report_view import GSTReportView
from app.ui.views.daybook_view import DayBookView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.settings_view import SettingsView

def test_all_ui_dialogs_and_saves():
    app = QApplication.instance() or QApplication(sys.argv)
    init_db()
    
    print("Testing PartyDialog instantiation and save...")
    dlg = PartyDialog()
    dlg.inp_name.setText("Test UI Party Automation")
    dlg.inp_phone.setText("9876543210")
    dlg.spin_op_bal.setValue(5000.0)
    dlg.dt_op_date.setDate(QDate(2026, 8, 17))
    # Call save_party directly
    dlg.save_party()
    print("PartyDialog save OK!")
    
    print("Testing VoucherEntryView instantiation & row add...")
    v_view = VoucherEntryView()
    v_view.add_item_row(False) # Test boolean signal from Qt
    v_view.add_item_row("Test Product", "9999", 2.0, "PCS", 500.0, 0.0, 18)
    print("VoucherEntryView OK!")
    
    print("Testing LedgerView instantiation & refresh...")
    l_view = LedgerView()
    l_view.load_ledger()
    print("LedgerView OK!")
    
    print("Testing OutstandingView instantiation & refresh...")
    o_view = OutstandingView()
    o_view.tab_receivables.load_data()
    o_view.tab_payables.load_data()
    print("OutstandingView OK!")
    
    print("Testing TrialBalanceView instantiation & refresh...")
    tb_view = TrialBalanceView()
    tb_view.load_data()
    print("TrialBalanceView OK!")
    
    print("Testing GSTReportView instantiation & refresh...")
    gst_view = GSTReportView()
    gst_view.tabs.widget(0).load_data()
    gst_view.tabs.widget(1).load_data()
    print("GSTReportView OK!")
    
    print("Testing DayBookView instantiation & refresh...")
    db_view = DayBookView()
    db_view.load_data()
    print("DayBookView OK!")
    
    print("Testing DashboardView instantiation & refresh...")
    dash_view = DashboardView()
    dash_view.refresh_data()
    print("DashboardView OK!")
    
    print("Testing SettingsView instantiation & load...")
    set_view = SettingsView()
    set_view.load_company_profile()
    print("SettingsView OK!")
    
    print("Testing QuotationView & QuotationFormDialog instantiation...")
    from app.ui.views.billing.quotation_view import QuotationView, QuotationFormDialog
    q_view = QuotationView()
    q_view.load_data()
    q_dlg = QuotationFormDialog()
    q_dlg.close()
    print("QuotationView & QuotationFormDialog OK!")

    print("\nALL UI VIEWS AND FORMS PASSED 100%!")

if __name__ == "__main__":
    test_all_ui_dialogs_and_saves()
