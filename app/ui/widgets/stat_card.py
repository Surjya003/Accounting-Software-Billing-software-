"""
Enterprise StatCard Widget for BillFlow Suite
Features 24px bold monospaced tabular figures, theme token styling,
and responsive color accent borders that adapt on theme switch.
"""
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from app.ui.theme import theme_manager, ThemeTokens


class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "",
                 value_color: Optional[str] = None, token_name: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setProperty("variant", "stat_card")
        self._token_name = token_name
        self._custom_color = value_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header / Title
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("StatCardTitle")
        self.lbl_title.setProperty("variant", "section")
        self.lbl_title.setFont(theme_manager.font("caption"))
        layout.addWidget(self.lbl_title)

        # Headline Value (tabular monospace font)
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("StatCardValue")
        self.lbl_value.setProperty("variant", "tabular")
        f_val = theme_manager.font("headline")
        f_val.setBold(True)
        self.lbl_value.setFont(f_val)
        layout.addWidget(self.lbl_value)

        # Subtitle / Hint
        self.lbl_sub = None
        if subtitle:
            self.lbl_sub = QLabel(subtitle)
            self.lbl_sub.setProperty("variant", "caption")
            self.lbl_sub.setFont(theme_manager.font("caption"))
            layout.addWidget(self.lbl_sub)

        # Connect to theme changes to refresh styling
        theme_manager.theme_changed.connect(self._on_theme_changed)
        self._apply_theme_colors(theme_manager.tokens)

    def _apply_theme_colors(self, t: ThemeTokens):
        # Resolve value color from token or fallback
        if self._token_name:
            val_col = getattr(t, self._token_name, t.text_primary)
        elif self._custom_color and self._custom_color != "default":
            # If a status color was passed (like green or red), map to theme status tokens
            c_low = self._custom_color.lower()
            if any(k in c_low for k in ["green", "2f6844", "15803d", "4ade80", "22c55e", "success"]):
                val_col = t.success
            elif any(k in c_low for k in ["red", "8b2635", "b91c1c", "f87171", "ef4444", "dc2626", "danger"]):
                val_col = t.danger
            elif any(k in c_low for k in ["blue", "0284c7", "2563eb", "1d4ed8", "60a5fa", "info"]):
                val_col = t.info
            elif any(k in c_low for k in ["amber", "gold", "a6822e", "b45309", "f59e0b", "warning"]):
                val_col = t.accent
            else:
                val_col = t.text_primary
        else:
            val_col = t.text_primary

        # Update styling without setStyleSheet overriding parent QSS using QPalette
        from PySide6.QtGui import QPalette, QColor
        palette = self.lbl_value.palette()
        palette.setColor(QPalette.WindowText, QColor(val_col))
        self.lbl_value.setPalette(palette)

    def _on_theme_changed(self, tokens: ThemeTokens):
        self._apply_theme_colors(tokens)

    def set_value(self, value: str, subtitle: Optional[str] = None):
        self.lbl_value.setText(value)
        if subtitle and self.lbl_sub:
            self.lbl_sub.setText(subtitle)
