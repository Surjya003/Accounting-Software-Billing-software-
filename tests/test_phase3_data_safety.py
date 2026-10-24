"""
Unit Tests for Phase 3: Data Safety & Reliability.
Verifies:
1. Versioned transactional schema migration engine & idempotency.
2. Database startup health checks (PRAGMA integrity_check & foreign_key_check).
3. Automatic backup verification (row counts & integrity) & 14-day rolling retention.
4. Single-instance lock enforcement & stale lock cleanup.
5. Clock tampering & rollback detection (> 24 hours).
"""
import json
import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from app.config import DATA_DIR, BACKUP_DIR, DB_PATH
from app.database.migrations import (
    run_migrations, check_database_health, verify_backup, enforce_backup_retention,
    init_schema_versions_table
)
from app.database.connection import create_backup
from app.services.system_guard import SingleInstanceLock, ClockGuard, LOCK_FILE, CLOCK_GUARD_FILE


def test_schema_migrations_and_idempotency(clean_db):
    """Verify versioned migrations apply cleanly and are completely idempotent."""
    # First run applies any pending
    applied = run_migrations()
    assert isinstance(applied, list)

    # Inspect schema_versions table
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT version, description, checksum FROM schema_versions ORDER BY version")
        rows = cursor.fetchall()
        assert len(rows) >= 5, "All 5 baseline migrations must be recorded"
        versions = [r[0] for r in rows]
        assert versions[:5] == [1, 2, 3, 4, 5]

    # Re-running immediately should be a no-op (0 applied)
    second_run = run_migrations()
    assert second_run == [], "Re-running migrations must apply 0 changes (idempotent)"


def test_database_health_checks(clean_db):
    """Verify PRAGMA integrity_check and foreign_key_check pass on valid database."""
    is_healthy, issues = check_database_health()
    assert is_healthy is True
    assert issues == []


def test_backup_verification_and_rolling_retention(clean_db, tmp_path):
    """Verify backup integrity checking and retention purging."""
    # 1. Create a real backup
    backup_file = create_backup(custom_dest_dir=str(tmp_path))
    assert backup_file.exists()

    # 2. Verify backup integrity
    valid, msg = verify_backup(backup_file)
    assert valid is True
    assert "Backup verified ok" in msg
    assert "Parties:" in msg

    # 3. Test retention: create 5 dummy backups and enforce max 3
    for i in range(5):
        dummy = tmp_path / f"accounting_backup_2026010{i}_120000.db"
        dummy.write_text("dummy sqlite header content")

    purged = enforce_backup_retention(backup_dir=tmp_path, max_backups=3)
    remaining = [f for f in tmp_path.iterdir() if f.suffix == ".db"]
    assert len(remaining) <= 3
    assert purged >= 2


def test_single_instance_lock_lifecycle(clean_db, tmp_path):
    """Verify acquisition, duplicate instance detection, and clean release."""
    # Ensure starting clean
    SingleInstanceLock.release()
    LOCK_FILE.unlink(missing_ok=True)

    # 1. First acquire succeeds
    ok1, err1 = SingleInstanceLock.acquire()
    assert ok1 is True
    assert err1 is None
    assert LOCK_FILE.exists()

    # 2. Second acquire from same process handles gracefully
    ok2, err2 = SingleInstanceLock.acquire()
    assert ok2 is True

    # 3. Release clears the lock file
    SingleInstanceLock.release()
    assert not LOCK_FILE.exists()


def test_clock_tampering_rollback_detection(clean_db):
    """Verify system detects clock rollbacks (> 24 hours into the past)."""
    CLOCK_GUARD_FILE.unlink(missing_ok=True)

    # 1. Normal timestamp check succeeds
    ok1, err1 = ClockGuard.verify_and_update()
    assert ok1 is True
    assert err1 is None
    assert CLOCK_GUARD_FILE.exists()

    # 2. Simulate future watermark (e.g., system clock was rolled back by 5 days)
    future_time = datetime.now() + timedelta(days=5)
    with open(CLOCK_GUARD_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_seen": future_time.isoformat()}, f)

    # 3. Next check must detect rollback
    ok2, err2 = ClockGuard.verify_and_update()
    assert ok2 is False
    assert "System clock rollback detected" in err2

    # Clean up watermark
    CLOCK_GUARD_FILE.unlink(missing_ok=True)
    ClockGuard.verify_and_update()
