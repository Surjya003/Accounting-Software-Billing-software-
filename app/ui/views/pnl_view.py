"""
Profit & Loss Statement View
Auto-calculated P&L from vouchers, invoices, and expenses.
Inspired by Vyapar's P&L and TallyPrime's Trading & P&L Account.
"""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDateEdit, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate, QRect, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from app.services.pnl_service import get_profit_loss_statement
from app.config import CURRENCY_SYMBOL
from app.ui.widgets.stat_card import StatCard


class PnLBarChart(QWidget):
    """Monthly Net Profit bar chart using QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(200)
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
        ml, mr, mt, mb = 68, 16, 28, 36
        cw = w - ml - mr
        ch = h - mt - mb
        if cw <= 0 or ch <= 0:
            painter.end()
            return

        all_vals = [d["revenue"] for d in self.data] + [abs(d["net_profit"]) for d in self.data]
        max_val = max(all_vals) if all_vals and max(all_vals) > 0 else 1.0
        n = len(self.data)
        group_w = cw / n
        bar_w = max(group_w * 0.32, 10)

        # Grid lines
        painter.setPen(QPen(QColor("#D4C49E"), 1))
        for i in range(5):
            y = mt + ch - (i * ch / 4)
            painter.drawLine(int(ml), int(y), int(w - mr), int(y))
            val = max_val * i / 4
            painter.setPen(QPen(QColor("#6B6558"), 1))
            painter.setFont(QFont("Consolas", 8))
            if val >= 100000:
                label = f"₹{val/100000:.1f}L"
            elif val >= 1000:
                label = f"₹{val/1000:.0f}K"
            else:
                label = f"₹{val:.0f}"
            painter.drawText(QRect(0, int(y) - 8, ml - 8, 16), Qt.AlignRight | Qt.AlignVCenter, label)
            painter.setPen(QPen(QColor("#D4C49E"), 1))

        for i, d in enumerate(self.data):
            xc = ml + group_w * i + group_w / 2
            # Revenue bar
            rev_h = (d["revenue"] / max_val) * ch if max_val > 0 else 0
            painter.setBrush(QBrush(QColor("#2C3E63")))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(xc - bar_w - 2, mt + ch - rev_h, bar_w, rev_h))

            # Net profit bar
            np_val = d["net_profit"]
            np_h = (abs(np_val) / max_val) * ch if max_val > 0 else 0
            color = QColor("#2F6844") if np_val >= 0 else QColor("#8B2635")
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(xc + 2, mt + ch - np_h, bar_w, np_h))

            # Month label
            painter.setPen(QPen(QColor("#6B6558"), 1))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(QRect(int(xc - group_w / 2), int(mt + ch + 4), int(group_w), 20), Qt.AlignCenter, d["month_short"])

        # Legend
        painter.setFont(QFont("Segoe UI", 9))
        painter.setBrush(QBrush(QColor("#2C3E63")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(w - 200, 6, 12, 12))
        painter.setPen(QPen(QColor("#1B1B18"), 1))
        painter.drawText(QRect(int(w - 184), 4, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, "Revenue")

        painter.setBrush(QBrush(QColor("#2F6844")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(w - 100, 6, 12, 12))
        painter.setPen(QPen(QColor("#1B1B18"), 1))
        painter.drawText(QRect(int(w - 84), 4, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, "Net Profit")

        painter.end()


class ProfitLossView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ──
        header = QHBoxLayout()
        lbl_title = QLabel("📊 Profit & Loss Statement")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")
        header.addWidget(lbl_title)
        header.addStretch()

        header.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        today = date.today()
        fy_start = date(today.year, 4, 1) if today.month >= 4 else date(today.year - 1, 4, 1)
        self.date_from.setDate(QDate(fy_start.year, fy_start.month, fy_start.day))
        header.addWidget(self.date_from)

        header.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        header.addWidget(self.date_to)

        btn_gen = QPushButton("📈 Generate P&L")
        btn_gen.setObjectName("PrimaryBtn")
        btn_gen.setStyleSheet("padding: 8px 18px;")
        btn_gen.clicked.connect(self.load_data)
        header.addWidget(btn_gen)
        layout.addLayout(header)

        # ── KPI Cards ──
        kpi_box = QHBoxLayout()
        kpi_box.setSpacing(12)
        self.card_revenue = StatCard("Total Revenue", f"{CURRENCY_SYMBOL}0.00")
        self.card_cogs = StatCard("Cost of Goods", f"{CURRENCY_SYMBOL}0.00")
        self.card_gross = StatCard("Gross Profit", f"{CURRENCY_SYMBOL}0.00")
        self.card_net = StatCard("Net Profit", f"{CURRENCY_SYMBOL}0.00")
        for card in [self.card_revenue, self.card_cogs, self.card_gross, self.card_net]:
            kpi_box.addWidget(card)
        layout.addLayout(kpi_box)

        # ── Main Content: Statement + Chart side by side ──
        content = QHBoxLayout()
        content.setSpacing(16)

        # Left: P&L Statement Table
        left_frame = QFrame()
        left_frame.setObjectName("Card")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)

        lbl_stmt = QLabel("TRADING & PROFIT AND LOSS ACCOUNT")
        lbl_stmt.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63; letter-spacing: 1px;")
        left_layout.addWidget(lbl_stmt)

        self.stmt_table = QTableWidget()
        self.stmt_table.setColumnCount(2)
        self.stmt_table.setHorizontalHeaderLabels(["Particulars", "Amount (₹)"])
        self.stmt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stmt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.stmt_table.setColumnWidth(1, 180)
        self.stmt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stmt_table.setAlternatingRowColors(False)
        left_layout.addWidget(self.stmt_table)
        content.addWidget(left_frame, 3)

        # Right: Chart + Margin info
        right_frame = QFrame()
        right_frame.setObjectName("Card")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)

        lbl_chart = QLabel("Monthly Revenue vs Net Profit")
        lbl_chart.setStyleSheet("font-size: 13px; font-weight: 600; color: #2C3E63;")
        right_layout.addWidget(lbl_chart)

        self.chart = PnLBarChart()
        right_layout.addWidget(self.chart, 1)

        # Margin indicators
        margin_box = QVBoxLayout()
        margin_box.setSpacing(6)
        self.lbl_gross_margin = QLabel("Gross Margin: —")
        self.lbl_gross_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2F6844;")
        self.lbl_net_margin = QLabel("Net Margin: —")
        self.lbl_net_margin.setStyleSheet("font-size: 14px; font-weight: 700; color: #2C3E63;")
        margin_box.addWidget(self.lbl_gross_margin)
        margin_box.addWidget(self.lbl_net_margin)
        right_layout.addLayout(margin_box)

        content.addWidget(right_frame, 2)
        layout.addLayout(content, 1)

    def load_data(self):
        start = self.date_from.date().toPython()
        end = self.date_to.date().toPython()

        pnl = get_profit_loss_statement(start, end)

        revenue = pnl["revenue"]["total_sales"]
        cogs = pnl["cost_of_goods"]["total_purchases"]
        gross = pnl["gross_profit"]
        net = pnl["net_profit"]
        expenses_total = pnl["operating_expenses"]["total"]
        expense_breakdown = pnl["operating_expenses"]["breakdown"]

        # Update KPI cards
        self.card_revenue.set_value(f"{CURRENCY_SYMBOL}{revenue:,.2f}")
        self.card_cogs.set_value(f"{CURRENCY_SYMBOL}{cogs:,.2f}")
        self.card_gross.set_value(f"{CURRENCY_SYMBOL}{gross:,.2f}")

        net_color = "#2F6844" if net >= 0 else "#8B2635"
        net_label = f"{CURRENCY_SYMBOL}{net:,.2f}" if net >= 0 else f"-{CURRENCY_SYMBOL}{abs(net):,.2f}"
        self.card_net.set_value(net_label)

        # Margins
        self.lbl_gross_margin.setText(f"Gross Margin: {pnl['gross_margin_pct']:.1f}%")
        self.lbl_net_margin.setText(f"Net Margin: {pnl['net_margin_pct']:.1f}%")

        # Build statement table
        rows = []
        rows.append(("REVENUE", "", True, False))
        rows.append(("  Sales / Debit Vouchers", revenue, False, False))
        rows.append(("  Tax Collected (GST)", pnl["revenue"]["tax_collected"], False, False))
        rows.append(("", "", False, False))
        rows.append(("COST OF GOODS SOLD", "", True, False))
        rows.append(("  Purchases / Credit Vouchers", cogs, False, False))
        rows.append(("  Tax Paid (GST on purchases)", pnl["cost_of_goods"]["tax_paid"], False, False))
        rows.append(("", "", False, False))
        rows.append(("GROSS PROFIT", gross, True, True))
        rows.append(("", "", False, False))
        rows.append(("OPERATING EXPENSES", "", True, False))

        for exp in expense_breakdown:
            rows.append((f"  {exp['category']}", exp['amount'], False, False))

        rows.append(("  Total Operating Expenses", expenses_total, False, True))
        rows.append(("", "", False, False))
        rows.append(("NET PROFIT / (LOSS)", net, True, True))

        self.stmt_table.setRowCount(len(rows))
        for i, (label, amount, is_header, is_total) in enumerate(rows):
            lbl_item = QTableWidgetItem(label)
            if is_header:
                lbl_item.setFont(QFont("Segoe UI", 12, QFont.Bold))
                lbl_item.setForeground(QColor("#2C3E63"))
            self.stmt_table.setItem(i, 0, lbl_item)

            if amount != "" and amount is not None:
                val = float(amount) if not isinstance(amount, str) else 0.0
                amt_text = f"{CURRENCY_SYMBOL}{val:,.2f}" if val >= 0 else f"-{CURRENCY_SYMBOL}{abs(val):,.2f}"
                amt_item = QTableWidgetItem(amt_text)
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if is_total:
                    amt_item.setFont(QFont("Consolas", 13, QFont.Bold))
                    if val >= 0:
                        amt_item.setForeground(QColor("#2F6844"))
                    else:
                        amt_item.setForeground(QColor("#8B2635"))
                else:
                    amt_item.setFont(QFont("Consolas", 12))
                self.stmt_table.setItem(i, 1, amt_item)
            else:
                self.stmt_table.setItem(i, 1, QTableWidgetItem(""))

        # Chart
        self.chart.set_data(pnl.get("monthly_trend", []))


# Alias for concise import
PnLView = ProfitLossView

