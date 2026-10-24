# BillFlow Suite — Disaster Recovery & Emergency Rollback Plan

**Document Version:** 1.0.0 (Production Release)  
**Applicability:** Production Deployments, Version Upgrades, and Schema Migrations  

---

## 1. Objective & Trigger Conditions

This document defines the emergency rollback procedure in the event that a deployment of BillFlow Suite encounters an unrecoverable runtime regression, data corruption, or severe operational disruption.

### 1.1 Rollback Trigger Criteria
A rollback must be initiated immediately if any of the following occur:
1. **Fatal Startup Crash:** Application terminates immediately on launch across multiple workstations.
2. **Schema Migration Failure:** An automated DDL migration fails midway, leaving the SQLite database in an inconsistent state.
3. **Data Integrity Regression:** `scripts/verify_books.py` reports any failed mathematical check (Trial Balance imbalance, invoice math mismatch, voucher imbalance).
4. **Data Divergence / Corruption:** PRAGMA `integrity_check` returns non-ok status.
5. **Critical Statutory Defect:** Invoices or GSTR-1 returns produce incorrect tax splits.

---

## 2. Emergency Rollback Procedures (Step-by-Step)

### Step 1: Terminate Active Processes
Ensure no instances of `BillFlow.exe` or background Python processes are holding file locks on the database:
```powershell
# Terminate running BillFlow processes
Stop-Process -Name "BillFlow" -Force -ErrorAction SilentlyContinue
# Remove single-instance lock file if process was killed abnormally
Remove-Item -Path "$env:APPDATA\BillFlow\data\.billflow.lock" -Force -ErrorAction SilentlyContinue
```

---

### Step 2: Preserve Current Post-Incident State
Before making any changes, capture a forensic snapshot of the current state:
```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$incident_dir = "$env:APPDATA\BillFlow\incident_$timestamp"
New-Item -ItemType Directory -Path $incident_dir -Force

# Copy database, logs, and lock state
Copy-Item "$env:APPDATA\BillFlow\data\accounting.db*" -Destination $incident_dir
Copy-Item "$env:APPDATA\BillFlow\logs\*" -Destination $incident_dir
```

---

### Step 3: Database Restoration from Pre-Migration Snapshot
BillFlow Suite automatically creates a verified backup before executing any schema migration (`pre_migration_v{version}_{timestamp}.db`) in `%APPDATA%\BillFlow\backups\`.

1. **Locate the latest pre-migration snapshot:**
   ```powershell
   Get-ChildItem -Path "$env:APPDATA\BillFlow\backups" -Filter "pre_migration_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
   ```
2. **Restore the snapshot:**
   ```powershell
   $snapshot = "$env:APPDATA\BillFlow\backups\<selected_pre_migration_file>.db"
   Copy-Item $snapshot -Destination "$env:APPDATA\BillFlow\data\accounting.db" -Force
   # Clean up any leftover WAL/SHM files
   Remove-Item "$env:APPDATA\BillFlow\data\accounting.db-wal" -Force -ErrorAction SilentlyContinue
   Remove-Item "$env:APPDATA\BillFlow\data\accounting.db-shm" -Force -ErrorAction SilentlyContinue
   ```

---

### Step 4: Application Binary Rollback
1. **Uninstall the problematic version:**
   - Run uninstaller: `C:\Program Files\BillFlow\unins000.exe /SILENT`
   - Confirm user data in `%APPDATA%\BillFlow` is intact.
2. **Reinstall the previous known-stable build:**
   - Run previous installer: `BillFlow_Setup_v0.9.x.exe /SILENT`

---

### Step 5: Verification & Integrity Sign-Off
Before releasing the system back to billing operators, verify database integrity:
```powershell
# Run independent books verification
python scripts/verify_books.py "$env:APPDATA\BillFlow\data\accounting.db"
```
**Verification criteria:**
- Output ends with `=== ALL 7 CHECKS PASSED ===`.
- Process exits with code `0`.
- Launch BillFlow, log in, and verify the latest invoice and voucher numbers match expectations.

---

## 3. Post-Incident Review Template

```text
================================================================================
                    INCIDENT & ROLLBACK POST-MORTEM REPORT
================================================================================
Incident ID:           INC-________________________
Date of Incident:      ____________________________
Time Initiated:        ____________    Time Resolved: ____________
Version Rolled Back:   v______         Rolled Back To: v______
Incident Commander:    ____________________________

1. Root Cause Summary:
   _____________________________________________________________________________
   _____________________________________________________________________________

2. Impact Assessment:
   - Downtime Duration:   ______ minutes
   - Financial Records Affected: [ ] None   [ ] Corrected via Snapshot
   - Workstations Affected: ______

3. Corrective Actions Required:
   - [ ] Regression test added to test suite
   - [ ] Migration DDL fix verified on copy database
   - [ ] Re-qualification through full CI gate

Sign-off: ________________________ (Lead Architect)  Date: ____________________
================================================================================
```

---
*End of Rollback Plan.*
