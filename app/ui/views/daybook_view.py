"""
Day Book View (Daily Transaction Journal)
"""
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.services.report_service import get_day_book
from app.services.export_service import export_daybook_excel, export_invoice_pdf
from app.services.voucher_service import get_voucher_by_id
from app.config import VOUCHER_TYPES
import os

class DayBookView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # 1. Filter Bar
        f_card = QFrame()
        f_card.setObjectName("Card")
        f_layout = QHBoxLayout(f_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(10)
        
        lbl_from = QLabel("<b>From Date:</b>")
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate(date.today().year, date.today().month, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)
        
        lbl_to = QLabel("<b>To Date:</b>")
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)
        
        lbl_type = QLabel("<b>Voucher Type:</b>")
        f_layout.addWidget(lbl_type)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["All"] + VOUCHER_TYPES)
        f_layout.addWidget(self.combo_type)
        
        btn_filter = QPushButton("🔍 Filter")
        btn_filter.setObjectName("PrimaryBtn")
        btn_filter.clicked.connect(self.load_data)
        f_layout.addWidget(btn_filter)
        
        f_layout.addStretch()
        
        btn_excel = QPushButton("📊 Export Excel")
        btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(btn_excel)
        
        layout.addWidget(f_card)
        
        # 2. Summary Ribbon
        self.ribbon = QFrame()
        self.ribbon.setObjectName("Card")
        r_layout = QHBoxLayout(self.ribbon)
        r_layout.setContentsMargins(12, 8, 12, 8)
        
        self.lbl_summary = QLabel("Loading summary...")
        self.lbl_summary.setStyleSheet("font-size: 13px; color: #1E293B;")
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
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
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
            f"<b>Transactions:</b> {data['count']} | "
            f"<b>Total Debits:</b> ₹{data['total_debit']:,.2f} | "
            f"<b>Total Credits:</b> ₹{data['total_credit']:,.2f} | "
            f"<b>Debit Txns:</b> ₹{data['total_debits_amt']:,.2f} | "
            f"<b>Credit Txns:</b> ₹{data['total_credits_amt']:,.2f}"
        )
        
        rows = data["rows"]
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            font_bold = QFont()
            font_bold.setBold(True)
            
            for r_idx, r in enumerate(rows):
                d_str = r["voucher_date"].strftime("%d-%m-%Y") if hasattr(r["voucher_date"], "strftime") else str(r["voucher_date"])
                
                it_d = QTableWidgetItem(d_str)
                it_t = QTableWidgetItem(r["voucher_type"])
                it_v = QTableWidgetItem(r["voucher_number"])
                it_v.setData(Qt.UserRole, r["id"])
                it_p = QTableWidgetItem(r["party_name"])
                it_p.setFont(font_bold)
                it_ref = QTableWidgetItem(r["reference_no"] or "-")
                it_m = QTableWidgetItem(r["payment_mode"] or "-")
                
                it_dr = QTableWidgetItem(f"₹{r['debit']:,.2f}" if r['debit'] > 0 else "-")
                it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                it_cr = QTableWidgetItem(f"₹{r['credit']:,.2f}" if r['credit'] > 0 else "-")
                it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                self.table.setItem(r_idx, 0, it_d)
                self.table.setItem(r_idx, 1, it_t)
                self.table.setItem(r_idx, 2, it_v)
                self.table.setItem(r_idx, 3, it_p)
                self.table.setItem(r_idx, 4, it_ref)
                self.table.setItem(r_idx, 5, it_m)
                self.table.setItem(r_idx, 6, it_dr)
                self.table.setItem(r_idx, 7, it_cr)
                
                # Print PDF button if invoice
                btn_print = QPushButton("🖨️ PDF")
                btn_print.setStyleSheet("padding: 2px 6px; font-size: 11px;")
                btn_print.clicked.connect(lambda _, vid=r["id"]: self.print_voucher_pdf(vid))
                self.table.setCellWidget(r_idx, 8, btn_print)
        finally:
            self.table.setUpdatesEnabled(True)

    def print_voucher_pdf(self, vid):
        v = get_voucher_by_id(vid)
        if v:
            try:
                p = export_invoice_pdf(v)
                QMessageBox.information(self, "PDF Exported", f"Invoice PDF generated:\n{p}")
                os.startfile(str(p))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")

    def export_excel(self):
        if not self.current_data:
            return
        try:
            p = export_daybook_excel(self.current_data)
            QMessageBox.information(self, "Excel Exported", f"Day Book saved to:\n{p}")
            os.startfile(str(p))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Excel: {e}")
