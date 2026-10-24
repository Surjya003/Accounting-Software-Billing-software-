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
    QDateEdit, QLineEdit, QFrame, QApplication, QSplitter,
    QDialog, QTextEdit, QComboBox, QFormLayout
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont

from app.services.report_service import get_outstanding_report
from app.services.export_service import export_outstanding_excel, export_outstanding_pdf
from app.database.connection import get_session
from app.database.models import CompanyProfile
from app.ui.widgets.stat_card import StatCard
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox, configure_dialog_window_flags
)
from app.ui.async_worker import run_in_background


class OutstandingTabWidget(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, report_type="Receivables", parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.current_report_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(12)

        # 1. KPI Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        token_accent = "accent" if self.report_type == "Receivables" else "warning"
        self.card_total = StatCard(f"TOTAL {self.report_type.upper()}", "₹0.00", "Total outstanding amount", token_name=token_accent)
        self.card_0_30 = StatCard("0 - 30 DAYS", "₹0.00", "Current period", token_name="success")
        self.card_31_60 = StatCard("31 - 60 DAYS", "₹0.00", "Moderate age", token_name="info")
        self.card_61_90 = StatCard("61 - 90 DAYS", "₹0.00", "Follow-up required", token_name="warning")
        self.card_90_plus = StatCard("90+ DAYS", "₹0.00", "Critical overdue", token_name="danger")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_0_30)
        kpi_layout.addWidget(self.card_31_60)
        kpi_layout.addWidget(self.card_61_90)
        kpi_layout.addWidget(self.card_90_plus)
        layout.addLayout(kpi_layout)

        # 2. Filter Bar
        f_card = CardFrame()
        f_layout = QHBoxLayout(f_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Filter by Party Name, City, Phone...")
        self.inp_search.textChanged.connect(self.apply_filter)
        f_layout.addWidget(self.inp_search, 2)

        lbl_as_of = QLabel("As of Date:")
        lbl_as_of.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_as_of)

        self.dt_as_of = QDateEdit()
        self.dt_as_of.setCalendarPopup(True)
        self.dt_as_of.setDate(QDate.currentDate())
        self.dt_as_of.setDisplayFormat("dd-MM-yyyy")
        self.dt_as_of.dateChanged.connect(self.load_data)
        f_layout.addWidget(self.dt_as_of, 1)

        f_layout.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.clicked.connect(self.load_data)
        f_layout.addWidget(btn_refresh)

        self.btn_pdf = QPushButton("Export PDF")
        self.btn_pdf.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_pdf.setProperty("variant", "secondary")
        self.btn_pdf.clicked.connect(self.export_pdf)
        f_layout.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("Export Excel")
        self.btn_excel.setIcon(theme_manager.get_icon("download", size=16))
        self.btn_excel.setProperty("variant", "secondary")
        self.btn_excel.clicked.connect(self.export_excel)
        f_layout.addWidget(self.btn_excel)

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

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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
            if query in p["party_name"].lower() or query in (p.get("city") or "").lower() or query in (p.get("phone") or "").lower()
        ]
        self.populate_table(filtered)

    def populate_table(self, rows):
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                it_name = QTableWidgetItem(r["party_name"])
                it_name.setData(Qt.UserRole, r["party_id"])

                it_city = QTableWidgetItem(r.get("city") or "—")
                it_phone = QTableWidgetItem(r.get("phone") or "—")
                it_credit = QTableWidgetItem(f"{r.get('credit_period_days', 30)}d")

                b0_30 = r.get('0_30', r.get('bucket_0_30', 0.0))
                b31_60 = r.get('31_60', r.get('bucket_31_60', 0.0))
                b61_90 = r.get('61_90', r.get('bucket_61_90', 0.0))
                b90_plus = r.get('90_plus', r.get('bucket_90_plus', 0.0))
                total_out = r.get('total_outstanding', r.get('amount', 0.0))

                it_0_30 = QTableWidgetItem(f"₹{b0_30:,.2f}" if b0_30 > 0 else "—")
                it_0_30.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                it_31_60 = QTableWidgetItem(f"₹{b31_60:,.2f}" if b31_60 > 0 else "—")
                it_31_60.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                it_61_90 = QTableWidgetItem(f"₹{b61_90:,.2f}" if b61_90 > 0 else "—")
                it_61_90.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if b61_90 > 0:
                    it_61_90.setForeground(theme_manager.qcolor("warning"))

                it_90 = QTableWidgetItem(f"₹{b90_plus:,.2f}" if b90_plus > 0 else "—")
                it_90.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if b90_plus > 0:
                    it_90.setForeground(theme_manager.qcolor("danger"))

                it_tot = QTableWidgetItem(f"₹{total_out:,.2f}")
                it_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_tot.setFont(theme_manager.get_font("body", bold=True))

                self.table.setItem(idx, 0, it_name)
                self.table.setItem(idx, 1, it_city)
                self.table.setItem(idx, 2, it_phone)
                self.table.setItem(idx, 3, it_credit)
                self.table.setItem(idx, 4, it_0_30)
                self.table.setItem(idx, 5, it_31_60)
                self.table.setItem(idx, 6, it_61_90)
                self.table.setItem(idx, 7, it_90)
                self.table.setItem(idx, 8, it_tot)

                # Actions Box
                act_w = QWidget()
                act_l = QHBoxLayout(act_w)
                act_l.setContentsMargins(4, 2, 4, 2)
                act_l.setSpacing(6)

                btn_led = QPushButton("Ledger")
                btn_led.setProperty("variant", "ghost")
                btn_led.setFixedHeight(28)
                btn_led.clicked.connect(lambda _, pid=r["party_id"]: self.navigate_to.emit("ledger", {"party_id": pid}))
                act_l.addWidget(btn_led)

                if self.report_type == "Receivables":
                    btn_rem = QPushButton("Reminder")
                    btn_rem.setProperty("variant", "secondary")
                    btn_rem.setFixedHeight(28)
                    btn_rem.clicked.connect(lambda _, p_data=r: self.open_reminder_dialog(p_data))
                    act_l.addWidget(btn_rem)

                self.table.setCellWidget(idx, 9, act_w)
        finally:
            self.table.setUpdatesEnabled(True)

    def _on_row_double_clicked(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            party_id = item.data(Qt.UserRole)
            self.navigate_to.emit("ledger", {"party_id": party_id})

    def open_reminder_dialog(self, party_data: dict):
        dlg = WhatsAppReminderDialog(party_data, parent=self)
        dlg.exec()

    def export_pdf(self):
        if not self.current_report_data:
            return

        def _on_success(p):
            ThemedMessageBox.information(self, "Exported", f"Outstanding Ageing PDF saved to:\n{p}")
            try:
                os.startfile(str(p))
            except Exception:
                pass

        def _on_error(e):
            ThemedMessageBox.critical(self, "Error", f"Failed to export PDF: {e}")

        run_in_background(
            export_outstanding_pdf,
            on_result=_on_success,
            on_error=_on_error,
            trigger_button=self.btn_pdf,
            report_data=self.current_report_data
        )

    def export_excel(self):
        if not self.current_report_data:
            return

        def _on_success(p):
            ThemedMessageBox.information(self, "Exported", f"Outstanding Ageing Excel saved to:\n{p}")
            try:
                os.startfile(str(p))
            except Exception:
                pass

        def _on_error(e):
            ThemedMessageBox.critical(self, "Error", f"Failed to export Excel: {e}")

        run_in_background(
            export_outstanding_excel,
            on_result=_on_success,
            on_error=_on_error,
            trigger_button=self.btn_excel,
            report_data=self.current_report_data
        )


class OutstandingView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.header_widget = PageHeaderWidget(
            title="Outstanding & Ageing Analysis",
            subtitle="Track debtors (receivables) and creditors (payables) across ageing slabs"
        )
        layout.addWidget(self.header_widget)

        self.tabs = QTabWidget()

        self.tab_receivables = OutstandingTabWidget("Receivables", parent=self)
        self.tab_receivables.navigate_to.connect(self.navigate_to)

        self.tab_payables = OutstandingTabWidget("Payables", parent=self)
        self.tab_payables.navigate_to.connect(self.navigate_to)

        self.tabs.addTab(self.tab_receivables, "Receivables (Debtors)")
        self.tabs.addTab(self.tab_payables, "Payables (Creditors)")

        layout.addWidget(self.tabs, 1)


class WhatsAppReminderDialog(QDialog):
    def __init__(self, party_data: dict, parent=None):
        super().__init__(parent)
        self.p = party_data
        self.setWindowTitle(f"Payment Reminder — {self.p.get('party_name', '')}")
        configure_dialog_window_flags(self, min_width=580, min_height=520)
        self.resize(580, 560)
        self.comp_name = "Our Company"
        self.comp_bank = ""
        self.comp_upi = ""
        self.comp_phone = ""
        self.custom_template = None
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
                    self.custom_template = getattr(comp, "whatsapp_template", None)
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
        layout.setSpacing(14)

        # Header Info Card
        card = CardFrame()
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(4)

        lbl_party = QLabel(f"Party: <b>{self.p.get('party_name', '')}</b>")
        lbl_party.setFont(theme_manager.get_font("body"))
        c_layout.addWidget(lbl_party)

        tot = self.p.get("total_outstanding", 0.0)
        lbl_due = QLabel(f"Total Outstanding Balance: <b>₹{tot:,.2f}</b>")
        lbl_due.setFont(theme_manager.get_font("subtitle", bold=True))
        c_layout.addWidget(lbl_due)
        layout.addWidget(card)

        # Form Controls
        form = QFormLayout()
        form.setSpacing(12)

        raw_phone = str(self.p.get("phone") or "").strip()
        self.inp_phone = QLineEdit(raw_phone)
        self.inp_phone.setPlaceholderText("Enter 10-digit mobile number (e.g. 9876543210)")
        form.addRow("WhatsApp Number:", self.inp_phone)

        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "Company Custom Template (Settings)",
            "Gentle Reminder (English)",
            "Overdue Payment Notice (English)",
            "नम्र स्मरण / बकाया याद दिलाना (Hindi)",
            "ताकीद / अंतिम भुगतान सूचना (Hindi Urgent)"
        ])
        self.combo_template.currentIndexChanged.connect(self._update_template)
        form.addRow("Message Tone:", self.combo_template)

        layout.addLayout(form)

        lbl_msg = QLabel("Message Preview (Editable):")
        lbl_msg.setFont(theme_manager.get_font("label", bold=True))
        layout.addWidget(lbl_msg)

        self.txt_message = QTextEdit()
        layout.addWidget(self.txt_message, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_copy = QPushButton("Copy Message")
        btn_copy.setIcon(theme_manager.get_icon("edit", size=16))
        btn_copy.setProperty("variant", "secondary")
        btn_copy.setFixedHeight(36)
        btn_copy.clicked.connect(self._copy_message)
        btn_layout.addWidget(btn_copy)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_send_wa = QPushButton("Open in WhatsApp")
        btn_send_wa.setIcon(theme_manager.get_icon("check", token_color="text_on_accent", size=16))
        btn_send_wa.setProperty("variant", "primary")
        btn_send_wa.setFixedHeight(36)
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
            template = self.custom_template or (
                "Dear {party_name},\n\n"
                "Greetings from *{company_name}*!\n\n"
                "This is a gentle reminder that your current outstanding balance is *₹{amount}*.\n\n"
                "📊 *Overdue Aging Summary:*\n"
                "• 0-30 Days: ₹{b0}\n"
                "• 31-60 Days: ₹{b31}\n"
                "• 61-90 Days: ₹{b61}\n"
                "• 90+ Days: ₹{b90}\n\n"
                "💳 *Bank Transfer Details:*\n{bank_details}\n\n"
                "Kindly arrange for payment at your earliest convenience. If already paid, please ignore this message.\n\n"
                "Warm regards,\n*{company_name}*"
            )
            msg = template.replace("{party_name}", party_name) \
                          .replace("{company_name}", self.comp_name) \
                          .replace("{amount}", f"{tot:,.2f}") \
                          .replace("{bank_details}", bank_text) \
                          .replace("{b0}", f"{b0:,.2f}") \
                          .replace("{b31}", f"{b31:,.2f}") \
                          .replace("{b61}", f"{b61:,.2f}") \
                          .replace("{b90}", f"{b90:,.2f}")
        elif idx == 1:
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

        self.txt_message.setPlainText(msg.strip())

    def _copy_message(self):
        text = self.txt_message.toPlainText().strip()
        QApplication.clipboard().setText(text)
        ThemedMessageBox.information(self, "Copied", "Reminder message copied to clipboard!")

    def _send_whatsapp(self):
        text = self.txt_message.toPlainText().strip()
        phone = self.inp_phone.text().strip()

        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
        elif len(clean_phone) == 11 and clean_phone.startswith("0"):
            clean_phone = "91" + clean_phone[1:]

        if not clean_phone or len(clean_phone) < 10:
            ThemedMessageBox.warning(self, "Invalid Phone", "Please enter a valid mobile number for WhatsApp.")
            return

        encoded_text = urllib.parse.quote(text)
        wa_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"

        try:
            webbrowser.open(wa_url)
            self.accept()
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Could not launch browser for WhatsApp: {e}")
