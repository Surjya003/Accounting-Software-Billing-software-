"""
BillFlow Suite - Main Application Entry Point
=============================================
Orchestrates enterprise startup pipeline with animated splash screen,
theme initialization, database migration integrity, offline license gating,
and graceful failure recovery.
"""
import sys
import os
from pathlib import Path
from typing import Optional

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from app.core import setup_logging, install_crash_handler, get_logger
from app.branding import APP_NAME, BRAND_NAME, MAKER_NAME, TAGLINE, VERSION
from app.ui.splash import SplashScreen, is_splash_enabled, is_reduce_motion_enabled
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
        from app.services.license_service import activate_license
        success, msg = activate_license(comp, key)
        if success:
            self.activated = True
            ThemedMessageBox.information(self, "License Activated", "Commercial license activated successfully!")
            self.accept()
        else:
            ThemedMessageBox.critical(self, "Activation Failed", f"License verification failed:\n{msg}")


# Standard startup pipeline steps with weights (total 100)
STARTUP_STEPS = [
    ("Starting application...", 5),
    ("Loading theme...", 10),
    ("Checking database...", 25),
    ("Applying updates...", 45),
    ("Loading company settings...", 60),
    ("Preparing modules...", 80),
    ("Opening workspace...", 95),
    ("Ready", 100),
]


def run_startup_pipeline(splash: Optional[SplashScreen] = None, custom_steps=None) -> QWidget:
    """
    Executes the real startup pipeline, updating splash progress and maintaining 60fps events.
    Returns the initialized MainWindow.
    """
    logger = get_logger("main")
    steps = custom_steps if custom_steps is not None else STARTUP_STEPS

    # Step 1: Starting application... (5%)
    if splash:
        splash.set_progress(5, "Starting application...")
    QApplication.processEvents()
    logger.info("Starting %s v%s", APP_NAME, VERSION)

    # Step 2: Loading theme... (10%)
    if splash:
        splash.set_progress(10, "Loading theme...")
    QApplication.processEvents()
    theme_manager.restore_theme()
    QApplication.processEvents()

    # Step 3: Checking database... (25%)
    if splash:
        splash.set_progress(25, "Checking database...")
    QApplication.processEvents()
    from app.config import DATA_DIR, DB_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QApplication.processEvents()

    # Step 4: Applying updates... (45%)
    if splash:
        splash.set_progress(45, "Applying updates...")
    QApplication.processEvents()
    from app.database.connection import init_db
    init_db()
    QApplication.processEvents()

    # Step 5: Loading company settings... (60%)
    if splash:
        splash.set_progress(60, "Loading company settings...")
    QApplication.processEvents()
    from app.services.license_service import get_license_status
    lic = get_license_status()
    QApplication.processEvents()

    # Step 6: Preparing modules... (80%)
    if splash:
        splash.set_progress(80, "Preparing modules...")
    QApplication.processEvents()
    from app.ui.main_window import MainWindow
    QApplication.processEvents()

    # Step 7: Opening workspace... (95%)
    if splash:
        splash.set_progress(95, "Opening workspace...")
    QApplication.processEvents()

    # Check license gate if trial expired
    if not lic.get("is_licensed") and not lic.get("is_trial"):
        if splash:
            splash.close_on_error()
        gate = LicenseGateDialog(lic)
        result = gate.exec()
        if result != QDialog.Accepted or not gate.activated:
            sys.exit(0)

    window = MainWindow()
    QApplication.processEvents()

    # Step 8: Ready (100%)
    if splash:
        splash.finish(window)
    else:
        window.show()

    return window


def run_app():
    """Main application lifecycle entry point."""
    # 0. Initialize Centralized Logging & Crash Protection
    setup_logging()
    install_crash_handler()
    logger = get_logger("main")

    # 1. Setup Qt Application
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Vyapar Software Solutions")

    # 2. Check and show splash immediately BEFORE slow work
    splash = None
    if is_splash_enabled():
        splash = SplashScreen()
        splash.show_splash()
        QApplication.processEvents()

    # 3. Run Startup Pipeline with comprehensive error handling
    try:
        window = run_startup_pipeline(splash=splash)
    except Exception as err:
        logger.exception("Application startup failed: %s", err)
        if splash:
            splash.close_on_error()
        ThemedMessageBox.critical(
            None,
            "Startup Failure",
            f"An error occurred while launching {APP_NAME}:\n\n{err}\n\nPlease consult the log file for details."
        )
        raise

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
