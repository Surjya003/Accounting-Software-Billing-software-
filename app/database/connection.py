"""
Database Engine, Session Management, and Backup Utilities
"""
import sqlite3
import datetime as dt
import shutil
import logging
import sys
import atexit
import signal
from datetime import datetime, date
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Register explicit ISO datetime adapters/converters to eliminate Python 3.12+ DeprecationWarnings
def _adapt_date_iso(val: dt.date) -> str:
    return val.isoformat()

def _adapt_datetime_iso(val: dt.datetime) -> str:
    return val.isoformat()

def _convert_date_iso(val: bytes) -> dt.date:
    return dt.date.fromisoformat(val.decode())

def _convert_datetime_iso(val: bytes) -> dt.datetime:
    return dt.datetime.fromisoformat(val.decode())

sqlite3.register_adapter(dt.date, _adapt_date_iso)
sqlite3.register_adapter(dt.datetime, _adapt_datetime_iso)
sqlite3.register_converter("date", _convert_date_iso)
sqlite3.register_converter("DATE", _convert_date_iso)
sqlite3.register_converter("datetime", _convert_datetime_iso)
sqlite3.register_converter("DATETIME", _convert_datetime_iso)
sqlite3.register_converter("TIMESTAMP", _convert_datetime_iso)

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.config import DATABASE_URI, DB_PATH, BACKUP_DIR
from app.database.models import Base, CompanyProfile

logger = logging.getLogger(__name__)

# Create engine with foreign keys and 30s busy timeout in SQLite
engine = create_engine(
    DATABASE_URI,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30.0}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB memory cache
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def init_db():
    """Initializes tables and default company profile if missing."""
    Base.metadata.create_all(bind=engine)

    try:
        from app.database.migrations import run_migrations, check_database_health
        is_healthy, issues = check_database_health()
        if not is_healthy:
            logger.critical(f"Database health check detected issues: {issues}")
        run_migrations()
    except Exception as me:
        logger.warning(f"Error during migration execution: {me}")
    
    # Check if company profile exists, if not create default
    with get_session() as session:
        # Check and migrate columns if missing in existing database
        try:
            with engine.connect() as conn:
                col_info = conn.exec_driver_sql("PRAGMA table_info(company_profile)").fetchall()
                col_names = [col[1] for col in col_info]
                if "logo_path" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE company_profile ADD COLUMN logo_path VARCHAR(500)")
                if "allow_negative_stock" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE company_profile ADD COLUMN allow_negative_stock BOOLEAN DEFAULT 0 NOT NULL")
                conn.commit()
        except Exception:
            pass
            
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("ALTER TABLE parties ADD COLUMN opening_balance_date DATE")
                conn.commit()
        except Exception:
            pass
        
        # Migration: Add product column to vouchers
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("ALTER TABLE vouchers ADD COLUMN product VARCHAR(255)")
                conn.commit()
        except Exception:
            pass

        # Migration: Add received_quantity to purchase_order_items and backfill
        try:
            with engine.connect() as conn:
                col_info = conn.exec_driver_sql("PRAGMA table_info(purchase_order_items)").fetchall()
                col_names = [col[1] for col in col_info]
                if "received_quantity" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE purchase_order_items ADD COLUMN received_quantity NUMERIC(12, 3) DEFAULT 0.000")
                
                # Backfill: for POs already marked "received", set received_quantity = quantity
                conn.exec_driver_sql("""
                    UPDATE purchase_order_items
                    SET received_quantity = quantity
                    WHERE (received_quantity IS NULL OR received_quantity = 0)
                      AND po_id IN (SELECT id FROM purchase_orders WHERE status = 'received')
                """)
                conn.commit()
        except Exception:
            pass

        # Migration: Add PDF Document Suite fields across all billing tables (idempotent)
        try:
            with engine.connect() as conn:
                def _add_col_if_missing(table_name, col_name, col_type):
                    try:
                        info = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
                        existing = [c[1] for c in info]
                        if col_name not in existing:
                            conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

                # 1. Company Profile
                _add_col_if_missing("company_profile", "declaration", "TEXT DEFAULT 'We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.'")
                _add_col_if_missing("company_profile", "terms_quotation", "TEXT DEFAULT '1. Validity: 30 days from date of quotation.\n2. Payment: 100% against delivery.\n3. Taxes: GST extra as applicable.'")
                _add_col_if_missing("company_profile", "terms_po", "TEXT DEFAULT '1. Quote PO number on all invoices and delivery challans.\n2. Goods subject to inspection and approval.'")
                _add_col_if_missing("company_profile", "notes_challan", "TEXT DEFAULT 'Goods sent on approval/job work basis. Not for sale.'")
                _add_col_if_missing("company_profile", "terms_proforma", "TEXT DEFAULT 'Goods will be dispatched immediately upon receipt of full payment.'")
                _add_col_if_missing("company_profile", "seal_path", "VARCHAR(500)")
                _add_col_if_missing("company_profile", "signature_path", "VARCHAR(500)")
                _add_col_if_missing("company_profile", "number_format", "VARCHAR(20) DEFAULT 'Indian'")
                _add_col_if_missing("company_profile", "show_value_on_challan", "BOOLEAN DEFAULT 0")
                _add_col_if_missing("company_profile", "print_all_copies", "BOOLEAN DEFAULT 0")
                _add_col_if_missing("company_profile", "print_hsn_summary", "BOOLEAN DEFAULT 1")
                _add_col_if_missing("company_profile", "stock_valuation_method", "VARCHAR(50) DEFAULT 'weighted_average'")
                _add_col_if_missing("company_profile", "ageing_allocation_method", "VARCHAR(50) DEFAULT 'Oldest first'")
                _add_col_if_missing("company_profile", "whatsapp_template", "TEXT")

                # 2. Parties (Separate Shipping Address)
                _add_col_if_missing("parties", "shipping_address", "TEXT")
                _add_col_if_missing("parties", "shipping_city", "VARCHAR(100)")
                _add_col_if_missing("parties", "shipping_state", "VARCHAR(100)")
                _add_col_if_missing("parties", "shipping_state_code", "VARCHAR(2)")
                _add_col_if_missing("parties", "shipping_pincode", "VARCHAR(10)")
                _add_col_if_missing("parties", "same_as_billing", "BOOLEAN DEFAULT 1")

                # 3. Invoices (7-Row Reference Grid & Tax particulars)
                _add_col_if_missing("invoices", "delivery_note", "VARCHAR(100)")
                _add_col_if_missing("invoices", "mode_terms_of_payment", "VARCHAR(100)")
                _add_col_if_missing("invoices", "reference_no_date", "VARCHAR(100)")
                _add_col_if_missing("invoices", "other_references", "VARCHAR(100)")
                _add_col_if_missing("invoices", "buyers_order_no", "VARCHAR(100)")
                _add_col_if_missing("invoices", "buyers_order_date", "DATE")
                _add_col_if_missing("invoices", "dispatch_doc_no", "VARCHAR(100)")
                _add_col_if_missing("invoices", "dispatched_through", "VARCHAR(100)")
                _add_col_if_missing("invoices", "terms_of_delivery", "TEXT")
                _add_col_if_missing("invoices", "place_of_supply", "VARCHAR(100)")
                _add_col_if_missing("invoices", "reverse_charge", "BOOLEAN DEFAULT 0")
                _add_col_if_missing("invoices", "copy_label", "VARCHAR(50) DEFAULT 'ORIGINAL FOR RECIPIENT'")

                # 4. Proforma Invoices
                _add_col_if_missing("proforma_invoices", "valid_until", "DATE")
                _add_col_if_missing("proforma_invoices", "advance_percent", "NUMERIC(5, 2) DEFAULT 0.00")
                _add_col_if_missing("proforma_invoices", "advance_received", "NUMERIC(15, 2) DEFAULT 0.00")
                _add_col_if_missing("proforma_invoices", "payment_terms", "VARCHAR(200)")
                _add_col_if_missing("proforma_invoices", "delivery_period", "VARCHAR(100)")
                _add_col_if_missing("proforma_invoices", "customer_po_no", "VARCHAR(100)")
                _add_col_if_missing("proforma_invoices", "customer_po_date", "DATE")
                _add_col_if_missing("proforma_invoices", "linked_invoice_reference", "VARCHAR(50)")

                # 5. Quotations
                _add_col_if_missing("quotations", "kind_attn", "VARCHAR(100)")
                _add_col_if_missing("quotations", "enquiry_ref_date", "VARCHAR(100)")
                _add_col_if_missing("quotations", "subject", "VARCHAR(255)")
                _add_col_if_missing("quotations", "price_basis", "VARCHAR(100)")
                _add_col_if_missing("quotations", "terms_payment", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_delivery", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_validity", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_freight", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_packing", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_warranty", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_taxes", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_inspection", "VARCHAR(200)")
                _add_col_if_missing("quotations", "terms_jurisdiction", "VARCHAR(200)")

                # 6. Delivery Challans
                _add_col_if_missing("delivery_challans", "reason_for_transportation", "VARCHAR(50) DEFAULT 'Delivery (invoice to follow)'")
                _add_col_if_missing("delivery_challans", "dispatch_datetime", "VARCHAR(50)")
                _add_col_if_missing("delivery_challans", "transporter_name", "VARCHAR(200)")
                _add_col_if_missing("delivery_challans", "transporter_id", "VARCHAR(50)")
                _add_col_if_missing("delivery_challans", "vehicle_no", "VARCHAR(50)")
                _add_col_if_missing("delivery_challans", "driver_name", "VARCHAR(100)")
                _add_col_if_missing("delivery_challans", "driver_mobile", "VARCHAR(20)")
                _add_col_if_missing("delivery_challans", "lr_no", "VARCHAR(50)")
                _add_col_if_missing("delivery_challans", "lr_date", "DATE")
                _add_col_if_missing("delivery_challans", "eway_bill_no", "VARCHAR(50)")
                _add_col_if_missing("delivery_challans", "from_place", "VARCHAR(100)")
                _add_col_if_missing("delivery_challans", "to_place", "VARCHAR(100)")
                _add_col_if_missing("delivery_challans", "distance_km", "NUMERIC(10, 2)")
                _add_col_if_missing("delivery_challans", "packages", "INTEGER")
                _add_col_if_missing("delivery_challans", "weight", "NUMERIC(10, 3)")
                _add_col_if_missing("delivery_challans", "show_value", "BOOLEAN DEFAULT 0")

                # 7. Challan Items
                _add_col_if_missing("challan_items", "qty_ordered", "NUMERIC(12, 3)")
                _add_col_if_missing("challan_items", "remarks", "VARCHAR(255)")

                # 8. Purchase Orders
                _add_col_if_missing("purchase_orders", "revision", "VARCHAR(20) DEFAULT '0'")
                _add_col_if_missing("purchase_orders", "quotation_ref", "VARCHAR(100)")
                _add_col_if_missing("purchase_orders", "quotation_date", "DATE")
                _add_col_if_missing("purchase_orders", "delivery_required_by", "DATE")
                _add_col_if_missing("purchase_orders", "payment_terms", "VARCHAR(200)")
                _add_col_if_missing("purchase_orders", "delivery_terms", "VARCHAR(100)")
                _add_col_if_missing("purchase_orders", "mode_of_dispatch", "VARCHAR(100)")
                _add_col_if_missing("purchase_orders", "insurance", "VARCHAR(100)")
                _add_col_if_missing("purchase_orders", "ship_to_address", "TEXT")
                _add_col_if_missing("purchase_orders", "special_instructions", "TEXT")

                # 9. Purchase Order Items
                _add_col_if_missing("purchase_order_items", "delivery_date", "DATE")
                _add_col_if_missing("purchase_order_items", "item_code", "VARCHAR(50)")

                # 10. Sales Returns
                _add_col_if_missing("sales_returns", "reason_category", "VARCHAR(50) DEFAULT 'Sales Return'")
                _add_col_if_missing("sales_returns", "original_invoice_no", "VARCHAR(50)")
                _add_col_if_missing("sales_returns", "original_invoice_date", "DATE")
                _add_col_if_missing("sales_returns", "adjustment_mode", "VARCHAR(50) DEFAULT 'Credit Note'")
                _add_col_if_missing("sales_returns", "adjustment_ref", "VARCHAR(100)")
                _add_col_if_missing("sales_returns", "returned_via", "VARCHAR(100)")

                # 11. Purchase Returns
                _add_col_if_missing("purchase_returns", "reason_category", "VARCHAR(50) DEFAULT 'Purchase Return'")
                _add_col_if_missing("purchase_returns", "original_invoice_no", "VARCHAR(50)")
                _add_col_if_missing("purchase_returns", "original_invoice_date", "DATE")
                _add_col_if_missing("purchase_returns", "adjustment_mode", "VARCHAR(50) DEFAULT 'Debit Note'")
                _add_col_if_missing("purchase_returns", "adjustment_ref", "VARCHAR(100)")
                _add_col_if_missing("purchase_returns", "returned_via", "VARCHAR(100)")

                conn.commit()
        except Exception as e:
            logger.warning(f"Error during PDF suite migration: {e}")

        
        # Migration: Convert old voucher types to new simplified types
        # Sale → Debit, Payment → Debit, Purchase → Credit, Receipt → Credit
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("UPDATE vouchers SET voucher_type = 'Debit' WHERE voucher_type IN ('Sale', 'Payment')")
                conn.exec_driver_sql("UPDATE vouchers SET voucher_type = 'Credit' WHERE voucher_type IN ('Purchase', 'Receipt')")
                conn.commit()
        except Exception:
            pass

        # Migration: Report duplicates and create UNIQUE indexes on document numbers
        dup_check_tables = [
            ("invoices", "invoice_number"),
            ("quotations", "quotation_number"),
            ("delivery_challans", "challan_number"),
            ("proforma_invoices", "proforma_number"),
            ("purchase_orders", "po_number"),
            ("sales_returns", "return_number"),
            ("purchase_returns", "return_number"),
            ("vouchers", "voucher_number"),
        ]
        try:
            with engine.connect() as conn:
                for table, col in dup_check_tables:
                    try:
                        dups = conn.exec_driver_sql(f"""
                            SELECT {col}, COUNT(*) as cnt FROM {table}
                            WHERE {col} IS NOT NULL AND TRIM({col}) != ''
                            GROUP BY {col} HAVING cnt > 1
                        """).fetchall()
                        if dups:
                            logger.warning(f"DUPLICATE DETECTED in table {table} column {col}: {dups}")
                            for val, cnt in dups:
                                rows = conn.exec_driver_sql(f"SELECT id FROM {table} WHERE {col} = ? ORDER BY id", (val,)).fetchall()
                                for idx, r in enumerate(rows[1:], 1):
                                    new_val = f"{val}-DUP{idx}"
                                    conn.exec_driver_sql(f"UPDATE {table} SET {col} = ? WHERE id = ?", (new_val, r[0]))
                        conn.exec_driver_sql(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_{col} ON {table}({col})")
                    except Exception as e:
                        logger.warning(f"Could not create unique index on {table}.{col}: {e}")
                conn.commit()
        except Exception:
            pass

        # Migration: Data cleanup / resync of finalized invoices with vouchers desynchronized prior to BUG-15 fix
        try:
            with engine.connect() as conn:
                mismatched = conn.exec_driver_sql("""
                    SELECT i.id, i.invoice_number, i.subtotal, i.cgst_total, i.sgst_total, i.igst_total, i.tax_amount, i.total_amount, v.id
                    FROM invoices i
                    JOIN vouchers v ON (v.voucher_number = i.invoice_number OR v.reference_no = i.invoice_number)
                    WHERE i.status = 'final' AND v.total_amount != i.total_amount
                """).fetchall()
                for row in mismatched:
                    logger.warning(f"Resyncing desynchronized voucher {row[8]} for finalized invoice {row[1]} to ₹{row[7]}")
                    conn.exec_driver_sql("""
                        UPDATE vouchers
                        SET amount_untaxed = ?, cgst_amount = ?, sgst_amount = ?, igst_amount = ?, total_tax = ?, total_amount = ?, debit_amount = ?
                        WHERE id = ?
                    """, (row[2], row[3], row[4], row[5], row[6], row[7], row[7], row[8]))
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not resync invoice vouchers: {e}")
            
        profile = session.query(CompanyProfile).first()
        if not profile:
            default_profile = CompanyProfile(
                name="Sita Ram & Sons Traders",
                trade_name="Sita Ram & Sons",
                gstin="27AABCS1429B1Z8",
                pan="AABCS1429B",
                address="Shop No. 12, Industrial Area Phase II, MIDC",
                city="Mumbai",
                state="Maharashtra",
                state_code="27",
                pincode="400001",
                phone="+91 98200 12345",
                email="contact@sitaramtraders.com",
                bank_name="State Bank of India",
                bank_account_no="381928472910",
                bank_ifsc="SBIN0001234",
                bank_branch="Fort Mumbai Main Branch",
                upi_id="sitaramtraders@sbi",
                financial_year="2024-25"
            )
            session.add(default_profile)
            session.commit()

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def get_db():
    """Dependency generator for fast operations."""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise

import sqlite3

def create_backup(custom_dest_dir=None) -> Path:
    """Creates an atomic timestamped backup of the SQLite database using SQLite's native backup API."""
    if custom_dest_dir:
        dest_path = Path(custom_dest_dir)
        if dest_path.suffix.lower() == ".db":
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            backup_file = dest_path
        else:
            dest_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = dest_path / f"accounting_backup_{timestamp}.db"
    else:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"accounting_backup_{timestamp}.db"

    checkpoint_wal(truncate=True)

    src = None
    dst = None
    try:
        src = sqlite3.connect(str(DB_PATH))
        dst = sqlite3.connect(str(backup_file))
        src.backup(dst)
    finally:
        if dst:
            dst.close()
        if src:
            src.close()

    logger.info(f"Database backup created successfully at {backup_file}")
    return backup_file

def checkpoint_wal(truncate: bool = True, silent: bool = False) -> bool:
    """
    BUG-09: Runs PRAGMA wal_checkpoint(TRUNCATE).
    Flushes all WAL pages to primary DB and truncates/cleans the WAL file.
    """
    try:
        mode = "TRUNCATE" if truncate else "PASSIVE"
        with engine.connect() as conn:
            conn.exec_driver_sql(f"PRAGMA wal_checkpoint({mode})")
            conn.commit()
        if not silent:
            logger.info(f"WAL checkpoint ({mode}) executed successfully.")
        return True
    except Exception as e:
        if not silent:
            logger.warning(f"WAL checkpoint failed: {e}")
        return False

def create_encrypted_backup(passphrase: str, custom_dest_dir=None) -> Path:
    """
    BUG-05 / Decision D2: Creates an AES-256-GCM encrypted backup of the SQLite database.
    File structure:
      MAGIC: b"BILLFLOW_ENC_V1" (15 bytes)
      SALT: 16 bytes (PBKDF2 salt)
      NONCE: 12 bytes (AES-GCM nonce)
      CIPHERTEXT: encrypted SQLite DB file + 16-byte GCM authentication tag
    """
    if not passphrase or len(passphrase.strip()) < 4:
        raise ValueError("Passphrase must be at least 4 characters long.")

    import os
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    # 1. Snapshot database safely via checkpointed backup API
    temp_snapshot = create_backup(custom_dest_dir=None)
    try:
        raw_data = temp_snapshot.read_bytes()
    finally:
        try:
            temp_snapshot.unlink(missing_ok=True)
        except Exception:
            pass

    # 2. Derive 256-bit AES key using PBKDF2HMAC
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(passphrase.encode("utf-8"))

    # 3. Encrypt via AES-GCM
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, raw_data, b"BILLFLOW_ENC_V1")

    # 4. Save to destination
    if custom_dest_dir:
        dest_path = Path(custom_dest_dir)
        if dest_path.is_file() or dest_path.suffix == ".enc":
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            enc_file = dest_path
        else:
            dest_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            enc_file = dest_path / f"accounting_backup_{timestamp}.enc"
    else:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        enc_file = BACKUP_DIR / f"accounting_backup_{timestamp}.enc"

    payload = b"BILLFLOW_ENC_V1" + salt + nonce + ciphertext
    enc_file.write_bytes(payload)
    logger.info(f"Encrypted database backup created successfully at {enc_file}")
    return enc_file


def restore_encrypted_backup(encrypted_backup_path, passphrase: str) -> bool:
    """
    BUG-05 / Decision D2: Decrypts an AES-256-GCM encrypted backup and restores database.
    Raises ValueError on incorrect passphrase or tampered file.
    """
    b_path = Path(encrypted_backup_path)
    if not b_path.exists():
        raise FileNotFoundError(f"Backup file not found at {b_path}")

    payload = b_path.read_bytes()
    magic = b"BILLFLOW_ENC_V1"
    if not payload.startswith(magic):
        raise ValueError("Invalid file format: Not a recognized BillFlow encrypted backup.")

    if len(payload) < len(magic) + 16 + 12 + 16:
        raise ValueError("Corrupted backup file: payload is too short.")

    salt = payload[len(magic):len(magic) + 16]
    nonce = payload[len(magic) + 16:len(magic) + 28]
    ciphertext = payload[len(magic) + 28:]

    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(passphrase.encode("utf-8"))
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, magic)
    except InvalidTag:
        raise ValueError("Decryption failed: Incorrect passphrase or corrupted backup file.")

    temp_restored = BACKUP_DIR / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    temp_restored.write_bytes(plaintext)
    try:
        return restore_backup(temp_restored)
    finally:
        try:
            temp_restored.unlink(missing_ok=True)
        except Exception:
            pass


def restore_backup(backup_file_path, passphrase: Optional[str] = None) -> bool:
    """Restores database atomically from a selected backup file using SQLite's native backup API."""
    b_path = Path(backup_file_path)
    if not b_path.exists():
        raise FileNotFoundError(f"Backup file not found at {b_path}")

    # Check if this is an encrypted backup file
    with open(b_path, "rb") as f:
        head = f.read(15)
    if head == b"BILLFLOW_ENC_V1":
        if not passphrase:
            raise ValueError("Passphrase is required to restore an encrypted backup.")
        return restore_encrypted_backup(b_path, passphrase)

    engine.dispose()

    with sqlite3.connect(str(b_path)) as src:
        with sqlite3.connect(str(DB_PATH)) as dst:
            src.backup(dst)

    engine.dispose()
    init_db()
    checkpoint_wal(truncate=True)
    logger.info(f"Database restored successfully from {b_path}")
    return True

def _cleanup_wal_at_exit():
    try:
        checkpoint_wal(truncate=True, silent=True)
        engine.dispose()
    except Exception:
        pass

atexit.register(_cleanup_wal_at_exit)

def _sigterm_handler(signum, frame):
    _cleanup_wal_at_exit()
    sys.exit(0)

try:
    signal.signal(signal.SIGTERM, _sigterm_handler)
except Exception:
    pass


