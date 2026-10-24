"""
BillFlow Suite - Universal Export Save Location & Notification Engine
=====================================================================
Provides:
1. `ask_save_path`: Unified dialog for picking save destination (PDF, XLSX, JSON, CSV).
2. Sanitizes suggested filenames (removes / \\ : * ? " < > |).
3. Remembers last-used folder per file type and respects Settings ("Ask every time", default folder).
4. Detects open/locked files and read-only folders with user-friendly retry.
5. `save_export_with_dialog`: Background generation to temp file + atomic copy to target path.
6. `ExportSavedToast`: Polished notification toast with "Open File" and "Open Folder" actions.
"""
import os
import re
import sys
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional, Callable, Any

from PySide6.QtWidgets import (
    QWidget, QFileDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QSettings, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon

from app.ui.theme import theme_manager, ThemedMessageBox
from app.ui.async_worker import run_in_background

logger = logging.getLogger("BillFlow.SaveDialog")

# Setting keys in QSettings
SETTINGS_SECTION = "ExportSettings"
KEY_ASK_EVERY_TIME = "ask_every_time"
KEY_DEFAULT_FOLDER = "default_export_folder"
KEY_LAST_FOLDER_PREFIX = "last_folder_"


def sanitize_filename(name: str) -> str:
    """Replaces invalid Windows/POSIX filename characters / \\ : * ? " < > | with _."""
    if not name:
        return "export"
    # Replace characters that are invalid in Windows filenames
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', str(name).strip())
    # Collapse consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('._ ') or "export"


def get_export_settings() -> tuple[bool, str]:
    """Returns (ask_every_time: bool, default_folder: str)."""
    settings = QSettings("BillFlow", SETTINGS_SECTION)
    ask_every_time = settings.value(KEY_ASK_EVERY_TIME, True, type=bool)
    default_folder = str(settings.value(KEY_DEFAULT_FOLDER, "")).strip()
    return ask_every_time, default_folder


def set_export_settings(ask_every_time: bool, default_folder: str = ""):
    """Updates export settings in QSettings."""
    settings = QSettings("BillFlow", SETTINGS_SECTION)
    settings.setValue(KEY_ASK_EVERY_TIME, bool(ask_every_time))
    settings.setValue(KEY_DEFAULT_FOLDER, str(default_folder).strip())


def get_last_folder(kind: str) -> Path:
    """Returns the remembered last folder for this file kind, or fallback."""
    settings = QSettings("BillFlow", SETTINGS_SECTION)
    saved = settings.value(f"{KEY_LAST_FOLDER_PREFIX}{kind.lower()}", "")
    if saved and os.path.isdir(str(saved)):
        return Path(str(saved))

    _, default_folder = get_export_settings()
    if default_folder and os.path.isdir(default_folder):
        return Path(default_folder)

    # Standard OS user documents/desktop fallback
    from app.config import EXPORTS_DIR
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR


def set_last_folder(kind: str, folder_path: Path):
    """Saves the last used folder for this file kind."""
    settings = QSettings("BillFlow", SETTINGS_SECTION)
    settings.setValue(f"{KEY_LAST_FOLDER_PREFIX}{kind.lower()}", str(folder_path.resolve()))


def is_file_writable(target_path: Path) -> tuple[bool, str]:
    """
    Checks if target file can be written to.
    Catches permission errors, read-only folders, and files locked by Acrobat/Excel.
    """
    parent = target_path.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create folder '{parent}': {e}"

    if not os.access(parent, os.W_OK):
        return False, f"Folder '{parent}' is read-only or permission is denied."

    if target_path.exists():
        # Check if file is locked by opening for append
        try:
            with open(target_path, "a+b"):
                pass
        except PermissionError:
            return False, (
                f"The file '{target_path.name}' is currently open in another program "
                f"(such as Adobe Acrobat or Excel).\n\n"
                f"Please close the file and try again, or choose a different save location."
            )
        except Exception as e:
            return False, f"Cannot write to '{target_path.name}': {e}"

    return True, ""


def ask_save_path(parent: Optional[QWidget], suggested_name: str, kind: str) -> Optional[Path]:
    """
    Prompts user for save destination with standard QFileDialog.
    Sanitizes suggested name, remembers last folder, and validates target writability.
    Returns Path if selected and confirmed, or None if cancelled.
    """
    kind = kind.lower().lstrip(".")
    safe_name = sanitize_filename(suggested_name)
    if not safe_name.lower().endswith(f".{kind}"):
        safe_name = f"{safe_name}.{kind}"

    ask_every_time, default_folder = get_export_settings()

    # Filters
    filters_map = {
        "pdf": "PDF Files (*.pdf);;All Files (*.*)",
        "xlsx": "Excel Spreadsheets (*.xlsx);;All Files (*.*)",
        "json": "JSON Data Files (*.json);;All Files (*.*)",
        "csv": "CSV Files (*.csv);;All Files (*.*)",
    }
    filter_str = filters_map.get(kind, f"{kind.upper()} Files (*.{kind});;All Files (*.*)")

    initial_dir = get_last_folder(kind)
    initial_path = str(initial_dir / safe_name)

    # If "Ask every time" is OFF and default folder is set and valid, use it directly
    if not ask_every_time and default_folder and os.path.isdir(default_folder):
        candidate = Path(default_folder) / safe_name
        ok, err = is_file_writable(candidate)
        if ok:
            return candidate
        else:
            ThemedMessageBox.warning(parent, "Save Location Unavailable", err)
            # Fall back to showing dialog

    while True:
        chosen_str, _ = QFileDialog.getSaveFileName(
            parent,
            f"Save {kind.upper()} Export",
            initial_path,
            filter_str
        )
        if not chosen_str:
            # User cancelled -> silent, leaves nothing behind
            return None

        chosen_path = Path(chosen_str)
        # Ensure correct extension
        if not chosen_path.suffix or chosen_path.suffix.lower() != f".{kind}":
            chosen_path = chosen_path.with_suffix(f".{kind}")

        ok, err = is_file_writable(chosen_path)
        if ok:
            set_last_folder(kind, chosen_path.parent)
            return chosen_path
        else:
            ThemedMessageBox.warning(
                parent,
                "Cannot Save to Chosen Location",
                f"{err}\n\nPlease choose a different location or filename."
            )
            initial_path = str(chosen_path)


class ExportSavedToast(QFrame):
    """
    Subtle, non-blocking toast notification banner that slides/fades in after export.
    Provides 'Open File' and 'Open Folder' action buttons.
    """
    def __init__(self, file_path: Path, parent: Optional[QWidget] = None, title: Optional[str] = None):
        super().__init__(parent)
        self.file_path = Path(file_path).resolve()
        self.setObjectName("ExportSavedToast")
        self.setProperty("variant", "card")
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        # Icon + message
        lbl_icon = QLabel()
        lbl_icon.setPixmap(theme_manager.icon("check", color_token="success", size=18).pixmap(18, 18))
        layout.addWidget(lbl_icon)

        prefix = title or "Saved"
        lbl_text = QLabel(f"<b>{prefix}:</b> {self.file_path.name}")
        lbl_text.setFont(theme_manager.font("body"))
        lbl_text.setProperty("variant", "body")
        layout.addWidget(lbl_text)

        layout.addStretch()

        btn_open = QPushButton("Open File")
        btn_open.setProperty("variant", "secondary")
        btn_open.setIcon(theme_manager.icon("external_link", size=14))
        btn_open.setFixedHeight(28)
        btn_open.clicked.connect(self._open_file)
        layout.addWidget(btn_open)

        btn_folder = QPushButton("Open Folder")
        btn_folder.setProperty("variant", "secondary")
        btn_folder.setIcon(theme_manager.icon("folder", size=14))
        btn_folder.setFixedHeight(28)
        btn_folder.clicked.connect(self._open_folder)
        layout.addWidget(btn_folder)

        btn_close = QPushButton()
        btn_close.setProperty("variant", "ghost")
        btn_close.setIcon(theme_manager.icon("close", size=12))
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # Position at bottom right of parent window
        self._position_toast()

        # Auto-dismiss timer (8 seconds)
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.close)
        self.dismiss_timer.start(8000)

    def _position_toast(self):
        parent_widget = self.parentWidget()
        if parent_widget:
            self.adjustSize()
            pw = parent_widget.width()
            ph = parent_widget.height()
            w = max(self.width(), 380)
            h = self.height()
            self.setGeometry(pw - w - 24, ph - h - 24, w, h)
            self.raise_()
            self.show()

    def _open_file(self):
        try:
            if sys.platform == "win32":
                os.startfile(str(self.file_path))
            else:
                import subprocess
                subprocess.call(("open" if sys.platform == "darwin" else "xdg-open", str(self.file_path)))
        except Exception as e:
            logger.warning(f"Could not open file: {e}")
        self.close()

    def _open_folder(self):
        try:
            folder = str(self.file_path.parent)
            if sys.platform == "win32":
                # Select the file in Windows Explorer
                import subprocess
                subprocess.Popen(f'explorer /select,"{self.file_path}"')
            else:
                import subprocess
                subprocess.call(("open" if sys.platform == "darwin" else "xdg-open", folder))
        except Exception as e:
            logger.warning(f"Could not open folder: {e}")
        self.close()


def show_saved_toast(parent: Optional[QWidget], file_path: Path, title: Optional[str] = None):
    """Displays the ExportSavedToast attached to the active window."""
    target_window = parent.window() if parent else (QApplication.activeWindow() or None)
    if target_window:
        toast = ExportSavedToast(file_path, parent=target_window, title=title)
        toast.show()
    else:
        ThemedMessageBox.information(
            parent,
            title or "Saved",
            f"File saved successfully to:\n{file_path}"
        )


def validate_company_profile_for_export(comp: Any) -> tuple[bool, str]:
    """
    Validates company profile completeness before document generation.
    Returns (is_valid: bool, error_message: str).
    """
    if not comp:
        return False, "Company profile record does not exist."
    name = str(getattr(comp, "name", "") or "").strip()
    state = str(getattr(comp, "state", "") or "").strip()
    if not name:
        return False, "Company Name is not configured. Please enter your business name in Settings."
    if not state:
        return False, "Company State is not configured. Please select your operating state in Settings."
    return True, ""


def execute_export_pipeline(
    parent: Optional[QWidget],
    suggested_name: str,
    kind: str,
    generator_fn: Optional[Callable[..., Any]] = None,
    trigger_button: Optional[QPushButton] = None,
    on_complete: Optional[Callable[[Path], None]] = None,
    export_fn: Optional[Callable[..., Any]] = None,
    toast_title: Optional[str] = None,
    **generator_kwargs
):
    """
    Standard orchestration pipeline for all exports:
    1. Prompts `ask_save_path` on the UI thread. If cancelled, stops silently.
    2. Creates a temporary file in temp directory.
    3. Executes `generator_fn` or `export_fn` inside `run_in_background` with busy indicator.
    4. On success: copies temp file to chosen destination, deletes temp, shows Saved toast.
    5. On error: cleans temp file, shows friendly error dialog.
    """
    fn = generator_fn or export_fn
    if fn is None:
        raise ValueError("Neither generator_fn nor export_fn was provided to execute_export_pipeline.")

    # 0. Check company profile completeness before PDF generation
    if kind.lower() == "pdf":
        from app.database.connection import get_session
        from app.database.models import CompanyProfile
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            valid, err_msg = validate_company_profile_for_export(comp)
            if not valid:
                ThemedMessageBox.warning(
                    parent,
                    "Company Profile Incomplete",
                    f"Complete your company profile in Settings before generating PDF documents.\n\n{err_msg}"
                )
                return

    chosen_path = ask_save_path(parent, suggested_name, kind)
    if not chosen_path:
        # Cancel = silent, leaves nothing behind
        return

    # Create temporary file
    temp_fd, temp_path_str = tempfile.mkstemp(suffix=f".{kind.lower().lstrip('.')}")
    os.close(temp_fd)
    temp_path = Path(temp_path_str)

    def _worker():
        import inspect
        kwargs = dict(generator_kwargs)
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            param_names = set(sig.parameters.keys())

            # 1. Single positional argument function (e.g. lambda out: ... or _generate(out_p))
            if len(params) == 1 and params[0].kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD
            ):
                return fn(temp_path)

            # 2. Named kwargs
            if "output_path" in param_names:
                kwargs["output_path"] = temp_path
            elif "filename" in param_names:
                kwargs["filename"] = str(temp_path)
            elif "filepath" in param_names:
                kwargs["filepath"] = str(temp_path)
            elif any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
                kwargs["output_path"] = temp_path
            elif len(params) > 0:
                return fn(temp_path, **kwargs)

            return fn(**kwargs)
        except Exception:
            try:
                return fn(temp_path)
            except TypeError:
                try:
                    return fn(str(temp_path))
                except TypeError:
                    return fn(**kwargs)

    def _on_success(_result):
        try:
            # Copy temp file to chosen path
            shutil.copy2(temp_path, chosen_path)
            # Remove temp file
            temp_path.unlink(missing_ok=True)
            # Show toast with Open File & Open Folder
            show_saved_toast(parent, chosen_path, title=toast_title)
            if on_complete:
                on_complete(chosen_path)
        except Exception as e:
            ThemedMessageBox.critical(parent, "Save Error", f"Failed to save file to '{chosen_path}': {e}")
        finally:
            temp_path.unlink(missing_ok=True)

    def _on_error(exc):
        temp_path.unlink(missing_ok=True)
        ThemedMessageBox.critical(parent, "Export Failed", f"Could not generate export:\n{exc}")

    run_in_background(
        _worker,
        on_result=_on_success,
        on_error=_on_error,
        trigger_button=trigger_button
    )
