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


from app.ui.theme import theme_manager, ThemedMessageBox, configure_dialog_window_flags

class LicenseGateDialog(QDialog):
    """Blocking dialog shown when trial has expired and no valid license exists."""

    def __init__(self, lic_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — License Activation Required")
        configure_dialog_window_flags(self, min_width=520, min_height=380)
        self.setModal(True)
        self.activated = False
        self.lic_status = lic_status

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        t = theme_manager.tokens

        # Status banner
        banner = QFrame()
        banner.setProperty("variant", "sunken")
        b_layout = QVBoxLayout(banner)
        lbl_title = QLabel(f"⚠️ {lic_status['status_text']}")
        lbl_title.setProperty("variant", "title")
        lbl_title.setWordWrap(True)
        b_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Your free trial period has ended. Please enter a valid license key "
            "to continue using the software. Contact the vendor with your Machine ID "
            "to obtain a license key."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setProperty("variant", "subtitle")
        b_layout.addWidget(lbl_desc)
        layout.addWidget(banner)

        # Machine ID display
        machine_id = lic_status["machine_id"]
        mid_box = QHBoxLayout()
        lbl_mid = QLabel(f"Your Machine ID: {machine_id}")
        lbl_mid.setProperty("variant", "tabular")
        lbl_mid.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mid_box.addWidget(lbl_mid)

        btn_copy = QPushButton("Copy")
        btn_copy.setProperty("variant", "secondary")
        btn_copy.setIcon(theme_manager.icon("copy", size=16))
        btn_copy.clicked.connect(lambda: [
            QApplication.clipboard().setText(machine_id),
            ThemedMessageBox.information(self, "Copied", "Machine ID copied to clipboard!")
        ])
        mid_box.addWidget(btn_copy)
        mid_box.addStretch()
        layout.addLayout(mid_box)

        # Activation form
        form = QFrame()
        form.setProperty("variant", "card")
        f_layout = QVBoxLayout(form)

        lbl_comp = QLabel("Registered Company Name *")
        lbl_comp.setProperty("variant", "label")
        f_layout.addWidget(lbl_comp)
        self.inp_comp = QLineEdit()
        self.inp_comp.setPlaceholderText("Exactly as provided by vendor")
        f_layout.addWidget(self.inp_comp)

        lbl_key = QLabel("Activation Key *")
        lbl_key.setProperty("variant", "label")
        f_layout.addWidget(lbl_key)
        self.inp_key = QLineEdit()
        self.inp_key.setPlaceholderText("e.g. P-4B92-7E1A-88D1-9F2B")
        f_layout.addWidget(self.inp_key)

        layout.addWidget(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_exit = QPushButton("Exit Application")
        btn_exit.setProperty("variant", "secondary")
        btn_exit.clicked.connect(self.reject)
        btn_box.addWidget(btn_exit)

        btn_activate = QPushButton("Activate License")
        btn_activate.setProperty("variant", "primary")
        btn_activate.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        btn_activate.clicked.connect(self.try_activate)
        btn_box.addWidget(btn_activate)

        layout.addLayout(btn_box)
        layout.addStretch()

    def try_activate(self):
        comp = self.inp_comp.text().strip()
        key = self.inp_key.text().strip()
        if not comp or not key:
            ThemedMessageBox.warning(self, "Missing Fields", "Please fill in both Company Name and Activation Key.")
            return
        success, msg = activate_license(comp, key)
        if success:
            self.activated = True
            ThemedMessageBox.information(self, "License Activated", "Commercial license activated successfully!")
            self.accept()
        else:
            ThemedMessageBox.critical(self, "Activation Failed", f"License verification failed:\n{msg}")


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

    # 2. Setup Qt Application & Theme System
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Vyapar Software Solutions")

    # Restore and apply enterprise theme
    theme_manager.restore_theme()

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

