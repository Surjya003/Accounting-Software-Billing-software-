"""
BillFlow Suite - Quotation Template (Commercial Business-Letter Architecture)
=============================================================================
Design Features:
- Elegant Letterhead with clean executive typography
- Formal business correspondence elements: 'Kind Attn.:', 'Subject:', salutation & opening offer text
- Soft grid styling (thin subtle dividers rather than heavy black frames)
- Numbered 9-point Commercial Terms & Conditions panel
- Formal 'Customer Acceptance' order confirmation signature box at base
- Stamps: DRAFT, EXPIRED

Quality Standard: Professional corporate B2B commercial estimate.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
)

# Core plumbing imports ONLY - templates must NEVER import from other templates
from app.services.pdf.core.page import (
    PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN, FRAME_WIDTH, FRAME_HEIGHT, NumberedCanvas, SimpleDocTemplate
)
from app.services.pdf.core.flex_table import calculate_filler_height, build_stretched_table
from app.services.pdf.core.adaptive_table import (
    AdaptiveCell, build_adaptive_items_table
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

COLOR_NAVY = colors.HexColor("#0F2942")         # Executive Proposal Navy
COLOR_NAVY_LIGHT = colors.HexColor("#F0F4F8")   # Very soft navy tint
COLOR_BORDER_SOFT = colors.HexColor("#CBD5E1")  # Slate 300
COLOR_LINE = colors.HexColor("#E2E8F0")         # Slate 200
COLOR_MUTED = colors.HexColor("#475569")        # Slate 600
COLOR_GOLD = colors.HexColor("#B45309")         # Amber 700 for validity badge

# Font sizes
FS_LETTERHEAD = 14.0
FS_TITLE = 13.0
FS_SECTION = 8.5
FS_BODY = 7.2
FS_SMALL = 6.5
FS_TINY = 5.8

# Items columns: Sl(24), Desc(174.58), HSN(46), Qty(44), Unit(30), UnitPrice(50), Disc(36), Tax%(44), Amt(66) = 538.58 pt
COLS_QUOTATION = [24.0, 174.58, 46.0, 44.0, 30.0, 50.0, 36.0, 44.0, 66.0]


def _build_quotation_story(data: Dict[str, Any]) -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or {}
    totals = data.get("totals", {}) or {}

    q_num = escape_xml(data.get("invoice_number") or data.get("quotation_number", "QT-DRAFT"))
    q_date = format_date_ddmmyyyy(data.get("date") or data.get("quotation_date"))
    valid_until = format_date_ddmmyyyy(data.get("valid_until"))

    # 1. Letterhead Block (Logo on left + Company Information on right/center)
    half_w = FRAME_WIDTH_PT / 2.0
    logo_img = load_safe_image(comp.get("logo_path"), max_w_pt=75.0, max_h_pt=40.0)

    comp_info_lines = [
        Paragraph(f"<b>{escape_xml(comp.get('name', 'Company Name'))}</b>", make_p(font_size=FS_LETTERHEAD, bold=True, color=COLOR_NAVY, leading=FS_LETTERHEAD + 2)),
        Paragraph(escape_xml(comp.get('address', '')), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)),
        Paragraph(f"GSTIN: <b>{escape_xml(comp.get('gstin', 'N/A'))}</b> | PAN: <b>{escape_xml(comp.get('pan', 'N/A'))}</b>", make_p(font_size=FS_BODY)),
        Paragraph(f"Email: {escape_xml(comp.get('email', ''))} | Phone: {escape_xml(comp.get('phone', ''))}", make_p(font_size=FS_BODY)),
    ]

    if logo_img:
        hdr_table = Table([[logo_img, comp_info_lines]], colWidths=[80.0, FRAME_WIDTH_PT - 80.0])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
    else:
        hdr_table = Table([[comp_info_lines]], colWidths=[FRAME_WIDTH_PT])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
    story.append(hdr_table)

    # Decorative thin accent bar
    bar_table = Table([[""]], colWidths=[FRAME_WIDTH_PT], rowHeights=[2.0])
    bar_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_NAVY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(bar_table)
    story.append(Spacer(1, 4))

    # 2. Quotation Title & Reference Strip
    title_left = Paragraph("<b>QUOTATION</b>", make_p(font_size=FS_TITLE, bold=True, color=COLOR_NAVY))
    meta_right = Paragraph(
        f"Quotation No.: <b>{q_num}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Date: <b>{q_date}</b>"
        + (f" &nbsp;&nbsp;|&nbsp;&nbsp; <font color='#B45309'><b>Valid Until: {valid_until}</b></font>" if valid_until else ""),
        make_p(font_size=FS_BODY + 0.5, alignment=2)
    )
    title_strip = Table([[title_left, meta_right]], colWidths=[140.0, FRAME_WIDTH_PT - 140.0])
    title_strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_BORDER_SOFT),
    ]))
    story.append(title_strip)
    story.append(Spacer(1, 4))

    # 3. Addressee & Enquiry Details Block
    kind_attn = escape_xml(data.get("kind_attn") or cust.get("contact_person") or "")
    enquiry_ref = escape_xml(data.get("enquiry_ref_date") or data.get("reference_number") or "-")
    subject_text = escape_xml(data.get("subject") or "Quotation for Supply of Materials / Equipment")

    to_lines = [
        "<b>To,</b>",
        f"<b>{escape_xml(cust.get('name', 'Client'))}</b>",
        escape_xml(cust.get('address', '')),
        f"GSTIN: <b>{escape_xml(cust.get('gstin', 'N/A'))}</b> | State: {escape_xml(cust.get('state', ''))}"
    ]
    if kind_attn:
        to_lines.append(f"<b>Kind Attn.:</b> {kind_attn}")

    p_to = Paragraph("<br/>".join(to_lines), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    p_enq = Paragraph(
        f"<b>Your Enquiry Ref. &amp; Date:</b><br/>{enquiry_ref}<br/><br/>"
        f"<b>Subject:</b><br/><u>{subject_text}</u>",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    party_table = Table([[p_to, p_enq]], colWidths=[half_w + 20.0, half_w - 20.0])
    party_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_NAVY_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER_SOFT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER_SOFT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 3))

    # 4. Opening Salutation Paragraph
    p_salut = Paragraph(
        "Dear Sir/Madam,<br/>"
        "With reference to your enquiry, we are pleased to offer our best quotation as follows:",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )
    story.append(p_salut)
    story.append(Spacer(1, 3))

    # 5. Items Table
    headers = [
        [
            Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Description</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Qty</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Unit Price</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Disc %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Tax %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]
    ]

    item_specs: List[List[AdaptiveCell]] = []
    tot_qty = 0.0
    tot_amt = 0.0

    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        unit = escape_xml(it.get("unit") or "PCS")
        rate = float(it.get("unit_price") or 0.0)
        disc_val = float(it.get("discount_pct") or 0.0)
        tax_pct = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        amt = float(it.get("total_item_amount") or (qty * rate))
        tot_amt += amt

        disc_str = f"{disc_val:.1f}%" if disc_val > 0 else "-"
        rate_str = format_currency(rate, num_fmt)
        amt_str = format_currency(amt, num_fmt)

        item_specs.append([
            AdaptiveCell(str(idx), alignment=1),
            AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
            AdaptiveCell(hsn, alignment=1),
            AdaptiveCell(f"{qty:,.2f}", alignment=2),
            AdaptiveCell(unit, alignment=1),
            AdaptiveCell(rate_str, alignment=2),
            AdaptiveCell(disc_str, alignment=2),
            AdaptiveCell(f"{tax_pct:.1f}%", alignment=2),
            AdaptiveCell(amt_str, alignment=2),
        ])

    total_row = [
        Paragraph("", make_p()),
        Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
        Paragraph("", make_p()),
        Paragraph(f"<b>{tot_qty:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph(f"<b>Rs. {format_currency(tot_amt, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
    ]

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_NAVY),
        ('LINEABOVE', (0, -1), (-1, -1), 0.6, COLOR_BORDER_SOFT),
        ('LINEBELOW', (0, -1), (-1, -1), 0.6, COLOR_BORDER_SOFT),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_LINE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER_SOFT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    # 6. Summary & Price Basis
    footer_elements = []

    sub_tot = float(totals.get("subtotal") or tot_amt)
    tax_amt = float(totals.get("tax_amount") or totals.get("igst_total") or 0.0)
    grand_total = float(totals.get("grand_total") or totals.get("total_amount") or tot_amt)
    amt_words = amount_to_words_inr(grand_total)

    price_basis = escape_xml(data.get("price_basis") or "Prices are Ex-works / Taxes extra as applicable")
    price_basis_p = Paragraph(f"<b>Price Basis:</b> {price_basis}<br/><b>Amount in Words:</b> {amt_words}", make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    tot_table_rows = [
        [Paragraph("Sub Total:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sub_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("Taxes (GST):", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(tax_amt, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("<b>Total Value:</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_NAVY)), Paragraph(f"<b>Rs. {format_currency(grand_total, num_fmt)}</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_NAVY, alignment=2))],
    ]
    t_tot = Table(tot_table_rows, colWidths=[half_w * 0.45, half_w * 0.55])
    t_tot.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_LINE),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER_SOFT),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_NAVY_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    sum_strip = Table([[price_basis_p, t_tot]], colWidths=[half_w, half_w])
    sum_strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    footer_elements.append(sum_strip)

    # 7. Numbered Commercial Terms & Conditions (Clean 2-Column layout)
    t_pay = escape_xml(data.get("terms_payment") or "100% against delivery / Proforma Invoice")
    t_del = escape_xml(data.get("terms_delivery") or "2-3 weeks from receipt of confirm PO")
    t_val = escape_xml(data.get("terms_validity") or "30 days from date of quotation")
    t_frt = escape_xml(data.get("terms_freight") or "Extra at actuals / To Pay")
    t_pck = escape_xml(data.get("terms_packing") or "Included / Standard export packing")
    t_war = escape_xml(data.get("terms_warranty") or "12 months from date of supply")
    t_tax = escape_xml(data.get("terms_taxes") or "GST extra as applicable")
    t_ins = escape_xml(data.get("terms_inspection") or "At our works prior to dispatch")
    t_jur = escape_xml(data.get("terms_jurisdiction") or "Subject to local court jurisdiction")

    terms_col1 = [
        Paragraph(f"<b>1. Payment Terms:</b> {t_pay}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>2. Delivery Period:</b> {t_del}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>3. Validity:</b> {t_val}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>4. Freight:</b> {t_frt}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>5. Packing:</b> {t_pck}", make_p(font_size=FS_TINY + 0.5)),
    ]
    terms_col2 = [
        Paragraph(f"<b>6. Warranty:</b> {t_war}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>7. Taxes:</b> {t_tax}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>8. Inspection:</b> {t_ins}", make_p(font_size=FS_TINY + 0.5)),
        Paragraph(f"<b>9. Jurisdiction:</b> {t_jur}", make_p(font_size=FS_TINY + 0.5)),
    ]

    terms_table = Table([[terms_col1, terms_col2]], colWidths=[half_w, half_w])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER_SOFT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(Paragraph("<b>Terms &amp; Conditions:</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_NAVY)))
    footer_elements.append(terms_table)

    # 8. Signatory & Boxed "Customer Acceptance" Slip at bottom
    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=80.0, max_h_pt=24.0)
    seal_img = load_safe_image(comp.get("seal_path"), max_w_pt=50.0, max_h_pt=24.0)

    for_company = [
        Paragraph(f"For <b>{escape_xml(comp.get('name', 'Company'))}</b>", make_p(font_size=FS_BODY, alignment=2)),
    ]
    if sig_img or seal_img:
        row_imgs = []
        if seal_img: row_imgs.append(seal_img)
        if sig_img: row_imgs.append(sig_img)
        t_imgs = Table([row_imgs], colWidths=[half_w / float(len(row_imgs))] * len(row_imgs))
        t_imgs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        for_company.append(t_imgs)
    else:
        for_company.append(Spacer(1, 18.0))
    for_company.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)))

    # Boxed Customer Acceptance Slip
    accept_text = [
        Paragraph("<b>Customer Acceptance:</b> <i>We accept this quotation and confirm our order</i>", make_p(font_size=FS_SMALL, bold=True)),
        Paragraph("Name &amp; Designation: __________________________ &nbsp;&nbsp;&nbsp; Date: ______________", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Signature &amp; Company Seal: ______________________ &nbsp;&nbsp;&nbsp; PO No.: _____________", make_p(font_size=FS_TINY + 0.5)),
    ]

    bot_table = Table([[accept_text, for_company]], colWidths=[half_w + 20.0, half_w - 20.0])
    bot_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 0.6, COLOR_BORDER_SOFT),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(Spacer(1, 2))
    footer_elements.append(bot_table)

    # 9. Build Adaptive Items Table Flowables
    table_flowables = build_adaptive_items_table(
        headers=headers,
        item_specs=item_specs,
        col_widths=COLS_QUOTATION,
        base_style=table_style,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.6, COLOR_BORDER_SOFT),
            ('LINEBELOW', (0, -1), (-1, -1), 0.6, COLOR_BORDER_SOFT),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_NAVY_LIGHT),
            ('TOPPADDING', (0, -1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 2),
        ],
        flowables_before=list(story),
        flowables_after=footer_elements,
        company_settings=comp,
        available_width=FRAME_WIDTH_PT,
        available_height=FRAME_HEIGHT,
        fallback_font_size=FS_BODY,
        fallback_padding=2.0,
        desc_col_idx=1,
        grid_color=COLOR_LINE
    )

    story.extend(table_flowables)
    story.extend(footer_elements)
    return story


def render_quotation_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Quotation to an A4 PDF document with corporate proposal letter layout."""
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

    story = _build_quotation_story(data)

    status = str(data.get("status", "")).lower()

    class QuotationNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "expired":
                draw_watermark_stamp(self, "EXPIRED", color_hex="#DC2626")

    doc.build(story, canvasmaker=QuotationNumberedCanvas)
    return output_path
