"""
Purchase Order View — Create and manage purchase orders to suppliers.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QDateEdit, QTextEdit, QDoubleSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from app.services.billing import purchase_order_service, product_service
from app.services.party_service import get_all_parties
from app.ui.views.billing.invoice_view import InvoiceItemWidget
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, StatusBadgeLabel, ThemedMessageBox,
    configure_dialog_window_flags
)
from app.ui.save_dialog import execute_export_pipeline


class POFormDialog(QDialog):
    def __init__(self, po_data=None, parent=None):
        super().__init__(parent)
        self.po_data = po_data
        self.setWindowTitle("Edit PO" if po_data else "New Purchase Order")
        configure_dialog_window_flags(self, min_width=920, min_height=600)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()
        if po_data:
            self.populate(po_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Edit PO" if self.po_data else "Create Purchase Order")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        form_frame = CardFrame()
        fl = QHBoxLayout(form_frame)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(12)

        pb = QVBoxLayout()
        pb.addWidget(QLabel("Supplier *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Supplier --")
        self.cmb_party.addItem("", None)
        parties = get_all_parties()
        suppliers = [p for p in parties if p.get("party_type") in ("Supplier", "Both")]
        if not suppliers:
            suppliers = parties
        for p in suppliers:
            self.cmb_party.addItem(p["name"], p["id"])
        pb.addWidget(self.cmb_party)
        fl.addLayout(pb, 2)

        db = QVBoxLayout()
        db.addWidget(QLabel("PO Date *"))
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        db.addWidget(self.dt_date)
        fl.addLayout(db, 1)

        layout.addWidget(form_frame)

        ih = QHBoxLayout()
        lbl_items = QLabel("Items")
        lbl_items.setFont(theme_manager.get_font("subtitle", bold=True))
        ih.addWidget(lbl_items)
        ih.addStretch()

        btn_add = QPushButton(" Add Item")
        btn_add.setIcon(theme_manager.get_icon("plus", size=16))
        btn_add.setProperty("variant", "secondary")
        btn_add.setFixedHeight(34)
        btn_add.clicked.connect(self.add_item)
        ih.addWidget(btn_add)
        layout.addLayout(ih)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_w = QWidget()
        self.items_layout = QVBoxLayout(scroll_w)
        self.items_layout.setSpacing(6)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.addStretch()
        scroll.setWidget(scroll_w)
        layout.addWidget(scroll, 1)

        self.add_item()

        self.lbl_total = QLabel("Total: ₹0.00")
        self.lbl_total.setFont(theme_manager.get_font("subtitle", bold=True))
        self.lbl_total.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_total)

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(50)
        self.txt_notes.setPlaceholderText("Notes...")
        layout.addWidget(self.txt_notes)

        bl = QHBoxLayout()
        bl.addStretch()

        bc = QPushButton("Cancel")
        bc.setProperty("variant", "secondary")
        bc.setFixedHeight(36)
        bc.clicked.connect(self.reject)
        bl.addWidget(bc)

        bs = QPushButton("Save PO")
        bs.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        bs.setProperty("variant", "primary")
        bs.setFixedHeight(36)
        bs.clicked.connect(self.accept)
        bl.addWidget(bs)

        layout.addLayout(bl)

    def add_item(self):
        w = InvoiceItemWidget(products_list=self.products)
        w.item_changed.connect(self._update_total)
        w.remove_requested.connect(self._remove_item)
        self.item_widgets.append(w)
        insert_pos = max(0, self.items_layout.count() - 1)
        self.items_layout.insertWidget(insert_pos, w)

    def _remove_item(self, w):
        if len(self.item_widgets) <= 1:
            return
        self.item_widgets.remove(w)
        self.items_layout.removeWidget(w)
        w.deleteLater()
        self._update_total()

    def _update_total(self):
        total = Decimal("0")
        for w in self.item_widgets:
            d = w.get_item_data()
            qty = Decimal(d["quantity"])
            rate = Decimal(d["unit_price"])
            gst = Decimal(d["gst_rate_pct"] or "0")
            taxable = qty * rate
            total += taxable + taxable * gst / Decimal("100")
        self.lbl_total.setText(f"Total: ₹{float(total):,.2f}")

    def populate(self, data):
        for i in range(self.cmb_party.count()):
            if self.cmb_party.itemData(i) == data.get("party_id"):
                self.cmb_party.setCurrentIndex(i)
                break

    def get_data(self):
        qd = self.dt_date.date()
        items = []
        for w in self.item_widgets:
            d = w.get_item_data()
            items.append({
                "product_id": d["product_id"],
                "item_description": d["item_description"],
                "hsn_code": d["hsn_code"],
                "quantity": d["quantity"],
                "unit": d["unit"],
                "unit_price": d["unit_price"],
                "tax_rate": d["gst_rate_pct"]
            })
        return {
            "po_data": {
                "party_id": self.cmb_party.currentData(),
                "po_date": date(qd.year(), qd.month(), qd.day()),
                "notes": self.txt_notes.toPlainText().strip()
            },
            "items_data": items,
        }


class PurchaseOrderView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.header_widget = PageHeaderWidget(
            title="Purchase Orders",
            subtitle="Create and track purchase orders to suppliers",
            action_text="New PO",
            action_icon="plus",
            action_callback=self.create_po
        )
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        self.header_widget.add_custom_action(btn_refresh)
        layout.addWidget(self.header_widget)

        ff = CardFrame()
        fl = QHBoxLayout(ff)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(12)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search orders...")
        self.inp_search.textChanged.connect(self.load_data)
        fl.addWidget(self.inp_search, 2)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["All", "draft", "sent", "received", "cancelled"])
        self.cmb_status.currentTextChanged.connect(self.load_data)
        fl.addWidget(self.cmb_status)
        layout.addWidget(ff)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["PO #", "Date", "Supplier", "Tax (₹)", "Total (₹)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4, 5]:
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 orders")
        self.lbl_count.setFont(theme_manager.get_font("caption"))
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        self.btn_print = QPushButton("Print PO")
        self.btn_print.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_print.setProperty("variant", "secondary")
        self.btn_print.clicked.connect(self.print_po)
        bottom.addWidget(self.btn_print)

        btn_recv = QPushButton("Mark as Received")
        btn_recv.setIcon(theme_manager.get_icon("check", token_color="success", size=16))
        btn_recv.setProperty("variant", "secondary")
        btn_recv.clicked.connect(self.mark_received)
        bottom.addWidget(btn_recv)

        btn_return = QPushButton("Return Goods")
        btn_return.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_return.setProperty("variant", "secondary")
        btn_return.clicked.connect(self.return_goods)
        bottom.addWidget(btn_return)

        bd = QPushButton("Delete")
        bd.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        bd.setProperty("variant", "danger")
        bd.clicked.connect(self.delete_po)
        bottom.addWidget(bd)
        layout.addLayout(bottom)

        self.load_data()


    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        status = self.cmb_status.currentText() if hasattr(self, 'cmb_status') else None
        pos = purchase_order_service.get_all_purchase_orders(search=search, status=status)
        self.table.setRowCount(len(pos))

        for row, po in enumerate(pos):
            self.table.setItem(row, 0, QTableWidgetItem(po["po_number"]))
            d = po.get("po_date", "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str)
            self.table.setItem(row, 1, it_d)

            self.table.setItem(row, 2, QTableWidgetItem(po.get("party_name", "")))

            for col, key in [(3, "tax_amount"), (4, "total_amount")]:
                it = QTableWidgetItem(f"₹{po.get(key, 0):,.2f}")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, it)

            st = po.get("status", "draft")
            badge = StatusBadgeLabel(st.upper(), status=st)
            self.table.setCellWidget(row, 5, badge)

            self.table.item(row, 0).setData(Qt.UserRole, po["id"])

        self.lbl_count.setText(f"{len(pos)} orders")

    def create_po(self):
        dlg = POFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                purchase_order_service.create_purchase_order(data["po_data"], data["items_data"])
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Purchase Order created!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def mark_received(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select a PO.")
            return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        try:
            purchase_order_service.mark_as_received(po_id)
            self.load_data()
            ThemedMessageBox.information(self, "Success", "PO marked as received. Stock updated!")
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", str(e))

    def delete_po(self):
        row = self.table.currentRow()
        if row < 0:
            return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        if ThemedMessageBox.question(self, "Delete", "Delete this PO?"):
            purchase_order_service.delete_purchase_order(po_id)
            self.load_data()

    def print_po(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Please select a Purchase Order to print.")
            return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        po = purchase_order_service.get_purchase_order_by_id(po_id)
        if not po:
            ThemedMessageBox.warning(self, "Warning", "Could not find Purchase Order details.")
            return
        try:
            from app.services.billing.purchase_order_pdf_generator import PurchaseOrderPDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                comp_data = comp.to_dict() if comp else {}

            generator = PurchaseOrderPDFGenerator()
            po_data = {
                "po_number": po["po_number"],
                "po_date": po.get("po_date", ""),
                "company": comp_data,
                "supplier": {
                    "name": po.get("party_name", ""),
                    "address": po.get("party_address", ""),
                    "gstin": po.get("party_gstin", ""),
                    "phone": po.get("party_phone", ""),
                },
                "items": [
                    {
                        "item_description": it.get("item_description") or "Item",
                        "hsn_code": it.get("hsn_code", "-"),
                        "quantity": float(it.get("quantity", 1)),
                        "unit": it.get("unit", "PCS"),
                        "unit_price": float(it.get("unit_price", 0)),
                        "tax_rate": float(it.get("tax_rate", 0)),
                        "total_item_amount": float(it.get("total_amount", 0)),
                    }
                    for it in po.get("items", [])
                ],
                "totals": {
                    "taxable_amount": float(po.get("subtotal", 0)),
                    "tax_amount": float(po.get("tax_amount", 0)),
                    "grand_total": float(po.get("total_amount", 0)),
                }
            }
            safe_num = po.get("po_number", "PO").replace('/', '-')
            s_name = po.get("supplier_name", "Supplier")
            suggested = f"PO_{safe_num}_{s_name}"

            def _generate(out_p):
                return generator.generate_po(po_data, filename=str(out_p))

            execute_export_pipeline(
                parent=self,
                suggested_name=suggested,
                kind="pdf",
                generator_fn=_generate,
                trigger_button=getattr(self, "btn_print", None)
            )
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Failed to generate Purchase Order PDF: {e}")

    def return_goods(self):
        row = self.table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "Info", "Select a purchase order to return goods.")
            return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        po_data = purchase_order_service.get_purchase_order_by_id(po_id)
        if not po_data:
            return
        if po_data["status"] not in ("received", "partially_received"):
            ThemedMessageBox.warning(self, "Notice", "Goods can only be returned for received or partially received purchase orders.")
            return
        self.navigate_to.emit("returns", {"po_id": po_id, "party_id": po_data["party_id"]})

