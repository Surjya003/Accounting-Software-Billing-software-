"""
Proforma Invoice View — Create, Edit, View Proforma Invoices (Quotations).
Same structure and features as Invoice View.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QTextEdit, QMessageBox,
    QDateEdit, QTabWidget, QRadioButton, QButtonGroup, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.billing import proforma_service, product_service, invoice_service
from app.services.party_service import get_all_parties
from app.ui.views.billing.invoice_view import InvoiceItemWidget
from app.database.models import Product
from decimal import Decimal


class ProformaFormDialog(QDialog):
    """Create / Edit proforma invoice dialog — mirrors InvoiceFormDialog."""
    def __init__(self, pf_data=None, parent=None):
        super().__init__(parent)
        self.pf_data = pf_data
        self.setWindowTitle("Edit Proforma" if pf_data else "New Proforma Invoice")
        self.setMinimumSize(1000, 750)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()
        if self.pf_data:
            self.populate(self.pf_data)
            items = self.pf_data.get("items", [])
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Edit Proforma" if self.pf_data else "Create Proforma Invoice")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")
        layout.addWidget(title)

        # Reference Numbers: Proforma No, PO No, PI No
        ref_frame = QFrame()
        ref_frame.setObjectName("Card")
        ref_layout = QHBoxLayout(ref_frame)

        pf_no_box = QVBoxLayout()
        pf_no_box.addWidget(QLabel("Proforma Number (auto if blank)"))
        self.txt_proforma_number = QLineEdit()
        self.txt_proforma_number.setPlaceholderText("Auto-generated e.g. PF/24-25/0001")
        pf_no_box.addWidget(self.txt_proforma_number)
        ref_layout.addLayout(pf_no_box, 2)

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
        date_box.addWidget(QLabel("Proforma Date *"))
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_date)
        form_layout.addLayout(date_box, 1)

        status_box = QVBoxLayout()
        status_box.addWidget(QLabel("Status"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["draft", "sent", "converted", "expired"])
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
        self.items_layout.addStretch()

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
        btn_save = QPushButton("Save Proforma")
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
        if data.get("proforma_date"):
            d = data["proforma_date"]
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
        self.txt_proforma_number.setText(data.get("proforma_number", "") or "")
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
        pf_num = self.txt_proforma_number.text().strip() or None
        return {
            "pf_data": {
                "party_id": party_id,
                "proforma_number": pf_num,
                "proforma_date": date(qd.year(), qd.month(), qd.day()),
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


class ProformaView(QWidget):
    """Proforma invoice list and management page."""
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
        lbl = QLabel("Proforma Invoices")
        lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl)
        lbl_sub = QLabel("Create and manage quotations / proforma invoices")
        lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_new = QPushButton("+ New Proforma")
        btn_new.setObjectName("PrimaryBtn")
        btn_new.setFixedHeight(36)
        btn_new.clicked.connect(self.create_proforma)
        header.addWidget(btn_new)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setObjectName("Card")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search proformas...")
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
        self.lbl_count.setStyleSheet("color: #6B6558;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_convert = QPushButton("Convert to Invoice")
        btn_convert.setObjectName("PrimaryBtn")
        btn_convert.clicked.connect(self.convert_to_invoice)
        bottom.addWidget(btn_convert)

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("SecondaryBtn")
        btn_edit.clicked.connect(lambda: self.edit_proforma())
        bottom.addWidget(btn_edit)

        btn_print = QPushButton("Print PDF")
        btn_print.setObjectName("PrimaryBtn")
        btn_print.clicked.connect(self.print_proforma)
        bottom.addWidget(btn_print)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DestructiveBtn")
        btn_del.clicked.connect(self.delete_pf)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        pfs = proforma_service.get_all_proformas(search=search)
        self.table.setRowCount(len(pfs))
        mono = QFont("Consolas", 10)

        for row, pf in enumerate(pfs):
            self.table.setItem(row, 0, QTableWidgetItem(pf["proforma_number"]))

            d = pf.get("proforma_date", "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str)
            it_d.setFont(mono)
            self.table.setItem(row, 1, it_d)

            self.table.setItem(row, 2, QTableWidgetItem(pf.get("party_name", "")))

            # PO Number
            self.table.setItem(row, 3, QTableWidgetItem(pf.get("po_number", "") or ""))
            # PI Number
            self.table.setItem(row, 4, QTableWidgetItem(pf.get("pi_number", "") or ""))

            for col, key in [(5, "tax_amount"), (6, "total_amount")]:
                it = QTableWidgetItem(f"₹{pf.get(key, 0):,.2f}")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(mono)
                self.table.setItem(row, col, it)

            status = pf.get("status", "draft")
            it_s = QTableWidgetItem(status.upper())
            color_map = {"draft": "#A6822E", "sent": "#2C3E63", "converted": "#2F6844", "expired": "#8B2635"}
            it_s.setForeground(QColor(color_map.get(status, "#1B1B18")))
            self.table.setItem(row, 5, it_s)

            self.table.item(row, 0).setData(Qt.UserRole, pf["id"])
        self.lbl_count.setText(f"{len(pfs)} proformas")

    def create_proforma(self):
        dlg = ProformaFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                proforma_service.create_proforma(data["pf_data"], data["items_data"])
                self.load_data()
                QMessageBox.information(self, "Success", "Proforma created successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_proforma(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0: return
        pf_id = self.table.item(row, 0).data(Qt.UserRole)
        pf_data = proforma_service.get_proforma_by_id(pf_id)
        if not pf_data: return
        dlg = ProformaFormDialog(pf_data=pf_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                proforma_service.update_proforma(pf_id, data["pf_data"], data["items_data"])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_pf(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a proforma to delete.")
            return
        pf_id = self.table.item(row, 0).data(Qt.UserRole)
        pf_num = self.table.item(row, 0).text()
        if QMessageBox.question(self, "Confirm Delete", f"Delete proforma {pf_num}?") == QMessageBox.Yes:
            proforma_service.delete_proforma(pf_id)
            self.load_data()

    def print_proforma(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a proforma to print.")
            return
        pf_id = self.table.item(row, 0).data(Qt.UserRole)
        pf_data = proforma_service.get_proforma_by_id(pf_id)
        if not pf_data: return

        try:
            from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            from app.config import EXPORTS_DIR
            import os
            import subprocess

            generator = InvoicePDFGenerator()

            # Load company profile
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

            is_interstate = pf_data.get('is_interstate', False)
            tax_mode_str = 'inter_state' if is_interstate else 'intra_state'

            pdf_data = {
                'invoice_number': pf_data['proforma_number'],
                'date': pf_data['proforma_date'].strftime('%d-%m-%Y') if hasattr(pf_data['proforma_date'], 'strftime') else str(pf_data['proforma_date']),
                'tax_mode': tax_mode_str,
                'po_number': pf_data.get('po_number', ''),
                'pi_number': pf_data.get('pi_number', ''),
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
                    'payment_terms': '',
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
                    'cgst_amount': float(pf_data.get('cgst_total', 0)),
                    'sgst_amount': float(pf_data.get('sgst_total', 0)),
                    'igst_amount': float(pf_data.get('igst_total', 0)),
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

            filename = os.path.join(str(EXPORTS_DIR), f"proforma_{pf_data.get('proforma_number', 'DRAFT').replace('/', '-')}.pdf")
            pdf_path = generator.generate_invoice(pdf_data, filename=filename)

            if os.name == 'nt':
                os.startfile(pdf_path)
            else:
                subprocess.call(('open', pdf_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF: {str(e)}")

    def convert_to_invoice(self):
        """Convert selected proforma to a tax invoice with stock deduction."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a proforma to convert.")
            return
        pf_id = self.table.item(row, 0).data(Qt.UserRole)
        pf_data = proforma_service.get_proforma_by_id(pf_id)
        if not pf_data:
            return

        # Confirm conversion
        reply = QMessageBox.question(
            self, "Convert to Invoice",
            f"Convert proforma {pf_data.get('proforma_number')} to a Tax Invoice?\n"
            "This will create a new invoice and update stock quantities.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            # Use proforma_service to convert (handles stock deduction)
            invoice = proforma_service.convert_to_invoice(pf_id)
            if invoice:
                # Update proforma status to 'converted'
                proforma_service.update_proforma(pf_id, {"status": "converted"}, None)
                self.load_data()
                QMessageBox.information(self, "Success", f"Invoice {invoice.invoice_number} created successfully!")
            else:
                QMessageBox.warning(self, "Error", "Conversion failed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
