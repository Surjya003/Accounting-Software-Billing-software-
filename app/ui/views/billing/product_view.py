"""
Product / Inventory Management View
Ported from Billing-software's ProductManager to PySide6 with Bahi-Khata theme.
"""
import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QTextEdit, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.billing import product_service
from app.config import EXPORTS_DIR

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class ProductDialog(QDialog):
    """Add/Edit product dialog."""
    def __init__(self, product_data=None, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setWindowTitle("Edit Product" if product_data else "Add New Product")
        self.setMinimumSize(500, 580)
        self.init_ui()
        if product_data:
            self.populate(product_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Edit Product" if self.product_data else "New Product")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1B1B18;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Product name *")
        form.addRow("Name *", self.inp_name)

        self.inp_hsn = QLineEdit()
        self.inp_hsn.setPlaceholderText("e.g. 8504")
        form.addRow("HSN Code", self.inp_hsn)

        self.inp_category = QLineEdit()
        self.inp_category.setPlaceholderText("e.g. Electrical, Hardware")
        form.addRow("Category", self.inp_category)

        self.cmb_unit = QComboBox()
        self.cmb_unit.addItems(["PCS", "KGS", "BOX", "MTR", "NOS", "LTR", "SET", "PKT"])
        form.addRow("Unit", self.cmb_unit)

        self.spn_price = QDoubleSpinBox()
        self.spn_price.setRange(0, 99999999.99)
        self.spn_price.setDecimals(2)
        self.spn_price.setPrefix("₹ ")
        form.addRow("Selling Price", self.spn_price)

        self.spn_purchase = QDoubleSpinBox()
        self.spn_purchase.setRange(0, 99999999.99)
        self.spn_purchase.setDecimals(2)
        self.spn_purchase.setPrefix("₹ ")
        form.addRow("Purchase Price", self.spn_purchase)

        self.cmb_tax = QComboBox()
        self.cmb_tax.addItems(["0", "5", "12", "18", "28"])
        self.cmb_tax.setCurrentText("18")
        form.addRow("GST Rate %", self.cmb_tax)

        self.spn_stock = QDoubleSpinBox()
        self.spn_stock.setRange(0, 9999999)
        self.spn_stock.setDecimals(3)
        form.addRow("Stock Qty", self.spn_stock)

        self.spn_threshold = QDoubleSpinBox()
        self.spn_threshold.setRange(0, 9999999)
        self.spn_threshold.setDecimals(3)
        self.spn_threshold.setValue(10)
        form.addRow("Low Stock Threshold", self.spn_threshold)

        self.inp_barcode = QLineEdit()
        self.inp_barcode.setPlaceholderText("Optional barcode")
        form.addRow("Barcode", self.inp_barcode)

        self.inp_desc = QTextEdit()
        self.inp_desc.setMaximumHeight(60)
        self.inp_desc.setPlaceholderText("Optional description")
        form.addRow("Description", self.inp_desc)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Product")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def populate(self, data):
        self.inp_name.setText(data.get("name", ""))
        self.inp_hsn.setText(data.get("hsn_code", "") or "")
        self.inp_category.setText(data.get("category", "") or "")
        idx = self.cmb_unit.findText(data.get("unit", "PCS"))
        if idx >= 0: self.cmb_unit.setCurrentIndex(idx)
        self.spn_price.setValue(data.get("price", 0))
        self.spn_purchase.setValue(data.get("purchase_price", 0) or 0)
        self.cmb_tax.setCurrentText(str(int(data.get("tax_rate", 18))))
        self.spn_stock.setValue(data.get("stock_quantity", 0))
        self.spn_threshold.setValue(data.get("low_stock_threshold", 10))
        self.inp_barcode.setText(data.get("barcode", "") or "")
        self.inp_desc.setPlainText(data.get("description", "") or "")

    def get_data(self):
        return {
            "name": self.inp_name.text().strip(),
            "hsn_code": self.inp_hsn.text().strip(),
            "category": self.inp_category.text().strip(),
            "unit": self.cmb_unit.currentText(),
            "price": self.spn_price.value(),
            "purchase_price": self.spn_purchase.value(),
            "tax_rate": float(self.cmb_tax.currentText()),
            "stock_quantity": self.spn_stock.value(),
            "low_stock_threshold": self.spn_threshold.value(),
            "barcode": self.inp_barcode.text().strip(),
            "description": self.inp_desc.toPlainText().strip(),
        }


class ProductView(QWidget):
    """Product/Inventory management page in the Bahi-Khata theme."""
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
        lbl_title = QLabel("Products & Inventory")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 600; color: #1B1B18;")
        title_box.addWidget(lbl_title)
        lbl_sub = QLabel("Manage product catalog, pricing, stock levels, and GST rates")
        lbl_sub.setStyleSheet("font-size: 12px; color: #6B6558;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        btn_add = QPushButton("+ Add Product")
        btn_add.setObjectName("PrimaryBtn")
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self.open_add_dialog)
        header.addWidget(btn_add)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self.load_products)
        header.addWidget(btn_refresh)

        btn_edit = QPushButton("Edit Selected")
        btn_edit.setFixedHeight(36)
        btn_edit.clicked.connect(self.open_edit_dialog)
        header.addWidget(btn_edit)

        btn_export_csv = QPushButton("Export CSV")
        btn_export_csv.setFixedHeight(36)
        btn_export_csv.clicked.connect(self.export_csv)
        header.addWidget(btn_export_csv)

        btn_export_excel = QPushButton("Export Excel")
        btn_export_excel.setFixedHeight(36)
        btn_export_excel.clicked.connect(self.export_excel)
        header.addWidget(btn_export_excel)

        layout.addLayout(header)

        # Filters
        filter_frame = QFrame()
        filter_frame.setObjectName("Card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 8, 12, 8)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Search products by name, HSN, barcode...")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_products)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        filter_layout.addWidget(self.inp_search, 2)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["All Products", "Low Stock Only"])
        self.cmb_filter.currentTextChanged.connect(self.load_products)
        filter_layout.addWidget(self.cmb_filter)

        layout.addWidget(filter_frame)

        # Products Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Name", "HSN", "Category", "Unit", "Price (₹)", "Purchase (₹)",
            "GST %", "Stock", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 9):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 90)   # HSN
        self.table.setColumnWidth(2, 120)  # Category
        self.table.setColumnWidth(3, 75)   # Unit
        self.table.setColumnWidth(4, 110)  # Price
        self.table.setColumnWidth(5, 110)  # Purchase
        self.table.setColumnWidth(6, 75)   # GST %
        self.table.setColumnWidth(7, 95)   # Stock
        self.table.setColumnWidth(8, 100)  # Status

        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.open_edit_dialog)
        layout.addWidget(self.table, 1)

        # Bottom action bar
        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 products")
        self.lbl_count.setStyleSheet("color: #6B6558; font-size: 12px;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()

        btn_delete = QPushButton("Delete Selected")
        btn_delete.setObjectName("DestructiveBtn")
        btn_delete.clicked.connect(self.delete_selected)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)

        self.load_products()

    def load_products(self):
        search = self.inp_search.text().strip() if hasattr(self, 'inp_search') else None
        low_stock = self.cmb_filter.currentText() == "Low Stock Only" if hasattr(self, 'cmb_filter') else False

        products = product_service.get_all_products(search=search, low_stock_only=low_stock)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(products))
            mono = QFont("Consolas", 10)
            for row, p in enumerate(products):
                self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
                self.table.setItem(row, 1, QTableWidgetItem(p.get("hsn_code") or "-"))
                self.table.setItem(row, 2, QTableWidgetItem(p.get("category") or "-"))
                self.table.setItem(row, 3, QTableWidgetItem(p.get("unit", "PCS")))

                it_price = QTableWidgetItem(f"₹{p['price']:,.2f}")
                it_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_price.setFont(mono)
                self.table.setItem(row, 4, it_price)

                pp = p.get("purchase_price") or 0
                it_pp = QTableWidgetItem(f"₹{pp:,.2f}")
                it_pp.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_pp.setFont(mono)
                self.table.setItem(row, 5, it_pp)

                it_gst = QTableWidgetItem(f"{p['tax_rate']:.0f}%")
                it_gst.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, it_gst)

                stock = p.get("stock_quantity", 0)
                threshold = p.get("low_stock_threshold", 10)
                it_stock = QTableWidgetItem(f"{stock:,.1f}")
                it_stock.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_stock.setFont(mono)
                if stock <= threshold:
                    it_stock.setForeground(QColor("#8B2635"))
                else:
                    it_stock.setForeground(QColor("#2F6844"))
                self.table.setItem(row, 7, it_stock)

                status = "Low Stock" if stock <= threshold else "In Stock"
                it_status = QTableWidgetItem(status)
                if stock <= threshold:
                    it_status.setForeground(QColor("#8B2635"))
                else:
                    it_status.setForeground(QColor("#2F6844"))
                self.table.setItem(row, 8, it_status)

                self.table.item(row, 0).setData(Qt.UserRole, p["id"])
        finally:
            self.table.setUpdatesEnabled(True)

        self.lbl_count.setText(f"{len(products)} products")

    def open_add_dialog(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Validation", "Product name is required.")
                return
            try:
                product_service.create_product(data)
                self.load_products()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def open_edit_dialog(self, index=None):
        row = index.row() if index else self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        product = product_service.get_product_by_id(pid)
        if not product:
            return
        dlg = ProductDialog(product_data=product, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                product_service.update_product(pid, data)
                self.load_products()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Select a product to delete.")
            return
        item = self.table.item(row, 0)
        if not item:
            return
        pid = item.data(Qt.UserRole)
        name = item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove '{name}' from inventory?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            product_service.delete_product(pid)
            self.load_products()

    def export_csv(self):
        """Export products to CSV file."""
        products = product_service.get_all_products()
        if not products:
            QMessageBox.information(self, "No Data", "No products to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", 
            f"Products_Inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not filename:
            return

        try:
            headers = ["Name", "HSN Code", "Category", "Unit", "Selling Price (₹)", 
                       "Purchase Price (₹)", "Wholesale Price (₹)", "GST %", 
                       "Stock Qty", "Low Stock Threshold", "Barcode", "Description", "Active"]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for p in products:
                    writer.writerow([
                        p.get("name", ""),
                        p.get("hsn_code", ""),
                        p.get("category", ""),
                        p.get("unit", "PCS"),
                        f"{p.get('price', 0):.2f}",
                        f"{p.get('purchase_price', 0) or 0:.2f}",
                        f"{p.get('wholesale_price', 0) or 0:.2f}",
                        f"{p.get('tax_rate', 18):.0f}",
                        f"{p.get('stock_quantity', 0):.3f}",
                        f"{p.get('low_stock_threshold', 10):.3f}",
                        p.get("barcode", ""),
                        p.get("description", ""),
                        "Yes" if p.get("is_active") else "No"
                    ])
            
            QMessageBox.information(self, "Success", f"Products exported successfully to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

    def export_excel(self):
        """Export products to Excel file."""
        if not HAS_OPENPYXL:
            QMessageBox.warning(self, "Missing Dependency", 
                "openpyxl is required for Excel export. Install it with:\npip install openpyxl")
            return

        products = product_service.get_all_products()
        if not products:
            QMessageBox.information(self, "No Data", "No products to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Excel",
            f"Products_Inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not filename:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Products Inventory"

            # Title row
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=13)
            title_cell = ws.cell(row=1, column=1, value="PRODUCTS & INVENTORY REPORT")
            title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
            title_cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 28

            # Subtitle with date
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=13)
            subtitle = ws.cell(row=2, column=1, 
                value=f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Total Products: {len(products)}")
            subtitle.font = Font(name="Calibri", size=10, italic=True, color="475569")
            subtitle.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[2].height = 18

            # Headers
            headers = ["Name", "HSN Code", "Category", "Unit", "Selling Price (₹)", 
                       "Purchase Price (₹)", "Wholesale Price (₹)", "GST %", 
                       "Stock Qty", "Low Stock Threshold", "Barcode", "Description", "Active"]
            
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            thin_border = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            row_num = 4
            for col_num, h in enumerate(headers, start=1):
                c = ws.cell(row=row_num, column=col_num, value=h)
                c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
                c.fill = header_fill
                c.alignment = Alignment(horizontal="right" if "₹" in h or "Qty" in h or "Price" in h or "GST" in h else "left", vertical="center")
                c.border = thin_border
            ws.row_dimensions[row_num].height = 20

            # Data rows
            for p in products:
                row_num += 1
                row_data = [
                    p.get("name", ""),
                    p.get("hsn_code", ""),
                    p.get("category", ""),
                    p.get("unit", "PCS"),
                    p.get("price", 0),
                    p.get("purchase_price", 0) or 0,
                    p.get("wholesale_price", 0) or 0,
                    p.get("tax_rate", 18),
                    p.get("stock_quantity", 0),
                    p.get("low_stock_threshold", 10),
                    p.get("barcode", ""),
                    p.get("description", ""),
                    "Yes" if p.get("is_active") else "No"
                ]
                
                for col_num, val in enumerate(row_data, start=1):
                    c = ws.cell(row=row_num, column=col_num, value=val)
                    c.border = thin_border
                    if col_num in [5, 6, 7]:  # Price columns
                        c.number_format = '#,##0.00'
                    elif col_num in [8]:  # GST %
                        c.number_format = '0"%"'
                    elif col_num in [9, 10]:  # Quantity columns
                        c.number_format = '#,##0.000'
                    c.alignment = Alignment(horizontal="right" if col_num in [5,6,7,8,9,10] else "left", vertical="center")

                # Highlight low stock rows
                stock = p.get("stock_quantity", 0)
                threshold = p.get("low_stock_threshold", 10)
                if stock <= threshold:
                    red_fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
                    for col_num in range(1, 14):
                        ws.cell(row=row_num, column=col_num).fill = red_fill

            # Auto-fit columns
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row in [1, 2]:  # skip header titles
                        continue
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(str(filename))
            QMessageBox.information(self, "Success", f"Products exported successfully to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export Excel: {str(e)}")
