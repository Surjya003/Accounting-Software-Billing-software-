# BillFlow Suite — Release Changelog

All notable changes to the BillFlow Suite codebase are documented in this file.  
The project adheres strictly to Semantic Versioning (`MAJOR.MINOR.PATCH`).

---

## [1.0.0] — Production Release — 2026-10-23

### 🚀 Milestone Overview
BillFlow Suite has achieved full **PRODUCTION READY** status across all 9 production phases, backed by 100% test pass rates across 65+ automated test scenarios and a 32,000-record performance stress benchmark.

---

### 🛡️ Phase 1: Core Audited Defects & Usability Fixes
- **FIXED:** Trial Balance calculation now strictly adheres to dual-entry accounting with absolute zero difference (`difference == 0.00`).
- **FIXED:** One-click Quotation conversion to Tax Invoice (`convert_quotation_to_invoice`) properly marks quotation status as `converted` and transfers line items without data loss.
- **FIXED:** Thread-safe, atomic sequence number generation using SQLite `BEGIN IMMEDIATE` transactions to prevent duplicate voucher numbers under rapid user entry.
- **FIXED:** Isolated Proforma Invoice sequence counter (`PI/YYYY-YY/XXXX`) from Tax Invoice sequence counter (`INV/YYYY-YY/XXXX`).
- **FIXED:** Sales Returns (Credit Notes) automatically increment and restore perpetual product warehouse inventory balances.
- **FIXED:** Enforced customer credit limits and overdue payment warnings across all sales and billing creation dialogs.
- **FIXED:** High-resolution company logo rendering maintains original aspect ratio without distortion or clipping.
- **FIXED:** Date filters in Daybook, Ledger, and Reports handle end-of-day bounds cleanly (`23:59:59.999999`).
- **FIXED:** All financial computations, tax splits, and currency rounding migrated to Python standard `Decimal`.

---

### 🔍 Phase 2: Audit Weak Spots & Deep Coverage Verification
- **DOCUMENTED:** Comprehensive root-cause analysis of Rule 55 Delivery Challan monetary value suppression vs Tax Invoices.
- **ENHANCED:** `app/services/export_service.py` with `sanitize_excel_cell()` to prevent Formula/CSV injection attacks (`=`, `+`, `-`, `@`) and normalized print titles (`$1:$1`).
- **ADDED:** Deep-coverage audit test suite (`tests/test_deep_coverage_audit.py`) validating 16 complex commercial scenarios:
  1. Mixed GST slabs on single invoice
  2. Sub-rupee rounding-off mechanics
  3. Financial year crossover (31-Mar to 01-Apr)
  4. Invoice cancellation and stock reversal
  5. Multi-line Sales Returns and Credit Notes
  6. Multi-line purchase vouchers and ITC
  7. GSTR-1 B2B / B2CL / B2CS categorization
  8. Trial Balance dual-column equality
  9. FIFO receivables ageing allocation
  10. GSTR-3B Table 4 Input Tax Credit math
  11. Inter-state IGST credit note offsets
  12. P&L Operating Expenses & Net Profit
  13. Multi-tier pricing (Wholesale vs Retail)
  14. Contra transfers between Cash & Bank
  15. Against-reference invoice payment allocation
  16. GSTR-1 Government Offline Tool JSON schema export
- **ADDED:** Independent CI verification script (`scripts/verify_books.py`) performing 7 mathematical and referential checks directly against SQLite database files.

---

### 💾 Phase 3: Data Safety, Migrations & Concurrency
- **ADDED:** Dynamic schema migration engine (`app/database/migrations.py`) with `schema_versions` tracking table.
- **ADDED:** Automatic pre-migration database snapshot creation before applying DDL updates.
- **ADDED:** Automated rolling backup retention maintaining the last 14 backup copies.
- **ADDED:** Single-instance process lock (`.billflow.lock`) with Windows API PID liveness checking and stale lock auto-recovery.
- **ADDED:** Monotonic Clock Guard (`ClockGuard`) detecting backward system clock manipulation > 24 hours.
- **ADDED:** Synchronous debouncing on UI save and export buttons to prevent double-click transaction duplication.

---

### 🔒 Phase 4: Security, RBAC & Audit Trails
- **ADDED:** Role-Based Access Control (RBAC) with 4 user roles: `Admin`, `Accountant`, `Billing`, `Viewer`.
- **ADDED:** Cryptographic password hashing using `scrypt` with 32-byte salt ($N=16384, r=8, p=1$).
- **ADDED:** Automated brute-force lockout: 5 consecutive failed login attempts locks account for 15 minutes.
- **ADDED:** Statutory Period Locking engine (`PeriodLock`) supporting soft and hard locks to freeze closed quarters.
- **ADDED:** Immutable Audit Logging (`AuditLog`) capturing all creates, updates, cancellations, and deletions.
- **AUDITED:** Executed `pip-audit -r requirements.txt` confirming **0 known vulnerabilities**.

---

### 📜 Phase 5: Statutory GST & Compliance Documentation
- **ADDED:** `docs/COMPLIANCE.md` covering:
  - E-invoicing thresholds (> ₹5 Cr B2B mandate and IRP INV-01 workflow).
  - E-way bill rules (Rule 138 thresholds, Part A/B particulars, validity distances).
  - CGST Rule 46: 16 mandatory tax invoice particulars verification matrix.
  - Section 34: Statutory timelines (30th November deadline) for Credit and Debit Notes.
  - 25-point Chartered Accountant Pre-Audit Questionnaire & Sign-Off Template.
- **ADDED:** UI hook in `gst_report_view.py` for one-click export of official GSTR-1 Offline Tool JSON.

---

### 📈 Phase 6: Observability & Performance Benchmarks
- **ADDED:** Structured rotating file logger in `%APPDATA%\BillFlow\logs\billflow.log` (10MB max, keep 5).
- **ADDED:** Global exception hook (`sys.excepthook`) with unique Error Reference IDs (`ERR-YYYYMMDD-XXXXXX`) and a user-friendly Copy Diagnostics dialog.
- **ADDED:** 1-Click Diagnostics Bundle Exporter (`export_diagnostics_bundle`) packaging health reports, system specs, DB stats, and recent logs into a zip.
- **VERIFIED:** Performance stress test on a **32,000+ record database** (`tests/test_performance_stress.py`):
  - Paginated invoice listing: **41.54 ms** (SLA < 2000 ms)
  - Party ledger balance aggregation: **43.00 ms** (SLA < 2000 ms)
  - Monthly GSTR-1 calculation (2,519 invoices): **433.54 ms** (SLA < 2000 ms)
  - 1,000-Row formatted Excel export: **172.20 ms** (SLA < 5000 ms)
  - 10-Item ReportLab Tax Invoice PDF export: **177.22 ms** (SLA < 5000 ms)
- **ENHANCED:** High-DPI PassThrough scale factor policy enabled for crisp display on Windows 125%/150% scaling.

---

### 📦 Phase 7: Packaging, Build Spec & Installer
- **ADDED:** PyInstaller build specification (`build_exe.spec`) bundling all ReportLab fonts, static assets, and models into an optimized windowed binary.
- **ADDED:** Inno Setup 6 installer script (`installer.iss`) targeting `Program Files\BillFlow` with user data, backups, and logs safely redirected to `%APPDATA%\BillFlow`.
- **ADDED:** Uninstall protection preserving user financial databases during application updates or removal.

---

### 📚 Phase 8: Documentation & CI Automation
- **ADDED:** Comprehensive end-user manual (`docs/USER_GUIDE.md`).
- **ADDED:** System administrator manual (`docs/ADMIN_GUIDE.md`).
- **ADDED:** Architectural boundaries and operational guide (`docs/KNOWN_LIMITATIONS.md`).
- **ADDED:** Pre-release verification checklist (`docs/RELEASE_CHECKLIST.md`).
- **ADDED:** Disaster recovery and rollback plan (`docs/ROLLBACK_PLAN.md`).
- **ADDED:** Automated local CI runner (`scripts/release_check.py`) validating the entire suite in a single command.

---
*End of Changelog.*
