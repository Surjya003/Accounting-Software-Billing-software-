"""
Main Application Window Shell
Houses the sleek sidebar, top header bar, view stack, and keyboard shortcuts.
Unified Accounting + Billing Suite.
"""
from datetime import datetime
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QStatusBar, QFrame, QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QKeySequence, QShortcut, QFont, QColor, QPixmap

from app.config import APP_NAME, APP_VERSION, APP_SUBTITLE
from app.database.connection import get_session
from app.database.models import CompanyProfile
from app.services.license_service import get_license_status
from app.ui.theme import LIGHT_THEME
from app.ui.views import (
    DashboardView, PartyView, VoucherEntryView, LedgerView,
    OutstandingView, DayBookView, TrialBalanceView, GSTReportView, SettingsView,
    ExpenseView, CashBankView, PnLView, StockReportView
)
from app.ui.views.billing import (
    ProductView, InvoiceView, ProformaView, QuotationView, PurchaseOrderView,
    ChallanView, ReturnView, BillingReportsView
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Indian B2B Accounting & Billing Suite")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        
        self.init_ui()
        self.setup_shortcuts()
        self.setup_timer()
        self.refresh_company_header()
        
    def init_ui(self):
        self.setStyleSheet(LIGHT_THEME)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(12, 16, 12, 16)
        s_layout.setSpacing(4)
        
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sidebar_logo.jpg")
        logo_lbl = QLabel()
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo_lbl.setPixmap(pixmap.scaledToWidth(180, Qt.SmoothTransformation))
            logo_lbl.setAlignment(Qt.AlignCenter)
            s_layout.addWidget(logo_lbl)
        else:
            lbl_app = QLabel("BillFlow")
            lbl_app.setObjectName("SidebarTitle")
            s_layout.addWidget(lbl_app)
            
            lbl_sub = QLabel("ACCOUNTING & BILLING SUITE")
            lbl_sub.setObjectName("SidebarSubtitle")
            s_layout.addWidget(lbl_sub)
        
        s_layout.addSpacing(6)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.nav_buttons = {}
        
        # --- BILLING Section ---
        section_bill = QLabel("BILLING")
        section_bill.setObjectName("SidebarSection")
        section_bill.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 8px 8px 4px 8px;")
        s_layout.addWidget(section_bill)
        
        billing_nav = [
            ("dashboard", "Dashboard", True),
            ("invoices", "Invoices", False),
            ("quotations", "Quotations", False),
            ("proforma", "Proforma", False),
            ("challans", "Delivery Challans", False),
            ("products", "Products & Inventory", False),
            ("stock_report", "Stock Movement", False),
            ("purchase_orders", "Purchase Orders", False),
            ("returns", "Returns", False),
            ("billing_reports", "Billing Reports", False),
        ]
        
        for key, label, is_checked in billing_nav:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setChecked(is_checked)
            btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
            self.btn_group.addButton(btn)
            self.nav_buttons[key] = btn
            s_layout.addWidget(btn)

        # --- ACCOUNTING Section ---
        section_acct = QLabel("ACCOUNTING")
        section_acct.setObjectName("SidebarSection")
        section_acct.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")
        s_layout.addWidget(section_acct)
        
        acct_nav = [
            ("parties", "Party Master", False),
            ("voucher", "Voucher Entry", False),
            ("cashbank", "Cash & Bank Book", False),
            ("expenses", "Expense Tracker", False),
            ("ledger", "Party Ledger", False),
            ("outstanding", "Outstanding Dues", False),
            ("daybook", "Day Book", False),
            ("trial_balance", "Trial Balance", False),
            ("pnl", "Profit & Loss A/C", False),
            ("gst", "GST Reports", False),
        ]
        
        for key, label, is_checked in acct_nav:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setChecked(is_checked)
            btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
            self.btn_group.addButton(btn)
            self.nav_buttons[key] = btn
            s_layout.addWidget(btn)
        
        # --- SYSTEM Section ---
        section_sys = QLabel("SYSTEM")
        section_sys.setObjectName("SidebarSection")
        section_sys.setStyleSheet("color: #A69876; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding: 12px 8px 4px 8px;")
        s_layout.addWidget(section_sys)
        
        btn_settings = QPushButton("Settings & Backup")
        btn_settings.setObjectName("NavButton")
        btn_settings.setCheckable(True)
        btn_settings.clicked.connect(lambda: self.navigate_to("settings"))
        self.btn_group.addButton(btn_settings)
        self.nav_buttons["settings"] = btn_settings
        s_layout.addWidget(btn_settings)
        
        s_layout.addStretch()
        
        # Version & License Box in Sidebar footer
        lic = get_license_status()
        self.lbl_lic_badge = QLabel(lic["status_text"])
        self.lbl_lic_badge.setStyleSheet("color: #D4C49E; font-size: 11px; font-weight: 600; padding: 6px;")
        s_layout.addWidget(self.lbl_lic_badge)
        
        main_layout.addWidget(sidebar)
        
        # 2. Right Content Area (Header Bar + Stacked Widget)
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(0)
        
        # Top Header Bar
        header = QFrame()
        header.setObjectName("HeaderBar")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 10)
        
        # Company Info Header
        comp_vbox = QVBoxLayout()
        comp_vbox.setSpacing(2)
        self.lbl_comp_name = QLabel("Sita Ram & Sons Traders")
        self.lbl_comp_name.setObjectName("HeaderTitle")
        self.lbl_comp_gstin = QLabel("GSTIN: 27AABCS1429B1Z8 | FY: 2024-25")
        self.lbl_comp_gstin.setObjectName("HeaderSubtitle")
        comp_vbox.addWidget(self.lbl_comp_name)
        comp_vbox.addWidget(self.lbl_comp_gstin)
        h_layout.addLayout(comp_vbox)
        
        h_layout.addStretch()
        
        # Live Clock
        self.lbl_clock = QLabel()
        self.lbl_clock.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background-color: #F1F5F9; padding: 4px 10px; border-radius: 4px;")
        h_layout.addWidget(self.lbl_clock)
        
        r_layout.addWidget(header)
        
        # Stacked Views
        self.stack = QStackedWidget()
        
        # -- Accounting Views --
        self.view_dashboard = DashboardView()
        self.view_dashboard.navigate_to.connect(self.navigate_to)
        
        self.view_parties = PartyView()
        self.view_parties.navigate_to.connect(self.navigate_to)
        
        self.view_voucher = VoucherEntryView()
        self.view_voucher.navigate_to.connect(self.navigate_to)
        
        self.view_ledger = LedgerView()
        self.view_ledger.navigate_to.connect(self.navigate_to)
        
        self.view_outstanding = OutstandingView()
        self.view_outstanding.navigate_to.connect(self.navigate_to)
        
        self.view_daybook = DayBookView()
        self.view_daybook.navigate_to.connect(self.navigate_to)
        
        self.view_trial_balance = TrialBalanceView()
        self.view_trial_balance.navigate_to.connect(self.navigate_to)
        
        self.view_gst = GSTReportView()
        
        self.view_settings = SettingsView()
        self.view_settings.profile_updated.connect(self.refresh_company_header)
        
        # -- Billing Views --
        self.view_invoices = InvoiceView()
        self.view_quotations = QuotationView()
        self.view_quotations.navigate_to.connect(self.navigate_to)
        self.view_proforma = ProformaView()
        self.view_challans = ChallanView()
        self.view_products = ProductView()
        self.view_purchase_orders = PurchaseOrderView()
        self.view_returns = ReturnView()
        self.view_billing_reports = BillingReportsView()

        # -- Extended Vyapar & TallyPrime Views --
        self.view_expense = ExpenseView()
        self.view_expense.navigate_to.connect(self.navigate_to)
        
        self.view_cashbank = CashBankView()
        self.view_cashbank.navigate_to.connect(self.navigate_to)
        
        self.view_pnl = PnLView()
        self.view_pnl.navigate_to.connect(self.navigate_to)
        
        self.view_stock_report = StockReportView()
        self.view_stock_report.navigate_to.connect(self.navigate_to)
        
        # Register all views in the stack
        self.stack.addWidget(self.view_dashboard)        # index 0
        self.stack.addWidget(self.view_parties)          # index 1
        self.stack.addWidget(self.view_voucher)          # index 2
        self.stack.addWidget(self.view_ledger)           # index 3
        self.stack.addWidget(self.view_outstanding)      # index 4
        self.stack.addWidget(self.view_daybook)          # index 5
        self.stack.addWidget(self.view_trial_balance)    # index 6
        self.stack.addWidget(self.view_gst)              # index 7
        self.stack.addWidget(self.view_settings)         # index 8
        # Billing views (index 9 onwards)
        self.stack.addWidget(self.view_invoices)         # index 9
        self.stack.addWidget(self.view_quotations)       # index 10
        self.stack.addWidget(self.view_proforma)         # index 11
        self.stack.addWidget(self.view_challans)         # index 12
        self.stack.addWidget(self.view_products)         # index 13
        self.stack.addWidget(self.view_purchase_orders)  # index 14
        self.stack.addWidget(self.view_returns)          # index 15
        self.stack.addWidget(self.view_billing_reports)  # index 16
        # Extended Views
        self.stack.addWidget(self.view_expense)          # index 17
        self.stack.addWidget(self.view_cashbank)         # index 18
        self.stack.addWidget(self.view_pnl)              # index 19
        self.stack.addWidget(self.view_stock_report)     # index 20
        
        r_layout.addWidget(self.stack, 1)
        main_layout.addWidget(right_panel, 1)
        
        # Status Bar
        self.statusBar().showMessage(
            "Ready | F1: Debit  F2: Credit  F3: Journal  F4: Cash/Bank  F5: Ledger  F6: Outstanding  F9: Invoice  F10: Products"
        )

    def setup_shortcuts(self):
        # Accounting shortcuts
        QShortcut(QKeySequence("F1"), self, lambda: self.navigate_to("voucher", {"type": "Debit"}))
        QShortcut(QKeySequence("F2"), self, lambda: self.navigate_to("voucher", {"type": "Credit"}))
        QShortcut(QKeySequence("F3"), self, lambda: self.navigate_to("voucher", {"type": "Journal"}))
        QShortcut(QKeySequence("F4"), self, lambda: self.navigate_to("cashbank", {}))
        QShortcut(QKeySequence("F5"), self, lambda: self.navigate_to("ledger", {}))
        QShortcut(QKeySequence("F6"), self, lambda: self.navigate_to("outstanding", {}))
        QShortcut(QKeySequence("F7"), self, lambda: self.navigate_to("daybook", {}))
        QShortcut(QKeySequence("F8"), self, lambda: self.navigate_to("trial_balance", {}))
        # Billing shortcuts
        QShortcut(QKeySequence("F9"), self, lambda: self.navigate_to("invoices", {}))
        QShortcut(QKeySequence("F10"), self, lambda: self.navigate_to("products", {}))
        QShortcut(QKeySequence("F11"), self, lambda: self.navigate_to("purchase_orders", {}))
        QShortcut(QKeySequence("F12"), self, lambda: self.navigate_to("billing_reports", {}))
        # Live Diagnostics & Thread Dump Shortcut
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, self.show_diagnostics_dialog)

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def update_clock(self):
        now_str = datetime.now().strftime("%d %b %Y | %I:%M:%S %p")
        self.lbl_clock.setText(now_str)

    def refresh_company_header(self):
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                self.lbl_comp_name.setText(comp.name or "Vyapar Traders")
                gst_str = f"GSTIN: {comp.gstin}" if comp.gstin else "GSTIN: Unregistered"
                self.lbl_comp_gstin.setText(f"{gst_str} | State: {comp.state or 'Maharashtra'} ({comp.state_code or '27'})")

    def navigate_to(self, view_name: str, params: dict = None):
        if params is None:
            params = {}
            
        view_map = {
            # Accounting views
            "dashboard": (0, self.view_dashboard),
            "parties": (1, self.view_parties),
            "voucher": (2, self.view_voucher),
            "ledger": (3, self.view_ledger),
            "outstanding": (4, self.view_outstanding),
            "daybook": (5, self.view_daybook),
            "trial_balance": (6, self.view_trial_balance),
            "gst": (7, self.view_gst),
            "settings": (8, self.view_settings),
            # Billing views
            "invoices": (9, self.view_invoices),
            "quotations": (10, self.view_quotations),
            "proforma": (11, self.view_proforma),
            "challans": (12, self.view_challans),
            "products": (13, self.view_products),
            "purchase_orders": (14, self.view_purchase_orders),
            "returns": (15, self.view_returns),
            "billing_reports": (16, self.view_billing_reports),
            # Extended Vyapar / TallyPrime features
            "expenses": (17, self.view_expense),
            "cashbank": (18, self.view_cashbank),
            "pnl": (19, self.view_pnl),
            "stock_report": (20, self.view_stock_report),
        }
        
        if view_name not in view_map:
            return
            
        idx, view_widget = view_map[view_name]
        self.stack.setCurrentIndex(idx)
        
        # Check sidebar button
        if view_name in self.nav_buttons:
            self.nav_buttons[view_name].setChecked(True)
            
        # Handle specific view arguments
        if view_name == "dashboard":
            self.view_dashboard.refresh_data()
        elif view_name == "parties":
            if params.get("action") == "new":
                self.view_parties.open_add_dialog()
            else:
                self.view_parties.load_parties()
        elif view_name == "voucher":
            if "type" in params:
                self.view_voucher.set_voucher_type(params["type"])
            self.view_voucher.combo_party.load_parties()
        elif view_name == "ledger":
            self.view_ledger.combo_party.load_parties()
            if "party_id" in params:
                self.view_ledger.set_party(params["party_id"])
        elif view_name == "outstanding":
            self.view_outstanding.tab_receivables.load_data()
            self.view_outstanding.tab_payables.load_data()
        elif view_name == "daybook":
            self.view_daybook.load_data()
        elif view_name == "trial_balance":
            self.view_trial_balance.load_data()
        elif view_name == "invoices":
            self.view_invoices.load_invoices()
        elif view_name == "quotations":
            self.view_quotations.load_data()
        elif view_name == "products":
            self.view_products.load_products()
        elif view_name == "proforma":
            self.view_proforma.load_data()
        elif view_name == "purchase_orders":
            self.view_purchase_orders.load_data()
        elif view_name == "challans":
            self.view_challans.load_data()
        elif view_name == "returns":
            self.view_returns.load_data()
        elif view_name == "billing_reports":
            self.view_billing_reports.refresh_data()
        elif view_name == "expenses":
            self.view_expense.load_data()
        elif view_name == "cashbank":
            self.view_cashbank.load_data()
        elif view_name == "pnl":
            self.view_pnl.load_data()
        elif view_name == "stock_report":
            self.view_stock_report.load_data()

    def show_diagnostics_dialog(self):
        """Displays live system health, memory stats, SQLite pragmas, and dumps thread stacks."""
        from app.core.diagnostics import run_system_health_check, dump_thread_stacks
        report = run_system_health_check()
        dump_thread_stacks()
        
        warn_text = "<br/>".join(f"• {w}" for w in report.get("warnings", []))
        if not warn_text:
            warn_text = "<span style='color:#2F6844;'>None (System running optimally)</span>"
            
        db = report.get("db", {})
        status_color = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"
        msg = (
            f"<b>System Health Status:</b> <span style='color: {status_color}; font-size:14px; font-weight:bold;'>{report['status']}</span><br/><br/>"
            f"<b>Process ID:</b> {report['pid']}<br/>"
            f"<b>RAM Usage:</b> {report['memory_mb']} MB<br/>"
            f"<b>Active Python Threads:</b> {report['active_threads']}<br/>"
            f"<b>Database Latency:</b> {db.get('latency_ms', 'N/A')} ms<br/>"
            f"<b>SQLite Mode:</b> {db.get('journal_mode', 'N/A')} (Lock timeout: {db.get('busy_timeout_ms', 'N/A')} ms)<br/>"
            f"<b>Integrity Check:</b> {db.get('integrity', 'N/A')}<br/><br/>"
            f"<b>Health Warnings:</b><br/>{warn_text}<br/><br/>"
            f"<i>Thread dump and diagnostic logs saved to:</i><br/>"
            f"<code>data/logs/thread_dump.log</code><br/>"
            f"<code>data/logs/app.log</code>"
        )
        box = QMessageBox(self)
        box.setWindowTitle("VyaparLedger — System Diagnostics & Health Check")
        box.setTextFormat(Qt.RichText)
        box.setText(msg)
        box.setIcon(QMessageBox.Information if report['status'] == 'HEALTHY' else QMessageBox.Warning)
        box.exec()


