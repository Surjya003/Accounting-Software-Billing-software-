"""
Expense Tracking View
Full expense management with category breakdown, add/delete, and summary reports.
"""
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QDateEdit, QTextEdit, QFormLayout,
    QDialog, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

from app.services.expense_service import (
    get_all_expenses, create_expense, delete_expense,
    get_all_categories, create_category, get_expense_summary
)
from app.config import CURRENCY_SYMBOL, PAYMENT_MODES
from app.ui.widgets.stat_card import StatCard
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox, configure_dialog_window_flags
)


class ExpenseView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── Header Bar ──
        self.header_widget = PageHeaderWidget(
            title="Expense Tracker",
            subtitle="Record, categorize, and monitor operational business expenses",
            action_text="Record Expense",
            action_icon="plus",
            action_callback=self.open_add_dialog
        )

        btn_add_cat = QPushButton("Manage Categories")
        btn_add_cat.setIcon(theme_manager.get_icon("edit", size=16))
        btn_add_cat.setProperty("variant", "secondary")
        btn_add_cat.setFixedHeight(36)
        btn_add_cat.clicked.connect(self.open_category_dialog)
        self.header_widget.add_custom_action(btn_add_cat)

        layout.addWidget(self.header_widget)

        # ── KPI Cards ──
        self.kpi_box = QHBoxLayout()
        self.kpi_box.setSpacing(12)
        self.card_total = StatCard("TOTAL EXPENSES (MONTH)", f"{CURRENCY_SYMBOL}0.00", "Current month outgoings", token_name="danger")
        self.card_today = StatCard("TODAY'S EXPENSES", f"{CURRENCY_SYMBOL}0.00", "Recorded today", token_name="warning")
        self.card_top_cat = StatCard("TOP CATEGORY", "—", "Highest spending category", token_name="accent")
        self.card_count = StatCard("ENTRIES THIS MONTH", "0", "Voucher entries count", token_name="text_primary")
        for card in [self.card_total, self.card_today, self.card_top_cat, self.card_count]:
            self.kpi_box.addWidget(card)
        layout.addLayout(self.kpi_box)

        # ── Filters ──
        filter_frame = CardFrame()
        filter_box = QHBoxLayout(filter_frame)
        filter_box.setContentsMargins(12, 8, 12, 8)
        filter_box.setSpacing(10)

        filter_box.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(date.today().year, date.today().month, 1))
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        filter_box.addWidget(self.date_from)

        filter_box.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        filter_box.addWidget(self.date_to)

        filter_box.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.setMinimumWidth(160)
        filter_box.addWidget(self.combo_category)

        btn_filter = QPushButton("Filter")
        btn_filter.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_filter.setProperty("variant", "secondary")
        btn_filter.clicked.connect(self.load_data)
        filter_box.addWidget(btn_filter)

        filter_box.addStretch()
        layout.addWidget(filter_frame)

        # ── Expense Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Expense #", "Category", "Description",
            "Amount", "GST", "Total", "Payment Mode"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i in [0, 1, 2, 4, 5, 6, 7]:
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        # ── Bottom Actions ──
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("")
        self.lbl_total.setFont(theme_manager.get_font("subtitle", bold=True))
        bottom.addWidget(self.lbl_total)
        bottom.addStretch()

        btn_delete = QPushButton("Delete Selected")
        btn_delete.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_delete.setProperty("variant", "danger")
        btn_delete.clicked.connect(self.delete_selected)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)

    def load_data(self):
        """Loads expense data with filters."""
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

                total_val = exp['total_amount']
                total_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{total_val:,.2f}")
                total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                total_item.setFont(theme_manager.get_font("body", bold=True))
                self.table.setItem(row, 6, total_item)

                self.table.setItem(row, 7, QTableWidgetItem(exp.get("payment_mode", "")))
                self.table.item(row, 0).setData(Qt.UserRole, exp.get("id"))
                grand_total += total_val
        finally:
            self.table.setUpdatesEnabled(True)

        self.lbl_total.setText(f"Total: {CURRENCY_SYMBOL}{grand_total:,.2f}")
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
            ThemedMessageBox.warning(self, "No Selection", "Please select an expense entry to delete.")
            return
        exp_id = self.table.item(row, 0).data(Qt.UserRole)
        if not exp_id:
            return
        if ThemedMessageBox.question(
            self, "Confirm Delete",
            "Delete expense entry? This action cannot be undone."
        ):
            try:
                delete_expense(exp_id)
                self.load_data()
                ThemedMessageBox.information(self, "Deleted", "Expense entry deleted successfully.")
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))


class AddExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record New Expense")
        configure_dialog_window_flags(self, min_width=500, min_height=520)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Record New Expense")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
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

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Expense")
        btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        btn_save.setProperty("variant", "primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save_expense)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def save_expense(self):
        try:
            amount = float(self.inp_amount.text().strip() or 0)
            gst = float(self.inp_gst.text().strip() or 0)
            if amount <= 0:
                ThemedMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
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
            ThemedMessageBox.information(self, "Success", "Expense recorded successfully!")
            self.accept()
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", str(e))


class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Expense Categories")
        configure_dialog_window_flags(self, min_width=480, min_height=420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Expense Categories")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Category Name", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setVisible(False)
        self.load_categories()
        layout.addWidget(self.table)

        add_box = QHBoxLayout()
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("New category name...")
        add_box.addWidget(self.inp_name, 2)

        btn_add = QPushButton("Add")
        btn_add.setIcon(theme_manager.get_icon("plus", token_color="text_on_accent", size=16))
        btn_add.setProperty("variant", "primary")
        btn_add.clicked.connect(self.add_category)
        add_box.addWidget(btn_add)
        layout.addLayout(add_box)

        btn_close = QPushButton("Close")
        btn_close.setProperty("variant", "secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_categories(self):
        cats = get_all_categories(include_inactive=True)
        self.table.setRowCount(len(cats))
        for row, c in enumerate(cats):
            self.table.setItem(row, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(c.get("description", "") or "—"))

    def add_category(self):
        name = self.inp_name.text().strip()
        if not name:
            return
        try:
            create_category(name)
            self.inp_name.clear()
            self.load_categories()
        except Exception as e:
            ThemedMessageBox.warning(self, "Error", str(e))
