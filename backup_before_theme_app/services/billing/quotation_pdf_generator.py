"""
Professional Commercial Quotation & Proposal PDF Generator.
Engineered for modern B2B commerce with an executive corporate layout.
Specifically designed to gracefully cover the FULL A4 page with balanced
visual weight, no bottom empty space, corporate navy and gold styling,
prominent validity tracking, and dual customer-acceptance & stamp blocks.
"""
import os
from datetime import date
from decimal import Decimal
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

try:
    from num2words import num2words
except ImportError:
    num2words = None


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that anchors an executive full-width corporate footer band
    at the bottom edge of every page and dynamically renders exact 'Page X of Y' numbering.
    """
    _comp_name = "Commercial Quotation"
    _comp_contact = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, total_pages):
        self.saveState()
        w, h = A4

        # Executive Corporate Navy Footer Band (height 28pt)
        self.setFillColor(colors.HexColor('#0F2942'))
        self.rect(0, 0, w, 28, stroke=0, fill=1)

        # Warm Amber Gold Accent Stripe (height 2.5pt)
        self.setFillColor(colors.HexColor('#D97706'))
        self.rect(0, 28, w, 2.5, stroke=0, fill=1)

        # Upper footer text (Company Name & Core Contact Details)
        self.setFillColor(colors.white)
        self.setFont('Helvetica-Bold', 7)
        top_line = f"{self._comp_name}"
        if self._comp_contact:
            top_line += f"  •  {self._comp_contact}"
        self.drawCentredString(w / 2.0, 16, top_line)

        # Lower footer text (Statutory Notice & Page Count)
        self.setFont('Helvetica', 6.5)
        self.drawString(25, 7, "This is an official Commercial Price Quotation  •  Commercial Confidential Document")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(w - 25, 7, page_str)

        self.restoreState()


class QuotationPDFGenerator:
    """
    Generates high-impact, business-oriented PDF quotations that cover the full A4 page.
    Features executive navy (#0F2942) and gold (#D97706) styling, balanced full-page
    density, client proposal card, detailed commercial terms, and dual signature blocks.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()

        # Corporate Executive Palette
        self.c_primary = colors.HexColor('#0F2942')       # Deep Executive Navy
        self.c_primary_light = colors.HexColor('#EBF3FA') # Soft Ice Blue
        self.c_secondary = colors.HexColor('#1E40AF')     # Royal Slate Blue
        self.c_accent = colors.HexColor('#D97706')        # Warm Champagne Gold / Amber
        self.c_accent_light = colors.HexColor('#FEF3C7')  # Soft Amber Tint
        self.c_accent_dark = colors.HexColor('#B45309')   # Rich Amber Text
        self.c_dark = colors.HexColor('#1E293B')          # Slate 800 (Main text)
        self.c_muted = colors.HexColor('#64748B')         # Slate 500 (Subtext)
        self.c_light_bg = colors.HexColor('#F8FAFC')      # Slate 50 background
        self.c_border = colors.HexColor('#CBD5E1')        # Slate 300 border
        self.c_border_subtle = colors.HexColor('#E2E8F0') # Slate 200 border
        self.c_success = colors.HexColor('#15803D')       # Emerald Green
        self.c_success_light = colors.HexColor('#DCFCE7') # Soft Emerald Tint

        self._setup_styles()

    def _setup_styles(self):
        # Top Header Styles
        self.styles.add(ParagraphStyle(
            name='QCompName', parent=self.styles['Normal'],
            fontSize=16, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=19, spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name='QCompTagline', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Oblique', textColor=self.c_muted,
            leading=10, spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name='QCompInfo', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.c_dark,
            leading=10.5
        ))

        # Document Title Block Styles
        self.styles.add(ParagraphStyle(
            name='QDocTitle', parent=self.styles['Normal'],
            fontSize=21, fontName='Helvetica-Bold', textColor=self.c_primary,
            alignment=TA_RIGHT, leading=23
        ))
        self.styles.add(ParagraphStyle(
            name='QDocSubtitle', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_accent_dark,
            alignment=TA_RIGHT, leading=10, spaceAfter=3
        ))
        self.styles.add(ParagraphStyle(
            name='QDocNumber', parent=self.styles['Normal'],
            fontSize=11.5, fontName='Helvetica-Bold', textColor=self.c_secondary,
            alignment=TA_RIGHT, leading=13
        ))
        self.styles.add(ParagraphStyle(
            name='QMetaRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=10.5
        ))
        self.styles.add(ParagraphStyle(
            name='QValidityBadge', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_accent_dark,
            alignment=TA_RIGHT, leading=11
        ))

        # Section Card Headers
        self.styles.add(ParagraphStyle(
            name='QSectionHeader', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=10, textTransform='uppercase'
        ))
        self.styles.add(ParagraphStyle(
            name='QClientName', parent=self.styles['Normal'],
            fontSize=10.5, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=12.5, spaceAfter=1
        ))
        self.styles.add(ParagraphStyle(
            name='QCardText', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.c_dark,
            leading=10.5
        ))

        # Table Styles
        self.styles.add(ParagraphStyle(
            name='QTableHead', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_CENTER, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QTableHeadLeft', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_LEFT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QTableHeadRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_RIGHT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QItemName', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_dark,
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='QItemDesc', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica', textColor=self.c_muted,
            leading=9
        ))
        self.styles.add(ParagraphStyle(
            name='QItemCellCenter', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_CENTER, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='QItemCellRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='QItemCellRightBold', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=10
        ))

        # Financial Summary Styles
        self.styles.add(ParagraphStyle(
            name='QSummaryLabel', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=11
        ))
        self.styles.add(ParagraphStyle(
            name='QSummaryVal', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=11
        ))
        self.styles.add(ParagraphStyle(
            name='QGrandLabel', parent=self.styles['Normal'],
            fontSize=9.5, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_RIGHT, leading=13
        ))
        self.styles.add(ParagraphStyle(
            name='QGrandVal', parent=self.styles['Normal'],
            fontSize=11, fontName='Helvetica-Bold', textColor=self.c_accent_light,
            alignment=TA_RIGHT, leading=13
        ))

        # Words & Bank Info Styles
        self.styles.add(ParagraphStyle(
            name='QWordsLabel', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica-Bold', textColor=self.c_muted,
            leading=8.5
        ))
        self.styles.add(ParagraphStyle(
            name='QWordsText', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=10.5
        ))
        self.styles.add(ParagraphStyle(
            name='QBankTitle', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QBankText', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica', textColor=self.c_dark,
            leading=9.5
        ))

        # Terms & Conditions Styles
        self.styles.add(ParagraphStyle(
            name='QTermsHeader', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=10, spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name='QTermsBody', parent=self.styles['Normal'],
            fontSize=6.8, fontName='Helvetica', textColor=self.c_dark,
            leading=9.8
        ))

        # Signature & Acceptance Styles
        self.styles.add(ParagraphStyle(
            name='QSignHeader', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.c_primary,
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='QSignSub', parent=self.styles['Normal'],
            fontSize=6.8, fontName='Helvetica', textColor=self.c_muted,
            leading=8.5
        ))
        self.styles.add(ParagraphStyle(
            name='QSignFootLeft', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_LEFT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QSignFootRight', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica', textColor=self.c_dark,
            alignment=TA_RIGHT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='QStampText', parent=self.styles['Normal'],
            fontSize=6.8, fontName='Helvetica-Oblique', textColor=self.c_muted,
            alignment=TA_CENTER, leading=9
        ))

    @staticmethod
    def _safe_str(val, default=''):
        if val is None or str(val).strip() in ('None', ''):
            return default
        return str(val).strip()

    def generate_quotation(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Generate a fully styled, executive commercial quotation PDF covering full A4 page.
        """
        if not filename:
            from app.config import EXPORTS_DIR
            q_num = self._safe_str(data.get('invoice_number', 'DRAFT')).replace('/', '-')
            filename = os.path.join(str(EXPORTS_DIR), f"quotation_{q_num}.pdf")

        filepath = filename
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Standard A4 with compact 25pt margins and bottom margin reserved for footer band
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=22,
            bottomMargin=34  # Leaves space for the 28pt corporate footer band
        )

        story = []
        company = data.get('company') or {}
        customer = data.get('customer') or {}
        logistics = data.get('logistics') or {}
        consignee = data.get('consignee') or {}
        items = data.get('items') or []
        totals = data.get('totals') or {}

        # ==============================================================================
        # 1. TOP BRAND RIBBON & HEADER
        # ==============================================================================
        comp_name = self._safe_str(company.get('name'), 'SITA RAM & SONS TRADERS')
        comp_addr = self._safe_str(company.get('address'), '')
        comp_city = self._safe_str(company.get('city'), '')
        comp_state = self._safe_str(company.get('state'), 'Maharashtra')
        comp_sc = self._safe_str(company.get('state_code'), '27')
        comp_pin = self._safe_str(company.get('pincode'), '')
        comp_gstin = self._safe_str(company.get('gstin'), '')
        comp_pan = self._safe_str(company.get('pan'), '')
        comp_phone = self._safe_str(company.get('phone'), '')
        comp_email = self._safe_str(company.get('email'), '')

        # Set canvas meta for dynamic footer
        NumberedCanvas._comp_name = comp_name
        contact_bits = []
        if comp_phone: contact_bits.append(f"Tel: {comp_phone}")
        if comp_email: contact_bits.append(f"Email: {comp_email}")
        if comp_gstin: contact_bits.append(f"GSTIN: {comp_gstin}")
        NumberedCanvas._comp_contact = "  •  ".join(contact_bits)

        addr_parts = [p for p in [comp_addr, comp_city, f"{comp_state} ({comp_sc})" if comp_state else "", comp_pin] if p]
        full_addr_str = ", ".join(addr_parts)

        # Left Column: Company Info
        left_header = []
        left_header.append(Paragraph(comp_name, self.styles['QCompName']))
        left_header.append(Paragraph("Commercial Trading, Industrial Supplies & Engineering Solutions", self.styles['QCompTagline']))
        if full_addr_str:
            left_header.append(Paragraph(full_addr_str, self.styles['QCompInfo']))

        id_lines = []
        if comp_gstin:
            id_lines.append(f"<b>GSTIN:</b> {comp_gstin}")
        if comp_pan:
            id_lines.append(f"<b>PAN:</b> {comp_pan}")
        if id_lines:
            left_header.append(Paragraph(" &nbsp;|&nbsp; ".join(id_lines), self.styles['QCompInfo']))

        contact_lines = []
        if comp_phone:
            contact_lines.append(f"<b>Tel:</b> {comp_phone}")
        if comp_email:
            contact_lines.append(f"<b>Email:</b> {comp_email}")
        if contact_lines:
            left_header.append(Paragraph(" &nbsp;|&nbsp; ".join(contact_lines), self.styles['QCompInfo']))

        # Right Column: Quotation Meta
        quote_no = self._safe_str(data.get('invoice_number'), 'QT/24-25/0001')
        quote_date = self._safe_str(data.get('date'), str(date.today()))
        valid_until = self._safe_str(data.get('valid_until'), '')
        ref_no = self._safe_str(data.get('reference_number') or data.get('po_number'), '')

        right_header = []
        right_header.append(Paragraph("PRICE QUOTATION", self.styles['QDocTitle']))
        right_header.append(Paragraph("OFFICIAL COMMERCIAL PROPOSAL", self.styles['QDocSubtitle']))
        right_header.append(Paragraph(f"Ref #: <b>{quote_no}</b>", self.styles['QDocNumber']))
        right_header.append(Paragraph(f"<b>Date of Issue:</b> {quote_date}", self.styles['QMetaRight']))

        if valid_until:
            right_header.append(Paragraph(f"<b>Offer Valid Until:</b> <font color='#B45309'><b>{valid_until}</b></font>", self.styles['QValidityBadge']))
        else:
            right_header.append(Paragraph("<b>Validity:</b> 30 Days from date of issue", self.styles['QMetaRight']))

        if ref_no:
            right_header.append(Paragraph(f"<b>Customer Ref/RFQ:</b> {ref_no}", self.styles['QMetaRight']))

        top_header_table = Table([[left_header, right_header]], colWidths=[314, 230])
        top_header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, self.c_primary),
        ]))
        story.append(top_header_table)
        story.append(Spacer(1, 7))

        # ==============================================================================
        # 2. CLIENT INFORMATION & PROPOSAL SCOPE CARD
        # ==============================================================================
        cust_name = self._safe_str(customer.get('name'), 'Valued Customer')
        cust_addr = self._safe_str(customer.get('address'), '—')
        cust_gstin = self._safe_str(customer.get('gstin'), 'Unregistered / Retail')
        cust_state = self._safe_str(customer.get('state'), comp_state)
        cust_phone = self._safe_str(customer.get('phone'), '')
        cust_email = self._safe_str(customer.get('email'), '')

        dest = self._safe_str(logistics.get('destination'), '')
        ship_addr = self._safe_str(consignee.get('address'), '')

        client_box = [
            Paragraph("PROPOSAL PREPARED FOR", self.styles['QSectionHeader']),
            Spacer(1, 1),
            Paragraph(cust_name, self.styles['QClientName']),
            Paragraph(f"<b>Address:</b> {cust_addr}", self.styles['QCardText']),
            Paragraph(f"<b>GSTIN/UIN:</b> {cust_gstin} &nbsp;|&nbsp; <b>State:</b> {cust_state}", self.styles['QCardText']),
        ]
        cust_contact = []
        if cust_phone: cust_contact.append(f"<b>Phone:</b> {cust_phone}")
        if cust_email: cust_contact.append(f"<b>Email:</b> {cust_email}")
        if cust_contact:
            client_box.append(Paragraph(" &nbsp;|&nbsp; ".join(cust_contact), self.styles['QCardText']))

        dest_val = dest if dest else (cust_state if cust_state else "Customer Premise")
        terms_val = self._safe_str(logistics.get('payment_terms'), 'As per standard commercial policy')
        carrier_val = self._safe_str(logistics.get('dispatched_through'), 'Standard Surface Transport')

        scope_box = [
            Paragraph("COMMERCIAL PARAMETERS", self.styles['QSectionHeader']),
            Spacer(1, 1),
            Paragraph(f"<b>Delivery Destination:</b> {dest_val}", self.styles['QCardText']),
            Paragraph(f"<b>Shipment Mode:</b> {carrier_val}", self.styles['QCardText']),
            Paragraph(f"<b>Price Basis:</b> Ex-Warehouse / Delivery as agreed", self.styles['QCardText']),
            Paragraph(f"<b>Payment Terms:</b> {terms_val}", self.styles['QCardText']),
        ]
        if ship_addr and ship_addr != cust_addr:
            scope_box.append(Paragraph(f"<b>Site / Ship To:</b> {ship_addr}", self.styles['QCardText']))

        client_card_table = Table([[client_box, scope_box]], colWidths=[304, 240])
        client_card_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, self.c_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.c_border_subtle),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), self.c_light_bg),
            ('BACKGROUND', (1, 0), (1, 0), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(client_card_table)
        story.append(Spacer(1, 7))

        # ==============================================================================
        # 3. LINE ITEMS TABLE (Exact 544 pt total width with full-page density)
        # ==============================================================================
        tax_mode = data.get('tax_mode', 'intra_state')
        is_interstate = (tax_mode == 'inter_state')

        headers = [
            Paragraph("<b>#</b>", self.styles['QTableHead']),
            Paragraph("<b>Item Description & Specifications</b>", self.styles['QTableHeadLeft']),
            Paragraph("<b>HSN</b>", self.styles['QTableHead']),
            Paragraph("<b>Qty</b>", self.styles['QTableHead']),
            Paragraph("<b>Unit</b>", self.styles['QTableHead']),
            Paragraph("<b>Rate (Rs.)</b>", self.styles['QTableHeadRight']),
            Paragraph("<b>Disc%</b>", self.styles['QTableHead']),
            Paragraph("<b>Taxable (Rs.)</b>", self.styles['QTableHeadRight']),
            Paragraph("<b>GST</b>", self.styles['QTableHead']),
            Paragraph("<b>Total (Rs.)</b>", self.styles['QTableHeadRight']),
        ]
        col_widths = [22, 168, 42, 35, 32, 55, 36, 58, 42, 54]  # sum = 544 pt

        table_rows = [headers]
        total_taxable_calc = Decimal("0.00")
        total_cgst_calc = Decimal("0.00")
        total_sgst_calc = Decimal("0.00")
        total_igst_calc = Decimal("0.00")
        total_discount_savings = Decimal("0.00")

        num_real_items = len(items)
        for idx, item in enumerate(items, 1):
            p_name = self._safe_str(item.get('product_name') or item.get('item_description'), 'Item')
            p_desc = self._safe_str(item.get('description'), '')
            hsn = self._safe_str(item.get('hsn_code'), '—')
            qty = Decimal(str(item.get('quantity', 1)))
            unit = self._safe_str(item.get('unit'), 'PCS')
            unit_price = Decimal(str(item.get('unit_price', 0)))
            disc_pct = Decimal(str(item.get('discount_pct', 0)))
            tax_rate = Decimal(str(item.get('tax_rate') or item.get('gst_rate_pct', 18)))

            base_val = qty * unit_price
            disc_amt = base_val * disc_pct / Decimal("100")
            taxable_val = base_val - disc_amt
            total_discount_savings += disc_amt
            total_taxable_calc += taxable_val

            tax_val = taxable_val * tax_rate / Decimal("100")
            if is_interstate:
                total_igst_calc += tax_val
                gst_label = f"IGST {tax_rate:.0f}%"
            else:
                total_cgst_calc += tax_val / Decimal("2")
                total_sgst_calc += tax_val / Decimal("2")
                gst_label = f"GST {tax_rate:.0f}%"

            line_total = taxable_val + tax_val

            desc_elements = [Paragraph(f"<b>{p_name}</b>", self.styles['QItemName'])]
            if p_desc:
                desc_elements.append(Paragraph(p_desc, self.styles['QItemDesc']))

            table_rows.append([
                Paragraph(str(idx), self.styles['QItemCellCenter']),
                desc_elements,
                Paragraph(hsn, self.styles['QItemCellCenter']),
                Paragraph(f"{qty:.2f}", self.styles['QItemCellCenter']),
                Paragraph(unit, self.styles['QItemCellCenter']),
                Paragraph(f"{unit_price:,.2f}", self.styles['QItemCellRight']),
                Paragraph(f"{disc_pct:.1f}%" if disc_pct > 0 else "—", self.styles['QItemCellCenter']),
                Paragraph(f"{taxable_val:,.2f}", self.styles['QItemCellRight']),
                Paragraph(gst_label, self.styles['QItemCellCenter']),
                Paragraph(f"<b>{line_total:,.2f}</b>", self.styles['QItemCellRightBold']),
            ])

        # Dynamic filler row logic to guarantee full-page A4 balance:
        if num_real_items <= 2:
            target_rows = 8
            row_pad = 6.0
        elif num_real_items == 3:
            target_rows = 7
            row_pad = 5.0
        elif num_real_items == 4:
            target_rows = 6
            row_pad = 4.0
        else:
            target_rows = num_real_items
            row_pad = 3.5

        if num_real_items < target_rows:
            for fill_idx in range(num_real_items + 1, target_rows + 1):
                table_rows.append([
                    Paragraph(f"<font color='#CBD5E1'>{fill_idx}</font>", self.styles['QItemCellCenter']),
                    Paragraph("<font color='#E2E8F0'>—</font>", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellRight']),
                    Paragraph("", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellRight']),
                    Paragraph("", self.styles['QItemCellCenter']),
                    Paragraph("", self.styles['QItemCellRightBold']),
                ])

        items_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), self.c_primary),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 5.0),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5.0),
            ('TOPPADDING', (0, 1), (-1, -1), row_pad),
            ('BOTTOMPADDING', (0, 1), (-1, -1), row_pad),
            ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
            ('BOX', (0, 0), (-1, -1), 0.75, self.c_primary),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, self.c_border_subtle),
        ]
        for r_idx in range(1, len(table_rows)):
            bg = colors.white if (r_idx % 2 != 0) else self.c_light_bg
            ts.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg))

        items_table.setStyle(TableStyle(ts))
        story.append(items_table)
        story.append(Spacer(1, 7))

        # ==============================================================================
        # 4. TOTALS, WORDS, AND BANKING SECTION
        # ==============================================================================
        taxable_final = float(totals.get('taxable_amount', total_taxable_calc))
        cgst_final = float(totals.get('cgst_amount', total_cgst_calc))
        sgst_final = float(totals.get('sgst_amount', total_sgst_calc))
        igst_final = float(totals.get('igst_amount', total_igst_calc))
        total_tax_final = cgst_final + sgst_final + igst_final
        grand_total_final = float(totals.get('grand_total', taxable_final + total_tax_final))

        left_sub = []

        amt_words = ""
        if num2words:
            try:
                amt_words = num2words(grand_total_final, lang='en_IN').title() + " Only"
            except Exception:
                try:
                    amt_words = num2words(grand_total_final).title() + " Only"
                except Exception:
                    amt_words = ""

        if amt_words:
            words_content = [
                Paragraph("TOTAL AMOUNT IN WORDS (INR):", self.styles['QWordsLabel']),
                Paragraph(f"<b>{amt_words}</b>", self.styles['QWordsText']),
            ]
            words_tbl = Table([[words_content]], colWidths=[304])
            words_tbl.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, self.c_border),
                ('BACKGROUND', (0, 0), (-1, -1), self.c_light_bg),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            left_sub.append(words_tbl)
            left_sub.append(Spacer(1, 4))

        # Payment & Remittance Card (ALWAYS present, never left blank!)
        b_name = self._safe_str(company.get('bank_name'))
        b_ac = self._safe_str(company.get('account_no') or company.get('bank_account_no'))
        b_ifsc = self._safe_str(company.get('ifsc') or company.get('bank_ifsc'))
        b_branch = self._safe_str(company.get('bank_branch'))
        b_upi = self._safe_str(company.get('upi_id'))

        if b_name or b_ac:
            bank_lines = [
                Paragraph("BANK WIRE TRANSFER & REMITTANCE DETAILS", self.styles['QBankTitle']),
                Paragraph(f"Bank Name: <b>{b_name}</b> &nbsp;|&nbsp; Branch: <b>{b_branch or 'Main Branch'}</b>", self.styles['QBankText']),
                Paragraph(f"Account #: <b>{b_ac}</b> &nbsp;|&nbsp; IFSC Code: <b>{b_ifsc}</b>", self.styles['QBankText']),
            ]
            if b_upi:
                bank_lines.append(Paragraph(f"UPI ID: <b>{b_upi}</b> &nbsp;|&nbsp; Beneficiary: <b>{comp_name}</b>", self.styles['QBankText']))
            bank_lines.append(Paragraph("<i>Remittance note: Kindly reference this quotation number in your transfer remarks.</i>", self.styles['QBankText']))
        else:
            bank_lines = [
                Paragraph("COMMERCIAL PAYMENT & SETTLEMENT INSTRUCTIONS", self.styles['QBankTitle']),
                Paragraph("<b>Mode of Payment:</b> RTGS / NEFT / Net Banking / Crossed A/C Payee Cheque", self.styles['QBankText']),
                Paragraph(f"<b>Beneficiary:</b> <b>{comp_name}</b> &nbsp;|&nbsp; <b>Currency:</b> INR (Indian Rupee)", self.styles['QBankText']),
                Paragraph("<b>Settlement Terms:</b> As agreed in commercial contract. Proforma invoice issued on request.", self.styles['QBankText']),
                Paragraph("<i>Official Tax Invoice with statutory e-Way Bill generated upon delivery.</i>", self.styles['QBankText']),
            ]

        bank_tbl = Table([[bank_lines]], colWidths=[304])
        bank_tbl.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, self.c_border_subtle),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 4.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        left_sub.append(bank_tbl)

        summary_rows = [
            [Paragraph("Taxable Subtotal:", self.styles['QSummaryLabel']), Paragraph(f"Rs. {taxable_final:,.2f}", self.styles['QSummaryVal'])],
        ]
        if total_discount_savings > 0:
            summary_rows.append([
                Paragraph("<font color='#15803D'>Client Discount Saved:</font>", self.styles['QSummaryLabel']),
                Paragraph(f"<font color='#15803D'>- Rs. {float(total_discount_savings):,.2f}</font>", self.styles['QSummaryVal'])
            ])

        if is_interstate:
            summary_rows.append([Paragraph("Integrated GST (IGST):", self.styles['QSummaryLabel']), Paragraph(f"Rs. {igst_final:,.2f}", self.styles['QSummaryVal'])])
        else:
            summary_rows.append([Paragraph("Central GST (CGST):", self.styles['QSummaryLabel']), Paragraph(f"Rs. {cgst_final:,.2f}", self.styles['QSummaryVal'])])
            summary_rows.append([Paragraph("State GST (SGST):", self.styles['QSummaryLabel']), Paragraph(f"Rs. {sgst_final:,.2f}", self.styles['QSummaryVal'])])

        summary_rows.append([Paragraph("Total GST Tax:", self.styles['QSummaryLabel']), Paragraph(f"Rs. {total_tax_final:,.2f}", self.styles['QSummaryVal'])])
        summary_rows.append([
            Paragraph("<b>GRAND TOTAL:</b>", self.styles['QGrandLabel']),
            Paragraph(f"<b>Rs. {grand_total_final:,.2f}</b>", self.styles['QGrandVal'])
        ])

        summary_table = Table(summary_rows, colWidths=[136, 100])
        summary_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -2), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('LINEABOVE', (0, -1), (-1, -1), 1, self.c_accent),
            ('BACKGROUND', (0, -1), (-1, -1), self.c_primary),
            ('TOPPADDING', (0, -1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 5),
        ]))

        split_totals_table = Table([[left_sub, summary_table]], colWidths=[308, 236])
        split_totals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(split_totals_table)
        story.append(Spacer(1, 7))

        # ==============================================================================
        # 5. COMMERCIAL TERMS & CONDITIONS (Comprehensive 7-Clause B2B Scope)
        # ==============================================================================
        raw_terms = self._safe_str(logistics.get('payment_terms') or data.get('terms_and_conditions'), '')
        if not raw_terms or len(raw_terms.split('\n')) <= 2:
            default_terms = [
                "1. Quotation Validity: This price quotation is strictly valid for 30 calendar days from date of issue and subject to written reconfirmation thereafter.",
                "2. Statutory Taxes: Goods and Services Tax (GST) is charged extra as applicable per prevailing statutory notifications.",
                "3. Order Confirmation: Formal Purchase Order referencing this Quotation Number must be issued to initiate order execution.",
                "4. Delivery Schedule: Standard dispatch schedule within 5-7 business days upon receipt of formal Purchase Order / Advance Clearance.",
                "5. Payment Terms: Payment as specified in commercial parameters. Delayed remittances are subject to interest @ 18% per annum.",
                "6. Inspection & Claims: Buyer shall inspect goods within 48 hours of arrival. Any discrepancies must be reported in writing immediately.",
                "7. Governing Jurisdiction: All transactions, quotations, and disputes are subject to local commercial court jurisdiction only."
            ]
        else:
            default_terms = [line.strip() for line in raw_terms.split('\n') if line.strip()]

        terms_lines = [Paragraph("COMMERCIAL TERMS & CONTRACTUAL CONDITIONS", self.styles['QTermsHeader'])]
        for t_line in default_terms:
            terms_lines.append(Paragraph(t_line, self.styles['QTermsBody']))

        terms_table = Table([[terms_lines]], colWidths=[544])
        terms_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, self.c_border_subtle),
            ('BACKGROUND', (0, 0), (-1, -1), self.c_light_bg),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(terms_table)
        story.append(Spacer(1, 7))

        # ==============================================================================
        # 6. DUAL ACCEPTANCE & AUTHORIZATION (Full Executive Height with Stamp Areas)
        # ==============================================================================
        # Left: Customer Acceptance Block
        cust_stamp_box = Table(
            [[Paragraph("[ AFFIX OFFICIAL CUSTOMER / COMPANY STAMP & SEAL HERE ]", self.styles['QStampText'])]],
            colWidths=[250], rowHeights=[48]
        )
        cust_stamp_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.6, self.c_border),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        sign_fields_data = [
            [
                Paragraph("<b>Authorized Signatory:</b> _________________", self.styles['QSignFootLeft']),
                Paragraph("<b>Designation:</b> _________________", self.styles['QSignFootLeft'])
            ],
            [
                Paragraph("<b>Signature Date:</b> _____ / _____ / 20___", self.styles['QSignFootLeft']),
                Paragraph("<b>PO / RFQ Ref #:</b> _________________", self.styles['QSignFootLeft'])
            ]
        ]
        sign_fields_tbl = Table(sign_fields_data, colWidths=[128, 126])
        sign_fields_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        cust_accept_box = [
            Paragraph("CUSTOMER ACCEPTANCE / PURCHASE AUTHORIZATION", self.styles['QSignHeader']),
            Paragraph("We confirm acceptance of this commercial proposal, scope of supply, and agreed terms.", self.styles['QSignSub']),
            Spacer(1, 3),
            cust_stamp_box,
            Spacer(1, 4),
            sign_fields_tbl,
        ]

        # Right: Company Signatory Block
        comp_stamp_box = Table(
            [[Paragraph(f"[ OFFICIAL SEAL / STAMP OF {comp_name[:24].upper()} ]", self.styles['QStampText'])]],
            colWidths=[250], rowHeights=[48]
        )
        comp_stamp_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.6, self.c_border),
            ('BACKGROUND', (0, 0), (-1, -1), self.c_light_bg),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        comp_fields_data = [
            [Paragraph("<b>Authorized Commercial Signatory & Endorsement</b>", self.styles['QSignFootRight'])],
            [Paragraph(f"<b>Prepared By:</b> Commercial Operations Desk &nbsp;|&nbsp; <b>Date:</b> {quote_date}", self.styles['QSignFootRight'])],
            [Paragraph("<b>System Verification:</b> Digitally Endorsed Official Commercial Proposal", self.styles['QSignFootRight'])],
        ]
        comp_fields_tbl = Table(comp_fields_data, colWidths=[258])
        comp_fields_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        company_auth_box = [
            Paragraph(f"FOR {comp_name.upper()}", self.styles['QSignHeader']),
            Paragraph("Authorised Commercial & Sales Representative", self.styles['QSignSub']),
            Spacer(1, 3),
            comp_stamp_box,
            Spacer(1, 4),
            comp_fields_tbl,
        ]

        dual_sign_table = Table([[cust_accept_box, company_auth_box]], colWidths=[270, 274])
        dual_sign_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, self.c_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.c_border_subtle),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), self.c_light_bg),
            ('BACKGROUND', (1, 0), (1, 0), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(dual_sign_table))

        # Build document using NumberedCanvas so footer is anchored at the bottom edge
        doc.build(story, canvasmaker=NumberedCanvas)
        return filepath
