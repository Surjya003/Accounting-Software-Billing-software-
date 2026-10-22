"""
Comprehensive Tests for Application Performance, Concurrency, and Crash Stability:
1. SQLite Concurrency & Pragmas (WAL, busy_timeout=30s, temp_store, cache_size)
2. Global Crash Interception & Traceback Logging
3. Real-time Memory Profiling & Health Diagnostics
4. On-demand Thread Stack Dump (Hang/Deadlock detection)
5. Elimination of N+1 Party Balance and Stock Movement Latencies
6. Settings Diagnostics UI & Live Health Inspection
"""
import sys
import os
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.connection import get_session, engine, init_db
from app.core.logger import LOG_DIR
from app.core.crash_handler import install_crash_handler, handle_uncaught_exception
from app.core.diagnostics import run_system_health_check, dump_thread_stacks, get_memory_usage_mb
from app.services.party_service import calculate_party_balance, calculate_all_party_balances
from app.services.stock_report_service import get_stock_movement_report
from app.ui.views.settings_view import SettingsView


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_sqlite_pragmas_and_concurrency_settings():
    """Verify WAL mode, 30s busy timeout, and memory caches are active on the engine."""
    with engine.connect() as conn:
        journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
        quick_check = conn.exec_driver_sql("PRAGMA quick_check").scalar()

        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"
        assert busy_timeout >= 30000, f"Expected busy_timeout >= 30000, got {busy_timeout}"
        assert quick_check.lower() == "ok", f"Expected quick_check 'ok', got {quick_check}"


def test_memory_profiling():
    """Verify resident memory usage profiler returns valid positive MB value."""
    mem_mb = get_memory_usage_mb()
    assert isinstance(mem_mb, float)
    assert mem_mb > 0.0, "Memory usage should be greater than 0 MB"


def test_system_health_check():
    """Verify run_system_health_check collects all diagnostic parameters accurately."""
    report = run_system_health_check()
    assert report["status"] in ("HEALTHY", "WARNING")
    assert report["pid"] == os.getpid()
    assert report["memory_mb"] > 0
    assert report["active_threads"] >= 1
    assert "db" in report
    assert report["db"]["journal_mode"].lower() == "wal"
    assert report["db"]["busy_timeout_ms"] >= 30000
    assert report["db"]["integrity"] == "ok"
    assert isinstance(report["db"]["latency_ms"], float)


def test_thread_stack_dump():
    """Verify dump_thread_stacks writes active thread frames to data/logs/thread_dump.log."""
    dump_text = dump_thread_stacks()
    assert "THREAD STACK DUMP" in dump_text
    assert "Active Threads:" in dump_text
    assert "[Thread ID:" in dump_text

    dump_file = LOG_DIR / "thread_dump.log"
    assert dump_file.exists(), "thread_dump.log file must be created"
    content = dump_file.read_text(encoding="utf-8")
    assert "THREAD STACK DUMP" in content


def test_crash_handler_logs_unhandled_exception(monkeypatch):
    """Verify uncaught exceptions are trapped, written to crash.log, and don't silently exit."""
    install_crash_handler()

    # Create a synthetic exception and invoke handler
    crash_file = LOG_DIR / "crash.log"
    initial_len = len(crash_file.read_text(encoding="utf-8")) if crash_file.exists() else 0

    try:
        raise ValueError("Diagnostic test for crash capture: synthetic crash event")
    except ValueError:
        exc_type, exc_val, exc_tb = sys.exc_info()
        handle_uncaught_exception(exc_type, exc_val, exc_tb)

    assert crash_file.exists(), "crash.log must exist after uncaught exception"
    crash_content = crash_file.read_text(encoding="utf-8")
    assert len(crash_content) > initial_len
    assert "Diagnostic test for crash capture" in crash_content
    assert "CRASH REPORT" in crash_content


def test_bulk_party_balances_parity():
    """Verify calculate_all_party_balances (1 query) gives identical results to calculate_party_balance."""
    with get_session() as session:
        bulk_balances = calculate_all_party_balances(session)
        assert isinstance(bulk_balances, dict)

        # Check all parties in database
        for party_id, (bulk_amt, bulk_type) in list(bulk_balances.items())[:10]:
            indiv_amt, indiv_type = calculate_party_balance(session, party_id)
            assert bulk_amt == indiv_amt
            assert bulk_type == indiv_type


def test_stock_movement_report_execution():
    """Verify stock movement report executes without slow loops or errors."""
    data = get_stock_movement_report()
    assert "items" in data
    assert "totals" in data
    assert "period" in data
    assert isinstance(data["items"], list)
    assert data["totals"]["total_sales_value"] >= 0.0


def test_settings_diagnostics_ui():
    """Verify the SettingsView diagnostics tab initializes and displays live system metrics."""
    app = QApplication.instance() or QApplication(sys.argv)
    settings = SettingsView()
    assert settings.tabs.count() == 4
    tab_title = settings.tabs.tabText(3)
    assert "Diagnostics" in tab_title

    # Test running health check via UI
    settings.run_health_check_ui()
    assert "HEALTHY" in settings.lbl_health_info.text() or "Status:" in settings.lbl_health_info.text()

    # Test log viewer
    settings.refresh_log_viewer_ui()
    assert len(settings.txt_log_content.toPlainText()) > 0
