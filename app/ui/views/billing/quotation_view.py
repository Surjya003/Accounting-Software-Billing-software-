"""
Quotation Management View — Create, Edit, View, and Print Sales Quotations & Estimates.
Features a dashboard with summary KPI cards, advanced search, filtering, full CRUD,
real-time GST item calculation, invoice conversion, and PDF printing.
"""
import os
import subprocess
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit,
    QDateEdit, QTabWidget, QRadioButton, QButtonGroup, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from app.services.billing import quotation_service, product_service
from app.services.party_service import get_all_parties
from app.ui.widgets.stat_card import StatCard
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, StatusBadgeLabel, ThemedMessageBox,
    configure_dialog_window_flags
)
from app.ui.save_dialog import execute_export_pipeline


class QuotationItemWidget(QFrame):
    """Single line item row for quotation form."""
    item_changed = Signal()
    remove_requested = Signal(object)

    def __init__(self, products_list=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ItemRow")
        self.setProperty("variant", "sunken")
        self.setFrameShape(QFrame.StyledPanel)
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
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product or type description --")
        self.cmb_product.addItem("", None)
        for p in self.products:
            self.cmb_product.addItem(f"{p['name']} ({p.get('hsn_code', '')})", p)
        self.cmb_product.currentIndexChanged.connect(self._on_product_selected)
        layout.addWidget(self.cmb_product, 4)

        self.spn_qty = QDoubleSpinBox()
        self.spn_qty.setRange(0.001, 999999)
        self.spn_qty.setDecimals(3)
        self.spn_qty.setValue(1)
        self.spn_qty.setMaximumWidth(95)
        self.spn_qty.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_qty, 1)

        self.txt_unit = QLineEdit("PCS")
        self.txt_unit.setPlaceholderText("Unit")
        self.txt_unit.setMaximumWidth(50)
        layout.addWidget(self.txt_unit)

        self.spn_rate = QDoubleSpinBox()
        self.spn_rate.setRange(0, 99999999.99)
        self.spn_rate.setDecimals(2)
        self.spn_rate.setPrefix("₹")
        self.spn_rate.setMaximumWidth(115)
        self.spn_rate.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_rate, 1)

        self.spn_disc = QDoubleSpinBox()
        self.spn_disc.setRange(0, 100)
        self.spn_disc.setDecimals(2)
        self.spn_disc.setSuffix("%")
        self.spn_disc.setMaximumWidth(80)
        self.spn_disc.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_disc, 1)

        self.cmb_gst = QComboBox()
        self.cmb_gst.addItems(["0", "5", "12", "18", "28"])
        self.cmb_gst.setCurrentText("18")
        self.cmb_gst.setMaximumWidth(70)
        self.cmb_gst.currentTextChanged.connect(self._recalculate)
        layout.addWidget(self.cmb_gst, 1)

        self.lbl_total = QLabel("₹0.00")
        self.lbl_total.setFont(theme_manager.get_font("body", bold=True))
        self.lbl_total.setMinimumWidth(95)
        self.lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_total, 1)

        btn_remove = QPushButton()
        btn_remove.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_remove.setProperty("variant", "ghost")
        btn_remove.setFixedSize(28, 28)
        btn_remove.setToolTip("Remove Item")
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(btn_remove)

        self.lbl_hsn_warn = QLabel("⚠️ HSN missing")
        self.lbl_hsn_warn.setProperty("variant", "warning")
        self.lbl_hsn_warn.setToolTip("HSN/SAC missing (non-blocking warning; confirm with CA)")
        self.lbl_hsn_warn.setVisible(False)
        layout.addWidget(self.lbl_hsn_warn)

    def _on_product_selected(self, idx):
        data = self.cmb_product.itemData(idx)
        if data:
            self.spn_rate.setValue(float(data.get("price", 0)))
            self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))
            if data.get("unit"):
                self.txt_unit.setText(data.get("unit"))
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
        self.lbl_total.setText(f"₹{total:,.2f}")
        self.item_changed.emit()

    def get_item_data(self) -> Dict[str, Any]:
        idx = self.cmb_product.currentIndex()
        prod = self.cmb_product.itemData(idx) if idx >= 0 else None
        desc = self.cmb_product.currentText().strip()
        hsn = prod.get("hsn_code", "") if prod else ""
        qty = Decimal(str(self.spn_qty.value()))
        rate = Decimal(str(self.spn_rate.value()))
        disc = Decimal(str(self.spn_disc.value()))
        gst = Decimal(str(self.cmb_gst.currentText() or "0"))

        base = qty * rate
        discount = base * disc / Decimal("100")
        taxable = base - discount
        tax = taxable * gst / Decimal("100")
        total = taxable + tax

        return {
            "product_id": prod.get("id") if prod else None,
            "item_description": desc,
            "hsn_code": hsn,
            "quantity": float(qty),
            "unit": self.txt_unit.text().strip() or "PCS",
            "unit_price": float(rate),
            "discount_pct": float(disc),
            "gst_rate_pct": float(gst),
            "taxable_amount": float(taxable),
            "tax_amount": float(tax),
            "total_amount": float(total),
        }

    def set_item_data(self, item: Dict[str, Any]):
        p_id = item.get("product_id")
        if p_id:
            for idx in range(self.cmb_product.count()):
                d = self.cmb_product.itemData(idx)
                if d and d.get("id") == p_id:
                    self.cmb_product.setCurrentIndex(idx)
                    break
        else:
            self.cmb_product.setEditText(item.get("item_description", ""))

        self.spn_qty.setValue(float(item.get("quantity", 1)))
        self.txt_unit.setText(item.get("unit", "PCS"))
        self.spn_rate.setValue(float(item.get("unit_price", 0)))
        self.spn_disc.setValue(float(item.get("discount_pct", 0)))
        self.cmb_gst.setCurrentText(str(int(float(item.get("gst_rate_pct", 18)))))
        self._recalculate()
        hsn = str(item.get("hsn_code") or "").strip()
        self.lbl_hsn_warn.setVisible(not bool(hsn))


class QuotationFormDialog(QDialog):
    """Create / Edit Quotation Dialog."""

    def __init__(self, quote_data=None, parent=None):
        super().__init__(parent)
        self.quote_data = quote_data
        self.setWindowTitle("Edit Quotation" if quote_data else "New Quotation / Estimate")
        configure_dialog_window_flags(self, min_width=960, min_height=650)
        self.products = product_service.get_all_products()
        self.parties = get_all_parties()
        self.item_widgets: List[QuotationItemWidget] = []
        self.init_ui()
        if quote_data:
            self.load_quote_data(quote_data)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header Title
        title_text = "Edit Quotation" if self.quote_data else "Create New Quotation"
        lbl_title = QLabel(title_text)
        lbl_title.setFont(theme_manager.get_font("title", bold=True))
        main_layout.addWidget(lbl_title)

        # Tabs for layout
        tabs = QTabWidget()

        # --- TAB 1: Main Details & Items ---
        tab_main = QWidget()
        tab_main_layout = QVBoxLayout(tab_main)
        tab_main_layout.setContentsMargins(16, 16, 16, 16)
        tab_main_layout.setSpacing(12)

        # Top Grid: Party, Dates, Numbers
        top_grid = QHBoxLayout()
        top_grid.setSpacing(12)

        # Party selection
        party_box = QVBoxLayout()
        party_box.addWidget(QLabel("Customer / Party *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Customer --")
        for p in self.parties:
            gst_label = f" (GSTIN: {p.get('gstin')})" if p.get('gstin') else ""
            self.cmb_party.addItem(f"{p['name']}{gst_label}", p['id'])
        party_box.addWidget(self.cmb_party)
        top_grid.addLayout(party_box, 2)

        # Quotation Number
        quote_no_box = QVBoxLayout()
        quote_no_box.addWidget(QLabel("Quotation # (auto if blank)"))
        self.txt_quote_number = QLineEdit()
        self.txt_quote_number.setPlaceholderText("Auto-generated")
        quote_no_box.addWidget(self.txt_quote_number)
        top_grid.addLayout(quote_no_box, 1)

        # Reference Number
        ref_box = QVBoxLayout()
        ref_box.addWidget(QLabel("Reference / RFQ #"))
        self.txt_ref_number = QLineEdit()
        self.txt_ref_number.setPlaceholderText("Enquiry / Ref #")
        ref_box.addWidget(self.txt_ref_number)
        top_grid.addLayout(ref_box, 1)

        # Quotation Date
        date_box = QVBoxLayout()
        date_box.addWidget(QLabel("Quotation Date *"))
        self.dt_quote_date = QDateEdit()
        self.dt_quote_date.setCalendarPopup(True)
        self.dt_quote_date.setDate(QDate.currentDate())
        self.dt_quote_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_quote_date)
        top_grid.addLayout(date_box, 1)

        # Valid Until Date
        valid_box = QVBoxLayout()
        valid_box.addWidget(QLabel("Valid Until"))
        self.dt_valid_until = QDateEdit()
        self.dt_valid_until.setCalendarPopup(True)
        self.dt_valid_until.setDate(QDate.currentDate().addDays(30))
        self.dt_valid_until.setDisplayFormat("dd-MM-yyyy")
        valid_box.addWidget(self.dt_valid_until)
        top_grid.addLayout(valid_box, 1)

        tab_main_layout.addLayout(top_grid)

        # Status & Tax Mode Row
        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        # Status
        stat_box = QHBoxLayout()
        stat_box.addWidget(QLabel("Status:"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["draft", "sent", "accepted", "rejected", "converted"])
        stat_box.addWidget(self.cmb_status)
        status_row.addLayout(stat_box)

        # Tax Mode
        tax_box = QHBoxLayout()
        tax_box.addWidget(QLabel("Tax Supply:"))
        self.rb_intra = QRadioButton("Intra-State (CGST + SGST)")
        self.rb_inter = QRadioButton("Inter-State (IGST)")
        self.rb_intra.setChecked(True)
        self.btn_grp_tax = QButtonGroup(self)
        self.btn_grp_tax.addButton(self.rb_intra)
        self.btn_grp_tax.addButton(self.rb_inter)
        self.rb_intra.toggled.connect(self._recalculate_all)
        self.rb_inter.toggled.connect(self._recalculate_all)
        tax_box.addWidget(self.rb_intra)
        tax_box.addWidget(self.rb_inter)
        status_row.addLayout(tax_box)

        status_row.addStretch()
        tab_main_layout.addLayout(status_row)

        # Line Items Header
        items_header = QHBoxLayout()
        lbl_items = QLabel("Line Items")
        lbl_items.setFont(theme_manager.get_font("subtitle", bold=True))
        items_header.addWidget(lbl_items)
        items_header.addStretch()
        tab_main_layout.addLayout(items_header)

        # Items Table Headers
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(12, 0, 12, 0)
        hdr_row.setSpacing(8)
        lbl_h_prod = QLabel("Product / Description")
        lbl_h_qty = QLabel("Qty")
        lbl_h_unit = QLabel("Unit")
        lbl_h_rate = QLabel("Rate (₹)")
        lbl_h_disc = QLabel("Disc %")
        lbl_h_gst = QLabel("GST %")
        lbl_h_tot = QLabel("Total (₹)")
        lbl_h_tot.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_h_tot.setMinimumWidth(100)

        for l in (lbl_h_prod, lbl_h_qty, lbl_h_unit, lbl_h_rate, lbl_h_disc, lbl_h_gst, lbl_h_tot):
            l.setFont(theme_manager.get_font("caption", bold=True))

        hdr_row.addWidget(lbl_h_prod, 3)
        hdr_row.addWidget(lbl_h_qty, 1)
        lbl_h_unit.setMaximumWidth(55)
        hdr_row.addWidget(lbl_h_unit)
        hdr_row.addWidget(lbl_h_rate, 1)
        hdr_row.addWidget(lbl_h_disc, 1)
        hdr_row.addWidget(lbl_h_gst, 1)
        hdr_row.addWidget(lbl_h_tot, 1)
        hdr_spacer = QLabel("")
        hdr_spacer.setFixedSize(28, 28)
        hdr_row.addWidget(hdr_spacer)
        tab_main_layout.addLayout(hdr_row)

        # Scrollable items area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.items_layout = QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(4)
        self.items_layout.addStretch()
        scroll.setWidget(self.scroll_content)
        tab_main_layout.addWidget(scroll, 1)

        # Add Item Button
        btn_add_item = QPushButton(" Add Item")
        btn_add_item.setIcon(theme_manager.get_icon("plus", size=16))
        btn_add_item.setProperty("variant", "secondary")
        btn_add_item.setFixedHeight(34)
        btn_add_item.clicked.connect(lambda: self.add_item_row())
        tab_main_layout.addWidget(btn_add_item)

        tabs.addTab(tab_main, "1. Items & Pricing")

        # --- TAB 2: Shipping & Logistics ---
        tab_shipping = QWidget()
        ship_layout = QFormLayout(tab_shipping)
        ship_layout.setContentsMargins(16, 16, 16, 16)
        ship_layout.setSpacing(12)

        self.txt_ship_address = QTextEdit()
        self.txt_ship_address.setMaximumHeight(70)
        self.txt_ship_address.setPlaceholderText("Delivery / Consignee Address (if different from billing)")
        ship_layout.addRow("Shipping Address:", self.txt_ship_address)

        self.txt_destination = QLineEdit()
        self.txt_destination.setPlaceholderText("e.g. Mumbai, Maharashtra")
        ship_layout.addRow("Destination:", self.txt_destination)

        self.txt_transporter = QLineEdit()
        self.txt_transporter.setPlaceholderText("e.g. V-Trans / SafeXpress")
        ship_layout.addRow("Dispatched Through:", self.txt_transporter)

        self.txt_vehicle_no = QLineEdit()
        self.txt_vehicle_no.setPlaceholderText("e.g. MH-04-AB-1234")
        ship_layout.addRow("Vehicle Number:", self.txt_vehicle_no)

        self.txt_lr_no = QLineEdit()
        self.txt_lr_no.setPlaceholderText("LR / RR / Lorry Receipt No.")
        ship_layout.addRow("LR Number:", self.txt_lr_no)

        self.txt_eway_bill = QLineEdit()
        self.txt_eway_bill.setPlaceholderText("12-digit E-Way Bill Number")
        ship_layout.addRow("E-Way Bill #:", self.txt_eway_bill)

        self.txt_po_number = QLineEdit()
        self.txt_po_number.setPlaceholderText("Buyer Order / Purchase Order #")
        ship_layout.addRow("PO / Buyer Order #:", self.txt_po_number)

        tabs.addTab(tab_shipping, "2. Logistics & Shipping")

        # --- TAB 3: Terms, Bank & Notes ---
        tab_terms = QWidget()
        terms_layout = QFormLayout(tab_terms)
        terms_layout.setContentsMargins(16, 16, 16, 16)
        terms_layout.setSpacing(12)

        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(80)
        self.txt_terms.setPlainText("1. Goods once sold will not be taken back.\n2. Payment within 30 days.\n3. Subject to local jurisdiction.")
        terms_layout.addRow("Terms & Conditions:", self.txt_terms)

        self.txt_bank_name = QLineEdit()
        self.txt_bank_name.setPlaceholderText("e.g. HDFC Bank")
        terms_layout.addRow("Bank Name:", self.txt_bank_name)

        self.txt_bank_ac = QLineEdit()
        self.txt_bank_ac.setPlaceholderText("Account Number")
        terms_layout.addRow("Bank Account #:", self.txt_bank_ac)

        self.txt_bank_ifsc = QLineEdit()
        self.txt_bank_ifsc.setPlaceholderText("IFSC Code")
        terms_layout.addRow("Bank IFSC:", self.txt_bank_ifsc)

        self.txt_upi_id = QLineEdit()
        self.txt_upi_id.setPlaceholderText("company@upi")
        terms_layout.addRow("UPI ID:", self.txt_upi_id)

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)
        self.txt_notes.setPlaceholderText("Internal notes or client-facing remarks")
        terms_layout.addRow("Notes / Remarks:", self.txt_notes)

        tabs.addTab(tab_terms, "3. Terms & Bank Info")

        main_layout.addWidget(tabs, 1)

        # Summary Bar (Live totals)
        summary_frame = CardFrame()
        sum_layout = QHBoxLayout(summary_frame)
        sum_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_subtotal = QLabel("Subtotal: ₹0.00")
        self.lbl_subtotal.setFont(theme_manager.get_font("body", bold=True))
        sum_layout.addWidget(self.lbl_subtotal)
        sum_layout.addSpacing(20)

        self.lbl_tax = QLabel("Tax: ₹0.00")
        self.lbl_tax.setFont(theme_manager.get_font("body", bold=True))
        sum_layout.addWidget(self.lbl_tax)
        sum_layout.addSpacing(20)

        self.lbl_grand_total = QLabel("Total: ₹0.00")
        self.lbl_grand_total.setFont(theme_manager.get_font("subtitle", bold=True))
        sum_layout.addWidget(self.lbl_grand_total)
        sum_layout.addStretch()

        main_layout.addWidget(summary_frame)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Quotation")
        btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        btn_save.setProperty("variant", "primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

        # Start with at least one item row if creating new
        if not self.quote_data:
            self.add_item_row()

    def add_item_row(self, item_data=None):
        row = QuotationItemWidget(self.products, parent=self)
        row.item_changed.connect(self._recalculate_all)
        row.remove_requested.connect(self.remove_item_row)
        if item_data:
            row.set_item_data(item_data)
        self.item_widgets.append(row)
        self.items_layout.insertWidget(self.items_layout.count() - 1, row)
        self._recalculate_all()

    def remove_item_row(self, row_widget):
        if len(self.item_widgets) <= 1:
            ThemedMessageBox.warning(self, "Warning", "Quotation must have at least one line item.")
            return
        self.item_widgets.remove(row_widget)
        self.items_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self._recalculate_all()

    def _recalculate_all(self):
        subtotal = Decimal("0")
        cgst_total = Decimal("0")
        sgst_total = Decimal("0")
        igst_total = Decimal("0")
        is_inter = self.rb_inter.isChecked()

        for w in self.item_widgets:
            data = w.get_item_data()
            taxable = Decimal(str(data["taxable_amount"]))
            tax = Decimal(str(data["tax_amount"]))
            subtotal += taxable
            if is_inter:
                igst_total += tax
            else:
                cgst_total += tax / Decimal("2")
                sgst_total += tax / Decimal("2")

        grand = subtotal + cgst_total + sgst_total + igst_total
        tax_total = cgst_total + sgst_total + igst_total

        self.lbl_subtotal.setText(f"Subtotal: ₹{subtotal:,.2f}")
        tax_str = f"Tax: ₹{tax_total:,.2f}"
        if is_inter:
            tax_str += f" (IGST: ₹{igst_total:,.2f})"
        else:
            tax_str += f" (CGST: ₹{cgst_total:,.2f}, SGST: ₹{sgst_total:,.2f})"
        self.lbl_tax.setText(tax_str)
        self.lbl_grand_total.setText(f"Grand Total: ₹{grand:,.2f}")

    def load_quote_data(self, q):
        # Party
        p_id = q.get("party_id")
        for idx in range(self.cmb_party.count()):
            if self.cmb_party.itemData(idx) == p_id:
                self.cmb_party.setCurrentIndex(idx)
                break

        self.txt_quote_number.setText(q.get("quotation_number", ""))
        self.txt_ref_number.setText(q.get("reference_number", "") or "")

        qd = q.get("quotation_date")
        if qd:
            self.dt_quote_date.setDate(QDate(qd.year, qd.month, qd.day))

        vu = q.get("valid_until")
        if vu:
            self.dt_valid_until.setDate(QDate(vu.year, vu.month, vu.day))

        self.cmb_status.setCurrentText(q.get("status", "draft"))

        if q.get("is_interstate"):
            self.rb_inter.setChecked(True)
        else:
            self.rb_intra.setChecked(True)

        # Shipping & Terms
        self.txt_ship_address.setPlainText(q.get("shipping_address", "") or "")
        self.txt_destination.setText(q.get("destination", "") or "")
        self.txt_transporter.setText(q.get("transporter_name", "") or "")
        self.txt_vehicle_no.setText(q.get("vehicle_number", "") or "")
        self.txt_lr_no.setText(q.get("lr_no", "") or "")
        self.txt_eway_bill.setText(q.get("eway_bill_no", "") or "")
        self.txt_po_number.setText(q.get("po_number", "") or "")

        self.txt_terms.setPlainText(q.get("terms_and_conditions", "") or "")
        self.txt_bank_name.setText(q.get("bank_name", "") or "")
        self.txt_bank_ac.setText(q.get("bank_account_no", "") or "")
        self.txt_bank_ifsc.setText(q.get("bank_ifsc", "") or "")
        self.txt_upi_id.setText(q.get("upi_id", "") or "")
        self.txt_notes.setPlainText(q.get("notes", "") or "")

        # Items
        for w in list(self.item_widgets):
            self.remove_item_row(w)
        self.item_widgets.clear()

        items = q.get("items", [])
        for it in items:
            self.add_item_row(it)
        if not items:
            self.add_item_row()

    def get_data(self) -> Dict[str, Any]:
        p_idx = self.cmb_party.currentIndex()
        party_id = self.cmb_party.itemData(p_idx)

        qd = self.dt_quote_date.date()
        quote_date = date(qd.year(), qd.month(), qd.day())

        vu = self.dt_valid_until.date()
        valid_until = date(vu.year(), vu.month(), vu.day())

        is_inter = self.rb_inter.isChecked()

        items_data = [w.get_item_data() for w in self.item_widgets]

        subtotal = sum(Decimal(str(it["taxable_amount"])) for it in items_data)
        tax_total = sum(Decimal(str(it["tax_amount"])) for it in items_data)
        grand = subtotal + tax_total

        cgst = Decimal("0") if is_inter else tax_total / Decimal("2")
        sgst = Decimal("0") if is_inter else tax_total / Decimal("2")
        igst = tax_total if is_inter else Decimal("0")

        quote_data = {
            "party_id": party_id,
            "quotation_number": self.txt_quote_number.text().strip() or None,
            "reference_number": self.txt_ref_number.text().strip() or None,
            "quotation_date": quote_date,
            "valid_until": valid_until,
            "status": self.cmb_status.currentText(),
            "is_interstate": is_inter,
            "subtotal": float(subtotal),
            "tax_amount": float(tax_total),
            "cgst_total": float(cgst),
            "sgst_total": float(sgst),
            "igst_total": float(igst),
            "total_amount": float(grand),
            "shipping_address": self.txt_ship_address.toPlainText().strip() or None,
            "destination": self.txt_destination.text().strip() or None,
            "transporter_name": self.txt_transporter.text().strip() or None,
            "vehicle_number": self.txt_vehicle_no.text().strip() or None,
            "lr_no": self.txt_lr_no.text().strip() or None,
            "eway_bill_no": self.txt_eway_bill.text().strip() or None,
            "po_number": self.txt_po_number.text().strip() or None,
            "terms_and_conditions": self.txt_terms.toPlainText().strip() or None,
            "bank_name": self.txt_bank_name.text().strip() or None,
            "bank_account_no": self.txt_bank_ac.text().strip() or None,
            "bank_ifsc": self.txt_bank_ifsc.text().strip() or None,
            "upi_id": self.txt_upi_id.text().strip() or None,
            "notes": self.txt_notes.toPlainText().strip() or None,
        }

        return {"quote_data": quote_data, "items_data": items_data}

    def save(self):
        p_idx = self.cmb_party.currentIndex()
        if p_idx < 0 or not self.cmb_party.itemData(p_idx):
            ThemedMessageBox.warning(self, "Validation Error", "Please select a Customer / Party.")
            return

        if not self.item_widgets:
            ThemedMessageBox.warning(self, "Validation Error", "Please add at least one line item.")
            return

        for w in self.item_widgets:
            data = w.get_item_data()
            if not data["item_description"]:
                ThemedMessageBox.warning(self, "Validation Error", "Line items must have a product or description.")
                return
            if data["quantity"] <= 0:
                ThemedMessageBox.warning(self, "Validation Error", "Item quantity must be greater than zero.")
                return

        self.accept()


class QuotationView(QWidget):
    """Main Quotation / Proposal Management Screen."""
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. Header Section
        self.header_widget = PageHeaderWidget(
            title="Sales Quotations",
            subtitle="Create, track, and convert sales estimates & quotes",
            action_text="New Quotation",
            action_icon="plus",
            action_callback=self.create_quotation
        )
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        self.header_widget.add_custom_action(btn_refresh)
        layout.addWidget(self.header_widget)

        # 2. KPI StatCards Row (Dashboard part)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.card_total = StatCard("TOTAL QUOTATIONS", "0", "Total Value: ₹0.00", token_name="text_primary")
        self.card_draft = StatCard("DRAFT / IN-PROGRESS", "0", "Pending review", token_name="warning")
        self.card_sent = StatCard("SENT TO CLIENTS", "0", "Awaiting response", token_name="info")
        self.card_won = StatCard("ACCEPTED / CONVERTED", "0", "Won proposals", token_name="success")

        kpi_row.addWidget(self.card_total)
        kpi_row.addWidget(self.card_draft)
        kpi_row.addWidget(self.card_sent)
        kpi_row.addWidget(self.card_won)
        layout.addLayout(kpi_row)

        # 3. Filter & Search Bar
        filter_frame = CardFrame()
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(12)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search by quotation #, customer name, ref #...")
        self.inp_search.textChanged.connect(self.load_data)
        fl.addWidget(self.inp_search, 3)

        fl.addWidget(QLabel("Status:"))
        self.cmb_status_filter = QComboBox()
        self.cmb_status_filter.addItems(["All", "draft", "sent", "accepted", "rejected", "converted"])
        self.cmb_status_filter.currentTextChanged.connect(self.load_data)
        fl.addWidget(self.cmb_status_filter, 1)

        layout.addWidget(filter_frame)

        # 4. Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Quotation #", "Date", "Valid Until", "Customer / Party", "Ref #", "Taxable (₹)", "Tax (₹)", "Total (₹)", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        for i in range(5, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_quotation)
        layout.addWidget(self.table, 1)

        # 5. Bottom Toolbar
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 quotations")
        self.lbl_count.setFont(theme_manager.get_font("caption"))
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_convert = QPushButton("Convert to Invoice")
        btn_convert.setIcon(theme_manager.get_icon("invoices", size=16))
        btn_convert.setProperty("variant", "secondary")
        btn_convert.setToolTip("Convert selected quotation into a final Tax Invoice and deduct inventory stock")
        btn_convert.clicked.connect(self.convert_to_invoice)
        bottom.addWidget(btn_convert)

        btn_edit = QPushButton("Edit")
        btn_edit.setIcon(theme_manager.get_icon("edit", size=16))
        btn_edit.setProperty("variant", "secondary")
        btn_edit.clicked.connect(lambda: self.edit_quotation())
        bottom.addWidget(btn_edit)

        self.btn_print = QPushButton("Print PDF")
        self.btn_print.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_print.setProperty("variant", "secondary")
        self.btn_print.clicked.connect(self.print_quotation)
        bottom.addWidget(self.btn_print)

        btn_del = QPushButton("Delete")
        btn_del.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_del.setProperty("variant", "danger")
        btn_del.clicked.connect(self.delete_quotation)
        bottom.addWidget(btn_del)

        layout.addLayout(bottom)

        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') and self.inp_search.text().strip() else None
        status = self.cmb_status_filter.currentText() if hasattr(self, 'cmb_status_filter') else "All"

        quotes = quotation_service.get_all_quotations(search=search, status=status)
        self.table.setRowCount(len(quotes))

        total_value_sum = 0.0

        for row, q in enumerate(quotes):
            # 0: Quotation Number
            it_num = QTableWidgetItem(q.get("quotation_number", ""))
            it_num.setData(Qt.UserRole, q.get("id"))
            self.table.setItem(row, 0, it_num)

            # 1: Quotation Date
            qd = q.get("quotation_date", "")
            qd_str = qd.strftime("%d-%m-%Y") if hasattr(qd, 'strftime') else str(qd or "")
            it_qd = QTableWidgetItem(qd_str)
            self.table.setItem(row, 1, it_qd)

            # 2: Valid Until
            vu = q.get("valid_until", "")
            vu_str = vu.strftime("%d-%m-%Y") if hasattr(vu, 'strftime') and vu else str(vu or "—")
            it_vu = QTableWidgetItem(vu_str)
            self.table.setItem(row, 2, it_vu)

            # 3: Customer / Party
            self.table.setItem(row, 3, QTableWidgetItem(q.get("party_name", "")))

            # 4: Reference Number
            self.table.setItem(row, 4, QTableWidgetItem(q.get("reference_number", "") or "—"))

            # 5: Taxable (Subtotal)
            subtotal = float(q.get("subtotal", 0))
            it_sub = QTableWidgetItem(f"₹{subtotal:,.2f}")
            it_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, it_sub)

            # 6: Tax
            tax = float(q.get("tax_amount", 0))
            it_tax = QTableWidgetItem(f"₹{tax:,.2f}")
            it_tax.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, it_tax)

            # 7: Total
            tot = float(q.get("total_amount", 0))
            total_value_sum += tot
            it_tot = QTableWidgetItem(f"₹{tot:,.2f}")
            it_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 7, it_tot)

            # 8: Status Badge
            stat = q.get("status", "draft").lower()
            badge = StatusBadgeLabel(stat.upper(), status=stat)
            self.table.setCellWidget(row, 8, badge)

        self.lbl_count.setText(f"{len(quotes)} quotations | Total: ₹{total_value_sum:,.2f}")

        # Update KPI Cards
        try:
            kpis = quotation_service.get_quotation_kpis()
            self.card_total.set_value(str(kpis["total_count"]), f"Total Value: ₹{kpis['total_value']:,.2f}")
            self.card_draft.set_value(str(kpis["draft_count"]), "Draft / In preparation")
            self.card_sent.set_value(str(kpis["sent_count"]), "Sent to clients")
            self.card_won.set_value(str(kpis["accepted_count"] + kpis["converted_count"]), f"Converted: {kpis['converted_count']}")
        except Exception:
            pass

    def create_quotation(self):
        dlg = QuotationFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                quotation_service.create_quotation(data["quote_data"], data["items_data"])
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Quotation created successfully!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to create quotation: {str(e)}")

    def edit_quotation(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Please select a quotation to edit.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_data = quotation_service.get_quotation_by_id(quote_id)
        if not quote_data:
            ThemedMessageBox.critical(self, "Error", "Quotation not found.")
            return

        dlg = QuotationFormDialog(quote_data=quote_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                quotation_service.update_quotation(quote_id, data["quote_data"], data["items_data"])
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Quotation updated successfully!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to update quotation: {str(e)}")

    def delete_quotation(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Please select a quotation to delete.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_num = item.text()

        if ThemedMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete quotation {quote_num}?"
        ):
            try:
                quotation_service.delete_quotation(quote_id)
                self.load_data()
                ThemedMessageBox.information(self, "Deleted", f"Quotation {quote_num} deleted.")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Could not delete quotation: {str(e)}")

    def print_quotation(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Please select a quotation to print.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        q_data = quotation_service.get_quotation_by_id(quote_id)
        if not q_data:
            return

        try:
            from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            from app.config import EXPORTS_DIR

            generator = QuotationPDFGenerator()

            # Load Company Profile
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

            is_interstate = q_data.get('is_interstate', False)
            tax_mode_str = 'inter_state' if is_interstate else 'intra_state'

            qd = q_data.get('quotation_date', '')
            qd_str = qd.strftime('%d-%m-%Y') if hasattr(qd, 'strftime') else str(qd or '')
            vu = q_data.get('valid_until', '')
            vu_str = vu.strftime('%d-%m-%Y') if hasattr(vu, 'strftime') and vu else str(vu or '')

            pdf_data = {
                'document_title': 'QUOTATION',
                'doc_no_label': 'Quotation No.',
                'sub_title': '(COMMERCIAL ESTIMATE / PROPOSAL)',
                'invoice_number': q_data['quotation_number'],
                'date': qd_str,
                'valid_until': vu_str,
                'tax_mode': tax_mode_str,
                'po_number': q_data.get('po_number', ''),
                'reference_number': q_data.get('reference_number', ''),
                'company': company_info,
                'customer': {
                    'name': q_data.get('party_name', ''),
                    'address': q_data.get('party_address', ''),
                    'gstin': q_data.get('party_gstin', ''),
                    'state': q_data.get('party_state', ''),
                    'phone': q_data.get('party_phone', '')
                },
                'logistics': {
                    'dispatch_doc_no': q_data.get('lr_no', ''),
                    'waybill_no': q_data.get('eway_bill_no', ''),
                    'dispatched_through': q_data.get('transporter_name', ''),
                    'destination': q_data.get('destination', ''),
                    'payment_terms': q_data.get('terms_and_conditions', ''),
                    'po_date': '',
                    'buyer_order_no': q_data.get('po_number', ''),
                    'terms_delivery': ''
                },
                'consignee': {
                    'address': q_data.get('shipping_address', '')
                },
                'items': [],
                'totals': {
                    'taxable_amount': float(q_data.get('subtotal', 0)),
                    'cgst_amount': float(q_data.get('cgst_total', 0)),
                    'sgst_amount': float(q_data.get('sgst_total', 0)),
                    'igst_amount': float(q_data.get('igst_total', 0)),
                    'grand_total': float(q_data.get('total_amount', 0)),
                }
            }

            for item in q_data.get('items', []):
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

            safe_num = q_data.get('quotation_number', 'DRAFT').replace('/', '-')
            p_name = q_data.get('party_name', 'Customer')
            suggested = f"Quotation_{safe_num}_{p_name}"

            def _generate(out_p):
                return generator.generate_quotation(pdf_data, filename=str(out_p))

            execute_export_pipeline(
                parent=self,
                suggested_name=suggested,
                kind="pdf",
                generator_fn=_generate,
                trigger_button=getattr(self, "btn_print", None)
            )

        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Could not generate Quotation PDF: {str(e)}")

    def convert_to_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Please select a quotation to convert into an invoice.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_num = item.text()

        if ThemedMessageBox.question(
            self,
            "Convert to Tax Invoice",
            f"Convert quotation {quote_num} to a Tax Invoice?\n\nThis will generate an official invoice and deduct inventory stock."
        ):
            try:
                invoice = quotation_service.convert_to_invoice(quote_id)
                self.load_data()
                ThemedMessageBox.information(
                    self,
                    "Quotation Converted",
                    f"Successfully generated Invoice #{invoice.invoice_number} from Quotation {quote_num}!"
                )
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", f"Failed to convert quotation: {str(e)}")
