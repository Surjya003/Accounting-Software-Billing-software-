"""
Invoice Management View — Create, Edit, View GST Tax Invoices
Ported from Billing-software to PySide6 with Bahi-Khata theme.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit, QMessageBox,
    QDateEdit, QTabWidget, QRadioButton, QButtonGroup, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.billing import invoice_service, product_service
from app.services.party_service import get_all_parties


class InvoiceItemWidget(QFrame):
    """Single line item row for the invoice form."""
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
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product --")
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
        self.lbl_total.setStyleSheet("font-family: Consolas; font-weight: bold; font-size: 13px;")
        self.lbl_total.setMinimumWidth(100)
        self.lbl_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_total, 1)

        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(28, 28)
        btn_remove.setStyleSheet("color: #8B2635; font-weight: bold; border: 1px solid #8B2635; border-radius: 4px;")
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(btn_remove)

    def _on_product_selected(self, idx):
        data = self.cmb_product.itemData(idx)
        if data:
            self.spn_rate.setValue(data.get("price", 0))
            self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))
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

    def populate_item(self, item_data):
        """Populate this widget from saved item data dict."""
        # Set product combo
        product_id = item_data.get("product_id")
        if product_id:
            for i in range(self.cmb_product.count()):
                pd = self.cmb_product.itemData(i)
                if pd and pd.get("id") == product_id:
                    self.cmb_product.setCurrentIndex(i)
                    break
        self.spn_qty.setValue(float(item_data.get("quantity", 1)))
        self.spn_rate.setValue(float(item_data.get("unit_price", 0)))
        self.spn_disc.setValue(float(item_data.get("discount_pct", 0)))
        gst_val = item_data.get("gst_rate_pct")
        if gst_val is None or str(gst_val).strip() == "":
            gst_val = item_data.get("tax_rate", 18)
        gst = str(int(float(gst_val if gst_val is not None else 18)))
        self.cmb_gst.setCurrentText(gst)
        self._recalculate()


class InvoiceFormDialog(QDialog):
    """Create / Edit invoice dialog."""
    def __init__(self, invoice_data=None, parent=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.setWindowTitle("Edit Invoice" if invoice_data else "New Tax Invoice")
        self.setMinimumSize(1000, 750)
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
            # Auto-fill defaults for new invoice
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Edit Invoice" if self.invoice_data else "Create New Tax Invoice")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")
        layout.addWidget(title)

        # Reference Numbers: Invoice No, PO No, PI No
        ref_frame = QFrame()
        ref_frame.setObjectName("Card")
        ref_layout = QHBoxLayout(ref_frame)

        inv_no_box = QVBoxLayout()
        inv_no_box.addWidget(QLabel("Invoice Number (auto if blank)"))
        self.txt_invoice_number = QLineEdit()
        self.txt_invoice_number.setPlaceholderText("Auto-generated e.g. INV/24-25/0001")
        inv_no_box.addWidget(self.txt_invoice_number)
        ref_layout.addLayout(inv_no_box, 2)

        po_box = QVBoxLayout()
        po_box.addWidget(QLabel("PO Number"))
        self.txt_po_number = QLineEdit()
        self.txt_po_number.setPlaceholderText("Purchase Order No.")
        po_box.addWidget(self.txt_po_number)
        ref_layout.addLayout(po_box, 1)

        pi_box = QVBoxLayout()
        pi_box.addWidget(QLabel("PI Number"))
        self.txt_pi_number = QLineEdit()
        self.txt_pi_number.setPlaceholderText("Proforma Invoice No.")
        pi_box.addWidget(self.txt_pi_number)
        ref_layout.addLayout(pi_box, 1)

        layout.addWidget(ref_frame)

        # Top form: Party, Date, Status
        form_frame = QFrame()
        form_frame.setObjectName("Card")
        form_layout = QHBoxLayout(form_frame)

        party_box = QVBoxLayout()
        party_box.addWidget(QLabel("Party *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Party --")
        self.cmb_party.addItem("", None)
        parties = get_all_parties()
        for p in parties:
            self.cmb_party.addItem(p["name"], p["id"])
        party_box.addWidget(self.cmb_party)
        form_layout.addLayout(party_box, 2)

        date_box = QVBoxLayout()
        date_box.addWidget(QLabel("Invoice Date *"))
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_date)
        form_layout.addLayout(date_box, 1)

        status_box = QVBoxLayout()
        status_box.addWidget(QLabel("Status"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["draft", "final", "cancelled"])
        status_box.addWidget(self.cmb_status)
        form_layout.addLayout(status_box, 1)

        # Tax Mode
        tax_box = QVBoxLayout()
        tax_box.addWidget(QLabel("Tax Mode"))
        
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
        form_layout.addLayout(tax_box, 2)

        layout.addWidget(form_frame)

        # Tabs Container
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # === TAB 1: LINE ITEMS ===
        tab_items = QWidget()
        tab_items_layout = QVBoxLayout(tab_items)
        
        # Items header
        items_header = QHBoxLayout()
        lbl_items = QLabel("Line Items")
        lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")
        items_header.addWidget(lbl_items)
        items_header.addStretch()
        btn_add_item = QPushButton("+ Add Item")
        btn_add_item.setObjectName("PrimaryBtn")
        btn_add_item.clicked.connect(self.add_item_row)
        items_header.addWidget(btn_add_item)
        tab_items_layout.addLayout(items_header)

        # Column labels
        col_labels = QHBoxLayout()
        col_labels.setContentsMargins(8, 0, 8, 0)
        for label, stretch in [("Product", 3), ("Qty", 1), ("Rate (₹)", 1), ("Disc %", 1), ("GST %", 1), ("Total", 1), ("", 0)]:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6B6558; text-transform: uppercase;")
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
        self.items_layout.addStretch()  # Push items to top

        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(items_scroll)
        scroll_area.setMinimumHeight(150)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        tab_items_layout.addWidget(scroll_area)

        # Add first item row
        self.add_item_row()

        # Totals
        totals_frame = QFrame()
        totals_frame.setObjectName("Card")
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.addStretch()

        self.lbl_subtotal = QLabel("Subtotal: ₹0.00")
        self.lbl_tax = QLabel("Tax: ₹0.00")
        self.lbl_grand = QLabel("Total: ₹0.00")
        self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63;")
        for lbl in [self.lbl_subtotal, self.lbl_tax, self.lbl_grand]:
            lbl.setStyleSheet(lbl.styleSheet() + "font-family: Consolas; padding: 4px 12px;")
            totals_layout.addWidget(lbl)

        tab_items_layout.addWidget(totals_frame)
        self.tabs.addTab(tab_items, "Items & Totals")

        # === TAB 2: LOGISTICS ===
        tab_log = QWidget()
        tab_log_layout = QFormLayout(tab_log)
        
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
        tab_log_layout.addRow("LR No", self.txt_lr_no)
        
        self.dt_lr_date = QDateEdit(QDate.currentDate())
        self.dt_lr_date.setCalendarPopup(True)
        tab_log_layout.addRow("LR Date", self.dt_lr_date)
        
        self.txt_eway_bill = QLineEdit()
        tab_log_layout.addRow("E-Way Bill No", self.txt_eway_bill)
        
        self.txt_destination = QLineEdit()
        tab_log_layout.addRow("Destination", self.txt_destination)
        
        self.tabs.addTab(tab_log, "Shipping & Logistics")

        # === TAB 3: TERMS & BANK ===
        tab_terms = QWidget()
        tab_terms_layout = QFormLayout(tab_terms)
        
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
        btn_save = QPushButton("Save Invoice")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
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
        # Insert before the stretch spacer (last item in layout)
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
            discount = base * disc / Decimal("100")
            taxable = base - discount
            t = taxable * gst / Decimal("100")
            subtotal += taxable
            tax += t
        total = subtotal + tax
        self.lbl_subtotal.setText(f"Subtotal: ₹{float(subtotal):,.2f}")
        self.lbl_tax.setText(f"Tax: ₹{float(tax):,.2f}")
        self.lbl_grand.setText(f"Total: ₹{float(total):,.2f}")

    def populate(self, data):
        # Set party
        for i in range(self.cmb_party.count()):
            if self.cmb_party.itemData(i) == data.get("party_id"):
                self.cmb_party.setCurrentIndex(i)
                break
        # Date
        if data.get("invoice_date"):
            d = data["invoice_date"]
            if hasattr(d, 'year'):
                self.dt_date.setDate(QDate(d.year, d.month, d.day))
        self.cmb_status.setCurrentText(data.get("status", "draft"))
        
        tax_mode = data.get("tax_mode", 0)
        if tax_mode == 1:
            self.rb_intra.setChecked(True)
        elif tax_mode == 2:
            self.rb_inter.setChecked(True)
        else:
            self.rb_auto.setChecked(True)

        # Reference numbers
        self.txt_invoice_number.setText(data.get("invoice_number", "") or "")
        self.txt_po_number.setText(data.get("po_number", "") or "")
        self.txt_pi_number.setText(data.get("pi_number", "") or "")
            
        self.txt_notes.setPlainText(data.get("notes", "") or "")
        
        self.txt_shipping_address.setPlainText(data.get("shipping_address", "") or "")
        self.txt_transporter.setText(data.get("transporter_name", "") or "")
        self.txt_vehicle_no.setText(data.get("vehicle_no", "") or "")
        self.txt_lr_no.setText(data.get("lr_no", "") or "")
        if data.get("lr_date"):
            ld = data["lr_date"]
            if hasattr(ld, 'year'):
                self.dt_lr_date.setDate(QDate(ld.year, ld.month, ld.day))
        self.txt_eway_bill.setText(data.get("eway_bill_no", "") or "")
        self.txt_destination.setText(data.get("destination", "") or "")
        
        self.txt_terms.setPlainText(data.get("terms_and_conditions", "") or "")
        self.txt_bank_name.setText(data.get("bank_name", "") or "")
        self.txt_bank_ac.setText(data.get("bank_ac_no", "") or "")
        self.txt_bank_ifsc.setText(data.get("bank_ifsc", "") or "")

    def get_data(self):
        party_id = self.cmb_party.currentData()
        qd = self.dt_date.date()
        items = [w.get_item_data() for w in self.item_widgets]
        inv_num = self.txt_invoice_number.text().strip() or None
        return {
            "invoice_data": {
                "party_id": party_id,
                "invoice_number": inv_num,
                "invoice_date": date(qd.year(), qd.month(), qd.day()),
                "status": self.cmb_status.currentText(),
                "tax_mode": self.tax_mode_group.checkedId(),
                "notes": self.txt_notes.toPlainText(),
                "po_number": self.txt_po_number.text().strip(),
                "pi_number": self.txt_pi_number.text().strip(),
                "shipping_address": self.txt_shipping_address.toPlainText(),
                "transporter_name": self.txt_transporter.text(),
                "vehicle_no": self.txt_vehicle_no.text(),
                "lr_no": self.txt_lr_no.text(),
                "lr_date": date(self.dt_lr_date.date().year(), self.dt_lr_date.date().month(), self.dt_lr_date.date().day()),
                "eway_bill_no": self.txt_eway_bill.text(),
                "destination": self.txt_destination.text(),
                "terms_and_conditions": self.txt_terms.toPlainText(),
                "bank_name": self.txt_bank_name.text(),
                "bank_ac_no": self.txt_bank_ac.text(),
                "bank_ifsc": self.txt_bank_ifsc.text()
            },
            "items_data": items,
        }


class InvoiceView(QWidget):
    """Invoice list and management page."""
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl = QLabel("Tax Invoices")
        lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl)
        lbl_sub = QLabel("Create and manage GST tax invoices for customers")
        lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_new = QPushButton("+ New Invoice")
        btn_new.setObjectName("PrimaryBtn")
        btn_new.setFixedHeight(36)
        btn_new.clicked.connect(self.create_invoice)
        header.addWidget(btn_new)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_invoices)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setObjectName("Card")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search by invoice number or party name...")
        self.inp_search.textChanged.connect(self.load_invoices)
        fl.addWidget(self.inp_search, 2)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["All", "draft", "final", "cancelled"])
        self.cmb_status.currentTextChanged.connect(self.load_invoices)
        fl.addWidget(self.cmb_status)

        layout.addWidget(filter_frame)

        # Invoice table
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
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_invoice)
        layout.addWidget(self.table, 1)

        # Bottom bar
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 invoices")
        self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("SecondaryBtn")
        btn_edit.clicked.connect(self.edit_invoice)
        bottom.addWidget(btn_edit)

        btn_print = QPushButton("Print Selected")
        btn_print.clicked.connect(self.print_invoice)
        bottom.addWidget(btn_print)
        
        btn_del = QPushButton("Delete Selected")
        btn_del.setObjectName("DestructiveBtn")
        btn_del.clicked.connect(self.delete_invoice)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

        self.load_invoices()

    def load_invoices(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        status = self.cmb_status.currentText() if hasattr(self, 'cmb_status') else None

        invoices = invoice_service.get_all_invoices(search=search, status=status)
        self.table.setRowCount(len(invoices))
        mono = QFont("Consolas", 10)

        for row, inv in enumerate(invoices):
            self.table.setItem(row, 0, QTableWidgetItem(inv["invoice_number"]))

            d = inv.get("invoice_date", "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_date = QTableWidgetItem(d_str)
            it_date.setFont(mono)
            self.table.setItem(row, 1, it_date)

            self.table.setItem(row, 2, QTableWidgetItem(inv.get("party_name", "")))

            # PO Number
            self.table.setItem(row, 3, QTableWidgetItem(inv.get("po_number", "") or ""))
            # PI Number
            self.table.setItem(row, 4, QTableWidgetItem(inv.get("pi_number", "") or ""))

            for col, key in [(5, "subtotal"), (6, "tax_amount"), (7, "total_amount")]:
                it = QTableWidgetItem(f"₹{inv.get(key, 0):,.2f}")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(mono)
                self.table.setItem(row, col, it)

            status = inv.get("status", "draft")
            it_st = QTableWidgetItem(status.upper())
            color_map = {"draft": "#A6822E", "final": "#2F6844", "cancelled": "#8B2635"}
            it_st.setForeground(QColor(color_map.get(status, "#1B1B18")))
            self.table.setItem(row, 6, it_st)

            self.table.item(row, 0).setData(Qt.UserRole, inv["id"])

        self.lbl_count.setText(f"{len(invoices)} invoices")

    def create_invoice(self):
        dlg = InvoiceFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                invoice_service.create_invoice(data["invoice_data"], data["items_data"])
                self.load_invoices()
                QMessageBox.information(self, "Success", "Invoice created successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_invoice(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0: return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_data = invoice_service.get_invoice_by_id(inv_id)
        if not inv_data: return
        dlg = InvoiceFormDialog(invoice_data=inv_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                invoice_service.update_invoice(inv_id, data["invoice_data"], data["items_data"])
                self.load_invoices()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select an invoice to delete.")
            return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_num = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete invoice {inv_num}?")
        if reply == QMessageBox.Yes:
            invoice_service.delete_invoice(inv_id)
            self.load_invoices()

    def print_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select an invoice to print.")
            return
        inv_id = self.table.item(row, 0).data(Qt.UserRole)
        inv_data = invoice_service.get_invoice_by_id(inv_id)
        if not inv_data: return
        
        try:
            from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            import os
            import subprocess
            
            generator = InvoicePDFGenerator()
            
            # Load company profile from database
            company_info = {}
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                if comp:
                    company_info = {
                        'name': comp.name or '',
                        'address': comp.address or '',
                        'gstin': comp.gstin or '',
                        'state': comp.state or '',
                        'phone': comp.phone or '',
                        'email': comp.email or '',
                        'bank_name': comp.bank_name or '',
                        'account_no': comp.bank_account_no or '',
                        'ifsc': comp.bank_ifsc or '',
                    }
            
            # Determine tax mode
            is_interstate = inv_data.get('is_interstate', False)
            tax_mode_str = 'inter_state' if is_interstate else 'intra_state'
            
            # Map data to generator format
            pdf_data = {
                'invoice_number': inv_data['invoice_number'],
                'date': inv_data['invoice_date'].strftime('%d-%m-%Y') if hasattr(inv_data['invoice_date'], 'strftime') else str(inv_data['invoice_date']),
                'tax_mode': tax_mode_str,
                'po_number': inv_data.get('po_number', ''),
                'pi_number': inv_data.get('pi_number', ''),
                'company': company_info,
                'customer': {
                    'name': inv_data.get('party_name', ''),
                    'address': inv_data.get('party_address', ''),
                    'gstin': inv_data.get('party_gstin', ''),
                    'state': inv_data.get('party_state', ''),
                    'phone': inv_data.get('party_phone', '')
                },
                'logistics': {
                    'dispatch_doc_no': inv_data.get('lr_no', ''),
                    'waybill_no': inv_data.get('eway_bill_no', ''),
                    'dispatched_through': inv_data.get('transporter_name', ''),
                    'destination': inv_data.get('destination', ''),
                    'payment_terms': '',
                    'po_date': '',
                    'buyer_order_no': inv_data.get('po_number', ''),
                    'terms_delivery': ''
                },
                'consignee': {
                    'address': inv_data.get('shipping_address', '')
                },
                'items': [],
                'totals': {
                    'taxable_amount': float(inv_data.get('subtotal', 0)),
                    'cgst_amount': float(inv_data.get('cgst_total', 0)),
                    'sgst_amount': float(inv_data.get('sgst_total', 0)),
                    'igst_amount': float(inv_data.get('igst_total', 0)),
                    'grand_total': float(inv_data.get('total_amount', 0)),
                }
            }
            
            for item in inv_data.get('items', []):
                qty = float(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0))
                gst_rate = float(item.get('gst_rate_pct', 0))
                taxable_value = float(item.get('taxable_value', 0))
                
                # Calculate tax amount for this item
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
                
            pdf_path = generator.generate_invoice(pdf_data)
            
            if os.name == 'nt':
                os.startfile(pdf_path)
            else:
                subprocess.call(('open', pdf_path))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF: {str(e)}")

