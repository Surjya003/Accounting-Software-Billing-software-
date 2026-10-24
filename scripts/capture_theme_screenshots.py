"""
Offscreen Visual Verification & Screenshot Capture Tool
Renders and grabs high-resolution screenshots of EVERY page and EVERY dialog
across all themes ("professional_light", "professional_dark", "classic_navy")
at both 1366x768 (min supported) and 1920x1080 (HD desktop) into docs/theme_screenshots/
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Force offscreen headless rendering
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize, QTimer

from app.ui.theme.theme_manager import theme_manager
from app.ui.main_window import MainWindow
from app.ui.views.party_view import PartyDialog
from app.ui.views.billing.invoice_view import InvoiceFormDialog
from app.ui.views.billing.quotation_view import QuotationFormDialog
from app.ui.views.billing.proforma_view import ProformaFormDialog
from app.ui.views.billing.challan_view import ChallanFormDialog
from app.ui.views.billing.purchase_order_view import POFormDialog
from app.ui.views.billing.return_view import ReturnFormDialog
from app.ui.views.billing.product_view import ProductDialog
from app.ui.views.cashbank_view import AddAccountDialog, AddTransactionDialog
from app.ui.views.expense_view import AddExpenseDialog, CategoryManagerDialog


def capture_all():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    base_out = Path("docs/theme_screenshots")
    base_out.mkdir(parents=True, exist_ok=True)

    themes = ["professional_light", "professional_dark", "classic_navy"]
    resolutions = [
        (1366, 768),
        (1920, 1080)
    ]

    page_names = [
        "01_dashboard",
        "02_parties",
        "03_voucher_entry",
        "04_party_ledger",
        "05_outstanding_dues",
        "06_daybook",
        "07_trial_balance",
        "08_gst_reports",
        "09_settings_appearance",
        "10_invoices",
        "11_quotations",
        "12_proforma",
        "13_challans",
        "14_products_inventory",
        "15_purchase_orders",
        "16_returns",
        "17_billing_reports",
        "18_expenses",
        "19_cash_bank",
        "20_profit_loss",
        "21_stock_report"
    ]

    dialog_constructors = [
        ("dialog_party", PartyDialog),
        ("dialog_invoice", InvoiceFormDialog),
        ("dialog_quotation", QuotationFormDialog),
        ("dialog_proforma", ProformaFormDialog),
        ("dialog_challan", ChallanFormDialog),
        ("dialog_purchase_order", POFormDialog),
        ("dialog_return", ReturnFormDialog),
        ("dialog_product", ProductDialog),
        ("dialog_cashbank_account", AddAccountDialog),
        ("dialog_cashbank_txn", AddTransactionDialog),
        ("dialog_expense", AddExpenseDialog),
        ("dialog_category_manager", CategoryManagerDialog),
    ]

    total_captured = 0

    for theme_key in themes:
        theme_manager.apply_theme(theme_key, save_preference=False)
        app.processEvents()

        for w, h in resolutions:
            theme_dir = base_out / theme_key / f"{w}x{h}"
            theme_dir.mkdir(parents=True, exist_ok=True)

            print(f"--- Capturing {theme_key} at {w}x{h} ---")

            # 1. Main Window Pages
            main_win = MainWindow()
            main_win.resize(w, h)
            main_win.show()
            app.processEvents()

            # Iterate stack views
            for idx in range(main_win.stack.count()):
                main_win.stack.setCurrentIndex(idx)
                app.processEvents()
                name = page_names[idx] if idx < len(page_names) else f"page_{idx:02d}"
                out_path = theme_dir / f"{name}.png"
                pixmap = main_win.grab()
                pixmap.save(str(out_path), "PNG")
                total_captured += 1

            main_win.close()
            app.processEvents()

            # 2. Dialogs
            for d_name, d_cls in dialog_constructors:
                try:
                    dlg = d_cls()
                    dlg.show()
                    app.processEvents()
                    out_path = theme_dir / f"{d_name}.png"
                    pixmap = dlg.grab()
                    pixmap.save(str(out_path), "PNG")
                    dlg.close()
                    app.processEvents()
                    total_captured += 1
                except Exception as e:
                    print(f"Error capturing dialog {d_name}: {e}")

    print(f"\n[DONE] Successfully captured {total_captured} visual verification screenshots into '{base_out.resolve()}'")


if __name__ == "__main__":
    capture_all()
