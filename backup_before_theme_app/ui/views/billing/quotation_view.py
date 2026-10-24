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
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit, QMessageBox,
    QDateEdit, QTabWidget, QRadioButton, QButtonGroup, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.billing import quotation_service, product_service
from app.services.party_service import get_all_parties
from app.ui.widgets.stat_card import StatCard


class QuotationItemWidget(QFrame):
    """Single line item row for quotation form."""
    item_changed = Signal()
    remove_requested = Signal(object)

    def __init__(self, products_list=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ItemRow")
        self.setStyleSheet("""
            QFrame#ItemRow {
                background-color: #FBFBF9;
                border: 1px solid #D4C49E;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.setMinimumHeight(48)
        self.setMaximumHeight(56)
        self.products = products_list or []
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.cmb_product = QComboBox()
        self.cmb_product.setEditable(True)
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product or type description --")
        self.cmb_product.addItem("", None)
        for p in self.products:
            self.cmb_product.addItem(f"{p['name']} ({p.get('hsn_code', '')})", p)
        self.cmb_product.currentIndexChanged.connect(self._on_product_selected)
        layout.addWidget(self.cmb_product, 3)

        self.spn_qty = QDoubleSpinBox()
        self.spn_qty.setRange(0.001, 999999)
        self.spn_qty.setDecimals(3)
        self.spn_qty.setValue(1)
        self.spn_qty.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_qty, 1)

        self.txt_unit = QLineEdit("PCS")
        self.txt_unit.setPlaceholderText("Unit")
        self.txt_unit.setMaximumWidth(55)
        layout.addWidget(self.txt_unit)

        self.spn_rate = QDoubleSpinBox()
        self.spn_rate.setRange(0, 99999999.99)
        self.spn_rate.setDecimals(2)
        self.spn_rate.setPrefix("₹")
        self.spn_rate.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_rate, 1)

        self.spn_disc = QDoubleSpinBox()
        self.spn_disc.setRange(0, 100)
        self.spn_disc.setDecimals(2)
        self.spn_disc.setSuffix("%")
        self.spn_disc.valueChanged.connect(self._recalculate)
        layout.addWidget(self.spn_disc, 1)

        self.cmb_gst = QComboBox()
        self.cmb_gst.addItems(["0", "5", "12", "18", "28"])
        self.cmb_gst.setCurrentText("18")
        self.cmb_gst.currentTextChanged.connect(self._recalculate)
        layout.addWidget(self.cmb_gst, 1)

        self.lbl_total = QLabel("₹0.00")
        self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px; color: #1B1B18;")
        self.lbl_total.setMinimumWidth(100)
        self.lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_total, 1)

        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(28, 28)
        btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px; background: transparent;")
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(btn_remove)

    def _on_product_selected(self, idx):
        data = self.cmb_product.itemData(idx)
        if data:
            self.spn_rate.setValue(float(data.get("price", 0)))
            self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))
            if data.get("unit"):
                self.txt_unit.setText(data.get("unit"))
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

    def get_item_data(self) -> Dict[str, Any]:
        product_data = self.cmb_product.currentData()
        product_id = product_data["id"] if product_data else None
        desc = self.cmb_product.currentText()
        if product_data:
            desc = product_data["name"]
        hsn = product_data.get("hsn_code", "") if product_data else ""
        return {
            "product_id": product_id,
            "item_description": desc,
            "hsn_code": hsn,
            "quantity": self.spn_qty.value(),
            "unit": self.txt_unit.text().strip() or "PCS",
            "unit_price": self.spn_rate.value(),
            "discount_pct": self.spn_disc.value(),
            "gst_rate_pct": float(self.cmb_gst.currentText() or "0")
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


class QuotationFormDialog(QDialog):
    """Create / Edit Quotation Dialog."""

    def __init__(self, quote_data=None, parent=None):
        super().__init__(parent)
        self.quote_data = quote_data
        self.setWindowTitle("Edit Quotation" if quote_data else "New Quotation / Estimate")
        self.setMinimumSize(960, 680)
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
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")
        main_layout.addWidget(lbl_title)

        # Tabs for layout
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }
            QTabBar::tab { background: #EFECE6; color: #6B6558; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; color: #1B1B18; font-weight: 600; border: 1px solid #D4C49E; border-bottom: none; }
        """)

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
        self.txt_quote_number.setPlaceholderText("Auto e.g. QT/24-25/0001")
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
        date_box.addWidget(self.dt_quote_date)
        top_grid.addLayout(date_box, 1)

        # Valid Until Date
        valid_box = QVBoxLayout()
        valid_box.addWidget(QLabel("Valid Until"))
        self.dt_valid_until = QDateEdit()
        self.dt_valid_until.setCalendarPopup(True)
        self.dt_valid_until.setDate(QDate.currentDate().addDays(30))
        valid_box.addWidget(self.dt_valid_until)
        top_grid.addLayout(valid_box, 1)

        tab_main_layout.addLayout(top_grid)

        # Status & Tax Mode Row
        tax_status_row = QHBoxLayout()
        tax_status_row.setSpacing(16)

        # Status
        status_box = QHBoxLayout()
        status_box.addWidget(QLabel("Status:"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["draft", "sent", "accepted", "rejected", "converted"])
        self.cmb_status.setCurrentText("draft")
        status_box.addWidget(self.cmb_status)
        tax_status_row.addLayout(status_box)

        # Tax Mode
        tax_mode_box = QHBoxLayout()
        tax_mode_box.addWidget(QLabel("Tax Mode:"))
        self.tax_mode_group = QButtonGroup(self)
        self.rb_auto = QRadioButton("Auto (GSTIN-based)")
        self.rb_intra = QRadioButton("Intra-State (CGST + SGST)")
        self.rb_inter = QRadioButton("Inter-State (IGST)")
        self.tax_mode_group.addButton(self.rb_auto, 0)
        self.tax_mode_group.addButton(self.rb_intra, 1)
        self.tax_mode_group.addButton(self.rb_inter, 2)
        self.rb_auto.setChecked(True)
        tax_mode_box.addWidget(self.rb_auto)
        tax_mode_box.addWidget(self.rb_intra)
        tax_mode_box.addWidget(self.rb_inter)
        self.tax_mode_group.idClicked.connect(lambda _: self._recalculate_all())
        tax_status_row.addLayout(tax_mode_box)
        tax_status_row.addStretch()

        tab_main_layout.addLayout(tax_status_row)

        # Line Items Header
        tab_main_layout.addWidget(QLabel("<b>Quotation Line Items</b>"))

        # Items Table Headers
        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(8, 0, 8, 0)
        hdr_layout.setSpacing(8)
        lbl_p = QLabel("Product / Description"); hdr_layout.addWidget(lbl_p, 3)
        lbl_q = QLabel("Qty"); hdr_layout.addWidget(lbl_q, 1)
        lbl_u = QLabel("Unit"); lbl_u.setMaximumWidth(55); hdr_layout.addWidget(lbl_u)
        lbl_r = QLabel("Rate (₹)"); hdr_layout.addWidget(lbl_r, 1)
        lbl_d = QLabel("Disc %"); hdr_layout.addWidget(lbl_d, 1)
        lbl_g = QLabel("GST %"); hdr_layout.addWidget(lbl_g, 1)
        lbl_t = QLabel("Amount (₹)"); lbl_t.setMinimumWidth(100); lbl_t.setAlignment(Qt.AlignRight); hdr_layout.addWidget(lbl_t, 1)
        lbl_act = QLabel(""); lbl_act.setFixedWidth(28); hdr_layout.addWidget(lbl_act)
        tab_main_layout.addLayout(hdr_layout)

        # Scrollable items area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #D4C49E; background: #FFFFFF; border-radius: 4px; }")
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(4, 4, 4, 4)
        self.items_layout.setSpacing(4)
        self.items_layout.addStretch()
        scroll.setWidget(self.items_container)
        tab_main_layout.addWidget(scroll, 1)

        # Add Item Button
        btn_add_item = QPushButton("+ Add Line Item")
        btn_add_item.setObjectName("SecondaryBtn")
        btn_add_item.setFixedHeight(32)
        btn_add_item.clicked.connect(self.add_item_row)
        tab_main_layout.addWidget(btn_add_item)

        tabs.addTab(tab_main, "1. Items & Pricing")

        # --- TAB 2: Shipping & Logistics ---
        tab_ship = QWidget()
        ship_layout = QFormLayout(tab_ship)
        ship_layout.setContentsMargins(16, 16, 16, 16)
        ship_layout.setSpacing(12)

        self.txt_shipping_address = QTextEdit()
        self.txt_shipping_address.setMaximumHeight(70)
        self.txt_shipping_address.setPlaceholderText("Delivery / Shipping Address (leave blank to use Party billing address)")
        ship_layout.addRow("Shipping Address:", self.txt_shipping_address)

        self.txt_transporter = QLineEdit()
        self.txt_transporter.setPlaceholderText("Transport carrier name")
        ship_layout.addRow("Transporter Name:", self.txt_transporter)

        self.txt_vehicle_no = QLineEdit()
        self.txt_vehicle_no.setPlaceholderText("e.g. MH-04-AB-1234")
        ship_layout.addRow("Vehicle Number:", self.txt_vehicle_no)

        self.txt_lr_no = QLineEdit()
        self.txt_lr_no.setPlaceholderText("Lorry Receipt / Consignment Note No.")
        ship_layout.addRow("LR / Dispatch Doc No:", self.txt_lr_no)

        self.dt_lr_date = QDateEdit()
        self.dt_lr_date.setCalendarPopup(True)
        self.dt_lr_date.setDate(QDate.currentDate())
        ship_layout.addRow("LR Date:", self.dt_lr_date)

        self.txt_eway_bill = QLineEdit()
        self.txt_eway_bill.setPlaceholderText("E-Way Bill No. (if applicable)")
        ship_layout.addRow("E-Way Bill No:", self.txt_eway_bill)

        self.txt_destination = QLineEdit()
        self.txt_destination.setPlaceholderText("Destination City / Town")
        ship_layout.addRow("Destination:", self.txt_destination)

        tabs.addTab(tab_ship, "2. Logistics & Delivery")

        # --- TAB 3: Terms, Bank & Notes ---
        tab_terms = QWidget()
        terms_layout = QFormLayout(tab_terms)
        terms_layout.setContentsMargins(16, 16, 16, 16)
        terms_layout.setSpacing(12)

        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(80)
        self.txt_terms.setPlainText("1. Quotation validity: 30 days from date of issue.\n2. Goods once dispatched cannot be returned.\n3. Payment: 100% advance or as agreed.")
        terms_layout.addRow("Terms & Conditions:", self.txt_terms)

        self.txt_bank_name = QLineEdit()
        terms_layout.addRow("Bank Name:", self.txt_bank_name)

        self.txt_bank_ac = QLineEdit()
        terms_layout.addRow("Bank Account #:", self.txt_bank_ac)

        self.txt_bank_ifsc = QLineEdit()
        terms_layout.addRow("Bank IFSC Code:", self.txt_bank_ifsc)

        self.txt_po_number = QLineEdit()
        self.txt_po_number.setPlaceholderText("Customer's PO Number")
        terms_layout.addRow("PO Number:", self.txt_po_number)

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)
        self.txt_notes.setPlaceholderText("Internal notes or client-facing remarks")
        terms_layout.addRow("Notes / Remarks:", self.txt_notes)

        tabs.addTab(tab_terms, "3. Terms & Bank Info")

        main_layout.addWidget(tabs, 1)

        # Summary Bar (Live totals)
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #F7F5EE; border: 1px solid #D4C49E; border-radius: 4px; padding: 8px 16px;")
        sum_layout = QHBoxLayout(summary_frame)
        sum_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_subtotal = QLabel("Subtotal: ₹0.00")
        self.lbl_subtotal.setStyleSheet("font-family: Consolas; font-weight: 600; color: #1B1B18;")
        sum_layout.addWidget(self.lbl_subtotal)
        sum_layout.addSpacing(20)

        self.lbl_tax = QLabel("Tax: ₹0.00")
        self.lbl_tax.setStyleSheet("font-family: Consolas; font-weight: 600; color: #2C3E63;")
        sum_layout.addWidget(self.lbl_tax)
        sum_layout.addSpacing(20)

        self.lbl_grand_total = QLabel("Total: ₹0.00")
        self.lbl_grand_total.setStyleSheet("font-family: Consolas; font-size: 15px; font-weight: bold; color: #2F6844;")
        sum_layout.addWidget(self.lbl_grand_total)
        sum_layout.addStretch()

        main_layout.addWidget(summary_frame)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Quotation")
        btn_save.setObjectName("PrimaryBtn")
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
            QMessageBox.warning(self, "Warning", "Quotation must have at least one line item.")
            return
        self.item_widgets.remove(row_widget)
        self.items_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self._recalculate_all()

    def _recalculate_all(self):
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        for w in self.item_widgets:
            qty = Decimal(str(w.spn_qty.value()))
            rate = Decimal(str(w.spn_rate.value()))
            disc = Decimal(str(w.spn_disc.value()))
            gst = Decimal(str(w.cmb_gst.currentText() or "0"))
            base = qty * rate
            disc_amt = base * disc / Decimal("100")
            taxable = base - disc_amt
            tax = taxable * gst / Decimal("100")
            subtotal += taxable
            tax_total += tax

        grand = subtotal + tax_total
        self.lbl_subtotal.setText(f"Subtotal: ₹{float(subtotal):,.2f}")
        self.lbl_tax.setText(f"Tax: ₹{float(tax_total):,.2f}")
        self.lbl_grand_total.setText(f"Total: ₹{float(grand):,.2f}")

    def load_quote_data(self, data: Dict[str, Any]):
        party_id = data.get("party_id")
        for idx in range(self.cmb_party.count()):
            if self.cmb_party.itemData(idx) == party_id:
                self.cmb_party.setCurrentIndex(idx)
                break

        self.txt_quote_number.setText(data.get("quotation_number", "") or "")
        self.txt_ref_number.setText(data.get("reference_number", "") or "")
        self.txt_po_number.setText(data.get("po_number", "") or "")

        if data.get("quotation_date"):
            d = data["quotation_date"]
            if hasattr(d, 'year'):
                self.dt_quote_date.setDate(QDate(d.year, d.month, d.day))

        if data.get("valid_until"):
            d = data["valid_until"]
            if hasattr(d, 'year'):
                self.dt_valid_until.setDate(QDate(d.year, d.month, d.day))

        status = data.get("status", "draft")
        self.cmb_status.setCurrentText(status)

        self.txt_notes.setPlainText(data.get("notes", "") or "")
        self.txt_shipping_address.setPlainText(data.get("shipping_address", "") or "")
        self.txt_transporter.setText(data.get("transporter_name", "") or "")
        self.txt_vehicle_no.setText(data.get("vehicle_no", "") or "")
        self.txt_lr_no.setText(data.get("lr_no", "") or "")
        if data.get("lr_date"):
            d = data["lr_date"]
            if hasattr(d, 'year'):
                self.dt_lr_date.setDate(QDate(d.year, d.month, d.day))
        self.txt_eway_bill.setText(data.get("eway_bill_no", "") or "")
        self.txt_destination.setText(data.get("destination", "") or "")
        self.txt_terms.setPlainText(data.get("terms_and_conditions", "") or "")
        self.txt_bank_name.setText(data.get("bank_name", "") or "")
        self.txt_bank_ac.setText(data.get("bank_ac_no", "") or "")
        self.txt_bank_ifsc.setText(data.get("bank_ifsc", "") or "")

        # Items
        items = data.get("items", [])
        if items:
            for w in self.item_widgets:
                self.items_layout.removeWidget(w)
                w.deleteLater()
            self.item_widgets.clear()
            for it in items:
                self.add_item_row(it)

    def get_data(self) -> Dict[str, Any]:
        party_id = self.cmb_party.currentData()
        qd = self.dt_quote_date.date()
        vd = self.dt_valid_until.date()
        lrd = self.dt_lr_date.date()
        items = [w.get_item_data() for w in self.item_widgets]
        q_num = self.txt_quote_number.text().strip() or None

        return {
            "quote_data": {
                "party_id": party_id,
                "quotation_number": q_num,
                "quotation_date": date(qd.year(), qd.month(), qd.day()),
                "valid_until": date(vd.year(), vd.month(), vd.day()) if vd.isValid() else None,
                "status": self.cmb_status.currentText(),
                "tax_mode": self.tax_mode_group.checkedId(),
                "notes": self.txt_notes.toPlainText().strip(),
                "reference_number": self.txt_ref_number.text().strip(),
                "po_number": self.txt_po_number.text().strip(),
                "shipping_address": self.txt_shipping_address.toPlainText().strip(),
                "transporter_name": self.txt_transporter.text().strip(),
                "vehicle_no": self.txt_vehicle_no.text().strip(),
                "lr_no": self.txt_lr_no.text().strip(),
                "lr_date": date(lrd.year(), lrd.month(), lrd.day()) if lrd.isValid() else None,
                "eway_bill_no": self.txt_eway_bill.text().strip(),
                "destination": self.txt_destination.text().strip(),
                "terms_and_conditions": self.txt_terms.toPlainText().strip(),
                "bank_name": self.txt_bank_name.text().strip(),
                "bank_ac_no": self.txt_bank_ac.text().strip(),
                "bank_ifsc": self.txt_bank_ifsc.text().strip()
            },
            "items_data": items
        }

    def save(self):
        party_id = self.cmb_party.currentData()
        if not party_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer / Party.")
            return

        items = [w.get_item_data() for w in self.item_widgets]
        if not items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one line item.")
            return

        for it in items:
            if not it.get("item_description"):
                QMessageBox.warning(self, "Validation Error", "Line items must have a product or description.")
                return
            if it.get("quantity", 0) <= 0:
                QMessageBox.warning(self, "Validation Error", "Item quantity must be greater than zero.")
                return

        self.accept()


class QuotationView(QWidget):
    """Quotation Dashboard & Management Page."""
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 1. Header Section
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl = QLabel("Quotations & Estimates")
        lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl)
        lbl_sub = QLabel("Create, track, print, and convert commercial quotations to invoices")
        lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_new = QPushButton("+ New Quotation")
        btn_new.setObjectName("PrimaryBtn")
        btn_new.setFixedHeight(36)
        btn_new.clicked.connect(self.create_quotation)
        header.addWidget(btn_new)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # 2. KPI StatCards Row (Dashboard part)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.card_total = StatCard("TOTAL QUOTATIONS", "0", "Total Value: ₹0.00", value_color="#1B1B18")
        self.card_draft = StatCard("DRAFT / IN-PROGRESS", "0", "Pending review", value_color="#A6822E")
        self.card_sent = StatCard("SENT TO CLIENTS", "0", "Awaiting response", value_color="#2C3E63")
        self.card_won = StatCard("ACCEPTED / CONVERTED", "0", "Won proposals", value_color="#2F6844")

        kpi_row.addWidget(self.card_total)
        kpi_row.addWidget(self.card_draft)
        kpi_row.addWidget(self.card_sent)
        kpi_row.addWidget(self.card_won)
        layout.addLayout(kpi_row)

        # 3. Filter & Search Bar
        filter_frame = QFrame()
        filter_frame.setObjectName("Card")
        filter_frame.setStyleSheet("""
            QFrame#Card {
                background-color: #FFFFFF;
                border: 1px solid #D4C49E;
                border-radius: 4px;
                padding: 4px;
            }
        """)
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
        self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_convert = QPushButton("Convert to Invoice")
        btn_convert.setObjectName("PrimaryBtn")
        btn_convert.setToolTip("Convert selected quotation into a final Tax Invoice and deduct inventory stock")
        btn_convert.clicked.connect(self.convert_to_invoice)
        bottom.addWidget(btn_convert)

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("SecondaryBtn")
        btn_edit.clicked.connect(lambda: self.edit_quotation())
        bottom.addWidget(btn_edit)

        btn_print = QPushButton("Print PDF")
        btn_print.setObjectName("PrimaryBtn")
        btn_print.clicked.connect(self.print_quotation)
        bottom.addWidget(btn_print)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DestructiveBtn")
        btn_del.clicked.connect(self.delete_quotation)
        bottom.addWidget(btn_del)

        layout.addLayout(bottom)

        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') and self.inp_search.text().strip() else None
        status = self.cmb_status_filter.currentText() if hasattr(self, 'cmb_status_filter') else "All"

        quotes = quotation_service.get_all_quotations(search=search, status=status)
        self.table.setRowCount(len(quotes))
        mono = QFont("Consolas", 10)

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
            it_qd.setFont(mono)
            self.table.setItem(row, 1, it_qd)

            # 2: Valid Until
            vu = q.get("valid_until", "")
            vu_str = vu.strftime("%d-%m-%Y") if hasattr(vu, 'strftime') and vu else str(vu or "—")
            it_vu = QTableWidgetItem(vu_str)
            it_vu.setFont(mono)
            self.table.setItem(row, 2, it_vu)

            # 3: Customer / Party
            self.table.setItem(row, 3, QTableWidgetItem(q.get("party_name", "")))

            # 4: Reference Number
            self.table.setItem(row, 4, QTableWidgetItem(q.get("reference_number", "") or "—"))

            # 5: Taxable (Subtotal)
            subtotal = float(q.get("subtotal", 0))
            it_sub = QTableWidgetItem(f"₹{subtotal:,.2f}")
            it_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_sub.setFont(mono)
            self.table.setItem(row, 5, it_sub)

            # 6: Tax
            tax = float(q.get("tax_amount", 0))
            it_tax = QTableWidgetItem(f"₹{tax:,.2f}")
            it_tax.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_tax.setFont(mono)
            self.table.setItem(row, 6, it_tax)

            # 7: Total
            tot = float(q.get("total_amount", 0))
            total_value_sum += tot
            it_tot = QTableWidgetItem(f"₹{tot:,.2f}")
            it_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_tot.setFont(mono)
            self.table.setItem(row, 7, it_tot)

            # 8: Status Badge
            stat = q.get("status", "draft").lower()
            it_s = QTableWidgetItem(stat.upper())
            it_s.setTextAlignment(Qt.AlignCenter)
            color_map = {
                "draft": "#A6822E",
                "sent": "#2C3E63",
                "accepted": "#2F6844",
                "converted": "#155724",
                "rejected": "#8B2635",
                "expired": "#6B6558"
            }
            it_s.setForeground(QColor(color_map.get(stat, "#1B1B18")))
            self.table.setItem(row, 8, it_s)

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
                QMessageBox.information(self, "Success", "Quotation created successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create quotation: {str(e)}")

    def edit_quotation(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a quotation to edit.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_data = quotation_service.get_quotation_by_id(quote_id)
        if not quote_data:
            QMessageBox.critical(self, "Error", "Quotation not found.")
            return

        dlg = QuotationFormDialog(quote_data=quote_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                quotation_service.update_quotation(quote_id, data["quote_data"], data["items_data"])
                self.load_data()
                QMessageBox.information(self, "Success", "Quotation updated successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update quotation: {str(e)}")

    def delete_quotation(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a quotation to delete.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_num = item.text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete quotation {quote_num}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                quotation_service.delete_quotation(quote_id)
                self.load_data()
                QMessageBox.information(self, "Deleted", f"Quotation {quote_num} deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete quotation: {str(e)}")

    def print_quotation(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a quotation to print.")
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
            filename = os.path.join(str(EXPORTS_DIR), f"quotation_{safe_num}.pdf")
            pdf_path = generator.generate_quotation(pdf_data, filename=filename)

            if os.name == 'nt':
                os.startfile(pdf_path)
            else:
                subprocess.call(('open', pdf_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate Quotation PDF: {str(e)}")

    def convert_to_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Please select a quotation to convert into an invoice.")
            return

        item = self.table.item(row, 0)
        if not item:
            return
        quote_id = item.data(Qt.UserRole)
        quote_num = item.text()

        reply = QMessageBox.question(
            self,
            "Convert to Tax Invoice",
            f"Convert quotation {quote_num} to a Tax Invoice?\n\nThis will generate an official invoice and deduct inventory stock.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                invoice = quotation_service.convert_to_invoice(quote_id)
                self.load_data()
                QMessageBox.information(
                    self,
                    "Quotation Converted",
                    f"Successfully generated Invoice #{invoice.invoice_number} from Quotation {quote_num}!"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to convert quotation: {str(e)}")
