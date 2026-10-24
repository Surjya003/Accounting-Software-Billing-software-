"""
Stock Movement & Item-wise Profitability Report View
Tracks per-product sales/purchase history, stock movement (in/out), and per-item profitability.
"""
from datetime import date, timedelta
import csv
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QDateEdit, QFileDialog,
    QApplication, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.stock_report_service import get_stock_movement_report
from app.config import CURRENCY_SYMBOL
from app.ui.widgets.stat_card import StatCard
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox
)


class StockReportView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_report_data = None
        self.all_items = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── Header ──
        self.header_widget = PageHeaderWidget(
            title="Stock Movement & Item Report",
            subtitle="Item-wise stock in/out tracking, sales, purchase cost, and gross profit analysis"
        )

        btn_export = QPushButton("Export CSV")
        btn_export.setIcon(theme_manager.get_icon("download", size=16))
        btn_export.setProperty("variant", "secondary")
        btn_export.setFixedHeight(36)
        btn_export.clicked.connect(self.export_csv)
        self.header_widget.add_custom_action(btn_export)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        self.header_widget.add_custom_action(btn_refresh)

        layout.addWidget(self.header_widget)

        # ── KPI Cards ──
        self.kpi_box = QHBoxLayout()
        self.kpi_box.setSpacing(12)

        self.card_sales = StatCard("TOTAL SALES REVENUE", f"{CURRENCY_SYMBOL}0.00", "Billed sales in period", token_name="accent")
        self.card_purchases = StatCard("TOTAL PURCHASE COST", f"{CURRENCY_SYMBOL}0.00", "Purchased goods cost", token_name="warning")
        self.card_profit = StatCard("GROSS PROFIT", f"{CURRENCY_SYMBOL}0.00", "Sales minus COGS", token_name="success")
        self.card_stock_val = StatCard("TOTAL STOCK VALUE", f"{CURRENCY_SYMBOL}0.00", "Closing inventory valuation", token_name="info")
        self.card_low_stock = StatCard("LOW STOCK ITEMS", "0", "Require re-order", token_name="danger")

        self.kpi_box.addWidget(self.card_sales)
        self.kpi_box.addWidget(self.card_purchases)
        self.kpi_box.addWidget(self.card_profit)
        self.kpi_box.addWidget(self.card_stock_val)
        self.kpi_box.addWidget(self.card_low_stock)
        layout.addLayout(self.kpi_box)

        # ── Filter Bar ──
        filter_card = CardFrame()
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(10)

        lbl_range = QLabel("Period:")
        lbl_range.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_range)

        self.combo_period = QComboBox()
        self.combo_period.addItems([
            "This Month", "Last Month", "This Quarter", "Financial Year (YTD)", "Last 30 Days", "Custom"
        ])
        self.combo_period.currentIndexChanged.connect(self._on_period_changed)
        f_layout.addWidget(self.combo_period)

        lbl_from = QLabel("From:")
        lbl_from.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)

        lbl_to = QLabel("To:")
        lbl_to.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)

        from app.ui.widgets.quick_date_selector import QuickDateSelector
        self.quick_dates = QuickDateSelector(self.dt_from, self.dt_to, on_change=self.load_data)
        f_layout.addWidget(self.quick_dates)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search by name, HSN, category...")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        f_layout.addWidget(self.inp_search, 2)

        self.combo_category = QComboBox()
        self.combo_category.addItem("All Categories")
        self.combo_category.currentIndexChanged.connect(self.apply_filter)
        f_layout.addWidget(self.combo_category)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setIcon(theme_manager.get_icon("refresh", size=16))
        self.btn_apply.setProperty("variant", "secondary")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self.load_data)
        f_layout.addWidget(self.btn_apply)

        layout.addWidget(filter_card)

        # ── Movement Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Product / Item Name", "HSN", "Category", "Current Stock",
            "Qty In", "Qty Out", "Sales Revenue", "Purchase Cost",
            "Gross Profit", "Margin %", "Stock Value"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 11):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 85)   # HSN
        self.table.setColumnWidth(2, 110)  # Category
        self.table.setColumnWidth(3, 110)  # Current Stock
        self.table.setColumnWidth(4, 90)   # Qty In
        self.table.setColumnWidth(5, 90)   # Qty Out
        self.table.setColumnWidth(6, 120)  # Sales Revenue
        self.table.setColumnWidth(7, 120)  # Purchase Cost
        self.table.setColumnWidth(8, 120)  # Gross Profit
        self.table.setColumnWidth(9, 85)   # Margin %
        self.table.setColumnWidth(10, 120) # Stock Value

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        # ── Bottom Bar ──
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 products")
        self.lbl_count.setFont(theme_manager.get_font("caption"))
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()
        layout.addLayout(bottom)

        self._on_period_changed(0)

    def _on_period_changed(self, idx):
        today = date.today()
        period = self.combo_period.currentText()

        if period == "This Month":
            start = date(today.year, today.month, 1)
            end = today
        elif period == "Last Month":
            first_this_month = date(today.year, today.month, 1)
            end = first_this_month - timedelta(days=1)
            start = date(end.year, end.month, 1)
        elif period == "This Quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start = date(today.year, quarter_month, 1)
            end = today
        elif period == "Financial Year (YTD)":
            fy_start_year = today.year if today.month >= 4 else today.year - 1
            start = date(fy_start_year, 4, 1)
            end = today
        elif period == "Last 30 Days":
            start = today - timedelta(days=30)
            end = today
        else:
            return

        self.dt_from.setDate(QDate(start.year, start.month, start.day))
        self.dt_to.setDate(QDate(end.year, end.month, end.day))
        self.load_data()

    def load_data(self):
        q_from = self.dt_from.date()
        q_to = self.dt_to.date()
        start = date(q_from.year(), q_from.month(), q_from.day())
        end = date(q_to.year(), q_to.month(), q_to.day())

        from app.ui.async_worker import run_in_background
        run_in_background(
            get_stock_movement_report,
            on_result=self._on_stock_report_loaded,
            on_error=self._on_stock_report_error,
            trigger_button=getattr(self, "btn_apply", None),
            start_date=start,
            end_date=end
        )

    def _on_stock_report_error(self, exc):
        ThemedMessageBox.critical(self, "Error", f"Failed to load stock movements: {exc}")

    def _on_stock_report_loaded(self, report):
        self.current_report_data = report

        # Update KPI cards
        summary = report.get("summary", {})
        self.card_sales.set_value(f"{CURRENCY_SYMBOL}{summary.get('total_sales_value', 0.0):,.2f}")
        self.card_purchases.set_value(f"{CURRENCY_SYMBOL}{summary.get('total_purchase_value', 0.0):,.2f}")
        self.card_profit.set_value(f"{CURRENCY_SYMBOL}{summary.get('total_gross_profit', 0.0):,.2f}")
        self.card_stock_val.set_value(f"{CURRENCY_SYMBOL}{summary.get('total_stock_value', 0.0):,.2f}")
        self.card_low_stock.set_value(str(summary.get("low_stock_count", 0)))

        # Update category filter combo
        categories = report.get("categories", [])
        current_cat = self.combo_category.currentText()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItem("All Categories")
        for cat in categories:
            self.combo_category.addItem(cat)
        idx = self.combo_category.findText(current_cat)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)
        self.combo_category.blockSignals(False)

        self.all_items = report.get("items", [])
        self.apply_filter()

    def apply_filter(self):
        query = self.inp_search.text().strip().lower()
        selected_cat = self.combo_category.currentText()

        filtered = self.all_items
        if selected_cat and selected_cat != "All Categories":
            filtered = [it for it in filtered if it.get("category") == selected_cat]

        if query:
            filtered = [
                it for it in filtered
                if query in it.get("name", "").lower()
                or query in (it.get("hsn_code") or "").lower()
                or query in (it.get("category") or "").lower()
            ]

        self._populate_table(filtered)

    def _populate_table(self, items):
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(items))
            for row, it in enumerate(items):
                # 0: Name
                it_name = QTableWidgetItem(it["name"])
                it_name.setData(Qt.UserRole, it["id"])
                self.table.setItem(row, 0, it_name)

                # 1: HSN
                self.table.setItem(row, 1, QTableWidgetItem(it.get("hsn_code") or "—"))

                # 2: Category
                self.table.setItem(row, 2, QTableWidgetItem(it.get("category") or "—"))

                # 3: Current Stock + Unit
                stock = it.get("current_stock", 0.0)
                unit = it.get("unit", "PCS")
                thresh = it.get("low_stock_threshold", 10.0)
                is_low = stock <= thresh

                it_stock = QTableWidgetItem(f"{stock:,.1f} {unit}")
                it_stock.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if is_low:
                    it_stock.setForeground(theme_manager.qcolor("danger"))
                self.table.setItem(row, 3, it_stock)

                # 4: Qty In (Purchased)
                it_in = QTableWidgetItem(f"{it.get('qty_in', 0.0):,.1f}")
                it_in.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, it_in)

                # 5: Qty Out (Sold)
                it_out = QTableWidgetItem(f"{it.get('qty_out', 0.0):,.1f}")
                it_out.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, it_out)

                # 6: Sales Revenue
                sales_rev = it.get("sales_value", 0.0)
                it_sales = QTableWidgetItem(f"₹{sales_rev:,.2f}" if sales_rev > 0 else "—")
                it_sales.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 6, it_sales)

                # 7: Purchase Cost
                purch_cost = it.get("purchase_cost", 0.0)
                it_purch = QTableWidgetItem(f"₹{purch_cost:,.2f}" if purch_cost > 0 else "—")
                it_purch.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 7, it_purch)

                # 8: Gross Profit
                profit = it.get("gross_profit", 0.0)
                it_profit = QTableWidgetItem(f"₹{profit:,.2f}" if (sales_rev > 0 or purch_cost > 0) else "—")
                it_profit.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if profit > 0:
                    it_profit.setForeground(theme_manager.qcolor("success"))
                elif profit < 0:
                    it_profit.setForeground(theme_manager.qcolor("danger"))
                self.table.setItem(row, 8, it_profit)

                # 9: Margin %
                margin = it.get("margin_pct", 0.0)
                it_margin = QTableWidgetItem(f"{margin:.1f}%" if sales_rev > 0 else "—")
                it_margin.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if margin > 0:
                    it_margin.setForeground(theme_manager.qcolor("success"))
                elif margin < 0:
                    it_margin.setForeground(theme_manager.qcolor("danger"))
                self.table.setItem(row, 9, it_margin)

                # 10: Stock Value
                stock_val = it.get("stock_value", 0.0)
                it_val = QTableWidgetItem(f"₹{stock_val:,.2f}")
                it_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 10, it_val)
        finally:
            self.table.setUpdatesEnabled(True)

        self.lbl_count.setText(f"{len(items)} products shown (Total: {len(self.all_items)})")

    def export_csv(self):
        if not self.all_items:
            ThemedMessageBox.warning(self, "No Data", "No stock movement data available to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Stock Movement Report to CSV",
            os.path.expanduser("~/Documents/stock_movement_report.csv"),
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            fieldnames = [
                "Product Name", "HSN Code", "Category", "Current Stock", "Unit",
                "Qty In", "Qty Out", "Sales Revenue (₹)", "Purchase Cost (₹)",
                "Gross Profit (₹)", "Margin (%)", "Stock Valuation (₹)"
            ]

            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for it in self.all_items:
                    writer.writerow([
                        it.get("name", ""),
                        it.get("hsn_code", "") or "",
                        it.get("category", "") or "",
                        f"{it.get('current_stock', 0.0):.2f}",
                        it.get("unit", "PCS"),
                        f"{it.get('qty_in', 0.0):.2f}",
                        f"{it.get('qty_out', 0.0):.2f}",
                        f"{it.get('sales_value', 0.0):.2f}",
                        f"{it.get('purchase_cost', 0.0):.2f}",
                        f"{it.get('gross_profit', 0.0):.2f}",
                        f"{it.get('margin_pct', 0.0):.1f}",
                        f"{it.get('stock_value', 0.0):.2f}",
                    ])

            ThemedMessageBox.information(
                self,
                "Export Successful",
                f"Stock movement report exported successfully to:\n{file_path}"
            )
        except Exception as e:
            ThemedMessageBox.critical(self, "Export Failed", f"Could not export CSV: {e}")
