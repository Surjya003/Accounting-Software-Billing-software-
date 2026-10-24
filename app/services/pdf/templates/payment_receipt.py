"""
BillFlow Suite - Payment Receipt / Voucher Template (Dual-Copy A4 Architecture)
================================================================================
Design Features:
- Exactly TWO self-contained copies rendered on ONE single A4 portrait sheet
- Top Half: 'CUSTOMER COPY'
- Perforated dashed divider line with scissors glyph: '- - - - ✂ Cut Here ✂ - - - -'
- Bottom Half: 'OFFICE COPY'
- Highlights: 'Received with thanks from', Prominent Amount Badge, 'Subject to realisation of cheque'
- Realized Bank / UPI / Cheque details with UTR reference and Outstanding Balance tracking

Statutory Citation: Valid receipt voucher under GST and Indian Commercial Practice.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, KeepTogether
)

# Core plumbing imports ONLY - templates must NEVER import from other templates
from app.services.pdf.core.page import (
    PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN, FRAME_WIDTH, FRAME_HEIGHT, NumberedCanvas, SimpleDocTemplate
)
from app.services.pdf.core.formatting import (
    format_currency, format_date_ddmmyyyy, amount_to_words_inr
)
from app.services.pdf.core.images import load_safe_image
from app.services.pdf.core.fonts import register_unicode_fonts, sanitize_rupee_text
from app.services.pdf.core.text import make_p, escape_xml
from app.services.pdf.core.stamps import draw_watermark_stamp

logger = logging.getLogger(__name__)

# --- NAMED GEOMETRY & STYLING CONSTANTS (mm & pt) ---
MARGIN_MM = 10.0
FRAME_WIDTH_PT = FRAME_WIDTH

COLOR_TEAL = colors.HexColor("#0D9488")        # Teal 600
COLOR_BG_LIGHT = colors.HexColor("#F0FDFA")    # Teal 50
COLOR_BORDER = colors.HexColor("#5EEAD4")      # Teal 300
COLOR_GRID = colors.HexColor("#CBD5E1")        # Slate 300
COLOR_DARK = colors.HexColor("#0F172A")        # Slate 900
COLOR_MUTED = colors.HexColor("#475569")       # Slate 600

# Font sizes
FS_TITLE = 11.5
FS_COPY_LABEL = 7.5
FS_BODY = 7.0
FS_SMALL = 6.2
FS_TINY = 5.6
FS_HERO_AMT = 12.0


def _build_receipt_card(data: Dict[str, Any], copy_name: str = "CUSTOMER COPY") -> Table:
    """Builds a complete, framed receipt box representing one-half of the A4 page."""
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or data.get("party", {}) or {}
    totals = data.get("totals", {}) or {}

    v_num = escape_xml(data.get("voucher_number") or data.get("receipt_number") or data.get("invoice_number", "REC-001"))
    v_date = format_date_ddmmyyyy(data.get("voucher_date") or data.get("date"))
    v_type = str(data.get("voucher_type") or "Receipt").title()
    title_text = f"{v_type.upper()} VOUCHER / PAYMENT RECEIPT"

    amount_val = float(data.get("total_amount") or data.get("amount") or totals.get("grand_total", 0.0))
    amt_words = amount_to_words_inr(amount_val)

    # 1. Header Row: Title & Copy Label
    hdr_row = [
        Paragraph(f"<b>{title_text}</b>", make_p(font_size=FS_TITLE, bold=True, color=COLOR_TEAL)),
        Paragraph(f"<b>({copy_name})</b>", make_p(font_size=FS_COPY_LABEL, bold=True, alignment=2, color=COLOR_MUTED))
    ]
    t_hdr = Table([hdr_row], colWidths=[FRAME_WIDTH_PT - 130.0, 130.0])
    t_hdr.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, 0), (-1, -1), 0.6, COLOR_TEAL),
    ]))

    # 2. Company & Receipt Meta Details
    half_w = (FRAME_WIDTH_PT - 10.0) / 2.0

    comp_info = [
        Paragraph(f"<b>{escape_xml(comp.get('name', 'Company Name'))}</b>", make_p(font_size=FS_BODY + 0.5, bold=True)),
        Paragraph(escape_xml(comp.get('address', '')), make_p(font_size=FS_SMALL)),
        Paragraph(f"GSTIN: <b>{escape_xml(comp.get('gstin', 'N/A'))}</b> | Ph: {escape_xml(comp.get('phone', ''))}", make_p(font_size=FS_SMALL)),
    ]

    rcpt_meta = [
        Paragraph(f"Receipt No.: <b>{v_num}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph(f"Date: <b>{v_date}</b>", make_p(font_size=FS_BODY, alignment=2)),
        Paragraph(f"Financial Year: {escape_xml(comp.get('financial_year', '2024-25'))}", make_p(font_size=FS_SMALL, alignment=2)),
    ]

    t_meta = Table([[comp_info, rcpt_meta]], colWidths=[half_w + 20.0, half_w - 20.0])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # 3. Party Received From & Highlighted Amount Box
    action_verb = "Received with thanks from" if "receipt" in v_type.lower() else "Paid with thanks to"
    party_p = Paragraph(
        f"{action_verb}:<br/>"
        f"<b>{escape_xml(cust.get('name', 'Party Name'))}</b><br/>"
        f"{escape_xml(cust.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(cust.get('gstin', 'N/A'))}</b> | State: {escape_xml(cust.get('state', ''))}",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    amt_box_content = [
        Paragraph("<b>AMOUNT RECEIVED:</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_TEAL, alignment=2)),
        Paragraph(f"<b>Rs. {format_currency(amount_val, num_fmt)}</b>", make_p(font_size=FS_HERO_AMT, bold=True, color=COLOR_TEAL, alignment=2)),
        Paragraph(f"<i>{amt_words}</i>", make_p(font_size=FS_TINY + 0.5, alignment=2, leading=FS_TINY + 2)),
    ]

    t_party_amt = Table([[party_p, amt_box_content]], colWidths=[half_w + 10.0, half_w - 10.0])
    t_party_amt.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (1, 0), COLOR_BG_LIGHT),
        ('BOX', (1, 0), (1, 0), 0.8, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    # 4. Transaction & Payment Details Strip (Mode, Cheque/UTR, Bank, Invoices)
    pay_mode = escape_xml(data.get("payment_mode") or "Bank Transfer / NEFT")
    ref_no = escape_xml(data.get("reference_no") or data.get("utr_no") or data.get("cheque_no") or "-")
    b_name = escape_xml(data.get("bank_name") or comp.get("bank_name") or "-")
    ag_inv = escape_xml(data.get("against_invoices") or data.get("invoice_ref") or "On Account / Current Ledger")
    bal_out = float(data.get("balance_outstanding") or data.get("closing_balance") or 0.0)

    t_details_data = [
        [
            Paragraph(f"Payment Mode:<br/><b>{pay_mode}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Ref / Cheque / UTR No.:<br/><b>{ref_no}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Bank &amp; Branch:<br/><b>{b_name}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Against Invoice(s):<br/><b>{ag_inv}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Balance Outstanding after this receipt:<br/><b>Rs. {format_currency(bal_out, num_fmt)}</b>", make_p(font_size=FS_SMALL, color=colors.HexColor("#B45309"))),
        ]
    ]
    col_w = (FRAME_WIDTH_PT - 10.0) / 5.0
    t_details = Table(t_details_data, colWidths=[col_w] * 5)
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))

    # 5. Bottom Signatory & Realisation Note
    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=75.0, max_h_pt=18.0)
    note_p = Paragraph(
        "<i>Subject to realisation of cheque / electronic bank clearance.<br/>"
        "This is a Computer Generated Document.</i>",
        make_p(font_size=FS_TINY, color=COLOR_MUTED, leading=FS_TINY + 2)
    )

    sign_content = [
        Paragraph(f"for <b>{escape_xml(comp.get('name', 'Company'))}</b>", make_p(font_size=FS_SMALL, alignment=2)),
    ]
    if sig_img:
        sign_content.append(sig_img)
    else:
        sign_content.append(Spacer(1, 14.0))
    sign_content.append(Paragraph("<b>Receiver's Signature / Authorised Signatory</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)))

    t_bot = Table([[note_p, sign_content]], colWidths=[half_w + 20.0, half_w - 20.0])
    t_bot.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Full card container
    card_content = [
        [t_hdr],
        [t_meta],
        [t_party_amt],
        [Spacer(1, 2)],
        [t_details],
        [Spacer(1, 2)],
        [t_bot]
    ]
    t_card = Table(card_content, colWidths=[FRAME_WIDTH_PT - 8.0])
    t_card.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_TEAL),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t_card


def render_payment_receipt_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders two framed copies (Customer & Office) on one single A4 page with dashed scissor cut line."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    register_unicode_fonts()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN
    )

    top_copy = _build_receipt_card(data, copy_name="CUSTOMER COPY")
    bottom_copy = _build_receipt_card(data, copy_name="OFFICE COPY")

    cut_line_p = Paragraph(
        "<font color='#64748B'>- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - "
        "&#9986; <b>Cut Here</b> &#9986; "
        "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -</font>",
        make_p(font_size=7.0, alignment=1)
    )

    story = [
        top_copy,
        Spacer(1, 8),
        cut_line_p,
        Spacer(1, 8),
        bottom_copy
    ]

    status = str(data.get("status", "")).lower()

    class ReceiptNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "cancelled":
                draw_watermark_stamp(self, "CANCELLED", color_hex="#DC2626")

    doc.build(story, canvasmaker=ReceiptNumberedCanvas)
    return output_path
