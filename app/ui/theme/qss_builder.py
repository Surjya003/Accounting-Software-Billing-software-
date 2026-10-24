"""
Dynamic QSS Stylesheet Builder for BillFlow Suite
Constructs a complete, enterprise-grade Qt6 stylesheet entirely from ThemeTokens.
Zero hardcoded color or size literals inside the stylesheet.
"""
from app.ui.theme.tokens import ThemeTokens


def build_qss(t: ThemeTokens) -> str:
    """Generate the complete application QSS stylesheet using the provided ThemeTokens."""
    qss = f"""
/* =========================================================================
   BillFlow Suite Enterprise Theme Stylesheet
   Theme: {t.display_name} ({t.name})
   ========================================================================= */

/* --- 1. Global Application Baseline --- */
QWidget {{
    background-color: {t.bg};
    color: {t.text_primary};
    font-family: {t.font_family};
    font-size: {t.font_size_body}px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    outline: none;
}}

QWidget:disabled {{
    color: {t.text_disabled};
}}

QMainWindow {{
    background-color: {t.bg};
}}

QDialog {{
    background-color: {t.surface};
    color: {t.text_primary};
}}

/* --- 2. Typography & Text Labels --- */
QLabel {{
    background: transparent;
    color: {t.text_primary};
    font-size: {t.font_size_body}px;
}}

QLabel[variant="title"], .ScreenTitle, #HeaderTitle {{
    font-size: {t.font_size_title}px;
    font-weight: {t.font_weight_bold};
    color: {t.text_primary};
}}

QLabel[variant="headline"] {{
    font-size: {t.font_size_headline}px;
    font-weight: {t.font_weight_bold};
    color: {t.text_primary};
}}

QLabel[variant="subtitle"], #HeaderSubtitle, .MutedLabel {{
    font-size: {t.font_size_caption}px;
    color: {t.text_secondary};
}}

QLabel[variant="caption"] {{
    font-size: {t.font_size_caption}px;
    color: {t.text_muted};
}}

QLabel[variant="section"], .SectionHeader, #SidebarSection {{
    font-size: {t.font_size_caption}px;
    font-weight: {t.font_weight_bold};
    color: {t.sidebar_section};
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}

QLabel[variant="danger"], QLabel[variant="error"] {{
    color: {t.danger};
    font-size: {t.font_size_caption}px;
    font-weight: {t.font_weight_medium};
}}

/* Tabular number font for money labels */
QLabel[variant="tabular"], .TabularFigure {{
    font-family: {t.font_family_mono};
    font-size: {t.font_size_body}px;
}}

/* --- 3. Cards, Panels & Containers --- */
QFrame#Card, QFrame[variant="card"] {{
    background-color: {t.surface};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
}}

QFrame#StatCard, QFrame[variant="stat_card"] {{
    background-color: {t.surface};
    border: 1px solid {t.border};
    border-radius: {t.radius_lg}px;
    padding: {t.spacing_md}px;
}}

QFrame[variant="sunken"] {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}

QFrame#HeaderBar {{
    background-color: {t.surface};
    border-bottom: 1px solid {t.border};
    padding: {t.spacing_md}px {t.spacing_xl}px;
}}

/* --- 4. Sidebar Navigation --- */
QFrame#Sidebar {{
    background-color: {t.sidebar_bg};
    border-right: 1px solid {t.sidebar_border};
}}

#SidebarTitle {{
    color: {t.text_on_accent};
    font-size: {t.font_size_title}px;
    font-weight: {t.font_weight_bold};
    padding: {t.spacing_lg}px {t.spacing_lg}px {t.spacing_xs}px {t.spacing_lg}px;
}}

#SidebarSubtitle {{
    color: {t.sidebar_text};
    font-size: {t.font_size_caption}px;
    font-weight: {t.font_weight_semibold};
    letter-spacing: 1.2px;
    text-transform: uppercase;
    padding: 0px {t.spacing_lg}px {t.spacing_lg}px {t.spacing_lg}px;
}}

QPushButton#NavButton, QPushButton[variant="nav"] {{
    background-color: transparent;
    color: {t.sidebar_text};
    border: none;
    border-radius: {t.radius_md}px;
    padding: {t.spacing_sm}px {t.spacing_md}px;
    text-align: left;
    font-size: {t.font_size_body}px;
    font-weight: {t.font_weight_medium};
    min-height: 24px;
}}

QPushButton#NavButton:hover, QPushButton[variant="nav"]:hover {{
    background-color: {t.sidebar_hover};
    color: #FFFFFF;
}}

QPushButton#NavButton:checked, QPushButton#NavButton[active="true"],
QPushButton[variant="nav"]:checked, QPushButton[variant="nav"][active="true"] {{
    background-color: {t.sidebar_active};
    color: {t.sidebar_active_text};
    font-weight: {t.font_weight_semibold};
    border-left: 3px solid {t.accent};
}}

/* --- 5. Buttons (Variants & States) --- */
QPushButton {{
    background-color: {t.surface};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: 5px {t.spacing_md}px;
    font-size: {t.font_size_body}px;
    font-weight: {t.font_weight_medium};
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {t.bg_alt};
    border-color: {t.border_strong};
}}

QPushButton:pressed {{
    background-color: {t.border};
}}

QPushButton:disabled {{
    background-color: {t.surface_sunken};
    color: {t.text_disabled};
    border-color: {t.border};
}}

/* Primary Action Button */
QPushButton#PrimaryBtn, QPushButton[variant="primary"] {{
    background-color: {t.accent};
    color: {t.text_on_accent};
    border: 1px solid {t.accent};
    border-radius: {t.radius_md}px;
    font-weight: {t.font_weight_semibold};
}}

QPushButton#PrimaryBtn:hover, QPushButton[variant="primary"]:hover {{
    background-color: {t.accent_hover};
    border-color: {t.accent_hover};
}}

QPushButton#PrimaryBtn:pressed, QPushButton[variant="primary"]:pressed {{
    background-color: {t.accent_pressed};
    border-color: {t.accent_pressed};
}}

QPushButton#PrimaryBtn:disabled, QPushButton[variant="primary"]:disabled {{
    background-color: {t.border};
    color: {t.text_disabled};
    border-color: {t.border};
}}

/* Secondary Action Button */
QPushButton#SecondaryBtn, QPushButton[variant="secondary"] {{
    background-color: {t.surface};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
}}

QPushButton#SecondaryBtn:hover, QPushButton[variant="secondary"]:hover {{
    background-color: {t.bg_alt};
    border-color: {t.border_strong};
}}

/* Destructive / Danger Button */
QPushButton#DestructiveBtn, QPushButton#DangerBtn, QPushButton[variant="danger"] {{
    background-color: {t.danger_soft};
    color: {t.danger};
    border: 1px solid {t.danger};
    border-radius: {t.radius_md}px;
    font-weight: {t.font_weight_semibold};
}}

QPushButton#DestructiveBtn:hover, QPushButton#DangerBtn:hover, QPushButton[variant="danger"]:hover {{
    background-color: {t.danger};
    color: {t.text_on_accent};
}}

/* Success Button */
QPushButton#SuccessBtn, QPushButton[variant="success"] {{
    background-color: {t.success_soft};
    color: {t.success};
    border: 1px solid {t.success};
    border-radius: {t.radius_md}px;
    font-weight: {t.font_weight_semibold};
}}

QPushButton#SuccessBtn:hover, QPushButton[variant="success"]:hover {{
    background-color: {t.success};
    color: {t.text_on_accent};
}}

/* Ghost / Flat Button */
QPushButton[variant="ghost"] {{
    background-color: transparent;
    color: {t.text_secondary};
    border: none;
    border-radius: {t.radius_md}px;
    height: {t.button_height}px;
}}

QPushButton[variant="ghost"]:hover {{
    background-color: {t.bg_alt};
    color: {t.text_primary};
}}

/* Icon-Only Button */
QPushButton[variant="icon_only"] {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: {t.radius_md}px;
    padding: {t.spacing_xs}px;
    width: {t.control_height}px;
    height: {t.control_height}px;
}}

QPushButton[variant="icon_only"]:hover {{
    background-color: {t.bg_alt};
    border-color: {t.border};
}}

/* --- 6. Form Inputs & Controls --- */
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
    background-color: {t.input_bg};
    color: {t.input_text};
    border: 1px solid {t.input_border};
    border-radius: {t.radius_md}px;
    padding: 4px {t.spacing_sm}px;
    font-size: {t.font_size_body}px;
    min-height: 22px;
}}

QTextEdit, QPlainTextEdit {{
    background-color: {t.input_bg};
    color: {t.input_text};
    border: 1px solid {t.input_border};
    border-radius: {t.radius_md}px;
    padding: 6px {t.spacing_sm}px;
    font-size: {t.font_size_body}px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    border: 1.5px solid {t.input_border_focus};
    background-color: {t.surface};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
    background-color: {t.surface_sunken};
    color: {t.text_disabled};
    border-color: {t.border};
}}

QLineEdit[readOnly="true"], QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {{
    background-color: {t.surface_sunken};
    color: {t.text_secondary};
}}

QLineEdit[invalid="true"], QComboBox[invalid="true"] {{
    border: 1.5px solid {t.danger};
}}

/* SpinBox Buttons */
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {t.border};
    border-bottom: 1px solid {t.border};
    border-top-right-radius: {t.radius_md}px;
    background-color: {t.surface_elevated};
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: {t.bg_alt};
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid {t.border};
    border-bottom-right-radius: {t.radius_md}px;
    background-color: {t.surface_elevated};
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {t.bg_alt};
}}

/* QComboBox */
QComboBox {{
    background-color: {t.input_bg};
    color: {t.input_text};
    border: 1px solid {t.input_border};
    border-radius: {t.radius_md}px;
    padding: 4px {t.spacing_sm}px;
    font-size: {t.font_size_body}px;
    min-height: 22px;
}}

QComboBox:focus {{
    border: 1.5px solid {t.input_border_focus};
}}

QComboBox:disabled {{
    background-color: {t.surface_sunken};
    color: {t.text_disabled};
    border-color: {t.border};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid {t.border};
    border-top-right-radius: {t.radius_md}px;
    border-bottom-right-radius: {t.radius_md}px;
    background-color: {t.surface_elevated};
}}

QComboBox::drop-down:hover {{
    background-color: {t.bg_alt};
}}

QComboBox QAbstractItemView {{
    background-color: {t.surface_elevated};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
    padding: {t.spacing_xs}px;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 4px 8px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {t.accent};
    color: {t.text_on_accent};
}}

/* Checkboxes and Radio Buttons */
QCheckBox, QRadioButton {{
    color: {t.text_primary};
    font-size: {t.font_size_body}px;
    spacing: {t.spacing_sm}px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {t.border_strong};
    background-color: {t.input_bg};
    border-radius: {t.radius_sm}px;
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}

QRadioButton::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}

QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: {t.surface_sunken};
    border-color: {t.border};
}}

/* --- 7. Data Tables & Lists --- */
QTableWidget, QTableView {{
    background-color: {t.surface};
    alternate-background-color: {t.table_row_alt};
    gridline-color: {t.table_grid};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    selection-background-color: {t.table_selected_bg};
    selection-color: {t.table_selected_text};
    color: {t.text_primary};
    font-size: {t.font_size_body}px;
    outline: none;
}}

QTableWidget::item, QTableView::item {{
    padding: {t.spacing_xs}px {t.spacing_sm}px;
    min-height: {t.row_height}px;
}}

QTableWidget::item:hover, QTableView::item:hover {{
    background-color: {t.table_row_hover};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {t.table_selected_bg};
    color: {t.table_selected_text};
}}

QHeaderView::section {{
    background-color: {t.table_header_bg};
    color: {t.table_header_text};
    padding: 8px 12px;
    border: none;
    border-right: 1px solid {t.border};
    border-bottom: 2px solid {t.border_strong};
    font-size: {t.font_size_caption}px;
    font-weight: {t.font_weight_bold};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QHeaderView::section:hover {{
    background-color: {t.bg_alt};
}}

QTableCornerButton::section {{
    background-color: {t.table_header_bg};
    border: 1px solid {t.border};
}}

/* TreeView and ListView */
QTreeView, QListView {{
    background-color: {t.surface};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    selection-background-color: {t.accent};
    selection-color: {t.text_on_accent};
}}

/* --- 8. Tabs & Groups --- */
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    background-color: {t.surface};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {t.bg_alt};
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-bottom: none;
    border-top-left-radius: {t.radius_md}px;
    border-top-right-radius: {t.radius_md}px;
    padding: 8px 18px;
    font-weight: {t.font_weight_medium};
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {t.surface};
    color: {t.accent};
    border-bottom: 2px solid {t.accent};
    font-weight: {t.font_weight_bold};
}}

QTabBar::tab:hover:!selected {{
    background-color: {t.border};
    color: {t.text_primary};
}}

QGroupBox {{
    font-weight: {t.font_weight_bold};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    margin-top: 12px;
    padding-top: 16px;
    color: {t.text_primary};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 10px;
    color: {t.text_primary};
}}

/* --- 9. Menus & Popups --- */
QMenu {{
    background-color: {t.surface_elevated};
    color: {t.text_primary};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: {t.spacing_xs}px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: {t.radius_sm}px;
}}

QMenu::item:selected {{
    background-color: {t.accent};
    color: {t.text_on_accent};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t.border};
    margin: 4px 8px;
}}

QMenuBar {{
    background-color: {t.surface};
    color: {t.text_primary};
    border-bottom: 1px solid {t.border};
}}

QMenuBar::item:selected {{
    background-color: {t.bg_alt};
}}

/* Tooltips */
QToolTip {{
    background-color: {t.tooltip_bg};
    color: {t.tooltip_text};
    border: 1px solid {t.tooltip_border};
    border-radius: {t.radius_sm}px;
    padding: 6px 10px;
    font-size: {t.font_size_caption}px;
}}

/* --- 10. Scrollbars --- */
QScrollBar:vertical {{
    background: {t.scrollbar_bg};
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {t.scrollbar_thumb};
    min-height: 24px;
    border-radius: 5px;
    margin: 1px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t.scrollbar_thumb_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {t.scrollbar_bg};
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {t.scrollbar_thumb};
    min-width: 24px;
    border-radius: 5px;
    margin: 1px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {t.scrollbar_thumb_hover};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* --- 11. Status Bar & Miscellaneous --- */
QStatusBar {{
    background-color: {t.surface};
    color: {t.text_secondary};
    border-top: 1px solid {t.border};
    font-size: {t.font_size_caption}px;
    padding: 4px 12px;
}}

QProgressBar {{
    background-color: {t.surface_sunken};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    text-align: center;
    color: {t.text_primary};
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: {t.radius_sm}px;
}}

QSplitter::handle {{
    background-color: {t.border};
}}

QSplitter::handle:hover {{
    background-color: {t.accent};
}}
"""
    return qss
