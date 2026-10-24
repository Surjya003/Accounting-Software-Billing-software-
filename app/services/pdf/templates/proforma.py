"""
BillFlow Suite - Proforma Invoice Template (Payment-Request Architecture)
========================================================================
Design Features:
- Executive Slate & Sapphire corporate styling
- Prominent 'Payment Request' callout with large payable amount and due date
- Integrated 'How to Pay' box featuring Bank details, UPI ID, and high-res UPI QR code
- Advance received and Balance Payable financial reconciliation
- Full A4 page fill with continuous column lines through dynamic filler rows

Statutory Note: "This is not a tax invoice. Not valid for input tax credit."
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
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget

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

# Color Palette: Slate & Sapphire Blue
COLOR_ACCENT = colors.HexColor("#1E3A8A")       # Sapphire Deep Blue
COLOR_ACCENT_BG = colors.HexColor("#EFF6FF")    # Ice Blue 50
COLOR_BORDER = colors.HexColor("#93C5FD")       # Light Blue 300
COLOR_GRID = colors.HexColor("#CBD5E1")         # Slate 300
COLOR_DARK = colors.HexColor("#0F172A")         # Slate 900
COLOR_MUTED = colors.HexColor("#475569")        # Slate 600

# Font sizes
FS_DOC_TITLE = 15.0
FS_SUBTITLE = 7.5
FS_SECTION_TITLE = 8.5
FS_BODY = 7.2
FS_SMALL = 6.5
FS_HERO_NUM = 12.0

# 9 Items Columns: Sl(24), Desc(174.58), HSN(46), Qty(44), Unit(30), Rate(50), Disc(36), Tax%(44), Amt(66) = 538.58 pt
COLS_PROFORMA = [24.0, 174.58, 46.0, 44.0, 30.0, 50.0, 36.0, 44.0, 66.0]


def _build_proforma_story(data: Dict[str, Any]) -> List[Any]:
    story = []
    num_fmt = data.get("company", {}).get("number_format", "Indian")

    comp = data.get("company", {}) or {}
    cust = data.get("customer", {}) or {}
    ship = data.get("shipping", {}) or cust
    totals = data.get("totals", {}) or {}

    pf_num = escape_xml(data.get("invoice_number") or data.get("proforma_number", "PF-DRAFT"))
    pf_date_str = format_date_ddmmyyyy(data.get("date") or data.get("proforma_date"))
    valid_until_str = format_date_ddmmyyyy(data.get("valid_until"))
    pay_by_str = valid_until_str or pf_date_str

    grand_total = float(totals.get("grand_total") or totals.get("total_amount") or 0.0)
    adv_percent = float(data.get("advance_percent") or 0.0)
    adv_received = float(data.get("advance_received") or 0.0)
    balance_payable = max(grand_total - adv_received, 0.0)

    # 1. Header: Left Title + Right Payment Request Highlight Box
    half_w = FRAME_WIDTH_PT / 2.0  # ~269.29 pt

    left_header = [
        Paragraph("<b>PROFORMA INVOICE</b>", make_p(font_size=FS_DOC_TITLE, bold=True, color=COLOR_ACCENT, leading=FS_DOC_TITLE + 2)),
        Paragraph("<i>This is not a tax invoice. Not valid for input tax credit.</i>", make_p(font_size=FS_SUBTITLE, color=COLOR_MUTED, leading=FS_SUBTITLE + 3)),
        Spacer(1, 4),
        Paragraph(f"<b>{escape_xml(comp.get('name', 'Company Name'))}</b>", make_p(font_size=FS_BODY + 1, bold=True)),
        Paragraph(escape_xml(comp.get('address', '')), make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)),
        Paragraph(f"GSTIN: <b>{escape_xml(comp.get('gstin', 'N/A'))}</b> | PAN: <b>{escape_xml(comp.get('pan', 'N/A'))}</b>", make_p(font_size=FS_BODY)),
        Paragraph(f"State: <b>{escape_xml(comp.get('state', ''))}</b> (Code: {escape_xml(comp.get('state_code', '-'))})", make_p(font_size=FS_BODY)),
    ]

    # Right Box: "Payment Request"
    req_box_rows = [
        [Paragraph("<b>Payment Request</b>", make_p(font_size=FS_SECTION_TITLE, bold=True, color=COLOR_ACCENT)), Paragraph(f"<b>{pf_num}</b>", make_p(font_size=FS_SECTION_TITLE, bold=True, alignment=2))],
        [Paragraph("Date Issued:", make_p(font_size=FS_BODY)), Paragraph(f"<b>{pf_date_str}</b>", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("Valid Until:", make_p(font_size=FS_BODY)), Paragraph(f"<b>{valid_until_str or '-'}</b>", make_p(font_size=FS_BODY, alignment=2))],
        [Paragraph("Pay By Date:", make_p(font_size=FS_BODY)), Paragraph(f"<b>{pay_by_str}</b>", make_p(font_size=FS_BODY, alignment=2))],
    ]
    if adv_percent > 0:
        req_box_rows.append([
            Paragraph("Advance Required:", make_p(font_size=FS_BODY)),
            Paragraph(f"<b>{adv_percent:.1f}%</b>", make_p(font_size=FS_BODY, alignment=2))
        ])

    req_box_rows.append([
        Paragraph("<b>Amount Payable:</b>", make_p(font_size=FS_HERO_NUM - 2, bold=True, color=COLOR_ACCENT)),
        Paragraph(f"<b>Rs. {format_currency(balance_payable, num_fmt)}</b>", make_p(font_size=FS_HERO_NUM, bold=True, color=COLOR_ACCENT, alignment=2))
    ])

    t_req = Table(req_box_rows, colWidths=[half_w * 0.45, half_w * 0.55])
    t_req.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_ACCENT_BG),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
        ('LINEABOVE', (0, -1), (-1, -1), 1, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    header_table = Table([[left_header, t_req]], colWidths=[half_w - 6.0, half_w + 6.0])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # 2. Prominent "How to pay" Box (Bank Details + UPI ID + pure-Python UPI QR code)
    b_name = escape_xml(comp.get("bank_name") or "-")
    b_ac = escape_xml(comp.get("bank_account_no") or comp.get("account_no") or "-")
    b_ifsc = escape_xml(comp.get("bank_ifsc") or comp.get("ifsc") or "-")
    b_branch = escape_xml(comp.get("bank_branch") or "-")
    upi_id = (comp.get("upi_id") or "").strip()

    bank_details_p = Paragraph(
        f"<b>How to pay</b> (Direct Bank Transfer / NEFT / RTGS / IMPS):<br/>"
        f"Bank Name: <b>{b_name}</b> | Account No.: <b>{b_ac}</b><br/>"
        f"IFSC Code: <b>{b_ifsc}</b> | Branch: <b>{b_branch}</b>"
        + (f"<br/>UPI ID: <b>{escape_xml(upi_id)}</b>" if upi_id else ""),
        make_p(font_size=FS_BODY, leading=FS_BODY + 3)
    )

    qr_flowable = None
    if upi_id:
        try:
            upi_payload = f"upi://pay?pa={upi_id}&pn={comp.get('name', 'Company')}&am={balance_payable:.2f}&cu=INR"
            qr_widget = QrCodeWidget(upi_payload)
            qr_widget.barWidth = 44.0
            qr_widget.barHeight = 44.0
            qr_widget.qrVersion = 1
            d_qr = Drawing(44.0, 44.0)
            d_qr.add(qr_widget)
            qr_flowable = d_qr
        except Exception as e:
            logger.warning(f"Failed to generate UPI QR: {e}")
            qr_flowable = Paragraph(f"Scan UPI:<br/>{escape_xml(upi_id)}", make_p(font_size=FS_SMALL, alignment=1))

    if qr_flowable:
        how_to_pay_table = Table([[bank_details_p, qr_flowable]], colWidths=[FRAME_WIDTH_PT - 60.0, 60.0])
    else:
        how_to_pay_table = Table([[bank_details_p]], colWidths=[FRAME_WIDTH_PT])

    how_to_pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(how_to_pay_table)
    story.append(Spacer(1, 4))

    # 3. Buyer Block ("Billed To" and "Ship To")
    billed_p = Paragraph(
        f"<b>Billed To:</b><br/>"
        f"<b>{escape_xml(cust.get('name', ''))}</b><br/>"
        f"{escape_xml(cust.get('address', ''))}<br/>"
        f"GSTIN: <b>{escape_xml(cust.get('gstin', 'N/A'))}</b> | State: <b>{escape_xml(cust.get('state', ''))}</b>",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    ship_name = ship.get('name') or cust.get('name', '')
    ship_addr = ship.get('address') or cust.get('address', '')
    ship_p = Paragraph(
        f"<b>Ship To:</b><br/>"
        f"<b>{escape_xml(ship_name)}</b><br/>"
        f"{escape_xml(ship_addr)}<br/>"
        f"GSTIN: <b>{escape_xml(ship.get('gstin') or cust.get('gstin', 'N/A'))}</b> | State: <b>{escape_xml(ship.get('state') or cust.get('state', ''))}</b>",
        make_p(font_size=FS_BODY, leading=FS_BODY + 2.5)
    )

    buyer_table = Table([[billed_p, ship_p]], colWidths=[half_w, half_w])
    buyer_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(buyer_table)
    story.append(Spacer(1, 4))

    # 4. Detail Strip (PO Ref, PO Date, Quotation Ref, Delivery Period, Payment Terms)
    po_ref = escape_xml(data.get("customer_po_no") or data.get("po_number") or "-")
    po_date = format_date_ddmmyyyy(data.get("customer_po_date") or data.get("po_date")) or "-"
    quot_ref = escape_xml(data.get("reference_number") or data.get("quotation_ref") or "-")
    del_period = escape_xml(data.get("delivery_period") or "-")
    pay_terms = escape_xml(data.get("payment_terms") or comp.get("terms_proforma") or "Immediate")

    strip_data = [
        [
            Paragraph(f"Customer PO Ref:<br/><b>{po_ref}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"PO Date:<br/><b>{po_date}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Ref/Quot No.:<br/><b>{quot_ref}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Delivery Period:<br/><b>{del_period}</b>", make_p(font_size=FS_SMALL)),
            Paragraph(f"Payment Terms:<br/><b>{pay_terms}</b>", make_p(font_size=FS_SMALL)),
        ]
    ]
    strip_w = FRAME_WIDTH_PT / 5.0
    t_strip = Table(strip_data, colWidths=[strip_w] * 5)
    t_strip.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_strip)
    story.append(Spacer(1, 4))

    # 5. Items Table
    headers = [
        [
            Paragraph("<b>Sl</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Description</b>", make_p(font_size=FS_BODY, bold=True)),
            Paragraph("<b>HSN</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Qty</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Unit</b>", make_p(font_size=FS_BODY, bold=True, alignment=1)),
            Paragraph("<b>Rate</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Disc</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Tax %</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
            Paragraph("<b>Amount</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)),
        ]
    ]

    item_rows = []
    tot_qty = 0.0
    tot_amt = 0.0

    for idx, it in enumerate(data.get("items", []), start=1):
        desc = escape_xml(it.get("item_description") or it.get("product_name") or "Item")
        hsn = escape_xml(str(it.get("hsn_code") or "-"))
        qty = float(it.get("quantity") or 0.0)
        tot_qty += qty
        unit = escape_xml(it.get("unit") or "PCS")
        rate = float(it.get("unit_price") or 0.0)
        disc_val = float(it.get("discount_pct") or it.get("discount") or 0.0)
        tax_pct = float(it.get("tax_rate") or it.get("gst_rate_pct") or 0.0)
        amt = float(it.get("total_item_amount") or (qty * rate))
        tot_amt += amt

        disc_str = f"{disc_val:.1f}%" if disc_val > 0 else "-"
        rate_str = format_currency(rate, num_fmt)
        amt_str = format_currency(amt, num_fmt)

        item_rows.append([
            Paragraph(str(idx), make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(f"<b>{desc}</b>", make_p(font_size=FS_BODY)),
            Paragraph(hsn, make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(f"{qty:,.2f}", make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(unit, make_p(font_size=FS_BODY, alignment=1)),
            Paragraph(rate_str, make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(disc_str, make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(f"{tax_pct:.1f}%", make_p(font_size=FS_BODY, alignment=2)),
            Paragraph(amt_str, make_p(font_size=FS_BODY, alignment=2)),
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
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_ACCENT_BG),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, COLOR_ACCENT),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_GRID),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_GRID),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_GRID),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    meas_table = Table(headers + item_rows + [total_row], colWidths=COLS_PROFORMA)
    meas_table.setStyle(TableStyle(table_style))

    # 6. Summary & Financial Reconciliation (Sub Total, Discount, Taxes, Grand Total, Advance, Balance)
    footer_elements = []

    sub_tot = float(totals.get("subtotal") or totals.get("taxable_amount") or tot_amt)
    cgst_tot = float(totals.get("cgst_total") or totals.get("cgst_amount") or 0.0)
    sgst_tot = float(totals.get("sgst_total") or totals.get("sgst_amount") or 0.0)
    igst_tot = float(totals.get("igst_total") or totals.get("igst_amount") or 0.0)
    round_off = float(totals.get("round_off") or 0.0)

    sum_rows = [
        [Paragraph("Sub Total:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sub_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))],
    ]
    if cgst_tot > 0 or sgst_tot > 0:
        sum_rows.append([Paragraph("CGST:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(cgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
        sum_rows.append([Paragraph("SGST:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(sgst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
    if igst_tot > 0:
        sum_rows.append([Paragraph("IGST:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(igst_tot, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])
    if round_off != 0.0:
        sum_rows.append([Paragraph("Round Off:", make_p(font_size=FS_BODY)), Paragraph(f"Rs. {format_currency(round_off, num_fmt)}", make_p(font_size=FS_BODY, alignment=2))])

    sum_rows.append([
        Paragraph("<b>Grand Total:</b>", make_p(font_size=FS_BODY + 1, bold=True)),
        Paragraph(f"<b>Rs. {format_currency(grand_total, num_fmt)}</b>", make_p(font_size=FS_BODY + 1, bold=True, alignment=2))
    ])

    if adv_received > 0:
        sum_rows.append([
            Paragraph("Less: Advance Received:", make_p(font_size=FS_BODY, color=colors.HexColor("#16A34A"))),
            Paragraph(f"<b>- Rs. {format_currency(adv_received, num_fmt)}</b>", make_p(font_size=FS_BODY, bold=True, color=colors.HexColor("#16A34A"), alignment=2))
        ])

    sum_rows.append([
        Paragraph("<b>Balance Payable:</b>", make_p(font_size=FS_BODY + 1.5, bold=True, color=COLOR_ACCENT)),
        Paragraph(f"<b>Rs. {format_currency(balance_payable, num_fmt)}</b>", make_p(font_size=FS_BODY + 1.5, bold=True, color=COLOR_ACCENT, alignment=2))
    ])

    t_summary = Table(sum_rows, colWidths=[half_w * 0.5, half_w * 0.5])
    t_summary.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_GRID),
        ('BOX', (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_ACCENT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    amt_words = amount_to_words_inr(grand_total)
    words_p = Paragraph(f"Amount in Words:<br/><b>{amt_words}</b>", make_p(font_size=FS_BODY, leading=FS_BODY + 3))

    terms_pf = comp.get("terms_proforma") or "1. Goods will be dispatched after receipt of payment.\n2. Validity of quotation/prices as stated above."
    terms_p = Paragraph(f"<b>Terms of Proforma:</b><br/>{escape_xml(terms_pf).replace(chr(10), '<br/>')}", make_p(font_size=FS_SMALL, leading=FS_SMALL + 2.5))

    left_summary_content = [words_p, Spacer(1, 4), terms_p]
    sum_box_table = Table([[left_summary_content, t_summary]], colWidths=[half_w - 6.0, half_w + 6.0])
    sum_box_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    footer_elements.append(sum_box_table)

    # 7. Declaration & Signatory
    decl_p = Paragraph(
        f"<b>Declaration:</b><br/>"
        + escape_xml(comp.get("declaration") or "We declare that this proforma invoice shows the true estimate and specifications of the goods."),
        make_p(font_size=FS_SMALL, leading=FS_SMALL + 2)
    )

    sig_img = load_safe_image(comp.get("signature_path"), max_w_pt=90.0, max_h_pt=30.0)
    sig_content = [
        Paragraph(f"for <b>{escape_xml(comp.get('name', 'Company'))}</b>", make_p(font_size=FS_BODY, alignment=2)),
    ]
    if sig_img:
        sig_content.append(sig_img)
    else:
        sig_content.append(Spacer(1, 24.0))
    sig_content.append(Paragraph("<b>Authorised Signatory</b>", make_p(font_size=FS_BODY, bold=True, alignment=2)))

    sign_table = Table([[decl_p, sig_content]], colWidths=[half_w, half_w])
    sign_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    footer_elements.append(sign_table)

    # 8. Measure flex filler height
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
        col_widths=COLS_PROFORMA,
        base_style=table_style,
        filler_height=filler_h,
        total_row_data=total_row,
        total_row_style=[
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, COLOR_GRID),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, COLOR_GRID),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_ACCENT_BG),
            ('TOPPADDING', (0, -1), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 2.5),
        ]
    )

    story.append(stretched_table)
    story.extend(footer_elements)
    return story


def render_proforma_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Renders the Proforma Invoice to an A4 PDF document with payment-request layout."""
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

    story = _build_proforma_story(data)

    # Check for converted or draft stamps
    status = str(data.get("status", "")).lower()
    linked_inv = data.get("linked_invoice_reference")

    class ProformaNumberedCanvas(NumberedCanvas):
        def draw_page_decorations(self, total_pages: int):
            super().draw_page_decorations(total_pages)
            if linked_inv:
                draw_watermark_stamp(self, f"CONVERTED: {linked_inv}", color_hex="#16A34A")
            elif status == "draft":
                draw_watermark_stamp(self, "DRAFT", color_hex="#94A3B8")
            elif status == "expired":
                draw_watermark_stamp(self, "EXPIRED", color_hex="#DC2626")

    doc.build(story, canvasmaker=ProformaNumberedCanvas)
    return output_path
