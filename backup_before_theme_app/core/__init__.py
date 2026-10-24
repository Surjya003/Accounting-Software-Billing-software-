"""
Core package initialization: Logging, Crash Handling, Diagnostics
"""
from app.core.logger import setup_logging, get_logger
from app.core.crash_handler import install_crash_handler, dump_all_threads
from app.core.diagnostics import run_system_health_check, dump_thread_stacks, get_memory_usage_mb
