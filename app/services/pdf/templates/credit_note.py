"""
BillFlow Suite - Credit Note Template (Sales Return & Adjustment Architecture)
==============================================================================
Statutory Citation: Issued under Section 34 of the CGST Act, 2017.
Design Features:
- Distinctive Burgundy/Crimson accounting credit accent styling
- Original Tax Invoice linkage and historical invoice value reference
- Reason for Issue standardized selection matrix
- Clear statutory itemization of Taxable Value Reversed and GST Tax Reversal
- Account Adjustment / Refund Allocation panel
- Dual Signatures: Company Authorized Signatory and Customer Acknowledgement strip

Stamps: DRAFT, CANCELLED.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

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

COLOR_CRIMSON = colors.HexColor("#881337")      # Rose/Burgundy 900
COLOR_BG_LIGHT = colors.HexColor("#FFF1F2")     # Rose 50
COLOR_BORDER = colors.HexColor("#FDA4AF")       # Rose 300
COLOR_GRID = colors.HexColor("#CBD5E1")         # Slate 300
COLOR_DARK = colors.HexColor("#0F172A")         # Slate 900

# Font sizes
FS_TITLE = 14.0
FS_SECTION = 8.5
FS_BODY = 7.2
FS_SMALL = 6.4
FS_TINY = 5.8

# Items columns: Sl(24), Desc(174.58), HSN(46), Qty(44), Rate(46), TaxableVal(58), Tax%(38), TaxAmt(44), Total(64) = 538.58 pt
COLS_CREDIT_NOTE = [24.0, 174.58, 46.0, 44.0, 46.0, 58.0, 38.0, 44.0, 64.0]

CREDIT_REASONS = [
    "Sales Return",
    "Rate/Price Difference",
    "Post-Sale Discount",
    "Deficiency in Goods/Services",
    "Others"
]


def _build_credit_note_story(data: Dict[str, Any]) -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or {}
    totals = data.get("totals", {}) or {}

    cn_num = escape_xml(data.get("return_number") or data.get("invoice_number", "CN-DRAFT"))
    cn_date = format_date_ddmmyyyy(data.get("return_date") or data.get("date"))

    orig_inv = escape_xml(data.get("original_invoice_no") or data.get("original_invoice_number") or data.get("reference_number") or "-")
    orig_date = format_date_ddmmyyyy(data.get("original_invoice_date")) or "-"
    orig_val = float(data.get("original_invoice_value") or totals.get("original_total", 0.0))

    # 1. Title Bar: "CREDIT NOTE" + Section 34 Statutory Citation
    title_data = [
        [
            Paragraph(f"<b>CREDIT NOTE</b><br/><font size=7 color='#475569'>Issued under Section 34 of the CGST Act, 2017</font>", make_p(font_size=FS_TITLE, bold=True, color=COLOR_CRIMSON)),
            Paragraph(f"Credit Note No.: <b>{cn_num}</b><br/>Date: <b>{cn_date}</b>", make_p(font_size=FS_BODY + 1, alignment=2))
        ]
    ]
    t_title = Table(title_data, colWidths=[FRAME_WIDTH_PT - 170.0, 170.0])
    t_title.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, COLOR_CRIMSON),
    ]))
    story.append(t_title)
    story.append(Spacer(1, 3))

    # 2. Original Invoice Linkage Strip
    orig_str = f"Against Invoice No. &amp; Date: <b>{orig_inv}</b> dt. <b>{orig_date}</b>"
    if orig_val > 0:
        orig_str += f" &nbsp;&nbsp;|&nbsp;&nbsp; Original Invoice Value: <b>Rs. {format_currency(orig_val, num_fmt)}</b>"

    t_orig = Table([[Paragraph(orig_str, make_p(font_size=FS_BODY + 0.5, color=COLOR_CRIMSON))]], colWidths=[FRAME_WIDTH_PT])
    t_orig.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_orig)
    story.append(Spacer(1, 3))

    # 3. Reason for Issue Checkbox Row
    curr_reason = (data.get("reason_category") or data.get("reason") or "Sales Return").strip()
    reason_spans = []
    for r in CREDIT_REASONS:
        mark = "[X]" if curr_reason.lower() in r.lower() else "[ &nbsp; ]"
        reason_spans.append(f"<b>{mark}</b> {r}")

    p_reason = Paragraph(f"<b>Reason for Issue:</b> &nbsp;&nbsp;&nbsp;&nbsp; " + " &nbsp;&nbsp;&nbsp;&nbsp; ".join(reason_spans), make_p(font_size=FS_SMALL))
    t_reasons = Table([[p_reason]], colWidths=[FRAME_WIDTH_PT])
    t_reasons.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_reasons)
    story.append(Spacer(1, 3))

    # 4. Parties Block (Consignor / Issuer on Left; Issued To Customer on Right)
    half_w = FRAME_WIDTH_PT / 2.0

    issuer_p = Paragraph(
        f"<b>Issued By:</b><br/>"
        f"<b>{escape_xml(comp.get('name') or '')}</b><br/>"
        f"{escape_xml(comp.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(comp.get('gstin') or 'Unregistered')}</b> | State: {escape_xml(comp.get('state', ''))}",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    issued_to_p = Paragraph(
        f"<b>Issued To (Customer):</b><br/>"
        f"<b>{escape_xml(cust.get('name', 'Customer'))}</b><br/>"
        f"{escape_xml(cust.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(cust.get('gstin', 'N/A'))}</b> | State: <b>{escape_xml(cust.get('state', ''))}</b> (Code: {escape_xml(cust.get('state_code', '-'))})",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    parties_table = Table([[issuer_p, issued_to_p]], colWidths=[half_w, half_w])
    parties_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 3))

    # 5. Items Table: Particulars of Goods Returned / Adjustment
    story.append(Paragraph("<b>Particulars of goods returned / adjustment:</b>", make_p(font_size=FS_SECTION, bold=True, color=COLOR_CRIMSON)))
    story.append(Spacer(1, 2))

    headers = [
        [
            Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Description</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Qty Returned</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Taxable Value</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Tax %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Tax Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]
    ]

    item_rows = []
    tot_qty = 0.0
    tot_taxable = 0.0
    tot_tax = 0.0
    tot_credit = 0.0

    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Returned Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        rate = float(it.get("unit_price") or 0.0)
        taxable = float(it.get("taxable_value") or (qty * rate))
        tot_taxable += taxable
        tax_pct = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        tax_amt = float(it.get("tax_amount") or (taxable * (tax_pct / 100.0)))
        tot_tax += tax_amt
        tot_item = float(it.get("total_item_amount") or it.get("total_amount") or (taxable + tax_amt))
        tot_credit += tot_item

        item_rows.append([
            Paragraph(str(idx), make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(f"<b>{desc}</b>", make_p(font_size=FS_BODY)),
            Paragraph(hsn, make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(f"{qty:,.2f}", make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(format_currency(rate, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(format_currency(taxable, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(f"{tax_pct:.1f}%", make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(format_currency(tax_amt, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(format_currency(tot_item, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
        ])

    total_row = [
        Paragraph("", make_p()),
        Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
        Paragraph("", make_p()),
        Paragraph(f"<b>{tot_qty:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
        Paragraph(f"<b>Rs. {format_currency(tot_taxable, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
        Paragraph(f"<b>Rs. {format_currency(tot_tax, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph(f"<b>Rs. {format_currency(tot_credit, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
    ]

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_CRIMSON),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    meas_table = Table(headers + item_rows + [total_row], colWidths=COLS_CREDIT_NOTE)
    meas_table.setStyle(TableStyle(table_style))

    # 6. Summary: Taxable Value Reversed & Taxes Reversed
    footer_elements = []

    sub_tot = float(totals.get("subtotal") or tot_taxable)
    cgst_tot = float(totals.get("cgst_total") or totals.get("cgst_amount") or 0.0)
    sgst_tot = float(totals.get("sgst_total") or totals.get("sgst_amount") or 0.0)
    igst_tot = float(totals.get("igst_total") or totals.get("igst_amount") or (tot_tax if cgst_tot == 0 and sgst_tot == 0 else 0.0))
    grand_credit = float(totals.get("total_amount") or totals.get("grand_total") or tot_credit)

    sum_rows = [
        [Paragraph("Taxable Value Reversed:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sub_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
    ]
    if cgst_tot > 0 or sgst_tot > 0:
        sum_rows.append([Paragraph("CGST Reversed:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(cgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
        sum_rows.append([Paragraph("SGST Reversed:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
    if igst_tot > 0:
        sum_rows.append([Paragraph("IGST Reversed:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(igst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])

    sum_rows.append([
        Paragraph("<b>Total Credit Amount:</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_CRIMSON)),
        Paragraph(f"<b>Rs. {format_currency(grand_credit, num_fmt)}</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_CRIMSON, alignment=2))
    ])

    t_sum = Table(sum_rows, colWidths=[half_w * 0.5, half_w * 0.5])
    t_sum.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    amt_words = amount_to_words_inr(grand_credit)
    p_words = Paragraph(f"Amount in Words:<br/><b>{amt_words}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    # Adjustment Details box
    adj_mode = escape_xml(data.get("adjustment_mode") or "Credit Note / Ledger Adjustment")
    adj_ref = escape_xml(data.get("adjustment_ref") or "Adjusted against customer outstanding ledger balance")
    p_adj = Paragraph(f"<b>Adjustment Details:</b><br/>Mode: {adj_mode}<br/>Reference: {adj_ref}", make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5))

    left_sum_box = [p_words, Spacer(1, 4), p_adj]
    t_sum_strip = Table([[left_sum_box, t_sum]], colWidths=[half_w, half_w])
    t_sum_strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(t_sum_strip)
    footer_elements.append(Spacer(1, 3))

    # 7. Signatory & Customer Acknowledgement Strip
    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=80.0, max_h_pt=24.0)

    auth_lines = [
        Paragraph(f"for <b>{escape_xml(comp.get('name') or '')}</b>", make_p(font_size=FS_BODY, alignment=2)),
    ]
    if sig_img:
        auth_lines.append(sig_img)
    else:
        auth_lines.append(Spacer(1, 20.0))
    auth_lines.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)))

    ack_lines = [
        Paragraph("<b>Customer Acknowledgement:</b>", make_p(font_size=FS_SMALL, bold=True)),
        Paragraph("<i>We acknowledge receipt of this credit note and agree to the above adjustments.</i>", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Received by: ________________________ &nbsp;&nbsp;&nbsp; Date: ____________", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Signature / Stamp: ___________________", make_p(font_size=FS_TINY + 0.5)),
    ]

    t_signs = Table([[ack_lines, auth_lines]], colWidths=[half_w + 20.0, half_w - 20.0])
    t_signs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    footer_elements.append(t_signs)

    # 8. Measure flex filler
    filler_h = calculate_filler_height(
        flowables_before_table=list(story),
        items_table_initial=meas_table,
        flowables_after_table=footer_elements,
        available_width=FRAME_WIDTH_PT,
        available_height=FRAME_HEIGHT,
        min_filler=10.0
    )

    stretched_table = build_stretched_table(
        header_data=headers,
        item_rows=item_rows,
        col_widths=COLS_CREDIT_NOTE,
        base_style=table_style,
        filler_height=filler_h,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
            ('TOPPADDING', (0, -1), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 2.5),
        ]
    )

    story.append(stretched_table)
    story.extend(footer_elements)
    return story


def render_credit_note_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Credit Note to an A4 PDF document with Section 34 CGST statutory layout."""
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

    story = _build_credit_note_story(data)
    status = str(data.get("status", "")).lower()

    class CreditNoteNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "cancelled":
                draw_watermark_stamp(self, "CANCELLED", color_hex="#DC2626")

    doc.build(story, canvasmaker=CreditNoteNumberedCanvas)
    return output_path
