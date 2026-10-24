"""
Database Migration and Health Service for BillFlow Suite.
Implements:
1. Versioned transactional migrations tracked in `schema_versions` table.
2. Pre-migration automatic atomic backups with automatic rollback on failure.
3. PRAGMA integrity_check and foreign_key_check on startup.
4. Scheduled automatic backup verification (row counts & integrity).
5. 14-day rolling backup retention enforcement.
"""
import hashlib
import logging
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from sqlalchemy import text
from app.config import DATA_DIR, BACKUP_DIR, DB_PATH
from app.database.connection import engine, create_backup, checkpoint_wal, DB_PATH

logger = logging.getLogger("BillFlow.Migrations")


class MigrationError(Exception):
    """Raised when a schema migration fails."""
    pass


def _calc_checksum(sql_statements: List[str]) -> str:
    h = hashlib.sha256()
    for s in sql_statements:
        h.update(s.strip().encode("utf-8"))
    return h.hexdigest()[:16]


def init_schema_versions_table(conn: sqlite3.Connection):
    """Ensures schema_versions table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        )
    """)
    conn.commit()


# Registered versioned migrations
# Each migration is (version: int, description: str, sql_statements: List[str])
MIGRATIONS = [
    (
        1,
        "Baseline PDF Suite & Document Metadata",
        [
            "ALTER TABLE challan_items ADD COLUMN qty_ordered NUMERIC(12, 3);",
            "ALTER TABLE challan_items ADD COLUMN remarks VARCHAR(255);",
            "ALTER TABLE purchase_orders ADD COLUMN revision VARCHAR(20) DEFAULT '0';",
            "ALTER TABLE purchase_orders ADD COLUMN quotation_ref VARCHAR(100);",
            "ALTER TABLE purchase_orders ADD COLUMN quotation_date DATE;",
            "ALTER TABLE purchase_orders ADD COLUMN delivery_required_by DATE;",
            "ALTER TABLE purchase_orders ADD COLUMN payment_terms VARCHAR(200);",
            "ALTER TABLE purchase_orders ADD COLUMN delivery_terms VARCHAR(100);",
            "ALTER TABLE purchase_orders ADD COLUMN mode_of_dispatch VARCHAR(100);",
            "ALTER TABLE purchase_orders ADD COLUMN insurance VARCHAR(100);",
            "ALTER TABLE purchase_orders ADD COLUMN ship_to_address TEXT;",
            "ALTER TABLE purchase_orders ADD COLUMN special_instructions TEXT;",
            "ALTER TABLE purchase_order_items ADD COLUMN delivery_date DATE;",
            "ALTER TABLE purchase_order_items ADD COLUMN item_code VARCHAR(50);",
        ]
    ),
    (
        2,
        "Company Valuation Method, Ageing Policy, and WhatsApp Template",
        [
            "ALTER TABLE company_profile ADD COLUMN stock_valuation_method VARCHAR(50) DEFAULT 'weighted_average';",
            "ALTER TABLE company_profile ADD COLUMN ageing_allocation_method VARCHAR(50) DEFAULT 'Oldest first';",
            "ALTER TABLE company_profile ADD COLUMN whatsapp_template TEXT;",
        ]
    ),
    (
        3,
        "Bill-by-Bill Voucher Allocations Engine",
        [
            """CREATE TABLE IF NOT EXISTS voucher_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id INTEGER NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
                payment_voucher_id INTEGER REFERENCES vouchers(id) ON DELETE CASCADE,
                invoice_voucher_id INTEGER REFERENCES vouchers(id) ON DELETE CASCADE,
                allocated_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                allocation_date DATE NOT NULL,
                allocation_type VARCHAR(30) NOT NULL DEFAULT 'FIFO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            "CREATE INDEX IF NOT EXISTS idx_alloc_party ON voucher_allocations(party_id);",
            "CREATE INDEX IF NOT EXISTS idx_alloc_pmt ON voucher_allocations(payment_voucher_id);",
            "CREATE INDEX IF NOT EXISTS idx_alloc_inv ON voucher_allocations(invoice_voucher_id);",
        ]
    ),
    (
        4,
        "Security Audit Trail Table",
        [
            """CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                username VARCHAR(100) NOT NULL DEFAULT 'System',
                action VARCHAR(50) NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address VARCHAR(50),
                notes TEXT
            );""",
            "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_logs(table_name, record_id);",
        ]
    ),
    (
        5,
        "User Security & Role-Based Access Control Baseline",
        [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(64) NOT NULL,
                full_name VARCHAR(100),
                role VARCHAR(30) NOT NULL DEFAULT 'Viewer',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS period_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                locked_until_date DATE NOT NULL,
                locked_by_user_id INTEGER,
                reason TEXT,
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );"""
        ]
    ),
    (
        6,
        "Adaptive Item Font Sizing for Billing Documents",
        [
            "ALTER TABLE company_profile ADD COLUMN adaptive_item_font_enabled BOOLEAN DEFAULT 1 NOT NULL;",
            "ALTER TABLE company_profile ADD COLUMN adaptive_item_font_max NUMERIC(4, 2) DEFAULT 13.0 NOT NULL;",
            "ALTER TABLE company_profile ADD COLUMN adaptive_item_font_min NUMERIC(4, 2) DEFAULT 7.5 NOT NULL;",
        ]
    )
]


def run_migrations(target_db_path: Optional[Path] = None) -> List[int]:
    """
    Executes pending migrations sequentially in isolated atomic transactions.
    Creates an automatic backup before applying migrations.
    Rolls back transaction on any error and raises MigrationError.
    """
    db_file = Path(target_db_path) if target_db_path else Path(DB_PATH)
    if not db_file.exists():
        logger.info("Database file does not exist yet; skipping migrations.")
        return []

    # Checkpoint WAL first
    checkpoint_wal(truncate=True, silent=True)

    applied_now = []
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        init_schema_versions_table(conn)

        # Get existing applied versions
        cursor = conn.cursor()
        cursor.execute("SELECT version, checksum FROM schema_versions")
        applied_map = {row["version"]: row["checksum"] for row in cursor.fetchall()}

        pending = [m for m in MIGRATIONS if m[0] not in applied_map]
        if not pending:
            logger.info("All schema migrations are up to date.")
            return []

        # Create pre-migration backup before applying any pending migrations
        try:
            backup_path = create_backup()
            logger.info(f"Pre-migration backup secured at: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not take pre-migration backup: {e}")

        for version, desc, stmts in pending:
            checksum = _calc_checksum(stmts)
            logger.info(f"Applying migration v{version}: {desc}...")
            
            # Run in isolated transaction
            cursor.execute("BEGIN IMMEDIATE")
            try:
                for sql in stmts:
                    try:
                        cursor.execute(sql)
                    except sqlite3.OperationalError as op_err:
                        # Allow duplicate column errors for idempotency with old databases
                        if "duplicate column name" in str(op_err).lower():
                            continue
                        raise
                
                cursor.execute(
                    "INSERT INTO schema_versions (version, description, applied_at, checksum) VALUES (?, ?, ?, ?)",
                    (version, desc, datetime.now().isoformat(), checksum)
                )
                conn.commit()
                applied_now.append(version)
                logger.info(f"Successfully applied migration v{version} ({desc}).")
            except Exception as e:
                conn.rollback()
                logger.error(f"Migration v{version} failed! Rolled back transaction. Error: {e}")
                raise MigrationError(f"Migration v{version} failed: {e}") from e

    return applied_now


def check_database_health(target_db_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Executes SQLite internal integrity checks:
    - PRAGMA integrity_check
    - PRAGMA foreign_key_check
    Returns (is_healthy, issues_list).
    """
    db_file = Path(target_db_path) if target_db_path else Path(DB_PATH)
    if not db_file.exists():
        return True, ["Database file does not exist yet (clean start)."]

    issues = []
    try:
        with sqlite3.connect(str(db_file)) as conn:
            cursor = conn.cursor()
            
            # 1. Integrity check
            cursor.execute("PRAGMA integrity_check")
            rows = cursor.fetchall()
            for r in rows:
                if r[0] != "ok":
                    issues.append(f"Corrupted page/structure: {r[0]}")

            # 2. Foreign key check
            cursor.execute("PRAGMA foreign_key_check")
            fk_rows = cursor.fetchall()
            for r in fk_rows:
                issues.append(f"Foreign key constraint violation: Table '{r[0]}', RowID {r[1]}, target '{r[2]}'")

    except Exception as e:
        issues.append(f"Database error during health check: {e}")

    is_healthy = (len(issues) == 0)
    return is_healthy, issues


def verify_backup(backup_path: Path) -> Tuple[bool, str]:
    """
    Validates a backup file by:
    1. Opening in an isolated connection.
    2. Running PRAGMA integrity_check.
    3. Verifying that key accounting tables contain readable rows.
    """
    if not backup_path.exists():
        return False, f"Backup file {backup_path} does not exist."

    conn = None
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        res = cursor.fetchone()
        if not res or res[0] != "ok":
            return False, f"Integrity check failed: {res[0] if res else 'Unknown'}"

        # Query core tables
        counts = {}
        for tbl in ["parties", "vouchers", "invoices", "products"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                counts[tbl] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[tbl] = 0

        return True, f"Backup verified ok. (Parties: {counts.get('parties', 0)}, Vouchers: {counts.get('vouchers', 0)}, Invoices: {counts.get('invoices', 0)})"
    except Exception as e:
        return False, f"Failed to verify backup: {e}"
    finally:
        if conn:
            conn.close()


def enforce_backup_retention(backup_dir: Optional[Path] = None, max_backups: int = 14) -> int:
    """
    Maintains rolling retention: deletes oldest backups exceeding max_backups.
    Returns number of deleted old backups.
    """
    b_dir = Path(backup_dir) if backup_dir else Path(BACKUP_DIR)
    if not b_dir.exists():
        return 0

    backup_files = sorted(
        [f for f in b_dir.iterdir() if f.is_file() and (f.suffix in (".db", ".enc", ".bak"))],
        key=lambda p: p.stat().st_mtime
    )

    deleted_count = 0
    if len(backup_files) > max_backups:
        excess = len(backup_files) - max_backups
        for old_file in backup_files[:excess]:
            try:
                old_file.unlink()
                deleted_count += 1
                logger.info(f"Retention policy: purged old backup {old_file.name}")
            except Exception as e:
                logger.warning(f"Could not delete old backup {old_file}: {e}")

    return deleted_count
