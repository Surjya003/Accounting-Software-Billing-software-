"""
Singleton ThemeManager for BillFlow Suite
Manages runtime theme switching, QPalette synchronization, persistence,
OS system appearance detection, and external JSON theme loading.
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Signal, QSettings, Qt
from PySide6.QtGui import QPalette, QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.theme.tokens import ThemeTokens
from app.ui.theme.themes import THEMES, PROFESSIONAL_LIGHT, PROFESSIONAL_DARK, CLASSIC_NAVY, load_custom_theme
from app.ui.theme.qss_builder import build_qss
from app.ui.theme.icons import get_icon, get_pixmap, clear_icon_cache

logger = logging.getLogger("billflow.theme")


class ThemeManager(QObject):
    """
    Central singleton managing application themes and UI styling.
    Emits theme_changed(ThemeTokens) when theme switches.
    """
    _instance: Optional["ThemeManager"] = None
    theme_changed = Signal(object)  # Emits ThemeTokens

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._settings = QSettings("BillFlow", "ThemeSystem")
        self._current_theme: ThemeTokens = PROFESSIONAL_LIGHT
        self._theme_mode: str = "professional_light"  # or 'professional_dark', 'classic_navy', 'system', 'custom'
        self._custom_theme_path: Optional[str] = None
        self._dev_warnings_enabled: bool = True

        # Load persisted preference
        saved_mode = self._settings.value("theme_mode", "professional_light")
        saved_custom = self._settings.value("custom_theme_path", "")
        self._theme_mode = saved_mode
        self._custom_theme_path = saved_custom if saved_custom else None

    @classmethod
    def instance(cls) -> "ThemeManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def current_theme(self) -> ThemeTokens:
        """Get active ThemeTokens."""
        return self._current_theme

    @property
    def tokens(self) -> ThemeTokens:
        """Alias for current_theme."""
        return self._current_theme

    @property
    def theme_mode(self) -> str:
        """Current mode setting (e.g. 'professional_light', 'professional_dark', 'classic_navy', 'system')."""
        return self._theme_mode

    # --- Theme Application & Switching ---
    def apply_theme(self, theme_key_or_name: str, save_preference: bool = True) -> bool:
        """
        Switch to the specified theme at runtime without restart.
        Synchronizes QSS, QPalette, fonts, and emits theme_changed.
        """
        app = QApplication.instance()

        # Handle 'system' mode
        if theme_key_or_name == "system":
            self._theme_mode = "system"
            is_sys_dark = self.detect_system_dark_mode()
            target_theme = PROFESSIONAL_DARK if is_sys_dark else PROFESSIONAL_LIGHT
        elif theme_key_or_name.endswith(".json") or (Path(theme_key_or_name).exists() and not theme_key_or_name in THEMES):
            self._theme_mode = "custom"
            self._custom_theme_path = theme_key_or_name
            loaded = load_custom_theme(theme_key_or_name)
            target_theme = loaded if loaded else PROFESSIONAL_LIGHT
        else:
            self._theme_mode = theme_key_or_name
            target_theme = THEMES.get(theme_key_or_name, PROFESSIONAL_LIGHT)

        self._current_theme = target_theme

        if app is not None:
            # 1. Apply QSS
            qss = build_qss(target_theme)
            app.setStyleSheet(qss)

            # 2. Synchronize QPalette for native dialogs & controls
            palette = self._build_qpalette(target_theme)
            app.setPalette(palette)

            # 3. Apply global typography
            font = QFont("Segoe UI", target_theme.font_size_body)
            font.setStyleHint(QFont.SansSerif)
            app.setFont(font)

            # 4. Refresh all open dialogs and top-level windows live
            for widget in app.topLevelWidgets():
                try:
                    st = widget.style()
                    if st:
                        st.unpolish(widget)
                        st.polish(widget)
                    widget.update()
                except Exception:
                    pass

        if save_preference:
            self._settings.setValue("theme_mode", self._theme_mode)
            if self._custom_theme_path:
                self._settings.setValue("custom_theme_path", self._custom_theme_path)

        # 5. Notify all listening widgets
        self.theme_changed.emit(self._current_theme)
        return True

    def toggle_theme(self) -> str:
        """Quick toggle between Light and Dark mode."""
        if self._current_theme.is_dark:
            new_theme = "professional_light"
        else:
            new_theme = "professional_dark"
        self.apply_theme(new_theme)
        return new_theme

    def restore_theme(self) -> None:
        """Restore saved theme preference upon application startup."""
        mode = self._settings.value("theme_mode", "professional_light")
        if mode == "custom" and self._custom_theme_path:
            self.apply_theme(self._custom_theme_path, save_preference=False)
        else:
            self.apply_theme(mode, save_preference=False)

    def _build_qpalette(self, t: ThemeTokens) -> QPalette:
        """Build a matching QPalette from ThemeTokens."""
        p = QPalette()
        p.setColor(QPalette.Window, QColor(t.bg))
        p.setColor(QPalette.WindowText, QColor(t.text_primary))
        p.setColor(QPalette.Base, QColor(t.surface))
        p.setColor(QPalette.AlternateBase, QColor(t.table_row_alt))
        p.setColor(QPalette.ToolTipBase, QColor(t.tooltip_bg))
        p.setColor(QPalette.ToolTipText, QColor(t.tooltip_text))
        p.setColor(QPalette.Text, QColor(t.text_primary))
        p.setColor(QPalette.Button, QColor(t.surface))
        p.setColor(QPalette.ButtonText, QColor(t.text_primary))
        p.setColor(QPalette.BrightText, QColor(t.text_on_accent))
        p.setColor(QPalette.Highlight, QColor(t.accent))
        p.setColor(QPalette.HighlightedText, QColor(t.text_on_accent))
        p.setColor(QPalette.Link, QColor(t.info))
        p.setColor(QPalette.PlaceholderText, QColor(t.input_placeholder))

        # Disabled state
        p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(t.text_disabled))
        p.setColor(QPalette.Disabled, QPalette.Text, QColor(t.text_disabled))
        p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t.text_disabled))
        return p

    def detect_system_dark_mode(self) -> bool:
        """Detect whether the host OS is configured in Dark Mode."""
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return value == 0
            except Exception:
                pass
        return False

    # --- Helper Accessor Methods ---
    def color(self, token_name: str) -> str:
        """Return hex color string for a token name."""
        return getattr(self._current_theme, token_name, "#000000")

    def qcolor(self, token_name: str) -> QColor:
        """Return QColor for a token name."""
        return QColor(self.color(token_name))

    def font(self, variant: str = "body", bold: bool = False) -> QFont:
        """Get standard QFont for a specific typography token."""
        t = self._current_theme
        f = QFont("Segoe UI")
        f.setStyleHint(QFont.SansSerif)

        if variant == "tabular" or variant == "mono":
            f = QFont("Consolas")
            f.setStyleHint(QFont.Monospace)
            f.setPointSize(t.font_size_body)
            if bold:
                f.setWeight(QFont.Bold)
            return f

        size_map = {
            "caption": t.font_size_caption,
            "body": t.font_size_body,
            "label": t.font_size_label,
            "subtitle": t.font_size_subtitle,
            "title": t.font_size_title,
            "headline": t.font_size_headline,
            "display": t.font_size_display,
        }
        f.setPointSize(size_map.get(variant, t.font_size_body))

        if bold or variant in ("title", "headline", "display"):
            f.setWeight(QFont.Bold)
        elif variant == "subtitle":
            f.setWeight(QFont.DemiBold)
        return f

    def get_font(self, variant: str = "body", bold: bool = False) -> QFont:
        """Alias for font()."""
        return self.font(variant=variant, bold=bold)

    def icon(self, name: str, color_token: Optional[str] = None, token_color: Optional[str] = None, size: int = 20) -> QIcon:
        """Get recolored QIcon for a named icon."""
        tok = color_token or token_color
        c = self.color(tok) if tok else self.color("text_secondary")
        return get_icon(name, color=c, size=size)

    def get_icon(self, name: str, color_token: Optional[str] = None, token_color: Optional[str] = None, size: int = 20) -> QIcon:
        """Alias for icon()."""
        return self.icon(name, color_token=color_token, token_color=token_color, size=size)

    def pixmap(self, name: str, color_token: Optional[str] = None, token_color: Optional[str] = None, size: int = 20) -> QPixmap:
        """Get recolored QPixmap for a named icon."""
        tok = color_token or token_color
        c = self.color(tok) if tok else self.color("text_secondary")
        return get_pixmap(name, color=c, size=size)

    def get_pixmap(self, name: str, color_token: Optional[str] = None, token_color: Optional[str] = None, size: int = 20) -> QPixmap:
        """Alias for pixmap()."""
        return self.pixmap(name, color_token=color_token, token_color=token_color, size=size)

    def spacing(self, scale: str = "md") -> int:
        """Get pixel spacing for a token (xs, sm, md, lg, xl, xxl)."""
        return getattr(self._current_theme, f"spacing_{scale}", 12)

    def get_export_accent(self) -> str:
        """Get brand accent color for PDF / Excel exports (always returns hex)."""
        return self._current_theme.accent

    # --- Dev-Time Integrity Hook ---
    def warn_if_inline_styling(self, widget: QWidget, method_name: str = "setStyleSheet") -> None:
        """Development-time warning hook if a widget tries to set an inline stylesheet."""
        if self._dev_warnings_enabled:
            logger.warning(
                f"[THEME VIOLATION] Widget '{widget.objectName() or widget.__class__.__name__}' "
                f"attempted to call {method_name}() with local inline styling. "
                f"Use theme tokens or variant properties instead."
            )


# Global singleton instance
theme_manager = ThemeManager.instance()
