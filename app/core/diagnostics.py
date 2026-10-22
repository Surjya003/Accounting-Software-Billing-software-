"""
System Health Check & Runtime Diagnostics Tool
Provides memory profiling, database integrity checks, and thread stack dumps.
"""
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any

from app.core.logger import get_logger, LOG_DIR
from app.database.connection import get_session, engine
from app.database.models import Base

logger = get_logger("diagnostics")


def get_memory_usage_mb() -> float:
    """Returns the current process resident memory usage in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        # Fallback for Windows without psutil using ctypes
        try:
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return round(counters.WorkingSetSize / (1024 * 1024), 2)
        except Exception:
            pass
        return 0.0


def run_system_health_check() -> Dict[str, Any]:
    """
    Performs comprehensive diagnostic inspection:
    1. SQLite Database integrity & PRAGMAs (WAL, busy_timeout)
    2. Read/write latency
    3. Process memory usage
    4. Active threads count
    5. Log files availability
    """
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "pid": os.getpid(),
        "memory_mb": get_memory_usage_mb(),
        "active_threads": len(sys._current_frames()),
        "status": "HEALTHY",
        "warnings": [],
    }

    # 1. Database Check & Latency
    t0 = time.perf_counter()
    try:
        with engine.connect() as conn:
            # Check WAL mode
            wal = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
            # Check busy timeout
            timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
            # Fast integrity check
            integrity = conn.exec_driver_sql("PRAGMA quick_check").scalar()
            
            db_ms = (time.perf_counter() - t0) * 1000.0
            report["db"] = {
                "latency_ms": round(db_ms, 2),
                "journal_mode": wal,
                "busy_timeout_ms": timeout,
                "integrity": integrity,
            }
            if integrity != "ok":
                report["status"] = "CORRUPTED"
                report["warnings"].append(f"SQLite quick_check reported: {integrity}")
            if timeout < 5000:
                report["warnings"].append(f"Low SQLite busy_timeout ({timeout}ms) may cause 'database is locked' errors.")
    except Exception as e:
        report["status"] = "ERROR"
        report["warnings"].append(f"Database error: {e}")
        logger.error("Health check database failure: %s", e)

    # 2. Check Memory usage
    if report["memory_mb"] > 500.0:
        report["warnings"].append(f"High memory consumption: {report['memory_mb']} MB")

    # 3. Log file status
    app_log = LOG_DIR / "app.log"
    report["log_file_size_kb"] = round(app_log.stat().st_size / 1024, 1) if app_log.exists() else 0

    logger.info("System Health Check: %s | Memory: %s MB | Latency: %s ms",
                report["status"], report["memory_mb"], report.get("db", {}).get("latency_ms", "N/A"))
    return report


def dump_thread_stacks() -> str:
    """Captures and writes the stack trace of every active thread to data/logs/thread_dump.log."""
    lines = [
        f"\n{'='*70}",
        f"THREAD STACK DUMP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Memory: {get_memory_usage_mb()} MB | Active Threads: {len(sys._current_frames())}",
        f"{'='*70}"
    ]
    for thread_id, frame in sys._current_frames().items():
        lines.append(f"\n[Thread ID: {thread_id}]")
        for line in traceback.format_stack(frame):
            lines.append("  " + line.rstrip())
    
    dump_text = "\n".join(lines)
    dump_file = LOG_DIR / "thread_dump.log"
    try:
        with open(dump_file, "a", encoding="utf-8") as f:
            f.write(dump_text + "\n")
    except Exception as e:
        logger.error("Failed to write thread dump: %s", e)

    logger.info("Thread dump saved to %s", dump_file)
    return dump_text
