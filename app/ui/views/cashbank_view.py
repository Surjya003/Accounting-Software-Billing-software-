"""
Cash & Bank Book View
Track cash-in-hand and bank account balances with receipt/payment/contra entries.
"""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QLineEdit, QDateEdit, QTextEdit, QFormLayout,
    QDialog, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont, QColor

from app.services.cashbank_service import (
    get_all_accounts, create_account, create_transaction,
    get_transactions, delete_transaction, get_account_ledger
)
from app.config import CURRENCY_SYMBOL
from app.ui.widgets.stat_card import StatCard
from app.ui.theme import theme_manager
from app.ui.theme.widgets import (
    PageHeaderWidget, CardFrame, ThemedMessageBox, configure_dialog_window_flags
)


class CashBankView(QWidget):
    navigate_to = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── Header ──
        self.header_widget = PageHeaderWidget(
            title="Cash & Bank Book",
            subtitle="Track cash-in-hand and bank balances with receipt, payment, and contra entries",
            action_text="Record Transaction",
            action_icon="plus",
            action_callback=self.open_add_transaction_dialog
        )

        btn_add_acc = QPushButton("Add Account")
        btn_add_acc.setIcon(theme_manager.get_icon("plus", size=16))
        btn_add_acc.setProperty("variant", "secondary")
        btn_add_acc.setFixedHeight(36)
        btn_add_acc.clicked.connect(self.open_add_account_dialog)
        self.header_widget.add_custom_action(btn_add_acc)

        layout.addWidget(self.header_widget)

        # ── KPI Cards (Account Balances) ──
        self.kpi_box = QHBoxLayout()
        self.kpi_box.setSpacing(12)
        self.card_cash = StatCard("Cash-in-Hand", f"{CURRENCY_SYMBOL}0.00", "Physical cash on hand", token_name="success")
        self.card_bank = StatCard("Total Bank Balance", f"{CURRENCY_SYMBOL}0.00", "All bank accounts", token_name="accent")
        self.card_total = StatCard("Combined Liquidity", f"{CURRENCY_SYMBOL}0.00", "Cash + Bank balance", token_name="info")
        self.card_txn_count = StatCard("Monthly Transactions", "0", "This month activity", token_name="text_primary")
        for card in [self.card_cash, self.card_bank, self.card_total, self.card_txn_count]:
            self.kpi_box.addWidget(card)
        layout.addLayout(self.kpi_box)

        # ── Tabs: Accounts Summary | Transactions ──
        self.tabs = QTabWidget()

        # Tab 1: Account Summary
        self.tab_accounts = QWidget()
        self.init_accounts_tab()
        self.tabs.addTab(self.tab_accounts, "Account Balances")

        # Tab 2: Transaction Ledger
        self.tab_transactions = QWidget()
        self.init_transactions_tab()
        self.tabs.addTab(self.tab_transactions, "Transaction Ledger")

        layout.addWidget(self.tabs, 1)

    def init_accounts_tab(self):
        layout = QVBoxLayout(self.tab_accounts)
        layout.setContentsMargins(8, 12, 8, 8)

        self.acc_table = QTableWidget()
        self.acc_table.setColumnCount(7)
        self.acc_table.setHorizontalHeaderLabels([
            "Account Name", "Type", "Bank", "Account No",
            "Opening Bal.", "Current Balance", "Total Receipts"
        ])
        self.acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            self.acc_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.acc_table.verticalHeader().setDefaultSectionSize(36)
        self.acc_table.verticalHeader().setVisible(False)
        self.acc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.acc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.acc_table)

    def init_transactions_tab(self):
        layout = QVBoxLayout(self.tab_transactions)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)

        # Filters
        filter_frame = CardFrame()
        filter_box = QHBoxLayout(filter_frame)
        filter_box.setContentsMargins(12, 8, 12, 8)
        filter_box.setSpacing(10)

        filter_box.addWidget(QLabel("Account:"))
        self.combo_acc = QComboBox()
        self.combo_acc.setMinimumWidth(180)
        filter_box.addWidget(self.combo_acc)

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

        btn_filter = QPushButton("Filter")
        btn_filter.setIcon(theme_manager.get_icon("refresh", size=16))
        btn_filter.setProperty("variant", "secondary")
        btn_filter.clicked.connect(self.load_transactions)
        filter_box.addWidget(btn_filter)

        filter_box.addStretch()
        layout.addWidget(filter_frame)

        # Transaction Table
        self.txn_table = QTableWidget()
        self.txn_table.setColumnCount(8)
        self.txn_table.setHorizontalHeaderLabels([
            "Date", "Account", "Type", "Description",
            "Receipt (In)", "Payment (Out)", "Running Bal.", "Reference"
        ])
        self.txn_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i in [0, 1, 2, 4, 5, 6, 7]:
            self.txn_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.txn_table.verticalHeader().setDefaultSectionSize(36)
        self.txn_table.verticalHeader().setVisible(False)
        self.txn_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.txn_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.txn_table, 1)

        # Bottom
        bottom = QHBoxLayout()
        self.lbl_summary = QLabel("")
        self.lbl_summary.setFont(theme_manager.get_font("body", bold=True))
        bottom.addWidget(self.lbl_summary)
        bottom.addStretch()

        btn_del = QPushButton("Delete Selected")
        btn_del.setIcon(theme_manager.get_icon("trash", token_color="danger", size=16))
        btn_del.setProperty("variant", "danger")
        btn_del.clicked.connect(self.delete_selected_txn)
        bottom.addWidget(btn_del)
        layout.addLayout(bottom)

    def load_data(self):
        """Loads all account data and transactions."""
        self._load_accounts()
        self._load_account_combo()
        self.load_transactions()
        self._update_kpis()

    def _load_accounts(self):
        accounts = get_all_accounts()
        self.acc_table.setUpdatesEnabled(False)
        try:
            self.acc_table.setRowCount(len(accounts))
            for row, acc in enumerate(accounts):
                self.acc_table.setItem(row, 0, QTableWidgetItem(acc["account_name"]))
                self.acc_table.setItem(row, 1, QTableWidgetItem(acc["account_type"]))
                self.acc_table.setItem(row, 2, QTableWidgetItem(acc.get("bank_name", "") or "—"))
                self.acc_table.setItem(row, 3, QTableWidgetItem(acc.get("account_number", "") or "—"))

                op_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{acc['opening_balance']:,.2f}")
                op_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.acc_table.setItem(row, 4, op_item)

                bal = acc['current_balance']
                bal_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{bal:,.2f}")
                bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                bal_item.setFont(theme_manager.get_font("body", bold=True))
                if bal >= 0:
                    bal_item.setForeground(theme_manager.qcolor("success"))
                else:
                    bal_item.setForeground(theme_manager.qcolor("danger"))
                self.acc_table.setItem(row, 5, bal_item)

                rec_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{acc['total_receipts']:,.2f}")
                rec_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.acc_table.setItem(row, 6, rec_item)
        finally:
            self.acc_table.setUpdatesEnabled(True)

    def _load_account_combo(self):
        prev_acc_id = self.combo_acc.currentData() if hasattr(self, 'combo_acc') and self.combo_acc.count() > 0 else None
        accounts = get_all_accounts()
        self.combo_acc.blockSignals(True)
        self.combo_acc.clear()
        self.combo_acc.addItem("All Accounts", None)
        found_idx = 0
        for idx, acc in enumerate(accounts, start=1):
            self.combo_acc.addItem(f"{acc['account_name']} ({acc['account_type']})", acc['id'])
            if acc['id'] == prev_acc_id:
                found_idx = idx
        self.combo_acc.setCurrentIndex(found_idx)
        self.combo_acc.blockSignals(False)

    def load_transactions(self):
        acc_id = self.combo_acc.currentData() if hasattr(self, 'combo_acc') else None
        start = self.date_from.date().toPython()
        end = self.date_to.date().toPython()

        self.txn_table.setUpdatesEnabled(False)
        try:
            if acc_id:
                ledger = get_account_ledger(acc_id, start, end)
                rows = ledger["transactions"]
                self.txn_table.setRowCount(len(rows))
                for row, txn in enumerate(rows):
                    d = txn.get("txn_date", "")
                    if hasattr(d, "strftime"):
                        d = d.strftime("%d-%m-%Y")
                    self.txn_table.setItem(row, 0, QTableWidgetItem(str(d)))
                    self.txn_table.setItem(row, 1, QTableWidgetItem(txn.get("account_name", "")))
                    self.txn_table.setItem(row, 2, QTableWidgetItem(txn.get("txn_type", "")))
                    self.txn_table.setItem(row, 3, QTableWidgetItem(txn.get("description", "")))

                    r_amt = txn['receipt_amount']
                    r_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{r_amt:,.2f}" if r_amt > 0 else "")
                    r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    r_item.setForeground(theme_manager.qcolor("success"))
                    self.txn_table.setItem(row, 4, r_item)

                    p_amt = txn['payment_amount']
                    p_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{p_amt:,.2f}" if p_amt > 0 else "")
                    p_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    p_item.setForeground(theme_manager.qcolor("danger"))
                    self.txn_table.setItem(row, 5, p_item)

                    bal_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{txn.get('running_balance', 0):,.2f}")
                    bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    bal_item.setFont(theme_manager.get_font("body", bold=True))
                    self.txn_table.setItem(row, 6, bal_item)

                    self.txn_table.setItem(row, 7, QTableWidgetItem(txn.get("reference_no", "") or "—"))
                    self.txn_table.item(row, 0).setData(Qt.UserRole, txn.get("id"))

                self.lbl_summary.setText(
                    f"Opening: {CURRENCY_SYMBOL}{ledger['opening_balance']:,.2f}  |  "
                    f"Receipts: {CURRENCY_SYMBOL}{ledger['total_receipts']:,.2f}  |  "
                    f"Payments: {CURRENCY_SYMBOL}{ledger['total_payments']:,.2f}  |  "
                    f"Closing: {CURRENCY_SYMBOL}{ledger['closing_balance']:,.2f}"
                )
            else:
                txns = get_transactions(start_date=start, end_date=end)
                self.txn_table.setRowCount(len(txns))
                total_r = total_p = 0.0
                for row, txn in enumerate(txns):
                    d = txn.get("txn_date", "")
                    if hasattr(d, "strftime"):
                        d = d.strftime("%d-%m-%Y")
                    self.txn_table.setItem(row, 0, QTableWidgetItem(str(d)))
                    self.txn_table.setItem(row, 1, QTableWidgetItem(txn.get("account_name", "")))
                    self.txn_table.setItem(row, 2, QTableWidgetItem(txn.get("txn_type", "")))
                    self.txn_table.setItem(row, 3, QTableWidgetItem(txn.get("description", "")))

                    r_amt = txn['receipt_amount']
                    r_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{r_amt:,.2f}" if r_amt > 0 else "")
                    r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    r_item.setForeground(theme_manager.qcolor("success"))
                    self.txn_table.setItem(row, 4, r_item)

                    p_amt = txn['payment_amount']
                    p_item = QTableWidgetItem(f"{CURRENCY_SYMBOL}{p_amt:,.2f}" if p_amt > 0 else "")
                    p_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    p_item.setForeground(theme_manager.qcolor("danger"))
                    self.txn_table.setItem(row, 5, p_item)

                    self.txn_table.setItem(row, 6, QTableWidgetItem("—"))
                    self.txn_table.setItem(row, 7, QTableWidgetItem(txn.get("reference_no", "") or "—"))
                    self.txn_table.item(row, 0).setData(Qt.UserRole, txn.get("id"))

                    total_r += txn['receipt_amount']
                    total_p += txn['payment_amount']

                self.lbl_summary.setText(
                    f"Total Receipts: {CURRENCY_SYMBOL}{total_r:,.2f}  |  "
                    f"Total Payments: {CURRENCY_SYMBOL}{total_p:,.2f}  |  "
                    f"Net: {CURRENCY_SYMBOL}{total_r - total_p:,.2f}"
                )
        finally:
            self.txn_table.setUpdatesEnabled(True)

    def _update_kpis(self):
        try:
            accounts = get_all_accounts()
            cash_total = sum(a['current_balance'] for a in accounts if a['account_type'] == 'Cash')
            bank_total = sum(a['current_balance'] for a in accounts if a['account_type'] == 'Bank')
            combined = cash_total + bank_total

            self.card_cash.set_value(f"{CURRENCY_SYMBOL}{cash_total:,.2f}")
            self.card_bank.set_value(f"{CURRENCY_SYMBOL}{bank_total:,.2f}")
            self.card_total.set_value(f"{CURRENCY_SYMBOL}{combined:,.2f}")

            start_m = date.today().replace(day=1)
            txns = get_transactions(start_date=start_m, end_date=date.today())
            self.card_txn_count.set_value(str(len(txns)))
        except Exception:
            pass

    def open_add_account_dialog(self):
        dlg = AddAccountDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def open_add_transaction_dialog(self):
        dlg = AddTransactionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def delete_selected_txn(self):
        row = self.txn_table.currentRow()
        if row < 0:
            ThemedMessageBox.warning(self, "No Selection", "Please select a transaction to delete.")
            return
        txn_id = self.txn_table.item(row, 0).data(Qt.UserRole)
        if not txn_id:
            return
        if ThemedMessageBox.question(
            self, "Confirm Delete",
            "Delete this transaction? This cannot be undone."
        ):
            try:
                delete_transaction(txn_id)
                self.load_data()
            except Exception as e:
                ThemedMessageBox.critical(self, "Error", str(e))


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Cash/Bank Account")
        configure_dialog_window_flags(self, min_width=500, min_height=420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Add New Cash/Bank Account")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. SBI Current A/C, Petty Cash")
        form.addRow("Account Name *:", self.inp_name)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Bank", "Cash"])
        form.addRow("Account Type:", self.combo_type)

        self.inp_bank = QLineEdit()
        self.inp_bank.setPlaceholderText("e.g. State Bank of India")
        form.addRow("Bank Name:", self.inp_bank)

        self.inp_ac_no = QLineEdit()
        self.inp_ac_no.setPlaceholderText("Account Number")
        form.addRow("Account Number:", self.inp_ac_no)

        self.inp_ifsc = QLineEdit()
        self.inp_ifsc.setPlaceholderText("e.g. SBIN0001234")
        form.addRow("IFSC Code:", self.inp_ifsc)

        self.inp_branch = QLineEdit()
        self.inp_branch.setPlaceholderText("Branch Name")
        form.addRow("Branch:", self.inp_branch)

        self.inp_opening = QLineEdit()
        self.inp_opening.setPlaceholderText("0.00")
        self.inp_opening.setText("0.00")
        form.addRow("Opening Balance (₹):", self.inp_opening)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Account")
        btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        btn_save.setProperty("variant", "primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save_account)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def save_account(self):
        try:
            data = {
                "account_name": self.inp_name.text().strip(),
                "account_type": self.combo_type.currentText(),
                "bank_name": self.inp_bank.text().strip(),
                "account_number": self.inp_ac_no.text().strip(),
                "ifsc_code": self.inp_ifsc.text().strip(),
                "branch": self.inp_branch.text().strip(),
                "opening_balance": float(self.inp_opening.text().strip() or 0),
            }
            create_account(data)
            ThemedMessageBox.information(self, "Success", "Account created successfully!")
            self.accept()
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", str(e))


class AddTransactionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Cash/Bank Transaction")
        configure_dialog_window_flags(self, min_width=520, min_height=480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Record Transaction")
        title.setFont(theme_manager.get_font("title", bold=True))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.combo_acc = QComboBox()
        accounts = get_all_accounts()
        for acc in accounts:
            self.combo_acc.addItem(f"{acc['account_name']} ({acc['account_type']})", acc['id'])
        form.addRow("Account *:", self.combo_acc)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        form.addRow("Date:", self.date_edit)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Receipt", "Payment", "Contra"])
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type *:", self.combo_type)

        self.lbl_contra = QLabel("Transfer With Account *:")
        self.combo_contra = QComboBox()
        for acc in accounts:
            self.combo_contra.addItem(f"{acc['account_name']} ({acc['account_type']})", acc['id'])
        form.addRow(self.lbl_contra, self.combo_contra)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("e.g. Payment from XYZ, Cash withdrawal")
        form.addRow("Description *:", self.inp_desc)

        self.inp_receipt = QLineEdit()
        self.inp_receipt.setPlaceholderText("0.00")
        form.addRow("Receipt Amount (₹):", self.inp_receipt)

        self.inp_payment = QLineEdit()
        self.inp_payment.setPlaceholderText("0.00")
        form.addRow("Payment Amount (₹):", self.inp_payment)

        self.inp_ref = QLineEdit()
        self.inp_ref.setPlaceholderText("Cheque No / UTR / UPI Ref")
        form.addRow("Reference:", self.inp_ref)

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

        btn_save = QPushButton("Save Transaction")
        btn_save.setIcon(theme_manager.get_icon("save", token_color="text_on_accent", size=16))
        btn_save.setProperty("variant", "primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save_transaction)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

        self._on_type_changed("Receipt")

    def _on_type_changed(self, txn_type):
        is_contra = (txn_type == "Contra")
        self.lbl_contra.setVisible(is_contra)
        self.combo_contra.setVisible(is_contra)
        self.inp_receipt.setEnabled(txn_type in ("Receipt", "Contra"))
        self.inp_payment.setEnabled(txn_type in ("Payment", "Contra"))
        if txn_type == "Receipt":
            self.inp_payment.setText("0.00")
        elif txn_type == "Payment":
            self.inp_receipt.setText("0.00")

    def save_transaction(self):
        try:
            is_contra = (self.combo_type.currentText() == "Contra")
            data = {
                "account_id": self.combo_acc.currentData(),
                "txn_date": self.date_edit.date().toPython(),
                "txn_type": self.combo_type.currentText(),
                "description": self.inp_desc.text().strip(),
                "receipt_amount": float(self.inp_receipt.text().strip() or 0),
                "payment_amount": float(self.inp_payment.text().strip() or 0),
                "reference_no": self.inp_ref.text().strip(),
                "contra_account_id": self.combo_contra.currentData() if is_contra else None,
                "notes": self.txt_notes.toPlainText().strip(),
            }
            create_transaction(data)
            ThemedMessageBox.information(self, "Success", "Transaction recorded!")
            self.accept()
        except Exception as e:
            ThemedMessageBox.critical(self, "Error", str(e))
