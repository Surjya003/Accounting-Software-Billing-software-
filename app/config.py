"""
Application Configuration and Constants
"""
import os
from pathlib import Path
from datetime import date

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("ACCOUNTING_DB_PATH", str(DATA_DIR / "accounting.db")))
DATABASE_URI = os.environ.get("ACCOUNTING_DATABASE_URI", f"sqlite:///{DB_PATH}")


# Application Info
APP_NAME = "BillFlow"
APP_VERSION = "1.0.0"
APP_SUBTITLE = "Commercial Party-wise Ledger & Accounting System"
ORGANIZATION = "Vyapar Software Solutions"
TRIAL_DAYS = 14

# Formatting & Currency
CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "INR"
DATE_FORMAT = "%d-%m-%Y"
DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"

# Party Types
PARTY_TYPE_CUSTOMER = "Customer"
PARTY_TYPE_SUPPLIER = "Supplier"
PARTY_TYPE_BOTH = "Both"
PARTY_TYPES = [PARTY_TYPE_CUSTOMER, PARTY_TYPE_SUPPLIER, PARTY_TYPE_BOTH]

# Balance Types
BALANCE_DEBIT = "Dr"   # Customer owes us / money receivable
BALANCE_CREDIT = "Cr"  # We owe supplier / money payable
BALANCE_TYPES = [BALANCE_DEBIT, BALANCE_CREDIT]

# Voucher Types (simplified: Debit / Credit / Journal)
VOUCHER_DEBIT = "Debit"
VOUCHER_CREDIT = "Credit"
VOUCHER_JOURNAL = "Journal"
VOUCHER_TYPES = [
    VOUCHER_DEBIT,
    VOUCHER_CREDIT,
    VOUCHER_JOURNAL
]

# Legacy aliases — kept so old import sites don't break during migration
VOUCHER_SALE = VOUCHER_DEBIT
VOUCHER_PURCHASE = VOUCHER_CREDIT
VOUCHER_PAYMENT = VOUCHER_DEBIT
VOUCHER_RECEIPT = VOUCHER_CREDIT

# Voucher Prefixes for Auto-numbering
VOUCHER_PREFIXES = {
    VOUCHER_DEBIT: "DBT",
    VOUCHER_CREDIT: "CRT",
    VOUCHER_JOURNAL: "JRN",
    "Sale": "DBT",
    "Purchase": "CRT",
    "Payment": "DBT",
    "Receipt": "CRT"
}

# Payment Modes
PAYMENT_MODE_CASH = "Cash"
PAYMENT_MODE_BANK = "Bank Transfer (NEFT/RTGS/IMPS)"
PAYMENT_MODE_UPI = "UPI"
PAYMENT_MODE_CHEQUE = "Cheque"
PAYMENT_MODE_OTHER = "Other / Adjusted"
PAYMENT_MODES = [
    PAYMENT_MODE_CASH,
    PAYMENT_MODE_BANK,
    PAYMENT_MODE_UPI,
    PAYMENT_MODE_CHEQUE,
    PAYMENT_MODE_OTHER
]

# GST Rates (%)
GST_RATES = [0, 5, 12, 18, 28]

# Ageing Buckets (in days)
AGEING_BUCKETS = [
    (0, 30, "0 - 30 Days"),
    (31, 60, "31 - 60 Days"),
    (61, 90, "61 - 90 Days"),
    (91, 999999, "90+ Days")
]

# Standard Indian States and Codes
INDIAN_STATES = [
    ("01", "Jammu and Kashmir"),
    ("02", "Himachal Pradesh"),
    ("03", "Punjab"),
    ("04", "Chandigarh"),
    ("05", "Uttarakhand"),
    ("06", "Haryana"),
    ("07", "Delhi"),
    ("08", "Rajasthan"),
    ("09", "Uttar Pradesh"),
    ("10", "Bihar"),
    ("11", "Sikkim"),
    ("12", "Arunachal Pradesh"),
    ("13", "Nagaland"),
    ("14", "Manipur"),
    ("15", "Mizoram"),
    ("16", "Tripura"),
    ("17", "Meghalaya"),
    ("18", "Assam"),
    ("19", "West Bengal"),
    ("20", "Jharkhand"),
    ("21", "Odisha"),
    ("22", "Chhattisgarh"),
    ("23", "Madhya Pradesh"),
    ("24", "Gujarat"),
    ("26", "Dadra and Nagar Haveli and Daman and Diu"),
    ("27", "Maharashtra"),
    ("29", "Karnataka"),
    ("30", "Goa"),
    ("31", "Lakshadweep"),
    ("32", "Kerala"),
    ("33", "Tamil Nadu"),
    ("34", "Puducherry"),
    ("35", "Andaman and Nicobar Islands"),
    ("36", "Telangana"),
    ("37", "Andhra Pradesh"),
    ("38", "Ladakh"),
    ("97", "Other Territory")
]

def get_financial_year(target_date: date = None) -> str:
    """Returns Indian Financial Year string (e.g., '2024-25' or '24-25')"""
    if target_date is None:
        target_date = date.today()
    year = target_date.year
    month = target_date.month
    if month >= 4:
        start_year = year
        end_year = (year + 1) % 100
    else:
        start_year = year - 1
        end_year = year % 100
    return f"{start_year}-{end_year:02d}"
