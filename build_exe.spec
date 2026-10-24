# -*- mode: python ; coding: utf-8 -*-
"""
BillFlow Suite - PyInstaller Build Specification
=================================================
Builds a standalone, highly-optimized, enterprise Windows desktop distribution
for BillFlow Suite (Binapani Automation).

Rules:
- Windowed executable (console=False)
- UPX disabled (upx=False) to eliminate antivirus false-positive heuristics
- Embedded Windows file version information resource
- High-DPI multi-size icon (assets/branding/app.ico)
- Read-only bundled data (assets/, themes/)
- Zero database or runtime user data bundled
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT_DIR = os.path.abspath(SPECPATH)

# Ensure version resource exists
version_gen_script = os.path.join(ROOT_DIR, "scripts", "generate_version_resource.py")
if os.path.exists(version_gen_script):
    try:
        import subprocess
        subprocess.run([sys.executable, version_gen_script], check=True, cwd=ROOT_DIR)
    except Exception as e:
        print(f"Warning: could not run generate_version_resource.py: {e}")

version_file = os.path.join(ROOT_DIR, "scripts", "file_version_info.txt")
icon_file = os.path.join(ROOT_DIR, "assets", "branding", "app.ico")

# Core hidden imports required for dynamic dispatch & plugins
hidden_imports = [
    # PySide6 Core & Graphics
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "shiboken6",

    # Database
    "sqlalchemy",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.dialects.sqlite",
    "sqlite3",

    # Security & Cryptography
    "cryptography",
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    "cryptography.hazmat.primitives.kdf.scrypt",
    "cryptography.hazmat.primitives.ciphers.aead",
    "cryptography.hazmat.backends.openssl",

    # Reporting & Spreadsheets
    "reportlab",
    "reportlab.lib",
    "reportlab.platypus",
    "reportlab.pdfgen",
    "reportlab.pdfbase.ttfonts",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.worksheet",
    "openpyxl.utils",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "num2words",

    # Internal App Modules
    "app.version",
    "app.branding",
    "app.config",
    "app.core.paths",
    "app.core.logger",
    "app.core.crash_handler",
    "app.core.diagnostics",
    "app.core.selftest",
    "app.database.models",
    "app.database.connection",
    "app.database.migrations",
    "app.services.auth_service",
    "app.services.audit_service",
    "app.services.system_guard",
    "app.services.license_service",
    "app.services.export_service",
    "app.services.gst_report_service",
    "app.services.inventory_valuation",
    "app.services.validation_helpers",
    "app.services.sample_data",
    "app.services.pdf",
    "app.services.billing.invoice_pdf_generator",
    "app.services.billing.proforma_pdf_generator",
    "app.services.billing.quotation_pdf_generator",
    "app.services.billing.challan_pdf_generator",
    "app.services.billing.return_pdf_generator",
    "app.services.billing.purchase_order_pdf_generator",
    "app.services.pdf.templates.tax_invoice",
    "app.services.pdf.templates.proforma",
    "app.services.pdf.templates.quotation",
    "app.services.pdf.templates.delivery_challan",
    "app.services.pdf.templates.credit_note",
    "app.services.pdf.templates.debit_note",
    "app.services.pdf.templates.purchase_order",
    "app.services.pdf.templates.payment_receipt",
    "app.ui.splash",
    "app.ui.about_dialog",
    "app.ui.save_dialog",
    "app.ui.async_worker",
    "app.ui.main_window",
    "app.ui.theme.theme_manager",
    "app.ui.theme.tokens",
    "app.ui.theme.icons",
    "app.ui.theme.qss_builder",
    "app.ui.theme.themes",
    "app.ui.theme.widgets",
]

hidden_imports += collect_submodules("reportlab")
hidden_imports += collect_submodules("openpyxl")

# Bundled data files
datas = []

# 1. Bundled Brand Assets & Fonts
assets_dir = os.path.join(ROOT_DIR, "assets")
if os.path.isdir(assets_dir):
    datas.append((assets_dir, "assets"))

# 2. Bundled Default Themes
themes_dir = os.path.join(ROOT_DIR, "themes")
if os.path.isdir(themes_dir):
    datas.append((themes_dir, "themes"))

# 3. ReportLab standard fonts (if present in installed package)
try:
    import reportlab
    rl_dir = os.path.dirname(reportlab.__file__)
    rl_fonts = os.path.join(rl_dir, "fonts")
    if os.path.isdir(rl_fonts):
        datas.append((rl_fonts, os.path.join("reportlab", "fonts")))
except ImportError:
    pass

# Carefully targeted exclusions to keep executable lean while preserving stability
excludes = [
    # Testing frameworks
    "pytest",
    "_pytest",
    "unittest",
    "test",
    "tests",

    # GUI toolkits not used
    "tkinter",
    "tcl",

    # Heavy data science / dev tools not used in offline billing desktop
    "IPython",
    "notebook",
    "jupyter",
    "matplotlib",
    "scipy",
    "playwright",
    "selenium",
    "pip_audit",

    # Unused PySide6 / Qt modules (trim distribution size significantly)
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtBluetooth",
    "PySide6.QtPositioning",
    "PySide6.QtDesigner",
    "PySide6.QtUiTools",
    "PySide6.QtHelp",
    "PySide6.QtTest",
    "PySide6.QtNetworkAuth",
]

a = Analysis(
    [os.path.join(ROOT_DIR, "app", "main.py")],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=list(set(hidden_imports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BillFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Hard rule: Disable UPX to prevent antivirus false positives
    console=False,  # Windowed application (no console popup)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.exists(icon_file) else None,
    version=version_file if os.path.exists(version_file) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BillFlow",
)
