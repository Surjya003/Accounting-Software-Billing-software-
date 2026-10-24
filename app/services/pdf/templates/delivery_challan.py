"""
BillFlow Suite - Delivery Challan Template (Industrial Dispatch Architecture)
=============================================================================
Statutory Compliance: Rule 55 of the CGST Rules, 2017 (Dispatch / Transport Document).
Design Features:
- Triplicate copy indicator (Original for Consignee / Duplicate for Transporter / Triplicate for Consignor)
- Standardized 'Reason for Transportation' checkbox selection matrix
- Comprehensive Logistics & Vehicle tracking grid (Vehicle, Driver, LR/GR, E-Way Bill, From/To, Distance)
- Quantity Ordered vs. Quantity Dispatched with Package Count, Weight, and Line Remarks
- Price-free by default (rate and valuation suppressed unless show_value flag is True)
- Triple sign-off: Prepared by, Authorized Signatory, and Receiver's Acknowledgement with condition receipt

Stamps: RETURNABLE (Job work / Approval), CONVERTED (Invoice reference).
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

COLOR_STEEL = colors.HexColor("#1B4F72")        # Logistics Steel Blue
COLOR_BG_LIGHT = colors.HexColor("#F4F8FA")     # Ice Mist
COLOR_GRID = colors.HexColor("#94A3B8")         # Slate 400
COLOR_BORDER = colors.HexColor("#475569")       # Slate 600
COLOR_TEXT = colors.HexColor("#0F172A")         # Slate 900

# Font sizes
FS_TITLE = 13.5
FS_COPY_LABEL = 7.5
FS_SECTION = 8.0
FS_BODY = 7.0
FS_SMALL = 6.2
FS_TINY = 5.6

# Rule 55(1) Column Configurations:
# A. Supply movement (Rule 55(1)(d) & (e)): Sl(20), Desc(130.58), HSN(42), Qty(36), Unit(26), TaxableVal(64), TaxRate(36), TaxAmt(54), TotalVal(65), Remarks(65) = 538.58 pt
COLS_SUPPLY = [20.0, 130.58, 42.0, 36.0, 26.0, 64.0, 36.0, 54.0, 65.0, 65.0]

# B. Non-supply movement with statutory taxable value (Rule 55(1)(d)): Sl(22), Desc(168.58), HSN(44), Qty(42), Unit(28), Rate(44), Pkg/Wt(44), TaxableVal(76), Remarks(70) = 538.58 pt
COLS_NON_SUPPLY = [22.0, 168.58, 44.0, 42.0, 28.0, 44.0, 44.0, 76.0, 70.0]

# C. Price-Free Columns (Strictly for permitted exempt movements): Sl(24), Desc(182.58), HSN(46), QtyOrd(46), QtyDisp(46), Unit(30), Pkg(40), Wt(44), Remarks(80) = 538.58 pt
COLS_PRICE_FREE = [24.0, 182.58, 46.0, 46.0, 46.0, 30.0, 40.0, 44.0, 80.0]
COLS_VALUED = COLS_NON_SUPPLY

TRANSPORT_REASONS = [
    "Supply on Approval",
    "Job Work",
    "Delivery (invoice to follow)",
    "Branch/Stock Transfer",
    "Return/Replacement",
    "Exhibition/Sales Promotion",
    "Others"
]


def _build_challan_story(data: Dict[str, Any], copy_label: str = "ORIGINAL FOR CONSIGNEE") -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or {}
    ship = data.get("shipping", {}) or cust
    logistics = data.get("logistics", {}) or {}

    ch_num = escape_xml(data.get("challan_number") or data.get("invoice_number", "DC-DRAFT"))
    ch_date = format_date_ddmmyyyy(data.get("challan_date") or data.get("date"))
    disp_time = escape_xml(data.get("dispatch_datetime") or "-")
    po_ref = escape_xml(data.get("po_number") or data.get("buyers_order_no") or "-")
    po_date = format_date_ddmmyyyy(data.get("buyers_order_date") or data.get("po_date")) or "-"

    curr_reason = (data.get("reason_for_transportation") or "Delivery (invoice to follow)").strip()
    is_price_free = bool(data.get("is_price_free", False))
    # Rule 55(1) requires taxable value on EVERY challan. Price-free is only for explicit exempt movements.
    show_value = not is_price_free
    is_supply = bool(
        data.get("is_supply") or
        any(s in curr_reason.lower() for s in ["supply", "approval", "invoice to follow", "sale"])
    )

    # 1. Header Bar: Centered "DELIVERY CHALLAN" + Copy label & Rule 55 citation
    title_table_data = [
        [
            Paragraph(f"<b>DELIVERY CHALLAN</b><br/><font size=6.5 color='#475569'>Issued under Rule 55 of the CGST Rules, 2017 &bull; NOT FOR SALE</font>", make_p(font_size=FS_TITLE, bold=True, color=COLOR_STEEL, alignment=0)),
            Paragraph(f"<b>({copy_label})</b><br/><font size=6.5 color='#475569'>Triplicate Dispatch Copy</font>", make_p(font_size=FS_COPY_LABEL + 0.5, bold=True, alignment=2))
        ]
    ]
    t_title = Table(title_table_data, colWidths=[FRAME_WIDTH_PT - 180.0, 180.0])
    t_title.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, COLOR_STEEL),
    ]))
    story.append(t_title)
    story.append(Spacer(1, 3))

    # 2. Reason for Transportation Checkbox Matrix
    reason_spans = []
    for r in TRANSPORT_REASONS:
        mark = "[X]" if curr_reason.lower() in r.lower() else "[ &nbsp; ]"
        reason_spans.append(f"<b>{mark}</b> {r}")

    reason_line1 = " &nbsp;&nbsp;&nbsp;&nbsp; ".join(reason_spans[:4])
    reason_line2 = " &nbsp;&nbsp;&nbsp;&nbsp; ".join(reason_spans[4:])
    p_reason = Paragraph(
        f"<b>Reason for Transportation:</b><br/>{reason_line1}<br/>{reason_line2}",
        make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5)
    )
    t_reason = Table([[p_reason]], colWidths=[FRAME_WIDTH_PT])
    t_reason.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_reason)
    story.append(Spacer(1, 3))

    # 3. Parties Block (Consignor vs Consignee & Bill To)
    half_w = FRAME_WIDTH_PT / 2.0

    consignor_p = Paragraph(
        f"<b>Consignor (Dispatched From):</b><br/>"
        f"<b>{escape_xml(comp.get('name', 'Company'))}</b><br/>"
        f"{escape_xml(comp.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(comp.get('gstin', 'N/A'))}</b> | State: {escape_xml(comp.get('state', ''))}",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    consignee_name = ship.get('name') or cust.get('name', '')
    consignee_addr = ship.get('address') or cust.get('address', '')
    bill_to_name = cust.get('name', '')
    is_diff_bill = bill_to_name and (bill_to_name.strip().lower() != consignee_name.strip().lower())

    consignee_lines = [
        f"<b>Consignee (Ship To):</b><br/>"
        f"<b>{escape_xml(consignee_name)}</b><br/>"
        f"{escape_xml(consignee_addr)}<br/>"
        f"GSTIN: <b>{escape_xml(ship.get('gstin') or cust.get('gstin', 'N/A'))}</b> | PIN: {escape_xml(ship.get('pincode') or cust.get('pincode', ''))}"
    ]
    if is_diff_bill:
        consignee_lines.append(f"<font color='#475569'><b>Bill To (if different):</b> {escape_xml(bill_to_name)} (GSTIN: {escape_xml(cust.get('gstin', ''))})</font>")

    p_consignee = Paragraph("<br/>".join(consignee_lines), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5))

    parties_table = Table([[consignor_p, p_consignee]], colWidths=[half_w, half_w])
    parties_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 3))

    # 4. Transport & Vehicle Tracking Grid (2 Rows x 4 Cols)
    t_name = escape_xml(data.get("transporter_name") or logistics.get("dispatched_through") or logistics.get("transporter_name") or "-")
    t_id = escape_xml(data.get("transporter_id") or logistics.get("transporter_id") or "-")
    veh_no = escape_xml(data.get("vehicle_no") or data.get("vehicle_number") or logistics.get("vehicle_no") or logistics.get("vehicle_number") or "-")
    driver = escape_xml(data.get("driver_name") or logistics.get("driver_name") or "-")
    d_mob = escape_xml(data.get("driver_mobile") or logistics.get("driver_mobile") or "-")
    driver_str = f"{driver} ({d_mob})" if d_mob != "-" else driver

    lr_no = escape_xml(data.get("lr_no") or logistics.get("dispatch_doc_no") or logistics.get("lr_no") or "-")
    lr_date = format_date_ddmmyyyy(data.get("lr_date") or logistics.get("lr_date")) or "-"
    eway_no = escape_xml(data.get("eway_bill_no") or logistics.get("waybill_no") or logistics.get("eway_bill_no") or "-")
    from_pl = escape_xml(data.get("from_place") or logistics.get("from_place") or comp.get("city") or "-")
    to_pl = escape_xml(data.get("to_place") or logistics.get("destination") or cust.get("city") or "-")
    dist_km = escape_xml(str(data.get("distance_km") or logistics.get("distance_km") or "-"))

    q_col = FRAME_WIDTH_PT / 4.0
    trans_rows = [
        [
            Paragraph(f"Challan No. &amp; Date:<br/><b>{ch_num}</b> | {ch_date}", make_p(font_size=FS_SMALL)),
            Paragraph(f"Dispatch Date/Time:<br/><b>{disp_time}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Transporter Name &amp; ID:<br/><b>{t_name}</b> | {t_id}", make_p(font_size=FS_SMALL)),
            Paragraph(f"Vehicle No.:<br/><b>{veh_no}</b>", make_p(font_size=FS_SMALL)),
        ],
        [
            Paragraph(f"LR / GR No. &amp; Date:<br/><b>{lr_no}</b> | {lr_date}", make_p(font_size=FS_SMALL)),
            Paragraph(f"E-Way Bill No.:<br/><b>{eway_no}</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_STEEL)),
            Paragraph(f"Route (From &rarr; To):<br/><b>{from_pl} &rarr; {to_pl}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Driver / Distance:<br/><b>{driver_str}</b> | {dist_km} km", make_p(font_size=FS_SMALL)),
        ]
    ]
    t_transport = Table(trans_rows, colWidths=[q_col] * 4)
    t_transport.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_STEEL),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_transport)
    story.append(Spacer(1, 3))

    # 5. Items Table (Rule 55(1) Compliance: Always show taxable value; show tax columns if supply)
    tot_disp = 0.0
    tot_ord = 0.0
    tot_pkgs = 0
    tot_wt = 0.0
    tot_val = 0.0
    tot_tax = 0.0
    tot_grand = 0.0

    if show_value and is_supply:
        col_widths = COLS_SUPPLY
        headers = [
            [
                Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Description of Goods</b>", make_p(font_size=FS_BODY, bold=True)),
                Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Qty Disp.</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Taxable Value</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>GST Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Tax Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Total Value</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Remarks</b>", make_p(font_size=FS_BODY, bold=True)),
            ]
        ]
    elif show_value and not is_supply:
        col_widths = COLS_NON_SUPPLY
        headers = [
            [
                Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Description of Goods</b>", make_p(font_size=FS_BODY, bold=True)),
                Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Qty Disp.</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Pkg / Wt</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Taxable Value</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Remarks / Notes</b>", make_p(font_size=FS_BODY, bold=True)),
            ]
        ]
    else:
        col_widths = COLS_PRICE_FREE
        headers = [
            [
                Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Description of Goods</b>", make_p(font_size=FS_BODY, bold=True)),
                Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Qty Ord.</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Qty Disp.</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Packages</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
                Paragraph("<b>Weight</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
                Paragraph("<b>Remarks / Serial Nos</b>", make_p(font_size=FS_BODY, bold=True)),
            ]
        ]

    item_specs: List[List[AdaptiveCell]] = []
    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty_d = float(it.get("quantity") or it.get("qty_dispatched") or 0.0)
        qty_o = float(it.get("qty_ordered") or qty_d)
        tot_disp += qty_d
        tot_ord += qty_o

        unit = escape_xml(it.get("unit") or "Nos")
        pkg = it.get("packages") or 1
        tot_pkgs += int(pkg)
        wt = float(it.get("weight") or 0.0)
        tot_wt += wt
        wt_str = f"{wt:.1f} kg" if wt > 0 else f"{pkg} pk"

        rate = float(it.get("unit_price") or 0.0)
        taxable_val = float(it.get("taxable_value") or (qty_d * rate))
        tax_rate = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        tax_amt = float(it.get("tax_amount") or it.get("total_tax") or round(taxable_val * (tax_rate / 100.0), 2))
        total_item_val = float(it.get("total_amount") or it.get("total_item_amount") or round(taxable_val + tax_amt, 2))

        tot_val += taxable_val
        tot_tax += tax_amt
        tot_grand += total_item_val

        rem = escape_xml(it.get("remarks") or "-")

        if show_value and is_supply:
            item_specs.append([
                AdaptiveCell(str(idx), alignment=1),
                AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
                AdaptiveCell(hsn, alignment=1),
                AdaptiveCell(f"{qty_d:,.2f}", alignment=2),
                AdaptiveCell(unit, alignment=1),
                AdaptiveCell(format_currency(taxable_val, num_fmt), alignment=2),
                AdaptiveCell(f"{tax_rate:.1f}%" if tax_rate > 0 else "0%", alignment=1),
                AdaptiveCell(format_currency(tax_amt, num_fmt), alignment=2),
                AdaptiveCell(format_currency(total_item_val, num_fmt), alignment=2),
                AdaptiveCell(rem, alignment=0, is_small=True),
            ])
        elif show_value and not is_supply:
            item_specs.append([
                AdaptiveCell(str(idx), alignment=1),
                AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
                AdaptiveCell(hsn, alignment=1),
                AdaptiveCell(f"{qty_d:,.2f}", alignment=2),
                AdaptiveCell(unit, alignment=1),
                AdaptiveCell(format_currency(rate, num_fmt), alignment=2),
                AdaptiveCell(wt_str, alignment=1),
                AdaptiveCell(format_currency(taxable_val, num_fmt), alignment=2),
                AdaptiveCell(rem, alignment=0, is_small=True),
            ])
        else:
            item_specs.append([
                AdaptiveCell(str(idx), alignment=1),
                AdaptiveCell(f"<b>{desc}</b>", alignment=0, bold=True),
                AdaptiveCell(hsn, alignment=1),
                AdaptiveCell(f"{qty_o:,.2f}", alignment=2),
                AdaptiveCell(f"<b>{qty_d:,.2f}</b>", alignment=2, bold=True),
                AdaptiveCell(unit, alignment=1),
                AdaptiveCell(str(pkg), alignment=1),
                AdaptiveCell(f"{wt:.1f} kg" if wt > 0 else "-", alignment=2),
                AdaptiveCell(rem, alignment=0, is_small=True),
            ])

    if show_value and is_supply:
        total_row = [
            Paragraph("", make_p()),
            Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_disp:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph(f"<b>Rs. {format_currency(tot_val, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph(f"<b>Rs. {format_currency(tot_tax, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph(f"<b>Rs. {format_currency(tot_grand, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
        ]
    elif show_value and not is_supply:
        total_row = [
            Paragraph("", make_p()),
            Paragraph("<b>Total</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_disp:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph("", make_p()),
            Paragraph(f"<b>Rs. {format_currency(tot_val, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
        ]
    else:
        total_row = [
            Paragraph("", make_p()),
            Paragraph("<b>Total Dispatched</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_ord:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph(f"<b>{tot_disp:,.2f}</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
            Paragraph(f"<b>{tot_pkgs}</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph(f"<b>{tot_wt:.1f} kg</b>" if tot_wt > 0 else "-", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("", make_p()),
        ]

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BG_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_STEEL),
        ('LINEABOVE', (0, -1), (-1, -1), 0.6, COLOR_BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    # 6. Footer Area (Condition Note, Valuation if enabled, Triple Sign-off)
    footer_elements = []

    reason_notes = {
        "Job Work": "Goods sent for job work basis under Rule 55 of the CGST Rules, 2017. To be returned after processing.",
        "Supply on Approval": "Goods sent on approval basis. Subject to acceptance / confirmation. Not for immediate sale.",
        "Branch/Stock Transfer": "Goods transferred between branches / warehouses. No commercial sale involved.",
    }
    printed_note = reason_notes.get(curr_reason, comp.get("notes_challan") or "Goods sent on delivery challan. Not for sale. Tax invoice to follow.")
    
    note_lines = [
        Paragraph(f"<b>Condition / Statutory Note:</b> {printed_note}", make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5))
    ]
    if show_value and tot_val > 0:
        note_lines.append(Paragraph(f"<b>Approximate Value of Goods:</b> Rs. {format_currency(tot_val, num_fmt)} ({amount_to_words_inr(tot_val)})", make_p(font_size=FS_SMALL, bold=True)))

    t_note = Table([[note_lines]], colWidths=[FRAME_WIDTH_PT])
    t_note.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    footer_elements.append(t_note)
    footer_elements.append(Spacer(1, 3))

    # 7. Triple Sign-Off (Prepared By, Authorized Signatory, Receiver's Acknowledgement)
    w_prep = FRAME_WIDTH_PT * 0.22
    w_auth = FRAME_WIDTH_PT * 0.33
    w_recv = FRAME_WIDTH_PT * 0.45

    p_prep = [
        Paragraph("<b>Prepared by:</b>", make_p(font_size=FS_SMALL)),
        Spacer(1, 24.0),
        Paragraph("Store In-charge / Dispatcher", make_p(font_size=FS_TINY)),
    ]

    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=80.0, max_h_pt=24.0)
    p_auth = [
        Paragraph(f"for <b>{escape_xml(comp.get('name', 'Company'))}</b>", make_p(font_size=FS_SMALL, alignment=2)),
    ]
    if sig_img:
        p_auth.append(sig_img)
    else:
        p_auth.append(Spacer(1, 20.0))
    p_auth.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_SMALL, bold=True, alignment=2)))

    p_recv = [
        Paragraph("<b>Receiver's Acknowledgement:</b>", make_p(font_size=FS_SMALL, bold=True, color=COLOR_STEEL)),
        Paragraph("<i>Received the above goods in good order and condition.</i>", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Name: ______________________ &nbsp;&nbsp; Date: ____________", make_p(font_size=FS_TINY + 0.5)),
        Paragraph("Signature: __________________ &nbsp;&nbsp; Seal: ____________", make_p(font_size=FS_TINY + 0.5)),
    ]

    t_signs = Table([[p_prep, p_auth, p_recv]], colWidths=[w_prep, w_auth, w_recv])
    t_signs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_STEEL),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    footer_elements.append(t_signs)

    # 8. Build Adaptive Items Table Flowables
    table_flowables = build_adaptive_items_table(
        headers=headers,
        item_specs=item_specs,
        col_widths=col_widths,
        base_style=table_style,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_BG_LIGHT),
            ('TOPPADDING', (0, -1), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 2.5),
        ],
        flowables_before=list(story),
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


def render_delivery_challan_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Delivery Challan to an A4 PDF document with industrial logistics layout."""
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
        "ORIGINAL FOR CONSIGNEE",
        "DUPLICATE FOR TRANSPORTER",
        "TRIPLICATE FOR CONSIGNOR"
    ] if print_all else [data.get("copy_label", "ORIGINAL FOR CONSIGNEE")]

    full_story = []
    for idx, c_label in enumerate(copies):
        if idx > 0:
            full_story.append(PageBreak())
        c_story = _build_challan_story(data, copy_label=c_label)
        full_story.extend(c_story)

    reason = str(data.get("reason_for_transportation", "")).lower()
    linked_inv = data.get("linked_invoice_reference")

    class ChallanNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if linked_inv:
                draw_watermark_stamp(self, f"CONVERTED: {linked_inv}", color_hex="#16A34A")
            elif "job work" in reason or "approval" in reason:
                draw_watermark_stamp(self, "RETURNABLE", color_hex="#0284C7")

    doc.build(full_story, canvasmaker=ChallanNumberedCanvas)
    return output_path
