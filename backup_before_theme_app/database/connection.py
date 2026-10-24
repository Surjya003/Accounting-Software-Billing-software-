"""
Database Engine, Session Management, and Backup Utilities
"""
import shutil
import logging
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

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
    
    # Check if company profile exists, if not create default
    with get_session() as session:
        # Check and migrate columns if missing in existing database
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("ALTER TABLE company_profile ADD COLUMN logo_path VARCHAR(500)")
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

        
        # Migration: Convert old voucher types to new simplified types
        # Sale → Debit, Payment → Debit, Purchase → Credit, Receipt → Credit
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("UPDATE vouchers SET voucher_type = 'Debit' WHERE voucher_type IN ('Sale', 'Payment')")
                conn.exec_driver_sql("UPDATE vouchers SET voucher_type = 'Credit' WHERE voucher_type IN ('Purchase', 'Receipt')")
                conn.commit()
        except Exception:
            pass
            
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

    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit()
    except Exception:
        pass

    with sqlite3.connect(str(DB_PATH)) as src:
        with sqlite3.connect(str(backup_file)) as dst:
            src.backup(dst)

    logger.info(f"Database backup created successfully at {backup_file}")
    return backup_file

def restore_backup(backup_file_path) -> bool:
    """Restores database atomically from a selected backup file using SQLite's native backup API."""
    b_path = Path(backup_file_path)
    if not b_path.exists():
        raise FileNotFoundError(f"Backup file not found at {b_path}")

    engine.dispose()

    with sqlite3.connect(str(b_path)) as src:
        with sqlite3.connect(str(DB_PATH)) as dst:
            src.backup(dst)

    engine.dispose()
    init_db()
    logger.info(f"Database restored successfully from {b_path}")
    return True

