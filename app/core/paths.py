"""
BillFlow Suite - Centralized Path & Resource Management
=======================================================
Single source of truth for read-only bundled assets (resource_path)
and writable runtime user data (user_data_dir).

Guarantees:
- In frozen production (PyInstaller):
    Read-only resources load from sys._MEIPASS.
    Writable paths (database, backups, logs, exports, custom themes, logos)
    always reside under %APPDATA%\\BillFlow\\ (data\\, backups\\, logs\\, exports\\, themes\\).
    NEVER writes to the application install folder (Program Files).
- In development / test mode:
    Preserves repository-relative directories (./data, ./backups, etc.)
    and respects ACCOUNTING_DB_PATH / BILLFLOW_DATA_DIR overrides so all
    unit and regression test suites pass cleanly.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Union

# Global override for testing or CLI argument (--data-dir <path>)
_CUSTOM_USER_DATA_DIR: Optional[Path] = None


def is_frozen() -> bool:
    """Returns True if the application is running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False)


def get_project_root() -> Path:
    """Returns the repository/project root directory in dev mode."""
    return Path(__file__).resolve().parent.parent.parent


def resource_path(relative_path: Union[str, Path] = "") -> Path:
    """
    Returns an absolute Path to a read-only bundled resource.
    In frozen mode: resolves relative to sys._MEIPASS.
    In dev mode: resolves relative to project root.
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = get_project_root()

    rel = Path(relative_path) if relative_path else Path("")
    return base / rel


def set_custom_data_dir(custom_path: Union[str, Path, None]) -> None:
    """
    Overrides the writable user data root directory.
    Useful for --data-dir CLI flag, test fixtures, and isolated testing.
    """
    global _CUSTOM_USER_DATA_DIR
    if custom_path:
        p = Path(custom_path).resolve()
        _CUSTOM_USER_DATA_DIR = p
        os.environ["BILLFLOW_DATA_DIR"] = str(p)
        ensure_user_dirs()
    else:
        _CUSTOM_USER_DATA_DIR = None
        os.environ.pop("BILLFLOW_DATA_DIR", None)


def user_data_root() -> Path:
    """
    Returns the root directory where user financial data and logs are stored.
    """
    # 1. Explicit in-process override
    if _CUSTOM_USER_DATA_DIR is not None:
        return _CUSTOM_USER_DATA_DIR

    # 2. Environment variable override
    env_dir = os.environ.get("BILLFLOW_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    # 3. Frozen production mode or forced user data mode -> %APPDATA%\BillFlow
    if is_frozen() or os.environ.get("BILLFLOW_FORCE_USER_DATA") == "1":
        appdata = os.environ.get("APPDATA")
        if appdata and os.name == "nt":
            return Path(appdata) / "BillFlow"
        return Path.home() / ".billflow"

    # 4. Development mode -> repository root
    return get_project_root()


def user_data_dir(subdir: str = "") -> Path:
    """
    Returns the path to a specific writable user directory
    (e.g., 'data', 'backups', 'logs', 'exports', 'themes').
    """
    root = user_data_root()
    if subdir:
        return root / subdir
    return root


def ensure_user_dirs() -> None:
    """
    Ensures all standard writable user data directories exist on disk with write permissions.
    """
    for sub in ["data", "backups", "logs", "exports", "themes"]:
        d = user_data_dir(sub)
        d.mkdir(parents=True, exist_ok=True)


def get_data_dir() -> Path:
    """Returns the writable data/ directory (stores SQLite DB, lock file, time guard)."""
    return user_data_dir("data")


def get_backup_dir() -> Path:
    """Returns the writable backups/ directory."""
    return user_data_dir("backups")


def get_logs_dir() -> Path:
    """Returns the writable logs/ directory."""
    return user_data_dir("logs")


def get_exports_dir() -> Path:
    """Returns the writable exports/ directory (PDFs and Excel spreadsheets)."""
    return user_data_dir("exports")


def get_themes_dir() -> Path:
    """Returns the user custom themes/ directory."""
    return user_data_dir("themes")


def get_db_path() -> Path:
    """
    Returns the path to the primary SQLite database file.
    Respects ACCOUNTING_DB_PATH if set.
    """
    env_path = os.environ.get("ACCOUNTING_DB_PATH")
    if env_path:
        return Path(env_path).resolve()
    return get_data_dir() / "accounting.db"


def get_database_uri() -> str:
    """
    Returns SQLAlchemy database connection URI.
    Respects ACCOUNTING_DATABASE_URI if set.
    """
    env_uri = os.environ.get("ACCOUNTING_DATABASE_URI")
    if env_uri:
        return env_uri
    return f"sqlite:///{get_db_path()}"


def get_asset_path(relative_path: Union[str, Path] = "") -> Path:
    """
    Resolves an asset path inside the bundled or development assets/ directory.
    """
    rel = Path(relative_path)
    if "assets" in rel.parts:
        return resource_path(rel)
    return resource_path(Path("assets") / rel)


def get_bundled_fonts_dir() -> Path:
    """Returns the directory containing bundled Unicode TrueType fonts."""
    return resource_path("assets/fonts")


def get_bundled_font_path(font_filename: str) -> Path:
    """Returns path to a specific bundled TrueType font file."""
    return resource_path(f"assets/fonts/{font_filename}")


def get_lock_file() -> Path:
    """Returns path to the single-instance application lock file."""
    return get_data_dir() / ".billflow.lock"


def get_clock_guard_file() -> Path:
    """Returns path to the anti-rollback clock watermark file."""
    return get_data_dir() / ".time_guard"
