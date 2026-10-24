"""
Quick Date Selector Widget for Reports and Registers.
Provides one-click shortcuts for: Today, This Month, This Quarter, This FY.
Complies with Indian Financial Year cycles (Apr 1 - Mar 31).
"""
import calendar
from datetime import date
from typing import Callable, Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton


def get_current_fy_bounds(today: Optional[date] = None):
    today = today or date.today()
    if today.month >= 4:
        start_year = today.year
        end_year = today.year + 1
    else:
        start_year = today.year - 1
        end_year = today.year
    return date(start_year, 4, 1), date(end_year, 3, 31)


def get_current_quarter_bounds(today: Optional[date] = None):
    today = today or date.today()
    m = today.month
    y = today.year
    if 4 <= m <= 6:
        return date(y, 4, 1), date(y, 6, 30)
    elif 7 <= m <= 9:
        return date(y, 7, 1), date(y, 9, 30)
    elif 10 <= m <= 12:
        return date(y, 10, 1), date(y, 12, 31)
    else:  # Jan-Mar
        return date(y, 1, 1), date(y, 3, 31)


def get_current_month_bounds(today: Optional[date] = None):
    today = today or date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


class QuickDateSelector(QWidget):
    """
    Compact horizontal button bar for quick date selection on reports.
    """
    def __init__(self, dt_from, dt_to, on_change: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self.dt_from = dt_from
        self.dt_to = dt_to
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.btn_today = QPushButton("Today")
        self.btn_month = QPushButton("This Month")
        self.btn_quarter = QPushButton("This Quarter")
        self.btn_fy = QPushButton("This FY")

        for btn in (self.btn_today, self.btn_month, self.btn_quarter, self.btn_fy):
            btn.setProperty("variant", "secondary")
            btn.setFixedHeight(28)
            btn.setContentsMargins(6, 2, 6, 2)
            layout.addWidget(btn)

        self.btn_today.clicked.connect(self._select_today)
        self.btn_month.clicked.connect(self._select_month)
        self.btn_quarter.clicked.connect(self._select_quarter)
        self.btn_fy.clicked.connect(self._select_fy)

    def _apply_dates(self, d_start: date, d_end: date):
        self.dt_from.setDate(QDate(d_start.year, d_start.month, d_start.day))
        self.dt_to.setDate(QDate(d_end.year, d_end.month, d_end.day))
        if self.on_change:
            self.on_change()

    def _select_today(self):
        t = date.today()
        self._apply_dates(t, t)

    def _select_month(self):
        s, e = get_current_month_bounds()
        self._apply_dates(s, e)

    def _select_quarter(self):
        s, e = get_current_quarter_bounds()
        self._apply_dates(s, e)

    def _select_fy(self):
        s, e = get_current_fy_bounds()
        self._apply_dates(s, e)
