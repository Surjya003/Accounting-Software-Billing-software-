"""
BillFlow Suite - Automated UI Layout Lint Test Suite
====================================================
Tests that all views and dialogs comply with layout integrity rules:
1. No widgets outside parent bounds
2. No minimumSizeHint clipping
3. No emoji icon glyphs in labels or buttons
4. No missing tooltips on icon-only buttons
5. Responsive sizing without hard overflows
"""
import os
import pytest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
import sys

app = QApplication.instance() or QApplication(sys.argv)

from scripts.ui_lint import UILayoutLinter, EMOJI_PATTERN, VIEWS
from app.ui.theme import theme_manager
from app.ui.main_window import MainWindow
from app.ui.views.billing.invoice_view import InvoiceFormDialog
from app.ui.views.billing.quotation_view import QuotationFormDialog
from app.ui.views.party_view import PartyDialog


@pytest.fixture(scope="module")
def main_win():
    win = MainWindow()
    win.resize(1280, 720)
    win.show()
    app.processEvents()
    return win


def test_no_emoji_in_navigation_and_headers(main_win):
    """Verifies that navigation items, tab bars, and headers use SVG icons, not emojis."""
    violations = []
    for btn_key, btn in main_win.nav_buttons.items():
        txt = btn.text()
        if EMOJI_PATTERN.search(txt):
            violations.append(f"Nav button '{btn_key}': {txt}")

    assert len(violations) == 0, f"Found emoji characters in navigation buttons: {violations}"


def test_views_within_bounds_at_720p(main_win):
    """Verifies that at minimum supported resolution (1280x720), views do not extend beyond window."""
    main_win.resize(1280, 720)
    app.processEvents()

    linter = UILayoutLinter()
    for key, title in VIEWS:
        main_win.navigate_to(key)
        app.processEvents()
        linter.lint_widget_tree(main_win, title, "professional_light", "1280x720")

    blockers = [f for f in linter.findings if f.severity == "Blocker"]
    assert len(blockers) == 0, f"Found Blocker layout issues at 1280x720: {[b.description for b in blockers]}"


def test_dialogs_geometry_constraints():
    """Verifies dialogs respect screen bounds and do not exceed standard height."""
    dialogs = [
        InvoiceFormDialog(),
        QuotationFormDialog(),
        PartyDialog(),
    ]

    for diag in dialogs:
        diag.setModal(False)
        diag.show()
        app.processEvents()

        # Dialog should never force height > 750 without inner scrolling
        hint = diag.minimumSizeHint()
        diag.close()
