"""
Trial Balance Sheet View (Books Sanity Verification)
"""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont
import os

from app.services.report_service import get_trial_balance
from app.services.export_service import export_trial_balance_pdf, export_trial_balance_excel
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox
)
from app.ui.async_worker import run_in_background
from app.ui.save_dialog import execute_export_pipeline


class TrialBalanceView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 0. Page Header
        self.header_widget = PageHeaderWidget(
            title="Trial Balance",
            subtitle="Double-entry books balance and arithmetic sanity verification"
        )
        self.btn_pdf = QPushButton("Export PDF")
        self.btn_pdf.setIcon(theme_manager.get_icon("file-text", size=16))
        self.btn_pdf.setProperty("variant", "secondary")
        self.btn_pdf.setFixedHeight(36)
        self.btn_pdf.clicked.connect(self.export_pdf)
        self.header_widget.add_custom_action(self.btn_pdf)

        self.btn_excel = QPushButton("Export Excel")
        self.btn_excel.setIcon(theme_manager.get_icon("download", size=16))
        self.btn_excel.setProperty("variant", "secondary")
        self.btn_excel.setFixedHeight(36)
        self.btn_excel.clicked.connect(self.export_excel)
        self.header_widget.add_custom_action(self.btn_excel)
        layout.addWidget(self.header_widget)

        # 1. Filter Bar
        f_card = CardFrame()
        f_layout = QHBoxLayout(f_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(10)

        lbl_from = QLabel("From Date:")
        lbl_from.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate(date.today().year, 4, 1) if date.today().month >= 4 else QDate(date.today().year - 1, 4, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)

        lbl_to = QLabel("To Date:")
        lbl_to.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)

        self.btn_filter = QPushButton("Generate Trial Balance")
        self.btn_filter.setIcon(theme_manager.get_icon("refresh", size=16))
        self.btn_filter.setProperty("variant", "primary")
        self.btn_filter.setFixedHeight(36)
        self.btn_filter.clicked.connect(self.load_data)
        f_layout.addWidget(self.btn_filter)

        f_layout.addStretch()
        layout.addWidget(f_card)

        # 2. Sanity Check Banner
        self.banner = CardFrame()
        b_layout = QHBoxLayout(self.banner)
        b_layout.setContentsMargins(14, 10, 14, 10)

        self.lbl_status = QLabel("Checking Trial Balance...")
        self.lbl_status.setFont(theme_manager.get_font("body", bold=True))
        b_layout.addWidget(self.lbl_status)
        layout.addWidget(self.banner)

        # 3. Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Party / Account Name", "Type",
            "Op Dr (₹)", "Op Cr (₹)",
            "Period Dr (₹)", "Period Cr (₹)",
            "Closing Dr (₹)", "Closing Cr (₹)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 8):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table, 1)

        self.load_data()

    def load_data(self):
        q_f = self.dt_from.date()
        q_t = self.dt_to.date()
        from_d = date(q_f.year(), q_f.month(), q_f.day())
        to_d = date(q_t.year(), q_t.month(), q_t.day())

        self.lbl_status.setText("Calculating Trial Balance...")

        def _on_success(data):
            self._render_data(data)

        def _on_error(e):
            ThemedMessageBox.critical(self, "Error", f"Failed to compute Trial Balance: {e}")

        self._worker = run_in_background(
            get_trial_balance,
            on_result=_on_success,
            on_error=_on_error,
            trigger_button=getattr(self, "btn_filter", None),
            from_date=from_d,
            to_date=to_d
        )

    def _render_data(self, data):
        self.current_data = data

        # Update Banner
        if data["is_balanced"]:
            col = theme_manager.color("success")
            self.lbl_status.setText(
                f"<span style='color: {col}; font-weight:bold;'>[BALANCED]</span> "
                f"Total Debits = Total Credits (Closing Dr: ₹{data['total_cl_dr']:,.2f} | Closing Cr: ₹{data['total_cl_cr']:,.2f})"
            )
        else:
            diff = abs(data['total_cl_dr'] - data['total_cl_cr'])
            col = theme_manager.color("danger")
            self.lbl_status.setText(
                f"<span style='color: {col}; font-weight:bold;'>[DIFFERENCE]</span> "
                f"Discrepancy: ₹{diff:,.2f} | (Closing Dr: ₹{data['total_cl_dr']:,.2f} vs Closing Cr: ₹{data['total_cl_cr']:,.2f})"
            )

        # Table rows + 1 total row
        rows = data["rows"]
        total_rows = len(rows) + 1
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(total_rows)

            for r_idx, r in enumerate(rows):
                it_name = QTableWidgetItem(r["party_name"])
                it_name.setData(Qt.UserRole, r["party_id"])
                it_type = QTableWidgetItem(r["party_type"])

                self.table.setItem(r_idx, 0, it_name)
                self.table.setItem(r_idx, 1, it_type)

                for c_idx, key in enumerate(["op_dr", "op_cr", "period_dr", "period_cr", "cl_dr", "cl_cr"], start=2):
                    val = r[key]
                    val_str = f"₹{val:,.2f}" if val > 0 else "—"
                    it = QTableWidgetItem(val_str)
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(r_idx, c_idx, it)

            # Total Row
            tot_idx = total_rows - 1
            it_t_name = QTableWidgetItem("GRAND TOTALS")
            it_t_name.setFont(theme_manager.get_font("body", bold=True))
            it_t_status = QTableWidgetItem("Balanced" if data["is_balanced"] else "Difference")
            it_t_status.setFont(theme_manager.get_font("body", bold=True))

            self.table.setItem(tot_idx, 0, it_t_name)
            self.table.setItem(tot_idx, 1, it_t_status)

            for c_idx, key in enumerate(["total_op_dr", "total_op_cr", "total_period_dr", "total_period_cr", "total_cl_dr", "total_cl_cr"], start=2):
                val = data[key]
                it = QTableWidgetItem(f"₹{val:,.2f}")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(theme_manager.get_font("body", bold=True))
                if "cl_dr" in key or "cl_cr" in key:
                    it.setForeground(theme_manager.qcolor("accent"))
                self.table.setItem(tot_idx, c_idx, it)
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_row_double_clicked(self, index):
        item = self.table.item(index.row(), 0)
        if item:
            pid = item.data(Qt.UserRole)
            if pid:
                self.navigate_to.emit("ledger", {"party_id": pid})

    def export_pdf(self):
        if not self.current_data or not self.current_data.get("rows"):
            ThemedMessageBox.warning(self, "No Data", "No Trial Balance data to export.")
            return

        to_d = self.dt_to.date().toString("yyyyMMdd")
        suggested = f"Trial_Balance_{to_d}"

        def _generate(out_path):
            return export_trial_balance_pdf(tb_data=self.current_data, output_path=out_path)

        execute_export_pipeline(
            parent=self,
            suggested_name=suggested,
            kind="pdf",
            generator_fn=_generate,
            trigger_button=self.btn_pdf
        )

    def export_excel(self):
        if not self.current_data or not self.current_data.get("rows"):
            ThemedMessageBox.warning(self, "No Data", "No Trial Balance data to export.")
            return

        to_d = self.dt_to.date().toString("yyyyMMdd")
        suggested = f"Trial_Balance_{to_d}"

        def _generate(out_path):
            return export_trial_balance_excel(tb_data=self.current_data, output_path=out_path)

        execute_export_pipeline(
            parent=self,
            suggested_name=suggested,
            kind="xlsx",
            generator_fn=_generate,
            trigger_button=self.btn_excel
        )
