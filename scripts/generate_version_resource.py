"""
Generates Windows File Version Info resource for PyInstaller.
Source of truth: app/version.py and app/branding.py.
"""
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.version import VERSION, VERSION_TUPLE
from app.branding import APP_NAME, BRAND_NAME, MAKER_NAME, COPYRIGHT_YEAR

OUTPUT_FILE = WORKSPACE / "scripts" / "file_version_info.txt"

content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_TUPLE},
    prodvers={VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{BRAND_NAME}'),
            StringStruct('FileDescription', '{APP_NAME}'),
            StringStruct('FileVersion', '{VERSION}.0'),
            StringStruct('InternalName', 'BillFlow'),
            StringStruct('LegalCopyright', 'Copyright (C) {COPYRIGHT_YEAR} {BRAND_NAME}. Made by {MAKER_NAME}'),
            StringStruct('OriginalFilename', 'BillFlow.exe'),
            StringStruct('ProductName', '{APP_NAME}'),
            StringStruct('ProductVersion', '{VERSION}.0'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

OUTPUT_FILE.write_text(content, encoding="utf-8")
print(f"Generated version resource: {OUTPUT_FILE}")
