"""
BillFlow Suite - Core PDF Layout Engine: Text Sanitization & Paragraph Helpers
==============================================================================
Provides XML escaping for ReportLab Paragraphs and typography styling helpers.
"""
import html
import uuid
from typing import Optional, Union
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors

from app.services.pdf.core.fonts import get_font_names, sanitize_rupee_text


def escape_xml(text: Optional[str]) -> str:
    """Escapes special characters (&, <, >, quotes) so ReportLab Paragraphs never crash."""
    if text is None:
        return ""
    s = sanitize_rupee_text(str(text))
    # Normalize existing entities before escaping
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return html.escape(s, quote=True)


def make_p(
    text: Optional[str] = None,
    font_size: float = 8.0,
    leading: Optional[float] = None,
    bold: bool = False,
    align: Optional[int] = None,
    alignment: Optional[int] = None,
    color: colors.Color = colors.HexColor("#0F172A"),
    name: Optional[str] = None
) -> Union[Paragraph, ParagraphStyle]:
    """
    Versatile ReportLab helper:
    - If `text` is provided as a string, returns a safely escaped Paragraph(safe_text, style).
    - If `text` is omitted or None, returns a ParagraphStyle configured with the specified parameters.
    Accepts both `align` and `alignment` (0=Left, 1=Center, 2=Right).
    """
    font_reg, font_bld = get_font_names()
    f_name = font_bld if bold else font_reg
    if leading is None:
        leading = font_size * 1.25

    eff_align = TA_LEFT
    if alignment is not None:
        eff_align = alignment
    elif align is not None:
        eff_align = align

    style_name = name or f"PStyle_{uuid.uuid4().hex[:8]}"
    style = ParagraphStyle(
        name=style_name,
        fontName=f_name,
        fontSize=font_size,
        leading=leading,
        alignment=eff_align,
        textColor=color
    )

    if text is not None:
        safe_text = escape_xml(text)
        return Paragraph(safe_text, style)
    return style
