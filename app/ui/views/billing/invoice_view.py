"""
Invoice Management View — Create, Edit, View GST Tax Invoices
Polished with BillFlow Enterprise Theme System.
"""
import os
import subprocess
from datetime import date
from decimal import Decimal
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit,
    QDateEdit, QTabWidget, QRadioButton, QButtonGroup, QCheckBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate, QEvent
from PySide6.QtGui import QFont, QColor

from app.services.billing import invoice_service, product_service
from app.services.party_service import get_all_parties
from app.ui.theme import (
    theme_manager, PageHeaderWidget, CardFrame, ThemedMessageBox, StatusBadgeLabel,
    configure_dialog_window_flags
)
from app.ui.save_dialog import execute_export_pipeline


class InvoiceItemWidget(QFrame):
    """Single line item row for the invoice form."""
    item_changed = Signal()
    remove_requested = Signal(object)
    add_row_requested = Signal(object)

    def __init__(self, products_list=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ItemRow")
        self.setProperty("variant", "sunken")
        self.setMinimumHeight(38)
        self.setMaximumHeight(44)
        self.products = products_list or []
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        self.cmb_product = QComboBox()
        self.cmb_product.setEditable(True)
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product --")
        self.cmb_product.addItem("", None)
        for p in self.products:
            self.cmb_product.addItem(f"{p['name']} ({p.get('hsn_code', '')})", p)
        self.cmb_product.currentIndexChanged.connect(self._on_product_selected)
        layout.addWidget(self.cmb_product, 4)

        self.spn_qty = QDoubleSpinBox()
        self.spn_qty.setRange(0.001, 999999)
        self.spn_qty.setDecimals(3)
        self.spn_qty.setValue(1)
        self.spn_qty.setMaximumWidth(100)
        self.spn_qty.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_qty, 1)

        self.spn_rate = QDoubleSpinBox()
        self.spn_rate.setRange(0, 99999999.99)
        self.spn_rate.setDecimals(2)
        self.spn_rate.setPrefix("₹")
        self.spn_rate.setMaximumWidth(120)
        self.spn_rate.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_rate, 1)

        self.spn_disc = QDoubleSpinBox()
        self.spn_disc.setRange(0, 100)
        self.spn_disc.setDecimals(2)
        self.spn_disc.setSuffix("%")
        self.spn_disc.setMaximumWidth(85)
        self.spn_disc.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_disc, 1)

        self.cmb_gst = QComboBox()
        self.cmb_gst.addItems(["0", "5", "12", "18", "28"])
        self.cmb_gst.setCurrentText("18")
        self.cmb_gst.setMaximumWidth(75)
        self.cmb_gst.currentTextChanged.connect(self._recalculate)
        self.cmb_gst.installEventFilter(self)
        layout.addWidget(self.cmb_gst, 1)

        self.lbl_total = QLabel("₹0.00")
        self.lbl_total.setProperty("variant", "tabular")
        self.lbl_total.setFont(theme_manager.font("tabular"))
        self.lbl_total.setMinimumWidth(95)
        self.lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_total, 1)

        btn_remove = QPushButton()
        btn_remove.setProperty("variant", "danger")
        btn_remove.setIcon(theme_manager.icon("close", color_token="danger", size=14))
        btn_remove.setFixedSize(28, 28)
        btn_remove.setToolTip("Remove line item")
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(btn_remove)

        self.lbl_hsn_warn = QLabel("⚠️ HSN missing")
        self.lbl_hsn_warn.setProperty("variant", "warning")
        self.lbl_hsn_warn.setToolTip("HSN/SAC missing (non-blocking warning; confirm with CA)")
        self.lbl_hsn_warn.setVisible(False)
        layout.addWidget(self.lbl_hsn_warn)

    def eventFilter(self, watched, event):
        if watched == self.cmb_gst and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.add_row_requested.emit(self)
                return True
        return super().eventFilter(watched, event)

    def _on_product_selected(self, idx):
        data = self.cmb_product.itemData(idx)
        if data:
            self.spn_rate.setValue(data.get("price", 0))
            self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))
            hsn = str(data.get("hsn_code") or "").strip()
            self.lbl_hsn_warn.setVisible(not bool(hsn))
        else:
            self.lbl_hsn_warn.setVisible(False)
        self._recalculate()

    def _recalculate(self):
        qty = Decimal(str(self.spn_qty.value()))
        rate = Decimal(str(self.spn_rate.value()))
        disc = Decimal(str(self.spn_disc.value()))
        gst = Decimal(str(self.cmb_gst.currentText() or "0"))
        base = qty * rate
        discount = base * disc / Decimal("100")
        taxable = base - discount
        tax = taxable * gst / Decimal("100")
        total = taxable + tax
        self.lbl_total.setText(f"₹{float(total):,.2f}")
        self.item_changed.emit()

    def get_item_data(self):
        product_data = self.cmb_product.currentData()
        product_id = product_data["id"] if product_data else None
        desc = self.cmb_product.currentText()
        if product_data:
            desc = product_data["name"]
        return {
            "product_id": product_id,
            "item_description": desc,
            "hsn_code": product_data.get("hsn_code", "") if product_data else "",
            "quantity": str(self.spn_qty.value()),
            "unit": product_data.get("unit", "PCS") if product_data else "PCS",
            "unit_price": str(self.spn_rate.value()),
            "discount_pct": str(self.spn_disc.value()),
            "gst_rate_pct": self.cmb_gst.currentText(),
            "tax_rate": self.cmb_gst.currentText(),
        }

    def set_item_data(self, item_data):
        product_id = item_data.get("product_id")
        matched = False
        if product_id:
            for i in range(self.cmb_product.count()):
                pd = self.cmb_product.itemData(i)
                if pd and pd.get("id") == product_id:
                    self.cmb_product.setCurrentIndex(i)
                    matched = True
                    break
        if not matched and item_data.get("item_description"):
            self.cmb_product.setEditText(item_data.get("item_description", ""))

        self.spn_qty.setValue(float(item_data.get("quantity", 1)))
        self.spn_rate.setValue(float(item_data.get("unit_price", 0)))
        self.spn_disc.setValue(float(item_data.get("discount_pct", 0)))
        gst_val = item_data.get("gst_rate_pct")
        if gst_val is None or str(gst_val).strip() == "":
            gst_val = item_data.get("tax_rate", 18)
        gst = str(int(float(gst_val if gst_val is not None else 18)))
        self.cmb_gst.setCurrentText(gst)
        self._recalculate()
        hsn = str(item_data.get("hsn_code") or "").strip()
        self.lbl_hsn_warn.setVisible(not bool(hsn))

    populate_item = set_item_data


class InvoiceFormDialog(QDialog):
    """Create / Edit invoice dialog with enterprise layout and totals hierarchy."""

    def __init__(self, invoice_data=None, parent=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.setWindowTitle("Edit Invoice" if invoice_data else "New Tax Invoice")
        configure_dialog_window_flags(self, min_width=980, min_height=660)
        self.resize(1040, 750)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()

        if self.invoice_data:
            self.populate(self.invoice_data)
            items = self.invoice_data.get("items", [])
            if items:
                self.item_widgets[0].populate_item(items[0])
                for it in items[1:]:
                    self.add_item_row()
                    self.item_widgets[-1].populate_item(it)
            self._update_totals()
        else:
            self._load_company_defaults()

    def _load_company_defaults(self):
        from app.database.connection import get_session
        from app.database.models import CompanyProfile
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                self.txt_terms.setPlainText(comp.terms_conditions or "")
                self.txt_bank_name.setText(comp.bank_name or "")
                self.txt_bank_ac.setText(comp.bank_account_no or "")
                self.txt_bank_ifsc.setText(comp.bank_ifsc or "")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        title = QLabel("Edit Tax Invoice" if self.invoice_data else "Create New Tax Invoice")
        title.setProperty("variant", "title")
        title.setFont(theme_manager.font("title"))
        layout.addWidget(title)

        # Consolidated Header Card (Party, Date, Status, Numbers, Tax Mode)
        header_card = CardFrame()
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(8)

        # Row 1: Party (stretch 3), Date (stretch 1), Status (stretch 1), Invoice No (stretch 2)
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        party_box = QVBoxLayout()
        lbl_party = QLabel("Party *")
        lbl_party.setProperty("variant", "label")
        party_box.addWidget(lbl_party)
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Party --")
        self.cmb_party.addItem("", None)
        parties = get_all_parties()
        for p in parties:
            self.cmb_party.addItem(p["name"], p["id"])
        party_box.addWidget(self.cmb_party)
        row1.addLayout(party_box, 3)

        date_box = QVBoxLayout()
        lbl_date = QLabel("Invoice Date *")
        lbl_date.setProperty("variant", "label")
        date_box.addWidget(lbl_date)
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_date)
        row1.addLayout(date_box, 1)

        status_box = QVBoxLayout()
        lbl_status = QLabel("Status")
        lbl_status.setProperty("variant", "label")
        status_box.addWidget(lbl_status)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["draft", "final", "cancelled"])
        status_box.addWidget(self.cmb_status)
        row1.addLayout(status_box, 1)

        inv_no_box = QVBoxLayout()
        lbl_inv_no = QLabel("Invoice Number (auto if blank)")
        lbl_inv_no.setProperty("variant", "label")
        inv_no_box.addWidget(lbl_inv_no)
        self.txt_invoice_number = QLineEdit()
        self.txt_invoice_number.setPlaceholderText("Auto-generated e.g. INV/24-25/0001")
        inv_no_box.addWidget(self.txt_invoice_number)
        row1.addLayout(inv_no_box, 2)

        header_layout.addLayout(row1)

        # Row 2: Buyer PO # (stretch 1), PI Reference (stretch 1), Tax Mode (stretch 2)
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        po_box = QVBoxLayout()
        lbl_po = QLabel("PO Number")
        lbl_po.setProperty("variant", "label")
        po_box.addWidget(lbl_po)
        self.txt_po_number = QLineEdit()
        self.txt_po_number.setPlaceholderText("Buyer PO No.")
        po_box.addWidget(self.txt_po_number)
        row2.addLayout(po_box, 1)

        pi_box = QVBoxLayout()
        lbl_pi = QLabel("PI Number")
        lbl_pi.setProperty("variant", "label")
        pi_box.addWidget(lbl_pi)
        self.txt_pi_number = QLineEdit()
        self.txt_pi_number.setPlaceholderText("Proforma Reference")
        pi_box.addWidget(self.txt_pi_number)
        row2.addLayout(pi_box, 1)

        tax_box = QVBoxLayout()
        lbl_tax_mode = QLabel("Tax Mode")
        lbl_tax_mode.setProperty("variant", "label")
        tax_box.addWidget(lbl_tax_mode)
        self.tax_mode_group = QButtonGroup()
        tax_layout = QHBoxLayout()
        self.rb_auto = QRadioButton("Auto")
        self.rb_intra = QRadioButton("Intra-State (CGST+SGST)")
        self.rb_inter = QRadioButton("Inter-State (IGST)")
        self.rb_auto.setChecked(True)
        self.tax_mode_group.addButton(self.rb_auto, 0)
        self.tax_mode_group.addButton(self.rb_intra, 1)
        self.tax_mode_group.addButton(self.rb_inter, 2)
        tax_layout.addWidget(self.rb_auto)
        tax_layout.addWidget(self.rb_intra)
        tax_layout.addWidget(self.rb_inter)
        tax_box.addLayout(tax_layout)
        row2.addLayout(tax_box, 2)

        header_layout.addLayout(row2)
        layout.addWidget(header_card)

        # Tabs Container
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # === TAB 1: LINE ITEMS ===
        tab_items = QWidget()
        tab_items_layout = QVBoxLayout(tab_items)
        tab_items_layout.setContentsMargins(12, 10, 12, 10)
        tab_items_layout.setSpacing(8)

        # Items header row
        items_header = QHBoxLayout()
        lbl_items = QLabel("Line Items")
        lbl_items.setProperty("variant", "subtitle")
        items_header.addWidget(lbl_items)
        items_header.addStretch()

        btn_add_item = QPushButton("Add Item")
        btn_add_item.setProperty("variant", "primary")
        btn_add_item.setIcon(theme_manager.icon("add", color_token="text_on_accent", size=14))
        btn_add_item.clicked.connect(self.add_item_row)
        items_header.addWidget(btn_add_item)
        tab_items_layout.addLayout(items_header)

        # Column labels aligned with ItemRow inputs
        col_labels = QHBoxLayout()
        col_labels.setContentsMargins(8, 0, 8, 0)
        col_labels.setSpacing(8)
        lbl_prod = QLabel("Product")
        lbl_prod.setProperty("variant", "caption")
        col_labels.addWidget(lbl_prod, 4)
        for label, w in [("Qty", 100), ("Rate (₹)", 120), ("Disc %", 85), ("GST %", 75)]:
            lbl = QLabel(label)
            lbl.setProperty("variant", "caption")
            lbl.setMaximumWidth(w)
            col_labels.addWidget(lbl, 1)
        lbl_t = QLabel("Total")
        lbl_t.setProperty("variant", "caption")
        lbl_t.setMinimumWidth(95)
        lbl_t.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        col_labels.addWidget(lbl_t, 1)
        lbl_sp = QLabel("")
        lbl_sp.setFixedSize(28, 28)
        col_labels.addWidget(lbl_sp)
        tab_items_layout.addLayout(col_labels)

        # Items scroll area
        items_scroll = QWidget()
        self.items_layout = QVBoxLayout(items_scroll)
        self.items_layout.setSpacing(6)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(items_scroll)
        scroll_area.setMinimumHeight(140)
        tab_items_layout.addWidget(scroll_area, 1)

        # Add first item row
        self.add_item_row()

        # Polished Totals Panel with Clear Hierarchy
        totals_frame = CardFrame()
        totals_frame.setMinimumHeight(60)
        totals_frame.setMaximumHeight(74)
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.setContentsMargins(16, 8, 16, 8)
        totals_layout.setSpacing(24)
        totals_layout.addStretch()

        # Subtotal
        sub_box = QVBoxLayout()
        lbl_sub_title = QLabel("TAXABLE VALUE")
        lbl_sub_title.setProperty("variant", "caption")
        sub_box.addWidget(lbl_sub_title)
        self.lbl_subtotal = QLabel("₹0.00")
        self.lbl_subtotal.setProperty("variant", "tabular")
        self.lbl_subtotal.setFont(theme_manager.font("body"))
        sub_box.addWidget(self.lbl_subtotal)
        totals_layout.addLayout(sub_box)

        # Tax
        tax_tot_box = QVBoxLayout()
        lbl_tax_title = QLabel("TOTAL GST")
        lbl_tax_title.setProperty("variant", "caption")
        tax_tot_box.addWidget(lbl_tax_title)
        self.lbl_tax = QLabel("₹0.00")
        self.lbl_tax.setProperty("variant", "tabular")
        self.lbl_tax.setFont(theme_manager.font("body"))
        tax_tot_box.addWidget(self.lbl_tax)
        totals_layout.addLayout(tax_tot_box)

        # Grand Total
        grand_box = QVBoxLayout()
        lbl_grand_title = QLabel("GRAND TOTAL")
        lbl_grand_title.setProperty("variant", "caption")
        grand_box.addWidget(lbl_grand_title)
        self.lbl_grand = QLabel("₹0.00")
        self.lbl_grand.setProperty("variant", "tabular")
        f_grand = theme_manager.font("headline")
        f_grand.setBold(True)
        self.lbl_grand.setFont(f_grand)
        grand_box.addWidget(self.lbl_grand)
        totals_layout.addLayout(grand_box)

        tab_items_layout.addWidget(totals_frame, 0)
        self.tabs.addTab(tab_items, "Items & Totals")

        # === TAB 2: DELIVERY & REFERENCES ===
        tab_delivery = QWidget()
        tab_delivery_layout = QFormLayout(tab_delivery)
        tab_delivery_layout.setContentsMargins(16, 16, 16, 16)
        tab_delivery_layout.setSpacing(10)

        self.txt_delivery_note = QLineEdit()
        self.txt_delivery_note.setPlaceholderText("Delivery note number / Challan reference")
        tab_delivery_layout.addRow("Delivery Note:", self.txt_delivery_note)

        self.txt_mode_terms_payment = QLineEdit()
        self.txt_mode_terms_payment.setPlaceholderText("e.g. Net 30 Days / Cheque / Advance / Cash / UPI")
        tab_delivery_layout.addRow("Mode/Terms of Payment:", self.txt_mode_terms_payment)

        self.txt_ref_no_date = QLineEdit()
        self.txt_ref_no_date.setPlaceholderText("e.g. REF-2026-001 dt 15-10-2026")
        tab_delivery_layout.addRow("Reference No. & Date.:", self.txt_ref_no_date)

        self.txt_other_references = QLineEdit()
        self.txt_other_references.setPlaceholderText("e.g. Quotation Ref / Sales Order Ref / Project Ref")
        tab_delivery_layout.addRow("Other Reference:", self.txt_other_references)

        self.txt_terms_of_delivery = QTextEdit()
        self.txt_terms_of_delivery.setMaximumHeight(75)
        self.txt_terms_of_delivery.setPlaceholderText("e.g. Ex-Works / Door delivery / Freight to pay / Delivery within 7 days")
        tab_delivery_layout.addRow("Terms of Delivery:", self.txt_terms_of_delivery)

        self.tabs.addTab(tab_delivery, "Delivery & References")

        # === TAB 3: LOGISTICS ===
        tab_log = QWidget()
        tab_log_layout = QFormLayout(tab_log)
        tab_log_layout.setContentsMargins(16, 16, 16, 16)
        tab_log_layout.setSpacing(10)

        self.chk_same_address = QCheckBox("Same as Party Billing Address")
        self.chk_same_address.stateChanged.connect(self.toggle_shipping_address)
        tab_log_layout.addRow("", self.chk_same_address)

        self.txt_shipping_address = QTextEdit()
        self.txt_shipping_address.setMaximumHeight(60)
        tab_log_layout.addRow("Shipping Address:", self.txt_shipping_address)

        self.txt_transporter = QLineEdit()
        tab_log_layout.addRow("Transporter Name:", self.txt_transporter)

        self.txt_vehicle_no = QLineEdit()
        tab_log_layout.addRow("Vehicle No:", self.txt_vehicle_no)

        self.txt_lr_no = QLineEdit()
        tab_log_layout.addRow("LR No:", self.txt_lr_no)

        self.dt_lr_date = QDateEdit(QDate.currentDate())
        self.dt_lr_date.setCalendarPopup(True)
        self.dt_lr_date.setDisplayFormat("dd-MM-yyyy")
        tab_log_layout.addRow("LR Date:", self.dt_lr_date)

        self.txt_eway_bill = QLineEdit()
        tab_log_layout.addRow("E-Way Bill No:", self.txt_eway_bill)

        self.txt_destination = QLineEdit()
        tab_log_layout.addRow("Destination:", self.txt_destination)

        self.tabs.addTab(tab_log, "Shipping & Logistics")

        # === TAB 4: TERMS & BANK ===
        tab_terms = QWidget()
        tab_terms_layout = QFormLayout(tab_terms)
        tab_terms_layout.setContentsMargins(16, 16, 16, 16)
        tab_terms_layout.setSpacing(10)

        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(80)
        self.txt_terms.setPlaceholderText("e.g. Goods once sold cannot be returned.")
        tab_terms_layout.addRow("Terms & Conditions:", self.txt_terms)

        self.txt_bank_name = QLineEdit()
        tab_terms_layout.addRow("Bank Name:", self.txt_bank_name)

        self.txt_bank_ac = QLineEdit()
        tab_terms_layout.addRow("Bank A/C No:", self.txt_bank_ac)

        self.txt_bank_ifsc = QLineEdit()
        tab_terms_layout.addRow("Bank IFSC Code:", self.txt_bank_ifsc)

        self.tabs.addTab(tab_terms, "Terms & Bank")

        # Optional Notes
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(45)
        self.txt_notes.setPlaceholderText("Optional remarks or invoice notes...")
        layout.addWidget(self.txt_notes)

        # Dialog Buttons (Cancel on left, Primary Save on right)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Invoice")
        self.btn_save.setProperty("variant", "primary")
        self.btn_save.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_save_clicked(self):
        self.btn_save.setEnabled(False)
        try:
            self.accept()
        finally:
            self.btn_save.setEnabled(True)

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
        item.add_row_requested.connect(self._on_item_add_row_requested)
        self.item_widgets.append(item)
        insert_pos = self.items_layout.count() - 1
        self.items_layout.insertWidget(insert_pos, item)
        return item

    def _on_item_add_row_requested(self, item):
        if self.item_widgets and self.item_widgets[-1] == item:
            new_item = self.add_item_row()
            new_item.cmb_product.setFocus()

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
            gst = Decimal(d["tax_rate"])

            base = qty * rate
            discount = base * disc / Decimal("100")
            taxable = base - discount
            t_amt = taxable * gst / Decimal("100")

            subtotal += taxable
            tax += t_amt

        grand = subtotal + tax
        self.lbl_subtotal.setText(f"₹{float(subtotal):,.2f}")
        self.lbl_tax.setText(f"₹{float(tax):,.2f}")
        self.lbl_grand.setText(f"₹{float(grand):,.2f}")

    def populate(self, inv):
        self.txt_invoice_number.setText(inv.get("invoice_number", ""))
        self.txt_po_number.setText(inv.get("po_number", "") or "")
        self.txt_pi_number.setText(inv.get("pi_number", "") or "")

        self.txt_delivery_note.setText(inv.get("delivery_note", "") or "")
        self.txt_mode_terms_payment.setText(inv.get("mode_terms_of_payment", "") or "")
        self.txt_ref_no_date.setText(inv.get("reference_no_date", "") or "")
        self.txt_other_references.setText(inv.get("other_references", "") or "")
        self.txt_terms_of_delivery.setPlainText(inv.get("terms_of_delivery", "") or "")

        party_id = inv.get("party_id")
        if party_id:
            for i in range(self.cmb_party.count()):
                if self.cmb_party.itemData(i) == party_id:
                    self.cmb_party.setCurrentIndex(i)
                    break

        d = inv.get("invoice_date")
        if d:
            if hasattr(d, "year"):
                self.dt_date.setDate(QDate(d.year, d.month, d.day))

        status = inv.get("status", "draft")
        idx = self.cmb_status.findText(status)
        if idx >= 0:
            self.cmb_status.setCurrentIndex(idx)

        self.txt_shipping_address.setPlainText(inv.get("shipping_address", "") or "")
        self.txt_transporter.setText(inv.get("transporter_name", "") or "")
        self.txt_vehicle_no.setText(inv.get("vehicle_no", "") or "")
        self.txt_lr_no.setText(inv.get("lr_no", "") or "")
        self.txt_eway_bill.setText(inv.get("eway_bill_no", "") or "")
        self.txt_destination.setText(inv.get("destination", "") or "")
        self.txt_terms.setPlainText(inv.get("terms_conditions", "") or "")
        self.txt_notes.setPlainText(inv.get("notes", "") or "")

    def get_data(self):
        q_d = self.dt_date.date()
        inv_date = date(q_d.year(), q_d.month(), q_d.day())
        q_lr_d = self.dt_lr_date.date()
        lr_date = date(q_lr_d.year(), q_lr_d.month(), q_lr_d.day())

        # Determine tax mode
        tax_mode_id = self.tax_mode_group.checkedId()
        is_interstate = None
        if tax_mode_id == 1:
            is_interstate = False
        elif tax_mode_id == 2:
            is_interstate = True

        invoice_data = {
            "invoice_number": self.txt_invoice_number.text().strip(),
            "party_id": self.cmb_party.currentData(),
            "invoice_date": inv_date,
            "po_number": self.txt_po_number.text().strip(),
            "pi_number": self.txt_pi_number.text().strip(),
            "delivery_note": self.txt_delivery_note.text().strip(),
            "mode_terms_of_payment": self.txt_mode_terms_payment.text().strip(),
            "reference_no_date": self.txt_ref_no_date.text().strip(),
            "other_references": self.txt_other_references.text().strip(),
            "terms_of_delivery": self.txt_terms_of_delivery.toPlainText().strip(),
            "status": self.cmb_status.currentText(),
            "is_interstate": is_interstate,
            "shipping_address": self.txt_shipping_address.toPlainText().strip(),
            "transporter_name": self.txt_transporter.text().strip(),
            "vehicle_no": self.txt_vehicle_no.text().strip(),
            "lr_no": self.txt_lr_no.text().strip(),
            "lr_date": lr_date,
            "eway_bill_no": self.txt_eway_bill.text().strip(),
            "destination": self.txt_destination.text().strip(),
            "terms_conditions": self.txt_terms.toPlainText().strip(),
            "terms_and_conditions": self.txt_terms.toPlainText().strip(),
            "notes": self.txt_notes.toPlainText().strip(),
            "bank_name": self.txt_bank_name.text().strip(),
            "bank_account_no": self.txt_bank_ac.text().strip(),
            "bank_ifsc": self.txt_bank_ifsc.text().strip(),
        }

        items_data = [w.get_item_data() for w in self.item_widgets]
        return {"invoice_data": invoice_data, "items_data": items_data}


class InvoiceView(QWidget):
    """Invoice list and management page."""
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Page Header
        header = PageHeaderWidget("Tax Invoices", "Create and manage GST tax invoices for commercial customers")
        header.add_action_button("New Invoice", icon_name="add", variant="primary", callback=self.create_invoice)
        header.add_action_button("Refresh", icon_name="refresh", variant="secondary", callback=self.load_invoices)
        layout.addWidget(header)

        # Filter bar
        filter_frame = CardFrame()
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search by invoice number or party name...")
        self.inp_search.textChanged.connect(self.load_invoices)
        fl.addWidget(self.inp_search, 2)

        lbl_status = QLabel("Status:")
        lbl_status.setProperty("variant", "label")
        fl.addWidget(lbl_status)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["All", "draft", "final", "cancelled"])
        self.cmb_status.currentTextChanged.connect(self.load_invoices)
        fl.addWidget(self.cmb_status)

        layout.addWidget(filter_frame)

        # Invoice table (36px rows)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Invoice #", "Date", "Party", "PO #", "PI #", "Subtotal (₹)", "Tax (₹)", "Total (₹)", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        for i in range(5, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_invoice)
        layout.addWidget(self.table, 1)

        # Bottom Action Bar
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 invoices")
        self.lbl_count.setProperty("variant", "caption")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_edit = QPushButton("Edit")
        btn_edit.setProperty("variant", "secondary")
        btn_edit.setIcon(theme_manager.icon("edit", size=14))
        btn_edit.clicked.connect(self.edit_invoice)
        bottom.addWidget(btn_edit)

        self.btn_print = QPushButton("Print Selected")
        self.btn_print.setProperty("variant", "secondary")
        self.btn_print.setIcon(theme_manager.icon("print", size=14))
        self.btn_print.clicked.connect(self.print_invoice)
        bottom.addWidget(self.btn_print)

        btn_del = QPushButton("Delete Selected")
        btn_del.setProperty("variant", "danger")
        btn_del.setIcon(theme_manager.icon("delete", color_token="danger", size=14))
        btn_del.clicked.connect(self.delete_invoice)
        bottom.addWidget(btn_del)

        layout.addLayout(bottom)
        self.load_invoices()

    def load_invoices(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        status = self.cmb_status.currentText() if hasattr(self, 'cmb_status') else None

        invoices = invoice_service.get_all_invoices(search=search, status=status)
        self.table.setRowCount(len(invoices))
        mono = theme_manager.font("tabular")
        mono_bold = theme_manager.font("tabular")
        mono_bold.setBold(True)

        for row, inv in enumerate(invoices):
            it_num = QTableWidgetItem(inv["invoice_number"])
            it_num.setData(Qt.UserRole, inv["id"])
            self.table.setItem(row, 0, it_num)

            d = inv.get("invoice_date", "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_date = QTableWidgetItem(d_str)
            it_date.setFont(mono)
            self.table.setItem(row, 1, it_date)

            self.table.setItem(row, 2, QTableWidgetItem(inv.get("party_name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(inv.get("po_number", "") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(inv.get("pi_number", "") or ""))

            # Subtotal
            it_sub = QTableWidgetItem(f"₹{inv.get('subtotal', 0):,.2f}")
            it_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_sub.setFont(mono)
            self.table.setItem(row, 5, it_sub)

            # Tax
            it_tax = QTableWidgetItem(f"₹{inv.get('tax_amount', 0):,.2f}")
            it_tax.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_tax.setFont(mono)
            self.table.setItem(row, 6, it_tax)

            # Grand Total
            it_tot = QTableWidgetItem(f"₹{inv.get('total_amount', 0):,.2f}")
            it_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_tot.setFont(mono_bold)
            self.table.setItem(row, 7, it_tot)

            # Status pill badge
            st = inv.get("status", "draft")
            badge = StatusBadgeLabel(st.capitalize())
            self.table.setCellWidget(row, 8, badge)

        self.lbl_count.setText(f"{len(invoices)} invoices")

    def create_invoice(self):
        dlg = InvoiceFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                invoice_service.create_invoice(data["invoice_data"], data["items_data"])
                self.load_invoices()
                ThemedMessageBox.information(self, "Success", "Invoice created successfully!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def edit_invoice(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0:
            return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_data = invoice_service.get_invoice_by_id(inv_id)
        if not inv_data:
            return
        dlg = InvoiceFormDialog(invoice_data=inv_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                invoice_service.update_invoice(inv_id, data["invoice_data"], data["items_data"])
                self.load_invoices()
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def delete_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select an invoice to delete.")
            return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_num = self.table.item(row, 0).text()
        reply = ThemedMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete invoice {inv_num}?")
        if reply:
            invoice_service.delete_invoice(inv_id)
            self.load_invoices()

    def print_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select an invoice to print.")
            return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_data = invoice_service.get_invoice_by_id(inv_id)
        if not inv_data:
            return

        from app.services.billing.invoice_pdf_generator import generate_invoice_pdf
        inv_num = inv_data.get("invoice_number", "INV")
        p_name = inv_data.get("party_name", "Customer")
        suggested = f"Invoice_{inv_num}_{p_name}"

        def _generate(out_p):
            return generate_invoice_pdf(inv_data, output_path=str(out_p))

        execute_export_pipeline(
            parent=self,
            suggested_name=suggested,
            kind="pdf",
            generator_fn=_generate,
            trigger_button=getattr(self, "btn_print", None)
        )
