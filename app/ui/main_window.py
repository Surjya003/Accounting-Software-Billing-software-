"""
Main Application Window Shell for BillFlow Suite
Houses the enterprise sidebar, top header bar, view stack, quick theme toggle,
and keyboard shortcut bindings (F1 to F12).
"""
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QStatusBar, QFrame, QButtonGroup, QMessageBox,
    QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QIcon

from app.config import APP_NAME, APP_VERSION, APP_SUBTITLE
from app.database.connection import get_session
from app.database.models import CompanyProfile
from app.services.license_service import get_license_status
from app.ui.theme import theme_manager, ThemeTokens
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

        self.sidebar_collapsed = False
        self.nav_buttons = {}
        self.nav_labels = {}

        self.init_ui()
        self.setup_shortcuts()
        self.setup_timer()
        self.refresh_company_header()

        # Connect to theme changes to refresh dynamic header items & icons
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)

        s_layout = QVBoxLayout(self.sidebar)
        s_layout.setContentsMargins(10, 14, 10, 14)
        s_layout.setSpacing(4)

        # Top Logo & App Title Row
        logo_box = QHBoxLayout()
        logo_box.setSpacing(8)

        # Sidebar toggle collapse button
        self.btn_toggle_sidebar = QPushButton()
        self.btn_toggle_sidebar.setProperty("variant", "icon_only")
        self.btn_toggle_sidebar.setIcon(theme_manager.icon("menu", color_token="sidebar_text", size=18))
        self.btn_toggle_sidebar.setToolTip("Toggle Sidebar (Ctrl+B)")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        logo_box.addWidget(self.btn_toggle_sidebar)

        self.lbl_app = QLabel("BillFlow")
        self.lbl_app.setObjectName("SidebarTitle")
        logo_box.addWidget(self.lbl_app)
        logo_box.addStretch()
        s_layout.addLayout(logo_box)

        self.lbl_sub = QLabel("ACCOUNTING & BILLING")
        self.lbl_sub.setObjectName("SidebarSubtitle")
        s_layout.addWidget(self.lbl_sub)

        # Scrollable sidebar area for all 21 items
        scroll_sidebar = QScrollArea()
        scroll_sidebar.setWidgetResizable(True)
        scroll_sidebar.setFrameShape(QFrame.NoFrame)
        scroll_sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # --- BILLING Section ---
        self.section_bill = QLabel("BILLING")
        self.section_bill.setObjectName("SidebarSection")
        self.section_bill.setProperty("variant", "section")
        scroll_layout.addWidget(self.section_bill)

        billing_nav = [
            ("dashboard", "Dashboard", "dashboard", True),
            ("invoices", "Invoices", "invoices", False),
            ("quotations", "Quotations", "quotations", False),
            ("proforma", "Proforma", "proforma", False),
            ("challans", "Delivery Challans", "challans", False),
            ("products", "Products & Inventory", "products", False),
            ("stock_report", "Stock Movement", "stock_report", False),
            ("purchase_orders", "Purchase Orders", "purchase_orders", False),
            ("returns", "Returns", "returns", False),
            ("billing_reports", "Billing Reports", "billing_reports", False),
        ]

        for key, label, icon_name, is_checked in billing_nav:
            btn = self._create_nav_button(key, label, icon_name, is_checked)
            self.btn_group.addButton(btn)
            self.nav_buttons[key] = btn
            self.nav_labels[key] = label
            scroll_layout.addWidget(btn)

        # --- ACCOUNTING Section ---
        scroll_layout.addSpacing(8)
        self.section_acct = QLabel("ACCOUNTING")
        self.section_acct.setObjectName("SidebarSection")
        self.section_acct.setProperty("variant", "section")
        scroll_layout.addWidget(self.section_acct)

        acct_nav = [
            ("parties", "Party Master", "parties", False),
            ("voucher", "Voucher Entry", "voucher", False),
            ("cashbank", "Cash & Bank Book", "cashbank", False),
            ("expenses", "Expense Tracker", "expenses", False),
            ("ledger", "Party Ledger", "ledger", False),
            ("outstanding", "Outstanding Dues", "outstanding", False),
            ("daybook", "Day Book", "daybook", False),
            ("trial_balance", "Trial Balance", "trial_balance", False),
            ("pnl", "Profit & Loss A/C", "pnl", False),
            ("gst", "GST Reports", "gst", False),
        ]

        for key, label, icon_name, is_checked in acct_nav:
            btn = self._create_nav_button(key, label, icon_name, is_checked)
            self.btn_group.addButton(btn)
            self.nav_buttons[key] = btn
            self.nav_labels[key] = label
            scroll_layout.addWidget(btn)

        # --- SYSTEM Section ---
        scroll_layout.addSpacing(8)
        self.section_sys = QLabel("SYSTEM")
        self.section_sys.setObjectName("SidebarSection")
        self.section_sys.setProperty("variant", "section")
        scroll_layout.addWidget(self.section_sys)

        btn_settings = self._create_nav_button("settings", "Settings & Backup", "settings", False)
        self.btn_group.addButton(btn_settings)
        self.nav_buttons["settings"] = btn_settings
        self.nav_labels["settings"] = "Settings & Backup"
        scroll_layout.addWidget(btn_settings)

        scroll_layout.addStretch()
        scroll_sidebar.setWidget(scroll_content)
        s_layout.addWidget(scroll_sidebar, 1)

        # License status in Sidebar footer
        lic = get_license_status()
        self.lbl_lic_badge = QLabel(lic["status_text"])
        self.lbl_lic_badge.setProperty("variant", "caption")
        s_layout.addWidget(self.lbl_lic_badge)

        main_layout.addWidget(self.sidebar)

        # 2. Right Content Area (Header Bar + Stacked Widget)
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(0)

        # Top Header Bar
        header = QFrame()
        header.setObjectName("HeaderBar")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 8, 20, 8)
        h_layout.setSpacing(16)

        # Company Info Header
        comp_vbox = QVBoxLayout()
        comp_vbox.setSpacing(2)
        self.lbl_comp_name = QLabel("BillFlow Commercial Traders")
        self.lbl_comp_name.setObjectName("HeaderTitle")
        self.lbl_comp_name.setProperty("variant", "title")

        self.lbl_comp_gstin = QLabel("GSTIN: 27AABCS1429B1Z8 | FY: 2024-25")
        self.lbl_comp_gstin.setObjectName("HeaderSubtitle")
        self.lbl_comp_gstin.setProperty("variant", "subtitle")

        comp_vbox.addWidget(self.lbl_comp_name)
        comp_vbox.addWidget(self.lbl_comp_gstin)
        h_layout.addLayout(comp_vbox)

        h_layout.addStretch()

        # Theme Switcher Quick Toggle (Sun / Moon)
        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setProperty("variant", "icon_only")
        self._update_theme_toggle_icon()
        self.btn_theme_toggle.setToolTip("Quick Switch Theme (Light / Dark)")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.btn_theme_toggle)

        # Live Clock
        self.lbl_clock = QLabel()
        self.lbl_clock.setProperty("variant", "tabular")
        self.lbl_clock.setFont(theme_manager.font("tabular"))
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

        # -- Extended Views --
        self.view_expense = ExpenseView()
        self.view_expense.navigate_to.connect(self.navigate_to)

        self.view_cashbank = CashBankView()
        self.view_cashbank.navigate_to.connect(self.navigate_to)

        self.view_pnl = PnLView()
        self.view_pnl.navigate_to.connect(self.navigate_to)

        self.view_stock_report = StockReportView()
        self.view_stock_report.navigate_to.connect(self.navigate_to)

        # Register all 21 views in the stack
        self.stack.addWidget(self.view_dashboard)        # index 0
        self.stack.addWidget(self.view_parties)          # index 1
        self.stack.addWidget(self.view_voucher)          # index 2
        self.stack.addWidget(self.view_ledger)           # index 3
        self.stack.addWidget(self.view_outstanding)      # index 4
        self.stack.addWidget(self.view_daybook)          # index 5
        self.stack.addWidget(self.view_trial_balance)    # index 6
        self.stack.addWidget(self.view_gst)              # index 7
        self.stack.addWidget(self.view_settings)         # index 8
        self.stack.addWidget(self.view_invoices)         # index 9
        self.stack.addWidget(self.view_quotations)       # index 10
        self.stack.addWidget(self.view_proforma)         # index 11
        self.stack.addWidget(self.view_challans)         # index 12
        self.stack.addWidget(self.view_products)         # index 13
        self.stack.addWidget(self.view_purchase_orders)  # index 14
        self.stack.addWidget(self.view_returns)          # index 15
        self.stack.addWidget(self.view_billing_reports)  # index 16
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

    def _create_nav_button(self, key: str, label: str, icon_name: str, is_checked: bool) -> QPushButton:
        btn = QPushButton(f"  {label}")
        btn.setObjectName("NavButton")
        btn.setProperty("variant", "nav")
        btn.setCheckable(True)
        btn.setChecked(is_checked)
        btn.setIcon(theme_manager.icon(icon_name, color_token="sidebar_text", size=18))
        btn.setIconSize(QSize(18, 18))
        btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
        return btn

    def toggle_sidebar(self):
        """Toggle sidebar between expanded (240px) and collapsed (68px)."""
        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.sidebar_collapsed:
            self.sidebar.setFixedWidth(68)
            self.lbl_app.setVisible(False)
            self.lbl_sub.setVisible(False)
            self.section_bill.setVisible(False)
            self.section_acct.setVisible(False)
            self.section_sys.setVisible(False)
            self.lbl_lic_badge.setVisible(False)
            for key, btn in self.nav_buttons.items():
                btn.setText("")
                btn.setToolTip(self.nav_labels[key])
        else:
            self.sidebar.setFixedWidth(240)
            self.lbl_app.setVisible(True)
            self.lbl_sub.setVisible(True)
            self.section_bill.setVisible(True)
            self.section_acct.setVisible(True)
            self.section_sys.setVisible(True)
            self.lbl_lic_badge.setVisible(True)
            for key, btn in self.nav_buttons.items():
                btn.setText(f"  {self.nav_labels[key]}")
                btn.setToolTip("")

    def _toggle_theme(self):
        theme_manager.toggle_theme()
        self._update_theme_toggle_icon()

    def _update_theme_toggle_icon(self):
        is_dark = theme_manager.current_theme.is_dark
        icon_name = "sun" if is_dark else "moon"
        self.btn_theme_toggle.setIcon(theme_manager.icon(icon_name, color_token="text_primary", size=20))

    def _on_theme_changed(self, tokens: ThemeTokens):
        self._update_theme_toggle_icon()
        # Refresh sidebar icons
        billing_icons = {
            "dashboard": "dashboard", "invoices": "invoices", "quotations": "quotations",
            "proforma": "proforma", "challans": "challans", "products": "products",
            "stock_report": "stock_report", "purchase_orders": "purchase_orders",
            "returns": "returns", "billing_reports": "billing_reports"
        }
        acct_icons = {
            "parties": "parties", "voucher": "voucher", "cashbank": "cashbank",
            "expenses": "expenses", "ledger": "ledger", "outstanding": "outstanding",
            "daybook": "daybook", "trial_balance": "trial_balance", "pnl": "pnl",
            "gst": "gst", "settings": "settings"
        }
        all_icons = {**billing_icons, **acct_icons}
        for key, btn in self.nav_buttons.items():
            ic_name = all_icons.get(key, "info")
            btn.setIcon(theme_manager.icon(ic_name, color_token="sidebar_text", size=18))

    def setup_shortcuts(self):
        # Sidebar shortcut
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_sidebar)
        # Theme toggle shortcut
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)

        # Accounting shortcuts F1-F8
        QShortcut(QKeySequence("F1"), self, lambda: self.navigate_to("voucher", {"type": "Debit"}))
        QShortcut(QKeySequence("F2"), self, lambda: self.navigate_to("voucher", {"type": "Credit"}))
        QShortcut(QKeySequence("F3"), self, lambda: self.navigate_to("voucher", {"type": "Journal"}))
        QShortcut(QKeySequence("F4"), self, lambda: self.navigate_to("cashbank", {}))
        QShortcut(QKeySequence("F5"), self, lambda: self.navigate_to("ledger", {}))
        QShortcut(QKeySequence("F6"), self, lambda: self.navigate_to("outstanding", {}))
        QShortcut(QKeySequence("F7"), self, lambda: self.navigate_to("daybook", {}))
        QShortcut(QKeySequence("F8"), self, lambda: self.navigate_to("trial_balance", {}))

        # Billing shortcuts F9-F12
        QShortcut(QKeySequence("F9"), self, lambda: self.navigate_to("invoices", {"action": "new"}))
        QShortcut(QKeySequence("F10"), self, lambda: self.navigate_to("products", {}))
        QShortcut(QKeySequence("F11"), self, lambda: self.navigate_to("purchase_orders", {}))
        QShortcut(QKeySequence("F12"), self, lambda: self.navigate_to("billing_reports", {}))

        # Diagnostics & Thread Dump
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
                self.lbl_comp_name.setText(comp.name or "BillFlow Commercial Traders")
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
            # Extended views
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
            if params.get("action") == "new":
                QTimer.singleShot(50, self.view_invoices.create_invoice)
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
        success_col = theme_manager.color("success")
        danger_col = theme_manager.color("danger")
        if not warn_text:
            warn_text = f"<span style='color:{success_col};'>None (System running optimally)</span>"

        db = report.get("db", {})
        status_color = success_col if report["status"] == "HEALTHY" else danger_col
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
        box.setWindowTitle(f"{APP_NAME} — System Diagnostics & Health Check")
        box.setTextFormat(Qt.RichText)
        box.setText(msg)
        box.setIcon(QMessageBox.Information if report['status'] == 'HEALTHY' else QMessageBox.Warning)
        box.exec()

    def closeEvent(self, event):
        """Runs PRAGMA wal_checkpoint(TRUNCATE) on MainWindow exit (BUG-09)."""
        try:
            from app.database.connection import checkpoint_wal
            checkpoint_wal(truncate=True)
        except Exception as e:
            logger.warning(f"Error running WAL checkpoint on close: {e}")
        event.accept()

