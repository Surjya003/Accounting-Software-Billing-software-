"""
Core package initialization: Logging, Crash Handling, Diagnostics
"""
from app.core.logger import setup_logging, get_logger
from app.core.crash_handler import install_crash_handler, dump_all_threads

