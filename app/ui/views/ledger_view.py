"""
Traditional Indian Ledger Statement View (Bahi Khata)
Features ruled columns, double header rule, monospaced tabular amounts, and theme tokens.
"""
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QApplication
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor
import os

from app.ui.widgets.party_combo import PartyComboBox
from app.services.ledger_service import get_party_ledger_statement
from app.services.export_service import export_party_ledger_pdf, export_party_ledger_excel
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox
)
from app.ui.async_worker import run_in_background
from app.ui.save_dialog import execute_export_pipeline


class LedgerView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_ledger_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Screen Title Header
        self.header_widget = PageHeaderWidget(
            title="Party Ledger Statement",
            subtitle="Detailed statement of accounts, transaction history, and running balances"
        )

        self.btn_pdf = QPushButton("PDF Statement")
        self.btn_pdf.setIcon(theme_manager.get_icon("printer", size=16))
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

        self.btn_whatsapp = QPushButton("Copy WhatsApp Text")
        self.btn_whatsapp.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_whatsapp.setProperty("variant", "secondary")
        self.btn_whatsapp.setFixedHeight(36)
        self.btn_whatsapp.clicked.connect(self.copy_whatsapp_summary)
        self.header_widget.add_custom_action(self.btn_whatsapp)

        layout.addWidget(self.header_widget)

        # 2. Filter Bar
        filter_card = CardFrame()
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(12)

        lbl_p = QLabel("Party:")
        lbl_p.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_p)

        self.combo_party = PartyComboBox()
        self.combo_party.setFixedHeight(36)
        self.combo_party.party_changed.connect(self.load_ledger)
        f_layout.addWidget(self.combo_party, 2)

        lbl_from = QLabel("From:")
        lbl_from.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_from)
        self.dt_from = QDateEdit()
        self.dt_from.setFixedHeight(36)
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDate(QDate(date.today().year, 4, 1) if date.today().month >= 4 else QDate(date.today().year - 1, 4, 1))
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_from, 1)

        lbl_to = QLabel("To:")
        lbl_to.setFont(theme_manager.get_font("label", bold=True))
        f_layout.addWidget(lbl_to)
        self.dt_to = QDateEdit()
        self.dt_to.setFixedHeight(36)
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDate(QDate.currentDate())
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        f_layout.addWidget(self.dt_to, 1)

        from app.ui.widgets.quick_date_selector import QuickDateSelector
        self.quick_dates = QuickDateSelector(self.dt_from, self.dt_to, on_change=self.load_ledger)
        f_layout.addWidget(self.quick_dates)

        btn_view = QPushButton("View Ledger")
        btn_view.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_view.setProperty("variant", "primary")
        btn_view.setFixedHeight(36)
        btn_view.clicked.connect(self.load_ledger)
        f_layout.addWidget(btn_view)

        f_layout.addStretch()
        layout.addWidget(filter_card)

        # 3. Party Summary Header Card
        self.summary_card = CardFrame()
        s_layout = QHBoxLayout(self.summary_card)
        s_layout.setContentsMargins(16, 14, 16, 14)
        s_layout.setSpacing(16)

        # Left side: Party details
        self.lbl_p_info = QLabel("<b>Party Details:</b> Please select a party above to view ledger statement")
        self.lbl_p_info.setFont(theme_manager.get_font("body"))
        s_layout.addWidget(self.lbl_p_info, 3)

        # Right side: Closing Balance headline
        self.bal_vbox = QVBoxLayout()
        self.bal_vbox.setSpacing(2)
        self.bal_vbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.lbl_bal_sub = QLabel("")
        self.lbl_bal_sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bal_sub.setFont(theme_manager.get_font("caption"))
        self.bal_vbox.addWidget(self.lbl_bal_sub)

        self.lbl_bal_headline = QLabel("")
        self.lbl_bal_headline.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_bal_headline.setFont(theme_manager.get_font("headline", bold=True))
        self.bal_vbox.addWidget(self.lbl_bal_headline)

        s_layout.addLayout(self.bal_vbox, 2)
        layout.addWidget(self.summary_card)

        # 4. Transaction Ledger Table
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

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
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
                f"<b>{p['name']}</b> ({location or 'Local'})<br/>"
                f"GSTIN: {gst_str} | Phone: {phone_str} | Credit Period: {p.get('credit_period_days', 30)} Days"
            )

            op_amt = data["opening_balance"]["amount"]
            op_type = data["opening_balance"]["type"]
            cl_amt = data["closing_balance"]["amount"]
            cl_type = data["closing_balance"]["type"]

            if cl_amt == 0:
                cl_token = "text_secondary"
            elif cl_type == "Dr":
                cl_token = "success"
            else:
                cl_token = "danger"

            self.lbl_bal_sub.setText(
                f"Opening: ₹{op_amt:,.2f} {op_type}  |  Total Debits: ₹{data['total_debit']:,.2f}  |  Total Credits: ₹{data['total_credit']:,.2f}"
            )
            self.lbl_bal_headline.setText(f"Closing: ₹{cl_amt:,.2f} {cl_type}")

            # Populate Table
            entries = data["entries"]
            total_rows = 1 + len(entries) + 1
            self.table.setUpdatesEnabled(False)
            try:
                self.table.setRowCount(total_rows)

                # 1. Opening Balance Row
                it_date = QTableWidgetItem(from_d.strftime("%d-%m-%Y"))
                it_type = QTableWidgetItem("Opening")
                it_prod = QTableWidgetItem("—")
                it_ref = QTableWidgetItem("—")
                it_narr = QTableWidgetItem("Opening Balance b/f")

                it_dr = QTableWidgetItem(f"₹{op_amt:,.2f}" if op_type == "Dr" else "—")
                it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                it_cr = QTableWidgetItem(f"₹{op_amt:,.2f}" if op_type == "Cr" else "—")
                it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                it_bal = QTableWidgetItem(f"₹{op_amt:,.2f} {op_type}")
                it_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_bal.setFont(theme_manager.get_font("body", bold=True))

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
                    it_t = QTableWidgetItem(r["voucher_type"])
                    it_p = QTableWidgetItem(r.get("product", "") or "—")
                    it_r = QTableWidgetItem(ref_str)
                    it_n = QTableWidgetItem(r["narration"] or "—")

                    dr_val = f"₹{r['debit']:,.2f}" if r['debit'] > 0 else "—"
                    cr_val = f"₹{r['credit']:,.2f}" if r['credit'] > 0 else "—"

                    it_dr = QTableWidgetItem(dr_val)
                    it_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                    it_cr = QTableWidgetItem(cr_val)
                    it_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                    it_b = QTableWidgetItem(f"₹{r['running_balance']:,.2f} {r['running_balance_type']}")
                    it_b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    it_b.setFont(theme_manager.get_font("body", bold=True))

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
                it_t_lbl.setFont(theme_manager.get_font("body", bold=True))

                it_t_dr = QTableWidgetItem(f"₹{data['total_debit']:,.2f}")
                it_t_dr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_dr.setFont(theme_manager.get_font("body", bold=True))

                it_t_cr = QTableWidgetItem(f"₹{data['total_credit']:,.2f}")
                it_t_cr.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_cr.setFont(theme_manager.get_font("body", bold=True))

                it_t_cl = QTableWidgetItem(f"₹{cl_amt:,.2f} {cl_type}")
                it_t_cl.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_t_cl.setFont(theme_manager.get_font("body", bold=True))
                it_t_cl.setForeground(theme_manager.qcolor(cl_token))

                self.table.setItem(tot_row, 1, it_t_lbl)
                self.table.setItem(tot_row, 4, QTableWidgetItem(f"Closing Balance as of {to_d.strftime('%d-%m-%Y')}"))
                self.table.setItem(tot_row, 5, it_t_dr)
                self.table.setItem(tot_row, 6, it_t_cr)
                self.table.setItem(tot_row, 7, it_t_cl)
            finally:
                self.table.setUpdatesEnabled(True)

        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Failed to load ledger: {e}")

    def export_pdf(self):
        if not self.current_ledger_data:
            ThemedMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return

        p_name = self.current_ledger_data.get("party", {}).get("name", "Party")
        from_str = self.dt_from.date().toString("yyyyMMdd")
        to_str = self.dt_to.date().toString("yyyyMMdd")
        suggested = f"Ledger_{p_name}_{from_str}_to_{to_str}"

        def _generate(out_path):
            return export_party_ledger_pdf(ledger_data=self.current_ledger_data, output_path=out_path)

        execute_export_pipeline(
            parent=self,
            suggested_name=suggested,
            kind="pdf",
            generator_fn=_generate,
            trigger_button=self.btn_pdf
        )

    def export_excel(self):
        if not self.current_ledger_data:
            ThemedMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return

        p_name = self.current_ledger_data.get("party", {}).get("name", "Party")
        from_str = self.dt_from.date().toString("yyyyMMdd")
        to_str = self.dt_to.date().toString("yyyyMMdd")
        suggested = f"Ledger_{p_name}_{from_str}_to_{to_str}"

        def _generate(out_path):
            return export_party_ledger_excel(ledger_data=self.current_ledger_data, output_path=out_path)

        execute_export_pipeline(
            parent=self,
            suggested_name=suggested,
            kind="xlsx",
            generator_fn=_generate,
            trigger_button=self.btn_excel
        )

    def copy_whatsapp_summary(self):
        if not self.current_ledger_data:
            ThemedMessageBox.warning(self, "Warning", "Please select and load a party ledger first.")
            return
        d = self.current_ledger_data
        p = d["party"]
        cl_amt = d["closing_balance"]["amount"]
        cl_type = d["closing_balance"]["type"]

        if cl_amt == 0:
            status_line = "Your account is fully cleared (Nil balance)."
        elif cl_type == "Dr":
            status_line = f"Outstanding balance due: ₹{cl_amt:,.2f}"
        else:
            status_line = f"Advance / Credit balance with us: ₹{cl_amt:,.2f}"

        text = (
            f"Dear {p['name']},\n\n"
            f"Here is your ledger account summary as of {date.today().strftime('%d-%m-%Y')}:\n\n"
            f"• Opening Balance: ₹{d['opening_balance']['amount']:,.2f} {d['opening_balance']['type']}\n"
            f"• Total Billed/Debit: ₹{d['total_debit']:,.2f}\n"
            f"• Total Received/Credit: ₹{d['total_credit']:,.2f}\n"
            f"• {status_line}\n\n"
            f"Please let us know if you need any detailed bill copies.\n"
            f"Thank you for your business!"
        )
        QApplication.clipboard().setText(text)
        ThemedMessageBox.information(self, "Copied", "WhatsApp payment reminder text copied to clipboard!")
