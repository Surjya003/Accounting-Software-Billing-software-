"""
Traditional Indian Ledger Statement View (Bahi Khata)
Features ruled columns, double header rule, monospaced tabular amounts, and Ink/Brass palette.
"""
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.ui.widgets.party_combo import PartyComboBox
from app.services.ledger_service import get_party_ledger_statement
from app.services.export_service import export_party_ledger_pdf, export_party_ledger_excel
import os


class LedgerView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_ledger_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)  # 24px space between major sections
        
        # 1. Screen Title Header
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        lbl_title = QLabel("Party Ledger")
        lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl_title)
        
        lbl_sub = QLabel("Detailed statement of accounts, transaction history, and running balances")
        lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        
        layout.addLayout(title_box)
        
        # 2. Filter Bar
        filter_card = QFrame()
        filter_card.setObjectName("Card")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(16, 16, 16, 16)
        f_layout.setSpacing(12)
        
        lbl_p = QLabel("Party:")
        lbl_p.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")
        f_layout.addWidget(lbl_p)
        
        self.combo_party = PartyComboBox()
        self.combo_party.setFixedHeight(36)
        self.combo_party.party_changed.connect(self.load_ledger)
        f_layout.addWidget(self.combo_party, 2)
        
        lbl_from = QLabel("From:")
        lbl_from.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setFixedHeight(36)
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate(date.today().year, 4, 1) if date.today().month >= 4 else QDate(date.today().year - 1, 4, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from, 1)
        
        lbl_to = QLabel("To:")
        lbl_to.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558;")
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setFixedHeight(36)
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to, 1)
        
        btn_view = QPushButton("View Ledger")
        btn_view.setObjectName("PrimaryBtn")
        btn_view.setFixedHeight(36)
        btn_view.clicked.connect(self.load_ledger)
        f_layout.addWidget(btn_view)
        
        f_layout.addStretch()
        
        # Action Buttons (36px height, 6px radius)
        self.btn_pdf = QPushButton("PDF Statement")
        self.btn_pdf.setFixedHeight(36)
        self.btn_pdf.clicked.connect(self.export_pdf)
        f_layout.addWidget(self.btn_pdf)
        
        self.btn_excel = QPushButton("Export Excel")
        self.btn_excel.setFixedHeight(36)
        self.btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(self.btn_excel)
        
        self.btn_whatsapp = QPushButton("Copy WhatsApp Text")
        self.btn_whatsapp.setFixedHeight(36)
        self.btn_whatsapp.clicked.connect(self.copy_whatsapp_summary)
        f_layout.addWidget(self.btn_whatsapp)
        
        layout.addWidget(filter_card)
        
        # 3. Party Summary Header Card
        self.summary_card = QFrame()
        self.summary_card.setObjectName("Card")
        s_layout = QHBoxLayout(self.summary_card)
        s_layout.setContentsMargins(16, 16, 16, 16)
        s_layout.setSpacing(16)
        
        # Left side: Party details
        self.lbl_p_info = QLabel("<b>Party Details:</b> Please select a party above to view ledger statement")
        self.lbl_p_info.setStyleSheet("font-size: 13px; color: #1B1B18; line-height: 1.4;")
        s_layout.addWidget(self.lbl_p_info, 3)
        
        # Right side: Closing Balance headline (24px bold tabular font)
        self.bal_vbox = QVBoxLayout()
        self.bal_vbox.setSpacing(2)
        self.bal_vbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.lbl_bal_sub = QLabel("")
        self.lbl_bal_sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bal_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        self.bal_vbox.addWidget(self.lbl_bal_sub)
        
        self.lbl_bal_headline = QLabel("")
        self.lbl_bal_headline.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bal_headline.setStyleSheet("font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: #6B6558;")
        self.bal_vbox.addWidget(self.lbl_bal_headline)
        
        s_layout.addLayout(self.bal_vbox, 2)
        layout.addWidget(self.summary_card)
        
        # 4. Transaction Ledger Table (Signature Ruled Columns)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Type", "Product", "Voucher / Ref No.", "Particulars / Narration",
            "Debit (₹)", "Credit (₹)", "Running Balance (₹)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.table.verticalHeader().setDefaultSectionSize(36)  # Minimum 36px table row height
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)  # Ruled vertical & horizontal brass lines
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table, 1)

    def set_party(self, party_id: int):
        self.combo_party.set_selected_party_id(party_id)
        self.load_ledger()

    def load_ledger(self):
        party_id = self.combo_party.get_selected_party_id()
        if not party_id:
            self.lbl_p_info.setText("Please select a party above.")
            self.lbl_bal_sub.setText("")
            self.lbl_bal_headline.setText("")
            self.table.setRowCount(0)
            return
            
        q_from = self.dt_from.date()
        q_to = self.dt_to.date()
        from_d = date(q_from.year(), q_from.month(), q_from.day())
        to_d = date(q_to.year(), q_to.month(), q_to.day())
        
        try:
            data = get_party_ledger_statement(party_id, from_d, to_d)
            self.current_ledger_data = data
            
            p = data["party"]
            gst_str = p.get('gstin') or "Unregistered"
            phone_str = p.get('phone') or "N/A"
            city_str = p.get('city') or ""
            state_str = p.get('state') or ""
            location = f"{city_str}, {state_str}".strip(", ")
            
            self.lbl_p_info.setText(
                f"<span style='font-family: \"Bahnschrift\", \"Segoe UI Semibold\", sans-serif; font-size: 15px; font-weight: 600; color: #1B1B18;'>{p['name']}</span> "
                f"<span style='font-size: 12px; color: #6B6558;'>({location or 'Local'})</span><br/>"
                f"<span style='font-size: 12px; color: #6B6558;'>GSTIN: {gst_str} | Phone: {phone_str} | Credit Period: {p.get('credit_period_days', 30)} Days</span>"
            )
            
            op_amt = data["opening_balance"]["amount"]
            op_type = data["opening_balance"]["type"]
            cl_amt = data["closing_balance"]["amount"]
            cl_type = data["closing_balance"]["type"]
            
            # Headline Closing Balance: Money owed TO me (Dr) in #2F6844 (Ledger Green), Money I owe (Cr) in #8B2635 (Ledger Maroon)
            if cl_amt == 0:
                cl_color = "#6B6558"
            elif cl_type == "Dr":
                cl_color = "#2F6844"  # Receivable
            else:
                cl_color = "#8B2635"  # Payable
                
            self.lbl_bal_sub.setText(
                f"Opening: ₹{op_amt:,.2f} {op_type}  |  Total Debits: ₹{data['total_debit']:,.2f}  |  Total Credits: ₹{data['total_credit']:,.2f}"
            )
            self.lbl_bal_headline.setText(f"Closing: ₹{cl_amt:,.2f} {cl_type}")
            self.lbl_bal_headline.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', monospace; font-size: 24px; font-weight: bold; color: {cl_color};")
            
            # Populate Table
            entries = data["entries"]
            total_rows = 1 + len(entries) + 1
            self.table.setUpdatesEnabled(False)
            try:
                self.table.setRowCount(total_rows)
                
                # Monospaced font for all tabular figures (dates, codes, amounts, balances)
                font_mono = QFont("Consolas", 10)
                font_mono_bold = QFont("Consolas", 10)
                font_mono_bold.setBold(True)
                
                font_hdr_bold = QFont("Bahnschrift", 10)
                font_hdr_bold.setBold(True)
                
                # 1. Opening Balance Row
                it_date = QTableWidgetItem(from_d.strftime("%d-%m-%Y"))
                it_date.setFont(font_mono)
                it_type = QTableWidgetItem("Opening")
                it_prod = QTableWidgetItem("-")
                it_ref = QTableWidgetItem("-")
                it_narr = QTableWidgetItem("Opening Balance b/f")
                
                it_dr = QTableWidgetItem(f"₹{op_amt:,.2f}" if op_type == "Dr" else "-")
                it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_dr.setFont(font_mono)
                
                it_cr = QTableWidgetItem(f"₹{op_amt:,.2f}" if op_type == "Cr" else "-")
                it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_cr.setFont(font_mono)
                
                it_bal = QTableWidgetItem(f"₹{op_amt:,.2f} {op_type}")
                it_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_bal.setFont(font_mono_bold)
                
                self.table.setItem(0, 0, it_date)
                self.table.setItem(0, 1, it_type)
                self.table.setItem(0, 2, it_prod)
                self.table.setItem(0, 3, it_ref)
                self.table.setItem(0, 4, it_narr)
                self.table.setItem(0, 5, it_dr)
                self.table.setItem(0, 6, it_cr)
                self.table.setItem(0, 7, it_bal)
                
                # 2. Entries
                for idx, r in enumerate(entries, start=1):
                    d_str = r["voucher_date"].strftime("%d-%m-%Y") if isinstance(r["voucher_date"], (date, datetime)) else str(r["voucher_date"])
                    ref_str = r["voucher_number"]
                    if r["reference_no"]:
                        ref_str += f" (Ref: {r['reference_no']})"
                        
                    it_d = QTableWidgetItem(d_str)
                    it_d.setFont(font_mono)
                    
                    it_t = QTableWidgetItem(r["voucher_type"])
                    it_p = QTableWidgetItem(r.get("product", "") or "-")
                    it_r = QTableWidgetItem(ref_str)
                    it_r.setFont(font_mono)
                    it_n = QTableWidgetItem(r["narration"] or "-")
                    
                    dr_val = f"₹{r['debit']:,.2f}" if r['debit'] > 0 else "-"
                    cr_val = f"₹{r['credit']:,.2f}" if r['credit'] > 0 else "-"
                    
                    it_dr = QTableWidgetItem(dr_val)
                    it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    it_dr.setFont(font_mono)
                    
                    it_cr = QTableWidgetItem(cr_val)
                    it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    it_cr.setFont(font_mono)
                    
                    it_b = QTableWidgetItem(f"₹{r['running_balance']:,.2f} {r['running_balance_type']}")
                    it_b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    it_b.setFont(font_mono_bold)
                    
                    self.table.setItem(idx, 0, it_d)
                    self.table.setItem(idx, 1, it_t)
                    self.table.setItem(idx, 2, it_p)
                    self.table.setItem(idx, 3, it_r)
                    self.table.setItem(idx, 4, it_n)
                    self.table.setItem(idx, 5, it_dr)
                    self.table.setItem(idx, 6, it_cr)
                    self.table.setItem(idx, 7, it_b)
                    
                # 3. Totals Row
                tot_row = total_rows - 1
                it_t_lbl = QTableWidgetItem("TOTALS")
                it_t_lbl.setFont(font_hdr_bold)
                
                it_t_dr = QTableWidgetItem(f"₹{data['total_debit']:,.2f}")
                it_t_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_dr.setFont(font_mono_bold)
                
                it_t_cr = QTableWidgetItem(f"₹{data['total_credit']:,.2f}")
                it_t_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_cr.setFont(font_mono_bold)
                
                it_t_cl = QTableWidgetItem(f"₹{cl_amt:,.2f} {cl_type}")
                it_t_cl.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_cl.setFont(font_mono_bold)
                it_t_cl.setForeground(QColor(cl_color))
                
                self.table.setItem(tot_row, 1, it_t_lbl)
                self.table.setItem(tot_row, 4, QTableWidgetItem(f"Closing Balance as of {to_d.strftime('%d-%m-%Y')}"))
                self.table.setItem(tot_row, 5, it_t_dr)
                self.table.setItem(tot_row, 6, it_t_cr)
                self.table.setItem(tot_row, 7, it_t_cl)
            finally:
                self.table.setUpdatesEnabled(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ledger: {e}")

    def export_pdf(self):
        if not self.current_ledger_data:
            QMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return
        try:
            pdf_path = export_party_ledger_pdf(self.current_ledger_data)
            QMessageBox.information(self, "PDF Exported", f"Ledger Statement PDF saved to:\n{pdf_path}")
            os.startfile(str(pdf_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")

    def export_excel(self):
        if not self.current_ledger_data:
            QMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return
        try:
            xlsx_path = export_party_ledger_excel(self.current_ledger_data)
            QMessageBox.information(self, "Excel Exported", f"Ledger Statement Excel saved to:\n{xlsx_path}")
            os.startfile(str(xlsx_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Excel: {e}")

    def copy_whatsapp_summary(self):
        if not self.current_ledger_data:
            QMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return
        d = self.current_ledger_data
        p = d["party"]
        to_d = d["to_date"].strftime("%d-%m-%Y") if d["to_date"] else date.today().strftime("%d-%m-%Y")
        
        cl_amt = d["closing_balance"]["amount"]
        cl_type = d["closing_balance"]["type"]
        status_word = "Receivable (Kindly settle at earliest)" if cl_type == "Dr" else "Payable (in your favour)"
        
        text = (
            f"Dear {p['name']},\n\n"
            f"Here is your Statement of Account as of *{to_d}*:\n"
            f"• Opening Balance: ₹{d['opening_balance']['amount']:,.2f} {d['opening_balance']['type']}\n"
            f"• Total Debits (+): ₹{d['total_debit']:,.2f}\n"
            f"• Total Credits (-): ₹{d['total_credit']:,.2f}\n"
            f"------------------------------------\n"
            f"*Closing Balance: ₹{cl_amt:,.2f} {cl_type}* ({status_word})\n"
            f"------------------------------------\n"
            f"Kindly review and let us know in case of any queries.\n"
            f"Regards,\nAccounts Dept."
        )
        
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "WhatsApp payment reminder text copied to clipboard! You can paste it directly to WhatsApp.")
