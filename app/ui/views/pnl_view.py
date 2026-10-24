"""
Profit & Loss Statement View
Auto-calculated P&L from vouchers, invoices, and expenses with reactive charts.
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
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame
)


class PnLBarChart(QWidget):
    """Monthly Net Profit bar chart using QPainter with full theme support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        theme_manager.theme_changed.connect(self.on_theme_changed)

    def on_theme_changed(self, theme_name):
        self.update()

    def set_data(self, data):
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        t = theme_manager.current_theme
        border_col = theme_manager.qcolor("border")
        sec_text_col = theme_manager.qcolor("text_secondary")
        pri_text_col = theme_manager.qcolor("text_primary")
        rev_col = theme_manager.qcolor("accent")
        succ_col = theme_manager.qcolor("success")
        dang_col = theme_manager.qcolor("danger")

        w = self.width()
        h = self.height()
        ml, mr, mt, mb = 68, 16, 28, 36
        cw = w - ml - mr
        ch = h - mt - mb
        if cw <= 0 or ch <= 0:
            painter.end()
            return

        all_vals = [d.get("revenue", 0.0) for d in self.data] + [abs(d.get("net_profit", 0.0)) for d in self.data]
        max_val = max(all_vals) if all_vals and max(all_vals) > 0 else 1.0
        n = len(self.data)
        group_w = cw / n
        bar_w = max(group_w * 0.32, 10)

        # Grid lines
        for i in range(5):
            y = mt + ch - (i * ch / 4)
            painter.setPen(QPen(border_col, 1))
            painter.drawLine(int(ml), int(y), int(w - mr), int(y))
            val = max_val * i / 4
            painter.setPen(QPen(sec_text_col, 1))
            painter.setFont(theme_manager.get_font("caption"))
            if val >= 100000:
                label = f"₹{val/100000:.1f}L"
            elif val >= 1000:
                label = f"₹{val/1000:.0f}K"
            else:
                label = f"₹{val:.0f}"
            painter.drawText(QRect(0, int(y) - 8, ml - 8, 16), Qt.AlignRight | Qt.AlignVCenter, label)

        for i, d in enumerate(self.data):
            xc = ml + group_w * i + group_w / 2
            # Revenue bar
            rev_val = d.get("revenue", 0.0)
            rev_h = (rev_val / max_val) * ch if max_val > 0 else 0
            painter.setBrush(QBrush(rev_col))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(xc - bar_w - 2, mt + ch - rev_h, bar_w, rev_h))

            # Net profit bar
            np_val = d.get("net_profit", 0.0)
            np_h = (abs(np_val) / max_val) * ch if max_val > 0 else 0
            color = succ_col if np_val >= 0 else dang_col
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(xc + 2, mt + ch - np_h, bar_w, np_h))

            # Month label
            painter.setPen(QPen(sec_text_col, 1))
            painter.setFont(theme_manager.get_font("caption", bold=True))
            m_lbl = d.get("month_short") or d.get("month", d.get("name", ""))
            painter.drawText(QRect(int(xc - group_w / 2), int(mt + ch + 4), int(group_w), 20), Qt.AlignCenter, m_lbl)

        # Legend
        painter.setFont(theme_manager.get_font("caption"))
        painter.setBrush(QBrush(rev_col))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(w - 200, 6, 12, 12))
        painter.setPen(QPen(pri_text_col, 1))
        painter.drawText(QRect(int(w - 184), 4, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, "Revenue")

        painter.setBrush(QBrush(succ_col))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(w - 100, 6, 12, 12))
        painter.setPen(QPen(pri_text_col, 1))
        painter.drawText(QRect(int(w - 84), 4, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, "Net Profit")

        painter.end()


class ProfitLossView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── Header ──
        self.header_widget = PageHeaderWidget(
            title="Profit & Loss Statement",
            subtitle="Trading, cost of goods, and net operational profit analysis"
        )

        hdr_filter_box = QHBoxLayout()
        hdr_filter_box.setSpacing(8)

        hdr_filter_box.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        today = date.today()
        fy_start = date(today.year, 4, 1) if today.month >= 4 else date(today.year - 1, 4, 1)
        self.date_from.setDate(QDate(fy_start.year, fy_start.month, fy_start.day))
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        hdr_filter_box.addWidget(self.date_from)

        hdr_filter_box.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        hdr_filter_box.addWidget(self.date_to)

        from app.ui.widgets.quick_date_selector import QuickDateSelector
        self.quick_dates = QuickDateSelector(self.date_from, self.date_to, on_change=self.load_data)
        hdr_filter_box.addWidget(self.quick_dates)

        self.btn_gen = QPushButton("Generate P&L")
        self.btn_gen.setIcon(theme_manager.get_icon("refresh", size=16))
        self.btn_gen.setProperty("variant", "primary")
        self.btn_gen.setFixedHeight(36)
        self.btn_gen.clicked.connect(self.load_data)
        hdr_filter_box.addWidget(self.btn_gen)

        w_hdr = QWidget()
        w_hdr.setLayout(hdr_filter_box)
        self.header_widget.add_custom_action(w_hdr)

        layout.addWidget(self.header_widget)

        # ── KPI Cards ──
        kpi_box = QHBoxLayout()
        kpi_box.setSpacing(12)
        self.card_revenue = StatCard("TOTAL REVENUE", f"{CURRENCY_SYMBOL}0.00", "Billed revenue", token_name="accent")
        self.card_cogs = StatCard("COST OF GOODS", f"{CURRENCY_SYMBOL}0.00", "Purchases & inventory cost", token_name="warning")
        self.card_gross = StatCard("GROSS PROFIT", f"{CURRENCY_SYMBOL}0.00", "Revenue minus COGS", token_name="info")
        self.card_net = StatCard("NET PROFIT", f"{CURRENCY_SYMBOL}0.00", "After operating expenses", token_name="success")
        for card in [self.card_revenue, self.card_cogs, self.card_gross, self.card_net]:
            kpi_box.addWidget(card)
        layout.addLayout(kpi_box)

        # ── Main Content: Statement + Chart side by side ──
        content = QHBoxLayout()
        content.setSpacing(16)

        # Left: P&L Statement Table
        left_frame = CardFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        lbl_stmt = QLabel("TRADING & PROFIT AND LOSS ACCOUNT")
        lbl_stmt.setFont(theme_manager.get_font("subtitle", bold=True))
        left_layout.addWidget(lbl_stmt)

        self.stmt_table = QTableWidget()
        self.stmt_table.setColumnCount(2)
        self.stmt_table.setHorizontalHeaderLabels(["Particulars", "Amount (₹)"])
        self.stmt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stmt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.stmt_table.setColumnWidth(1, 180)
        self.stmt_table.verticalHeader().setDefaultSectionSize(34)
        self.stmt_table.verticalHeader().setVisible(False)
        self.stmt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        left_layout.addWidget(self.stmt_table)
        content.addWidget(left_frame, 3)

        # Right: Chart + Margin info
        right_frame = CardFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        lbl_chart = QLabel("Monthly Revenue vs Net Profit")
        lbl_chart.setFont(theme_manager.get_font("subtitle", bold=True))
        right_layout.addWidget(lbl_chart)

        self.chart = PnLBarChart()
        right_layout.addWidget(self.chart, 1)

        # Margin indicators
        margin_box = QVBoxLayout()
        margin_box.setSpacing(6)
        self.lbl_gross_margin = QLabel("Gross Margin: —")
        self.lbl_gross_margin.setFont(theme_manager.get_font("body", bold=True))
        self.lbl_net_margin = QLabel("Net Margin: —")
        self.lbl_net_margin.setFont(theme_manager.get_font("body", bold=True))
        margin_box.addWidget(self.lbl_gross_margin)
        margin_box.addWidget(self.lbl_net_margin)
        right_layout.addLayout(margin_box)

        content.addWidget(right_frame, 2)
        layout.addLayout(content, 1)

        self.load_data()

    def load_data(self):
        start = self.date_from.date().toPython()
        end = self.date_to.date().toPython()

        from app.ui.async_worker import run_in_background
        run_in_background(
            get_profit_loss_statement,
            on_result=self._on_pnl_loaded,
            on_error=self._on_pnl_error,
            trigger_button=getattr(self, "btn_gen", None),
            start_date=start,
            end_date=end
        )

    def _on_pnl_error(self, exc):
        ThemedMessageBox.critical(self, "Error Generating P&L", f"Could not calculate P&L: {exc}")

    def _on_pnl_loaded(self, pnl):
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
                lbl_item.setFont(theme_manager.get_font("body", bold=True))
                lbl_item.setForeground(theme_manager.qcolor("accent"))
            self.stmt_table.setItem(i, 0, lbl_item)

            if amount != "" and amount is not None:
                val = float(amount) if not isinstance(amount, str) else 0.0
                amt_text = f"{CURRENCY_SYMBOL}{val:,.2f}" if val >= 0 else f"-{CURRENCY_SYMBOL}{abs(val):,.2f}"
                amt_item = QTableWidgetItem(amt_text)
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if is_total:
                    amt_item.setFont(theme_manager.get_font("body", bold=True))
                    if val >= 0:
                        amt_item.setForeground(theme_manager.qcolor("success"))
                    else:
                        amt_item.setForeground(theme_manager.qcolor("danger"))
                else:
                    amt_item.setFont(theme_manager.get_font("body"))
                self.stmt_table.setItem(i, 1, amt_item)
            else:
                self.stmt_table.setItem(i, 1, QTableWidgetItem(""))

        # Chart
        self.chart.set_data(pnl.get("monthly_trend", []))


PnLView = ProfitLossView
