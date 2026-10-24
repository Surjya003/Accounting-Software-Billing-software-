# -*- mode: python ; coding: utf-8 -*-
"""
BillFlow Suite - PyInstaller Build Specification
Builds standalone, optimized Windows desktop executable for BillFlow Suite v1.0.0.
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
ROOT_DIR = os.path.abspath(SPECPATH)

# Collect submodules
hidden_imports = [
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    # Database
    "sqlalchemy",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.ext.baked",
    "sqlite3",
    # Documents & Exports
    "reportlab",
    "reportlab.lib",
    "reportlab.platypus",
    "reportlab.pdfgen",
    "reportlab.pdfbase.ttfonts",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.worksheet",
    "barcode",
    "barcode.writer",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "num2words",
    # Security & RBAC
    "cryptography",
    "cryptography.hazmat.primitives.kdf.scrypt",
    "cryptography.hazmat.backends.openssl",
    # App internals
    "app.database.models",
    "app.database.migrations",
    "app.services.auth_service",
    "app.services.audit_service",
    "app.services.system_guard",
    "app.services.gst_report_service",
    "app.services.export_service",
    "app.services.inventory_valuation",
    "app.core.logger",
    "app.core.crash_handler",
    "app.core.diagnostics",
]

# Additional submodules from core packages
hidden_imports += collect_submodules("reportlab")
hidden_imports += collect_submodules("openpyxl")
hidden_imports += collect_submodules("barcode")

# Data files to bundle
datas = [
    (os.path.join(ROOT_DIR, "docs", "COMPLIANCE.md"), "docs"),
]

# If company logo exists, include it
logo_path = os.path.join(ROOT_DIR, "data", "company_logo.png")
if os.path.exists(logo_path):
    datas.append((logo_path, "data"))

# Collect reportlab standard fonts if present
try:
    import reportlab
    rl_dir = os.path.dirname(reportlab.__file__)
    rl_fonts = os.path.join(rl_dir, "fonts")
    if os.path.isdir(rl_fonts):
        datas.append((rl_fonts, os.path.join("reportlab", "fonts")))
except ImportError:
    pass

a = Analysis(
    [os.path.join(ROOT_DIR, "app", "main.py")],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=list(set(hidden_imports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "unittest",
        "tkinter",
        "IPython",
        "notebook",
        "matplotlib",
        "scipy",
        "pip_audit",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
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
    upx=True,
    console=False,  # Windowed desktop application (no console popup)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT_DIR, "data", "app_icon.ico") if os.path.exists(os.path.join(ROOT_DIR, "data", "app_icon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BillFlow",
)
