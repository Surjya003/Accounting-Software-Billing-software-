"""
Stock Movement & Item-wise Profitability Report View
Tracks per-product sales/purchase history, stock movement (in/out), and per-item profitability.
Inspired by Vyapar's Item Report and TallyPrime's Stock Summary & Movement Analysis.
"""
from datetime import date, timedelta
import csv
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QDateEdit, QMessageBox, QFileDialog,
    QApplication, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.stock_report_service import get_stock_movement_report
from app.config import CURRENCY_SYMBOL
from app.ui.widgets.stat_card import StatCard


class StockReportView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_report_data = None
        self.all_items = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ──
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("📦 Stock Movement & Item Report")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")
        lbl_sub = QLabel("Item-wise stock in/out tracking, sales, purchase cost, and gross profit analysis")
        lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_export = QPushButton("📊 Export CSV")
        btn_export.setStyleSheet("padding: 7px 14px; font-size: 12px;")
        btn_export.clicked.connect(self.export_csv)
        header.addWidget(btn_export)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("PrimaryBtn")
        btn_refresh.setStyleSheet("padding: 7px 16px; font-size: 12px;")
        btn_refresh.clicked.connect(self.load_data)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # ── KPI Cards ──
        self.kpi_box = QHBoxLayout()
        self.kpi_box.setSpacing(12)

        self.card_sales = StatCard("Total Sales Revenue", f"{CURRENCY_SYMBOL}0.00", "Billed sales in period", "#2C3E63")
        self.card_purchases = StatCard("Total Purchase Cost", f"{CURRENCY_SYMBOL}0.00", "Purchased goods cost", "#A6822E")
        self.card_profit = StatCard("Gross Profit", f"{CURRENCY_SYMBOL}0.00", "Sales minus COGS", "#2F6844")
        self.card_stock_val = StatCard("Total Stock Value", f"{CURRENCY_SYMBOL}0.00", "Closing inventory valuation", "#0284C7")
        self.card_low_stock = StatCard("Low Stock Items", "0", "Require re-order", "#8B2635")

        self.kpi_box.addWidget(self.card_sales)
        self.kpi_box.addWidget(self.card_purchases)
        self.kpi_box.addWidget(self.card_profit)
        self.kpi_box.addWidget(self.card_stock_val)
        self.kpi_box.addWidget(self.card_low_stock)
        layout.addLayout(self.kpi_box)

        # ── Filter Bar ──
        filter_card = QFrame()
        filter_card.setObjectName("Card")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(10)

        # Quick Range Selector
        lbl_range = QLabel("<b>Period:</b>")
        lbl_range.setStyleSheet("color: #1B1B18; font-size: 12px;")
        f_layout.addWidget(lbl_range)

        self.combo_period = QComboBox()
        self.combo_period.addItems([
            "This Month", "Last Month", "This Quarter", "Financial Year (YTD)", "Last 30 Days", "Custom"
        ])
        self.combo_period.currentIndexChanged.connect(self._on_period_changed)
        f_layout.addWidget(self.combo_period)

        # Date Pickers
        lbl_from = QLabel("From:")
        lbl_from.setStyleSheet("color: #6B6558; font-size: 12px;")
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)

        lbl_to = QLabel("To:")
        lbl_to.setStyleSheet("color: #6B6558; font-size: 12px;")
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)

        # Search box with debounce
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("🔍 Search by product name, HSN code, or category...")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        f_layout.addWidget(self.inp_search, 2)

        # Category filter combo
        self.combo_category = QComboBox()
        self.combo_category.addItem("All Categories")
        self.combo_category.currentIndexChanged.connect(self.apply_filter)
        f_layout.addWidget(self.combo_category)

        # Apply Dates Button
        btn_apply = QPushButton("Apply")
        btn_apply.setStyleSheet("padding: 4px 12px; font-size: 12px;")
        btn_apply.clicked.connect(self.load_data)
        f_layout.addWidget(btn_apply)

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
        self.table.setColumnWidth(3, 105)  # Current Stock
        self.table.setColumnWidth(4, 80)   # Qty In
        self.table.setColumnWidth(5, 80)   # Qty Out
        self.table.setColumnWidth(6, 120)  # Sales Revenue
        self.table.setColumnWidth(7, 120)  # Purchase Cost
        self.table.setColumnWidth(8, 115)  # Gross Profit
        self.table.setColumnWidth(9, 85)   # Margin %
        self.table.setColumnWidth(10, 120) # Stock Value

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.table, 1)

        # Initialize dates to This Month
        self._set_period_this_month()
        self.load_data()

    def _set_period_this_month(self):
        today = date.today()
        first_day = today.replace(day=1)
        self.dt_from.setDate(QDate(first_day.year, first_day.month, first_day.day))
        self.dt_to.setDate(QDate(today.year, today.month, today.day))

    def _on_period_changed(self, idx):
        today = date.today()
        text = self.combo_period.currentText()
        if text == "This Month":
            first_day = today.replace(day=1)
            self.dt_from.setDate(QDate(first_day.year, first_day.month, first_day.day))
            self.dt_to.setDate(QDate(today.year, today.month, today.day))
        elif text == "Last Month":
            first_this_month = today.replace(day=1)
            last_day_prev = first_this_month - timedelta(days=1)
            first_day_prev = last_day_prev.replace(day=1)
            self.dt_from.setDate(QDate(first_day_prev.year, first_day_prev.month, first_day_prev.day))
            self.dt_to.setDate(QDate(last_day_prev.year, last_day_prev.month, last_day_prev.day))
        elif text == "This Quarter":
            q_month = ((today.month - 1) // 3) * 3 + 1
            start_q = date(today.year, q_month, 1)
            self.dt_from.setDate(QDate(start_q.year, start_q.month, start_q.day))
            self.dt_to.setDate(QDate(today.year, today.month, today.day))
        elif text == "Financial Year (YTD)":
            fy_year = today.year if today.month >= 4 else today.year - 1
            start_fy = date(fy_year, 4, 1)
            self.dt_from.setDate(QDate(start_fy.year, start_fy.month, start_fy.day))
            self.dt_to.setDate(QDate(today.year, today.month, today.day))
        elif text == "Last 30 Days":
            start_30 = today - timedelta(days=30)
            self.dt_from.setDate(QDate(start_30.year, start_30.month, start_30.day))
            self.dt_to.setDate(QDate(today.year, today.month, today.day))
        
        if text != "Custom":
            self.load_data()

    def load_data(self):
        q_start = self.dt_from.date()
        q_end = self.dt_to.date()
        start_d = date(q_start.year(), q_start.month(), q_start.day())
        end_d = date(q_end.year(), q_end.month(), q_end.day())

        report = get_stock_movement_report(start_date=start_d, end_date=end_d)
        self.current_report_data = report
        self.all_items = report.get("items", [])

        # Update KPI cards
        totals = report.get("totals", {})
        self.card_sales.set_value(f"{CURRENCY_SYMBOL}{totals.get('total_sales_value', 0):,.2f}")
        self.card_purchases.set_value(f"{CURRENCY_SYMBOL}{totals.get('total_purchase_value', 0):,.2f}")
        
        profit = totals.get("total_profit", 0)
        sales_val = totals.get("total_sales_value", 0)
        avg_margin = (profit / sales_val * 100) if sales_val > 0 else 0.0
        self.card_profit.set_value(f"{CURRENCY_SYMBOL}{profit:,.2f}", f"Avg Margin: {avg_margin:.1f}%")
        self.card_stock_val.set_value(f"{CURRENCY_SYMBOL}{report.get('total_stock_value', 0):,.2f}")
        self.card_low_stock.set_value(str(report.get("low_stock_count", 0)), "Threshold <= 10")

        # Update category filter dropdown
        categories = sorted(list({i["category"] for i in self.all_items if i.get("category")}))
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

        self.apply_filter()

    def apply_filter(self):
        query = self.inp_search.text().strip().lower()
        selected_cat = self.combo_category.currentText()

        filtered = []
        for item in self.all_items:
            # Category match
            if selected_cat != "All Categories" and item.get("category") != selected_cat:
                continue
            # Search text match
            if query:
                name_match = query in item.get("name", "").lower()
                hsn_match = query in item.get("hsn_code", "").lower()
                cat_match = query in item.get("category", "").lower()
                if not (name_match or hsn_match or cat_match):
                    continue
            filtered.append(item)

        self.populate_table(filtered)

    def populate_table(self, items):
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(items))
            font_bold = QFont()
            font_bold.setBold(True)

            for r_idx, item in enumerate(items):
                # 0. Product Name
                it_name = QTableWidgetItem(item["name"])
                it_name.setData(Qt.UserRole, item["id"])
                it_name.setFont(font_bold)

                # 1. HSN
                it_hsn = QTableWidgetItem(item["hsn_code"] or "—")

                # 2. Category
                it_cat = QTableWidgetItem(item["category"] or "General")

                # 3. Current Stock
                unit = item["unit"] or "Pcs"
                stock_qty = item["current_stock"]
                it_stock = QTableWidgetItem(f"{stock_qty:g} {unit}")
                it_stock.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if stock_qty <= 10:
                    it_stock.setForeground(QColor("#8B2635"))
                    it_stock.setFont(font_bold)

                # 4. Qty In (Purchased)
                it_qin = QTableWidgetItem(f"{item['qty_purchased']:g}")
                it_qin.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # 5. Qty Out (Sold)
                it_qout = QTableWidgetItem(f"{item['qty_sold']:g}")
                it_qout.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # 6. Sales Revenue
                it_rev = QTableWidgetItem(f"{CURRENCY_SYMBOL}{item['sales_revenue']:,.2f}")
                it_rev.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_rev.setFont(font_bold)

                # 7. Purchase Cost
                it_cost = QTableWidgetItem(f"{CURRENCY_SYMBOL}{item['purchase_cost']:,.2f}")
                it_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # 8. Gross Profit
                profit = item["profit"]
                it_profit = QTableWidgetItem(f"{CURRENCY_SYMBOL}{profit:,.2f}")
                it_profit.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_profit.setFont(font_bold)
                if profit > 0:
                    it_profit.setForeground(QColor("#2F6844"))
                elif profit < 0:
                    it_profit.setForeground(QColor("#8B2635"))

                # 9. Margin %
                margin = item["margin_pct"]
                it_margin = QTableWidgetItem(f"{margin:.1f}%")
                it_margin.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if margin >= 20:
                    it_margin.setForeground(QColor("#2F6844"))
                elif margin < 5:
                    it_margin.setForeground(QColor("#8B2635"))

                # 10. Stock Value
                it_val = QTableWidgetItem(f"{CURRENCY_SYMBOL}{item['stock_value']:,.2f}")
                it_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.table.setItem(r_idx, 0, it_name)
                self.table.setItem(r_idx, 1, it_hsn)
                self.table.setItem(r_idx, 2, it_cat)
                self.table.setItem(r_idx, 3, it_stock)
                self.table.setItem(r_idx, 4, it_qin)
                self.table.setItem(r_idx, 5, it_qout)
                self.table.setItem(r_idx, 6, it_rev)
                self.table.setItem(r_idx, 7, it_cost)
                self.table.setItem(r_idx, 8, it_profit)
                self.table.setItem(r_idx, 9, it_margin)
                self.table.setItem(r_idx, 10, it_val)
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_table_double_clicked(self, index):
        item = self.table.item(index.row(), 0)
        if item:
            prod_id = item.data(Qt.UserRole)
            self.navigate_to.emit("products", {"product_id": prod_id})

    def export_csv(self):
        if not self.all_items:
            QMessageBox.warning(self, "No Data", "No stock movement data available to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Stock Movement Report", "Stock_Movement_Report.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Product Name", "HSN", "Category", "Current Stock", "Unit",
                    "Qty Purchased", "Qty Sold", "Sales Revenue (INR)",
                    "Purchase Cost (INR)", "Gross Profit (INR)", "Margin (%)", "Stock Value (INR)"
                ])
                for it in self.all_items:
                    writer.writerow([
                        it["name"], it["hsn_code"], it["category"], it["current_stock"], it["unit"],
                        it["qty_purchased"], it["qty_sold"], it["sales_revenue"],
                        it["purchase_cost"], it["profit"], it["margin_pct"], it["stock_value"]
                    ])
            QMessageBox.information(self, "Export Successful", f"Stock movement report exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export CSV: {e}")
