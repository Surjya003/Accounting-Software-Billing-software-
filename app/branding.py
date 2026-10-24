"""
BillFlow Suite - Single Source of Truth for Enterprise Branding
===============================================================
Central brand definitions for application shell, splash screen, About dialog,
and system diagnostics logs.

IMPORTANT: Customer-facing documents (Tax Invoice, Proforma, Quotation, Challan, PO)
MUST NOT import these constants — they must always reflect the customer's own
CompanyProfile stored in the database.
"""
from datetime import datetime
from app.config import APP_VERSION

APP_NAME = "BillFlow Suite"
BRAND_NAME = "Binapani Automation"
MAKER_NAME = "Surjyakamal Saha"
TAGLINE = "Offline Accounting & Billing"
VERSION = APP_VERSION
COPYRIGHT_YEAR = f"2024–{datetime.now().year}"
CREDIT_LINE = f"Made by {MAKER_NAME}"
BRAND_FOOTER = "Offline Accounting & Billing"


def get_asset_path(relative_path: str):
    """Resolve an asset path reliably in both dev and PyInstaller frozen bundles."""
    import sys
    from pathlib import Path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base / relative_path

