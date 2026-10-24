# BillFlow Suite — Known Limitations & Architectural Notes

This document transparently records known architectural boundaries, current design decisions, and recommended production practices for BillFlow Suite.

---

### 1. Stock Valuation Method (Weighted Average Cost)
- **Current Behavior**: Inventory valuation is calculated using **Weighted Average Cost (WAC)** as the standard default method across P&L, stock reports, and dashboard KPIs:
  $$\text{WAC Unit Cost} = \frac{\text{Total Cumulative Inward Purchase Value}}{\text{Total Cumulative Inward Purchase Quantity}}$$
- **Limitation**: Individual batch-level First-In-First-Out (FIFO) physical lot tracking with per-lot expiry layers is **not implemented**.
- **Audit Verification**: Proved by hand calculation: Buy 10 @ ₹1,000 + Buy 10 @ ₹2,000 $\rightarrow$ Weighted Average Unit Cost = ₹1,500.00. Selling 10 units yields COGS = ₹15,000.00 and Closing Stock = ₹15,000.00.

---

### 2. Database Storage & Encryption at Rest
- **Current Behavior**: Primary operational database is stored locally in standard SQLite database format with Write-Ahead Logging (`WAL` mode) enabled for concurrency, integrity, and crash safety.
- **Limitation**: Native SQL database file-level runtime encryption (such as SQLCipher) is **not available on Windows Python 3.14** due to lack of prebuilt binary wheels on PyPI/conda.
- **Enterprise Protection Implemented**:
  1. **AES-256-GCM Encrypted Backups**: Backups can be exported as AES-256-GCM encrypted `.enc` archives with PBKDF2 key derivation (100,000 SHA-256 rounds), rendering the snapshot mathematically unreadable without the passphrase.
  2. **Operating System At-Rest Security**: For full disk encryption of primary working databases at rest, organizations should enable:
     - Windows: **BitLocker** Drive Encryption
     - macOS: **FileVault**
     - Linux: **LUKS** / dm-crypt


---

### 3. Hardware Lock & Trial Period Reset Boundaries
- **Current Behavior**: The software provides a **14-day free trial** from first launch, enforced via HMAC-SHA256 machine fingerprinting (combining Windows MachineGuid, MAC address, and CPU identifiers) with monotonic timestamp anti-tamper clock verification.
- **Limitation**: Because the application operates **100% offline without remote telemetry**:
  - Deleting the local SQLite database file resets the trial state unless a commercial key has been activated.
  - Manual system clock rollback is detected and blocks trial usage, but firmware-level clock manipulation prior to database initialization cannot be completely prevented offline.

---

### 4. Purchase Returns Flow
- **Current Behavior**: Full Debit Note & Purchase Return accounting, stock reduction, and GST ledger synchronization are implemented and tested at the service layer (`return_service.create_purchase_return()`).
- **UI Workflow**: In the Purchase Orders view, clicking **"Return Goods"** on a received PO initiates the return flow against the supplier and order.

---

### 5. Multi-Thread Database Session Scope
- **Rule**: SQLAlchemy database sessions (`SessionLocal` / `get_session()`) must **never be shared across background threads**.
- **Implementation**: Background worker threads (`AsyncWorker` / `run_in_background`) and UI export workers instantiate their own short-lived database sessions with `BEGIN IMMEDIATE` transaction serialization for sequence numbering.

---

### 6. Concurrency & Network Drive Topology
- **Current Architecture**: Standalone desktop deployment using local SQLite 3 in Write-Ahead Logging (`WAL`) mode.
- **Concurrency Characteristics**:
  - Supports **unlimited concurrent readers** without locking read queries.
  - Automatically serializes write transactions with a 30-second busy timeout (`PRAGMA busy_timeout=30000`).
- **Limitation**: While safe across multiple threads in a single process, running SQLite across SMB/CIFS network mapped drives with multiple simultaneous writing workstations can experience Windows SMB file locking latency.
- **Recommendation**: For multi-user environments with more than 3 simultaneous billing counters, run BillFlow in terminal services/RDP sessions or maintain local client databases with daily master synchronization.

---

### 7. E-Invoicing Thresholds & Real-Time Portal Connectivity
- **Statutory Threshold**: Mandated for businesses with aggregate turnover exceeding **₹5 Crores**.
- **Current Architecture**: BillFlow Suite is an **offline desktop system**. It exports compliant **GSTR-1 JSON** files and B2B invoice tables matching the official GST Offline Tool schema.
- **Limitation**: Direct real-time API push to NIC IRP (Invoice Registration Portal) for instantaneous IRN and digital QR code signing requires an active internet connection and authorized GSP (GST Suvidha Provider) credentials.
- **Workflow**: For enterprises > ₹5 Cr turnover, export the B2B batch JSON from BillFlow and upload via the free Government Offline Utility or authorized GSP portal.

---

### 8. Single-Page vs Multi-Page PDF Invoice Layouts
- **Current Behavior**: Tax invoices with 1 to 10 items render in an elegant, fixed-height single-page layout with unbroken vertical column rules stretching to the summary footer.
- **Boundary**: Invoices containing more than 15–20 line items automatically paginate into multi-page documents with repeating table headers and carry-forward sub-totals.

