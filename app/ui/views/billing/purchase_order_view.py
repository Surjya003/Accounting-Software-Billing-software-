"""
Purchase Order View — Create and manage purchase orders to suppliers.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QMessageBox, QDateEdit, QTextEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.billing import purchase_order_service, product_service
from app.services.party_service import get_all_parties
from app.ui.views.billing.invoice_view import InvoiceItemWidget


class POFormDialog(QDialog):
    def __init__(self, po_data=None, parent=None):
        super().__init__(parent)
        self.po_data = po_data
        self.setWindowTitle("Edit PO" if po_data else "New Purchase Order")
        self.setMinimumSize(900, 600)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()
        if po_data: self.populate(po_data)

    def init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(12)
        title = QLabel("Edit PO" if self.po_data else "Create Purchase Order")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;"); layout.addWidget(title)

        form_frame = QFrame(); form_frame.setObjectName("Card")
        fl = QHBoxLayout(form_frame)
        pb = QVBoxLayout(); pb.addWidget(QLabel("Supplier *"))
        self.cmb_party = QComboBox(); self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Supplier --")
        self.cmb_party.addItem("", None)
        parties = get_all_parties()
        suppliers = [p for p in parties if p.get("party_type") in ("Supplier", "Both")]
        if not suppliers: suppliers = parties
        for p in suppliers: self.cmb_party.addItem(p["name"], p["id"])
        pb.addWidget(self.cmb_party); fl.addLayout(pb, 2)

        db = QVBoxLayout(); db.addWidget(QLabel("PO Date *"))
        self.dt_date = QDateEdit(QDate.currentDate()); self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy"); db.addWidget(self.dt_date); fl.addLayout(db, 1)
        layout.addWidget(form_frame)

        ih = QHBoxLayout()
        lbl_items = QLabel("Items"); lbl_items.setStyleSheet("font-size: 15px; font-weight: 600;")
        ih.addWidget(lbl_items); ih.addStretch()
        btn_add = QPushButton("+ Add Item"); btn_add.setObjectName("PrimaryBtn")
        btn_add.clicked.connect(self.add_item); ih.addWidget(btn_add)
        layout.addLayout(ih)

        self.items_layout = QVBoxLayout(); self.items_layout.setSpacing(4)
        layout.addLayout(self.items_layout); self.add_item()

        self.lbl_total = QLabel("Total: ₹0.00")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E63; font-family: Consolas;")
        self.lbl_total.setAlignment(Qt.AlignRight); layout.addWidget(self.lbl_total)

        self.txt_notes = QTextEdit(); self.txt_notes.setMaximumHeight(50)
        self.txt_notes.setPlaceholderText("Notes..."); layout.addWidget(self.txt_notes)

        bl = QHBoxLayout()
        bs = QPushButton("Save PO"); bs.setObjectName("PrimaryBtn"); bs.setFixedHeight(40); bs.clicked.connect(self.accept)
        bc = QPushButton("Cancel"); bc.setFixedHeight(40); bc.clicked.connect(self.reject)
        bl.addWidget(bs); bl.addWidget(bc); bl.addStretch(); layout.addLayout(bl)

    def add_item(self):
        w = InvoiceItemWidget(products_list=self.products)
        w.item_changed.connect(self._update_total)
        w.remove_requested.connect(self._remove_item)
        self.item_widgets.append(w); self.items_layout.addWidget(w)

    def _remove_item(self, w):
        if len(self.item_widgets) <= 1: return
        self.item_widgets.remove(w); self.items_layout.removeWidget(w); w.deleteLater(); self._update_total()

    def _update_total(self):
        total = Decimal("0")
        for w in self.item_widgets:
            d = w.get_item_data()
            qty = Decimal(d["quantity"]); rate = Decimal(d["unit_price"])
            gst = Decimal(d["gst_rate_pct"] or "0")
            taxable = qty * rate; total += taxable + taxable * gst / Decimal("100")
        self.lbl_total.setText(f"Total: ₹{float(total):,.2f}")

    def populate(self, data):
        for i in range(self.cmb_party.count()):
            if self.cmb_party.itemData(i) == data.get("party_id"): self.cmb_party.setCurrentIndex(i); break

    def get_data(self):
        qd = self.dt_date.date()
        items = []
        for w in self.item_widgets:
            d = w.get_item_data()
            items.append({"product_id": d["product_id"], "item_description": d["item_description"],
                          "hsn_code": d["hsn_code"], "quantity": d["quantity"], "unit": d["unit"],
                          "unit_price": d["unit_price"], "tax_rate": d["gst_rate_pct"]})
        return {
            "po_data": {"party_id": self.cmb_party.currentData(), "po_date": date(qd.year(), qd.month(), qd.day()),
                        "notes": self.txt_notes.toPlainText().strip()},
            "items_data": items,
        }


class PurchaseOrderView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent); self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header = QHBoxLayout()
        tb = QVBoxLayout(); tb.setSpacing(4)
        lbl = QLabel("Purchase Orders"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        tb.addWidget(lbl)
        ls = QLabel("Create and track purchase orders to suppliers"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")
        tb.addWidget(ls); header.addLayout(tb); header.addStretch()
        bn = QPushButton("+ New PO"); bn.setObjectName("PrimaryBtn"); bn.setFixedHeight(36)
        bn.clicked.connect(self.create_po); header.addWidget(bn)
        br = QPushButton("Refresh"); br.setFixedHeight(36); br.clicked.connect(self.load_data); header.addWidget(br)
        layout.addLayout(header)

        ff = QFrame(); ff.setObjectName("Card"); fl = QHBoxLayout(ff); fl.setContentsMargins(12, 8, 12, 8)
        self.inp_search = QLineEdit(); self.inp_search.setPlaceholderText("Search...")
        self.inp_search.textChanged.connect(self.load_data); fl.addWidget(self.inp_search, 2)
        self.cmb_status = QComboBox(); self.cmb_status.addItems(["All", "draft", "sent", "received", "cancelled"])
        self.cmb_status.currentTextChanged.connect(self.load_data); fl.addWidget(self.cmb_status)
        layout.addWidget(ff)

        self.table = QTableWidget(); self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["PO #", "Date", "Supplier", "Tax (₹)", "Total (₹)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4, 5]: self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36); self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 orders"); self.lbl_count.setStyleSheet("color: #6B6558;")
        bottom.addWidget(self.lbl_count); bottom.addStretch()

        btn_recv = QPushButton("Mark as Received"); btn_recv.setObjectName("SuccessBtn")
        btn_recv.clicked.connect(self.mark_received); bottom.addWidget(btn_recv)
        bd = QPushButton("Delete"); bd.setObjectName("DestructiveBtn"); bd.clicked.connect(self.delete_po)
        bottom.addWidget(bd); layout.addLayout(bottom)
        self.load_data()

    def load_data(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        status = self.cmb_status.currentText() if hasattr(self, 'cmb_status') else None
        pos = purchase_order_service.get_all_purchase_orders(search=search, status=status)
        self.table.setRowCount(len(pos)); mono = QFont("Consolas", 10)
        for row, po in enumerate(pos):
            self.table.setItem(row, 0, QTableWidgetItem(po["po_number"]))
            d = po.get("po_date", ""); d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str); it_d.setFont(mono); self.table.setItem(row, 1, it_d)
            self.table.setItem(row, 2, QTableWidgetItem(po.get("party_name", "")))
            for col, key in [(3, "tax_amount"), (4, "total_amount")]:
                it = QTableWidgetItem(f"₹{po.get(key, 0):,.2f}"); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(mono); self.table.setItem(row, col, it)
            st = po.get("status", "draft")
            it_s = QTableWidgetItem(st.upper())
            cm = {"draft": "#A6822E", "sent": "#2C3E63", "received": "#2F6844", "cancelled": "#8B2635"}
            it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); self.table.setItem(row, 5, it_s)
            self.table.item(row, 0).setData(Qt.UserRole, po["id"])
        self.lbl_count.setText(f"{len(pos)} orders")

    def create_po(self):
        dlg = POFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                purchase_order_service.create_purchase_order(data["po_data"], data["items_data"])
                self.load_data(); QMessageBox.information(self, "Success", "Purchase Order created!")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def mark_received(self):
        row = self.table.currentRow()
        if row < 0: QMessageBox.information(self, "Info", "Select a PO."); return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        try:
            purchase_order_service.mark_as_received(po_id)
            self.load_data(); QMessageBox.information(self, "Success", "PO marked as received. Stock updated!")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def delete_po(self):
        row = self.table.currentRow()
        if row < 0: return
        po_id = self.table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", "Delete this PO?") == QMessageBox.Yes:
            purchase_order_service.delete_purchase_order(po_id); self.load_data()
