"""
Traditional Indian Ledger Dashboard View (Bahi Khata)
Features ruled columns, tabular figures, and restrained ink/brass color palette.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap
import os
from app.ui.widgets.stat_card import StatCard
from app.services.report_service import get_dashboard_kpis
from app.ui.theme import get_balance_badge_html, get_voucher_badge_html


class MonthlyTrendChart(QWidget):
    """Custom flat QPainter bar chart showing 6-month comparison in Ink Indigo & Ledger Brass."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # list of {"month_short", "sales", "purchases"}
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, data):
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin_left = 68
        margin_right = 16
        margin_top = 28
        margin_bottom = 36

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        if chart_w <= 0 or chart_h <= 0:
            painter.end()
            return

        # Find max value for scale
        all_vals = [d["sales"] for d in self.data] + [d["purchases"] for d in self.data]
        max_val = max(all_vals) if all_vals and max(all_vals) > 0 else 1.0

        n = len(self.data)
        group_w = chart_w / n
        bar_w = max(group_w * 0.32, 10)
        gap = max(group_w * 0.08, 4)

        # Draw Y-axis gridlines and labels (#D4C49E brass ruled line, #6B6558 muted text)
        painter.setPen(QPen(QColor("#D4C49E"), 1))
        num_gridlines = 4
        for i in range(num_gridlines + 1):
            y_pos = margin_top + chart_h - (i * chart_h / num_gridlines)
            painter.drawLine(int(margin_left), int(y_pos), int(w - margin_right), int(y_pos))
            val = max_val * i / num_gridlines
            painter.setPen(QPen(QColor("#6B6558"), 1))
            painter.setFont(QFont("Consolas", 8))
            if val >= 100000:
                label = f"₹{val/100000:.1f}L"
            elif val >= 1000:
                label = f"₹{val/1000:.0f}K"
            else:
                label = f"₹{val:.0f}"
            painter.drawText(QRect(0, int(y_pos) - 8, margin_left - 8, 16), Qt.AlignRight | Qt.AlignVCenter, label)
            painter.setPen(QPen(QColor("#D4C49E"), 1))

        # Draw Flat Solid Bars (No gradients, flat ink & brass)
        for i, d in enumerate(self.data):
            x_center = margin_left + group_w * i + group_w / 2

            # Debits bar: Solid #2C3E63 (Ink Indigo)
            s_height = (d["sales"] / max_val) * chart_h if max_val > 0 else 0
            s_x = x_center - bar_w - gap / 2
            s_y = margin_top + chart_h - s_height
            painter.setBrush(QBrush(QColor("#2C3E63")))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(s_x, s_y, bar_w, s_height))

            # Credits bar: Solid #A6822E (Ledger Brass)
            p_height = (d["purchases"] / max_val) * chart_h if max_val > 0 else 0
            p_x = x_center + gap / 2
            p_y = margin_top + chart_h - p_height
            painter.setBrush(QBrush(QColor("#A6822E")))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(p_x, p_y, bar_w, p_height))

            # Month label (12px, #6B6558)
            painter.setPen(QPen(QColor("#6B6558"), 1))
            painter.setFont(QFont("Segoe UI", 9))
            lbl_rect = QRect(int(margin_left + group_w * i), int(margin_top + chart_h + 6), int(group_w), 20)
            painter.drawText(lbl_rect, Qt.AlignHCenter | Qt.AlignTop, d["month_short"])

        # Legend (Top right, flat swatches)
        legend_y = 6
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2C3E63"))
        painter.drawRect(int(margin_left), legend_y, 12, 12)
        painter.setPen(QColor("#1B1B18"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(int(margin_left + 16), legend_y + 10, "Debits")

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#A6822E"))
        painter.drawRect(int(margin_left + 80), legend_y, 12, 12)
        painter.setPen(QColor("#1B1B18"))
        painter.drawText(int(margin_left + 96), legend_y + 10, "Credits")

        painter.end()


class DashboardView(QWidget):
    navigate_to = Signal(str, dict)  # view_name, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)  # 24px space between major sections (8px grid)
        
        # 1. Screen Title Header
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        lbl_title = QLabel("Dashboard")
        lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl_title)
        
        lbl_sub = QLabel("Business financial overview and quick actions")
        lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        
        main_layout.addLayout(title_box)
        
        # 2. KPI Rows
        # Row 1: Billing & Inventory KPIs
        kpi_layout_1 = QHBoxLayout()
        kpi_layout_1.setSpacing(16)
        self.card_inv_amt = StatCard("Today's Sales (Invoices)", "₹0.00", "Total sales today", value_color="#2F6844")
        self.card_inv_cnt = StatCard("Invoices Today", "0", "Count of invoices", value_color="#1B1B18")
        self.card_prof = StatCard("Pending Quotations", "0", "Sent proformas", value_color="#A6822E")
        self.card_stock = StatCard("Low Stock Alerts", "0", "Items needing reorder", value_color="#8B2635")
        kpi_layout_1.addWidget(self.card_inv_amt)
        kpi_layout_1.addWidget(self.card_inv_cnt)
        kpi_layout_1.addWidget(self.card_prof)
        kpi_layout_1.addWidget(self.card_stock)
        main_layout.addLayout(kpi_layout_1)
        
        # Row 2: Accounting KPIs
        kpi_layout_2 = QHBoxLayout()
        kpi_layout_2.setSpacing(16)
        self.card_rec = StatCard("Total Receivables (Debtors)", "₹0.00", "Money owed to you", value_color="#2F6844")
        self.card_pay = StatCard("Total Payables (Creditors)", "₹0.00", "Money you owe", value_color="#8B2635")
        self.card_sales = StatCard("Today's Debits", "₹0.00", "Billed today", value_color="#2C3E63")
        self.card_rec_today = StatCard("Today's Collections", "₹0.00", "Collected today", value_color="#1B1B18")
        kpi_layout_2.addWidget(self.card_rec)
        kpi_layout_2.addWidget(self.card_pay)
        kpi_layout_2.addWidget(self.card_sales)
        kpi_layout_2.addWidget(self.card_rec_today)
        main_layout.addLayout(kpi_layout_2)
        
        # 3. Quick Action Toolbar
        action_frame = QFrame()
        action_frame.setObjectName("Card")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(10)
        
        lbl_quick = QLabel("Quick Actions:")
        lbl_quick.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;")
        action_layout.addWidget(lbl_quick)
        
        btn_inv = QPushButton("New Invoice (F9)")
        btn_inv.setObjectName("PrimaryBtn")
        btn_inv.setFixedHeight(36)
        btn_inv.clicked.connect(lambda: self.navigate_to.emit("invoices", {}))
        action_layout.addWidget(btn_inv)
        
        btn_prod = QPushButton("Products (F10)")
        btn_prod.setFixedHeight(36)
        btn_prod.clicked.connect(lambda: self.navigate_to.emit("products", {}))
        action_layout.addWidget(btn_prod)
        
        btn_debit = QPushButton("New Debit (F1)")
        btn_debit.setFixedHeight(36)
        btn_debit.clicked.connect(lambda: self.navigate_to.emit("voucher", {"type": "Debit"}))
        action_layout.addWidget(btn_debit)
        
        btn_credit = QPushButton("New Credit (F2)")
        btn_credit.setFixedHeight(36)
        btn_credit.clicked.connect(lambda: self.navigate_to.emit("voucher", {"type": "Credit"}))
        action_layout.addWidget(btn_credit)
        
        btn_party = QPushButton("Add Party")
        btn_party.setFixedHeight(36)
        btn_party.clicked.connect(lambda: self.navigate_to.emit("parties", {"action": "new"}))
        action_layout.addWidget(btn_party)
        
        action_layout.addStretch()
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.refresh_data)
        action_layout.addWidget(btn_refresh)
        
        main_layout.addWidget(action_frame)
        
        # 4. Three Column Grid
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)
        
        # --- LEFT COLUMN (Debtors & Low Stock) ---
        left_layout = QVBoxLayout()
        left_layout.setSpacing(16)
        
        # Top Debtors
        debtors_frame = QFrame()
        debtors_frame.setObjectName("Card")
        debtors_layout = QVBoxLayout(debtors_frame)
        debtors_layout.setContentsMargins(16, 16, 16, 16)
        
        d_head = QHBoxLayout()
        lbl_d = QLabel("Top Debtors")
        lbl_d.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")
        d_head.addWidget(lbl_d)
        d_head.addStretch()
        debtors_layout.addLayout(d_head)
        
        self.tbl_debtors = QTableWidget()
        self.tbl_debtors.setColumnCount(3)
        self.tbl_debtors.setHorizontalHeaderLabels(["Party Name", "Phone", "Due (₹)"])
        self.tbl_debtors.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_debtors.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_debtors.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_debtors.verticalHeader().setVisible(False)
        self.tbl_debtors.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_debtors.doubleClicked.connect(self._on_debtor_double_clicked)
        debtors_layout.addWidget(self.tbl_debtors)
        left_layout.addWidget(debtors_frame, 1)
        
        # Low Stock
        stock_frame = QFrame()
        stock_frame.setObjectName("Card")
        stock_layout = QVBoxLayout(stock_frame)
        stock_layout.setContentsMargins(16, 16, 16, 16)
        
        s_head = QHBoxLayout()
        lbl_s = QLabel("Low Stock Alerts")
        lbl_s.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600; color:#8B2635;")
        s_head.addWidget(lbl_s)
        s_head.addStretch()
        stock_layout.addLayout(s_head)
        
        self.tbl_stock = QTableWidget()
        self.tbl_stock.setColumnCount(3)
        self.tbl_stock.setHorizontalHeaderLabels(["Product", "Stock", "Min"])
        self.tbl_stock.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_stock.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_stock.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_stock.verticalHeader().setVisible(False)
        self.tbl_stock.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_stock.doubleClicked.connect(lambda: self.navigate_to.emit("products", {}))
        stock_layout.addWidget(self.tbl_stock)
        left_layout.addWidget(stock_frame, 1)
        
        grid_layout.addLayout(left_layout, 1)
        
        # --- CENTER COLUMN (Trend Chart) ---
        chart_frame = QFrame()
        chart_frame.setObjectName("Card")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        
        lbl_chart = QLabel("Monthly Debits vs Credits (6 Months)")
        lbl_chart.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")
        chart_layout.addWidget(lbl_chart)
        
        self.trend_chart = MonthlyTrendChart()
        chart_layout.addWidget(self.trend_chart, 1)
        
        grid_layout.addWidget(chart_frame, 1)
        
        # --- RIGHT COLUMN (Vouchers & Invoices) ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(16)
        
        # Recent Vouchers
        recents_frame = QFrame()
        recents_frame.setObjectName("Card")
        recents_layout = QVBoxLayout(recents_frame)
        recents_layout.setContentsMargins(16, 16, 16, 16)
        
        r_head = QHBoxLayout()
        lbl_r = QLabel("Recent Ledgers")
        lbl_r.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")
        r_head.addWidget(lbl_r)
        r_head.addStretch()
        recents_layout.addLayout(r_head)
        
        self.tbl_recents = QTableWidget()
        self.tbl_recents.setColumnCount(4)
        self.tbl_recents.setHorizontalHeaderLabels(["Date", "Type", "Party", "Amount"])
        self.tbl_recents.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_recents.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_recents.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_recents.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_recents.verticalHeader().setVisible(False)
        self.tbl_recents.setSelectionBehavior(QTableWidget.SelectRows)
        recents_layout.addWidget(self.tbl_recents)
        right_layout.addWidget(recents_frame, 1)
        
        # Recent Invoices
        inv_frame = QFrame()
        inv_frame.setObjectName("Card")
        inv_layout = QVBoxLayout(inv_frame)
        inv_layout.setContentsMargins(16, 16, 16, 16)
        
        i_head = QHBoxLayout()
        lbl_i = QLabel("Recent Invoices")
        lbl_i.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 15px; font-weight: 600;")
        i_head.addWidget(lbl_i)
        i_head.addStretch()
        inv_layout.addLayout(i_head)
        
        self.tbl_invoices = QTableWidget()
        self.tbl_invoices.setColumnCount(4)
        self.tbl_invoices.setHorizontalHeaderLabels(["Date", "Inv #", "Party", "Amount"])
        self.tbl_invoices.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_invoices.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_invoices.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_invoices.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_invoices.verticalHeader().setVisible(False)
        self.tbl_invoices.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_invoices.doubleClicked.connect(lambda: self.navigate_to.emit("invoices", {}))
        inv_layout.addWidget(self.tbl_invoices)
        right_layout.addWidget(inv_frame, 1)
        
        grid_layout.addLayout(right_layout, 1)
        
        main_layout.addLayout(grid_layout, 1)
        self.refresh_data()
        
    def refresh_data(self):
        kpi = get_dashboard_kpis()
        self.card_rec.set_value(f"₹{kpi['total_receivables']:,.2f}")
        self.card_pay.set_value(f"₹{kpi['total_payables']:,.2f}")
        self.card_sales.set_value(f"₹{kpi['today_sales']:,.2f}", f"Month: ₹{kpi['month_sales']:,.2f}")
        self.card_rec_today.set_value(f"₹{kpi['today_collections']:,.2f}")
        
        self.card_inv_amt.set_value(f"₹{kpi.get('today_invoices_amount', 0.0):,.2f}")
        self.card_inv_cnt.set_value(str(kpi.get('today_invoices_count', 0)))
        self.card_prof.set_value(str(kpi.get('pending_proformas_count', 0)))
        self.card_stock.set_value(str(len(kpi.get('low_stock_products', []))))
        
        self.trend_chart.set_data(kpi.get("monthly_trend", []))
        
        mono_font = QFont("Consolas", 10)
        mono_bold = QFont("Consolas", 10)
        mono_bold.setBold(True)
        
        # Debtors
        top_d = kpi.get("top_debtors", [])
        self.tbl_debtors.setRowCount(len(top_d))
        for r, d in enumerate(top_d):
            it_name = QTableWidgetItem(d["name"])
            it_name.setData(Qt.UserRole, d["id"])
            it_phone = QTableWidgetItem(d["phone"] or "-")
            it_amt = QTableWidgetItem(f"₹{d['amount']:,.2f}")
            it_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_amt.setForeground(QColor("#2F6844"))
            it_amt.setFont(mono_bold)
            self.tbl_debtors.setItem(r, 0, it_name)
            self.tbl_debtors.setItem(r, 1, it_phone)
            self.tbl_debtors.setItem(r, 2, it_amt)
            
        # Low Stock
        low_s = kpi.get("low_stock_products", [])
        self.tbl_stock.setRowCount(len(low_s))
        for r, p in enumerate(low_s):
            it_name = QTableWidgetItem(p["name"])
            it_stock = QTableWidgetItem(f"{p['stock_quantity']:.1f}")
            it_stock.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_stock.setForeground(QColor("#8B2635"))
            it_stock.setFont(mono_bold)
            it_min = QTableWidgetItem(f"{p['low_stock_threshold']:.1f}")
            it_min.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tbl_stock.setItem(r, 0, it_name)
            self.tbl_stock.setItem(r, 1, it_stock)
            self.tbl_stock.setItem(r, 2, it_min)
            
        # Recent Vouchers
        vchs = kpi.get("recent_vouchers", [])
        self.tbl_recents.setRowCount(len(vchs))
        for r, v in enumerate(vchs):
            dt = v["voucher_date"]
            d_str = dt.strftime("%d-%m") if hasattr(dt, "strftime") else str(dt)
            it_date = QTableWidgetItem(d_str)
            it_type = QTableWidgetItem(v["voucher_type"])
            it_party = QTableWidgetItem(v["party_name"])
            it_amt = QTableWidgetItem(f"₹{v['total_amount']:,.2f}")
            it_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_amt.setFont(mono_font)
            self.tbl_recents.setItem(r, 0, it_date)
            self.tbl_recents.setItem(r, 1, it_type)
            self.tbl_recents.setItem(r, 2, it_party)
            self.tbl_recents.setItem(r, 3, it_amt)
            
        # Recent Invoices
        invs = kpi.get("recent_invoices", [])
        self.tbl_invoices.setRowCount(len(invs))
        for r, inv in enumerate(invs):
            dt = inv["invoice_date"]
            d_str = dt.strftime("%d-%m") if hasattr(dt, "strftime") else str(dt)
            it_date = QTableWidgetItem(d_str)
            it_num = QTableWidgetItem(inv["invoice_number"])
            it_party = QTableWidgetItem(inv["party_name"])
            it_amt = QTableWidgetItem(f"₹{inv['total_amount']:,.2f}")
            it_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_amt.setFont(mono_font)
            self.tbl_invoices.setItem(r, 0, it_date)
            self.tbl_invoices.setItem(r, 1, it_num)
            self.tbl_invoices.setItem(r, 2, it_party)
            self.tbl_invoices.setItem(r, 3, it_amt)

    def _on_debtor_double_clicked(self, index):
        item = self.tbl_debtors.item(index.row(), 0)
        if item:
            party_id = item.data(Qt.UserRole)
            self.navigate_to.emit("ledger", {"party_id": party_id})



