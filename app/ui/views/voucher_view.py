"""
Fast Voucher Entry View (Debit, Credit, Journal)
Includes itemized GST tax calculations and invoice printing.
"""
from datetime import date, datetime
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox, QTextEdit, QFrame, QScrollArea, QSplitter, QCheckBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont

from app.ui.widgets.party_combo import PartyComboBox
from app.services.voucher_service import (
    create_voucher, get_voucher_by_id, get_all_vouchers, delete_voucher,
    generate_voucher_number
)
from app.services.party_service import get_party_by_id
from app.services.export_service import export_invoice_pdf
from app.config import (
    VOUCHER_TYPES, VOUCHER_DEBIT, VOUCHER_CREDIT,
    VOUCHER_JOURNAL, PAYMENT_MODES, GST_RATES
)
from app.database.connection import get_session
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, StatusBadgeLabel, ThemedMessageBox
)


class VoucherEntryView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_editing_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Toolbar
        self.header_widget = PageHeaderWidget(
            title="Voucher Entry",
            subtitle="Record Debit, Credit, Payment, Receipt, and Journal vouchers"
        )
        btn_reset = QPushButton("Reset / New")
        btn_reset.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_reset.setProperty("variant", "secondary")
        btn_reset.setFixedHeight(36)
        btn_reset.clicked.connect(self.reset_form)
        self.header_widget.add_custom_action(btn_reset)
        layout.addWidget(self.header_widget)

        # Voucher Config Bar
        head_card = CardFrame()
        h_layout = QHBoxLayout(head_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(14)

        lbl_type = QLabel("Voucher Type:")
        lbl_type.setFont(theme_manager.get_font("label", bold=True))
        h_layout.addWidget(lbl_type)

        self.combo_vtype = QComboBox()
        self.combo_vtype.addItems(VOUCHER_TYPES)
        self.combo_vtype.currentIndexChanged.connect(self._on_type_changed)
        h_layout.addWidget(self.combo_vtype, 1)

        lbl_date = QLabel("Date:")
        lbl_date.setFont(theme_manager.get_font("label", bold=True))
        h_layout.addWidget(lbl_date)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        h_layout.addWidget(self.date_edit, 1)

        lbl_vnum = QLabel("Vch No:")
        lbl_vnum.setFont(theme_manager.get_font("label", bold=True))
        h_layout.addWidget(lbl_vnum)
        self.inp_vnum = QLineEdit()
        self.inp_vnum.setPlaceholderText("Auto-generated")
        h_layout.addWidget(self.inp_vnum, 1)

        layout.addWidget(head_card)

        # Main Form Body
        body_frame = CardFrame()
        b_layout = QVBoxLayout(body_frame)
        b_layout.setContentsMargins(16, 16, 16, 16)
        b_layout.setSpacing(14)

        # Row 1: Party Selector & Ref details
        r1_layout = QHBoxLayout()
        r1_layout.setSpacing(12)

        party_box = QVBoxLayout()
        party_box.setSpacing(4)
        lbl_party = QLabel("Party / Account *")
        lbl_party.setFont(theme_manager.get_font("label", bold=True))
        party_box.addWidget(lbl_party)
        self.combo_party = PartyComboBox(parent=self)
        self.combo_party.party_changed.connect(self._on_party_changed)
        party_box.addWidget(self.combo_party)
        r1_layout.addLayout(party_box, 3)

        ref_box = QVBoxLayout()
        ref_box.setSpacing(4)
        lbl_ref = QLabel("Ref / Bill / Cheque No:")
        lbl_ref.setFont(theme_manager.get_font("label", bold=True))
        ref_box.addWidget(lbl_ref)
        self.inp_ref = QLineEdit()
        self.inp_ref.setPlaceholderText("e.g. Inv #8891 / UTR No")
        ref_box.addWidget(self.inp_ref)
        r1_layout.addLayout(ref_box, 2)

        # Product / Item field (visible for Debit and Credit)
        prod_box = QVBoxLayout()
        prod_box.setSpacing(4)
        lbl_prod = QLabel("Product / Item:")
        lbl_prod.setFont(theme_manager.get_font("label", bold=True))
        prod_box.addWidget(lbl_prod)
        self.inp_product = QLineEdit()
        self.inp_product.setPlaceholderText("e.g. ACS560 Drive x2, PLC Module x1")
        prod_box.addWidget(self.inp_product)
        r1_layout.addLayout(prod_box, 2)

        mode_box = QVBoxLayout()
        mode_box.setSpacing(4)
        lbl_mode = QLabel("Payment / Settle Mode:")
        lbl_mode.setFont(theme_manager.get_font("label", bold=True))
        mode_box.addWidget(lbl_mode)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(PAYMENT_MODES)
        mode_box.addWidget(self.combo_mode)
        r1_layout.addLayout(mode_box, 2)

        b_layout.addLayout(r1_layout)

        # Live Party Balance Card
        self.lbl_party_balance = QLabel("Party Current Balance: Please select a party")
        self.lbl_party_balance.setFont(theme_manager.get_font("caption"))
        b_layout.addWidget(self.lbl_party_balance)

        # Item Grid / Direct Amount Area
        self.item_container = QWidget()
        item_vbox = QVBoxLayout(self.item_container)
        item_vbox.setContentsMargins(0, 4, 0, 4)
        item_vbox.setSpacing(8)

        item_hdr = QHBoxLayout()
        lbl_items = QLabel("Line Items / Products Billed")
        lbl_items.setFont(theme_manager.get_font("subtitle", bold=True))
        item_hdr.addWidget(lbl_items)
        item_hdr.addStretch()

        btn_add_item = QPushButton(" Add Line Item")
        btn_add_item.setIcon(theme_manager.get_icon("plus", size=16))
        btn_add_item.setProperty("variant", "secondary")
        btn_add_item.setFixedHeight(34)
        btn_add_item.clicked.connect(self.add_item_row)
        item_hdr.addWidget(btn_add_item)
        item_vbox.addLayout(item_hdr)

        self.chk_use_items = QCheckBox("Include Line Items (with GST)")
        self.chk_use_items.setChecked(True)
        self.chk_use_items.stateChanged.connect(self._on_type_changed)
        item_vbox.addWidget(self.chk_use_items)

        self.tbl_items = QTableWidget()
        self.tbl_items.setColumnCount(8)
        self.tbl_items.setHorizontalHeaderLabels([
            "Item Description", "HSN/SAC", "Qty", "Unit", "Rate (₹)", "Disc %", "GST %", "Del"
        ])
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 8):
            self.tbl_items.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tbl_items.verticalHeader().setDefaultSectionSize(36)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setMaximumHeight(180)
        item_vbox.addWidget(self.tbl_items)
        b_layout.addWidget(self.item_container)

        # Direct Amount Container (for Payment, Receipt, Journal)
        self.direct_amount_container = QWidget()
        da_layout = QHBoxLayout(self.direct_amount_container)
        da_layout.setContentsMargins(0, 4, 0, 4)
        da_layout.setSpacing(12)

        da_box = QVBoxLayout()
        da_box.setSpacing(4)
        self.lbl_direct_amt = QLabel("Amount (₹) *:")
        self.lbl_direct_amt.setFont(theme_manager.get_font("label", bold=True))
        da_box.addWidget(self.lbl_direct_amt)
        self.spin_direct_amt = QDoubleSpinBox()
        self.spin_direct_amt.setMaximum(999999999.99)
        self.spin_direct_amt.setDecimals(2)
        self.spin_direct_amt.setPrefix("₹ ")
        self.spin_direct_amt.valueChanged.connect(self.calculate_totals)
        da_box.addWidget(self.spin_direct_amt)
        da_layout.addLayout(da_box, 1)

        self.jrn_box = QWidget()
        jrn_layout = QHBoxLayout(self.jrn_box)
        jrn_layout.setContentsMargins(0, 0, 0, 0)
        lbl_jrn = QLabel("Journal Side:")
        lbl_jrn.setFont(theme_manager.get_font("label", bold=True))
        jrn_layout.addWidget(lbl_jrn)
        self.combo_jrn_side = QComboBox()
        self.combo_jrn_side.addItem("Debit Party (+ Receivable)", "Dr")
        self.combo_jrn_side.addItem("Credit Party (- Payable/Discount)", "Cr")
        jrn_layout.addWidget(self.combo_jrn_side)
        da_layout.addWidget(self.jrn_box, 1)
        self.jrn_box.setVisible(False)

        da_layout.addStretch(2)
        b_layout.addWidget(self.direct_amount_container)

        # Bottom Summary & Narration
        b_bottom = QHBoxLayout()
        b_bottom.setSpacing(14)

        narr_box = QVBoxLayout()
        narr_box.setSpacing(4)
        lbl_narr = QLabel("Narration / Remarks / Transport Details:")
        lbl_narr.setFont(theme_manager.get_font("label", bold=True))
        narr_box.addWidget(lbl_narr)
        self.txt_narration = QTextEdit()
        self.txt_narration.setMaximumHeight(70)
        self.txt_narration.setPlaceholderText("Enter notes, transport details, vehicle no, etc.")
        narr_box.addWidget(self.txt_narration)
        b_bottom.addLayout(narr_box, 2)

        # Totals Display Panel
        tot_panel = CardFrame()
        tot_layout = QVBoxLayout(tot_panel)
        tot_layout.setContentsMargins(12, 10, 12, 10)
        tot_layout.setSpacing(4)

        self.lbl_taxable = QLabel("Taxable Value: ₹0.00")
        self.lbl_taxable.setFont(theme_manager.get_font("caption"))
        self.lbl_cgst = QLabel("CGST: ₹0.00")
        self.lbl_cgst.setFont(theme_manager.get_font("caption"))
        self.lbl_sgst = QLabel("SGST: ₹0.00")
        self.lbl_sgst.setFont(theme_manager.get_font("caption"))
        self.lbl_igst = QLabel("IGST: ₹0.00")
        self.lbl_igst.setFont(theme_manager.get_font("caption"))
        self.lbl_grand_total = QLabel("Grand Total: ₹0.00")
        self.lbl_grand_total.setFont(theme_manager.get_font("subtitle", bold=True))

        tot_layout.addWidget(self.lbl_taxable)
        tot_layout.addWidget(self.lbl_cgst)
        tot_layout.addWidget(self.lbl_sgst)
        tot_layout.addWidget(self.lbl_igst)
        tot_layout.addWidget(self.lbl_grand_total)
        b_bottom.addWidget(tot_panel, 1)

        b_layout.addLayout(b_bottom)

        # Save & Print Action Buttons
        act_box = QHBoxLayout()
        act_box.addStretch()

        self.btn_save = QPushButton("Save Voucher")
        self.btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        self.btn_save.setProperty("variant", "primary")
        self.btn_save.setFixedHeight(38)
        self.btn_save.clicked.connect(self.save_voucher)
        act_box.addWidget(self.btn_save)

        self.btn_save_print = QPushButton("Save & Print PDF")
        self.btn_save_print.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_save_print.setProperty("variant", "secondary")
        self.btn_save_print.setFixedHeight(38)
        self.btn_save_print.clicked.connect(lambda: self.save_voucher(print_pdf=True))
        act_box.addWidget(self.btn_save_print)

        b_layout.addLayout(act_box)
        layout.addWidget(body_frame, 1)

        self._on_type_changed(0)

    def _on_type_changed(self, index=None):
        vtype = self.combo_vtype.currentText()
        is_journal = vtype == VOUCHER_JOURNAL
        is_debit_credit = vtype in [VOUCHER_DEBIT, VOUCHER_CREDIT]
        use_items = is_debit_credit and self.chk_use_items.isChecked()

        self.inp_product.setVisible(is_debit_credit)

        self.item_container.setVisible(use_items)
        self.direct_amount_container.setVisible(not use_items)
        self.jrn_box.setVisible(is_journal)
        self.chk_use_items.setVisible(is_debit_credit)

        if not use_items:
            self.lbl_taxable.setVisible(False)
            self.lbl_cgst.setVisible(False)
            self.lbl_sgst.setVisible(False)
            self.lbl_igst.setVisible(False)
        else:
            self.lbl_taxable.setVisible(True)
            self.lbl_cgst.setVisible(True)
            self.lbl_sgst.setVisible(True)
            self.lbl_igst.setVisible(True)
            if self.tbl_items.rowCount() == 0:
                self.add_item_row()

        self.calculate_totals()

    def _on_party_changed(self, party_id):
        p = get_party_by_id(party_id)
        if p:
            bal_str = f"₹{p['current_balance']:,.2f} {p['current_balance_type']}"
            gst_str = p.get('gstin') or "Unregistered"
            self.lbl_party_balance.setText(
                f"Selected: {p['name']} | GSTIN: {gst_str} | State: {p.get('state','Maharashtra')} ({p.get('state_code','27')}) | Current Balance: {bal_str}"
            )
        self.calculate_totals()

    def add_item_row(self, desc="", hsn="", qty=1.0, unit="PCS", rate=0.0, disc=0.0, gst=18, *args, **kwargs):
        if isinstance(desc, bool):
            desc = ""
        row = self.tbl_items.rowCount()
        self.tbl_items.insertRow(row)

        inp_desc = QLineEdit(str(desc) if desc else "")
        inp_desc.setPlaceholderText("Item name / description")
        inp_desc.textChanged.connect(self.calculate_totals)

        inp_hsn = QLineEdit(hsn)
        inp_hsn.setPlaceholderText("HSN")

        spin_qty = QDoubleSpinBox()
        spin_qty.setMaximum(999999.999)
        spin_qty.setDecimals(3)
        spin_qty.setValue(qty)
        spin_qty.valueChanged.connect(self.calculate_totals)

        combo_unit = QComboBox()
        combo_unit.addItems(["PCS", "TON", "KGS", "MTR", "BOX", "NOS", "SET", "LTR", "BAG"])
        idx_u = combo_unit.findText(unit)
        if idx_u >= 0:
            combo_unit.setCurrentIndex(idx_u)

        spin_rate = QDoubleSpinBox()
        spin_rate.setMaximum(999999999.99)
        spin_rate.setDecimals(2)
        spin_rate.setValue(rate)
        spin_rate.valueChanged.connect(self.calculate_totals)

        spin_disc = QDoubleSpinBox()
        spin_disc.setMaximum(100.0)
        spin_disc.setDecimals(2)
        spin_disc.setValue(disc)
        spin_disc.setSuffix("%")
        spin_disc.valueChanged.connect(self.calculate_totals)

        combo_gst = QComboBox()
        for r in GST_RATES:
            combo_gst.addItem(f"{r}%", r)
        idx_g = combo_gst.findData(gst)
        if idx_g >= 0:
            combo_gst.setCurrentIndex(idx_g)
        combo_gst.currentIndexChanged.connect(self.calculate_totals)

        btn_del = QPushButton()
        btn_del.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_del.setProperty("variant", "ghost")
        btn_del.setFixedSize(28, 28)
        btn_del.clicked.connect(lambda _, r=row: self.remove_item_row(r))

        self.tbl_items.setCellWidget(row, 0, inp_desc)
        self.tbl_items.setCellWidget(row, 1, inp_hsn)
        self.tbl_items.setCellWidget(row, 2, spin_qty)
        self.tbl_items.setCellWidget(row, 3, combo_unit)
        self.tbl_items.setCellWidget(row, 4, spin_rate)
        self.tbl_items.setCellWidget(row, 5, spin_disc)
        self.tbl_items.setCellWidget(row, 6, combo_gst)
        self.tbl_items.setCellWidget(row, 7, btn_del)

        self.calculate_totals()

    def remove_item_row(self, row):
        self.tbl_items.removeRow(row)
        self.calculate_totals()

    def calculate_totals(self):
        vtype = self.combo_vtype.currentText()
        use_items = vtype in [VOUCHER_DEBIT, VOUCHER_CREDIT] and self.chk_use_items.isChecked()
        if not use_items:
            amt = Decimal(str(self.spin_direct_amt.value()))
            self.lbl_grand_total.setText(f"Grand Total: ₹{amt:,.2f}")
            return

        pid = self.combo_party.get_selected_party_id()
        party_st_code = "27"
        if pid:
            p = get_party_by_id(pid)
            if p and p.get("state_code"):
                party_st_code = p["state_code"]

        is_interstate = (party_st_code != "27")

        tot_taxable = Decimal("0.00")
        tot_cgst = Decimal("0.00")
        tot_sgst = Decimal("0.00")
        tot_igst = Decimal("0.00")

        for r in range(self.tbl_items.rowCount()):
            qty_widget = self.tbl_items.cellWidget(r, 2)
            rate_widget = self.tbl_items.cellWidget(r, 4)
            disc_widget = self.tbl_items.cellWidget(r, 5)
            gst_widget = self.tbl_items.cellWidget(r, 6)

            if not qty_widget or not rate_widget:
                continue

            qty = Decimal(str(qty_widget.value()))
            rate = Decimal(str(rate_widget.value()))
            disc = Decimal(str(disc_widget.value())) if disc_widget else Decimal("0.00")
            gst = Decimal(str(gst_widget.currentData())) if gst_widget else Decimal("18.00")

            gross = (qty * rate).quantize(Decimal("0.01"))
            discount = (gross * (disc / Decimal("100.00"))).quantize(Decimal("0.01"))
            taxable = gross - discount

            if is_interstate:
                igst = (taxable * (gst / Decimal("100.00"))).quantize(Decimal("0.01"))
                cgst = Decimal("0.00")
                sgst = Decimal("0.00")
            else:
                cgst = (taxable * (gst / Decimal("200.00"))).quantize(Decimal("0.01"))
                sgst = cgst
                igst = Decimal("0.00")

            tot_taxable += taxable
            tot_cgst += cgst
            tot_sgst += sgst
            tot_igst += igst

        grand_total = tot_taxable + tot_cgst + tot_sgst + tot_igst

        self.lbl_taxable.setText(f"Taxable Value: ₹{tot_taxable:,.2f}")
        self.lbl_cgst.setText(f"CGST: ₹{tot_cgst:,.2f}")
        self.lbl_sgst.setText(f"SGST: ₹{tot_sgst:,.2f}")
        self.lbl_igst.setText(f"IGST: ₹{tot_igst:,.2f}")
        self.lbl_grand_total.setText(f"Grand Total: ₹{grand_total:,.2f}")

    def save_voucher(self, print_pdf=False):
        self.btn_save.setEnabled(False)
        self.btn_save_print.setEnabled(False)
        try:
            party_id = self.combo_party.get_selected_party_id()
            if not party_id:
                ThemedMessageBox.warning(self, "Validation Error", "Please select a Party.")
                return

            vtype = self.combo_vtype.currentText()
            qdate = self.date_edit.date()
            vdate = date(qdate.year(), qdate.month(), qdate.day())

            v_data = {
                "voucher_type": vtype,
                "voucher_date": vdate,
                "party_id": party_id,
                "product": self.inp_product.text().strip() if vtype != VOUCHER_JOURNAL else None,
                "reference_no": self.inp_ref.text().strip(),
                "payment_mode": self.combo_mode.currentText(),
                "narration": self.txt_narration.toPlainText().strip()
            }

            custom_vnum = self.inp_vnum.text().strip()
            if custom_vnum:
                v_data["voucher_number"] = custom_vnum

            items_data = []
            use_items = vtype in [VOUCHER_DEBIT, VOUCHER_CREDIT] and self.chk_use_items.isChecked()
            if use_items:
                for r in range(self.tbl_items.rowCount()):
                    desc_w = self.tbl_items.cellWidget(r, 0)
                    hsn_w = self.tbl_items.cellWidget(r, 1)
                    qty_w = self.tbl_items.cellWidget(r, 2)
                    unit_w = self.tbl_items.cellWidget(r, 3)
                    rate_w = self.tbl_items.cellWidget(r, 4)
                    disc_w = self.tbl_items.cellWidget(r, 5)
                    gst_w = self.tbl_items.cellWidget(r, 6)

                    desc_text = desc_w.text().strip() if desc_w else ""
                    if not desc_text:
                        continue

                    items_data.append({
                        "item_description": desc_text,
                        "hsn_sac_code": hsn_w.text().strip() if hsn_w else "",
                        "quantity": qty_w.value() if qty_w else 1.0,
                        "unit": unit_w.currentText() if unit_w else "PCS",
                        "unit_price": rate_w.value() if rate_w else 0.0,
                        "discount_pct": disc_w.value() if disc_w else 0.0,
                        "gst_rate_pct": gst_w.currentData() if gst_w else 18.0
                    })

                if len(items_data) == 0:
                    ThemedMessageBox.warning(self, "Validation Error", "Please add at least one line item with description and rate.")
                    return
            else:
                dir_amt = self.spin_direct_amt.value()
                if dir_amt <= 0:
                    ThemedMessageBox.warning(self, "Validation Error", "Please enter a valid amount greater than 0.")
                    return
                v_data["total_amount"] = Decimal(str(dir_amt))
                if vtype == VOUCHER_JOURNAL:
                    side = self.combo_jrn_side.currentData()
                    if side == "Dr":
                        v_data["debit_amount"] = Decimal(str(dir_amt))
                        v_data["credit_amount"] = Decimal("0.00")
                    else:
                        v_data["debit_amount"] = Decimal("0.00")
                        v_data["credit_amount"] = Decimal(str(dir_amt))

            created_v = create_voucher(v_data, items_data if items_data else None)
            ThemedMessageBox.information(self, "Success", f"Voucher {created_v.voucher_number} saved successfully!")

            if print_pdf:
                v_dict = get_voucher_by_id(created_v.id)
                if v_dict:
                    pdf_path = export_invoice_pdf(v_dict)
                    ThemedMessageBox.information(self, "PDF Generated", f"Invoice PDF exported successfully:\n{pdf_path}")
                    import os
                    os.startfile(str(pdf_path))

            self.reset_form()
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Failed to save voucher: {e}")
        finally:
            self.btn_save.setEnabled(True)
            self.btn_save_print.setEnabled(True)

    def reset_form(self):
        self.current_editing_id = None
        self.inp_vnum.clear()
        self.inp_ref.clear()
        self.inp_product.clear()
        self.txt_narration.clear()
        self.spin_direct_amt.setValue(0.0)
        self.tbl_items.setRowCount(0)
        self.combo_party.setCurrentIndex(0)
        self.lbl_party_balance.setText("Party Current Balance: Please select a party")
        self.date_edit.setDate(QDate.currentDate())
        vtype = self.combo_vtype.currentText()
        if vtype in [VOUCHER_DEBIT, VOUCHER_CREDIT] and self.chk_use_items.isChecked():
            self.add_item_row()
        self.calculate_totals()

    def set_voucher_type(self, vtype: str):
        idx = self.combo_vtype.findText(vtype)
        if idx >= 0:
            self.combo_vtype.setCurrentIndex(idx)
