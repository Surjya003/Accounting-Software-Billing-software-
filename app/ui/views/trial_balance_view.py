"""
Trial Balance Sheet View (Books Sanity Verification)
"""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.services.report_service import get_trial_balance
from app.services.export_service import export_trial_balance_excel
import os

class TrialBalanceView(QWidget):
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
        self.dt_from.setDate(QDate(date.today().year, 4, 1) if date.today().month >= 4 else QDate(date.today().year - 1, 4, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)
        
        lbl_to = QLabel("<b>To Date:</b>")
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)
        
        btn_filter = QPushButton("🔍 Generate Trial Balance")
        btn_filter.setObjectName("PrimaryBtn")
        btn_filter.clicked.connect(self.load_data)
        f_layout.addWidget(btn_filter)
        
        f_layout.addStretch()
        
        btn_excel = QPushButton("📊 Export Excel")
        btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(btn_excel)
        
        layout.addWidget(f_card)
        
        # 2. Sanity Check Banner
        self.banner = QFrame()
        self.banner.setObjectName("Card")
        b_layout = QHBoxLayout(self.banner)
        b_layout.setContentsMargins(14, 10, 14, 10)
        
        self.lbl_status = QLabel("Checking Trial Balance...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
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
            
        self.table.setAlternatingRowColors(True)
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
        
        data = get_trial_balance(from_d, to_d)
        self.current_data = data
        
        # Update Banner
        if data["is_balanced"]:
            self.lbl_status.setText(
                f"✅ <b>Trial Balance is Balanced!</b> | Total Debits = Total Credits (Closing Dr: ₹{data['total_cl_dr']:,.2f} | Closing Cr: ₹{data['total_cl_cr']:,.2f})"
            )
            self.banner.setStyleSheet("#Card { background-color: #ECFDF5; border: 1px solid #A7F3D0; }")
            self.lbl_status.setStyleSheet("font-size: 13px; color: #065F46; font-weight: bold;")
        else:
            diff = abs(data['total_cl_dr'] - data['total_cl_cr'])
            self.lbl_status.setText(
                f"⚠️ <b>Trial Balance Difference: ₹{diff:,.2f}</b> | (Total Closing Dr: ₹{data['total_cl_dr']:,.2f} vs Cr: ₹{data['total_cl_cr']:,.2f})"
            )
            self.banner.setStyleSheet("#Card { background-color: #FEF2F2; border: 1px solid #FECACA; }")
            self.lbl_status.setStyleSheet("font-size: 13px; color: #991B1B; font-weight: bold;")
            
        # Table rows + 1 total row
        rows = data["rows"]
        total_rows = len(rows) + 1
        self.table.setRowCount(total_rows)
        font_bold = QFont()
        font_bold.setBold(True)
        
        for r_idx, r in enumerate(rows):
            it_name = QTableWidgetItem(r["party_name"])
            it_name.setData(Qt.UserRole, r["party_id"])
            it_type = QTableWidgetItem(r["party_type"])
            
            self.table.setItem(r_idx, 0, it_name)
            self.table.setItem(r_idx, 1, it_type)
            
            for c_idx, key in enumerate(["op_dr", "op_cr", "period_dr", "period_cr", "cl_dr", "cl_cr"], start=2):
                val = r[key]
                val_str = f"₹{val:,.2f}" if val > 0 else "-"
                it = QTableWidgetItem(val_str)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c_idx, it)
                
        # Total Row
        tot_idx = total_rows - 1
        it_t_name = QTableWidgetItem("GRAND TOTALS")
        it_t_name.setFont(font_bold)
        it_t_status = QTableWidgetItem("Balanced" if data["is_balanced"] else "Diff")
        it_t_status.setFont(font_bold)
        
        self.table.setItem(tot_idx, 0, it_t_name)
        self.table.setItem(tot_idx, 1, it_t_status)
        
        for c_idx, key in enumerate(["total_op_dr", "total_op_cr", "total_period_dr", "total_period_cr", "total_cl_dr", "total_cl_cr"], start=2):
            val = data[key]
            it = QTableWidgetItem(f"₹{val:,.2f}")
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it.setFont(font_bold)
            if "cl_dr" in key or "cl_cr" in key:
                it.setForeground(QColor("#0284C7"))
            self.table.setItem(tot_idx, c_idx, it)

    def _on_row_double_clicked(self, index):
        item = self.table.item(index.row(), 0)
        if item:
            pid = item.data(Qt.UserRole)
            if pid:
                self.navigate_to.emit("ledger", {"party_id": pid})

    def export_excel(self):
        if not self.current_data:
            return
        try:
            p = export_trial_balance_excel(self.current_data)
            QMessageBox.information(self, "Exported", f"Trial Balance saved to:\n{p}")
            os.startfile(str(p))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export Excel: {e}")
