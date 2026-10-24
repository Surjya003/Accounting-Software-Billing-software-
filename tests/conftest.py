import os
import sys
from pathlib import Path
import shutil

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DATA_DIR = ROOT_DIR / "data"
TEST_DB_PATH = DATA_DIR / "test_accounting.db"
REAL_DB_PATH = DATA_DIR / "accounting.db"

if REAL_DB_PATH.exists():
    for extra in [TEST_DB_PATH, DATA_DIR / "test_accounting.db-wal", DATA_DIR / "test_accounting.db-shm"]:
        if extra.exists():
            try:
                extra.unlink()
            except Exception:
                pass
    shutil.copy2(REAL_DB_PATH, TEST_DB_PATH)

os.environ["ACCOUNTING_DB_PATH"] = str(TEST_DB_PATH)
os.environ["ACCOUNTING_DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"

from app.database.connection import init_db
init_db()

import pytest

@pytest.fixture
def clean_db():
    yield
