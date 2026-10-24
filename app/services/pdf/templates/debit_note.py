"""
BillFlow Suite - Debit Note Template (Purchase Return & Supplier Adjustment Architecture)
========================================================================================
Statutory Citation: Issued under Section 34 of the CGST Act, 2017.
Design Features (Visibly distinct from Credit Note):
- Full-width deep indigo title ribbon across top with white text
- 2-Column asymmetrical party layout: Left 'Supplier / Vendor (Debited)' vs Right 'From (Buyer Operations)'
- Boxed badge matrix for Return Reasons
- Distinct column arrangement: Sl | Item Code & Description | HSN | Qty | Unit | Unit Price | Taxable | GST ITC | Debit Total
- Highlighted statutory 'Input Tax Credit (ITC) Reversal' declaration box
- Standalone Dispatch & Vehicle Return card
- Supplier acceptance sign-off block

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

COLOR_INDIGO_DARK = colors.HexColor("#1E1B4B")  # Deep Indigo 950
COLOR_INDIGO_MED = colors.HexColor("#3730A3")   # Indigo 800
COLOR_BG_LIGHT = colors.HexColor("#EEF2FF")     # Indigo 50
COLOR_BG_CARD = colors.HexColor("#F8FAFC")      # Slate 50
COLOR_BORDER = colors.HexColor("#818CF8")       # Indigo 400
COLOR_GRID = colors.HexColor("#CBD5E1")         # Slate 300
COLOR_WHITE = colors.HexColor("#FFFFFF")

# Font sizes
FS_BANNER = 13.0
FS_SECTION = 8.5
FS_BODY = 7.2
FS_SMALL = 6.4
FS_TINY = 5.8

# Distinct 9 Columns: Sl(22), HSN(46), Desc(166.58), Qty(44), Unit(28), Rate(46), Taxable(58), GST_ITC(58), DebitTot(70) = 538.58 pt
COLS_DEBIT_DISTINCT = [22.0, 46.0, 166.58, 44.0, 28.0, 46.0, 58.0, 58.0, 70.0]

DEBIT_REASONS = [
    "Purchase Return",
    "Rate Difference",
    "Shortage",
    "Damaged/Rejected Goods",
    "Quality Rejection",
    "Others"
]


def _build_debit_note_story(data: Dict[str, Any]) -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    supplier = data.get("customer", {}) or data.get("supplier", {}) or {}
    totals = data.get("totals", {}) or {}

    dn_num = escape_xml(data.get("return_number") or data.get("invoice_number", "DN-DRAFT"))
    dn_date = format_date_ddmmyyyy(data.get("return_date") or data.get("date"))

    supp_bill_no = escape_xml(data.get("original_bill_no") or data.get("original_invoice_no") or data.get("reference_number") or "-")
    supp_bill_date = format_date_ddmmyyyy(data.get("original_bill_date") or data.get("original_invoice_date")) or "-"
    po_ref = escape_xml(data.get("po_number") or data.get("grn_number") or "-")

    # 1. Full-Width Deep Indigo Title Banner
    banner_left = Paragraph(
        "<b>DEBIT NOTE &nbsp;&bull;&nbsp; COMMERCIAL &amp; GST ADJUSTMENT</b><br/>"
        "<font size=6.5 color='#C7D2FE'>Issued under Section 34 of the CGST Act, 2017 &bull; Input Tax Credit Reversal Document</font>",
        make_p(font_size=FS_BANNER - 2, bold=True, color=COLOR_WHITE)
    )
    banner_right = Paragraph(
        f"<b>Debit Note No.: {dn_num}</b><br/>"
        f"Date: <b>{dn_date}</b>",
        make_p(font_size=FS_BODY + 1, alignment=2, color=COLOR_WHITE)
    )
    t_banner = Table([[banner_left, banner_right]], colWidths=[FRAME_WIDTH_PT - 160.0, 160.0])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_INDIGO_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 3))

    # 2. Dual Asymmetrical Cards: Left 'Supplier Debited' vs Right 'Procurement Department'
    w_left = FRAME_WIDTH_PT * 0.55
    w_right = FRAME_WIDTH_PT * 0.45

    supp_p = Paragraph(
        f"<b>Supplier Debited:</b><br/>"
        f"<b>{escape_xml(supplier.get('name', 'Supplier Name'))}</b><br/>"
        f"{escape_xml(supplier.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(supplier.get('gstin', 'N/A'))}</b> &nbsp;|&nbsp; State: <b>{escape_xml(supplier.get('state', ''))}</b>",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    buyer_p = Paragraph(
        f"<b>Issued By (Buyer):</b><br/>"
        f"<b>{escape_xml(comp.get('name') or '')}</b><br/>"
        f"{escape_xml(comp.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(comp.get('gstin') or 'Unregistered')}</b><br/>"
        f"Against Supplier Invoice: <b>{supp_bill_no}</b> dt. <b>{supp_bill_date}</b><br/>"
        f"Our Purchase/Goods Receipt Ref.: <b>{po_ref}</b>",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    t_parties = Table([[supp_p, buyer_p]], colWidths=[w_left, w_right])
    t_parties.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), COLOR_BG_LIGHT),
        ('BACKGROUND', (1, 0), (1, 0), COLOR_BG_CARD),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_parties)
    story.append(Spacer(1, 3))

    # 3. Reason for Debit Badge Matrix (2 Rows x 3 Columns)
    curr_reason = (data.get("reason_category") or data.get("reason") or "Purchase Return").strip()
    reason_cells = []
    for r in DEBIT_REASONS:
        mark = "[X]" if curr_reason.lower() in r.lower() else "[ &nbsp; ]"
        reason_cells.append(Paragraph(f"<b>{mark}</b> {r}", make_p(font_size=FS_SMALL)))

    r_row1 = reason_cells[:3]
    r_row2 = reason_cells[3:]
    t_reasons = Table([r_row1, r_row2], colWidths=[FRAME_WIDTH_PT / 3.0] * 3)
    t_reasons.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(Paragraph("<b>Reason for Debit:</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_INDIGO_MED)))
    story.append(t_reasons)
    story.append(Spacer(1, 3))

    # 4. Items Table: Particulars of goods debited / returned
    story.append(Paragraph("<b>Particulars of goods debited / returned:</b>", make_p(font_size=FS_SECTION, bold=True, color=COLOR_INDIGO_MED)))
    story.append(Spacer(1, 2))

    headers = [
        [
            Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Description of Goods Debited</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("<b>Qty</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Taxable Value</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>GST ITC</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Total Debit</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]
    ]

    item_rows = []
    tot_qty = 0.0
    tot_taxable = 0.0
    tot_tax = 0.0
    tot_debit = 0.0

    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Debited Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        unit = escape_xml(it.get("unit") or "PCS")
        rate = float(it.get("unit_price") or 0.0)
        taxable = float(it.get("taxable_value") or (qty * rate))
        tot_taxable += taxable
        tax_pct = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        tax_amt = float(it.get("tax_amount") or (taxable * (tax_pct / 100.0)))
        tot_tax += tax_amt
        tot_item = float(it.get("total_item_amount") or it.get("total_amount") or (taxable + tax_amt))
        tot_debit += tot_item

        item_rows.append([
            Paragraph(str(idx), make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(hsn, make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(f"<b>{desc}</b>", make_p(font_size=FS_BODY)),
            Paragraph(f"{qty:,.2f}", make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(unit, make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(format_currency(rate, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(format_currency(taxable, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(f"{tax_pct:.1f}% : {format_currency(tax_amt, num_fmt)}", make_p(font_size=FS_SMALL, alignment=2)),
            Paragraph(format_currency(tot_item, num_fmt), make_p(font_size=FS_BODY, alignment=2)),
        ])

    total_row = [
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
        Paragraph(f"<b>{tot_qty:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph(f"<b>Rs. {format_currency(tot_taxable, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph(f"<b>Rs. {format_currency(tot_tax, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph(f"<b>Rs. {format_currency(tot_debit, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
    ]

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_INDIGO_MED),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    meas_table = Table(headers + item_rows + [total_row], colWidths=COLS_DEBIT_DISTINCT)
    meas_table.setStyle(TableStyle(table_style))

    # 5. Summary & Reversal Cards
    footer_elements = []

    sub_tot = float(totals.get("subtotal") or tot_taxable)
    cgst_tot = float(totals.get("cgst_total") or totals.get("cgst_amount") or 0.0)
    sgst_tot = float(totals.get("sgst_total") or totals.get("sgst_amount") or 0.0)
    igst_tot = float(totals.get("igst_total") or totals.get("igst_amount") or (tot_tax if cgst_tot == 0 and sgst_tot == 0 else 0.0))
    grand_debit = float(totals.get("total_amount") or totals.get("grand_total") or tot_debit)

    sum_rows = [
        [Paragraph("Taxable Value Debited:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sub_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
    ]
    if cgst_tot > 0 or sgst_tot > 0:
        sum_rows.append([Paragraph("Input Tax Credit (ITC) to be Reversed (CGST):", make_p(font_size=FS_SMALL)), Paragraph(f"Rs. {format_currency(cgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
        sum_rows.append([Paragraph("Input Tax Credit (ITC) to be Reversed (SGST):", make_p(font_size=FS_SMALL)), Paragraph(f"Rs. {format_currency(sgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
    if igst_tot > 0:
        sum_rows.append([Paragraph("Input Tax Credit (ITC) to be Reversed (IGST):", make_p(font_size=FS_SMALL)), Paragraph(f"Rs. {format_currency(igst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])

    sum_rows.append([
        Paragraph("<b>Total Debit Amount:</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_INDIGO_MED)),
        Paragraph(f"<b>Rs. {format_currency(grand_debit, num_fmt)}</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_INDIGO_MED, alignment=2))
    ])

    half_w = FRAME_WIDTH_PT / 2.0
    t_sum = Table(sum_rows, colWidths=[half_w * 0.58, half_w * 0.42])
    t_sum.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    amt_words = amount_to_words_inr(grand_debit)
    p_words = Paragraph(f"Amount in Words:<br/><b>{amt_words}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    ret_via = escape_xml(data.get("returned_via") or "Courier / Transporter Dispatch")
    veh_ref = escape_xml(data.get("vehicle_no") or data.get("eway_bill_no") or "-")
    p_goods_ret = Paragraph(
        f"<b>Goods Return Details:</b><br/>"
        f"Returned Via: <b>{ret_via}</b> &nbsp;&bull;&nbsp; Vehicle/Doc Ref: <b>{veh_ref}</b><br/>"
        f"<font color='#475569'>We confirm that Input Tax Credit (ITC) against the above items is reversed in our GSTR-3B.</font>",
        make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5)
    )

    t_sum_strip = Table([[Paragraph("", make_p()), ""], [p_words, t_sum], [p_goods_ret, ""]], colWidths=[half_w, half_w])
    t_sum_strip.setStyle(TableStyle([
        ('SPAN', (0, 2), (1, 2)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    footer_elements.append(t_sum_strip)
    footer_elements.append(Spacer(1, 2))

    # 6. Signatory & Supplier Acknowledgement
    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=75.0, max_h_pt=20.0)

    auth_lines = [
        Paragraph(f"for <b>{escape_xml(comp.get('name') or '')}</b>", make_p(font_size=FS_BODY, alignment=2)),
    ]
    if sig_img:
        auth_lines.append(sig_img)
    else:
        auth_lines.append(Spacer(1, 16.0))
    auth_lines.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)))

    supp_ack_lines = [
        Paragraph("<b>Supplier Acknowledgement: We accept this debit note</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_INDIGO_MED)),
        Paragraph("<i>Accepted debit amount to be adjusted against supplier ledger credit.</i>", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Name: __________________________ &nbsp;&nbsp;&nbsp; Date: ____________", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Supplier Signature &amp; Seal: _____________________", make_p(font_size=FS_TINY + 0.5)),
    ]

    t_signs = Table([[supp_ack_lines, auth_lines]], colWidths=[half_w + 15.0, half_w - 15.0])
    t_signs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    footer_elements.append(t_signs)

    # 7. Measure flex filler
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
        col_widths=COLS_DEBIT_DISTINCT,
        base_style=table_style,
        filler_height=filler_h,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
            ('TOPPADDING', (0, -1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 2),
        ]
    )

    story.append(stretched_table)
    story.extend(footer_elements)
    return story


def render_debit_note_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Debit Note to an A4 PDF document with distinct supplier return layout."""
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

    story = _build_debit_note_story(data)
    status = str(data.get("status", "")).lower()

    class DebitNoteNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "cancelled":
                draw_watermark_stamp(self, "CANCELLED", color_hex="#DC2626")

    doc.build(story, canvasmaker=DebitNoteNumberedCanvas)
    return output_path
