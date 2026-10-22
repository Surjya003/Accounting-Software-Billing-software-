"""
Delivery Challan View — Create and manage delivery challans.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QMessageBox, QDateEdit, QTextEdit, QRadioButton, QButtonGroup,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.database.connection import get_session
from app.database.models import CompanyProfile
from app.services.billing.gst_engine import GSTEngine, TransactionType
from app.services.billing import challan_service, product_service
from app.services.party_service import get_all_parties
from app.ui.views.billing.invoice_view import InvoiceItemWidget


class ChallanFormDialog(QDialog):
    def __init__(self, ch_data=None, parent=None):
        super().__init__(parent)
        self.ch_data = ch_data
        self.setWindowTitle("Edit Challan" if ch_data else "New Delivery Challan")
        self.setMinimumSize(950, 650)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.company_state_code = "27"
        self._load_company_state()
        self.init_ui()
        if self.ch_data:
            self.populate(self.ch_data)
        else:
            self._update_totals()

    def _load_company_state(self):
        try:
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                if comp:
                    sc = comp.state_code or ""
                    if not sc and comp.gstin and len(comp.gstin) >= 2 and comp.gstin[:2].isdigit():
                        sc = comp.gstin[:2]
                    if sc:
                        self.company_state_code = sc
        except Exception:
            self.company_state_code = "27"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Edit Delivery Challan" if self.ch_data else "Create Delivery Challan")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")
        layout.addWidget(title)

        # Reference numbers: Challan No (manual), Date
        ref_frame = QFrame()
        ref_frame.setObjectName("Card")
        ref_layout = QHBoxLayout(ref_frame)

        ch_no_box = QVBoxLayout()
        ch_no_box.addWidget(QLabel("Challan Number (manual)"))
        self.txt_challan_number = QLineEdit()
        self.txt_challan_number.setPlaceholderText("Enter manually e.g. DC/001")
        ch_no_box.addWidget(self.txt_challan_number)
        ref_layout.addLayout(ch_no_box, 2)

        date_box = QVBoxLayout()
        date_box.addWidget(QLabel("Date *"))
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        date_box.addWidget(self.dt_date)
        ref_layout.addLayout(date_box, 1)

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
        ref_layout.addLayout(tax_box, 2)

        layout.addWidget(ref_frame)

        # Party selection
        form_frame = QFrame()
        form_frame.setObjectName("Card")
        form_layout = QHBoxLayout(form_frame)

        party_box = QVBoxLayout()
        party_box.addWidget(QLabel("Party *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Party --")
        self.cmb_party.addItem("", None)
        self.parties_map = {}
        for p in get_all_parties():
            self.parties_map[p["id"]] = p
            self.cmb_party.addItem(p["name"], p["id"])
        self.cmb_party.currentIndexChanged.connect(self._update_totals)
        party_box.addWidget(self.cmb_party)
        form_layout.addLayout(party_box, 2)

        # Status
        status_box = QVBoxLayout()
        status_box.addWidget(QLabel("Status"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["sent", "received", "returned", "converted"])
        status_box.addWidget(self.cmb_status)
        form_layout.addLayout(status_box, 1)

        layout.addWidget(form_frame)

        # Items header
        items_header = QHBoxLayout()
        lbl_items = QLabel("Line Items")
        lbl_items.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B1B18;")
        items_header.addWidget(lbl_items)
        items_header.addStretch()
        btn_add_item = QPushButton("+ Add Item")
        btn_add_item.setObjectName("PrimaryBtn")
        btn_add_item.clicked.connect(self.add_item)
        items_header.addWidget(btn_add_item)
        layout.addLayout(items_header)

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
        layout.addLayout(col_labels)

        # Items container inside scroll area
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
        layout.addWidget(scroll_area)

        self.add_item()

        # Totals container
        totals_frame = QFrame()
        totals_frame.setObjectName("Card")
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.addStretch()

        self.lbl_subtotal = QLabel("Subtotal: ₹0.00")
        self.lbl_cgst = QLabel("CGST: ₹0.00")
        self.lbl_sgst = QLabel("SGST: ₹0.00")
        self.lbl_igst = QLabel("IGST: ₹0.00")
        self.lbl_tax = QLabel("Tax: ₹0.00")
        self.lbl_grand = QLabel("Total: ₹0.00")
        self.lbl_grand.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas; padding: 4px 12px;")
        for lbl in [self.lbl_subtotal, self.lbl_cgst, self.lbl_sgst, self.lbl_igst, self.lbl_tax]:
            lbl.setStyleSheet("font-family: Consolas; font-size: 13px; padding: 4px 12px;")
            totals_layout.addWidget(lbl)
        totals_layout.addWidget(self.lbl_grand)

        layout.addWidget(totals_frame)
        
        # Connect tax mode changes to update totals
        self.tax_mode_group.buttonClicked.connect(self._update_totals)

        # Transport & Notes
        self.txt_transport = QLineEdit()
        self.txt_transport.setPlaceholderText("Transport details...")
        layout.addWidget(self.txt_transport)

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(50)
        self.txt_notes.setPlaceholderText("Notes...")
        layout.addWidget(self.txt_notes)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Challan")
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

    def add_item(self):
        w = InvoiceItemWidget(products_list=self.products)
        w.item_changed.connect(self._update_totals)
        w.remove_requested.connect(self._remove_item)
        self.item_widgets.append(w)
        insert_pos = self.items_layout.count() - 1
        self.items_layout.insertWidget(insert_pos, w)

    def _remove_item(self, w):
        if len(self.item_widgets) <= 1:
            return
        self.item_widgets.remove(w)
        self.items_layout.removeWidget(w)
        w.deleteLater()
        self._update_totals()

    def _update_totals(self):
        party_id = self.cmb_party.currentData()
        party = self.parties_map.get(party_id) if hasattr(self, 'parties_map') else None
        party_sc = ""
        if party:
            party_sc = party.get("state_code") or ""
            if not party_sc and party.get("gstin") and len(party.get("gstin")) >= 2 and party.get("gstin")[:2].isdigit():
                party_sc = party.get("gstin")[:2]

        tax_mode = self.tax_mode_group.checkedId()
        if tax_mode == 1:
            is_interstate = False
        elif tax_mode == 2:
            is_interstate = True
        else:
            # Auto mode
            comp_sc = getattr(self, "company_state_code", "27")
            if party_sc and comp_sc:
                is_interstate = (party_sc.strip() != comp_sc.strip())
            else:
                is_interstate = False

        t_type = TransactionType.INTER_STATE if is_interstate else TransactionType.INTRA_STATE

        subtotal = Decimal("0.00")
        cgst_total = Decimal("0.00")
        sgst_total = Decimal("0.00")
        igst_total = Decimal("0.00")

        for w in self.item_widgets:
            d = w.get_item_data()
            qty = Decimal(d.get("quantity", "1"))
            rate = Decimal(d.get("unit_price", "0"))
            disc = Decimal(d.get("discount_pct", "0"))
            gst_val = d.get("gst_rate_pct")
            if gst_val is None or str(gst_val).strip() == "":
                gst_val = d.get("tax_rate", "0")
            gst = Decimal(str(gst_val))

            res = GSTEngine.calculate_line_item(qty, rate, disc, gst, t_type)

            subtotal += res["taxable_value"]
            cgst_total += res["cgst_amt"]
            sgst_total += res["sgst_amt"]
            igst_total += res["igst_amt"]

        tax_total = cgst_total + sgst_total + igst_total
        grand_total = subtotal + tax_total

        self.lbl_subtotal.setText(f"Subtotal: ₹{float(subtotal):,.2f}")
        if is_interstate:
            self.lbl_igst.setVisible(True)
            self.lbl_cgst.setVisible(False)
            self.lbl_sgst.setVisible(False)
            self.lbl_igst.setText(f"IGST: ₹{float(igst_total):,.2f}")
        else:
            self.lbl_igst.setVisible(False)
            self.lbl_cgst.setVisible(True)
            self.lbl_sgst.setVisible(True)
            self.lbl_cgst.setText(f"CGST: ₹{float(cgst_total):,.2f}")
            self.lbl_sgst.setText(f"SGST: ₹{float(sgst_total):,.2f}")

        self.lbl_tax.setText(f"Tax: ₹{float(tax_total):,.2f}")
        self.lbl_grand.setText(f"Total: ₹{float(grand_total):,.2f}")

    def get_data(self):
        qd = self.dt_date.date()
        items = [w.get_item_data() for w in self.item_widgets]
        tax_mode = self.tax_mode_group.checkedId()
        return {
            "ch_data": {
                "party_id": self.cmb_party.currentData(),
                "challan_number": self.txt_challan_number.text().strip() or None,
                "challan_date": date(qd.year(), qd.month(), qd.day()),
                "status": self.cmb_status.currentText(),
                "tax_mode": tax_mode,
                "transport_details": self.txt_transport.text().strip(),
                "notes": self.txt_notes.toPlainText().strip()
            },
            "items_data": items,
        }

    def populate(self, data):
        # Challan number
        self.txt_challan_number.setText(data.get("challan_number", "") or "")
        
        # Date
        if data.get("challan_date"):
            d = data["challan_date"]
            if hasattr(d, 'year'):
                self.dt_date.setDate(QDate(d.year, d.month, d.day))

        # Party
        party_id = data.get("party_id")
        for i in range(self.cmb_party.count()):
            if self.cmb_party.itemData(i) == party_id:
                self.cmb_party.setCurrentIndex(i)
                break

        # Tax mode
        if "tax_mode" in data:
            tax_mode = data["tax_mode"]
        else:
            tax_mode = 2 if data.get("is_interstate") else 1

        if tax_mode == 1:
            self.rb_intra.setChecked(True)
        elif tax_mode == 2:
            self.rb_inter.setChecked(True)
        else:
            self.rb_auto.setChecked(True)

        # Status
        self.cmb_status.setCurrentText(data.get("status", "sent"))

        # Transport and notes
        self.txt_transport.setText(data.get("transport_details", "") or "")
        self.txt_notes.setPlainText(data.get("notes", "") or "")

        # Items
        items = data.get("items", [])
        if items:
            while len(self.item_widgets) > 1:
                self._remove_item(self.item_widgets[-1])
            self.item_widgets[0].populate_item(items[0])
            for it in items[1:]:
                self.add_item()
                self.item_widgets[-1].populate_item(it)
        self._update_totals()


class ChallanView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent); self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header = QHBoxLayout()
        tb = QVBoxLayout(); tb.setSpacing(4)
        lbl = QLabel("Delivery Challans"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        tb.addWidget(lbl)
        ls = QLabel("Create and track delivery challans"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")
        tb.addWidget(ls); header.addLayout(tb); header.addStretch()
        bn = QPushButton("+ New Challan"); bn.setObjectName("PrimaryBtn"); bn.setFixedHeight(36)
        bn.clicked.connect(self.create_challan); header.addWidget(bn)
        br = QPushButton("Refresh"); br.setFixedHeight(36); br.clicked.connect(self.load_data); header.addWidget(br)
        layout.addLayout(header)

        ff = QFrame(); ff.setObjectName("Card"); fl = QHBoxLayout(ff); fl.setContentsMargins(12, 8, 12, 8)
        self.inp_search = QLineEdit(); self.inp_search.setPlaceholderText("Search...")
        self.inp_search.textChanged.connect(self.load_data); fl.addWidget(self.inp_search, 2)
        layout.addWidget(ff)

        self.table = QTableWidget(); self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Challan #", "Date", "Party", "Tax (₹)", "Total (₹)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4, 5]: self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36); self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 challans")
        self.lbl_count.setStyleSheet("color: #6B6558;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("SecondaryBtn")
        btn_edit.clicked.connect(self.edit_challan)
        bottom.addWidget(btn_edit)

        btn_print = QPushButton("Print")
        btn_print.setObjectName("PrimaryBtn")
        btn_print.clicked.connect(self.print_challan)
        bottom.addWidget(btn_print)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DestructiveBtn")
        btn_del.clicked.connect(self.delete_challan)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)
        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        challans = challan_service.get_all_challans(search=search)
        self.table.setRowCount(len(challans)); mono = QFont("Consolas", 10)
        for row, ch in enumerate(challans):
            self.table.setItem(row, 0, QTableWidgetItem(ch["challan_number"]))
            d = ch.get("challan_date", ""); d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str); it_d.setFont(mono); self.table.setItem(row, 1, it_d)
            self.table.setItem(row, 2, QTableWidgetItem(ch.get("party_name", "")))
            for col, key in [(3, "tax_amount"), (4, "total_amount")]:
                it = QTableWidgetItem(f"₹{ch.get(key, 0):,.2f}"); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(mono); self.table.setItem(row, col, it)
            it_s = QTableWidgetItem(ch.get("status", "").upper()); self.table.setItem(row, 5, it_s)
            self.table.item(row, 0).setData(Qt.UserRole, ch["id"])
        self.lbl_count.setText(f"{len(challans)} challans")

    def create_challan(self):
        dlg = ChallanFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                challan_service.create_challan(data["ch_data"], data["items_data"])
                self.load_data(); QMessageBox.information(self, "Success", "Challan created!")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def delete_challan(self):
        row = self.table.currentRow()
        if row < 0: return
        ch_id = self.table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", "Delete this challan?") == QMessageBox.Yes:
            challan_service.delete_challan(ch_id); self.load_data()

    def edit_challan(self):
        row = self.table.currentRow()
        if row < 0: return
        ch_id = self.table.item(row, 0).data(Qt.UserRole)
        ch_data = challan_service.get_challan_by_id(ch_id)
        if not ch_data: return
        dlg = ChallanFormDialog(ch_data=ch_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                challan_service.update_challan(ch_id, data["ch_data"], data["items_data"])
                self.load_data()
                QMessageBox.information(self, "Success", "Challan updated!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def print_challan(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a challan to print.")
            return
        ch_id = self.table.item(row, 0).data(Qt.UserRole)
        ch_data = challan_service.get_challan_by_id(ch_id)
        if not ch_data: return

        try:
            from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            from app.config import EXPORTS_DIR
            import os
            import subprocess

            generator = ChallanPDFGenerator()

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
                    }

            is_interstate = ch_data.get('is_interstate', False)

            pdf_data = {
                'challan_number': ch_data['challan_number'],
                'date': ch_data['challan_date'].strftime('%d-%m-%Y') if hasattr(ch_data['challan_date'], 'strftime') else str(ch_data['challan_date']),
                'is_interstate': is_interstate,
                'company': company_info,
                'customer': {
                    'name': ch_data.get('party_name', ''),
                    'address': ch_data.get('party_address', ''),
                    'gstin': ch_data.get('party_gstin', ''),
                    'state': ch_data.get('party_state', ''),
                    'phone': ch_data.get('party_phone', ''),
                    'shipping_address': ch_data.get('party_address', ''),
                },
                'logistics': {
                    'dispatched_through': ch_data.get('transport_details', ''),
                    'vehicle_number': '',
                    'dispatch_doc_no': '',
                    'waybill_no': '',
                    'destination': '',
                },
                'transport_details': ch_data.get('transport_details', ''),
                'items': [],
                'totals': {
                    'taxable_amount': float(ch_data.get('subtotal', 0)),
                    'cgst_amount': float(ch_data.get('cgst_total', 0)),
                    'sgst_amount': float(ch_data.get('sgst_total', 0)),
                    'igst_amount': float(ch_data.get('igst_total', 0)),
                    'tax_amount': float(ch_data.get('tax_amount', 0)),
                    'grand_total': float(ch_data.get('total_amount', 0)),
                }
            }

            for item in ch_data.get('items', []):
                qty = float(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0))
                tax_rate = float(item.get('tax_rate', 0))
                cgst_amt = float(item.get('cgst_amount', 0))
                sgst_amt = float(item.get('sgst_amount', 0))
                igst_amt = float(item.get('igst_amount', 0))
                tax_amt = cgst_amt + sgst_amt + igst_amt

                pdf_data['items'].append({
                    'product_name': item.get('item_description', ''),
                    'description': '',
                    'hsn_code': item.get('hsn_code', ''),
                    'quantity': qty,
                    'unit': item.get('unit', 'PCS'),
                    'unit_price': unit_price,
                    'tax_rate': tax_rate,
                    'tax_amount': tax_amt,
                    'cgst_amount': cgst_amt,
                    'sgst_amount': sgst_amt,
                    'igst_amount': igst_amt,
                })

            filename = os.path.join(str(EXPORTS_DIR), f"challan_{ch_data.get('challan_number', 'DRAFT').replace('/', '-')}.pdf")
            pdf_path = generator.generate_challan(pdf_data, filename=filename)

            if os.name == 'nt':
                os.startfile(pdf_path)
            else:
                subprocess.call(('open', pdf_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF: {str(e)}")
