"""
Traditional Indian Ledger (Bahi Khata) Design System & QSS Stylesheets
Colors:
  Ink Indigo (Headers, Primary Actions, Active State): #2C3E63
  Ledger Brass (Accent, Column Rules, Tab Underlines): #A6822E
  Ledger Maroon (Payable / Money I Owe - Red Ink):     #8B2635
  Ledger Green (Receivable / Money Owed To Me):        #2F6844
  Page Background (Cool Muted Paper-Grey):             #EAEAE4
  Card/Panel Background (Ledger Paper White):          #FBFBF9
  Rule/Divider Lines (Brass at low opacity):           #D4C49E
  Primary Text:                                        #1B1B18
  Secondary/Muted Text:                                #6B6558
"""

LIGHT_THEME = """
/* Global Application Styles */
QWidget {
    background-color: #EAEAE4;
    color: #1B1B18;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #A6822E;
    selection-color: #FFFFFF;
}

/* Main Window Top Header */
#HeaderBar {
    background-color: #FBFBF9;
    border-bottom: 1px solid #D4C49E;
    padding: 12px 24px;
}

#HeaderTitle {
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #1B1B18;
}

#HeaderSubtitle {
    font-size: 12px;
    color: #6B6558;
}

/* Sidebar */
#Sidebar {
    background-color: #2C3E63;
    border-right: 1px solid #1F2D48;
}

#SidebarTitle {
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    color: #FBFBF9;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 16px 16px 4px 16px;
}

#SidebarSubtitle {
    color: #D4C49E;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    padding: 0px 16px 16px 16px;
}

#NavButton {
    background-color: transparent;
    color: #DDE2EB;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}

#NavButton:hover {
    background-color: #3A507D;
    color: #FBFBF9;
}

#NavButton:checked, #NavButton[active="true"] {
    background-color: #A6822E;
    color: #FFFFFF;
    font-weight: 600;
}

/* Cards and Panels */
#Card {
    background-color: #FBFBF9;
    border: 1px solid #D4C49E;
    border-radius: 4px;
    padding: 16px;
}

#StatCard {
    background-color: #FBFBF9;
    border: 1px solid #D4C49E;
    border-radius: 4px;
    padding: 16px;
}

#StatCardTitle {
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #6B6558;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

#StatCardValue {
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 24px;
    font-weight: bold;
    color: #1B1B18;
}

/* Section and Screen Headers */
.ScreenTitle {
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #1B1B18;
}

.SectionHeader {
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: #1B1B18;
}

.MutedLabel {
    font-size: 12px;
    color: #6B6558;
}

/* Form Controls */
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
    background-color: #FFFFFF;
    color: #1B1B18;
    border: 1px solid #D4C49E;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border: 1.5px solid #2C3E63;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {
    background-color: #EAEAE4;
    color: #6B6558;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #FBFBF9;
    color: #1B1B18;
    border: 1px solid #D4C49E;
    selection-background-color: #A6822E;
    selection-color: #FFFFFF;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background-color: #FBFBF9;
    color: #2C3E63;
    border: 1px solid #2C3E63;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
    height: 32px;
}

QPushButton:hover {
    background-color: #EAEAE4;
}

QPushButton:pressed {
    background-color: #D4C49E;
}

QPushButton#PrimaryBtn {
    background-color: #2C3E63;
    color: #FBFBF9;
    border: none;
    border-radius: 6px;
    height: 36px;
    font-weight: 600;
}

QPushButton#PrimaryBtn:hover {
    background-color: #3A507D;
}

QPushButton#PrimaryBtn:pressed {
    background-color: #1F2D48;
}

QPushButton#SecondaryBtn {
    background-color: #FBFBF9;
    color: #2C3E63;
    border: 1px solid #2C3E63;
    border-radius: 6px;
    height: 32px;
}

QPushButton#SecondaryBtn:hover {
    background-color: #EAEAE4;
}

QPushButton#DestructiveBtn {
    background-color: #FBFBF9;
    color: #8B2635;
    border: 1px solid #8B2635;
    border-radius: 6px;
    height: 32px;
}

QPushButton#DestructiveBtn:hover {
    background-color: #8B2635;
    color: #FBFBF9;
}

QPushButton#SuccessBtn {
    background-color: #FBFBF9;
    color: #2F6844;
    border: 1px solid #2F6844;
    border-radius: 6px;
    height: 32px;
}

QPushButton#SuccessBtn:hover {
    background-color: #2F6844;
    color: #FBFBF9;
}

QPushButton#WarningBtn {
    background-color: #FBFBF9;
    color: #2C3E63;
    border: 1px solid #2C3E63;
    border-radius: 6px;
    height: 32px;
}

QPushButton#WarningBtn:hover {
    background-color: #EAEAE4;
}

QPushButton#DangerBtn {
    background-color: #FBFBF9;
    color: #8B2635;
    border: 1px solid #8B2635;
    border-radius: 6px;
    height: 32px;
}

QPushButton#DangerBtn:hover {
    background-color: #8B2635;
    color: #FBFBF9;
}

/* =========================================================================
   THE SIGNATURE ELEMENT: Traditional Ledger Ruled Columns & Double Header Rule
   ========================================================================= */
QTableWidget, QTableView {
    background-color: #FBFBF9;
    alternate-background-color: #FBFBF9; /* Pure continuous ledger paper, no zebra striping */
    gridline-color: #D4C49E;            /* Brass ruled vertical/horizontal lines (1px) */
    border: 1px solid #D4C49E;
    border-radius: 4px;
    selection-background-color: #A6822E;
    selection-color: #FFFFFF;
    font-size: 13px;
    color: #1B1B18;
}

QHeaderView::section {
    background-color: #F1F1EB;
    color: #1B1B18;
    padding: 8px 12px;
    border: none;
    border-right: 1px solid #D4C49E;     /* Ruled vertical column separator */
    border-bottom: 3px double #A6822E;   /* Signature double horizontal ledger rule */
    font-family: "Bahnschrift", "Segoe UI Semibold", "Segoe UI", sans-serif;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:hover {
    background-color: #EAEAE4;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #D4C49E;
    border-radius: 4px;
    background-color: #FBFBF9;
    top: -1px;
}

QTabBar::tab {
    background-color: #EAEAE4;
    color: #6B6558;
    border: 1px solid #D4C49E;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 16px;
    font-weight: 600;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #FBFBF9;
    color: #2C3E63;
    border-bottom: 2px solid #A6822E; /* Ledger Brass active tab underline */
}

QTabBar::tab:hover:!selected {
    background-color: #D4C49E;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #EAEAE4;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #D4C49E;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #A6822E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #EAEAE4;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #D4C49E;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #A6822E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #2C3E63;
    color: #FBFBF9;
    border-top: 1px solid #A6822E;
    font-size: 12px;
    padding: 4px 12px;
}

QStatusBar QLabel {
    color: #FBFBF9;
}
"""

def get_balance_badge_html(amount: float, bal_type: str) -> str:
    """Returns styled HTML badge for party balance using exact palette colors & tabular font."""
    if amount == 0:
        return "<span style='font-family: Consolas, Cascadia Mono, monospace; color: #6B6558; font-weight: bold;'>₹0.00 Nil</span>"
    if bal_type == "Dr":
        # Receivable - Money owed TO me: #2F6844 (Ledger Green)
        return f"<span style='font-family: Consolas, Cascadia Mono, monospace; color: #2F6844; font-weight: bold;'>₹{amount:,.2f} Dr</span>"
    else:
        # Payable - Money I owe: #8B2635 (Ledger Maroon / Red-ink debit)
        return f"<span style='font-family: Consolas, Cascadia Mono, monospace; color: #8B2635; font-weight: bold;'>₹{amount:,.2f} Cr</span>"

def get_voucher_badge_html(v_type: str) -> str:
    """Returns clean flat colored badge for voucher type with subtle ruled border."""
    colors_map = {
        "Debit": ("#E8ECF2", "#2C3E63", "#C4CEDD"),
        "Credit": ("#E9F2EC", "#2F6844", "#B8D8C2"),
        "Journal": ("#F5EDE8", "#8B2635", "#DEC5BB"),
        "Sale": ("#E8ECF2", "#2C3E63", "#C4CEDD"),
        "Purchase": ("#E9F2EC", "#2F6844", "#B8D8C2"),
        "Payment": ("#E8ECF2", "#2C3E63", "#C4CEDD"),
        "Receipt": ("#E9F2EC", "#2F6844", "#B8D8C2")
    }
    bg, fg, border = colors_map.get(v_type, ("#F1F1EB", "#1B1B18", "#D4C49E"))
    return f"<span style='background-color: {bg}; color: {fg}; border: 1px solid {border}; padding: 2px 8px; border-radius: 3px; font-weight: 600; font-size: 11px;'>{v_type}</span>"

