"""
Expense Tracking View
Full expense management with category breakdown, add/delete, and summary reports.
Inspired by Vyapar's Expense Tracker.
"""
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QDateEdit, QTextEdit, QFormLayout,
    QDialog, QDialogButtonBox, QMessageBox, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.expense_service import (
    get_all_expenses, create_expense, delete_expense,
    get_all_categories, create_category, get_expense_summary
)
from app.config import CURRENCY_SYMBOL, PAYMENT_MODES
from app.ui.widgets.stat_card import StatCard


class ExpenseView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header Bar ──
        header = QHBoxLayout()
        lbl_title = QLabel("💰 Expense Tracker")
        lbl_title.setProperty("class", "ScreenTitle")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1B1B18;")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_add = QPushButton("➕ Record Expense")
        btn_add.setObjectName("PrimaryBtn")
        btn_add.setStyleSheet("padding: 8px 18px; font-size: 13px;")
        btn_add.clicked.connect(self.open_add_dialog)
        header.addWidget(btn_add)

        btn_add_cat = QPushButton("📁 Manage Categories")
        btn_add_cat.clicked.connect(self.open_category_dialog)
        header.addWidget(btn_add_cat)
        layout.addLayout(header)

        # ── KPI Cards ──
        self.kpi_box = QHBoxLayout()
        self.kpi_box.setSpacing(12)
        self.card_total = StatCard("Total Expenses (This Month)", f"{CURRENCY_SYMBOL}0.00")
        self.card_today = StatCard("Today's Expenses", f"{CURRENCY_SYMBOL}0.00")
        self.card_top_cat = StatCard("Top Category", "—")
        self.card_count = StatCard("Entries This Month", "0")
        for card in [self.card_total, self.card_today, self.card_top_cat, self.card_count]:
            self.kpi_box.addWidget(card)
        layout.addLayout(self.kpi_box)

        # ── Filters ──
        filter_box = QHBoxLayout()
        filter_box.setSpacing(8)

        filter_box.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(date.today().year, date.today().month, 1))
        filter_box.addWidget(self.date_from)

        filter_box.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_box.addWidget(self.date_to)

        filter_box.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.setMinimumWidth(160)
        filter_box.addWidget(self.combo_category)

        btn_filter = QPushButton("🔍 Filter")
        btn_filter.setObjectName("SecondaryBtn")
        btn_filter.clicked.connect(self.load_data)
        filter_box.addWidget(btn_filter)

        filter_box.addStretch()
        layout.addLayout(filter_box)

        # ── Expense Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Expense #", "Category", "Description",
            "Amount", "GST", "Total", "Payment Mode"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        # ── Bottom Actions ──
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #8B2635;")
        bottom.addWidget(self.lbl_total)
        bottom.addStretch()

        btn_delete = QPushButton("🗑️ Delete Selected")
        btn_delete.setObjectName("DestructiveBtn")
        btn_delete.clicked.connect(self.delete_selected)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)

    def load_data(self):
        """Loads expense data with filters."""
        # Preserve selected category
        prev_cat_id = self.combo_category.currentData() if self.combo_category.count() > 0 else None
        cats = get_all_categories()
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItem("All Categories", None)
        found_idx = 0
        for idx, c in enumerate(cats, start=1):
            self.combo_category.addItem(c["name"], c["id"])
            if c["id"] == prev_cat_id:
                found_idx = idx
        self.combo_category.setCurrentIndex(found_idx)
        self.combo_category.blockSignals(False)

        start = self.date_from.date().toPython()
        end = self.date_to.date().toPython()
        cat_id = self.combo_category.currentData()

        expenses = get_all_expenses(start_date=start, end_date=end, category_id=cat_id)

        self.table.setUpdatesEnabled(False)
        grand_total = 0.0
        try:
            self.table.setRowCount(len(expenses))
            for row, exp in enumerate(expenses):
                d = exp.get("expense_date", "")
                if hasattr(d, "strftime"):
                    d = d.strftime("%d-%m-%Y")
                self.table.setItem(row, 0, QTableWidgetItem(str(d)))
                self.table.setItem(row, 1, QTableWidgetItem(exp.get("expense_number", "")))
                self.table.setItem(row, 2, QTableWidgetItem(exp.get("category_name", "")))
                self.table.setItem(row, 3, QTableWidgetItem(exp.get("description", "")))

                amt_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{exp['amount']:,.2f}")
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, amt_item)

                gst_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{exp['gst_amount']:,.2f}")
                gst_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, gst_item)

                total_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{exp['total_amount']:,.2f}")
                total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                total_item.setFont(QFont("Consolas", 12, QFont.Bold))
                self.table.setItem(row, 6, total_item)

                self.table.setItem(row, 7, QTableWidgetItem(exp.get("payment_mode", "")))

                # Store ID for deletion
                self.table.item(row, 0).setData(Qt.UserRole, exp.get("id"))
                grand_total += exp["total_amount"]
        finally:
            self.table.setUpdatesEnabled(True)

        self.lbl_total.setText(f"Total: {CURRENCY_SYMBOL}{grand_total:,.2f}")

        # Update KPI cards
        self._update_kpis()

    def _update_kpis(self):
        try:
            summary = get_expense_summary()
            self.card_total.set_value(f"{CURRENCY_SYMBOL}{summary['grand_total']:,.2f}")
            self.card_count.set_value(str(sum(c['count'] for c in summary['categories'])))
            if summary['categories']:
                self.card_top_cat.set_value(summary['categories'][0]['category'])
            else:
                self.card_top_cat.set_value("—")

            # Today's expenses
            today_summary = get_expense_summary(start_date=date.today(), end_date=date.today())
            self.card_today.set_value(f"{CURRENCY_SYMBOL}{today_summary['grand_total']:,.2f}")
        except Exception:
            pass

    def open_add_dialog(self):
        dlg = AddExpenseDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def open_category_dialog(self):
        dlg = CategoryManagerDialog(self)
        dlg.exec()
        self.load_data()

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an expense entry to delete.")
            return
        exp_id = self.table.item(row, 0).data(Qt.UserRole)
        if not exp_id:
            return
        res = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete expense entry? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            try:
                delete_expense(exp_id)
                self.load_data()
                QMessageBox.information(self, "Deleted", "Expense entry deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


class AddExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record New Expense")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date:", self.date_edit)

        self.combo_cat = QComboBox()
        cats = get_all_categories()
        for c in cats:
            self.combo_cat.addItem(c["name"], c["id"])
        form.addRow("Category:", self.combo_cat)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("e.g. October office rent, Courier charges")
        form.addRow("Description *:", self.inp_desc)

        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0.00")
        form.addRow("Amount (₹):", self.inp_amount)

        self.inp_gst = QLineEdit()
        self.inp_gst.setPlaceholderText("0.00")
        self.inp_gst.setText("0.00")
        form.addRow("GST Amount (₹):", self.inp_gst)

        self.combo_payment = QComboBox()
        self.combo_payment.addItems(PAYMENT_MODES)
        form.addRow("Payment Mode:", self.combo_payment)

        self.inp_ref = QLineEdit()
        self.inp_ref.setPlaceholderText("Bill/Receipt reference number")
        form.addRow("Reference No:", self.inp_ref)

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(50)
        form.addRow("Notes:", self.txt_notes)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.save_expense)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def save_expense(self):
        try:
            amount = float(self.inp_amount.text().strip() or 0)
            gst = float(self.inp_gst.text().strip() or 0)
            if amount <= 0:
                QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
                return

            data = {
                "expense_date": self.date_edit.date().toPython(),
                "category_id": self.combo_cat.currentData(),
                "description": self.inp_desc.text().strip(),
                "amount": amount,
                "gst_amount": gst,
                "payment_mode": self.combo_payment.currentText(),
                "reference_no": self.inp_ref.text().strip(),
                "notes": self.txt_notes.toPlainText().strip(),
            }
            create_expense(data)
            QMessageBox.information(self, "Success", "Expense recorded successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Expense Categories")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Category Name", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.load_categories()
        layout.addWidget(self.table)

        add_box = QHBoxLayout()
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("New category name")
        add_box.addWidget(self.inp_name)
        btn_add = QPushButton("➕ Add")
        btn_add.setObjectName("PrimaryBtn")
        btn_add.clicked.connect(self.add_category)
        add_box.addWidget(btn_add)
        layout.addLayout(add_box)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_categories(self):
        cats = get_all_categories(include_inactive=True)
        self.table.setRowCount(len(cats))
        for row, c in enumerate(cats):
            self.table.setItem(row, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(c.get("description", "")))

    def add_category(self):
        name = self.inp_name.text().strip()
        if not name:
            return
        try:
            create_category(name)
            self.inp_name.clear()
            self.load_categories()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
