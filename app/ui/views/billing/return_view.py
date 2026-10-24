"""
Returns View — Sales & Purchase Returns Management.
"""
from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QDateEdit, QTextEdit, QTabWidget, QDoubleSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from app.services.billing import return_service, product_service
from app.services.party_service import get_all_parties
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, StatusBadgeLabel, ThemedMessageBox,
    configure_dialog_window_flags
)
from app.ui.save_dialog import execute_export_pipeline


class ReturnItemRow(QFrame):
    """Simple return item row."""
    def __init__(self, products=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ItemRow")
        self.setProperty("variant", "sunken")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(38)
        self.setMaximumHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        self.cmb_product = QComboBox()
        self.cmb_product.setEditable(True)
        self.cmb_product.lineEdit().setPlaceholderText("-- Select Product --")
        self.cmb_product.addItem("", None)
        for p in (products or []):
            self.cmb_product.addItem(p['name'], p)
        self.cmb_product.currentIndexChanged.connect(self._on_select)
        layout.addWidget(self.cmb_product, 4)

        self.spn_qty = QDoubleSpinBox()
        self.spn_qty.setRange(0.001, 999999)
        self.spn_qty.setDecimals(3)
        self.spn_qty.setValue(1)
        self.spn_qty.setMaximumWidth(100)
        layout.addWidget(self.spn_qty, 1)

        self.spn_rate = QDoubleSpinBox()
        self.spn_rate.setRange(0, 99999999)
        self.spn_rate.setDecimals(2)
        self.spn_rate.setPrefix("₹")
        self.spn_rate.setMaximumWidth(120)
        layout.addWidget(self.spn_rate, 1)

        self.cmb_gst = QComboBox()
        self.cmb_gst.addItems(["0", "5", "12", "18", "28"])
        self.cmb_gst.setCurrentText("18")
        self.cmb_gst.setMaximumWidth(80)
        layout.addWidget(self.cmb_gst, 1)

    def _on_select(self, idx):
        data = self.cmb_product.itemData(idx)
        if data:
            self.spn_rate.setValue(data.get("price", 0))
            self.cmb_gst.setCurrentText(str(int(data.get("tax_rate", 18))))

    def get_data(self):
        pd = self.cmb_product.currentData()
        return {
            "product_id": pd["id"] if pd else None,
            "item_description": pd["name"] if pd else self.cmb_product.currentText(),
            "quantity": str(self.spn_qty.value()),
            "unit_price": str(self.spn_rate.value()),
            "tax_rate": self.cmb_gst.currentText()
        }


class ReturnFormDialog(QDialog):
    def __init__(self, return_type="sales", parent=None):
        super().__init__(parent)
        self.return_type = return_type
        self.setWindowTitle(f"New {'Sales' if return_type == 'sales' else 'Purchase'} Return")
        configure_dialog_window_flags(self, min_width=850, min_height=550)
        self.item_widgets = []
        self.products = product_service.get_all_products()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(f"New {'Sales' if self.return_type == 'sales' else 'Purchase'} Return")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        ff = CardFrame()
        fl = QHBoxLayout(ff)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(12)

        pb = QVBoxLayout()
        pb.addWidget(QLabel("Party *"))
        self.cmb_party = QComboBox()
        self.cmb_party.setEditable(True)
        self.cmb_party.lineEdit().setPlaceholderText("-- Select Party --")
        self.cmb_party.addItem("", None)
        for p in get_all_parties():
            self.cmb_party.addItem(p["name"], p["id"])
        pb.addWidget(self.cmb_party)
        fl.addLayout(pb, 2)

        db = QVBoxLayout()
        db.addWidget(QLabel("Date *"))
        self.dt_date = QDateEdit(QDate.currentDate())
        self.dt_date.setCalendarPopup(True)
        self.dt_date.setDisplayFormat("dd-MM-yyyy")
        db.addWidget(self.dt_date)
        fl.addLayout(db, 1)

        layout.addWidget(ff)

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

        self.txt_reason = QTextEdit()
        self.txt_reason.setMaximumHeight(60)
        self.txt_reason.setPlaceholderText("Reason for return...")
        layout.addWidget(self.txt_reason)

        bl = QHBoxLayout()
        bl.addStretch()

        bc = QPushButton("Cancel")
        bc.setProperty("variant", "secondary")
        bc.setFixedHeight(36)
        bc.clicked.connect(self.reject)
        bl.addWidget(bc)

        bs = QPushButton("Save Return")
        bs.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        bs.setProperty("variant", "primary")
        bs.setFixedHeight(36)
        bs.clicked.connect(self.accept)
        bl.addWidget(bs)

        layout.addLayout(bl)

    def add_item(self):
        w = ReturnItemRow(products=self.products)
        self.item_widgets.append(w)
        self.items_layout.addWidget(w)

    def get_data(self):
        qd = self.dt_date.date()
        return {
            "data": {
                "party_id": self.cmb_party.currentData(),
                "return_date": date(qd.year(), qd.month(), qd.day()),
                "reason": self.txt_reason.toPlainText().strip()
            },
            "items_data": [w.get_data() for w in self.item_widgets],
        }


class ReturnView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.header_widget = PageHeaderWidget(
            title="Returns & Credit Notes",
            subtitle="Manage sales returns & purchase returns",
            action_text="New Sales Return",
            action_icon="plus",
            action_callback=lambda: self.create_return("sales")
        )

        btn_pr = QPushButton("New Purchase Return")
        btn_pr.setIcon(theme_manager.get_icon("plus", size=16))
        btn_pr.setProperty("variant", "secondary")
        btn_pr.setFixedHeight(36)
        btn_pr.clicked.connect(lambda: self.create_return("purchase"))
        self.header_widget.add_custom_action(btn_pr)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_refresh.setProperty("variant", "secondary")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_data)
        self.header_widget.add_custom_action(btn_refresh)

        layout.addWidget(self.header_widget)

        self.tabs = QTabWidget()
        self.sr_table = self._create_table(["Return #", "Date", "Party", "Amount (₹)", "Status"])
        self.tabs.addTab(self.sr_table, "Sales Returns")
        self.pr_table = self._create_table(["Return #", "Date", "Party", "Amount (₹)", "Status"])
        self.tabs.addTab(self.pr_table, "Purchase Returns")
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setFont(theme_manager.get_font("caption"))
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        self.btn_print = QPushButton("Print Note / Return")
        self.btn_print.setIcon(theme_manager.get_icon("printer", size=16))
        self.btn_print.setProperty("variant", "secondary")
        self.btn_print.clicked.connect(self.print_return)
        bottom.addWidget(self.btn_print)

        layout.addLayout(bottom)

        self.load_data()

    def _create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4]:
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(36)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _fill_table(self, table, data, date_key, num_key):
        table.setRowCount(len(data))
        for row, r in enumerate(data):
            it_num = QTableWidgetItem(r[num_key])
            it_num.setData(Qt.UserRole, r["id"])
            table.setItem(row, 0, it_num)

            d = r.get(date_key, "")
            d_str = d.strftime("%d-%m-%Y") if hasattr(d, 'strftime') else str(d)
            it_d = QTableWidgetItem(d_str)
            table.setItem(row, 1, it_d)

            table.setItem(row, 2, QTableWidgetItem(r.get("party_name", "")))

            tot = float(r.get('total_amount', 0))
            it_a = QTableWidgetItem(f"₹{tot:,.2f}")
            it_a.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 3, it_a)

            st = r.get("status", "pending")
            badge = StatusBadgeLabel(st.upper(), status=st)
            table.setCellWidget(row, 4, badge)

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
                self.load_data()
                ThemedMessageBox.information(self, "Success", "Return created!")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))

    def print_return(self):
        curr_idx = self.tabs.currentIndex()
        is_sales = (curr_idx == 0)
        table = self.sr_table if is_sales else self.pr_table
        row = table.currentRow()
        if row < 0:
            doc_name = "Sales Return" if is_sales else "Purchase Return"
            ThemedMessageBox.information(self, "Info", f"Please select a {doc_name} to print.")
            return

        it = table.item(row, 0)
        if not it:
            return
        ret_id = it.data(Qt.UserRole)
        if not ret_id:
            ThemedMessageBox.warning(self, "Warning", "Please refresh the table to print this return.")
            return

        if is_sales:
            ret = return_service.get_sales_return_by_id(ret_id)
        else:
            ret = return_service.get_purchase_return_by_id(ret_id)

        if not ret:
            ThemedMessageBox.warning(self, "Warning", "Could not find return details.")
            return

        try:
            from app.services.billing.return_pdf_generator import ReturnPDFGenerator
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                comp_data = comp.to_dict() if comp else {}

            generator = ReturnPDFGenerator()
            ret_data = {
                "return_number": ret["return_number"],
                "return_date": ret.get("return_date", ""),
                "original_invoice_number": ret.get("original_invoice_number", ""),
                "original_bill_number": ret.get("original_bill_number", ""),
                "reason": ret.get("reason", "Goods Returned"),
                "company": comp_data,
                "customer": {
                    "name": ret.get("party_name", ""),
                    "address": ret.get("party_address", ""),
                    "gstin": ret.get("party_gstin", ""),
                    "phone": ret.get("party_phone", ""),
                },
                "items": [
                    {
                        "item_description": it.get("item_description") or "Returned Item",
                        "hsn_code": it.get("hsn_code", "-"),
                        "quantity": float(it.get("quantity", 1)),
                        "unit": it.get("unit", "PCS"),
                        "unit_price": float(it.get("unit_price", 0)),
                        "tax_rate": float(it.get("tax_rate", 0)),
                        "total_item_amount": float(it.get("total_amount", 0)),
                        "reason": it.get("reason", ""),
                    }
                    for it in ret.get("items", [])
                ],
                "totals": {
                    "taxable_amount": float(ret.get("subtotal", 0)),
                    "tax_amount": float(ret.get("tax_amount", 0)),
                    "grand_total": float(ret.get("total_amount", 0)),
                }
            }

            safe_num = ret["return_number"].replace('/', '-')
            p_name = ret.get("party_name", "Party")
            note_type = "CreditNote" if is_sales else "DebitNote"
            suggested = f"{note_type}_{safe_num}_{p_name}"

            def _generate(out_p):
                if is_sales:
                    return generator.generate_credit_note(ret_data, filename=str(out_p))
                else:
                    return generator.generate_debit_note(ret_data, filename=str(out_p))

            execute_export_pipeline(
                parent=self,
                suggested_name=suggested,
                kind="pdf",
                generator_fn=_generate,
                trigger_button=getattr(self, "btn_print", None)
            )
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")

