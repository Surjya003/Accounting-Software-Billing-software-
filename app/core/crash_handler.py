"""
Global Crash Prevention, Faulthandler, and Exception Hook
Catches and logs all unhandled exceptions, thread hangs, and C-level crashes.
"""
import sys
import os
import faulthandler
import traceback
import logging
from datetime import datetime
from pathlib import Path

from app.core.logger import LOG_DIR, get_logger

logger = get_logger("crash_handler")

CRASH_LOG_FILE = LOG_DIR / "crash.log"
FAULT_LOG_FILE = LOG_DIR / "crash_fault.log"

_fault_file_handle = None


def setup_faulthandler():
    """Enables Python faulthandler to capture low-level segfaults and C-crashes."""
    global _fault_file_handle
    try:
        _fault_file_handle = open(str(FAULT_LOG_FILE), "a", encoding="utf-8")
        faulthandler.enable(file=_fault_file_handle, all_threads=True)
        logger.info("Faulthandler enabled (logging C-level faults to %s)", FAULT_LOG_FILE)
    except Exception as e:
        logger.warning("Could not enable faulthandler: %s", e)


def dump_all_threads() -> str:
    """Returns a full stack trace of all running threads (useful for detecting deadlocks & hangs)."""
    lines = [f"\n=== THREAD DUMP AT {datetime.now().isoformat()} ==="]
    for thread_id, frame in sys._current_frames().items():
        lines.append(f"\n--- Thread ID: {thread_id} ---")
        for line in traceback.format_stack(frame):
            lines.append(line.rstrip())
    dump_str = "\n".join(lines)
    
    # Write to diagnostics log
    diag_file = LOG_DIR / "thread_dump.log"
    try:
        with open(diag_file, "a", encoding="utf-8") as f:
            f.write(dump_str + "\n")
    except Exception:
        pass
    
    logger.info("Thread dump saved to %s", diag_file)
    return dump_str


def handle_uncaught_exception(exc_type, exc_value, exc_traceback, show_dialog: bool = True):
    """
    Global exception hook. Replaces sys.excepthook to intercept unhandled errors.
    Prevents silent crashes, writes to crash.log, and shows a helpful message.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow Ctrl+C to exit normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    crash_report = (
        f"\n{'='*70}\n"
        f"CRASH REPORT - {timestamp}\n"
        f"Exception: {exc_type.__name__}: {exc_value}\n"
        f"{'='*70}\n"
        f"{tb_text}\n"
    )

    # 1. Log to rotating logger
    logger.critical("UNCAUGHT EXCEPTION:\n%s", crash_report)

    # 2. Append to dedicated crash log file
    try:
        with open(str(CRASH_LOG_FILE), "a", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception as io_err:
        sys.stderr.write(f"Failed to write to crash log: {io_err}\n")

    sys.stderr.write(crash_report)

    # 3. If Qt GUI is running and not in automated test, display user-friendly error dialog
    if show_dialog and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app:
                err_msg = (
                    f"An unexpected error occurred:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"A diagnostic report has been saved to:\n"
                    f"{CRASH_LOG_FILE}\n\n"
                    f"The application will attempt to continue running safely."
                )
                QMessageBox.critical(None, "Application Error", err_msg)
        except Exception:
            pass


def install_crash_handler():
    """Installs the global exception hook and low-level fault handler."""
    setup_faulthandler()
    sys.excepthook = handle_uncaught_exception
    logger.info("Global exception hook installed successfully.")
