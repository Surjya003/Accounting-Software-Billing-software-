"""
BillFlow Suite - Core PDF Layout Engine: Font Discovery & Registration
======================================================================
Discovers and registers Unicode TrueType fonts (Nirmala UI, DejaVu Sans, Noto Sans)
supporting Indian Devanagari and Rupee (₹) symbol with fallback to standard Helvetica.
"""
import os
import sys
import logging
from typing import Tuple
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger("pdf_fonts")

_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_INITIALIZED = False
_SUPPORTS_RUPEE = False


def register_unicode_fonts() -> Tuple[str, str]:
    """
    Registers a TrueType font for Unicode / Devanagari / Rupee support.
    Returns (regular_font_name, bold_font_name).
    """
    global _FONT_REGULAR, _FONT_BOLD, _FONT_INITIALIZED, _SUPPORTS_RUPEE
    if _FONT_INITIALIZED:
        return _FONT_REGULAR, _FONT_BOLD

    candidate_search_dirs = [
        r"C:\Windows\Fonts",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts",
        "/System/Library/Fonts",
        "/Library/Fonts",
    ]

    # Priority font pairs
    font_pairs = [
        # 1. Nirmala UI (Windows 10/11 native Indian font with crisp Rupee & Hindi glyphs)
        ("NirmalaUI", "Nirmala.ttf", "NirmalaB.ttf", True),
        ("NirmalaUI", "nirmala.ttf", "nirmalab.ttf", True),
        # 2. DejaVu Sans
        ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", True),
        # 3. Arial Unicode / Segoe UI
        ("SegoeUI", "segoeui.ttf", "segoeuib.ttf", True),
        ("Arial", "arial.ttf", "arialbd.ttf", False),
    ]

    registered = False
    for family_name, reg_file, bold_file, has_rupee in font_pairs:
        for sdir in candidate_search_dirs:
            if not os.path.isdir(sdir):
                continue
            r_path = os.path.join(sdir, reg_file)
            b_path = os.path.join(sdir, bold_file)

            if os.path.isfile(r_path):
                try:
                    pdfmetrics.registerFont(TTFont(f"{family_name}", r_path))
                    if os.path.isfile(b_path):
                        pdfmetrics.registerFont(TTFont(f"{family_name}-Bold", b_path))
                        _FONT_BOLD = f"{family_name}-Bold"
                    else:
                        _FONT_BOLD = f"{family_name}"
                    _FONT_REGULAR = f"{family_name}"
                    _SUPPORTS_RUPEE = has_rupee
                    registered = True
                    logger.info(f"Registered PDF font: {_FONT_REGULAR} from {r_path}")
                    break
                except Exception as e:
                    logger.debug(f"Could not register font {r_path}: {e}")
        if registered:
            break

    _FONT_INITIALIZED = True
    return _FONT_REGULAR, _FONT_BOLD


def get_font_names() -> Tuple[str, str]:
    """Returns the active regular and bold font names."""
    if not _FONT_INITIALIZED:
        return register_unicode_fonts()
    return _FONT_REGULAR, _FONT_BOLD


def sanitize_rupee_text(text: str) -> str:
    """
    Replaces unicode ₹ with 'Rs.' if the registered font does not natively support ₹,
    preventing missing glyph square boxes.
    """
    if not text:
        return ""
    if not _SUPPORTS_RUPEE and "₹" in text:
        return text.replace("₹", "Rs. ")
    return text
