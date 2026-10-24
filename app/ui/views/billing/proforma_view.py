"""
Proforma Invoice View & Form Dialog.
Allows creating, editing, printing, and converting Proforma Invoices to Tax Invoices.
"""
import os
import subprocess
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit,
    QDateEdit, QTabWidget, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from app.services.billing import proforma_service, product_service
from app.services.party_service import get_all_parties
from app.ui.views.billing.invoice_view import InvoiceItemWidget
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, StatusBadgeLabel, ThemedMessageBox,
    configure_dialog_window_flags
)
from app.ui.save_dialog import execute_export_pipeline


class ProformaFormDialog(QDialog):
    """Dialog for creating/editing a proforma invoice."""

    def __init__(self, proforma_data=None, parent=None):
        super().__init__(parent)
        self.proforma_data = proforma_data
        self.setWindowTitle("Edit Proforma Invoice" if proforma_data else "New Proforma Invoice")
        configure_dialog_window_flags(self, min_width=920, min_height=640)
        self.products = product_service.get_all_products()
        self.parties = get_all_parties()
        self.item_widgets = []
        self.init_ui()
        if proforma_data:
            self.load_data(proforma_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title_text = "Edit Proforma Invoice" if self.proforma_data else "New Proforma Invoice"
        title = QLabel(title_text)
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        # Top grid: Party, Date, Due Date, Tax Mode
        top_grid = QHBoxLayout()
        top_grid.setSpacing(12)

        # Party
        party_box = QVBoxLayout()
        party_box.addWidget(QLabel("Party / Customer *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("Select party...")
        for p in self.parties:
            gst_label = f" ({p.get('gstin')})" if p.get("gstin") else ""
            self.cmb_party.addItem(f"{p['name']}{gst_label}", p["id"])
        party_box.addWidget(self.cmb_party)
        top_grid.addLayout(party_box, 2)

        # Proforma Number
        num_box = QVBoxLayout()
        num_box.addWidget(QLabel("Proforma # (Auto)"))
        self.txt_pf_number = QLineEdit()
        self.txt_pf_number.setPlaceholderText("Leave blank for auto")
        num_box.addWidget(self.txt_pf_number)
        top_grid.addLayout(num_box, 1)

        # Date
        date_box = QVBoxLayout()
        date_box.addWidget(QLabel("Date *"))
        self.dt_date = QDateEdit()
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDate(QDate.currentDate())
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_date)
        top_grid.addLayout(date_box, 1)

        # Valid Until
        valid_box = QVBoxLayout()
        valid_box.addWidget(QLabel("Valid Until"))
        self.dt_valid = QDateEdit()
        self.dt_valid.setCalendarPopup(True)
        self.dt_valid.setDate(QDate.currentDate().addDays(30))
        self.dt_valid.setDisplayFormat("dd-MM-yyyy")
        valid_box.addWidget(self.dt_valid)
        top_grid.addLayout(valid_box, 1)

        # Tax Mode
        tax_box = QVBoxLayout()
        tax_box.addWidget(QLabel("Supply Type"))
        self.cmb_tax_mode = QComboBox()
        self.cmb_tax_mode.addItems(["Intra-State (CGST + SGST)", "Inter-State (IGST)"])
        self.cmb_tax_mode.currentIndexChanged.connect(self._update_totals)
        tax_box.addWidget(self.cmb_tax_mode)
        top_grid.addLayout(tax_box, 1)

        layout.addLayout(top_grid)

        # Second row: PO Number & PI Number
        ref_row = QHBoxLayout()
        ref_row.setSpacing(12)

        po_box = QVBoxLayout()
        po_box.addWidget(QLabel("PO Number (Buyer Order #)"))
        self.txt_po_number = QLineEdit()
        self.txt_po_number.setPlaceholderText("Optional PO #")
        po_box.addWidget(self.txt_po_number)
        ref_row.addLayout(po_box, 1)

        pi_box = QVBoxLayout()
        pi_box.addWidget(QLabel("PI Number / Ref #"))
        self.txt_pi_number = QLineEdit()
        self.txt_pi_number.setPlaceholderText("Optional reference / PI #")
        pi_box.addWidget(self.txt_pi_number)
        ref_row.addLayout(pi_box, 1)

        ref_row.addStretch(1)
        layout.addLayout(ref_row)

        # Tabbed interface for Items, Logistics, and Terms
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # === TAB 1: LINE ITEMS ===
        tab_items = QWidget()
        tab_items_layout = QVBoxLayout(tab_items)
        tab_items_layout.setContentsMargins(12, 12, 12, 12)
        tab_items_layout.setSpacing(10)

        # Items header
        items_header = QHBoxLayout()
        lbl_items = QLabel("Line Items")
        lbl_items.setFont(theme_manager.get_font("subtitle", bold=True))
        items_header.addWidget(lbl_items)
        items_header.addStretch()
        btn_add_item = QPushButton(" Add Item")
        btn_add_item.setIcon(theme_manager.get_icon("plus", size=16))
        btn_add_item.setProperty("variant", "secondary")
        btn_add_item.setFixedHeight(34)
        btn_add_item.clicked.connect(self.add_item_row)
        items_header.addWidget(btn_add_item)
        tab_items_layout.addLayout(items_header)

        # Column labels
        col_labels = QHBoxLayout()
        col_labels.setContentsMargins(8, 0, 8, 0)
        col_labels.setSpacing(8)
        for label, stretch in [("Product", 3), ("Qty", 1), ("Rate (₹)", 1), ("Disc %", 1), ("GST %", 1), ("Total", 1), ("", 0)]:
            lbl = QLabel(label)
            lbl.setFont(theme_manager.get_font("caption", bold=True))
            if stretch:
                col_labels.addWidget(lbl, stretch)
            else:
                col_labels.addWidget(lbl)
        tab_items_layout.addLayout(col_labels)

        # Items container inside a scroll area
        items_scroll = QWidget()
        self.items_layout = QVBoxLayout(items_scroll)
        self.items_layout.setSpacing(6)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(items_scroll)
        scroll_area.setMinimumHeight(150)
        tab_items_layout.addWidget(scroll_area, 1)

        # Add first item row
        self.add_item_row()

        # Totals
        totals_frame = CardFrame()
        totals_frame.setMinimumHeight(56)
        totals_frame.setMaximumHeight(70)
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.setContentsMargins(12, 8, 12, 8)
        totals_layout.addStretch()

        self.lbl_subtotal = QLabel("Subtotal: ₹0.00")
        self.lbl_subtotal.setFont(theme_manager.get_font("body", bold=True))
        self.lbl_tax = QLabel("Tax: ₹0.00")
        self.lbl_tax.setFont(theme_manager.get_font("body", bold=True))
        self.lbl_grand = QLabel("Total: ₹0.00")
        self.lbl_grand.setFont(theme_manager.get_font("subtitle", bold=True))

        totals_layout.addWidget(self.lbl_subtotal)
        totals_layout.addSpacing(20)
        totals_layout.addWidget(self.lbl_tax)
        totals_layout.addSpacing(20)
        totals_layout.addWidget(self.lbl_grand)

        tab_items_layout.addWidget(totals_frame, 0)
        self.tabs.addTab(tab_items, "Items & Totals")

        # === TAB 2: LOGISTICS ===
        tab_log = QWidget()
        tab_log_layout = QFormLayout(tab_log)
        tab_log_layout.setContentsMargins(16, 16, 16, 16)
        tab_log_layout.setSpacing(12)

        self.chk_same_address = QCheckBox("Same as Party Billing Address")
        self.chk_same_address.stateChanged.connect(self.toggle_shipping_address)
        tab_log_layout.addRow("", self.chk_same_address)

        self.txt_shipping_address = QTextEdit()
        self.txt_shipping_address.setMaximumHeight(60)
        tab_log_layout.addRow("Shipping Address", self.txt_shipping_address)

        self.txt_transporter = QLineEdit()
        tab_log_layout.addRow("Transporter Name", self.txt_transporter)

        self.txt_vehicle_no = QLineEdit()
        tab_log_layout.addRow("Vehicle No", self.txt_vehicle_no)

        self.txt_lr_no = QLineEdit()
        tab_log_layout.addRow("LR / RR No", self.txt_lr_no)

        self.txt_eway_bill = QLineEdit()
        tab_log_layout.addRow("E-Way Bill No", self.txt_eway_bill)

        self.txt_destination = QLineEdit()
        tab_log_layout.addRow("Destination", self.txt_destination)

        self.tabs.addTab(tab_log, "Shipping & Logistics")

        # === TAB 3: TERMS & BANK ===
        tab_terms = QWidget()
        tab_terms_layout = QFormLayout(tab_terms)
        tab_terms_layout.setContentsMargins(16, 16, 16, 16)
        tab_terms_layout.setSpacing(12)

        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(80)
        self.txt_terms.setPlaceholderText("e.g. Goods once sold cannot be returned.")
        tab_terms_layout.addRow("Terms & Conditions", self.txt_terms)

        self.txt_bank_name = QLineEdit()
        tab_terms_layout.addRow("Bank Name", self.txt_bank_name)

        self.txt_bank_ac = QLineEdit()
        tab_terms_layout.addRow("Bank A/C No", self.txt_bank_ac)

        self.txt_bank_ifsc = QLineEdit()
        tab_terms_layout.addRow("Bank IFSC Code", self.txt_bank_ifsc)

        self.tabs.addTab(tab_terms, "Terms & Bank")

        # Notes
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(50)
        self.txt_notes.setPlaceholderText("Optional notes...")
        layout.addWidget(self.txt_notes)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Proforma")
        btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        btn_save.setProperty("variant", "primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def toggle_shipping_address(self, state):
        if state:
            self.txt_shipping_address.setEnabled(False)
            self.txt_shipping_address.setPlainText("Same as Billing Address")
        else:
            self.txt_shipping_address.setEnabled(True)
            self.txt_shipping_address.clear()

    def add_item_row(self):
        item = InvoiceItemWidget(products_list=self.products)
        item.item_changed.connect(self._update_totals)
        item.remove_requested.connect(self._remove_item)
        self.item_widgets.append(item)
        insert_pos = self.items_layout.count() - 1
        self.items_layout.insertWidget(insert_pos, item)

    def _remove_item(self, widget):
        if len(self.item_widgets) <= 1:
            return
        self.item_widgets.remove(widget)
        self.items_layout.removeWidget(widget)
        widget.deleteLater()
        self._update_totals()

    def _update_totals(self):
        subtotal = tax = Decimal("0")
        for w in self.item_widgets:
            d = w.get_item_data()
            qty = Decimal(d["quantity"])
            rate = Decimal(d["unit_price"])
            disc = Decimal(d["discount_pct"])
            gst = Decimal(d["gst_rate_pct"] or "0")
            base = qty * rate
            after_disc = base * (1 - disc / 100)
            item_tax = after_disc * gst / 100
            subtotal += after_disc
            tax += item_tax

        total = subtotal + tax
        self.lbl_subtotal.setText(f"Subtotal: ₹{subtotal:,.2f}")
        self.lbl_tax.setText(f"Tax: ₹{tax:,.2f}")
        self.lbl_grand.setText(f"Total: ₹{total:,.2f}")

    def load_data(self, pf):
        # Party
        for i in range(self.cmb_party.count()):
            if self.cmb_party.itemData(i) == pf.get("party_id"):
                self.cmb_party.setCurrentIndex(i)
                break
        self.txt_pf_number.setText(pf.get("proforma_number", ""))
        self.txt_po_number.setText(pf.get("po_number", "") or "")
        self.txt_pi_number.setText(pf.get("pi_number", "") or "")

        d = pf.get("proforma_date")
        if d:
            self.dt_date.setDate(QDate(d.year, d.month, d.day))
        v = pf.get("valid_until")
        if v:
            self.dt_valid.setDate(QDate(v.year, v.month, v.day))

        if pf.get("is_interstate"):
            self.cmb_tax_mode.setCurrentIndex(1)
        else:
            self.cmb_tax_mode.setCurrentIndex(0)

        # Logistics
        self.txt_shipping_address.setPlainText(pf.get("shipping_address", "") or "")
        self.txt_transporter.setText(pf.get("transporter_name", "") or "")
        self.txt_vehicle_no.setText(pf.get("vehicle_number", "") or "")
        self.txt_lr_no.setText(pf.get("lr_no", "") or "")
        self.txt_eway_bill.setText(pf.get("eway_bill_no", "") or "")
        self.txt_destination.setText(pf.get("destination", "") or "")

        # Terms & Bank
        self.txt_terms.setPlainText(pf.get("terms_and_conditions", "") or "")
        self.txt_bank_name.setText(pf.get("bank_name", "") or "")
        self.txt_bank_ac.setText(pf.get("bank_account_no", "") or "")
        self.txt_bank_ifsc.setText(pf.get("bank_ifsc", "") or "")
        self.txt_notes.setPlainText(pf.get("notes", "") or "")

        # Items
        for w in list(self.item_widgets):
            self.items_layout.removeWidget(w)
            w.deleteLater()
        self.item_widgets.clear()

        for it in pf.get("items", []):
            widget = InvoiceItemWidget(products_list=self.products)
            widget.set_item_data(it)
            widget.item_changed.connect(self._update_totals)
            widget.remove_requested.connect(self._remove_item)
            self.item_widgets.append(widget)
            self.items_layout.insertWidget(self.items_layout.count() - 1, widget)

        self._update_totals()

    def get_data(self):
        qd = self.dt_date.date()
        dt_val = date(qd.year(), qd.month(), qd.day())
        vd = self.dt_valid.date()
        valid_val = date(vd.year(), vd.month(), vd.day())

        items = []
        subtotal = tax = Decimal("0")
        is_inter = self.cmb_tax_mode.currentIndex() == 1

        for w in self.item_widgets:
            d = w.get_item_data()
            qty = Decimal(d["quantity"])
            rate = Decimal(d["unit_price"])
            disc = Decimal(d["discount_pct"])
            gst = Decimal(d["gst_rate_pct"] or "0")
            base = qty * rate
            after_disc = base * (1 - disc / 100)
            item_tax = after_disc * gst / 100
            cgst = sgst = Decimal("0")
            igst = Decimal("0")
            if is_inter:
                igst = item_tax
            else:
                cgst = item_tax / 2
                sgst = item_tax / 2

            subtotal += after_disc
            tax += item_tax

            items.append({
                "product_id": d.get("product_id"),
                "item_description": d["item_description"],
                "hsn_code": d.get("hsn_code", ""),
                "quantity": float(qty),
                "unit": d.get("unit", "PCS"),
                "unit_price": float(rate),
                "discount_pct": float(disc),
                "taxable_amount": float(after_disc),
                "gst_rate_pct": float(gst),
                "cgst_amount": float(cgst),
                "sgst_amount": float(sgst),
                "igst_amount": float(igst),
                "total_amount": float(after_disc + item_tax),
            })

        return {
            "proforma_data": {
                "party_id": self.cmb_party.currentData(),
                "proforma_number": self.txt_pf_number.text().strip() or None,
                "po_number": self.txt_po_number.text().strip() or None,
                "pi_number": self.txt_pi_number.text().strip() or None,
                "proforma_date": dt_val,
                "valid_until": valid_val,
                "is_interstate": is_inter,
                "subtotal": float(subtotal),
                "tax_amount": float(tax),
                "total_amount": float(subtotal + tax),
                "notes": self.txt_notes.toPlainText(),
                "shipping_address": self.txt_shipping_address.toPlainText(),
                "transporter_name": self.txt_transporter.text(),
                "vehicle_number": self.txt_vehicle_no.text(),
                "lr_no": self.txt_lr_no.text(),
                "eway_bill_no": self.txt_eway_bill.text(),
                "destination": self.txt_destination.text(),
                "terms_and_conditions": self.txt_terms.toPlainText(),
                "bank_name": self.txt_bank_name.text(),
                "bank_account_no": self.txt_bank_ac.text(),
                "bank_ifsc": self.txt_bank_ifsc.text()
            },
            "items_data": items,
        }


class ProformaView(QWidget):
    """Proforma invoice list and management page."""
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        self.header_widget = PageHeaderWidget(
            title="Proforma Invoices",
            subtitle="Create and manage quotations / proforma invoices",
            action_text="New Proforma",
            action_icon="plus",
            action_callback=self.create_proforma
        )
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        self.header_widget.add_custom_action(btn_refresh)
        layout.addWidget(self.header_widget)

        # Filter bar
        filter_frame = CardFrame()
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search proformas by party, PO #, PI #, proforma #...")
        self.inp_search.textChanged.connect(self.load_data)
        fl.addWidget(self.inp_search, 2)
        layout.addWidget(filter_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Proforma #", "Date", "Party", "PO #", "PI #", "Tax (₹)", "Total (₹)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        for i in [0, 1, 5, 6, 7]:
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_proforma)
        layout.addWidget(self.table, 1)

        # Bottom bar
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 proformas")
        self.lbl_count.setFont(theme_manager.get_font("caption"))
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_convert = QPushButton("Convert to Invoice")
        btn_convert.setIcon(theme_manager.get_icon("invoices", size=16))
        btn_convert.setProperty("variant", "secondary")
        btn_convert.clicked.connect(self.convert_to_invoice)
        bottom.addWidget(btn_convert)

        btn_edit = QPushButton("Edit")
        btn_edit.setIcon(theme_manager.get_icon("edit", size=16))
        btn_edit.setProperty("variant", "secondary")
        btn_edit.clicked.connect(lambda: self.edit_proforma())
        bottom.addWidget(btn_edit)

        self.btn_print = QPushButton("Print PDF")
        self.btn_print.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_print.setProperty("variant", "secondary")
        self.btn_print.clicked.connect(self.print_proforma)
        bottom.addWidget(self.btn_print)

        btn_del = QPushButton("Delete")
        btn_del.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_del.setProperty("variant", "danger")
        btn_del.clicked.connect(self.delete_pf)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        pfs = proforma_service.get_all_proformas(search=search)
        self.table.setRowCount(len(pfs))

        for row, pf in enumerate(pfs):
            self.table.setItem(row, 0, QTableWidgetItem(pf["proforma_number"]))

            d = pf.get("proforma_date", "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str)
            self.table.setItem(row, 1, it_d)

            self.table.setItem(row, 2, QTableWidgetItem(pf.get("party_name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(pf.get("po_number", "") or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(pf.get("pi_number", "") or "—"))

            tax = float(pf.get("tax_amount", 0))
            it_tax = QTableWidgetItem(f"₹{tax:,.2f}")
            it_tax.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, it_tax)

            total = float(pf.get("total_amount", 0))
            it_total = QTableWidgetItem(f"₹{total:,.2f}")
            it_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, it_total)

            status = pf.get("status", "draft")
            badge = StatusBadgeLabel(status.upper(), status=status)
            self.table.setCellWidget(row, 7, badge)

        self.lbl_count.setText(f"{len(pfs)} proforma invoices")

    def create_proforma(self):
        dlg = ProformaFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                proforma_service.create_proforma(data["proforma_data"], data["items_data"])
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Proforma created successfully!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def edit_proforma(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0:
            return
        pf_num = self.table.item(row, 0).text()
        pf = proforma_service.get_proforma_by_number(pf_num)
        if not pf:
            return
        dlg = ProformaFormDialog(proforma_data=pf, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                proforma_service.update_proforma(pf["id"], data["proforma_data"], data["items_data"])
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Proforma updated successfully!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def delete_pf(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select a proforma to delete.")
            return
        pf_num = self.table.item(row, 0).text()
        pf = proforma_service.get_proforma_by_number(pf_num)
        if not pf:
            return
        if ThemedMessageBox.question(self, "Confirm Delete", f"Delete proforma {pf_num}?"):
            proforma_service.delete_proforma(pf["id"])
            self.load_data()

    def print_proforma(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select a proforma to print.")
            return
        pf_num = self.table.item(row, 0).text()
        pf_data = proforma_service.get_proforma_by_number(pf_num)
        if not pf_data:
            return

        try:
            from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            from app.config import EXPORTS_DIR

            generator = ProformaPDFGenerator()

            company_info = {}
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                if comp:
                    company_info = {
                        'name': comp.name or '',
                        'address': comp.address or '',
                        'city': comp.city or '',
                        'state': comp.state or '',
                        'state_code': comp.state_code or '',
                        'pincode': comp.pincode or '',
                        'gstin': comp.gstin or '',
                        'pan': comp.pan or '',
                        'phone': comp.phone or '',
                        'email': comp.email or '',
                        'bank_name': comp.bank_name or '',
                        'account_no': comp.bank_account_no or '',
                        'ifsc': comp.bank_ifsc or '',
                        'bank_branch': comp.bank_branch or '',
                        'upi_id': comp.upi_id or '',
                    }

            is_interstate = pf_data.get('is_interstate', False)
            tax_mode_str = 'inter_state' if is_interstate else 'intra_state'

            qd = pf_data.get('proforma_date', '')
            qd_str = qd.strftime('%d-%m-%Y') if hasattr(qd, 'strftime') else str(qd or '')
            vu = pf_data.get('valid_until', '')
            vu_str = vu.strftime('%d-%m-%Y') if hasattr(vu, 'strftime') and vu else str(vu or '')

            pdf_data = {
                'document_title': 'PROFORMA INVOICE',
                'doc_no_label': 'Proforma No.',
                'sub_title': '(QUOTATION / PRE-INVOICE)',
                'invoice_number': pf_data['proforma_number'],
                'date': qd_str,
                'valid_until': vu_str,
                'tax_mode': tax_mode_str,
                'po_number': pf_data.get('po_number', ''),
                'reference_number': pf_data.get('pi_number', ''),
                'company': company_info,
                'customer': {
                    'name': pf_data.get('party_name', ''),
                    'address': pf_data.get('party_address', ''),
                    'gstin': pf_data.get('party_gstin', ''),
                    'state': pf_data.get('party_state', ''),
                    'phone': pf_data.get('party_phone', '')
                },
                'logistics': {
                    'dispatch_doc_no': pf_data.get('lr_no', ''),
                    'waybill_no': pf_data.get('eway_bill_no', ''),
                    'dispatched_through': pf_data.get('transporter_name', ''),
                    'destination': pf_data.get('destination', ''),
                    'payment_terms': pf_data.get('terms_and_conditions', ''),
                    'po_date': '',
                    'buyer_order_no': pf_data.get('po_number', ''),
                    'terms_delivery': ''
                },
                'consignee': {
                    'address': pf_data.get('shipping_address', '')
                },
                'items': [],
                'totals': {
                    'taxable_amount': float(pf_data.get('subtotal', 0)),
                    'cgst_amount': float(pf_data.get('cgst_total', 0) or (pf_data.get('tax_amount', 0)/2 if not is_interstate else 0)),
                    'sgst_amount': float(pf_data.get('sgst_total', 0) or (pf_data.get('tax_amount', 0)/2 if not is_interstate else 0)),
                    'igst_amount': float(pf_data.get('igst_total', 0) or (pf_data.get('tax_amount', 0) if is_interstate else 0)),
                    'grand_total': float(pf_data.get('total_amount', 0)),
                }
            }

            for item in pf_data.get('items', []):
                qty = float(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0))
                gst_rate = float(item.get('gst_rate_pct', 0))
                cgst_amt = float(item.get('cgst_amount', 0))
                sgst_amt = float(item.get('sgst_amount', 0))
                igst_amt = float(item.get('igst_amount', 0))
                item_tax_amount = cgst_amt + sgst_amt + igst_amt

                pdf_data['items'].append({
                    'product_name': item.get('item_description', ''),
                    'description': '',
                    'hsn_code': item.get('hsn_code', ''),
                    'quantity': qty,
                    'unit': item.get('unit', 'PCS'),
                    'unit_price': unit_price,
                    'tax_rate': gst_rate,
                    'tax_amount': item_tax_amount,
                })

            safe_num = pf_data.get('proforma_number', 'DRAFT').replace('/', '-')
            p_name = pf_data.get('party_name', 'Party')
            suggested = f"Proforma_{safe_num}_{p_name}"

            def _generate(out_p):
                return generator.generate_proforma(pdf_data, filename=str(out_p))

            execute_export_pipeline(
                parent=self,
                suggested_name=suggested,
                kind="pdf",
                generator_fn=_generate,
                trigger_button=getattr(self, "btn_print", None)
            )

        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Could not generate PDF: {str(e)}")

    def convert_to_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select a proforma to convert.")
            return

        pf_num = self.table.item(row, 0).text()
        pf = proforma_service.get_proforma_by_number(pf_num)
        if not pf:
            return

        if ThemedMessageBox.question(
            self,
            "Convert to Invoice",
            f"Convert Proforma {pf_num} to Tax Invoice?\n\nThis will create an official invoice and deduct inventory stock."
        ):
            try:
                invoice = proforma_service.convert_to_invoice(pf["id"])
                if invoice:
                    self.load_data()
                    ThemedMessageBox.information(
                        self,
                        "Success",
                        f"Invoice {invoice.invoice_number} created from proforma {pf_num}!"
                    )
                else:
                    ThemedMessageBox.warning(self, "Error", "Conversion failed.")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))
