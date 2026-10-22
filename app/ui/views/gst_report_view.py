"""
GST Reports & Feeder Summaries View (GSTR-1 Outward Sales & GSTR-3B Inward ITC)
"""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.services.report_service import get_gst_summary
from app.ui.widgets.stat_card import StatCard
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.config import EXPORTS_DIR
import os

class GSTTabWidget(QWidget):
    def __init__(self, report_type="Sales", parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.current_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # KPI Row
        kpi_layout = QHBoxLayout()
        self.card_taxable = StatCard("Taxable Turnover", "₹0.00", "Net value before tax", "#0284C7")
        self.card_cgst = StatCard("Total CGST", "₹0.00", "Central tax", "#10B981")
        self.card_sgst = StatCard("Total SGST", "₹0.00", "State tax", "#10B981")
        self.card_igst = StatCard("Total IGST", "₹0.00", "Inter-state tax", "#6366F1")
        self.card_total = StatCard("Total Invoice Value", "₹0.00", "Gross value", "#0F172A")
        
        kpi_layout.addWidget(self.card_taxable)
        kpi_layout.addWidget(self.card_cgst)
        kpi_layout.addWidget(self.card_sgst)
        kpi_layout.addWidget(self.card_igst)
        kpi_layout.addWidget(self.card_total)
        layout.addLayout(kpi_layout)
        
        # Filter
        f_card = QFrame()
        f_card.setObjectName("Card")
        f_layout = QHBoxLayout(f_card)
        f_layout.setContentsMargins(10, 6, 10, 6)
        f_layout.setSpacing(10)
        
        lbl_from = QLabel("<b>From:</b>")
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate(date.today().year, date.today().month, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from)
        
        lbl_to = QLabel("<b>To:</b>")
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to)
        
        btn_filter = QPushButton("🔍 Load GST Summary")
        btn_filter.setObjectName("PrimaryBtn")
        btn_filter.clicked.connect(self.load_data)
        f_layout.addWidget(btn_filter)
        
        f_layout.addStretch()
        
        btn_excel = QPushButton("📊 Export for CA (Excel)")
        btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(btn_excel)
        
        layout.addWidget(f_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Date", "Invoice / Bill No.", "Party Name", "GSTIN",
            "Taxable (₹)", "CGST (₹)", "SGST (₹)", "IGST (₹)", "Total (₹)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in range(3, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
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
        
        data = get_gst_summary(from_d, to_d, report_type=self.report_type)
        self.current_data = data
        
        self.card_taxable.set_value(f"₹{data['total_taxable']:,.2f}")
        self.card_cgst.set_value(f"₹{data['total_cgst']:,.2f}")
        self.card_sgst.set_value(f"₹{data['total_sgst']:,.2f}")
        self.card_igst.set_value(f"₹{data['total_igst']:,.2f}")
        self.card_total.set_value(f"₹{data['total_value']:,.2f}", f"{data['count']} Invoices")
        
        rows = data["rows"]
        total_rows = len(rows) + 1
        self.table.setRowCount(total_rows)
        font_bold = QFont()
        font_bold.setBold(True)
        
        for r_idx, r in enumerate(rows):
            d_str = r["voucher_date"].strftime("%d-%m-%Y") if hasattr(r["voucher_date"], "strftime") else str(r["voucher_date"])
            
            it_d = QTableWidgetItem(d_str)
            it_v = QTableWidgetItem(r["voucher_number"])
            it_p = QTableWidgetItem(r["party_name"])
            it_g = QTableWidgetItem(r["party_gstin"])
            
            self.table.setItem(r_idx, 0, it_d)
            self.table.setItem(r_idx, 1, it_v)
            self.table.setItem(r_idx, 2, it_p)
            self.table.setItem(r_idx, 3, it_g)
            
            for c_idx, key in enumerate(["taxable_value", "cgst", "sgst", "igst", "total_value"], start=4):
                val = r[key]
                it = QTableWidgetItem(f"₹{val:,.2f}" if val > 0 else "-")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c_idx, it)
                
        # Grand Total Row
        tot_idx = total_rows - 1
        it_t_lbl = QTableWidgetItem("GRAND TOTALS")
        it_t_lbl.setFont(font_bold)
        self.table.setItem(tot_idx, 2, it_t_lbl)
        
        for c_idx, key in enumerate(["total_taxable", "total_cgst", "total_sgst", "total_igst", "total_value"], start=4):
            val = data[key]
            it = QTableWidgetItem(f"₹{val:,.2f}")
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it.setFont(font_bold)
            if key == "total_value":
                it.setForeground(QColor("#0284C7"))
            self.table.setItem(tot_idx, c_idx, it)

    def export_excel(self):
        if not self.current_data:
            return
        try:
            filename = f"GST_{self.report_type}_{self.current_data['from_date']}_to_{self.current_data['to_date']}.xlsx"
            out_p = EXPORTS_DIR / filename
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"GST {self.report_type}"
            
            # Write Header
            ws.cell(row=1, column=1, value=f"GST {self.report_type.upper()} SUMMARY REPORT").font = Font(bold=True, size=14)
            ws.cell(row=2, column=1, value=f"Period: {self.current_data['from_date']} to {self.current_data['to_date']}").font = Font(italic=True)
            
            headers = ["Date", "Invoice / Bill No.", "Party Name", "GSTIN", "Taxable Value (₹)", "CGST (₹)", "SGST (₹)", "IGST (₹)", "Total Value (₹)"]
            for col_num, h in enumerate(headers, start=1):
                c = ws.cell(row=4, column=col_num, value=h)
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
                c.alignment = Alignment(horizontal="right" if "₹" in h else "left")
                
            row_num = 4
            for r in self.current_data["rows"]:
                row_num += 1
                d_str = r["voucher_date"].strftime("%d-%m-%Y") if hasattr(r["voucher_date"], "strftime") else str(r["voucher_date"])
                ws.cell(row=row_num, column=1, value=d_str)
                ws.cell(row=row_num, column=2, value=r["voucher_number"])
                ws.cell(row=row_num, column=3, value=r["party_name"])
                ws.cell(row=row_num, column=4, value=r["party_gstin"])
                
                for idx, k in enumerate(["taxable_value", "cgst", "sgst", "igst", "total_value"], start=5):
                    c = ws.cell(row=row_num, column=idx, value=r[k])
                    c.number_format = '#,##0.00'
                    
            # Total row
            row_num += 1
            ws.cell(row=row_num, column=3, value="GRAND TOTALS").font = Font(bold=True)
            for idx, k in enumerate(["total_taxable", "total_cgst", "total_sgst", "total_igst", "total_value"], start=5):
                c = ws.cell(row=row_num, column=idx, value=self.current_data[k])
                c.font = Font(bold=True)
                c.number_format = '#,##0.00'
                
            wb.save(str(out_p))
            QMessageBox.information(self, "Exported", f"GST Report saved to:\n{out_p}")
            os.startfile(str(out_p))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export GST Excel: {e}")


class GSTReportView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(GSTTabWidget("Sales", parent=self), "📤 Outward Supplies (GSTR-1 Sales Feeder)")
        self.tabs.addTab(GSTTabWidget("Purchases", parent=self), "📥 Inward Supplies (GSTR-3B ITC Purchase Feeder)")
        layout.addWidget(self.tabs)
