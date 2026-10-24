"""
Core PDF Plumbing for BillFlow Suite
"""
from app.services.pdf.core.page import (
    PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN, PAGE_MARGIN_MM,
    FRAME_X, FRAME_Y, FRAME_WIDTH, FRAME_HEIGHT, FRAME_LINE_WIDTH, COLOR_FRAME,
    NumberedCanvas
)
from app.services.pdf.core.flex_table import calculate_filler_height, build_stretched_table
from app.services.pdf.core.formatting import format_currency, format_date_ddmmyyyy, amount_to_words_inr
from app.services.pdf.core.images import load_safe_image
from app.services.pdf.core.fonts import register_unicode_fonts, get_font_names, sanitize_rupee_text
from app.services.pdf.core.text import escape_xml, make_p
from app.services.pdf.core.stamps import draw_watermark_stamp
