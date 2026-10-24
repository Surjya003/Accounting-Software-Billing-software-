"""
Outstanding & Ageing Analysis View (Receivables & Payables: 0-30, 31-60, 61-90, 90+ days)
The single most-used screen in trading businesses.
"""
from datetime import date
import os
import urllib.parse
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QLineEdit, QFrame, QMessageBox, QApplication, QSplitter,
    QDialog, QTextEdit, QComboBox, QFormLayout
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.services.report_service import get_outstanding_report
from app.services.export_service import export_outstanding_excel, export_outstanding_pdf
from app.database.connection import get_session
from app.database.models import CompanyProfile
from app.ui.widgets.stat_card import StatCard


class OutstandingTabWidget(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, report_type="Receivables", parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.current_report_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # 1. KPI Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)
        
        accent = "#0284C7" if self.report_type == "Receivables" else "#D97706"
        self.card_total = StatCard(f"Total {self.report_type}", "₹0.00", "Total outstanding amount", accent)
        self.card_0_30 = StatCard("0 - 30 Days", "₹0.00", "Current period", "#10B981")
        self.card_31_60 = StatCard("31 - 60 Days", "₹0.00", "Moderate age", "#0284C7")
        self.card_61_90 = StatCard("61 - 90 Days", "₹0.00", "Follow-up required", "#F59E0B")
        self.card_90_plus = StatCard("90+ Days", "₹0.00", "Critical overdue", "#EF4444")
        
        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_0_30)
        kpi_layout.addWidget(self.card_31_60)
        kpi_layout.addWidget(self.card_61_90)
        kpi_layout.addWidget(self.card_90_plus)
        layout.addLayout(kpi_layout)
        
        # 2. Filter Bar
        f_card = QFrame()
        f_card.setObjectName("Card")
        f_layout = QHBoxLayout(f_card)
        f_layout.setContentsMargins(10, 6, 10, 6)
        f_layout.setSpacing(10)
        
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("🔍 Filter by Party Name, City, Phone...")
        self.inp_search.textChanged.connect(self.apply_filter)
        f_layout.addWidget(self.inp_search, 2)
        
        lbl_as_of = QLabel("<b>As of Date:</b>")
        f_layout.addWidget(lbl_as_of)
        
        self.dt_as_of = QDateEdit()
        self.dt_as_of.setCalendarPopup(True)
        self.dt_as_of.setDate(QDate.currentDate())
        self.dt_as_of.setDisplayFormat("dd-MM-yyyy")
        self.dt_as_of.dateChanged.connect(self.load_data)
        f_layout.addWidget(self.dt_as_of, 1)
        
        f_layout.addStretch()
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.load_data)
        f_layout.addWidget(btn_refresh)
        
        btn_pdf = QPushButton("📄 Export PDF")
        btn_pdf.setObjectName("PrimaryBtn")
        btn_pdf.clicked.connect(self.export_pdf)
        f_layout.addWidget(btn_pdf)
        
        btn_excel = QPushButton("📊 Export Excel")
        btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(btn_excel)
        
        layout.addWidget(f_card)
        
        # 3. Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Party Name", "City", "Phone", "Credit",
            "0-30 Days (₹)", "31-60 Days (₹)", "61-90 Days (₹)", "90+ Days (₹)",
            "Total Outstanding (₹)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 10):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table, 1)
        
        self.load_data()

    def load_data(self):
        q_as_of = self.dt_as_of.date()
        as_of = date(q_as_of.year(), q_as_of.month(), q_as_of.day())
        
        data = get_outstanding_report(report_type=self.report_type, as_of_date=as_of)
        self.current_report_data = data
        
        self.card_total.set_value(f"₹{data['grand_total']:,.2f}", f"{data['party_count']} Parties")
        self.card_0_30.set_value(f"₹{data['total_0_30']:,.2f}")
        self.card_31_60.set_value(f"₹{data['total_31_60']:,.2f}")
        self.card_61_90.set_value(f"₹{data['total_61_90']:,.2f}")
        self.card_90_plus.set_value(f"₹{data['total_90_plus']:,.2f}")
        
        self.populate_table(data["party_rows"])

    def apply_filter(self):
        if not self.current_report_data:
            return
        query = self.inp_search.text().strip().lower()
        if not query:
            self.populate_table(self.current_report_data["party_rows"])
            return
            
        filtered = [
            p for p in self.current_report_data["party_rows"]
            if query in p["party_name"].lower() or query in p["city"].lower() or query in p["phone"].lower()
        ]
        self.populate_table(filtered)

    def populate_table(self, rows):
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            font_bold = QFont()
            font_bold.setBold(True)
            
            for r_idx, p in enumerate(rows):
                it_name = QTableWidgetItem(p["party_name"])
                it_name.setData(Qt.UserRole, p["party_id"])
                it_name.setFont(font_bold)
                
                it_city = QTableWidgetItem(p["city"] or "-")
                it_phone = QTableWidgetItem(p["phone"] or "-")
                it_cr = QTableWidgetItem(f"{p['credit_days']} d")
                
                it_0_30 = QTableWidgetItem(f"₹{p['bucket_0_30']:,.2f}" if p['bucket_0_30'] > 0 else "-")
                it_0_30.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                it_31_60 = QTableWidgetItem(f"₹{p['bucket_31_60']:,.2f}" if p['bucket_31_60'] > 0 else "-")
                it_31_60.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                it_61_90 = QTableWidgetItem(f"₹{p['bucket_61_90']:,.2f}" if p['bucket_61_90'] > 0 else "-")
                it_61_90.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if p['bucket_61_90'] > 0:
                    it_61_90.setForeground(QColor("#D97706"))
                    
                it_90 = QTableWidgetItem(f"₹{p['bucket_90_plus']:,.2f}" if p['bucket_90_plus'] > 0 else "-")
                it_90.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if p['bucket_90_plus'] > 0:
                    it_90.setForeground(QColor("#DC2626"))
                    it_90.setFont(font_bold)
                    
                it_tot = QTableWidgetItem(f"₹{p['total_outstanding']:,.2f}")
                it_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_tot.setFont(font_bold)
                accent_col = "#0284C7" if self.report_type == "Receivables" else "#D97706"
                it_tot.setForeground(QColor(accent_col))
                
                self.table.setItem(r_idx, 0, it_name)
                self.table.setItem(r_idx, 1, it_city)
                self.table.setItem(r_idx, 2, it_phone)
                self.table.setItem(r_idx, 3, it_cr)
                self.table.setItem(r_idx, 4, it_0_30)
                self.table.setItem(r_idx, 5, it_31_60)
                self.table.setItem(r_idx, 6, it_61_90)
                self.table.setItem(r_idx, 7, it_90)
                self.table.setItem(r_idx, 8, it_tot)
                
                # Action button
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(2, 2, 2, 2)
                act_layout.setSpacing(4)
                
                btn_led = QPushButton("Ledger")
                btn_led.setStyleSheet("padding: 2px 6px; font-size: 11px;")
                btn_led.clicked.connect(lambda _, pid=p["party_id"]: self.navigate_to.emit("ledger", {"party_id": pid}))
                act_layout.addWidget(btn_led)
                
                btn_rem = QPushButton("💬 WhatsApp")
                btn_rem.setStyleSheet("padding: 2px 8px; font-size: 11px; font-weight: 600; color: #2F6844; border: 1px solid #2F6844; border-radius: 3px;")
                btn_rem.setToolTip("Open WhatsApp Payment Reminder")
                btn_rem.clicked.connect(lambda _, row_p=p: self.open_whatsapp_dialog(row_p))
                act_layout.addWidget(btn_rem)
                
                self.table.setCellWidget(r_idx, 9, act_widget)
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_row_double_clicked(self, index):
        item = self.table.item(index.row(), 0)
        if item:
            pid = item.data(Qt.UserRole)
            self.navigate_to.emit("ledger", {"party_id": pid})

    def open_whatsapp_dialog(self, p):
        dlg = WhatsAppReminderDialog(p, parent=self)
        dlg.exec()


    def export_pdf(self):
        if not self.current_report_data:
            return
        try:
            p = export_outstanding_pdf(self.current_report_data)
            QMessageBox.information(self, "Exported", f"Outstanding Ageing PDF saved to:\n{p}")
            os.startfile(str(p))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {e}")

    def export_excel(self):
        if not self.current_report_data:
            return
        try:
            p = export_outstanding_excel(self.current_report_data)
            QMessageBox.information(self, "Exported", f"Outstanding Ageing Excel saved to:\n{p}")
            os.startfile(str(p))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export Excel: {e}")


class OutstandingView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        self.tabs = QTabWidget()
        
        self.tab_receivables = OutstandingTabWidget("Receivables", parent=self)
        self.tab_receivables.navigate_to.connect(self.navigate_to)
        
        self.tab_payables = OutstandingTabWidget("Payables", parent=self)
        self.tab_payables.navigate_to.connect(self.navigate_to)
        
        self.tabs.addTab(self.tab_receivables, "📥 Receivables (Debtors - Money Owed to You)")
        self.tabs.addTab(self.tab_payables, "📤 Payables (Creditors - Money You Owe)")
        
        layout.addWidget(self.tabs)


class WhatsAppReminderDialog(QDialog):
    """
    Vyapar-style 1-click WhatsApp payment reminder dialog.
    Supports English & Hindi tones, phone number sanitization,
    Company bank & UPI details injection, and direct WhatsApp launch.
    """
    def __init__(self, party_data: dict, parent=None):
        super().__init__(parent)
        self.p = party_data
        self.setWindowTitle(f"💬 WhatsApp Payment Reminder — {self.p.get('party_name', '')}")
        self.resize(580, 560)
        self.comp_name = "Our Company"
        self.comp_bank = ""
        self.comp_upi = ""
        self.comp_phone = ""
        self._load_company_details()
        self.init_ui()
        self._update_template()

    def _load_company_details(self):
        try:
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                if comp:
                    self.comp_name = comp.name or "Our Company"
                    self.comp_phone = comp.phone or ""
                    self.comp_upi = comp.upi_id or ""
                    parts = []
                    if comp.bank_name:
                        parts.append(f"Bank: {comp.bank_name}")
                    if comp.bank_account_no:
                        parts.append(f"A/C: {comp.bank_account_no}")
                    if comp.bank_ifsc:
                        parts.append(f"IFSC: {comp.bank_ifsc}")
                    if comp.upi_id:
                        parts.append(f"UPI ID: {comp.upi_id}")
                    self.comp_bank = " | ".join(parts)
        except Exception:
            pass

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Info Card
        card = QFrame()
        card.setObjectName("Card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(4)

        lbl_party = QLabel(f"<b>Party:</b> {self.p.get('party_name', '')}")
        lbl_party.setStyleSheet("font-size: 14px; color: #1B1B18;")
        c_layout.addWidget(lbl_party)

        tot = self.p.get("total_outstanding", 0.0)
        lbl_due = QLabel(f"<b>Total Outstanding Balance:</b> <span style='color: #8B2635; font-size: 15px; font-weight: bold;'>₹{tot:,.2f}</span>")
        c_layout.addWidget(lbl_due)
        layout.addWidget(card)

        # Form Controls
        form = QFormLayout()
        form.setSpacing(10)

        # Phone Number
        raw_phone = str(self.p.get("phone") or "").strip()
        self.inp_phone = QLineEdit(raw_phone)
        self.inp_phone.setPlaceholderText("Enter 10-digit mobile number (e.g. 9876543210)")
        form.addRow("<b>WhatsApp Number:</b>", self.inp_phone)

        # Template Selector
        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "Gentle Reminder (English)",
            "Overdue Payment Notice (English)",
            "नम्र स्मरण / बकाया याद दिलाना (Hindi)",
            "ताकीद / अंतिम भुगतान सूचना (Hindi Urgent)"
        ])
        self.combo_template.currentIndexChanged.connect(self._update_template)
        form.addRow("<b>Message Tone:</b>", self.combo_template)

        layout.addLayout(form)

        # Message Preview Text Box
        lbl_msg = QLabel("<b>Message Preview (Editable):</b>")
        layout.addWidget(lbl_msg)

        self.txt_message = QTextEdit()
        self.txt_message.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #FFFFFF; color: #1B1B18; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px;")
        layout.addWidget(self.txt_message, 1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_copy = QPushButton("📋 Copy Message")
        btn_copy.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        btn_copy.clicked.connect(self._copy_message)
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_send_wa = QPushButton("🚀 Open in WhatsApp")
        btn_send_wa.setObjectName("SuccessBtn")
        btn_send_wa.setStyleSheet("background-color: #2F6844; color: #FFFFFF; font-weight: bold; padding: 8px 20px; font-size: 13px; border-radius: 4px;")
        btn_send_wa.clicked.connect(self._send_whatsapp)
        btn_layout.addWidget(btn_send_wa)

        layout.addLayout(btn_layout)

    def _update_template(self):
        party_name = self.p.get("party_name", "Valued Customer")
        tot = self.p.get("total_outstanding", 0.0)
        b0 = self.p.get("bucket_0_30", 0.0)
        b31 = self.p.get("bucket_31_60", 0.0)
        b61 = self.p.get("bucket_61_90", 0.0)
        b90 = self.p.get("bucket_90_plus", 0.0)
        critical = b61 + b90

        bank_text = self.comp_bank if self.comp_bank else "Please contact us for bank account details."

        idx = self.combo_template.currentIndex()
        if idx == 0:
            # Gentle Reminder English
            msg = (
                f"Dear {party_name},\n\n"
                f"Greetings from *{self.comp_name}*!\n\n"
                f"This is a gentle reminder that your current outstanding balance is *₹{tot:,.2f}*.\n\n"
                f"📊 *Overdue Aging Summary:*\n"
                f"• 0-30 Days: ₹{b0:,.2f}\n"
                f"• 31-60 Days: ₹{b31:,.2f}\n"
                f"• 61-90 Days: ₹{b61:,.2f}\n"
                f"• 90+ Days: ₹{b90:,.2f}\n\n"
                f"💳 *Bank Transfer Details:*\n{bank_text}\n\n"
                f"Kindly arrange for payment at your earliest convenience. If already paid, please ignore this message.\n\n"
                f"Warm regards,\n*{self.comp_name}*"
            )
        elif idx == 1:
            # Overdue Payment Notice English
            msg = (
                f"⚠️ *PAYMENT REMINDER / OVERDUE NOTICE*\n\n"
                f"To: *{party_name}*\n"
                f"From: *{self.comp_name}*\n\n"
                f"We wish to bring to your urgent attention that an amount of *₹{tot:,.2f}* is overdue on your account (₹{critical:,.2f} overdue > 60 days).\n\n"
                f"Kindly remit the payment today to avoid interruption in your credit period or future dispatches.\n\n"
                f"💳 *Remit to:*\n{bank_text}\n\n"
                f"Please reply with the UTR / payment reference once processed.\n\n"
                f"Thank you,\n*{self.comp_name}*"
            )
        elif idx == 2:
            # Hindi Gentle Reminder
            msg = (
                f"नमस्ते *{party_name}* जी,\n\n"
                f"*{self.comp_name}* की ओर से सादर प्रणाम।\n\n"
                f"यह आपके खाते के बकाया भुगतान *₹{tot:,.2f}* के संदर्भ में एक नम्र स्मरण है।\n\n"
                f"💳 *भुगतान विवरण:*\n{bank_text}\n\n"
                f"कृपया बकाया राशि का भुगतान जल्द से जल्द करने की कृपा करें।\nयदि आप पहले ही भुगतान कर चुके हैं, तो कृपया यूटीआर/रसीद साझा करें।\n\n"
                f"सधन्यवाद,\n*{self.comp_name}*"
            )
        else:
            # Hindi Firm Notice
            msg = (
                f"⚠️ *बकाया भुगतान सूचना (Overdue Notice)*\n\n"
                f"सेवा में: *{party_name}*\n"
                f"प्रेषक: *{self.comp_name}*\n\n"
                f"आपके खाते में कुल *₹{tot:,.2f}* का भुगतान काफी समय से बकाया है।\n"
                f"व्यापारिक संबंधों को सुचारू बनाए रखने हेतु कृपया तुरंत भुगतान सुनिश्चित करें।\n\n"
                f"💳 *बैंक खाता विवरण:*\n{bank_text}\n\n"
                f"भुगतान के उपरांत कृपया रसीद प्रेषित करें।\n\n"
                f"धन्यवाद,\n*{self.comp_name}*"
            )

        self.txt_message.setText(msg)

    def _copy_message(self):
        text = self.txt_message.toPlainText()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Reminder message copied to clipboard!")

    def _send_whatsapp(self):
        phone_raw = self.inp_phone.text().strip()
        # Clean digits
        digits = "".join(ch for ch in phone_raw if ch.isdigit())
        if len(digits) == 10:
            digits = "91" + digits
        elif len(digits) == 11 and digits.startswith("0"):
            digits = "91" + digits[1:]

        if not digits:
            QMessageBox.warning(self, "Invalid Phone", "Please enter a valid mobile number for WhatsApp.")
            return

        msg = self.txt_message.toPlainText()
        # Copy to clipboard as fallback
        QApplication.clipboard().setText(msg)

        encoded_msg = urllib.parse.quote(msg)
        wa_url = f"https://api.whatsapp.com/send?phone={digits}&text={encoded_msg}"

        try:
            webbrowser.open(wa_url)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not launch browser for WhatsApp: {e}")

