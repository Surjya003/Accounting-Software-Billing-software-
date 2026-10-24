# BillFlow Suite — Pre-Flight Release Checklist

**Release Target:** BillFlow Suite v1.0.0  
**Publisher:** Binapani Automation  
**Author:** Surjyakamal Saha  
**Installer:** `release\BillFlow_Setup_v1.0.0.exe`  

Before distributing any new release to end users, execute this manual checklist sequentially:

---

### Phase 1: Automated Build & Verification Gate
- [ ] Run `build_release.bat` from clean working copy.
- [ ] Verify exit code is 0 and output confirms:
  - 0 user databases or developer data bundled inside `dist\BillFlow\`
  - Headless `--selftest` passes with exit code 0 (all 8 PDFs, Excel, encrypted backup)
  - Inno Setup compiles with 0 errors and 0 warnings
  - `release\SHA256SUMS.txt` generated

---

### Phase 2: Fresh Machine Installation Test
- [ ] Copy `BillFlow_Setup_v{version}.exe` to a clean Windows 10 or 11 test machine (or Windows Sandbox).
- [ ] **SmartScreen Note:** When running an unsigned installer, Windows Defender SmartScreen displays *"Windows protected your PC"*.
  - Click **More info**.
  - Verify Publisher displays **Binapani Automation** (or *Unknown Publisher* until EV/OV signed).
  - Click **Run anyway**.
- [ ] Verify Install Scope selection dialog appears:
  - Default: *Install for me only (recommended)* (`%LOCALAPPDATA%\Programs\BillFlow Suite\`)
  - Optional: *Install for all users* (`C:\Program Files\BillFlow Suite\`)
- [ ] Complete installation wizard and verify:
  - Desktop shortcut created (if selected)
  - Start Menu shortcuts created:
    - *BillFlow Suite*
    - *Open BillFlow Data Folder*
    - *Uninstall BillFlow Suite*
  - Finish page displays credit: *"Made by Surjyakamal Saha"*
  - "Launch BillFlow Suite" launches application smoothly with brand splash screen.

---

### Phase 3: Core Functional Smoke Test
- [ ] **Initial Database Setup:** App opens on fresh database with no existing customer data.
- [ ] **Company Profile:** Enter Company Name, GSTIN, Address, Bank Details, and save.
- [ ] **Party & Product:** Create one Customer party and one Product with GST rate.
- [ ] **Tax Invoice Generation:** Create an invoice with the product.
- [ ] **PDF Print / Export:** Generate Tax Invoice PDF; open in PDF viewer and confirm:
  - Brand/Company details match profile
  - Vertical grid lines extend to footer
  - Amount in words displays *"Rupees ... Only"*
  - Signature and seal blocks are positioned properly
- [ ] **Other Document Exports:** Generate Quotation, Delivery Challan, Proforma, Credit Note.
- [ ] **Encrypted Backup:** Go to Settings -> Backup; generate an AES-256-GCM encrypted backup (`*.enc`).
- [ ] **Disaster Recovery Restore:** Restore the backup and verify data parity.

---

### Phase 4: Upgrade & Downgrade Protection Gate
- [ ] With BillFlow Suite running, attempt to run the installer again.
  - *Requirement:* Setup alerts that BillFlow Suite is running via `BillFlowSuite_SingleInstance_Mutex` and asks to close it.
- [ ] Install a newer version over an older version:
  - *Requirement:* Setup installs smoothly in-place; all customer data in `%APPDATA%\BillFlow\` is preserved; schema migrations execute cleanly.
- [ ] Attempt to install an older version over a newer version:
  - *Requirement:* Setup displays downgrade prevention error message and aborts.

---

### Phase 5: Uninstallation & Data Preservation Gate
- [ ] Close BillFlow Suite.
- [ ] Run uninstaller from Windows Settings -> Installed Apps (or Start Menu shortcut).
- [ ] At the uninstallation prompt:
  - Select **NO** to keep financial data.
- [ ] Verify results:
  - Application binary folder (`%LOCALAPPDATA%\Programs\BillFlow Suite\` or `C:\Program Files\BillFlow Suite\`) is completely removed.
  - Shortcuts on Desktop and Start Menu are removed.
  - Add/Remove Programs registry entry is removed.
  - **CRITICAL:** `%APPDATA%\BillFlow\` (`data\accounting.db`, `backups\`, `logs\`, `exports\`) remains completely intact.
- [ ] Test silent `/DELETEDATA=1` parameter on a disposable test machine to confirm complete cleanup when explicitly commanded.
