import sqlite3
import subprocess
import sys
import tempfile
import os
import shutil
import pytest
from pathlib import Path

def test_wal_checkpoint_truncate_empties_wal():
    """
    Defect 8 Proof Part 1:
    Prove that after transactions, running PRAGMA wal_checkpoint(TRUNCATE)
    flushes all pages and reduces .db-wal file size to 0 bytes.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test_wal.db"
        wal_path = Path(temp_dir) / "test_wal.db-wal"

        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, val TEXT)")

        # Insert transactions to populate WAL
        for i in range(100):
            conn.execute("INSERT INTO test_data (val) VALUES (?)", (f"Data entry {i}",))
        conn.commit()

        # WAL file must exist and have content
        assert wal_path.exists(), "WAL file should exist after commits in WAL mode"
        wal_size_before = wal_path.stat().st_size
        assert wal_size_before > 0, f"WAL size before checkpoint should be > 0, got {wal_size_before}"

        # Run wal_checkpoint(TRUNCATE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        res = cursor.fetchone()
        conn.close()

        # Checkpoint result is (busy, log, checkpointed)
        # res[0] == 0 means successful checkpoint
        assert res[0] == 0, f"Checkpoint failed: {res}"

        # After TRUNCATE checkpoint, WAL file size must be 0
        wal_size_after = wal_path.stat().st_size if wal_path.exists() else 0
        assert wal_size_after == 0, f"WAL file should be truncated to 0 bytes, got {wal_size_after}"
        print(f"\n[VERIFIED Defect 8 Truncate] WAL size before: {wal_size_before} bytes -> after: {wal_size_after} bytes")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_crash_recovery_from_wal_on_next_start():
    """
    Defect 8 Proof Part 2:
    Simulate a killed process that leaves uncheckpointed WAL file.
    Use a subprocess that writes committed transactions and terminates abruptly with os._exit(1)
    (leaving the WAL file uncheckpointed on disk).
    Prove that on next start, SQLite WAL recovery transparently reads all committed
    data and completes integrity check without corruption.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "crash_test.db"
        wal_path = Path(temp_dir) / "crash_test.db-wal"

        # Spawn a subprocess that commits data and kills itself via os._exit(1)
        sub_code = f"""
import sqlite3, os
conn = sqlite3.connect(r"{db_path}")
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("CREATE TABLE ledger (id INTEGER PRIMARY KEY, note TEXT, amount REAL)")
conn.execute("INSERT INTO ledger (note, amount) VALUES ('Opening Balance', 50000.0)")
conn.execute("INSERT INTO ledger (note, amount) VALUES ('Invoice #101', 12500.0)")
conn.commit()
# Abrupt crash without clean sqlite3 close or atexit
os._exit(99)
"""
        proc = subprocess.run([sys.executable, "-c", sub_code])
        assert proc.returncode == 99, f"Subprocess should exit with 99, got {proc.returncode}"

        # Verify WAL file exists with uncheckpointed data
        assert wal_path.exists(), "WAL file must exist after abrupt process crash"
        wal_size = wal_path.stat().st_size
        assert wal_size > 0, f"WAL size should be > 0, got {wal_size}"
        print(f"\n[Crash Sim] Uncheckpointed WAL size after abrupt crash: {wal_size} bytes")

        # Process 2 (Next Start / Recovery): Re-open database
        conn2 = sqlite3.connect(str(db_path))
        cursor2 = conn2.cursor()
        cursor2.execute("PRAGMA integrity_check")
        integrity = cursor2.fetchone()[0]
        assert integrity == "ok", f"Integrity check failed: {integrity}"

        cursor2.execute("SELECT COUNT(*), SUM(amount) FROM ledger")
        count, total = cursor2.fetchone()
        assert count == 2, f"Expected 2 rows, got {count}"
        assert total == 62500.0, f"Expected total 62500.0, got {total}"

        # Now clean exit with checkpoint
        cursor2.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn2.close()

        final_wal_size = wal_path.stat().st_size if wal_path.exists() else 0
        assert final_wal_size == 0
        print(f"[VERIFIED Defect 8 Recovery] Recovered {count} rows totaling {total}, integrity={integrity}, final WAL={final_wal_size} bytes")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
