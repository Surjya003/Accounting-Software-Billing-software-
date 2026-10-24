"""
BillFlow Suite - Purchase Order Template (Procurement & Purchasing Architecture)
================================================================================
Design Features:
- Executive Emerald & Charcoal procurement styling
- Dual Facility Cards: Vendor / Supplier vs. Deliver To / Ship To
- Standardized procurement terms strip (Delivery Required By, Freight, Mode, Insurance)
- Detailed line items with Item Code, Delivery Date schedule, HSN, and GST
- Special Delivery Instructions and Quality Inspection clauses
- Triple sign-off: Prepared by, Authorized Signatory, and Supplier Order Acceptance

Stamps: DRAFT, CANCELLED, FULLY RECEIVED, PARTIALLY RECEIVED.
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
from app.services.pdf.core.adaptive_table import (
    AdaptiveCell, format_total_quantity, build_adaptive_items_table
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

COLOR_EMERALD = colors.HexColor("#065F46")     # Emerald 800
COLOR_BG_LIGHT = colors.HexColor("#ECFDF5")    # Mint 50
COLOR_BORDER = colors.HexColor("#6EE7B7")      # Mint 300
COLOR_GRID = colors.HexColor("#CBD5E1")        # Slate 300
COLOR_DARK = colors.HexColor("#0F172A")        # Slate 900

# Font sizes
FS_TITLE = 14.5
FS_SECTION = 8.5
FS_BODY = 7.2
FS_SMALL = 6.4
FS_TINY = 5.8

# 11 Items Columns: Sl(18), Code(33), Desc(130.58), HSN(50), Qty(38), Unit(26), Rate(50), Disc(33), GST(34), Amt(62), DelDate(64) = 538.58 pt
COLS_PO = [18.0, 33.0, 130.58, 50.0, 38.0, 26.0, 50.0, 33.0, 34.0, 62.0, 64.0]


def _build_po_story(data: Dict[str, Any]) -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    supplier = data.get("supplier", {}) or data.get("customer", {}) or {}
    totals = data.get("totals", {}) or {}

    po_num = escape_xml(data.get("po_number") or data.get("invoice_number", "PO-DRAFT"))
    po_date = format_date_ddmmyyyy(data.get("po_date") or data.get("date"))
    revision = escape_xml(str(data.get("revision") or "0"))
    quot_ref = escape_xml(data.get("quotation_ref") or "-")
    quot_date = format_date_ddmmyyyy(data.get("quotation_date")) or "-"

    # 1. Title Bar: "PURCHASE ORDER" + PO Metadata
    title_data = [
        [
            Paragraph(f"<b>PURCHASE ORDER</b>", make_p(font_size=FS_TITLE, bold=True, color=COLOR_EMERALD)),
            Paragraph(
                f"PO No.: <b>{po_num}</b> (Rev: <b>{revision}</b>)<br/>"
                f"Date: <b>{po_date}</b><br/>"
                f"Quotation Ref: {quot_ref} dt. {quot_date}",
                make_p(font_size=FS_BODY, alignment=2)
            )
        ]
    ]
    t_title = Table(title_data, colWidths=[FRAME_WIDTH_PT - 210.0, 210.0])
    t_title.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, COLOR_EMERALD),
    ]))
    story.append(t_title)
    story.append(Spacer(1, 3))

    # 2. Dual Cards: "Vendor / Supplier" vs. "Deliver To / Ship To"
    half_w = FRAME_WIDTH_PT / 2.0

    supp_lines = [
        "<b>Vendor / Supplier:</b>",
        f"<b>{escape_xml(supplier.get('name', 'Vendor Name'))}</b>",
        escape_xml(supplier.get('address', '')),
        f"GSTIN: <b>{escape_xml(supplier.get('gstin', 'N/A'))}</b> | State: {escape_xml(supplier.get('state', ''))}",
    ]
    if supplier.get('phone') or supplier.get('contact_person'):
        supp_lines.append(f"Attn: {escape_xml(supplier.get('contact_person', ''))} | Ph: {escape_xml(supplier.get('phone', ''))}")
    p_supp = Paragraph("<br/>".join(supp_lines), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    ship_addr = escape_xml(data.get("ship_to_address") or comp.get("address", ""))
    ship_lines = [
        "<b>Deliver To / Ship To:</b>",
        f"<b>{escape_xml(comp.get('name') or '')}</b>",
        ship_addr,
        f"GSTIN: <b>{escape_xml(comp.get('gstin') or 'Unregistered')}</b> | State: {escape_xml(comp.get('state', ''))}",
    ]
    if comp.get('phone') or comp.get('email'):
        ship_lines.append(f"Contact: {escape_xml(comp.get('phone', ''))} | Email: {escape_xml(comp.get('email', ''))}")
    p_ship = Paragraph("<br/>".join(ship_lines), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    t_parties = Table([[p_supp, p_ship]], colWidths=[half_w, half_w])
    t_parties.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_parties)
    story.append(Spacer(1, 3))

    # 3. Terms Strip (5 Columns: Delivery Required By, Payment Terms, Delivery Terms, Mode, Insurance)
    del_req = format_date_ddmmyyyy(data.get("delivery_required_by")) or "-"
    pay_terms = escape_xml(data.get("payment_terms") or "30 Days after receipt & approval")
    del_terms = escape_xml(data.get("delivery_terms") or "FOR Destination (Freight Paid)")
    mode_disp = escape_xml(data.get("mode_of_dispatch") or "Road Transport / Courier")
    ins_terms = escape_xml(data.get("insurance") or "Vendor's Scope / Transit Insured")

    fifth_w = FRAME_WIDTH_PT / 5.0
    terms_strip_data = [
        [
            Paragraph(f"Delivery Required By:<br/><b>{del_req}</b>", make_p(font_size=FS_SMALL, color=COLOR_EMERALD, bold=True)),
            Paragraph(f"Payment Terms:<br/><b>{pay_terms}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Delivery Terms:<br/><b>{del_terms}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Mode of Dispatch:<br/><b>{mode_disp}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Insurance:<br/><b>{ins_terms}</b>", make_p(font_size=FS_SMALL)),
        ]
    ]
    t_strip = Table(terms_strip_data, colWidths=[fifth_w] * 5)
    t_strip.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_strip)
    story.append(Spacer(1, 3))

    # 4. Items Table
    headers = [
        [
            Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Item Code</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Description</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Qty</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Disc%</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>GST%</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Delivery</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
        ]
    ]

    item_specs: List[List[AdaptiveCell]] = []
    tot_qty = 0.0
    tot_amt = 0.0

    for idx, it in enumerate(data.get("items", []), start=1):
        item_code = escape_xml(it.get("item_code") or "-")
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        unit = escape_xml(it.get("unit") or "PCS")
        rate = float(it.get("unit_price") or 0.0)
        disc_val = float(it.get("discount_pct") or 0.0)
        tax_pct = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        amt = float(it.get("total_item_amount") or it.get("total_amount") or (qty * rate))
        tot_amt += amt
        line_del = format_date_ddmmyyyy(it.get("delivery_date")) or del_req or "-"

        rate_str = format_currency(rate, num_fmt)
        amt_str = format_currency(amt, num_fmt)
        disc_str = f"{disc_val:.1f}%" if disc_val > 0 else "-"

        item_specs.append([
            AdaptiveCell(str(idx), alignment=1),
            AdaptiveCell(item_code, alignment=1),
            AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
            AdaptiveCell(hsn, alignment=1),
            AdaptiveCell(f"{qty:,.2f}", alignment=2),
            AdaptiveCell(unit, alignment=1),
            AdaptiveCell(rate_str, alignment=2),
            AdaptiveCell(disc_str, alignment=2),
            AdaptiveCell(f"{tax_pct:.1f}%", alignment=2),
            AdaptiveCell(amt_str, alignment=2),
            AdaptiveCell(line_del, alignment=1, is_small=True),
        ])

    tot_qty_str = format_total_quantity(data.get("items", []), tot_qty)
    total_row = [
        Paragraph("", make_p()),
        Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph(f"<b>{tot_qty_str}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph("", make_p()),
        Paragraph(f"<b>Rs. {format_currency(tot_amt, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        Paragraph("", make_p()),
    ]

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_EMERALD),
        ('LINEABOVE', (0, -1), (-1, -1), 0.6, COLOR_BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    # 5. Financial Summary & Special Instructions
    footer_elements = []

    sub_tot = float(totals.get("subtotal") or tot_amt)
    tax_amt = float(totals.get("tax_amount") or 0.0)
    grand_total = float(totals.get("total_amount") or totals.get("grand_total") or tot_amt)
    amt_words = amount_to_words_inr(grand_total)

    sum_rows = [
        [Paragraph("Sub Total:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sub_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("Taxes (GST):", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(tax_amt, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("<b>Grand Total:</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_EMERALD)), Paragraph(f"<b>Rs. {format_currency(grand_total, num_fmt)}</b>", make_p(font_size=FS_BODY + 1, bold=True, color=COLOR_EMERALD, alignment=2))],
    ]
    t_sum = Table(sum_rows, colWidths=[half_w * 0.45, half_w * 0.55])
    t_sum.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))

    spec_inst = escape_xml(data.get("special_instructions") or "1. Quote PO Number on all invoices, delivery challans, and packages.\n2. Goods must be securely packed to avoid transit damage.")
    p_spec = Paragraph(f"<b>Special Instructions:</b><br/>{spec_inst.replace(chr(10), '<br/>')}<br/><br/><b>Amount in Words:</b> {amt_words}", make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5))

    t_sum_strip = Table([[p_spec, t_sum]], colWidths=[half_w, half_w])
    t_sum_strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    footer_elements.append(t_sum_strip)

    # 6. Numbered Procurement Terms & Conditions
    po_terms = comp.get("terms_po") or "1. Goods subject to inspection and approval upon delivery.\n2. Defective materials will be rejected at vendor's cost.\n3. Late delivery penalty: 0.5% per week up to a maximum of 5%."
    p_terms = Paragraph(f"<b>Terms &amp; Conditions:</b><br/>{escape_xml(po_terms).replace(chr(10), '<br/>')}", make_p(font_size=FS_TINY + 0.5, leading=FS_TINY + 2.5))
    t_po_terms = Table([[p_terms]], colWidths=[FRAME_WIDTH_PT])
    t_po_terms.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    footer_elements.append(t_po_terms)
    footer_elements.append(Spacer(1, 2))

    # 7. Triple Sign-Off: Prepared by, Authorized Signatory, Supplier Acknowledgement
    w_prep = FRAME_WIDTH_PT * 0.25
    w_auth = FRAME_WIDTH_PT * 0.30
    w_supp = FRAME_WIDTH_PT * 0.45

    p_prep = [
        Paragraph("<b>Prepared by:</b>", make_p(font_size=FS_SMALL)),
        Spacer(1, 20.0),
        Paragraph("Purchase Executive", make_p(font_size=FS_TINY)),
    ]

    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=80.0, max_h_pt=20.0)
    p_auth = [
        Paragraph(f"for <b>{escape_xml(comp.get('name') or '')}</b>", make_p(font_size=FS_SMALL, alignment=2)),
    ]
    if sig_img:
        p_auth.append(sig_img)
    else:
        p_auth.append(Spacer(1, 16.0))
    p_auth.append(Paragraph("<b>Approved by / Authorised Signatory</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)))

    p_supp_ack = [
        Paragraph("<b>Supplier Acknowledgement: We accept this order</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_EMERALD)),
        Paragraph("Name: ______________________ &nbsp;&nbsp;&nbsp; Date: ____________", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Signature: __________________ &nbsp;&nbsp;&nbsp; Seal: ____________", make_p(font_size=FS_TINY + 0.5)),
    ]

    t_signs = Table([[p_prep, p_auth, p_supp_ack]], colWidths=[w_prep, w_auth, w_supp])
    t_signs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_EMERALD),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(t_signs)

    # 8. Build Adaptive Items Table Flowables
    table_flowables = build_adaptive_items_table(
        headers=headers,
        item_specs=item_specs,
        col_widths=COLS_PO,
        base_style=table_style,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
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
        desc_col_idx=2,
        grid_color=COLOR_GRID
    )

    story.extend(table_flowables)
    story.extend(footer_elements)
    return story


def render_purchase_order_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Purchase Order to an A4 PDF document with procurement layout."""
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

    story = _build_po_story(data)
    status = str(data.get("status", "")).lower()

    class PONumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "cancelled":
                draw_watermark_stamp(self, "CANCELLED", color_hex="#DC2626")
            elif status == "received":
                draw_watermark_stamp(self, "FULLY RECEIVED", color_hex="#16A34A")
            elif status == "partially_received":
                draw_watermark_stamp(self, "PARTIALLY RECEIVED", color_hex="#D97706")

    doc.build(story, canvasmaker=PONumberedCanvas)
    return output_path
