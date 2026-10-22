"""
Searchable Party Selection ComboBox with Live Balance Preview
"""
from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt, Signal
from typing import Optional, List, Dict, Any

from app.services.party_service import get_all_parties

class PartyComboBox(QComboBox):
    party_changed = Signal(int)  # emits party_id

    def __init__(self, party_type: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.party_type = party_type
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.completer().setFilterMode(Qt.MatchContains)
        self.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.lineEdit().setPlaceholderText("-- Select Party --")
        
        self.currentIndexChanged.connect(self._on_index_changed)
        self.load_parties()
        
    def load_parties(self, select_party_id: Optional[int] = None):
        self.blockSignals(True)
        self.clear()
        
        parties = get_all_parties(party_type=self.party_type, active_only=True)
        self.addItem("", userData=None)
        
        selected_index = 0
        for idx, p in enumerate(parties, start=1):
            bal_str = f"₹{p['current_balance']:,.2f} {p['current_balance_type']}"
            display_text = f"{p['name']} ({p.get('city','') or 'Local'}) - [Bal: {bal_str}]"
            self.addItem(display_text, userData=p["id"])
            if select_party_id and p["id"] == select_party_id:
                selected_index = idx
                
        self.setCurrentIndex(selected_index)
        self.blockSignals(False)

    def _on_index_changed(self, index: int):
        party_id = self.currentData()
        if party_id:
            self.party_changed.emit(party_id)

    def get_selected_party_id(self) -> Optional[int]:
        return self.currentData()

    def set_selected_party_id(self, party_id: int):
        for i in range(self.count()):
            if self.itemData(i) == party_id:
                self.setCurrentIndex(i)
                return
