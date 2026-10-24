# BillFlow Suite — Pre-Release Verification Checklist

**Target Release:** v1.0.0 (Production Release)  
**Branch:** `release/production-ready`  
**Execution Environment:** Windows 10/11 x64, Python 3.14.3  

---

## 1. Automated Test Suites & Regression Gates

All automated test gates must execute with **100% pass rate** before packaging:

- [ ] **Gate 1: Dependency Vulnerability Audit**
  ```bash
  python -m pip_audit -r requirements.txt
  ```
  *Requirement:* Exit code 0, 0 known vulnerabilities found.

- [ ] **Gate 2: Core QA Test Suite**
  ```bash
  python tests/test_full_qa_suite.py
  ```
  *Requirement:* 38/38 tests passing (100%).

- [ ] **Gate 3: Deep Coverage Audit Suite**
  ```bash
  pytest tests/test_deep_coverage_audit.py
  ```
  *Requirement:* 16/16 scenarios passing (100%).

- [ ] **Gate 4: Phase 3 Data Safety Suite**
  ```bash
  pytest tests/test_phase3_data_safety.py
  ```
  *Requirement:* 5/5 tests passing (100%).

- [ ] **Gate 5: Phase 4 Security & RBAC Suite**
  ```bash
  pytest tests/test_phase4_security_rbac.py
  ```
  *Requirement:* 5/5 tests passing (100%).

- [ ] **Gate 6: Performance & Stress Benchmarks**
  ```bash
  pytest tests/test_performance_stress.py -v -s
  ```
  *Requirement:* 32k record test database, all queries < 2.0s, all exports < 5.0s.

- [ ] **Gate 7: Independent Books Sanity Verification**
  ```bash
  python scripts/verify_books.py data/test_accounting.db
  ```
  *Requirement:* All 7 mathematical and referential checks pass with Exit Code 0.

- [ ] **Gate 8: Master Release Runner**
  ```bash
  python scripts/release_check.py
  ```
  *Requirement:* Consolidated runner confirms 100% pass across all modules.

---

## 2. Document & PDF Visual Review

- [ ] Verify Tax Invoice PDF layout against reference `docs/reference/12-signed.pdf`:
  - Seller and Buyer GSTIN and State Codes present.
  - Dates strictly in `DD-MM-YYYY` format.
  - Amount in words strictly formatted as `"Rupees ... Only"`.
  - Signature and seal blocks positioned safely in free space without covering text.
  - Vertical column grid lines stretch continuously to the footer.
- [ ] Verify Delivery Challan PDF properly suppresses monetary amounts per Rule 55.
- [ ] Verify Quotation PDF displays validity period and customer enquiry reference.
- [ ] Verify Proforma Invoice PDF displays distinct Proforma title and bank details.
- [ ] Verify Credit Note PDF displays Section 34 reference and linked original invoice number.

---

## 3. Packaging & Installer Build

- [ ] **PyInstaller Build:**
  ```bash
  pyinstaller build_exe.spec --clean -y
  ```
  *Requirement:* Produces `dist/BillFlow/BillFlow.exe` with no missing DLL or import errors.
- [ ] **Launch Standalone Binary:**
  ```bash
  dist\BillFlow\BillFlow.exe
  ```
  *Requirement:* Application launches cleanly, applies enterprise theme, and opens Dashboard.
- [ ] **Inno Setup Build:**
  ```bash
  iscc installer.iss
  ```
  *Requirement:* Produces `dist_installer\BillFlow_Setup_v1.0.0.exe`.

---

## 4. Fresh Installation & Smoke Test

- [ ] Install `BillFlow_Setup_v1.0.0.exe` on a clean Windows machine / user profile.
- [ ] Confirm installation path defaults to `C:\Program Files\BillFlow\` (or `%LOCALAPPDATA%\Programs\BillFlow`).
- [ ] Confirm active database creates cleanly in `%APPDATA%\BillFlow\data\accounting.db`.
- [ ] Confirm logs write to `%APPDATA%\BillFlow\logs\billflow.log`.
- [ ] Perform End-to-End Billing Smoke Test:
  1. Create Party (Customer).
  2. Create Product with 18% GST.
  3. Create Tax Invoice (Verify CGST+SGST math and PDF generation).
  4. Record Receipt Voucher in Cash & Bank.
  5. Check Daybook and Trial Balance equality.
  6. Export GSTR-1 Offline JSON from GST Reports view.
  7. Generate 1-Click Database Backup in Settings.
- [ ] Test Uninstallation:
  - Uninstall via Windows Settings / Control Panel.
  - Verify executable files in Program Files are removed.
  - **CRITICAL:** Verify `%APPDATA%\BillFlow\data\accounting.db` and backups are **PRESERVED**.

---
*Sign-off Authority: Lead QA Engineer & Release Manager*
