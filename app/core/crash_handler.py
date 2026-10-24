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


import uuid
import platform
from app.version import VERSION as APP_VERSION
APP_NAME = "BillFlow Suite"

def generate_error_id() -> str:
    """Generates a structured, unique error reference ID."""
    now_str = datetime.now().strftime("%Y%m%d")
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"ERR-{now_str}-{short_uid}"


def handle_uncaught_exception(exc_type, exc_value, exc_traceback, show_dialog: bool = True):
    """
    Global exception hook. Replaces sys.excepthook to intercept unhandled errors.
    Prevents silent crashes, writes to crash.log with a unique Error Reference ID,
    and shows an informative dialog with copy diagnostics capability.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow Ctrl+C to exit normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_id = generate_error_id()
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    crash_report = (
        f"\n{'='*70}\n"
        f"CRASH REPORT - {timestamp} | Error Ref ID: {error_id}\n"
        f"Exception: {exc_type.__name__}: {exc_value}\n"
        f"Platform: {platform.platform()} | Python: {platform.python_version()}\n"
        f"{'='*70}\n"
        f"{tb_text}\n"
    )

    # 1. Log to rotating logger
    logger.critical("UNCAUGHT EXCEPTION [%s]:\n%s", error_id, crash_report)

    # 2. Append to dedicated crash log file
    try:
        with open(str(CRASH_LOG_FILE), "a", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception as io_err:
        if sys.stderr:
            sys.stderr.write(f"Failed to write to crash log: {io_err}\n")

    if sys.stderr:
        sys.stderr.write(crash_report)

    # 3. If Qt GUI is running and not in automated test, display user-friendly error dialog
    if show_dialog and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
            from PySide6.QtCore import Qt

            app = QApplication.instance()
            if app:
                diag = QDialog()
                diag.setWindowTitle(f"{APP_NAME} - Unexpected Error [{error_id}]")
                diag.resize(560, 400)
                layout = QVBoxLayout(diag)
                layout.setContentsMargins(18, 18, 18, 18)
                layout.setSpacing(12)

                lbl_title = QLabel(f"⚠️ An unexpected error occurred in {APP_NAME}")
                lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc2626;")
                layout.addWidget(lbl_title)

                lbl_ref = QLabel(f"<b>Error Reference ID:</b> <code style='font-size:13px;'>{error_id}</code>")
                lbl_ref.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(lbl_ref)

                lbl_desc = QLabel(f"<b>Details:</b> {exc_type.__name__}: {exc_value}")
                lbl_desc.setWordWrap(True)
                layout.addWidget(lbl_desc)

                txt_tb = QTextEdit()
                txt_tb.setReadOnly(True)
                txt_tb.setPlainText(tb_text)
                txt_tb.setMaximumHeight(150)
                layout.addWidget(txt_tb)

                diagnostics_payload = (
                    f"App: {APP_NAME} v{APP_VERSION}\n"
                    f"Error Reference ID: {error_id}\n"
                    f"Time: {timestamp}\n"
                    f"Platform: {platform.platform()}\n"
                    f"Python: {platform.python_version()}\n"
                    f"Exception: {exc_type.__name__}: {exc_value}\n\n"
                    f"Traceback:\n{tb_text}"
                )

                btn_box = QHBoxLayout()
                btn_copy = QPushButton("📋 Copy Diagnostics to Clipboard")
                btn_copy.clicked.connect(lambda: [
                    QApplication.clipboard().setText(diagnostics_payload),
                    btn_copy.setText("✓ Copied to Clipboard!")
                ])
                btn_box.addWidget(btn_copy)
                btn_box.addStretch()

                btn_close = QPushButton("Close")
                btn_close.clicked.connect(diag.accept)
                btn_box.addWidget(btn_close)
                layout.addLayout(btn_box)

                diag.exec()
        except Exception:
            pass


def install_crash_handler():
    """Installs the global exception hook and low-level fault handler."""
    setup_faulthandler()
    sys.excepthook = handle_uncaught_exception
    logger.info("Global exception hook installed successfully.")

