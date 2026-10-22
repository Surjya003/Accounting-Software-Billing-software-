"""
VyaparLedger Pro - Main Application Entry Point
"""
import sys
import os
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from app.core import setup_logging, install_crash_handler, get_logger
from app.database.connection import init_db
from app.services.sample_data import populate_sample_data
from app.services.license_service import (
    get_license_status, activate_license, get_machine_fingerprint
)
from app.ui.main_window import MainWindow
from app.config import APP_NAME, APP_VERSION


class LicenseGateDialog(QDialog):
    """Blocking dialog shown when trial has expired and no valid license exists."""

    def __init__(self, lic_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — License Activation Required")
        self.setMinimumSize(520, 380)
        self.setModal(True)
        self.activated = False
        self.lic_status = lic_status

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Status banner
        banner = QFrame()
        banner.setStyleSheet(
            "background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 14px;"
        )
        b_layout = QVBoxLayout(banner)
        lbl_title = QLabel(f"<b style='font-size:15px;color:#991B1B;'>⚠️ {lic_status['status_text']}</b>")
        lbl_title.setWordWrap(True)
        b_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Your free trial period has ended. Please enter a valid license key "
            "to continue using the software. Contact the vendor with your Machine ID "
            "to obtain a license key."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #7F1D1D; font-size: 12px;")
        b_layout.addWidget(lbl_desc)
        layout.addWidget(banner)

        # Machine ID display
        machine_id = lic_status["machine_id"]
        mid_box = QHBoxLayout()
        lbl_mid = QLabel(f"<b>Your Machine ID:</b> <code style='color:#0284C7;font-size:14px;'>{machine_id}</code>")
        lbl_mid.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mid_box.addWidget(lbl_mid)
        btn_copy = QPushButton("📋 Copy")
        btn_copy.setStyleSheet("padding: 4px 10px;")
        btn_copy.clicked.connect(lambda: [
            QApplication.clipboard().setText(machine_id),
            QMessageBox.information(self, "Copied", "Machine ID copied to clipboard!")
        ])
        mid_box.addWidget(btn_copy)
        mid_box.addStretch()
        layout.addLayout(mid_box)

        # Activation form
        form = QFrame()
        form.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px;")
        f_layout = QVBoxLayout(form)

        lbl_comp = QLabel("<b>Registered Company Name *</b>")
        f_layout.addWidget(lbl_comp)
        self.inp_comp = QLineEdit()
        self.inp_comp.setPlaceholderText("Exactly as provided by vendor")
        self.inp_comp.setStyleSheet("padding: 8px; font-size: 13px;")
        f_layout.addWidget(self.inp_comp)

        lbl_key = QLabel("<b>Activation Key *</b>")
        f_layout.addWidget(lbl_key)
        self.inp_key = QLineEdit()
        self.inp_key.setPlaceholderText("e.g. P-4B92-7E1A-88D1-9F2B")
        self.inp_key.setStyleSheet("padding: 8px; font-size: 13px;")
        f_layout.addWidget(self.inp_key)

        layout.addWidget(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_activate = QPushButton("⚡ Activate License")
        btn_activate.setStyleSheet(
            "background-color: #0284C7; color: white; padding: 10px 24px; "
            "font-size: 13px; font-weight: bold; border-radius: 6px;"
        )
        btn_activate.clicked.connect(self.try_activate)
        btn_box.addWidget(btn_activate)

        btn_exit = QPushButton("Exit Application")
        btn_exit.setStyleSheet("padding: 10px 16px;")
        btn_exit.clicked.connect(self.reject)
        btn_box.addWidget(btn_exit)
        btn_box.addStretch()

        layout.addLayout(btn_box)
        layout.addStretch()

    def try_activate(self):
        comp = self.inp_comp.text().strip()
        key = self.inp_key.text().strip()
        if not comp or not key:
            QMessageBox.warning(self, "Missing Fields", "Please fill in both Company Name and Activation Key.")
            return
        success, msg = activate_license(comp, key)
        if success:
            self.activated = True
            QMessageBox.information(self, "License Activated", "Commercial license activated successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Activation Failed", f"License verification failed:\n{msg}")


def run_app():
    # 0. Initialize Centralized Logging & Crash Protection
    setup_logging()
    install_crash_handler()
    logger = get_logger("main")
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)

    # 1. Initialize SQLite Database Schema
    try:
        init_db()
    except Exception as db_err:
        logger.exception("Failed to initialize database: %s", db_err)
        raise

    # 2. Setup Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Vyapar Software Solutions")
    
    # Clean default system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 3. License Gate Check
    lic = get_license_status()
    if not lic["is_licensed"] and not lic["is_trial"]:
        # Trial expired, no valid license — force activation dialog
        gate = LicenseGateDialog(lic)
        result = gate.exec()
        if result != QDialog.Accepted or not gate.activated:
            sys.exit(0)
    
    # 4. Launch Main Window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()

