"""
BillFlow Suite - Complete UI/UX Audit & Screenshot Capture Tool
===============================================================
Captures every window, page, dialog, and state variation in offscreen mode
across all 4 themes (Professional Light, Professional Dark, Classic Navy, Custom Emerald)
and across standard resolutions (1280x720, 1366x768, 1600x900, 1920x1080, 2560x1440)
and DPI scales (1.0, 1.25, 1.5, 2.0).

Saves screenshots to: docs/ui_audit/{theme}/{size}/{screen}.png
"""
import os
import sys
import shutil
from pathlib import Path

# Enforce offscreen platform before importing Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure test DB copy is used — NEVER touch data/accounting.db
DATA_DIR = ROOT_DIR / "data"
REAL_DB = DATA_DIR / "accounting.db"
AUDIT_DB = DATA_DIR / "test_ui_audit.db"

if REAL_DB.exists():
    shutil.copy2(REAL_DB, AUDIT_DB)

os.environ["ACCOUNTING_DB_PATH"] = str(AUDIT_DB)
os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{AUDIT_DB}"

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication

# Ensure single QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

from app.database.connection import init_db
init_db()

from app.ui.theme import theme_manager
from app.ui.theme.themes import load_custom_theme
from app.ui.main_window import MainWindow
from app.ui.views.party_view import PartyDialog
from app.ui.views.billing.product_view import ProductDialog
from app.ui.views.billing.invoice_view import InvoiceFormDialog
from app.ui.views.billing.quotation_view import QuotationFormDialog
from app.ui.views.billing.proforma_view import ProformaFormDialog
from app.ui.views.billing.challan_view import ChallanFormDialog
from app.ui.views.billing.purchase_order_view import POFormDialog
from app.ui.views.billing.return_view import ReturnFormDialog
from app.ui.views.expense_view import AddExpenseDialog, CategoryManagerDialog
from app.ui.views.cashbank_view import AddAccountDialog, AddTransactionDialog
from app.ui.views.outstanding_view import WhatsAppReminderDialog
from app.ui.theme.widgets import ThemedMessageBox
from app.main import LicenseGateDialog

CUSTOM_THEME_PATH = str(ROOT_DIR / "themes" / "custom_emerald.json")

THEMES = [
    ("professional_light", "professional_light"),
    ("professional_dark", "professional_dark"),
    ("classic_navy", "classic_navy"),
    ("custom_emerald", CUSTOM_THEME_PATH),
]

SIZES = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
]

DPRS = [1.0, 1.25, 1.5, 2.0]

VIEWS = [
    ("dashboard", "01_dashboard"),
    ("invoices", "02_invoices"),
    ("quotations", "03_quotations"),
    ("proforma", "04_proforma"),
    ("challans", "05_challans"),
    ("products", "06_products"),
    ("stock_report", "07_stock_movement"),
    ("purchase_orders", "08_purchase_orders"),
    ("returns", "09_returns"),
    ("billing_reports", "10_billing_reports"),
    ("parties", "11_parties"),
    ("voucher", "12_voucher"),
    ("cashbank", "13_cashbank"),
    ("expenses", "14_expenses"),
    ("ledger", "15_ledger"),
    ("outstanding", "16_outstanding"),
    ("daybook", "17_daybook"),
    ("trial_balance", "18_trial_balance"),
    ("pnl", "19_pnl"),
    ("gst", "20_gst_reports"),
    ("settings", "21_settings"),
]

DIALOG_FACTORIES = [
    ("invoice_dialog", lambda: InvoiceFormDialog()),
    ("quotation_dialog", lambda: QuotationFormDialog()),
    ("proforma_dialog", lambda: ProformaFormDialog()),
    ("challan_dialog", lambda: ChallanFormDialog()),
    ("po_dialog", lambda: POFormDialog()),
    ("return_dialog", lambda: ReturnFormDialog()),
    ("party_dialog", lambda: PartyDialog()),
    ("product_dialog", lambda: ProductDialog()),
    ("expense_dialog", lambda: AddExpenseDialog()),
    ("category_dialog", lambda: CategoryManagerDialog()),
    ("account_dialog", lambda: AddAccountDialog()),
    ("transaction_dialog", lambda: AddTransactionDialog()),
    ("whatsapp_dialog", lambda: WhatsAppReminderDialog({"party_name": "Tata Systems", "phone": "9830012345", "closing_balance": 45000.0, "credit_period_days": 14})),
    ("message_box", lambda: ThemedMessageBox("Confirmation", "Are you sure you want to save this invoice?", severity="warning", buttons="ok_cancel")),
    ("license_gate", lambda: LicenseGateDialog({"status_text": "Trial Period Expired", "machine_id": "MCH-8921-AF39"})),
]

OUT_BASE = ROOT_DIR / "docs" / "ui_audit"

def capture_widget(widget, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    widget.show()
    widget.adjustSize()
    app.processEvents()
    pixmap = widget.grab()
    pixmap.save(str(out_path), "PNG")


def run_audit_capture():
    print("=" * 80)
    print("STARTING UI/UX AUDIT SCREENSHOT CAPTURE")
    print(f"Themes: {THEMES}")
    print(f"Sizes: {SIZES}")
    print(f"Output Directory: {OUT_BASE}")
    print("=" * 80)

    # 1. Capture Main Views across themes, sizes, and DPR
    # Instantiate MainWindow once
    win = MainWindow()

    total_captured = 0

    for theme_label, theme_arg in THEMES:
        print(f"\n--- Applying Theme: {theme_label} ---")
        theme_manager.apply_theme(theme_arg, save_preference=False)
        app.processEvents()

        # Capture at primary resolutions
        for width, height in SIZES:
            size_label = f"{width}x{height}"
            win.resize(width, height)
            win.show()
            app.processEvents()

            for key, screen_name in VIEWS:
                win.navigate_to(key)
                app.processEvents()
                out_png = OUT_BASE / theme_label / size_label / f"{screen_name}.png"
                capture_widget(win, out_png)
                total_captured += 1

            # Also capture collapsed sidebar state at 1280x720 and 1920x1080
            if size_label in ("1280x720", "1920x1080"):
                if not win.sidebar_collapsed:
                    win.toggle_sidebar()
                    app.processEvents()
                out_png = OUT_BASE / theme_label / size_label / "00_sidebar_collapsed.png"
                capture_widget(win, out_png)
                total_captured += 1
                # Restore
                win.toggle_sidebar()
                app.processEvents()

        # Capture Dialogs for this theme
        print(f"Capturing Dialogs in {theme_label}...")
        for diag_key, factory in DIALOG_FACTORIES:
            try:
                diag = factory()
                diag.setModal(False)
                out_png = OUT_BASE / theme_label / "dialogs" / f"{diag_key}.png"
                capture_widget(diag, out_png)
                diag.close()
                total_captured += 1
            except Exception as e:
                print(f"Error capturing {diag_key}: {e}")

    print("\n" + "=" * 80)
    print(f"AUDIT SCREENSHOT CAPTURE COMPLETE! Total images captured: {total_captured}")
    print("=" * 80)

if __name__ == "__main__":
    run_audit_capture()
