"""
Settings & Configuration View
Handles Company Profile, 1-Click SQLite Backups, Restore, Sample Data, and Hardware-Locked Offline Licensing.
"""
from pathlib import Path
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QTabWidget, QFrame,
    QFormLayout, QMessageBox, QFileDialog, QApplication, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.database.connection import get_session, create_backup, restore_backup
from app.database.models import CompanyProfile
from app.services.license_service import get_license_status, activate_license, get_machine_fingerprint
from app.services.sample_data import populate_sample_data, clear_all_business_data
from app.config import INDIAN_STATES, DB_PATH, BACKUP_DIR
from app.core.diagnostics import run_system_health_check, dump_thread_stacks, get_memory_usage_mb
from app.core.logger import LOG_DIR

class SettingsView(QWidget):
    profile_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Company Profile
        self.tab_company = QWidget()
        self.init_company_tab()
        self.tabs.addTab(self.tab_company, "🏢 Company Profile & Bank Details")
        
        # Tab 2: Database & Backup
        self.tab_backup = QWidget()
        self.init_backup_tab()
        self.tabs.addTab(self.tab_backup, "💾 Backup & Database Management")
        
        # Tab 3: Offline Licensing
        self.tab_license = QWidget()
        self.init_license_tab()
        self.tabs.addTab(self.tab_license, "🔑 Offline License & Activation")
        
        # Tab 4: System Diagnostics & Crash Logs
        self.tab_diagnostics = QWidget()
        self.init_diagnostics_tab()
        self.tabs.addTab(self.tab_diagnostics, "🩺 System Health & Crash Diagnostics")
        
        layout.addWidget(self.tabs)

    def init_company_tab(self):
        layout = QVBoxLayout(self.tab_company)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.inp_cname = QLineEdit()
        form_layout.addRow("Company Name *:", self.inp_cname)
        
        self.inp_cgstin = QLineEdit()
        form_layout.addRow("GSTIN:", self.inp_cgstin)
        
        self.inp_cpan = QLineEdit()
        form_layout.addRow("PAN:", self.inp_cpan)
        
        self.inp_cphone = QLineEdit()
        form_layout.addRow("Phone / Mobile:", self.inp_cphone)
        
        self.inp_cemail = QLineEdit()
        form_layout.addRow("Email:", self.inp_cemail)
        
        self.inp_caddr = QLineEdit()
        form_layout.addRow("Address:", self.inp_caddr)
        
        self.inp_ccity = QLineEdit()
        form_layout.addRow("City:", self.inp_ccity)
        
        self.combo_cstate = QComboBox()
        for code, st_name in INDIAN_STATES:
            self.combo_cstate.addItem(f"{code} - {st_name}", userData=(code, st_name))
        form_layout.addRow("State & Code:", self.combo_cstate)
        
        # Bank Details
        self.inp_bank_name = QLineEdit()
        form_layout.addRow("Bank Name:", self.inp_bank_name)
        
        self.inp_bank_ac = QLineEdit()
        form_layout.addRow("Bank A/C No:", self.inp_bank_ac)
        
        self.inp_bank_ifsc = QLineEdit()
        form_layout.addRow("Bank IFSC:", self.inp_bank_ifsc)
        
        self.inp_upi = QLineEdit()
        form_layout.addRow("UPI ID (for QR / Payments):", self.inp_upi)
        
        # Logo Picker Row
        logo_box = QHBoxLayout()
        self.lbl_logo_path = QLabel("No logo selected")
        self.lbl_logo_path.setStyleSheet("color: #64748B; font-size: 11px;")
        btn_browse_logo = QPushButton("📁 Browse Logo Image...")
        btn_browse_logo.clicked.connect(self.browse_logo)
        btn_clear_logo = QPushButton("❌ Clear Logo")
        btn_clear_logo.clicked.connect(lambda: [setattr(self, 'current_logo_path', None), self.lbl_logo_path.setText("No logo selected")])
        logo_box.addWidget(btn_browse_logo)
        logo_box.addWidget(btn_clear_logo)
        logo_box.addWidget(self.lbl_logo_path, 1)
        form_layout.addRow("Company Logo (Printouts):", logo_box)
        self.current_logo_path = None
        
        self.txt_terms = QTextEdit()
        self.txt_terms.setMaximumHeight(65)
        form_layout.addRow("Invoice Terms & Conditions:", self.txt_terms)
        
        layout.addLayout(form_layout)
        
        btn_save = QPushButton("💾 Save Company Profile")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setStyleSheet("padding: 8px 24px; font-size: 13px;")
        btn_save.clicked.connect(self.save_company_profile)
        layout.addWidget(btn_save, alignment=Qt.AlignRight)
        
        self.load_company_profile()

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_path:
            self.current_logo_path = file_path
            self.lbl_logo_path.setText(Path(file_path).name)

    def load_company_profile(self):
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if comp:
                self.inp_cname.setText(comp.name or "")
                self.inp_cgstin.setText(comp.gstin or "")
                self.inp_cpan.setText(comp.pan or "")
                self.inp_cphone.setText(comp.phone or "")
                self.inp_cemail.setText(comp.email or "")
                self.inp_caddr.setText(comp.address or "")
                self.inp_ccity.setText(comp.city or "")
                
                st_code = comp.state_code or "27"
                for i in range(self.combo_cstate.count()):
                    data = self.combo_cstate.itemData(i)
                    if data and data[0] == st_code:
                        self.combo_cstate.setCurrentIndex(i)
                        break
                        
                self.inp_bank_name.setText(comp.bank_name or "")
                self.inp_bank_ac.setText(comp.bank_account_no or "")
                self.inp_bank_ifsc.setText(comp.bank_ifsc or "")
                self.inp_upi.setText(comp.upi_id or "")
                self.txt_terms.setPlainText(comp.terms_conditions or "")
                
                if comp.logo_path and Path(comp.logo_path).exists():
                    self.current_logo_path = comp.logo_path
                    self.lbl_logo_path.setText(Path(comp.logo_path).name)
                else:
                    self.current_logo_path = None
                    self.lbl_logo_path.setText("No logo selected")

    def save_company_profile(self):
        st_data = self.combo_cstate.currentData()
        st_code, st_name = st_data if st_data else ("27", "Maharashtra")
        
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if not comp:
                comp = CompanyProfile()
                session.add(comp)
                
            comp.name = self.inp_cname.text().strip()
            comp.gstin = self.inp_cgstin.text().strip().upper()
            comp.pan = self.inp_cpan.text().strip().upper()
            comp.phone = self.inp_cphone.text().strip()
            comp.email = self.inp_cemail.text().strip()
            comp.address = self.inp_caddr.text().strip()
            comp.city = self.inp_ccity.text().strip()
            comp.state = st_name
            comp.state_code = st_code
            comp.bank_name = self.inp_bank_name.text().strip()
            comp.bank_account_no = self.inp_bank_ac.text().strip()
            comp.bank_ifsc = self.inp_bank_ifsc.text().strip().upper()
            comp.upi_id = self.inp_upi.text().strip()
            comp.logo_path = self.current_logo_path
            comp.terms_conditions = self.txt_terms.toPlainText().strip()
            session.commit()
            
        QMessageBox.information(self, "Success", "Company profile saved successfully!")
        self.profile_updated.emit()

    def init_backup_tab(self):
        layout = QVBoxLayout(self.tab_backup)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)
        
        # Info Card
        info_card = QFrame()
        info_card.setObjectName("Card")
        ic_layout = QVBoxLayout(info_card)
        
        db_size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
        lbl_info = QLabel(
            f"<b>Database Location:</b> {DB_PATH}<br/>"
            f"<b>Database Engine:</b> SQLite 3 with WAL Mode (Zero Server Dependency)<br/>"
            f"<b>Current DB Size:</b> {db_size_kb:,.1f} KB<br/>"
            f"<b>Backup Directory:</b> {BACKUP_DIR}"
        )
        lbl_info.setStyleSheet("font-size: 13px; color: #1E293B;")
        ic_layout.addWidget(lbl_info)
        layout.addWidget(info_card)
        
        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        
        btn_create_backup = QPushButton("📦 Create Instant Backup Now")
        btn_create_backup.setObjectName("PrimaryBtn")
        btn_create_backup.setStyleSheet("padding: 10px 16px;")
        btn_create_backup.clicked.connect(self.handle_backup)
        btn_box.addWidget(btn_create_backup)
        
        btn_restore = QPushButton("🔄 Restore Database from Backup File")
        btn_restore.setStyleSheet("padding: 10px 16px;")
        btn_restore.clicked.connect(self.handle_restore)
        btn_box.addWidget(btn_restore)
        
        btn_sample = QPushButton("🌱 Seed / Reset Sample Demo Data")
        btn_sample.setObjectName("WarningBtn")
        btn_sample.setStyleSheet("padding: 10px 16px;")
        btn_sample.clicked.connect(self.handle_sample_data)
        btn_box.addWidget(btn_sample)
        
        btn_clear = QPushButton("🗑️ Clear / Wipe All Data")
        btn_clear.setObjectName("DestructiveBtn")
        btn_clear.setStyleSheet("padding: 10px 16px; background-color: #8B2635; color: white;")
        btn_clear.clicked.connect(self.handle_clear_data)
        btn_box.addWidget(btn_clear)
        
        layout.addLayout(btn_box)
        layout.addStretch()

    def handle_backup(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Backup Destination Folder",
            str(BACKUP_DIR)
        )
        if not folder:
            return  # User cancelled
        try:
            b_path = create_backup(custom_dest_dir=Path(folder))
            QMessageBox.information(self, "Backup Successful", f"Full database backup created at:\n{b_path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Error creating backup: {e}")

    def handle_restore(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File to Restore",
            str(BACKUP_DIR), "SQLite DB Files (*.db *.sqlite);;All Files (*.*)"
        )
        if not file_path:
            return
            
        res = QMessageBox.warning(
            self, "Confirm Restore",
            "Restoring will overwrite your current active database with the selected backup.\nDo you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            try:
                restore_backup(Path(file_path))
                QMessageBox.information(self, "Restored", "Database restored successfully! Please restart application to ensure cached states are refreshed.")
            except Exception as e:
                QMessageBox.critical(self, "Restore Error", f"Failed to restore: {e}")

    def handle_sample_data(self):
        res = QMessageBox.question(
            self, "Seed Demo Data",
            "This will reset all party masters and transactions with sample B2B trading data for demonstration.\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            try:
                populate_sample_data(force=True)
                QMessageBox.information(self, "Sample Data Populated", "Sample trading parties and transactions generated successfully!")
                self.profile_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to populate sample data: {e}")

    def handle_clear_data(self):
        res = QMessageBox.warning(
            self, "Confirm Wipe All Data",
            "This will permanently delete ALL parties, products, vouchers, invoices, quotations, POs, expenses, and transactions from the database.\n\n"
            "This action cannot be undone. Do you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if res == QMessageBox.Yes:
            try:
                clear_all_business_data()
                QMessageBox.information(self, "Data Wiped Clean", "All dummy and business records have been permanently cleared. The database is now ready for your real data.")
                self.load_company_profile()
                self.profile_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear data: {e}")

    def init_license_tab(self):
        layout = QVBoxLayout(self.tab_license)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        
        lic = get_license_status()
        
        # Status Card
        stat_card = QFrame()
        stat_card.setObjectName("Card")
        sc_layout = QVBoxLayout(stat_card)
        
        bg_col = "#ECFDF5" if lic["is_licensed"] else "#FFFBEB"
        border_col = "#A7F3D0" if lic["is_licensed"] else "#FDE68A"
        stat_card.setStyleSheet(f"#Card {{ background-color: {bg_col}; border: 1px solid {border_col}; }}")
        
        self.lbl_lic_status = QLabel(
            f"<b>License Status:</b> {lic['status_text']}<br/>"
            f"<b>Machine Hardware ID:</b> <code>{lic['machine_id']}</code><br/>"
            f"<b>Licensed To:</b> {lic.get('issued_to') or 'Unregistered / Evaluation Mode'}"
        )
        self.lbl_lic_status.setStyleSheet("font-size: 13px; color: #0F172A;")
        sc_layout.addWidget(self.lbl_lic_status)
        layout.addWidget(stat_card)
        
        # Activation Form
        form_frame = QFrame()
        form_frame.setObjectName("Card")
        f_layout = QFormLayout(form_frame)
        f_layout.setSpacing(10)
        
        # Copy Machine ID button
        m_box = QHBoxLayout()
        self.lbl_m_val = QLabel(lic["machine_id"])
        self.lbl_m_val.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #0284C7;")
        btn_copy_m = QPushButton("📋 Copy Machine ID")
        btn_copy_m.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_copy_m.clicked.connect(lambda: [QApplication.clipboard().setText(lic["machine_id"]), QMessageBox.information(self, "Copied", "Machine ID copied to clipboard!")])
        m_box.addWidget(self.lbl_m_val)
        m_box.addWidget(btn_copy_m)
        m_box.addStretch()
        f_layout.addRow("Your Machine ID:", m_box)
        
        self.inp_lic_comp = QLineEdit()
        self.inp_lic_comp.setPlaceholderText("Enter Registered Company Name exactly as provided by vendor")
        f_layout.addRow("Registered Company *:", self.inp_lic_comp)
        
        self.inp_lic_key = QLineEdit()
        self.inp_lic_key.setPlaceholderText("e.g. P-4B92-7E1A-88D1-9F2B")
        f_layout.addRow("Activation Key *:", self.inp_lic_key)
        
        layout.addWidget(form_frame)
        
        btn_activate = QPushButton("⚡ Activate Commercial License")
        btn_activate.setObjectName("PrimaryBtn")
        btn_activate.setStyleSheet("padding: 8px 24px; font-size: 13px;")
        btn_activate.clicked.connect(self.handle_activation)
        layout.addWidget(btn_activate, alignment=Qt.AlignRight)
        
        layout.addStretch()

    def handle_activation(self):
        cname = self.inp_lic_comp.text().strip()
        key = self.inp_lic_key.text().strip()
        if not cname or not key:
            QMessageBox.warning(self, "Validation Error", "Please provide Company Name and Activation Key.")
            return
            
        success, msg = activate_license(cname, key)
        if success:
            QMessageBox.information(self, "License Activated", "Congratulations! Your commercial license has been activated successfully on this PC.")
            # Reload license tab
            lic = get_license_status()
            self.lbl_lic_status.setText(
                f"<b>License Status:</b> {lic['status_text']}<br/>"
                f"<b>Machine Hardware ID:</b> <code>{lic['machine_id']}</code><br/>"
                f"<b>Licensed To:</b> {lic.get('issued_to')}"
            )
        else:
            QMessageBox.critical(self, "Activation Failed", f"License key verification failed:\n{msg}")

    def init_diagnostics_tab(self):
        layout = QVBoxLayout(self.tab_diagnostics)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. Health Status Card
        self.health_card = QFrame()
        self.health_card.setObjectName("Card")
        hc_layout = QVBoxLayout(self.health_card)
        self.lbl_health_info = QLabel("Click 'Run Health Check' to inspect system memory, threads, and SQLite latency.")
        self.lbl_health_info.setStyleSheet("font-size: 13px; line-height: 1.5; color: #1E293B;")
        hc_layout.addWidget(self.lbl_health_info)
        layout.addWidget(self.health_card)

        # 2. Action buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_run_check = QPushButton("🩺 Run Live Health Check")
        btn_run_check.setObjectName("PrimaryBtn")
        btn_run_check.setStyleSheet("padding: 8px 16px;")
        btn_run_check.clicked.connect(self.run_health_check_ui)
        btn_box.addWidget(btn_run_check)

        btn_thread_dump = QPushButton("🧵 Generate Thread Dump")
        btn_thread_dump.setStyleSheet("padding: 8px 16px;")
        btn_thread_dump.clicked.connect(self.generate_thread_dump_ui)
        btn_box.addWidget(btn_thread_dump)

        btn_open_logs = QPushButton("📁 Open Logs Folder")
        btn_open_logs.setStyleSheet("padding: 8px 16px;")
        btn_open_logs.clicked.connect(self.open_logs_folder_ui)
        btn_box.addWidget(btn_open_logs)

        btn_box.addStretch()
        layout.addLayout(btn_box)

        # 3. Log Viewer Section
        viewer_frame = QFrame()
        viewer_frame.setObjectName("Card")
        vf_layout = QVBoxLayout(viewer_frame)
        vf_layout.setContentsMargins(10, 10, 10, 10)
        vf_layout.setSpacing(8)

        v_top = QHBoxLayout()
        v_top.addWidget(QLabel("<b>Log File:</b>"))
        self.combo_log_file = QComboBox()
        self.combo_log_file.addItems(["app.log (Application Event Log)", "crash.log (Fatal Crash Traces)", "thread_dump.log (Thread Stack Traces)"])
        self.combo_log_file.currentIndexChanged.connect(self.refresh_log_viewer_ui)
        v_top.addWidget(self.combo_log_file)

        btn_refresh_log = QPushButton("🔄 Refresh Log")
        btn_refresh_log.clicked.connect(self.refresh_log_viewer_ui)
        v_top.addWidget(btn_refresh_log)

        v_top.addStretch()
        vf_layout.addLayout(v_top)

        self.txt_log_content = QPlainTextEdit()
        self.txt_log_content.setReadOnly(True)
        self.txt_log_content.setFont(QFont("Consolas", 9))
        self.txt_log_content.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border-radius: 4px; padding: 6px;")
        vf_layout.addWidget(self.txt_log_content, 1)

        layout.addWidget(viewer_frame, 1)

        # Run health check initially
        self.run_health_check_ui()

    def run_health_check_ui(self):
        report = run_system_health_check()
        db = report.get("db", {})
        status_col = "#2F6844" if report["status"] == "HEALTHY" else "#8B2635"
        warn_html = "<br/>".join(f"• {w}" for w in report.get("warnings", [])) if report.get("warnings") else "None (Optimal)"
        
        self.lbl_health_info.setText(
            f"<b>Status:</b> <span style='color: {status_col}; font-weight:bold;'>{report['status']}</span> | "
            f"<b>PID:</b> {report['pid']} | "
            f"<b>Python:</b> {report['python_version']} ({report['platform']})<br/>"
            f"<b>Process RAM:</b> {report['memory_mb']} MB | "
            f"<b>Active Threads:</b> {report['active_threads']} | "
            f"<b>App Log Size:</b> {report.get('log_file_size_kb', 0)} KB<br/>"
            f"<b>SQLite Mode:</b> {db.get('journal_mode', 'N/A')} | "
            f"<b>Busy Timeout:</b> {db.get('busy_timeout_ms', 'N/A')} ms | "
            f"<b>Integrity:</b> {db.get('integrity', 'N/A')} | "
            f"<b>Query Latency:</b> {db.get('latency_ms', 'N/A')} ms<br/>"
            f"<b>Warnings:</b> {warn_html}"
        )
        self.refresh_log_viewer_ui()

    def generate_thread_dump_ui(self):
        dump_text = dump_thread_stacks()
        QMessageBox.information(
            self, "Thread Dump Saved",
            f"A snapshot of all running thread stack traces was captured and saved to:\n{LOG_DIR / 'thread_dump.log'}"
        )
        # Switch combo to thread_dump.log and display it
        self.combo_log_file.setCurrentIndex(2)
        self.refresh_log_viewer_ui()

    def open_logs_folder_ui(self):
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(LOG_DIR))
        except Exception as e:
            QMessageBox.warning(self, "Open Folder Error", f"Could not open logs folder: {e}")

    def refresh_log_viewer_ui(self):
        idx = self.combo_log_file.currentIndex()
        filenames = ["app.log", "crash.log", "thread_dump.log"]
        fname = filenames[idx] if 0 <= idx < len(filenames) else "app.log"
        target_path = LOG_DIR / fname

        if not target_path.exists():
            self.txt_log_content.setPlainText(f"File {fname} does not exist yet. No events recorded.")
            return

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                # Show last 200 lines to prevent memory lag
                tail = lines[-200:] if len(lines) > 200 else lines
                self.txt_log_content.setPlainText("".join(tail))
                self.txt_log_content.verticalScrollBar().setValue(
                    self.txt_log_content.verticalScrollBar().maximum()
                )
        except Exception as e:
            self.txt_log_content.setPlainText(f"Failed to read {fname}: {e}")

