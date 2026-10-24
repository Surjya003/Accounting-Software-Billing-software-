"""
Theme Integrity Test Suite
Verifies:
1. Zero hardcoded colors or local setStyleSheet calls outside app/ui/theme/
2. Token completeness across all themes
3. WCAG AA compliance (contrast ratio >= 4.5:1) for all critical text/background pairs
4. Generated QSS has no unresolved placeholders or syntax corruption
5. Custom theme loader never crashes on malformed or missing tokens
"""
import os
import re
import json
import pytest
from pathlib import Path
from dataclasses import fields

from app.ui.theme.tokens import ThemeTokens
from app.ui.theme.themes import (
    THEMES, PROFESSIONAL_LIGHT, PROFESSIONAL_DARK, CLASSIC_NAVY,
    calculate_contrast_ratio as calculate_contrast, load_custom_theme, verify_theme_wcag
)
from app.ui.theme.qss_builder import build_qss
from app.ui.theme.theme_manager import theme_manager


def test_no_hardcoded_styles_in_app_ui():
    """
    Ensures no screen outside app/ui/theme/ contains setStyleSheet calls,
    QColor("#..."), or hardcoded hex color literals.
    """
    ui_dir = Path("app/ui")
    pattern_hex = re.compile(r'[\'"](#[0-9a-fA-F]{3,8})[\'"]')
    pattern_style = re.compile(r'setStyleSheet\(')
    pattern_qcolor = re.compile(r'QColor\([\'\"]#')

    violations = []
    for py_file in ui_dir.rglob("*.py"):
        rel_str = str(py_file).replace("\\", "/")
        if "app/ui/theme" in rel_str:
            continue

        with open(py_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                clean = line.strip()
                if clean.startswith("#") or clean.startswith('"""') or clean.startswith("'''"):
                    continue

                if pattern_style.search(clean):
                    violations.append(f"{py_file}:{line_no} setStyleSheet: {clean}")
                elif pattern_qcolor.search(clean):
                    violations.append(f"{py_file}:{line_no} QColor(#...): {clean}")
                else:
                    matches = pattern_hex.findall(clean)
                    if matches:
                        violations.append(f"{py_file}:{line_no} Hardcoded hex {matches}: {clean}")

    assert len(violations) == 0, (
        f"Found {len(violations)} theme violations outside app/ui/theme/:\n" +
        "\n".join(violations[:20])
    )


def test_theme_token_completeness():
    """Verify all built-in themes define 100% identical token attributes without None or empty."""
    token_fields = [f.name for f in fields(ThemeTokens)]

    for name, theme in THEMES.items():
        assert isinstance(theme, ThemeTokens), f"Theme {name} is not ThemeTokens instance"
        for field_name in token_fields:
            val = getattr(theme, field_name)
            assert val is not None, f"Theme {name} missing value for token: {field_name}"
            if isinstance(val, str):
                assert len(val.strip()) > 0, f"Theme {name} has empty string for token: {field_name}"


def test_wcag_aa_contrast_compliance():
    """
    Mathematically verifies WCAG 2.1 AA contrast ratio (>= 4.5:1) for all critical
    color pairs in all themes.
    """
    test_pairs = [
        ("text_primary", "bg"),
        ("text_primary", "surface"),
        ("text_primary", "table_row_alt"),
        ("sidebar_text", "sidebar_bg"),
        ("text_on_accent", "accent"),
        ("success", "success_soft"),
        ("warning", "warning_soft"),
        ("danger", "danger_soft"),
        ("info", "info_soft"),
    ]

    for name, theme in THEMES.items():
        for fg_tok, bg_tok in test_pairs:
            fg = getattr(theme, fg_tok)
            bg = getattr(theme, bg_tok)
            ratio = calculate_contrast(fg, bg)
            # WCAG AA for normal text requires 4.5:1
            assert ratio >= 4.5, (
                f"Theme '{name}' fails WCAG AA for {fg_tok} ({fg}) on {bg_tok} ({bg}): "
                f"ratio {ratio:.2f} < 4.5:1"
            )


def test_qss_no_unresolved_placeholders():
    """Verify that build_qss() produces clean CSS with zero unresolved placeholders."""
    placeholder_pattern = re.compile(r'\{[a-zA-Z0-9_]+\}')

    for name, theme in THEMES.items():
        qss = build_qss(theme)
        assert len(qss) > 2000, f"Generated QSS for {name} unexpectedly small"
        unresolved = placeholder_pattern.findall(qss)
        assert len(unresolved) == 0, f"Theme {name} QSS contains unresolved placeholders: {unresolved}"


def test_custom_theme_safe_fallback(tmp_path):
    """Verify that loading an invalid custom theme falls back gracefully without crashing."""
    # 1. Broken JSON
    broken_json = tmp_path / "broken.json"
    broken_json.write_text("{not valid json", encoding="utf-8")
    loaded = load_custom_theme(str(broken_json))
    assert loaded is None

    # 2. Incomplete JSON (missing required tokens)
    incomplete_json = tmp_path / "incomplete.json"
    incomplete_json.write_text(json.dumps({"name": "Test Missing", "bg": "#FFFFFF"}), encoding="utf-8")
    loaded2 = load_custom_theme(str(incomplete_json))
    assert loaded2 is None

    # 3. Manager application with broken path falls back to default
    success = theme_manager.apply_theme(str(broken_json))
    assert success is True
    assert theme_manager.tokens == PROFESSIONAL_LIGHT
