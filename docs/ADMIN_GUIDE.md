# BillFlow Suite — System Administrator & Technical Manual

**Document Version:** 1.0.0 (Production Release)  
**Target Audience:** System Administrators, IT Engineers, DevOps, Compliance Officers  

---

## 1. System Architecture & Topology

BillFlow Suite is an enterprise-grade offline desktop accounting and billing system designed for high reliability, data safety, and zero cloud dependency.

### 1.1 Technical Stack
- **Runtime Environment:** Python 3.14.3 (64-bit)
- **GUI Engine:** PySide6 (Qt 6.6+ with High-DPI PassThrough rendering)
- **Database Engine:** SQLite 3 with Write-Ahead Logging (`WAL`), `synchronous=NORMAL`, 64MB cache, and 30,000 ms busy timeout
- **ORM / Persistence:** SQLAlchemy 2.0 (thread-isolated session scopes with `BEGIN IMMEDIATE` write serialization)
- **Document Rendering:** ReportLab 4.0+ (vector graphics, Type 1 and TrueType Unicode fonts, Nirmala UI fallback)
- **Spreadsheet Processing:** openpyxl 3.1+ (formula preservation, freeze panes, print area auto-configuration)
- **Security & Crypto:** cryptography (scrypt KDF, HMAC-SHA256, Fernet)

### 1.2 Storage Directory Topology
| Directory | Windows Default Location | Purpose |
| :--- | :--- | :--- |
| **Binaries & Assets** | `C:\Program Files\BillFlow\` | Executable (`BillFlow.exe`), Qt DLLs, fonts |
| **Active Financial DB** | `%APPDATA%\BillFlow\data\accounting.db` | Primary SQLite transaction database |
| **Rolling Backups** | `%APPDATA%\BillFlow\backups\` | Timestamped `.db` backup snapshots (14 rolling copies) |
| **Enterprise Logs** | `%APPDATA%\BillFlow\logs\billflow.log` | Rotating event log (max 10MB, keep 5) |
| **Crash & Fault Logs** | `%APPDATA%\BillFlow\logs\crash.log` | Uncaught exception dumps and thread traces |
| **Generated Exports** | `%APPDATA%\BillFlow\exports\` | PDF invoices, Excel reports, GSTR-1 JSON files |

---

## 2. Database Schema Management & Migrations

### 2.1 Schema Version Tracking Table
BillFlow tracks applied database migrations through the `schema_versions` table:
```sql
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);
```

### 2.2 Idempotent DDL Migration Engine
All schema changes are applied automatically during application startup via `app/database/migrations.py`.
- **Pre-Migration Backup:** Before executing any migration, the engine creates a verified pre-migration backup (`pre_migration_v{version}_{timestamp}.db`).
- **Column Addition:** Uses `_add_col_if_missing(conn, table_name, column_name, column_type)` to safely inspect `PRAGMA table_info` before issuing `ALTER TABLE ... ADD COLUMN`, preventing duplication errors.
- **Transactional Atomicity:** Migrations are wrapped in explicit database transactions; if any step fails, the transaction rolls back cleanly.

### 2.3 Health Verification (`check_database_health`)
The administrator or automated CI can verify database health at any time:
```python
from app.database.migrations import check_database_health
report = check_database_health("path/to/accounting.db")
# Returns: {"status": "HEALTHY", "integrity_check": "ok", "foreign_key_check": "ok", "wal_mode": "wal"}
```

### 2.4 Encrypted Backups (AES-256-GCM) & Lost Passphrase Protocol
BillFlow Suite supports exporting cryptographic database backups in `.enc` format:
- **Cipher**: AES-256 in Galois/Counter Mode (GCM) providing authenticated encryption (AEAD).
- **Key Derivation**: PBKDF2HMAC with SHA-256, 100,000 iterations, and a unique 16-byte random salt per backup.
- **Header Structure**: `BILLFLOW_ENC_V1` (15 bytes) + Salt (16 bytes) + Nonce (12 bytes) + Ciphertext + GCM Tag (16 bytes).

**Lost Passphrase Protocol:**
> [!IMPORTANT]
> Because BillFlow operates 100% offline with zero cloud backdoors or master escrow keys, **a forgotten backup passphrase CANNOT be cracked or recovered**.
> In the event of a lost passphrase:
> 1. Do not overwrite or delete existing databases.
> 2. Locate the most recent automated rolling backup snapshot in `%APPDATA%\BillFlow\backups\accounting_backup_YYYYMMDD_HHMMSS.db`.
> 3. Verify backup integrity via `verify_backup(path)`.
> 4. Restore the unencrypted rolling backup via Settings > Restore Database.
> 5. For endpoint protection at rest, enable **BitLocker** drive encryption on Windows.

---

## 3. Security, Authentication & Role-Based Access Control (RBAC)

### 3.1 Role Hierarchy & Permissions
| Role | Financial Access | Period Lock Override | User Management | Export / Print |
| :--- | :---: | :---: | :---: | :---: |
| **Admin** | Full (Read/Write/Delete) | Yes | Yes | Yes |
| **Accountant** | Full (Read/Write/Cancel) | No | No | Yes |
| **Billing** | Invoices & Quotations Only | No | No | Yes |
| **Viewer** | Read-Only Across All Views | No | No | Read-Only |

### 3.2 Password Hashing & Brute-Force Lockout
- **Key Derivation:** Passwords are hashed using **scrypt** with a 32-byte cryptographic salt, CPU/memory cost parameter $N=2^{14}$, $r=8$, $p=1$.
- **Brute-Force Protection:** If an account receives **5 consecutive failed login attempts**, it is automatically locked for **15 minutes**.

### 3.3 Statutory Period Locking (`PeriodLock`)
To comply with tax laws and prevent retroactive tampering after returns are filed:
- **Lock Types:** `soft` (requires warning confirmation) or `hard` (blocks all write/cancel operations).
- **Enforcement:** `invoice_service.py` and `voucher_service.py` call `check_period_unlocked(date)` before committing any financial transaction. Attempting to post to a locked period raises `PermissionError`.

### 3.4 Immutable Audit Logging (`AuditLog`)
Every critical financial modification (invoice creation, cancellation, return, voucher adjustment) is recorded in the `audit_logs` table with:
- Timestamp (UTC ISO 8601)
- User ID and Username
- Action (`CREATE`, `UPDATE`, `CANCEL`, `DELETE`)
- Table Name and Record ID
- Old Values JSON and New Values JSON

---

## 4. System Guard & Process Protection

### 4.1 Single-Instance Enforcement
To eliminate SQLite WAL locking deadlocks caused by multiple processes opening the same database file, `app/services/system_guard.py` enforces a single-instance lock via `.billflow.lock`:
- Writes current Process ID (PID) to lock file.
- Checks Windows API `OpenProcess` to verify if existing PID is actively running.
- Cleans up stale lock files automatically if prior process terminated abnormally.

### 4.2 Monotonic Clock Guard (`ClockGuard`)
Detects system clock manipulation (e.g. rolling back Windows clock to extend trial licenses or post retroactive entries):
- Periodically records highest observed system time in `%APPDATA%\BillFlow\data\.time_guard`.
- If current system time is found to be more than **24 hours in the past** relative to the saved timestamp, startup is aborted with a security alert.

### 4.3 Double-Click UI Debouncing
All UI save and export buttons are equipped with synchronous disabling (`btn.setEnabled(False)`) within `try...finally: btn.setEnabled(True)` blocks to prevent duplicate voucher creation or double invoice submission on slow network drives.

---

## 5. Observability, Logging & Diagnostics

### 5.1 Centralized Rotating Logger
- **File:** `%APPDATA%\BillFlow\logs\billflow.log`
- **Rotation:** Maximum 10 MB per file, maintaining 5 historical backups (`billflow.log.1` through `.5`).
- **Formatting:** `YYYY-MM-DD HH:MM:SS [LEVEL] [Thread] Module:Line: Message`.

### 5.2 Global Exception Hook & Error Reference IDs
When an unhandled exception occurs:
1. `sys.excepthook` intercepts the error (`app/core/crash_handler.py`).
2. Generates a unique Error Reference ID (e.g. `ERR-20261023-A4F1D9`).
3. Logs complete traceback and system metrics to `crash.log`.
4. Displays user-friendly dialog with a **"Copy Diagnostics"** button.

### 5.3 Diagnostic Bundle Generator
Admins can generate a complete diagnostics bundle via CLI or UI (Settings > Diagnostics > "Export Diagnostics"):
```python
from app.core.diagnostics import export_diagnostics_bundle
zip_path = export_diagnostics_bundle()
```
The resulting `.zip` contains:
- `system_health.json` (memory, thread count, SQLite latency)
- `environment.json` (OS, architecture, Python build)
- `configuration.json` (sanitized paths, licensing state)
- `database_health.json` (PRAGMA integrity check, foreign keys, row counts)
- `logs/billflow.log` (recent 500 lines)

---

## 6. Disaster Recovery & Command-Line Verification

### 6.1 Books Integrity Verification Script
Execute the 7-point mathematical integrity verification script on any database copy:
```bash
python scripts/verify_books.py data/accounting.db
```
**7 Checks Performed:**
1. SQLite PRAGMA `quick_check` and `foreign_key_check`
2. Company profile existence and state code validity
3. Invoice tax math (Subtotal + CGST + SGST + IGST + Round-off == Grand Total)
4. Invoice item sum vs header totals
5. Sequential invoice numbering continuity per financial year
6. Voucher debit/credit balance equality
7. Trial Balance equality (Total Debits == Total Credits)

Exits **0** if all checks pass; non-zero with failure summary if any defect is detected.

---
*End of Administrator Guide.*
