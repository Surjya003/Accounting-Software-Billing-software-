"""
System Guard Service for BillFlow Suite (Phase 3).
Handles:
1. Single-Instance Lock (.billflow.lock with PID liveness detection).
2. Clock Tampering & Rollback Detection (watermark timestamp tracking).
3. Automated Daily Startup / Exit Backups with 14-day rolling retention.
"""
import atexit
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from app.config import DATA_DIR, BACKUP_DIR
from app.database.connection import create_backup
from app.database.migrations import enforce_backup_retention, check_database_health, verify_backup

logger = logging.getLogger("BillFlow.SystemGuard")

LOCK_FILE = DATA_DIR / ".billflow.lock"
CLOCK_GUARD_FILE = DATA_DIR / ".time_guard"


def is_pid_alive(pid: int) -> bool:
    """Checks if a given process ID is currently running on the operating system."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


class SingleInstanceLock:
    """Enforces single running application instance using PID-verified lock file."""
    _acquired = False

    @classmethod
    def acquire(cls, force_clear_stale: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Attempts to acquire the single-instance lock.
        Returns (success: bool, error_message: Optional[str]).
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                locked_pid = data.get("pid")
                locked_time = data.get("started_at", "Unknown")

                if locked_pid and locked_pid != current_pid and is_pid_alive(locked_pid):
                    if not force_clear_stale:
                        msg = f"Another instance of BillFlow Suite is already running (PID {locked_pid}, started {locked_time})."
                        return False, msg
                    logger.warning(f"Forced clearance of active lock PID {locked_pid}.")
                else:
                    logger.info(f"Removing stale lock file from dead PID {locked_pid}.")
            except Exception as e:
                logger.warning(f"Unreadable lock file: {e}. Clearing.")

            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass

        # Write new lock file
        try:
            lock_data = {
                "pid": current_pid,
                "started_at": datetime.now().isoformat(),
                "python_version": sys.version
            }
            with open(LOCK_FILE, "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2)
            cls._acquired = True
            atexit.register(cls.release)
            return True, None
        except Exception as e:
            return False, f"Failed to acquire application lock: {e}"

    @classmethod
    def release(cls):
        """Releases the lock file if owned by the current process."""
        if not cls._acquired:
            return
        try:
            if LOCK_FILE.exists():
                with open(LOCK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("pid") == os.getpid():
                    LOCK_FILE.unlink(missing_ok=True)
                    logger.info("Released single-instance application lock.")
        except Exception:
            pass
        finally:
            cls._acquired = False


class ClockGuard:
    """Detects system clock rollbacks (> 24 hours in the past) to protect financial data integrity."""

    @classmethod
    def verify_and_update(cls) -> Tuple[bool, Optional[str]]:
        """
        Checks current system time against recorded watermark.
        Returns (is_valid: bool, error_message: Optional[str]).
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()

        if CLOCK_GUARD_FILE.exists():
            try:
                with open(CLOCK_GUARD_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                last_seen_str = data.get("last_seen")
                if last_seen_str:
                    last_seen = datetime.fromisoformat(last_seen_str)
                    # If system clock was moved backward by more than 24 hours
                    if now < (last_seen - timedelta(hours=24)):
                        diff = last_seen - now
                        msg = (
                            f"System clock rollback detected! Current time ({now.strftime('%Y-%m-%d %H:%M')}) "
                            f"is {diff.days} days behind last recorded activity ({last_seen.strftime('%Y-%m-%d %H:%M')})."
                        )
                        logger.critical(msg)
                        return False, msg

                    # If moved forward normally or backward by < 24h, take the max watermark
                    if last_seen > now:
                        now = last_seen
            except Exception as e:
                logger.warning(f"Error reading clock watermark: {e}")

        # Update watermark
        try:
            with open(CLOCK_GUARD_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_seen": now.isoformat()}, f, indent=2)
            return True, None
        except Exception as e:
            logger.warning(f"Error saving clock watermark: {e}")
            return True, None


def perform_startup_safety_checks(auto_backup: bool = True) -> Dict[str, Any]:
    """
    Executes full startup safety suite:
    1. Single-instance acquisition.
    2. Clock tampering verification.
    3. SQLite PRAGMA integrity_check.
    4. Scheduled daily automatic backup with rolling 14-day retention.
    """
    results = {
        "lock_ok": True,
        "lock_error": None,
        "clock_ok": True,
        "clock_error": None,
        "integrity_ok": True,
        "integrity_issues": [],
        "backup_path": None,
        "backups_purged": 0
    }

    # 1. Lock check
    lock_ok, lock_err = SingleInstanceLock.acquire()
    results["lock_ok"] = lock_ok
    results["lock_error"] = lock_err

    # 2. Clock guard check
    clock_ok, clock_err = ClockGuard.verify_and_update()
    results["clock_ok"] = clock_ok
    results["clock_error"] = clock_err

    # 3. Database health check
    health_ok, issues = check_database_health()
    results["integrity_ok"] = health_ok
    results["integrity_issues"] = issues

    # 4. Automated backup & retention
    if auto_backup and health_ok:
        try:
            b_path = create_backup()
            valid, v_msg = verify_backup(b_path)
            if valid:
                results["backup_path"] = str(b_path)
                purged = enforce_backup_retention(max_backups=14)
                results["backups_purged"] = purged
                logger.info(f"Startup backup verified and secured: {b_path.name}. Purged {purged} old backups.")
            else:
                logger.error(f"Startup backup failed verification: {v_msg}")
        except Exception as e:
            logger.warning(f"Startup automatic backup failed: {e}")

    return results
