"""
Centralized Application Logging Configuration
Handles console logging and rotating file logs in data/logs/app.log.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def _resolve_log_dir() -> Path:
    """Resolves enterprise log directory, preferring %APPDATA%/BillFlow/logs on Windows with fallback."""
    appdata = os.environ.get("APPDATA")
    if appdata and os.name == "nt":
        target = Path(appdata) / "BillFlow" / "logs"
        try:
            target.mkdir(parents=True, exist_ok=True)
            test_file = target / ".write_test"
            test_file.touch()
            test_file.unlink()
            return target
        except Exception:
            pass
    # Fallback to local data/logs
    local_target = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
    local_target.mkdir(parents=True, exist_ok=True)
    return local_target


LOG_DIR = _resolve_log_dir()
LOG_FILE = LOG_DIR / "billflow.log"
# Backward-compatibility alias for older references
APP_LOG_FILE = LOG_FILE

_is_configured = False


def setup_logging(level=logging.INFO) -> logging.Logger:
    """Configures root logger with rotating file and console handlers."""
    global _is_configured
    if _is_configured:
        return logging.getLogger("vyapar")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Format: Timestamp | Level | Thread | Module:Line | Message
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Rotating File Handler (10MB per file, up to 5 backups)
    try:
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Failed to initialize file logger at {LOG_FILE}: {e}\n")

    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _is_configured = True
    logger = logging.getLogger("vyapar")
    logger.info(f"=== Application Logging Started. Log file: {LOG_FILE} ===")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Returns a namespaced logger."""
    if not _is_configured:
        setup_logging()
    return logging.getLogger(f"vyapar.{name}")
