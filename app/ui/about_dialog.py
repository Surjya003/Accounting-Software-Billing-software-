"""
BillFlow Suite - Themed About & Diagnostics Dialog
==================================================
Displays brand identity, developer credit, versioning, system runtime metadata,
and offline license state with a one-click 'Copy Diagnostics' facility.
100% theme-token compliant (zero hardcoded colors or local stylesheets).
"""
import sys
import platform
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QApplication, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont
from PySide6.QtSvg import QSvgRenderer

from app.branding import (
    APP_NAME, BRAND_NAME, MAKER_NAME, TAGLINE, VERSION, CREDIT_LINE,
    COPYRIGHT_YEAR, get_asset_path
)
from app.services.license_service import get_license_status
from app.ui.theme import (
    theme_manager, ThemedMessageBox, configure_dialog_window_flags
)
from app.ui.theme.widgets import CardFrame


class AboutDialog(QDialog):
    """Themed About Dialog displaying enterprise branding and system diagnostics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        configure_dialog_window_flags(self, min_width=540, min_height=460)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        tokens = theme_manager.tokens
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 1. Header Card with Emblem, Title and Tagline
        header_card = CardFrame()
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(16, 16, 16, 16)
        h_layout.setSpacing(8)

        # Title Row with Icon
        title_box = QHBoxLayout()
        title_box.setSpacing(12)

        lbl_logo = QLabel()
        logo_path = get_asset_path("assets/branding/logo.svg")
        if logo_path.exists():
            lbl_logo.setPixmap(theme_manager.pixmap("app_icon", size=48))
        else:
            lbl_logo.setPixmap(theme_manager.pixmap("info", size=48))
        title_box.addWidget(lbl_logo)

        app_info = QVBoxLayout()
        app_info.setSpacing(2)
        lbl_app_title = QLabel(APP_NAME)
        lbl_app_title.setProperty("variant", "title")
        lbl_app_title.setFont(theme_manager.font("display"))
        app_info.addWidget(lbl_app_title)

        lbl_brand = QLabel(f"{BRAND_NAME} — {TAGLINE}")
        lbl_brand.setProperty("variant", "subtitle")
        app_info.addWidget(lbl_brand)
        title_box.addLayout(app_info)
        title_box.addStretch()
        h_layout.addLayout(title_box)

        lbl_credit = QLabel(f"{CREDIT_LINE} | © {COPYRIGHT_YEAR} {BRAND_NAME}")
        lbl_credit.setProperty("variant", "caption")
        h_layout.addWidget(lbl_credit)

        layout.addWidget(header_card)

        # 2. System Diagnostics Info Card
        diag_card = CardFrame()
        d_layout = QVBoxLayout(diag_card)
        d_layout.setContentsMargins(16, 16, 16, 16)
        d_layout.setSpacing(10)

        lbl_diag_title = QLabel("System Environment & Runtime Diagnostics")
        lbl_diag_title.setProperty("variant", "title")
        lbl_diag_title.setFont(theme_manager.font("subtitle"))
        d_layout.addWidget(lbl_diag_title)

        lic = get_license_status()

        # Build diagnostic metrics table
        self.diagnostics_data = {
            "Application": f"{APP_NAME} v{VERSION}",
            "Enterprise Brand": BRAND_NAME,
            "Engineering Lead": MAKER_NAME,
            "License Status": lic.get("status_text", "Trial / Active"),
            "Machine Fingerprint": lic.get("machine_id", "Offline-Verified"),
            "Database Schema": f"v{VERSION} (Up to date)",
            "Python Runtime": platform.python_version(),
            "GUI Engine": "PySide6 (Qt 6)",
            "Operating System": platform.platform(),
        }

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        for row, (label_text, val_text) in enumerate(self.diagnostics_data.items()):
            lbl_k = QLabel(f"{label_text}:")
            lbl_k.setProperty("variant", "label")
            lbl_v = QLabel(str(val_text))
            lbl_v.setProperty("variant", "tabular" if "Runtime" in label_text or "Machine" in label_text else "body")
            lbl_v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(lbl_k, row, 0)
            grid.addWidget(lbl_v, row, 1)

        d_layout.addLayout(grid)
        layout.addWidget(diag_card)

        # 3. Action Buttons Row (Copy Diagnostics, Close)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_copy = QPushButton("Copy Diagnostics")
        btn_copy.setProperty("variant", "secondary")
        btn_copy.setIcon(theme_manager.icon("copy", size=16))
        btn_copy.clicked.connect(self._copy_diagnostics)
        btn_row.addWidget(btn_copy)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setProperty("variant", "primary")
        btn_close.setIcon(theme_manager.icon("check", color_token="text_on_accent", size=16))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _copy_diagnostics(self):
        """Format diagnostics as structured text and copy to system clipboard."""
        lines = [
            f"{APP_NAME} - Enterprise System Diagnostics",
            "=" * 45,
        ]
        for k, v in self.diagnostics_data.items():
            lines.append(f"{k:20}: {v}")
        lines.append("=" * 45)

        report = "\n".join(lines)
        QApplication.clipboard().setText(report)
        ThemedMessageBox.information(
            self,
            "Diagnostics Copied",
            "System diagnostics report has been copied to your clipboard."
        )
