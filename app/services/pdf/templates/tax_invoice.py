"""
BillFlow Suite - Tax Invoice Template (Reference Baseline)
===========================================================
Replication of the reference document docs/reference/12-signed.pdf with all 5 flaws fixed:
1. Seller State Name and Code always filled (derived from GSTIN or state profile).
2. Dates strictly DD-MM-YYYY format.
3. Amount in words strictly formatted as "Rupees ... Only" (with paise).
4. Seal and signature positioned safely in dedicated free space without covering text.
5. Continuous vertical column grid lines stretching to the footer (no 15% bottom blank band).

Statutory Compliance: Rule 46 of the CGST Rules, 2017.
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
    format_currency, format_date_ddmmyyyy, amount_to_words_inr, sanitize_number_format
)
from app.services.pdf.core.images import load_safe_image
from app.services.pdf.core.fonts import register_unicode_fonts, sanitize_rupee_text
from app.services.pdf.core.text import make_p, escape_xml
from app.services.pdf.core.stamps import draw_watermark_stamp

logger = logging.getLogger(__name__)

# --- NAMED GEOMETRY & STYLING CONSTANTS (mm & pt) ---
MARGIN_MM = 10.0
MARGIN_PT = MARGIN_MM * mm
FRAME_WIDTH_PT = FRAME_WIDTH
COLOR_BLACK = colors.HexColor("#000000")
COLOR_GRID = colors.HexColor("#000000")
COLOR_LIGHT_GRAY = colors.HexColor("#F1F5F9")
COLOR_TEXT_MUTED = colors.HexColor("#334155")

# Font sizes
FS_DOC_TITLE = 11.5
FS_COPY_LABEL = 8.0
FS_SECTION_TITLE = 8.0
FS_BODY = 7.2
FS_SMALL = 6.5
FS_TINY = 5.8

# Column widths for Items Table (Total must equal FRAME_WIDTH_PT = ~538.58 pt)
# Inter-state (IGST): Sl(26), Desc(210.58), HSN(54), Qty(48), Rate(54), Per(28), IGST(52), Amount(66) = 538.58
COLS_INTERSTATE = [26.0, 210.58, 54.0, 48.0, 54.0, 28.0, 52.0, 66.0]

# Intra-state (CGST + SGST): Sl(26), Desc(182.58), HSN(50), Qty(46), Rate(50), Per(26), CGST(46), SGST(46), Amount(66) = 538.58
COLS_INTRASTATE = [26.0, 182.58, 50.0, 46.0, 50.0, 26.0, 46.0, 46.0, 66.0]

GST_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
    "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
    "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory"
}

def derive_state_and_code(gstin: str, state_name: str = "", state_code: str = "") -> tuple:
    """Safely extracts or derives state name and 2-digit code."""
    c_code = (state_code or "").strip()
    s_name = (state_name or "").strip()
    if gstin and len(gstin.strip()) >= 2 and gstin.strip()[:2].isdigit():
        derived_code = gstin.strip()[:2]
        if not c_code:
            c_code = derived_code
        if not s_name:
            s_name = GST_STATE_CODES.get(derived_code, s_name)
    if c_code and not s_name:
        s_name = GST_STATE_CODES.get(c_code, "")
    return s_name, c_code


def _build_tax_invoice_story(data: Dict[str, Any], copy_label: str = "ORIGINAL FOR RECIPIENT") -> List[Any]:
    """Constructs the story elements for one copy of the Tax Invoice."""
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or {}
    ship = data.get("shipping", {}) or cust
    logistics = data.get("logistics", {}) or {}
    totals = data.get("totals", {}) or {}

    # State extraction & derivation (Fix for reference flaw: State Name blank)
    seller_state, seller_code = derive_state_and_code(comp.get("gstin", ""), comp.get("state", ""), comp.get("state_code", ""))
    buyer_state, buyer_code = derive_state_and_code(cust.get("gstin", ""), cust.get("state", ""), cust.get("state_code", ""))
    ship_state, ship_code = derive_state_and_code(ship.get("gstin", cust.get("gstin", "")), ship.get("state", buyer_state), ship.get("state_code", buyer_code))

    is_interstate = (
        data.get("tax_mode") == "inter_state"
        or float(totals.get("igst_amount") or totals.get("igst_total") or 0.0) > 0.0
    )

    # 1. Document Title Bar: Centered "TAX INVOICE" + Right copy label
    title_table_data = [
        [
            Paragraph(f"<b>TAX INVOICE</b> <font size='7' color='#475569'>[Rule 46 CGST]</font>", make_p(font_size=FS_DOC_TITLE, bold=True, alignment=1)),
            Paragraph(f"<b>({copy_label})</b>", make_p(font_size=FS_COPY_LABEL, bold=True, alignment=2))
        ]
    ]
    t_title = Table(title_table_data, colWidths=[FRAME_WIDTH_PT - 160.0, 160.0])
    t_title.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, COLOR_GRID),
    ]))
    story.append(t_title)

    # 2. Header Grid (Left Column: Seller, Consignee, Buyer; Right Column: 7-Row Reference Grid)
    half_w = FRAME_WIDTH_PT / 2.0  # 269.29 pt each

    # Seller Block
    seller_lines = [
        f"<b>{escape_xml(comp.get('name') or '')}</b>",
        escape_xml(comp.get('address', '')),
        f"GSTIN/UIN: <b>{escape_xml(comp.get('gstin') or 'Unregistered')}</b>",
        f"State Name : <b>{escape_xml(seller_state)}</b>, Code : <b>{escape_xml(seller_code or '-')}</b>",
    ]
    if comp.get('phone') or comp.get('email'):
        seller_lines.append(f"Contact: {escape_xml(comp.get('phone', ''))} | E-Mail: {escape_xml(comp.get('email', ''))}")
    p_seller = Paragraph("<br/>".join([l for l in seller_lines if l]), make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    # Consignee (Ship to)
    consignee_name = ship.get('name') or cust.get('name', '')
    consignee_addr = ship.get('address') or cust.get('address', '')
    consignee_lines = [
        f"<b>Consignee (Ship to)</b>",
        f"<b>{escape_xml(consignee_name)}</b>",
        escape_xml(consignee_addr),
        f"GSTIN/UIN : <b>{escape_xml(ship.get('gstin') or cust.get('gstin', 'N/A'))}</b>",
        f"State Name : <b>{escape_xml(ship_state)}</b>, Code : <b>{escape_xml(ship_code or '-')}</b>",
    ]
    p_consignee = Paragraph("<br/>".join([l for l in consignee_lines if l]), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    # Buyer (Bill to)
    buyer_lines = [
        f"<b>Buyer (Bill to)</b>",
        f"<b>{escape_xml(cust.get('name', ''))}</b>",
        escape_xml(cust.get('address', '')),
        f"GSTIN/UIN : <b>{escape_xml(cust.get('gstin', 'N/A'))}</b>",
        f"State Name : <b>{escape_xml(buyer_state)}</b>, Code : <b>{escape_xml(buyer_code or '-')}</b>",
    ]
    p_buyer = Paragraph("<br/>".join([l for l in buyer_lines if l]), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    left_box_data = [
        [p_seller],
        [p_consignee],
        [p_buyer],
    ]
    t_left = Table(left_box_data, colWidths=[half_w])
    t_left.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (0, 0), 0.6, COLOR_GRID),
        ('LINEBELOW', (0, 1), (0, 1), 0.6, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Right Column: The 7-row reference grid exactly matching reference
    q_half = half_w / 2.0  # 134.64 pt each
    inv_date_str = format_date_ddmmyyyy(data.get("date") or data.get("invoice_date"))
    po_date_str = format_date_ddmmyyyy(data.get("buyers_order_date") or logistics.get("buyer_order_date") or data.get("po_date"))

    inv_num = escape_xml(data.get("invoice_number", "DRAFT"))
    eway_num = escape_xml(data.get("eway_bill_no") or logistics.get("waybill_no") or "-")
    del_note = escape_xml(data.get("delivery_note") or logistics.get("delivery_note") or "-")
    mode_terms = escape_xml(data.get("mode_terms_of_payment") or logistics.get("payment_terms") or data.get("payment_mode") or "-")
    ref_no_date = escape_xml(data.get("reference_no_date") or data.get("reference_number") or logistics.get("reference_no_date") or "-")
    other_ref = escape_xml(data.get("other_references") or logistics.get("other_references") or "-")
    buyer_order_no = escape_xml(data.get("buyers_order_no") or logistics.get("buyer_order_no") or data.get("po_number") or "-")
    dispatch_doc_no = escape_xml(data.get("dispatch_doc_no") or logistics.get("dispatch_doc_no") or "-")
    dispatched_through = escape_xml(data.get("dispatched_through") or logistics.get("dispatched_through") or "-")
    destination = escape_xml(data.get("destination") or logistics.get("destination") or "-")
    terms_delivery_raw = data.get("terms_of_delivery") or logistics.get("terms_delivery") or data.get("terms_delivery") or "-"
    terms_delivery = escape_xml(terms_delivery_raw).replace("\n", "<br/>")

    row1_left = Paragraph(f"Invoice No.<br/><b>{inv_num}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row1_right = Paragraph(f"Dated<br/><b>{inv_date_str}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row2_left = Paragraph(f"Delivery Note<br/><b>{del_note}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row2_right = Paragraph(f"Mode/Terms of Payment<br/><b>{mode_terms}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row3_left = Paragraph(f"Reference No. &amp; Date.<br/><b>{ref_no_date}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row3_right = Paragraph(f"Other References<br/><b>{other_ref}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row4_left = Paragraph(f"Buyer's Order No.<br/><b>{buyer_order_no}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row4_right = Paragraph(f"Dated<br/><b>{po_date_str or '-'}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row5_left = Paragraph(f"Dispatch Doc No.<br/><b>{dispatch_doc_no}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row5_right = Paragraph(f"Waybill / E-Way Bill No.<br/><b>{eway_num}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row6_left = Paragraph(f"Dispatched through<br/><b>{dispatched_through}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))
    row6_right = Paragraph(f"Destination<br/><b>{destination}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    row7_full = Paragraph(f"Terms of Delivery<br/>{terms_delivery}", make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    right_grid_data = [
        [row1_left, row1_right],
        [row2_left, row2_right],
        [row3_left, row3_right],
        [row4_left, row4_right],
        [row5_left, row5_right],
        [row6_left, row6_right],
        [row7_full, ""],
    ]
    t_right = Table(right_grid_data, colWidths=[q_half, q_half])
    t_right.setStyle(TableStyle([
        ('SPAN', (0, 6), (1, 6)),
        ('INNERGRID', (0, 0), (-1, 5), 0.6, COLOR_GRID),
        ('LINEBELOW', (0, 5), (1, 5), 0.6, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Combined Top Box
    top_box_table = Table([[t_left, t_right]], colWidths=[half_w, half_w])
    top_box_table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.8, COLOR_GRID),
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(top_box_table)

    # 3. Items Table
    col_widths = COLS_INTERSTATE if is_interstate else COLS_INTRASTATE
    if is_interstate:
        headers = [
            [
                Paragraph("<b>Sl No.</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Description of Goods</b>", make_p(font_size=FS_BODY, bold=True, alignment=0)),
                Paragraph("<b>HSN/SAC</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Quantity</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>per</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>IGST %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            ]
        ]
    else:
        headers = [
            [
                Paragraph("<b>Sl No.</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Description of Goods</b>", make_p(font_size=FS_BODY, bold=True, alignment=0)),
                Paragraph("<b>HSN/SAC</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Quantity</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>per</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>CGST %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>SGST %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            ]
        ]

    item_specs: List[List[AdaptiveCell]] = []
    tot_qty = 0.0
    tot_amt = 0.0
    hsn_summary_map = {}

    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Item")
        hsn = escape_xml(str(it.get("hsn_code") or it.get("hsn_sac") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        unit = escape_xml(it.get("unit") or "Nos")
        rate = float(it.get("unit_price") or it.get("rate") or 0.0)
        tax_rate = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        amt = float(it.get("total_item_amount") or it.get("amount") or (qty * rate))
        tot_amt += amt

        # Track HSN summary
        taxable_item = qty * rate * (1.0 - (float(it.get("discount_pct", 0.0)) / 100.0))
        if hsn not in hsn_summary_map:
            hsn_summary_map[hsn] = {"taxable": 0.0, "rate": tax_rate, "tax": 0.0}
        hsn_summary_map[hsn]["taxable"] += taxable_item
        hsn_summary_map[hsn]["tax"] += taxable_item * (tax_rate / 100.0)

        rate_str = format_currency(rate, num_fmt)
        amt_str = format_currency(amt, num_fmt)

        if is_interstate:
            item_specs.append([
                AdaptiveCell(str(idx), alignment=1),
                AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
                AdaptiveCell(hsn, alignment=1),
                AdaptiveCell(f"{qty:,.2f}", alignment=2),
                AdaptiveCell(rate_str, alignment=2),
                AdaptiveCell(unit, alignment=1),
                AdaptiveCell(f"{tax_rate:.1f} %", alignment=2),
                AdaptiveCell(amt_str, alignment=2),
            ])
        else:
            half_tax = tax_rate / 2.0
            item_specs.append([
                AdaptiveCell(str(idx), alignment=1),
                AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
                AdaptiveCell(hsn, alignment=1),
                AdaptiveCell(f"{qty:,.2f}", alignment=2),
                AdaptiveCell(rate_str, alignment=2),
                AdaptiveCell(unit, alignment=1),
                AdaptiveCell(f"{half_tax:.1f} %", alignment=2),
                AdaptiveCell(f"{half_tax:.1f} %", alignment=2),
                AdaptiveCell(amt_str, alignment=2),
            ])

    # Total row of table with matched quantity unit (or plain total if units differ)
    tot_qty_str = format_total_quantity(data.get("items", []), tot_qty)
    if is_interstate:
        total_row = [
            Paragraph("", make_p()),
            Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True, alignment=0)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_qty_str}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph(f"<b>Rs. {format_currency(tot_amt, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]
    else:
        total_row = [
            Paragraph("", make_p()),
            Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True, alignment=0)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_qty_str}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph(f"<b>Rs. {format_currency(tot_amt, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]

    table_style = [
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_GRID),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_GRID),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    # 4. Summary & Footer Area
    grand_total = float(totals.get("grand_total") or totals.get("total_amount") or tot_amt)
    taxable_val = float(totals.get("taxable_amount") or totals.get("subtotal") or 0.0)
    cgst_val = float(totals.get("cgst_amount") or totals.get("cgst_total") or 0.0)
    sgst_val = float(totals.get("sgst_amount") or totals.get("sgst_total") or 0.0)
    igst_val = float(totals.get("igst_amount") or totals.get("igst_total") or 0.0)
    round_off = float(totals.get("round_off") or 0.0)

    # Amount in words (Fix reference flaw: Missing "Rupees")
    amt_words = amount_to_words_inr(grand_total)

    footer_elements = []

    # Amount chargeable in words bar
    words_table_data = [
        [
            Paragraph(f"Amount Chargeable (in words)<br/><b>{amt_words}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3)),
            Paragraph("<i>E. &amp; O.E</i>", make_p(font_size=FS_SMALL, alignment=2))
        ]
    ]
    t_words = Table(words_table_data, colWidths=[FRAME_WIDTH_PT - 70.0, 70.0])
    t_words.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(t_words)

    # Tax breakdown / HSN Summary (if Setting enabled or multiple HSNs)
    print_hsn = comp.get("print_hsn_summary", True)
    if print_hsn and len(hsn_summary_map) > 0:
        hsn_headers = [
            Paragraph("<b>HSN/SAC</b>", make_p(font_size=FS_SMALL, bold=True, alignment=1)),
            Paragraph("<b>Taxable Value</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
        ]
        if is_interstate:
            hsn_headers.extend([
                Paragraph("<b>Integrated Tax (Rate, Amt)</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
                Paragraph("<b>Total Tax Amount</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
            ])
            hsn_cols = [100.0, 138.58, 160.0, 140.0]
        else:
            hsn_headers.extend([
                Paragraph("<b>Central Tax (Rate, Amt)</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
                Paragraph("<b>State Tax (Rate, Amt)</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
                Paragraph("<b>Total Tax Amount</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)),
            ])
            hsn_cols = [80.0, 118.58, 120.0, 120.0, 100.0]

        hsn_rows = [hsn_headers]
        for h_code, h_data in hsn_summary_map.items():
            t_val_str = format_currency(h_data["taxable"], num_fmt)
            t_amt_str = format_currency(h_data["tax"], num_fmt)
            if is_interstate:
                hsn_rows.append([
                    Paragraph(h_code, make_p(font_size=FS_SMALL, alignment=1)),
                    Paragraph(t_val_str, make_p(font_size=FS_SMALL, alignment=2)),
                    Paragraph(f"{h_data['rate']:.1f}% : {t_amt_str}", make_p(font_size=FS_SMALL, alignment=2)),
                    Paragraph(t_amt_str, make_p(font_size=FS_SMALL, alignment=2)),
                ])
            else:
                half_t = h_data["tax"] / 2.0
                half_r = h_data["rate"] / 2.0
                hsn_rows.append([
                    Paragraph(h_code, make_p(font_size=FS_SMALL, alignment=1)),
                    Paragraph(t_val_str, make_p(font_size=FS_SMALL, alignment=2)),
                    Paragraph(f"{half_r:.1f}% : {format_currency(half_t, num_fmt)}", make_p(font_size=FS_SMALL, alignment=2)),
                    Paragraph(f"{half_r:.1f}% : {format_currency(half_t, num_fmt)}", make_p(font_size=FS_SMALL, alignment=2)),
                    Paragraph(t_amt_str, make_p(font_size=FS_SMALL, alignment=2)),
                ])
        t_hsn = Table(hsn_rows, colWidths=hsn_cols)
        t_hsn.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_GRID),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]))
        footer_elements.append(t_hsn)

    # Bank Details & Declaration (Left) vs Signatory (Right)
    b_name = escape_xml(comp.get("bank_name") or "-")
    b_ac = escape_xml(comp.get("bank_account_no") or comp.get("account_no") or "-")
    b_ifsc = escape_xml(comp.get("bank_ifsc") or comp.get("ifsc") or "-")
    b_branch = escape_xml(comp.get("bank_branch") or "-")

    declaration_text = comp.get("declaration") or "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct."
    pos_state = data.get("place_of_supply") or buyer_state or "-"
    rev_charge = "Yes" if data.get("reverse_charge") else "No"

    bank_decl_content = [
        f"<b>Company's Bank Details</b>",
        f"Bank Name : <b>{b_name}</b>",
        f"A/c No. : <b>{b_ac}</b>",
        f"Branch &amp; IFS : <b>{b_branch} &amp; {b_ifsc}</b>",
        f"Place of Supply: <b>{escape_xml(pos_state)}</b> | Reverse Charge: <b>{rev_charge}</b>",
        f"<br/><b>Declaration:</b><br/>{escape_xml(declaration_text)}"
    ]
    p_bank_decl = Paragraph("<br/>".join(bank_decl_content), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    # Right cell: for <Company>, safe seal/signature image, Authorised Signatory
    sign_lines = [
        Paragraph(f"for <b>{escape_xml(comp.get('name') or '')}</b>", make_p(font_size=FS_BODY, alignment=2)),
    ]

    # Load signature & seal safely in dedicated space
    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=100.0, max_h_pt=35.0)
    seal_img = load_safe_image(comp.get("seal_path"), max_w_pt=60.0, max_h_pt=35.0)

    if sig_img or seal_img:
        sig_seal_row = []
        if seal_img:
            sig_seal_row.append(seal_img)
        if sig_img:
            sig_seal_row.append(sig_img)
        sig_table = Table([sig_seal_row], colWidths=[half_w / float(len(sig_seal_row))] * len(sig_seal_row))
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        sign_lines.append(sig_table)
    else:
        sign_lines.append(Spacer(1, 30.0))

    sign_lines.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)))

    bottom_box_table = Table([[p_bank_decl, sign_lines]], colWidths=[half_w, half_w])
    bottom_box_table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(bottom_box_table)

    # 5. Build Adaptive Items Table Flowables
    table_flowables = build_adaptive_items_table(
        headers=headers,
        item_specs=item_specs,
        col_widths=col_widths,
        base_style=table_style,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_GRID),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_GRID),
            ('TOPPADDING', (0, -1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 3),
        ],
        flowables_before=[t_title, top_box_table],
        flowables_after=footer_elements,
        company_settings=comp,
        available_width=FRAME_WIDTH_PT,
        available_height=FRAME_HEIGHT,
        fallback_font_size=FS_BODY,
        fallback_padding=2.5,
        desc_col_idx=1,
        grid_color=COLOR_GRID
    )

    story.extend(table_flowables)
    story.extend(footer_elements)
    return story


def render_tax_invoice_pdf(data: Dict[str, Any], output_path: str) -> str:
    """
    Renders the Tax Invoice to an A4 PDF document matching the reference layout.
    Supports single or triplicate print options via Settings (print_all_copies).
    """
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

    print_all = data.get("company", {}).get("print_all_copies", False) or data.get("print_all_copies", False)
    copies = [
        "ORIGINAL FOR RECIPIENT",
        "DUPLICATE FOR TRANSPORTER",
        "TRIPLICATE FOR SUPPLIER"
    ] if print_all else [data.get("copy_label", "ORIGINAL FOR RECIPIENT")]

    full_story = []
    for idx, c_label in enumerate(copies):
        if idx > 0:
            full_story.append(PageBreak())
        c_story = _build_tax_invoice_story(data, copy_label=c_label)
        full_story.extend(c_story)

    # Set custom bottom note on canvas
    class TaxInvoiceNumberedCanvas(NumberedCanvas):
        _bottom_document_note = "This is a Computer Generated Invoice"

    doc.build(full_story, canvasmaker=TaxInvoiceNumberedCanvas)
    return output_path
