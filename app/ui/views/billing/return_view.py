"""
Returns View — Sales & Purchase Returns Management.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QMessageBox, QDateEdit, QTextEdit, QTabWidget, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.billing import return_service, product_service
from app.services.party_service import get_all_parties


class ReturnItemRow(QFrame):
    """Simple return item row."""
    def __init__(self, products=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QHBoxLayout(self); layout.setContentsMargins(8, 4, 8, 4); layout.setSpacing(8)
        self.cmb_product = QComboBox(); self.cmb_product.setEditable(True)
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product --")
        self.cmb_product.addItem("", None)
        for p in (products or []):
            self.cmb_product.addItem(p['name'], p)
        self.cmb_product.currentIndexChanged.connect(self._on_select)
        layout.addWidget(self.cmb_product, 3)

        self.spn_qty = QDoubleSpinBox(); self.spn_qty.setRange(0.001, 999999); self.spn_qty.setDecimals(3); self.spn_qty.setValue(1)
        layout.addWidget(self.spn_qty, 1)
        self.spn_rate = QDoubleSpinBox(); self.spn_rate.setRange(0, 99999999); self.spn_rate.setDecimals(2); self.spn_rate.setPrefix("₹")
        layout.addWidget(self.spn_rate, 1)
        self.cmb_gst = QComboBox(); self.cmb_gst.addItems(["0", "5", "12", "18", "28"]); self.cmb_gst.setCurrentText("18")
        layout.addWidget(self.cmb_gst, 1)

    def _on_select(self, idx):
        data = self.cmb_product.itemData(idx)
        if data: self.spn_rate.setValue(data.get("price", 0)); self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))

    def get_data(self):
        pd = self.cmb_product.currentData()
        return {"product_id": pd["id"] if pd else None, "item_description": pd["name"] if pd else self.cmb_product.currentText(),
                "quantity": str(self.spn_qty.value()), "unit_price": str(self.spn_rate.value()), "tax_rate": self.cmb_gst.currentText()}


class ReturnFormDialog(QDialog):
    def __init__(self, return_type="sales", parent=None):
        super().__init__(parent)
        self.return_type = return_type
        self.setWindowTitle(f"New {'Sales' if return_type == 'sales' else 'Purchase'} Return")
        self.setMinimumSize(800, 550)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(12)
        title = QLabel(f"New {'Sales' if self.return_type == 'sales' else 'Purchase'} Return")
        title.setStyleSheet("font-size: 18px; font-weight: 600;"); layout.addWidget(title)

        ff = QFrame(); ff.setObjectName("Card"); fl = QHBoxLayout(ff)
        pb = QVBoxLayout(); pb.addWidget(QLabel("Party *"))
        self.cmb_party = QComboBox(); self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Party --")
        self.cmb_party.addItem("", None)
        for p in get_all_parties(): self.cmb_party.addItem(p["name"], p["id"])
        pb.addWidget(self.cmb_party); fl.addLayout(pb, 2)
        db = QVBoxLayout(); db.addWidget(QLabel("Date *"))
        self.dt_date = QDateEdit(QDate.currentDate()); self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy"); db.addWidget(self.dt_date); fl.addLayout(db, 1)
        layout.addWidget(ff)

        ih = QHBoxLayout(); ih.addWidget(QLabel("Items")); ih.addStretch()
        btn_add = QPushButton("+ Add Item"); btn_add.setObjectName("PrimaryBtn")
        btn_add.clicked.connect(self.add_item); ih.addWidget(btn_add)
        layout.addLayout(ih)
        self.items_layout = QVBoxLayout(); layout.addLayout(self.items_layout); self.add_item()

        self.txt_reason = QTextEdit(); self.txt_reason.setMaximumHeight(60)
        self.txt_reason.setPlaceholderText("Reason for return..."); layout.addWidget(self.txt_reason)

        bl = QHBoxLayout()
        bs = QPushButton("Save Return"); bs.setObjectName("PrimaryBtn"); bs.setFixedHeight(40); bs.clicked.connect(self.accept)
        bc = QPushButton("Cancel"); bc.setFixedHeight(40); bc.clicked.connect(self.reject)
        bl.addWidget(bs); bl.addWidget(bc); bl.addStretch(); layout.addLayout(bl)

    def add_item(self):
        w = ReturnItemRow(products=self.products); self.item_widgets.append(w); self.items_layout.addWidget(w)

    def get_data(self):
        qd = self.dt_date.date()
        return {
            "data": {"party_id": self.cmb_party.currentData(), "return_date": date(qd.year(), qd.month(), qd.day()),
                     "reason": self.txt_reason.toPlainText().strip()},
            "items_data": [w.get_data() for w in self.item_widgets],
        }


class ReturnView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent); self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        header = QHBoxLayout()
        tb = QVBoxLayout(); tb.setSpacing(4)
        lbl = QLabel("Returns"); lbl.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        tb.addWidget(lbl)
        ls = QLabel("Manage sales returns & purchase returns"); ls.setStyleSheet("font-size: 12px; color: #6B6558;")
        tb.addWidget(ls); header.addLayout(tb); header.addStretch()

        btn_sr = QPushButton("+ Sales Return"); btn_sr.setObjectName("PrimaryBtn"); btn_sr.setFixedHeight(36)
        btn_sr.clicked.connect(lambda: self.create_return("sales")); header.addWidget(btn_sr)
        btn_pr = QPushButton("+ Purchase Return"); btn_pr.setFixedHeight(36)
        btn_pr.clicked.connect(lambda: self.create_return("purchase")); header.addWidget(btn_pr)
        br = QPushButton("Refresh"); br.setFixedHeight(36); br.clicked.connect(self.load_data); header.addWidget(br)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.sr_table = self._create_table(["Return #", "Date", "Party", "Amount (₹)", "Status"])
        self.tabs.addTab(self.sr_table, "Sales Returns")
        self.pr_table = self._create_table(["Return #", "Date", "Party", "Amount (₹)", "Status"])
        self.tabs.addTab(self.pr_table, "Purchase Returns")
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel(""); self.lbl_count.setStyleSheet("color: #6B6558;")
        bottom.addWidget(self.lbl_count); bottom.addStretch()
        layout.addLayout(bottom)
        self.load_data()

    def _create_table(self, headers):
        table = QTableWidget(); table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4]: table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(36); table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows); table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _fill_table(self, table, data, date_key, num_key):
        table.setRowCount(len(data)); mono = QFont("Consolas", 10)
        for row, r in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(r[num_key]))
            d = r.get(date_key, ""); d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str); it_d.setFont(mono); table.setItem(row, 1, it_d)
            table.setItem(row, 2, QTableWidgetItem(r.get("party_name", "")))
            it_a = QTableWidgetItem(f"₹{r.get('total_amount', 0):,.2f}"); it_a.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_a.setFont(mono); table.setItem(row, 3, it_a)
            st = r.get("status", "pending")
            it_s = QTableWidgetItem(st.upper())
            cm = {"pending": "#A6822E", "approved": "#2F6844", "rejected": "#8B2635"}
            it_s.setForeground(QColor(cm.get(st, "#1B1B18"))); table.setItem(row, 4, it_s)

    def load_data(self):
        srs = return_service.get_all_sales_returns()
        prs = return_service.get_all_purchase_returns()
        self._fill_table(self.sr_table, srs, "return_date", "return_number")
        self._fill_table(self.pr_table, prs, "return_date", "return_number")
        self.lbl_count.setText(f"{len(srs)} sales returns, {len(prs)} purchase returns")

    def create_return(self, return_type):
        dlg = ReturnFormDialog(return_type=return_type, parent=self)
        if dlg.exec() == QDialog.Accepted:
            d = dlg.get_data()
            try:
                if return_type == "sales":
                    return_service.create_sales_return(d["data"], d["items_data"])
                else:
                    return_service.create_purchase_return(d["data"], d["items_data"])
                self.load_data(); QMessageBox.information(self, "Success", "Return created!")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))
