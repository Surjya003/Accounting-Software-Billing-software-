"""
BillFlow Suite - Core PDF Layout Engine: Document Watermark Stamps
==================================================================
Renders diagonal semi-transparent watermark stamps (DRAFT, CANCELLED,
CONVERTED, EXPIRED, RETURNABLE, FULLY RECEIVED) across the document.
"""
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from app.services.pdf.core.page import PAGE_WIDTH, PAGE_HEIGHT


def draw_watermark_stamp(
    canv: canvas.Canvas,
    stamp_text: str,
    color_hex: str = "#DC2626",
    alpha: float = 0.15,
    rotation: float = 45.0
):
    """Draws a prominent semi-transparent rotated watermark stamp across the page."""
    if not stamp_text:
        return

    canv.saveState()
    try:
        # Set transparency if supported by canvas
        if hasattr(canv, "setFillAlpha"):
            canv.setFillAlpha(alpha)
            canv.setStrokeAlpha(alpha)

        canv.setFont("Helvetica-Bold", 54.0)
        canv.setFillColor(colors.HexColor(color_hex))
        canv.setStrokeColor(colors.HexColor(color_hex))

        # Center translation
        cx = PAGE_WIDTH / 2.0
        cy = PAGE_HEIGHT / 2.0
        canv.translate(cx, cy)
        canv.rotate(rotation)

        text_w = canv.stringWidth(stamp_text, "Helvetica-Bold", 54.0)
        canv.drawCentredString(0, -18, stamp_text)

        # Draw framing stamp box around the word
        pad_x = 24.0
        pad_y = 14.0
        canv.setLineWidth(3.0)
        canv.rect(-text_w / 2.0 - pad_x, -18 - pad_y, text_w + (2 * pad_x), 54 + (2 * pad_y), fill=0, stroke=1)
    finally:
        canv.restoreState()
