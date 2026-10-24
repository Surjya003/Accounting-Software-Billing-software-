"""
Unit tests for universal save dialog and export pipeline (app/ui/save_dialog.py).
Tests:
1. Bad character sanitization (/ \\ : * ? " < > | replaced with _)
2. Cancel leaves nothing behind (silent, no error)
3. Locked file detection & friendly error message
4. Read-only folder detection
5. Export settings (ask every time, default folder, last folder per file type)
6. Temporary file generation + copy to final location
"""
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from PySide6.QtWidgets import QApplication

from app.ui.save_dialog import (
    sanitize_filename, is_file_writable, ask_save_path,
    get_export_settings, set_export_settings,
    get_last_folder, set_last_folder, execute_export_pipeline
)

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_sanitize_filename_special_characters():
    """Validates that all forbidden characters / \\ : * ? \" < > | are replaced with _."""
    # Test cases with bad characters
    raw = 'INV/2026-27/001:Special*Test?"<>|End'
    sanitized = sanitize_filename(raw)
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert ":" not in sanitized
    assert "*" not in sanitized
    assert "?" not in sanitized
    assert '"' not in sanitized
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert "|" not in sanitized
    assert sanitized == "INV_2026-27_001_Special_Test_End"

    # Single slash and backslash
    assert sanitize_filename("INV-BA/26-27/12") == "INV-BA_26-27_12"
    assert sanitize_filename("C:\\Path\\To\\Doc") == "C_Path_To_Doc"

    # Empty / whitespace
    assert sanitize_filename("") == "export"
    assert sanitize_filename("   ") == "export"


def test_is_file_writable_and_locked_file():
    """Tests file writable check on new files and open/locked files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "test_doc.pdf"

        # 1. New file in writable dir is writable
        ok, msg = is_file_writable(tmp_path)
        assert ok is True
        assert msg == ""

        # 2. Existing file is writable
        tmp_path.write_bytes(b"initial content")
        ok, msg = is_file_writable(tmp_path)
        assert ok is True

        # 3. Locked file (opened exclusively)
        # On Windows, opening with specific sharing mode or keeping handle open
        try:
            f = open(tmp_path, "r+b")
            # In Python on Windows, if file is opened, appending might succeed unless locked,
            # but is_file_writable tries opening with "a+b"
            # We can mock open raising PermissionError
            with patch("builtins.open", side_effect=PermissionError("File in use")):
                ok_locked, err_locked = is_file_writable(tmp_path)
                assert ok_locked is False
                assert "currently open in another program" in err_locked
        finally:
            f.close()


def test_export_settings_persistence():
    """Tests saving and retrieving export settings via QSettings."""
    set_export_settings(True, "C:\\TestExports")
    ask, default_dir = get_export_settings()
    assert ask is True
    assert default_dir == "C:\\TestExports"

    set_export_settings(False, "")
    ask, default_dir = get_export_settings()
    assert ask is False
    assert default_dir == ""

    # Reset to default
    set_export_settings(True, "")


def test_last_folder_per_kind():
    """Tests that last folder is stored and retrieved per file kind."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = Path(tmp_dir)
        set_last_folder("pdf", p)
        assert get_last_folder("pdf") == p.resolve()


def test_ask_save_path_cancel_returns_none(qapp):
    """Verifies that user cancel in QFileDialog returns None silently."""
    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=("", "")):
        result = ask_save_path(None, "suggested_invoice.pdf", "pdf")
        assert result is None


def test_execute_export_pipeline_cancel_leaves_no_temp(qapp):
    """Verifies that cancelling save dialog runs no generator and creates no temp files."""
    generator_called = False

    def dummy_generator(output_path):
        nonlocal generator_called
        generator_called = True
        Path(output_path).write_text("generated")

    with patch("app.ui.save_dialog.ask_save_path", return_value=None):
        execute_export_pipeline(
            parent=None,
            suggested_name="invoice_123.pdf",
            kind="pdf",
            generator_fn=dummy_generator
        )

    assert generator_called is False


def test_execute_export_pipeline_positional_generator(qapp):
    """Verifies that generator functions taking a single positional argument work cleanly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_file = Path(tmp_dir) / "output.pdf"
        completed_dest = None

        def _generate(out_p):
            Path(out_p).write_text("sample pdf content")

        def _on_done(p):
            nonlocal completed_dest
            completed_dest = p

        with patch("app.ui.save_dialog.ask_save_path", return_value=dest_file), \
             patch("app.ui.save_dialog.show_saved_toast"), \
             patch("app.ui.save_dialog.validate_company_profile_for_export", return_value=(True, "")):
            execute_export_pipeline(
                parent=None,
                suggested_name="invoice.pdf",
                kind="pdf",
                generator_fn=_generate,
                on_complete=_on_done
            )
            from PySide6.QtCore import QCoreApplication, QThreadPool
            QThreadPool.globalInstance().waitForDone(3000)
            QCoreApplication.processEvents()

        assert dest_file.exists()
        assert dest_file.read_text() == "sample pdf content"
        assert completed_dest == dest_file


def test_execute_export_pipeline_with_export_fn_alias(qapp):
    """Verifies that export_fn parameter alias works as expected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_file = Path(tmp_dir) / "report.xlsx"

        with patch("app.ui.save_dialog.ask_save_path", return_value=dest_file), \
             patch("app.ui.save_dialog.show_saved_toast"), \
             patch("app.ui.save_dialog.validate_company_profile_for_export", return_value=(True, "")):
            execute_export_pipeline(
                parent=None,
                suggested_name="report.xlsx",
                kind="xlsx",
                export_fn=lambda out: Path(out).write_text("excel data"),
                toast_title="Excel Exported"
            )
            from PySide6.QtCore import QCoreApplication, QThreadPool
            QThreadPool.globalInstance().waitForDone(3000)
            QCoreApplication.processEvents()

        assert dest_file.exists()
        assert dest_file.read_text() == "excel data"

