"""
Design Tokens for BillFlow Suite
The single source of truth for all colors, typography, spacing, radius, and component sizes.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    display_name: str
    is_dark: bool

    # Surfaces & Backgrounds
    bg: str                   # Main application / canvas background
    bg_alt: str               # Alternate page background
    surface: str              # Card, panel, dialog background
    surface_elevated: str     # Popups, dropdown views, elevated cards
    surface_sunken: str       # Inset areas, stat card background, code panels

    # Sidebar Navigation
    sidebar_bg: str           # Sidebar background
    sidebar_text: str         # Default sidebar item text color
    sidebar_hover: str        # Sidebar item hover background
    sidebar_active: str       # Sidebar item active background
    sidebar_active_text: str  # Sidebar item active text color
    sidebar_border: str       # Sidebar border / divider
    sidebar_section: str      # Uppercase section header label color

    # Borders & Rings
    border: str               # Standard UI border (inputs, cards, dividers)
    border_strong: str        # Emphasized border (tables, headers)
    border_focus: str         # Focused input border
    focus_ring: str           # Focus ring glow / rgba outline

    # Text & Content
    text_primary: str         # Primary headings and body text
    text_secondary: str       # Subtitles, muted labels, secondary text
    text_disabled: str        # Disabled controls text
    text_on_accent: str       # Text displayed over accent / primary buttons
    text_muted: str           # Subtle hints, footer metadata

    # Brand & Primary Accents
    accent: str               # Primary brand action color
    accent_hover: str         # Primary button hover
    accent_pressed: str       # Primary button active/pressed
    accent_subtle: str        # Soft tinted accent background

    # Semantic Status Colors & Soft Background Tints
    success: str              # Paid, Received, Profit, Active
    success_soft: str         # Soft green badge background
    warning: str              # Pending, Partially Paid, Caution
    warning_soft: str         # Soft amber badge background
    danger: str               # Overdue, Unpaid, Loss, Destructive action
    danger_soft: str          # Soft red badge background
    info: str                 # Draft, Info, Converted, Reference
    info_soft: str            # Soft blue badge background

    # Tables & Lists
    table_header_bg: str      # Header row background
    table_header_text: str    # Header row text color
    table_row_alt: str        # Alternating row background
    table_row_hover: str      # Row hover background
    table_selected_bg: str    # Selected row background
    table_selected_text: str  # Selected row text
    table_grid: str           # Table gridline color

    # Form Controls & Inputs
    input_bg: str             # LineEdit, SpinBox, DateEdit background
    input_border: str         # Default input border
    input_border_focus: str   # Focused input border
    input_text: str           # Input text color
    input_placeholder: str    # Input placeholder text color

    # Tooltips & Scrollbars
    tooltip_bg: str           # Tooltip background
    tooltip_text: str         # Tooltip text
    tooltip_border: str       # Tooltip border
    scrollbar_bg: str         # Scrollbar track
    scrollbar_thumb: str      # Scrollbar thumb handle
    scrollbar_thumb_hover: str# Scrollbar thumb hover

    # Charts
    chart_series: List[str]   # Palette of colors for charts
    chart_axis: str           # Axis lines and tick labels
    chart_grid: str           # Gridlines color

    # Typography
    font_family: str = '"Segoe UI", "Inter", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif'
    font_family_mono: str = '"Consolas", "Cascadia Code", "Courier New", monospace'
    font_size_caption: int = 11
    font_size_body: int = 13
    font_size_label: int = 13
    font_size_subtitle: int = 15
    font_size_title: int = 18
    font_size_headline: int = 22
    font_size_display: int = 28
    font_weight_regular: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700

    # Spacing Scale (4, 8, 12, 16, 24, 32)
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 16
    spacing_xl: int = 24
    spacing_xxl: int = 32

    # Radius Scale (4, 6, 8, 12)
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8
    radius_xl: int = 12

    # Sizing
    control_height: int = 36
    button_height: int = 36
    row_height: int = 36
    sidebar_width: int = 240
    sidebar_collapsed_width: int = 68
    icon_size_sm: int = 16
    icon_size_md: int = 20
    icon_size_lg: int = 24

    def to_dict(self) -> Dict[str, Any]:
        """Convert tokens to a dictionary."""
        d = {}
        for k, v in self.__dict__.items():
            d[k] = list(v) if isinstance(v, (list, tuple)) else v
        return d
