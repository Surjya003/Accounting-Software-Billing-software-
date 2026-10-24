# BillFlow Suite — Windows Build & Release Engineering Guide

## 1. Release Architecture & Metadata
- **Product Name:** BillFlow Suite
- **Executable Name:** `BillFlow.exe`
- **Company / Publisher:** Binapani Automation
- **Author / Made by:** Surjyakamal Saha
- **Single Source of Truth for Version:** [`app/version.py`](file:///c:/Users/surjy/OneDrive/Desktop/Accounting%20Software/app/version.py)
- **AppId GUID:** `{B111F10A-7C1B-4A5D-8E2F-1A3C5B7D9E0F}` (CRITICAL: Never change this GUID; Inno Setup uses it for upgrade detection and downgrade prevention).
- **Single-Instance Mutex:** `BillFlowSuite_SingleInstance_Mutex`

---

## 2. Prerequisites
The production build pipeline has been validated with the following tooling:
1. **Operating System:** Windows 10 / Windows 11 (64-bit)
2. **Python Environment:** Python 3.14 (or Python 3.11/3.12 64-bit)
3. **Core Dependencies:**
   - PySide6 (>= 6.8.0)
   - SQLAlchemy (>= 2.0.0)
   - ReportLab (>= 4.0.0)
   - OpenPyXL (>= 3.1.0)
   - Cryptography (>= 42.0.0)
   - Pillow (>= 10.0.0)
   - PyInstaller (>= 6.11.0) & pyinstaller-hooks-contrib (>= 2024.0)
4. **Installer Compiler:** Inno Setup 6 or 7
   - Default 64-bit installation path: `C:\Program Files\Inno Setup 7\ISCC.exe` or `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

---

## 3. One-Command Automated Release Build
To execute the complete production build pipeline:

```cmd
build_release.bat
```
or via Python directly:
```cmd
python scripts\build_release.py
```

### Build Pipeline Stages:
1. **Clean:** Purges `build/`, `dist/`, and `release/` artifacts to prevent stale cache contamination.
2. **Branding Assets:** Generates multi-size `assets/branding/app.ico` (16 to 256px), Inno Setup wizard bitmaps (`wizard.bmp` 164x314, `wizard_small.bmp` 55x58), and Windows version-info resource (`scripts/file_version_info.txt`).
3. **Automated Verification:** Runs pre-build regression test gates.
4. **PyInstaller Compilation:** Produces a standalone, single-file executable in `dist\BillFlow.exe` (or onedir bundle in `dist\BillFlow\` via `--onedir`) with console disabled (`console=False`), UPX disabled (`upx=False` to prevent AV false positives), and size trimming for unused Qt modules. Because `dist\BillFlow.exe` is completely self-contained, it can be executed from any folder or copied directly to `C:\Program Files\Billflow` without requiring a separate `_internal` directory.
5. **Data Safety Assertion:** Verifies that ZERO databases (`*.db`, `*.sqlite`), backups (`*.enc`), logs, or developer test files are bundled into `dist\`.
6. **Qt Plugin Audit:** Confirms `platforms/qwindows.dll`, `imageformats`, and `iconengines/qsvg` are present and operational.
7. **Headless Frozen Self-Test:** Executes `dist\BillFlow.exe --selftest --no-splash --data-dir=<temp>` verifying all 8 PDF document generators, encrypted backup/restore, Unicode/Hindi font rendering, and theme engines in a sandboxed directory.
8. **Inno Setup Compilation:** Compiles `installer.iss` with `ISCC.exe` into `release\BillFlow_Setup_v{version}.exe`.
9. **Checksums:** Calculates SHA-256 digests and outputs `release\SHA256SUMS.txt`.

---

## 4. Manual Compilation with Inno Setup Desktop IDE
You can also compile the installer using the Inno Setup GUI:
1. Launch **Inno Setup Compiler** from the Windows Start menu.
2. Open [`installer.iss`](file:///c:/Users/surjy/OneDrive/Desktop/Accounting%20Software/installer.iss).
3. Press **F9** (or menu *Build* -> *Compile*).
4. The compiled installer will be saved to `release\BillFlow_Setup_v{version}.exe`.
*Note:* The script contains `#ifndef AppVersion` guards and automatically detects the version from `dist\BillFlow\BillFlow.exe` via `GetVersionNumbersString` with a fallback constant.

---

## 5. Version Bumping Workflow
1. Open [`app/version.py`](file:///c:/Users/surjy/OneDrive/Desktop/Accounting%20Software/app/version.py).
2. Update `VERSION = "X.Y.Z"` and `VERSION_TUPLE = (X, Y, Z, 0)`.
3. Run `build_release.bat`.
4. All targets (exe version resource, About dialog, splash screen, Inno installer filename, and uninstall registry) will automatically synchronize to the new version.

---

## 6. Directory Layout & User Data Architecture
BillFlow Suite strictly separates **read-only application binaries** from **writable enterprise financial records**:

### Application Installation Directory (Read-Only)
- Per-user install: `%LOCALAPPDATA%\Programs\BillFlow Suite\`
- All-users install: `C:\Program Files\BillFlow Suite\`
- Contains: `BillFlow.exe`, Qt DLLs, Python runtime, bundled read-only assets in `assets/` and themes in `themes/`.
- **CRITICAL:** The app never writes logs, databases, or temp files to this folder.

### User Data Directory (Writable)
All runtime state lives under `%APPDATA%\BillFlow\`:
- `%APPDATA%\BillFlow\data\accounting.db` — SQLite enterprise accounting database (WAL mode).
- `%APPDATA%\BillFlow\backups\` — AES-256-GCM encrypted automated and manual backups.
- `%APPDATA%\BillFlow\logs\` — Rotating application and crash logs (`billflow.log`).
- `%APPDATA%\BillFlow\exports\` — Customer invoices, Day Books, GSTR reports in PDF and Excel.
- `%APPDATA%\BillFlow\themes\` — User customized color themes.

---

## 7. Backup and Data Disaster Recovery
### Restoring Data on a New PC:
1. Install BillFlow Suite on the target PC using `BillFlow_Setup_vX.Y.Z.exe`.
2. Launch BillFlow Suite once to initialize the directory structure, then close it.
3. Copy the encrypted backup file (`*.enc`) to the target machine.
4. Launch BillFlow Suite, navigate to **Settings -> Backup & Security -> Restore Backup**, enter the backup password, and select the `.enc` file.
5. Alternatively, copy `accounting.db` directly to `%APPDATA%\BillFlow\data\accounting.db`.

---

## 8. Code Signing Guide (EV / OV / Azure Trusted Signing)
Code signing removes the Windows Defender SmartScreen "Unknown Publisher" prompt:

### Option A: Hardware Token / PFX Certificate via SignTool
Run SignTool from Windows SDK:
```cmd
signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 /d "BillFlow Suite" "release\BillFlow_Setup_v1.0.0.exe"
```

### Option B: Enabling SignTool in Inno Setup
1. In Inno Setup IDE, open *Tools* -> *Configure Sign Tools...*.
2. Add a sign tool named `standard` with command:
   ```cmd
   "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe" sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f
   ```
3. In [`installer.iss`](file:///c:/Users/surjy/OneDrive/Desktop/Accounting%20Software/installer.iss), uncomment:
   ```ini
   SignTool=standard
   SignedUninstaller=yes
   ```

---

## 9. Publishing Updates & Upgrade Protocol
1. **In-place Upgrade:** Installing a newer version over an older version automatically detects the existing installation via `AppId`, preserves all `%APPDATA%\BillFlow\` data intact, and runs database schema migrations automatically on next launch.
2. **Downgrade Refusal:** The installer queries the Windows Uninstall registry. If an attempt is made to install an older version over a newer version, the setup displays an error and exits to prevent database schema corruption.
3. **Running Instance Guard:** If BillFlow Suite is open, both the installer and uninstaller detect `BillFlowSuite_SingleInstance_Mutex` and require the user to close the app before proceeding.

---

## 10. Known Technical Limitations
1. **Architecture:** Native 64-bit x64 Windows binary; 32-bit (x86) Windows systems are not supported.
2. **Operating System:** Supported on Windows 10 (version 1809+) and Windows 11.
3. **Database at Rest:** The SQLite database is stored locally. While database backups are AES-256-GCM encrypted, the live working database relies on Windows NTFS User Profile encryption (EFS / BitLocker).
