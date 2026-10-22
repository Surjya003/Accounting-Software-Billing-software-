from datetime import date
from decimal import Decimal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QTextEdit,
    QMessageBox, QFrame, QAbstractItemView, QDateEdit
)
from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtGui import QColor, QFont

from app.services.party_service import (
    get_all_parties, get_party_by_id, create_party, update_party, delete_party,
    validate_gstin
)
from app.config import (
    PARTY_TYPES, PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH,
    BALANCE_DEBIT, BALANCE_CREDIT, INDIAN_STATES
)

class PartyDialog(QDialog):
    def __init__(self, party_id=None, parent=None):
        super().__init__(parent)
        self.party_id = party_id
        self.setWindowTitle("Edit Party" if party_id else "Add New Party Master")
        self.setMinimumWidth(540)
        self.init_ui()
        if party_id:
            self.load_party_data()
            
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. Shree Ganesh Hardware & Construction")
        form_layout.addRow("Party Name *:", self.inp_name)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(PARTY_TYPES)
        form_layout.addRow("Party Type *:", self.combo_type)
        
        self.inp_gstin = QLineEdit()
        self.inp_gstin.setPlaceholderText("15-digit GSTIN (e.g. 27ABCDE1234F1Z5)")
        self.inp_gstin.textChanged.connect(self._on_gstin_changed)
        form_layout.addRow("GSTIN:", self.inp_gstin)
        
        self.inp_pan = QLineEdit()
        self.inp_pan.setPlaceholderText("10-digit PAN")
        form_layout.addRow("PAN:", self.inp_pan)
        
        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("Mobile / Phone Number")
        form_layout.addRow("Phone / Mobile:", self.inp_phone)
        
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("Email Address")
        form_layout.addRow("Email:", self.inp_email)
        
        self.inp_contact = QLineEdit()
        self.inp_contact.setPlaceholderText("Contact Person Name")
        form_layout.addRow("Contact Person:", self.inp_contact)
        
        self.inp_address = QLineEdit()
        self.inp_address.setPlaceholderText("Shop / Office / Plot Address")
        form_layout.addRow("Address:", self.inp_address)
        
        self.inp_city = QLineEdit()
        self.inp_city.setPlaceholderText("City (e.g. Mumbai)")
        form_layout.addRow("City:", self.inp_city)
        
        self.combo_state = QComboBox()
        for code, st_name in INDIAN_STATES:
            self.combo_state.addItem(f"{code} - {st_name}", userData=(code, st_name))
        # Default to Maharashtra
        self.combo_state.setCurrentIndex(21)
        form_layout.addRow("State & Code:", self.combo_state)
        
        # Opening Balance Row (Amount, Type, As-of Date)
        op_layout = QHBoxLayout()
        self.spin_op_bal = QDoubleSpinBox()
        self.spin_op_bal.setMaximum(999999999.99)
        self.spin_op_bal.setDecimals(2)
        self.spin_op_bal.setPrefix("₹ ")
        
        self.combo_op_type = QComboBox()
        self.combo_op_type.addItem("Dr (Receivable - Party Owes You)", BALANCE_DEBIT)
        self.combo_op_type.addItem("Cr (Payable - You Owe Party)", BALANCE_CREDIT)
        
        self.dt_op_date = QDateEdit()
        self.dt_op_date.setCalendarPopup(True)
        self.dt_op_date.setDate(QDate.currentDate())
        self.dt_op_date.setDisplayFormat("dd-MM-yyyy")
        self.dt_op_date.setToolTip("As-of date of this opening balance (used for ageing analysis)")
        
        op_layout.addWidget(self.spin_op_bal, 2)
        op_layout.addWidget(self.combo_op_type, 3)
        op_layout.addWidget(self.dt_op_date, 2)
        form_layout.addRow("Opening Bal & Date:", op_layout)
        
        self.spin_credit_days = QSpinBox()
        self.spin_credit_days.setValue(30)
        self.spin_credit_days.setRange(0, 365)
        self.spin_credit_days.setSuffix(" Days")
        form_layout.addRow("Credit Period:", self.spin_credit_days)
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)
        self.txt_notes.setPlaceholderText("Additional remarks, bank account notes, etc.")
        form_layout.addRow("Notes:", self.txt_notes)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Save Party")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self.save_party)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

    def _on_gstin_changed(self, text):
        clean = text.strip().upper()
        if len(clean) >= 2 and clean[:2].isdigit():
            st_code = clean[:2]
            for i in range(self.combo_state.count()):
                data = self.combo_state.itemData(i)
                if data and data[0] == st_code:
                    self.combo_state.setCurrentIndex(i)
                    break
        if len(clean) >= 10:
            self.inp_pan.setText(clean[2:12])

    def load_party_data(self):
        p = get_party_by_id(self.party_id)
        if not p:
            return
        self.inp_name.setText(p.get("name", ""))
        idx = self.combo_type.findText(p.get("party_type", PARTY_TYPE_CUSTOMER))
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        self.inp_gstin.setText(p.get("gstin", "") or "")
        self.inp_pan.setText(p.get("pan", "") or "")
        self.inp_phone.setText(p.get("phone", "") or "")
        self.inp_email.setText(p.get("email", "") or "")
        self.inp_contact.setText(p.get("contact_person", "") or "")
        self.inp_address.setText(p.get("address", "") or "")
        self.inp_city.setText(p.get("city", "") or "")
        
        # Select state
        st_code = p.get("state_code", "27")
        for i in range(self.combo_state.count()):
            data = self.combo_state.itemData(i)
            if data and data[0] == st_code:
                self.combo_state.setCurrentIndex(i)
                break
                
        self.spin_op_bal.setValue(float(p.get("opening_balance", 0.0)))
        idx_type = self.combo_op_type.findData(p.get("opening_balance_type", BALANCE_DEBIT))
        if idx_type >= 0:
            self.combo_op_type.setCurrentIndex(idx_type)
        if p.get("opening_balance_date"):
            op_d = p["opening_balance_date"]
            if hasattr(op_d, "year"):
                self.dt_op_date.setDate(QDate(op_d.year, op_d.month, op_d.day))
        self.spin_credit_days.setValue(p.get("credit_period_days", 30))
        self.txt_notes.setPlainText(p.get("notes", "") or "")

    def save_party(self):
        name = self.inp_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Party Name is required.")
            return
            
        gstin = self.inp_gstin.text().strip().upper()
        if gstin and not validate_gstin(gstin):
            res = QMessageBox.question(
                self, "GSTIN Warning",
                "The entered GSTIN does not follow standard 15-digit Indian format.\nDo you want to save anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return
                
        st_data = self.combo_state.currentData()
        st_code, st_name = st_data if st_data else ("27", "Maharashtra")
        
        q_op_d = self.dt_op_date.date()
        op_date = date(q_op_d.year(), q_op_d.month(), q_op_d.day())
        
        data = {
            "name": name,
            "party_type": self.combo_type.currentText(),
            "gstin": gstin,
            "pan": self.inp_pan.text().strip().upper(),
            "phone": self.inp_phone.text().strip(),
            "email": self.inp_email.text().strip(),
            "contact_person": self.inp_contact.text().strip(),
            "address": self.inp_address.text().strip(),
            "city": self.inp_city.text().strip(),
            "state": st_name,
            "state_code": st_code,
            "opening_balance": Decimal(str(self.spin_op_bal.value())),
            "opening_balance_type": self.combo_op_type.currentData(),
            "opening_balance_date": op_date,
            "credit_period_days": self.spin_credit_days.value(),
            "notes": self.txt_notes.toPlainText().strip()
        }
        
        try:
            if self.party_id:
                update_party(self.party_id, data)
            else:
                create_party(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save party: {e}")


class PartyView(QWidget):
    navigate_to = Signal(str, dict)  # view_name, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # 1. Filter Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("Card")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(12, 8, 12, 8)
        t_layout.setSpacing(10)
        
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("🔍 Search by Name, Phone, GSTIN, Code, City...")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_parties)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        t_layout.addWidget(self.inp_search, 2)
        
        lbl_type = QLabel("Type:")
        t_layout.addWidget(lbl_type)
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.addItems(["All", PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH])
        self.combo_filter_type.currentIndexChanged.connect(self.load_parties)
        t_layout.addWidget(self.combo_filter_type, 1)
        
        t_layout.addStretch()
        
        btn_add = QPushButton("➕ Add New Party")
        btn_add.setObjectName("PrimaryBtn")
        btn_add.clicked.connect(self.open_add_dialog)
        t_layout.addWidget(btn_add)
        
        layout.addWidget(toolbar)
        
        # 2. Parties Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Code", "Party Name", "Type", "GSTIN", "Phone / City",
            "Opening Bal", "Current Balance (₹)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (0, 2, 3, 4, 5, 6, 7):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 135)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 125)
        self.table.setColumnWidth(6, 145)
        self.table.setColumnWidth(7, 180)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        
        layout.addWidget(self.table, 1)
        self.load_parties()

    def load_parties(self):
        p_type = self.combo_filter_type.currentText()
        query = self.inp_search.text().strip()
        parties = get_all_parties(party_type=p_type, search_query=query, active_only=True)
        
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(parties))
            for r_idx, p in enumerate(parties):
                it_code = QTableWidgetItem(p.get("code", "") or "")
                it_code.setData(Qt.UserRole, p["id"])
                
                it_name = QTableWidgetItem(p["name"])
                font = it_name.font()
                font.setBold(True)
                it_name.setFont(font)
                
                it_type = QTableWidgetItem(p["party_type"])
                it_gst = QTableWidgetItem(p.get("gstin", "") or "Unregistered")
                
                phone_city = f"{p.get('phone','') or '-'} / {p.get('city','') or '-'}"
                it_pc = QTableWidgetItem(phone_city)
                
                op_str = f"₹{p['opening_balance']:,.2f} {p['opening_balance_type']}"
                it_op = QTableWidgetItem(op_str)
                it_op.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                cur_bal = p["current_balance"]
                cur_type = p["current_balance_type"]
                it_cur = QTableWidgetItem(f"₹{cur_bal:,.2f} {cur_type}")
                it_cur.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it_cur.setFont(font)
                if cur_type == "Dr":
                    it_cur.setForeground(QColor("#0284C7"))  # Receivable
                else:
                    it_cur.setForeground(QColor("#D97706"))  # Payable
                    
                self.table.setItem(r_idx, 0, it_code)
                self.table.setItem(r_idx, 1, it_name)
                self.table.setItem(r_idx, 2, it_type)
                self.table.setItem(r_idx, 3, it_gst)
                self.table.setItem(r_idx, 4, it_pc)
                self.table.setItem(r_idx, 5, it_op)
                self.table.setItem(r_idx, 6, it_cur)
                
                # Action Buttons Widget
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(4)
                
                btn_led = QPushButton("Ledger")
                btn_led.setStyleSheet("padding: 3px 8px; font-size: 11px;")
                btn_led.clicked.connect(lambda _, pid=p["id"]: self.navigate_to.emit("ledger", {"party_id": pid}))
                act_layout.addWidget(btn_led)
                
                btn_edit = QPushButton("Edit")
                btn_edit.setStyleSheet("padding: 3px 8px; font-size: 11px;")
                btn_edit.clicked.connect(lambda _, pid=p["id"]: self.open_edit_dialog(pid))
                act_layout.addWidget(btn_edit)
                
                btn_del = QPushButton("Delete")
                btn_del.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #DC2626;")
                btn_del.clicked.connect(lambda _, pid=p["id"], pname=p["name"]: self.delete_party_action(pid, pname))
                act_layout.addWidget(btn_del)
                
                self.table.setCellWidget(r_idx, 7, act_widget)
        finally:
            self.table.setUpdatesEnabled(True)

    def open_add_dialog(self):
        dlg = PartyDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.load_parties()

    def open_edit_dialog(self, party_id):
        dlg = PartyDialog(party_id=party_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.load_parties()

    def delete_party_action(self, party_id: int, party_name: str):
        reply = QMessageBox.question(
            self,
            "Confirm Delete Party",
            f"Are you sure you want to delete {party_name}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        success, msg = delete_party(party_id)
        if success:
            QMessageBox.information(self, "Party Deleted", f"Party '{party_name}' deleted successfully.")
            self.load_parties()
        else:
            QMessageBox.warning(self, "Cannot Delete Party", msg)

    def _on_row_double_clicked(self, index):
        item = self.table.item(index.row(), 0)
        if item:
            pid = item.data(Qt.UserRole)
            self.navigate_to.emit("ledger", {"party_id": pid})
