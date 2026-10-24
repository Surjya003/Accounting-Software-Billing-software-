"""
Traditional Indian Ledger StatCard Widget
Features 24px bold monospaced tabular figures and refined brass borders.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "", value_color: str = "#1B1B18", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.value_color = value_color
        
        self.setStyleSheet(f"""
            #StatCard {{
                background-color: #FBFBF9;
                border: 1px solid #D4C49E;
                border-left: 3px solid {value_color};
                border-radius: 4px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Header / Title (12px, semi-bold, #6B6558, uppercase)
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("StatCardTitle")
        self.lbl_title.setStyleSheet("font-family: 'Bahnschrift', 'Segoe UI Semibold', 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; color: #6B6558; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_title)
        
        # Headline Value (24px, bold, tabular monospace font)
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("StatCardValue")
        self.lbl_value.setStyleSheet(f"font-family: 'Consolas', 'Cascadia Mono', 'Courier New', monospace; font-size: 24px; font-weight: bold; color: {value_color};")
        layout.addWidget(self.lbl_value)
        
        # Subtitle / Hint (12px, regular, #6B6558)
        if subtitle:
            self.lbl_sub = QLabel(subtitle)
            self.lbl_sub.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #6B6558;")
            layout.addWidget(self.lbl_sub)
            
    def set_value(self, value: str, subtitle: str = None):
        self.lbl_value.setText(value)
        if subtitle and hasattr(self, 'lbl_sub'):
            self.lbl_sub.setText(subtitle)


