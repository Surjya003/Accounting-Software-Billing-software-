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
        from app.database.connection import engine
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


def export_diagnostics_bundle(output_path: str = None) -> str:
    """
    Creates a comprehensive, sanitized diagnostics zip archive containing:
    1. system_health.json (health check + latency + memory)
    2. environment.json (OS platform, Python, architecture, active threads)
    3. configuration.json (sanitized config, paths, license metadata)
    4. db_health.json (integrity check, foreign key check, table stats)
    5. Recent log tails (billflow.log, crash.log, thread_dump.log)
    """
    import zipfile
    import json
    import platform
    from pathlib import Path
    from app.config import (
        APP_NAME, APP_VERSION, EXPORTS_DIR, DB_PATH, BACKUP_DIR, TRIAL_DAYS
    )
    from app.services.license_service import get_license_status

    if not output_path:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(EXPORTS_DIR / f"BillFlow_Diagnostics_{ts}.zip")

    # 1. System Health Report
    health_data = run_system_health_check()

    # 2. Environment Info
    env_info = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_compiler": platform.python_compiler(),
        "process_id": os.getpid(),
        "memory_rss_mb": get_memory_usage_mb(),
        "active_threads_count": len(sys._current_frames()),
    }

    # 3. Sanitized Config
    lic = get_license_status()
    config_info = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "trial_days": TRIAL_DAYS,
        "db_path_exists": Path(DB_PATH).exists(),
        "db_size_bytes": Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0,
        "backup_dir_exists": Path(BACKUP_DIR).exists(),
        "exports_dir_exists": Path(EXPORTS_DIR).exists(),
        "license_status": {
            "status_text": lic.get("status_text"),
            "is_licensed": lic.get("is_licensed"),
            "is_trial": lic.get("is_trial"),
            "machine_id": lic.get("machine_id"),
        }
    }

    # 4. Database Health & Table Counts
    db_health = {"status": "UNKNOWN"}
    try:
        from app.database.migrations import check_database_health
        db_health = check_database_health(DB_PATH)
    except Exception as e:
        db_health["error"] = str(e)

    # 5. Build ZIP
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("system_health.json", json.dumps(health_data, indent=2))
        zf.writestr("environment.json", json.dumps(env_info, indent=2))
        zf.writestr("configuration.json", json.dumps(config_info, indent=2))
        zf.writestr("database_health.json", json.dumps(db_health, indent=2))

        # Include recent log tails
        for log_name in ["billflow.log", "app.log", "crash.log", "thread_dump.log"]:
            log_p = LOG_DIR / log_name
            if log_p.exists():
                try:
                    with open(log_p, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        tail_lines = lines[-500:] if len(lines) > 500 else lines
                        zf.writestr(f"logs/{log_name}", "".join(tail_lines))
                except Exception as log_err:
                    zf.writestr(f"logs/{log_name}.error", str(log_err))

    logger.info("Exported diagnostics bundle to %s", output_path)
    return output_path
