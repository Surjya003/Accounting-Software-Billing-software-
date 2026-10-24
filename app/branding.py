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
from app.version import VERSION
from app.core.paths import get_asset_path, resource_path

APP_NAME = "BillFlow Suite"
BRAND_NAME = "Binapani Automation"
MAKER_NAME = "Surjyakamal Saha"
TAGLINE = "Offline Accounting & Billing"
VERSION = VERSION
COPYRIGHT_YEAR = f"2024–{datetime.now().year}"
CREDIT_LINE = f"Made by {MAKER_NAME}"
BRAND_FOOTER = "Offline Accounting & Billing"


