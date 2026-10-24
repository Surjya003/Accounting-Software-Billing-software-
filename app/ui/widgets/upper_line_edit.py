"""
Uppercase QLineEdit widget that enforces live uppercase transformation (BUG-03).
"""
from PySide6.QtWidgets import QLineEdit


class UpperLineEdit(QLineEdit):
    """QLineEdit that automatically forces typed input to uppercase live."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textEdited.connect(self._force_upper)

    def _force_upper(self, text: str):
        pos = self.cursorPosition()
        upper_text = text.upper()
        if text != upper_text:
            self.setText(upper_text)
            self.setCursorPosition(pos)

    def text(self) -> str:
        """Returns stripped uppercase text."""
        return super().text().strip().upper()
