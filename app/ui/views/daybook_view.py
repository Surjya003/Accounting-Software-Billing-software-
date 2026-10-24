"""
Day Book View (Daily Transaction Journal)
"""
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont
import os

from app.services.report_service import get_day_book
from app.services.export_service import export_daybook_excel, export_invoice_pdf
from app.services.voucher_service import get_voucher_by_id
from app.config import VOUCHER_TYPES
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox
)
from app.ui.async_worker import run_in_background


class DayBookView(QWidget):
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
            title="Day Book",
            subtitle="Chronological transaction journal and daily ledger"
        )
        self.btn_pdf = QPushButton("Export PDF")
        self.btn_pdf.setIcon(theme_manager.get_icon("download", size=16))
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
        self.dt_from.setDate(QDate(date.today().year, date.today().month, 1))
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

        from app.ui.widgets.quick_date_selector import QuickDateSelector
        self.quick_dates = QuickDateSelector(self.dt_from, self.dt_to, on_change=self.load_data)
        f_layout.addWidget(self.quick_dates)

        lbl_type = QLabel("Voucher Type:")
        lbl_type.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_type)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["All"] + VOUCHER_TYPES)
        f_layout.addWidget(self.combo_type)

        btn_filter = QPushButton("Filter")
        btn_filter.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_filter.setProperty("variant", "secondary")
        btn_filter.clicked.connect(self.load_data)
        f_layout.addWidget(btn_filter)

        f_layout.addStretch()
        layout.addWidget(f_card)

        # 2. Summary Ribbon
        self.ribbon = CardFrame()
        r_layout = QHBoxLayout(self.ribbon)
        r_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_summary = QLabel("Loading summary...")
        self.lbl_summary.setFont(theme_manager.get_font("body"))
        r_layout.addWidget(self.lbl_summary)
        layout.addWidget(self.ribbon)

        # 3. Day Book Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Date", "Type", "Voucher No.", "Party Name", "Ref No.", "Mode",
            "Debit (₹)", "Credit (₹)", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.load_data()

    def load_data(self):
        q_f = self.dt_from.date()
        q_t = self.dt_to.date()
        from_d = date(q_f.year(), q_f.month(), q_f.day())
        to_d = date(q_t.year(), q_t.month(), q_t.day())
        vtype = self.combo_type.currentText()

        data = get_day_book(from_d, to_d, voucher_type=vtype)
        self.current_data = data

        self.lbl_summary.setText(
            f"Transactions: {data['count']}  |  "
            f"Total Debits: ₹{data['total_debit']:,.2f}  |  "
            f"Total Credits: ₹{data['total_credit']:,.2f}  |  "
            f"Debit Txns: ₹{data['total_debits_amt']:,.2f}  |  "
            f"Credit Txns: ₹{data['total_credits_amt']:,.2f}"
        )

        rows = data["rows"]
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                d_str = r["voucher_date"].strftime("%d-%m-%Y") if hasattr(r["voucher_date"], "strftime") else str(r["voucher_date"])

                it_d = QTableWidgetItem(d_str)
                it_t = QTableWidgetItem(r["voucher_type"])
                it_v = QTableWidgetItem(r["voucher_number"])
                it_v.setData(Qt.UserRole, r["id"])
                it_p = QTableWidgetItem(r["party_name"])
                it_ref = QTableWidgetItem(r["reference_no"] or "—")
                it_m = QTableWidgetItem(r["payment_mode"] or "—")

                it_dr = QTableWidgetItem(f"₹{r['debit']:,.2f}" if r['debit'] > 0 else "—")
                it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                it_cr = QTableWidgetItem(f"₹{r['credit']:,.2f}" if r['credit'] > 0 else "—")
                it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.table.setItem(r_idx, 0, it_d)
                self.table.setItem(r_idx, 1, it_t)
                self.table.setItem(r_idx, 2, it_v)
                self.table.setItem(r_idx, 3, it_p)
                self.table.setItem(r_idx, 4, it_ref)
                self.table.setItem(r_idx, 5, it_m)
                self.table.setItem(r_idx, 6, it_dr)
                self.table.setItem(r_idx, 7, it_cr)

                btn_print = QPushButton("PDF")
                btn_print.setIcon(theme_manager.get_icon("printer", size=14))
                btn_print.setProperty("variant", "ghost")
                btn_print.setFixedHeight(28)
                btn_print.clicked.connect(lambda _, vid=r["id"]: self.print_voucher_pdf(vid))
                self.table.setCellWidget(r_idx, 8, btn_print)
        finally:
            self.table.setUpdatesEnabled(True)

    def print_voucher_pdf(self, vid):
        from app.ui.save_dialog import execute_export_pipeline
        v = get_voucher_by_id(vid)
        if not v:
            ThemedMessageBox.warning(self, "Not Found", f"Voucher #{vid} not found")
            return
        v_num = v.get("voucher_number", f"Voucher_{vid}")
        party = v.get("party_name", "")
        sug = f"{v_num}_{party}" if party else str(v_num)
        execute_export_pipeline(
            parent=self,
            export_fn=lambda out: export_invoice_pdf(v, output_path=out),
            suggested_name=sug,
            kind="pdf",
            toast_title="Voucher PDF Exported"
        )

    def export_pdf(self):
        from app.ui.save_dialog import execute_export_pipeline
        from app.services.export_service import export_daybook_pdf
        d_from = self.dt_from.date().toPython()
        d_to = self.dt_to.date().toPython()
        if not self.current_data or not self.current_data.get("rows"):
            ThemedMessageBox.warning(self, "No Records", "No Day Book transactions found for the selected period.")
            return
        execute_export_pipeline(
            parent=self,
            export_fn=lambda out: export_daybook_pdf(daybook_data=self.current_data, output_path=out),
            suggested_name=f"DayBook_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}",
            kind="pdf",
            toast_title="Day Book PDF Exported"
        )

    def export_excel(self):
        from app.ui.save_dialog import execute_export_pipeline
        from app.services.export_service import export_daybook_excel
        d_from = self.dt_from.date().toPython()
        d_to = self.dt_to.date().toPython()
        if not self.current_data or not self.current_data.get("rows"):
            ThemedMessageBox.warning(self, "No Records", "No Day Book transactions found for the selected period.")
            return
        execute_export_pipeline(
            parent=self,
            export_fn=lambda out: export_daybook_excel(daybook_data=self.current_data, output_path=out),
            suggested_name=f"DayBook_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}",
            kind="xlsx",
            toast_title="Day Book Excel Exported"
        )
