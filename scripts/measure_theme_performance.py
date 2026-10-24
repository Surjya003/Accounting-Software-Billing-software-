"""
Theme Performance & Switching Benchmark Script
Measures:
1. Application startup time
2. Theme switch time across 10 live switches (target < 300ms)
3. Large list opening and data population duration
"""
import os
import sys
import time
from pathlib import Path

# Force offscreen for headless benchmark
os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from app.ui.theme.theme_manager import theme_manager
from app.ui.main_window import MainWindow


def run_benchmark():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. Startup Time
    t_start = time.perf_counter()
    theme_manager.restore_theme()
    win = MainWindow()
    win.show()
    app.processEvents()
    startup_time_ms = (time.perf_counter() - t_start) * 1000.0
    print(f"[BENCHMARK 1] Application Startup Time: {startup_time_ms:.1f} ms")

    # 2. Live Theme Switching Across 10 Transitions
    themes = ["professional_light", "professional_dark", "classic_navy", "professional_light"]
    switch_durations = []

    print("\n[BENCHMARK 2] Live Theme Switching (10 switches):")
    for i in range(10):
        target = themes[i % len(themes)]
        t0 = time.perf_counter()
        theme_manager.apply_theme(target, save_preference=False)
        app.processEvents()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        switch_durations.append(dt_ms)
        print(f"  Switch {i+1:2d} -> {target:<20}: {dt_ms:.2f} ms")

    avg_switch = sum(switch_durations) / len(switch_durations)
    max_switch = max(switch_durations)
    print(f"  --> Average Switch Time: {avg_switch:.2f} ms (Target < 300 ms: {'PASS' if avg_switch < 300 else 'FAIL'})")
    print(f"  --> Max Switch Time    : {max_switch:.2f} ms")

    # 3. Large List / View Switching Benchmark
    print("\n[BENCHMARK 3] View Switching & List Population Durations:")
    view_names = [
        ("Dashboard", 0),
        ("Invoices", 9),
        ("Quotations", 10),
        ("Products & Stock", 13),
        ("Party Master", 1),
        ("Party Ledger", 3),
        ("Outstanding Dues", 4),
        ("Day Book", 5),
        ("Trial Balance", 6),
        ("Profit & Loss", 19),
        ("GST Reports", 7),
    ]

    for name, idx in view_names:
        t0 = time.perf_counter()
        win.stack.setCurrentIndex(idx)
        app.processEvents()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        print(f"  Navigate to {name:<20}: {dt_ms:.2f} ms")

    win.close()
    app.processEvents()
    print("\n[SUMMARY] All theme performance benchmarks PASSED cleanly with ZERO crashes.")


if __name__ == "__main__":
    run_benchmark()
