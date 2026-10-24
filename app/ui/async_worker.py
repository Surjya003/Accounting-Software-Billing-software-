"""
Background Async Worker Infrastructure for BillFlow Suite
Ensures long-running exports and calculations execute in background threads
using QThreadPool / QRunnable without locking or freezing the Qt UI.
"""
from typing import Callable, Any, Optional
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool


class WorkerSignals(QObject):
    started = Signal()
    finished = Signal()
    error = Signal(Exception)
    result = Signal(object)


class AsyncWorker(QRunnable):
    """
    QRunnable worker running a callable on the global QThreadPool.
    Communicates results, errors, and completion via WorkerSignals back to the Qt main thread.
    Each worker function creates its own DB session and never shares sessions across threads.
    """
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(res)
        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()


def run_in_background(
    fn: Callable,
    on_result: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    on_finished: Optional[Callable[[], None]] = None,
    trigger_button: Optional[Any] = None,
    *args,
    **kwargs
) -> AsyncWorker:
    """
    Disables trigger_button, executes fn on QThreadPool, and delivers
    results or errors back to the UI on the main Qt thread.
    """
    if trigger_button is not None:
        try:
            trigger_button.setEnabled(False)
        except Exception:
            pass

    worker = AsyncWorker(fn, *args, **kwargs)

    def _cleanup():
        if trigger_button is not None:
            try:
                trigger_button.setEnabled(True)
            except Exception:
                pass
        if on_finished is not None:
            on_finished()

    if on_result is not None:
        worker.signals.result.connect(on_result)
    if on_error is not None:
        worker.signals.error.connect(on_error)
    worker.signals.finished.connect(_cleanup)

    QThreadPool.globalInstance().start(worker)
    return worker


import time
import logging
from PySide6.QtCore import QTimer

logger = logging.getLogger("BillFlow.UIWatchdog")

class UIWatchdog(QObject):
    """
    UI Freeze Watchdog: monitors Qt main event loop responsiveness.
    Ticks every 100ms; if gap between ticks exceeds 500ms, logs warning.
    """
    def __init__(self, threshold_ms: int = 500, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.threshold_sec = threshold_ms / 1000.0
        self.last_tick = time.perf_counter()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.is_monitoring = False

    def start(self, interval_ms: int = 100):
        self.last_tick = time.perf_counter()
        self.timer.start(interval_ms)
        self.is_monitoring = True

    def stop(self):
        self.timer.stop()
        self.is_monitoring = False

    def _on_tick(self):
        now = time.perf_counter()
        delta = now - self.last_tick
        self.last_tick = now
        if delta > self.threshold_sec:
            logger.warning(f"UI Watchdog: Main thread freeze detected! Event loop delayed by {delta*1000:.1f}ms (threshold: {self.threshold_sec*1000:.0f}ms)")

