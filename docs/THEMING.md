# BillFlow Suite — Design & Theming Guide

This document describes the centralized visual design and theme system for BillFlow Suite (Indian B2B billing and accounting offline desktop application).

---

## 1. Core Architecture

The theming engine lives in [`app/ui/theme/`](file:///app/ui/theme/) and is built on five pillars:

1. **`tokens.py` (`ThemeTokens`)**: Single source of truth. Every theme is an instance of `ThemeTokens` containing semantic color tokens, typography scales, spacing tokens, and component dimensions.
2. **`themes.py` (`THEMES`)**: Shipped themes meeting WCAG 2.1 AA accessibility contrast standards:
   - `Professional Light` (default): Clean white/light-gray surfaces, executive slate-navy sidebar, restrained gold accent for brand continuity.
   - `Professional Dark`: Deep high-contrast dark surfaces (`#0B0F17`, `#111827`), reduced glare, high-contrast text.
   - `Classic Navy`: Traditional navy-forward palette (`#0F2942`) tailored for trading operations.
3. **`qss_builder.py` (`build_qss`)**: Universal QSS stylesheet generator. Maps token values to all standard Qt6 widgets, pseudo-states (`:hover`, `:pressed`, `:focus`, `:disabled`, `:selected`), and semantic variants (`variant="primary"`, `variant="danger"`, etc.).
4. **`icons.py`**: Pure vector SVG icons (Lucide / Tabler outline style, 1.75px stroke). Dynamically recolored at runtime using active theme tokens (`currentColor`).
5. **`theme_manager.py` (`theme_manager`)**: Application-wide singleton that applies QSS, synchronizes `QPalette` (for native OS dialogs), updates global application fonts, detects OS Light/Dark mode, persists user preferences across restarts, and enables live theme switching with zero application restart.

---

## 2. The Golden Rule: Never Hardcode Colors in Screens

> **STRICT INVARIANT:**
> Under no circumstances should any view, dialog, or custom widget in `app/ui/` (outside `app/ui/theme/`) define hardcoded hex colors (`#hex`), call `setStyleSheet("color: ...")`, or use `QColor("#...")`.
> 
> Continuous integration runs `tests/test_theme_integrity.py`, which will automatically **FAIL** if any hardcoded color or inline stylesheet is committed outside `app/ui/theme/`.

### How to Style Widgets Correctly:
- **Buttons**: Set dynamic property `variant`:
  - `btn.setProperty("variant", "primary")` — Brand accent filled button with high-contrast text.
  - `btn.setProperty("variant", "secondary")` — Subtle bordered button for secondary actions.
  - `btn.setProperty("variant", "danger")` — Destructive action button.
  - `btn.setProperty("variant", "ghost")` — Flat button without background or border.
  - `btn.setProperty("variant", "icon_only")` — Square compact icon button.
- **Labels**: Set dynamic property `variant`:
  - `lbl.setProperty("variant", "title")` — Bold title typography.
  - `lbl.setProperty("variant", "subtitle")` — Secondary subtitle typography.
  - `lbl.setProperty("variant", "caption")` — Small muted caption text.
  - `lbl.setProperty("variant", "headline")` — Large metric or KPI number.
  - `lbl.setProperty("variant", "tabular")` — Monospace numbers for financial amounts.
- **Containers**: Wrap content sections in `CardFrame()` for clean surface background, border, and rounded corners.
- **Headers**: Use `PageHeaderWidget(title, subtitle, action_text, action_icon, action_callback)` for uniform top-bar layouts.
- **Status Pills**: Use `StatusBadgeLabel(status_text)` (automatically renders soft background and high-contrast text for Paid, Partial, Unpaid, Overdue, Draft, etc.).
- **Message Boxes**: Use `ThemedMessageBox.information(...)`, `.warning(...)`, `.critical(...)`, or `.question(...)` instead of jarring default `QMessageBox`.
- **Dynamic / Custom Painting**: In custom `paintEvent` (e.g. charts), read active tokens directly via `theme_manager.tokens` or `theme_manager.qcolor("token_name")`. Connect to `theme_manager.theme_changed` to trigger `self.update()`.

---

## 3. How to Add a New Theme in 3 Steps

You can add a new theme in one file without modifying application logic:

### Step 1: Define the Theme in `app/ui/theme/themes.py`
Create a new `ThemeTokens` instance with your custom palette:
```python
MY_CUSTOM_THEME = ThemeTokens(
    name="emerald_executive",
    display_name="Emerald Executive",
    is_dark=False,
    bg="#F0FDF4",
    surface="#FFFFFF",
    sidebar_bg="#064E3B",
    sidebar_text="#A7F3D0",
    sidebar_active="#059669",
    accent="#059669",
    accent_hover="#047857",
    accent_pressed="#065F46",
    # ... fill remaining tokens matching ThemeTokens definition
)
```

### Step 2: Register it in the `THEMES` Dictionary
In `app/ui/theme/themes.py`, add your theme to the registry:
```python
THEMES["emerald_executive"] = MY_CUSTOM_THEME
```

### Step 3: Verify Integrity & Contrast
Run the automated test suite:
```bash
python -m pytest tests/test_theme_integrity.py tests/test_theme_switching.py
```
If contrast ratio satisfies WCAG 2.1 AA (>= 4.5:1), your theme is immediately available in the application theme switcher!

---

## 4. Loading External JSON Themes

Users and administrators can also supply custom theme JSON files in runtime via the Settings page or CLI:
1. Place `my_theme.json` containing the required token keys.
2. In **Settings -> Appearance & Themes**, choose **"Custom Theme (.json file)"** and browse for the file.
3. If valid, the theme applies instantly with no restart. If invalid or tokens are missing, the system safely falls back to the default theme without crashing.
