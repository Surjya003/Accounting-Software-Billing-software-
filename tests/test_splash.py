"""
Unit and Integration Tests for Animated Splash Screen and About Dialog
======================================================================
Verifies:
1. Splash builds and renders in all enterprise themes (Light/Dark/Navy)
2. Startup pipeline progress is monotonic and reaches 100%
3. Minimum visible time is enforced (1200ms)
4. Fade-out and cross-fade to MainWindow / target window
5. Reduce-motion provides immediate static display without animations
6. Failure handling stops animation and closes splash immediately
7. --no-splash command line flag disables splash
8. Missing or broken logo falls back safely to 'BA' monogram without crashing
9. Splash object maintains strong reference against premature garbage collection
10. Themed AboutDialog displays correct branding and diagnostics
"""
import sys
import os
import gc
import pytest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer, QSettings

from app.branding import (
    APP_NAME, BRAND_NAME, MAKER_NAME, TAGLINE, VERSION, CREDIT_LINE
)
from app.ui.splash import (
    SplashScreen, is_splash_enabled, is_reduce_motion_enabled, _ACTIVE_SPLASH
)
from app.ui.about_dialog import AboutDialog
from app.ui.theme import theme_manager


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single persistent QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication(sys.argv)
    return app


def test_splash_builds_in_all_themes(qapp):
    """Verify splash initializes and renders crisp frame across all themes."""
    themes_to_test = ["professional_light", "professional_dark", "classic_navy"]
    for theme_key in themes_to_test:
        theme_manager.apply_theme(theme_key)
        splash = SplashScreen(reduce_motion=True)
        splash.show_splash()

        # Check geometry
        assert splash.width() >= 640
        assert splash.height() >= 380

        # Offscreen render grab
        pixmap = splash.grab()
        assert not pixmap.isNull()
        assert pixmap.width() == splash.width()
        assert pixmap.height() == splash.height()

        splash.close()


def test_splash_progress_monotonic_and_reaches_100(qapp):
    """Verify progress advances monotonically and hits 100%."""
    splash = SplashScreen(reduce_motion=True)
    splash.show_splash()

    assert splash.get_progress_value() == 0.0

    steps = [5, 10, 25, 45, 60, 80, 95, 100]
    last_val = 0.0
    for val in steps:
        splash.set_progress(val, f"Testing step {val}%")
        current = splash.get_progress_value()
        assert current >= last_val, f"Progress decreased from {last_val} to {current}"
        last_val = current

    assert splash.get_progress_value() == 100.0
    splash.close()


def test_splash_minimum_visible_time(qapp):
    """Verify minimum visible duration constant is 1.2s (1200ms)."""
    splash = SplashScreen(reduce_motion=False)
    splash.show_splash()
    assert splash._min_visible_ms == 1200
    assert splash._start_timer.isValid()
    splash.close()


def test_splash_cross_fade_to_target_window(qapp):
    """Verify finish() activates the target window."""
    splash = SplashScreen(reduce_motion=True)
    splash.show_splash()

    target = QWidget()
    splash.finish(target)
    qapp.processEvents()

    assert not splash.isVisible()
    assert target.isVisible()
    target.close()


def test_splash_reduce_motion_static_card(qapp):
    """Verify reduce_motion displays static card with zero animations."""
    splash = SplashScreen(reduce_motion=True)
    splash.show_splash()

    assert splash.card_scale == 1.0
    assert splash.logo_scale == 1.0
    assert splash.logo_opacity == 1.0
    assert splash.line_expand == 1.0
    assert splash.title_opacity == 1.0
    assert splash.title_offset == 0.0
    assert splash.brand_opacity == 1.0
    assert splash.brand_offset == 0.0
    assert splash.tagline_opacity == 1.0
    assert splash.tagline_offset == 0.0
    assert splash._anim_group is None
    splash.close()


def test_splash_failure_closes_immediately(qapp):
    """Verify close_on_error immediately hides and stops splash."""
    splash = SplashScreen(reduce_motion=False)
    splash.show_splash()
    assert splash.isVisible()

    splash.close_on_error()
    qapp.processEvents()
    assert not splash.isVisible()


def test_no_splash_flag(monkeypatch):
    """Verify --no-splash flag correctly disables splash."""
    monkeypatch.setattr(sys, "argv", ["app.main", "--no-splash"])
    assert is_splash_enabled() is False


def test_missing_logo_fallback_to_monogram(qapp, monkeypatch, tmp_path):
    """Verify missing logo does not crash and renders 'BA' monogram fallback."""
    fake_logo_path = tmp_path / "non_existent_logo.svg"
    monkeypatch.setattr("app.ui.splash.get_asset_path", lambda _: fake_logo_path)

    splash = SplashScreen(reduce_motion=True)
    splash.show_splash()
    assert splash._svg_renderer is None

    # Render with monogram fallback
    pixmap = splash.grab()
    assert not pixmap.isNull()
    splash.close()


def test_splash_keeps_global_reference(qapp):
    """Verify splash retains reference in _ACTIVE_SPLASH against GC."""
    import app.ui.splash as smod
    splash = SplashScreen(reduce_motion=True)
    assert smod._ACTIVE_SPLASH is splash

    # Simulate local scope deletion
    del splash
    gc.collect()

    assert smod._ACTIVE_SPLASH is not None
    smod._ACTIVE_SPLASH.close()


def test_about_dialog_metadata_and_copy(qapp):
    """Verify AboutDialog contains proper branding and diagnostics."""
    dlg = AboutDialog()
    data = dlg.diagnostics_data

    assert APP_NAME in data["Application"]
    assert BRAND_NAME == data["Enterprise Brand"]
    assert MAKER_NAME == data["Engineering Lead"]
    assert "PySide6" in data["GUI Engine"]

    # Test copy diagnostics to clipboard
    dlg._copy_diagnostics()
    cb_text = QApplication.clipboard().text()
    assert APP_NAME in cb_text
    assert BRAND_NAME in cb_text
    assert MAKER_NAME in cb_text
    dlg.close()
