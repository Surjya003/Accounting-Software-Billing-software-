"""
Unit Tests for app.core.paths Module
====================================
Tests path resolution in both standard development mode and simulated
PyInstaller frozen mode (sys.frozen + sys._MEIPASS).
"""
import os
import sys
import tempfile
from pathlib import Path
import pytest

from app.core.paths import (
    is_frozen,
    resource_path,
    user_data_root,
    user_data_dir,
    ensure_user_dirs,
    get_data_dir,
    get_backup_dir,
    get_logs_dir,
    get_exports_dir,
    get_themes_dir,
    get_db_path,
    get_database_uri,
    get_asset_path,
    get_bundled_font_path,
    set_custom_data_dir,
)


def test_dev_mode_path_resolution(monkeypatch):
    """Verifies that in standard dev mode, resources resolve to repo and writable dirs follow dev convention."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delenv("BILLFLOW_DATA_DIR", raising=False)
    monkeypatch.delenv("BILLFLOW_FORCE_USER_DATA", raising=False)
    set_custom_data_dir(None)

    assert not is_frozen()
    res = resource_path("assets/branding/logo.svg")
    assert res.exists()
    assert "assets" in str(res)

    # Dev mode root is repository root
    data_d = get_data_dir()
    assert data_d.name == "data"
    assert "data" in str(data_d)


def test_frozen_mode_path_resolution(monkeypatch, tmp_path):
    """Verifies that in simulated frozen mode, resource_path uses sys._MEIPASS and writable dirs use %APPDATA%."""
    fake_meipass = tmp_path / "fake_meipass"
    fake_meipass.mkdir()
    fake_asset = fake_meipass / "assets" / "test.txt"
    fake_asset.parent.mkdir(parents=True)
    fake_asset.write_text("frozen_content")

    fake_appdata = tmp_path / "AppData" / "Roaming"
    fake_appdata.mkdir(parents=True)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)
    monkeypatch.setenv("APPDATA", str(fake_appdata))
    monkeypatch.delenv("BILLFLOW_DATA_DIR", raising=False)
    monkeypatch.delenv("ACCOUNTING_DB_PATH", raising=False)
    monkeypatch.delenv("ACCOUNTING_DATABASE_URI", raising=False)
    set_custom_data_dir(None)

    assert is_frozen()

    # Read-only resource resolves to _MEIPASS
    resolved_res = resource_path("assets/test.txt")
    assert resolved_res == fake_asset
    assert resolved_res.read_text() == "frozen_content"

    # Writable user data root must resolve to %APPDATA%\BillFlow
    expected_root = fake_appdata / "BillFlow"
    assert user_data_root() == expected_root

    assert get_data_dir() == expected_root / "data"
    assert get_backup_dir() == expected_root / "backups"
    assert get_logs_dir() == expected_root / "logs"
    assert get_exports_dir() == expected_root / "exports"
    assert get_themes_dir() == expected_root / "themes"

    # Ensure user dirs creates them safely
    ensure_user_dirs()
    assert (expected_root / "data").exists()
    assert (expected_root / "backups").exists()
    assert (expected_root / "logs").exists()
    assert (expected_root / "exports").exists()
    assert (expected_root / "themes").exists()

    # Database file path inside AppData
    db_p = get_db_path()
    assert db_p == expected_root / "data" / "accounting.db"
    assert get_database_uri() == f"sqlite:///{db_p}"


def test_custom_data_dir_override(tmp_path):
    """Verifies that custom data dir override (--data-dir or BILLFLOW_DATA_DIR) directs all writable paths to custom folder."""
    custom_dir = tmp_path / "custom_billflow_data"
    set_custom_data_dir(custom_dir)

    try:
        assert user_data_root() == custom_dir.resolve()
        assert get_data_dir() == custom_dir / "data"
        assert get_backup_dir() == custom_dir / "backups"
        assert get_logs_dir() == custom_dir / "logs"
        assert get_exports_dir() == custom_dir / "exports"
        assert (custom_dir / "data").exists()
    finally:
        set_custom_data_dir(None)
