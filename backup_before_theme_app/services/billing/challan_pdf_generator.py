"""
Delivery Challan PDF Generator
Professional PDF generator for delivery challans with CGST/SGST/IGST support,
clean visual hierarchy, balanced dual-column summary, and executive signatures.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import date
try:
    from num2words import num2words
except ImportError:
    num2words = None


class ChallanPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.primary_color = colors.HexColor('#1B4F72')        # Professional Navy
        self.primary_dark = colors.HexColor('#0F2C59')         # Deep Navy
        self.primary_light = colors.HexColor('#EBF3FB')        # Soft Ice Blue highlight
        self.bg_light = colors.HexColor('#F8FAFC')             # Slate 50
        self.border_color = colors.HexColor('#CBD5E1')         # Slate 300
        self.border_subtle = colors.HexColor('#E2E8F0')        # Slate 200
        self.text_dark = colors.HexColor('#1E293B')            # Slate 800
        self.text_muted = colors.HexColor('#64748B')           # Slate 500
        self.setup_custom_styles()

    def setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CompName', parent=self.styles['Normal'],
            fontSize=13, fontName='Helvetica-Bold', textColor=self.primary_dark, leading=16
        ))
        self.styles.add(ParagraphStyle(
            name='CompInfo', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.text_muted, leading=10.5
        ))
        self.styles.add(ParagraphStyle(
            name='ChallanTitle', parent=self.styles['Normal'],
            fontSize=17, fontName='Helvetica-Bold', textColor=self.primary_color,
            alignment=TA_RIGHT, leading=20
        ))
        self.styles.add(ParagraphStyle(
            name='ChallanSubTitle', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=self.text_muted,
            alignment=TA_RIGHT, leading=10
        ))

        # Metadata grid
        self.styles.add(ParagraphStyle(
            name='GridLabel', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica-Bold', textColor=self.text_muted, leading=8
        ))
        self.styles.add(ParagraphStyle(
            name='GridValue', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.text_dark, leading=10
        ))

        # Party details
        self.styles.add(ParagraphStyle(
            name='PartyHead', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.primary_color, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='PartyText', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.text_dark, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='PartyMuted', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica', textColor=self.text_muted, leading=9
        ))

        # Items table
        self.styles.add(ParagraphStyle(
            name='TH', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_CENTER, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='TCell', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=self.text_dark, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='TCellCenter', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER, textColor=self.text_dark, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='TCellRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', alignment=TA_RIGHT, textColor=self.text_dark, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='TCellBoldRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=self.text_dark, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='TCellBoldCenter', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=self.text_dark, leading=10
        ))

        # Amount in words & terms
        self.styles.add(ParagraphStyle(
            name='WordsLabel', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica-Bold', textColor=self.text_muted, leading=8
        ))
        self.styles.add(ParagraphStyle(
            name='WordsText', parent=self.styles['Normal'],
            fontSize=8.5, fontName='Helvetica-Bold', textColor=self.primary_dark, leading=11
        ))
        self.styles.add(ParagraphStyle(
            name='TermsLabel', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica-Bold', textColor=self.text_muted, leading=8
        ))
        self.styles.add(ParagraphStyle(
            name='TermsText', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica', textColor=self.text_muted, leading=8.5
        ))

        # Tax table
        self.styles.add(ParagraphStyle(
            name='TaxLabel', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica', textColor=colors.HexColor('#334155'),
            alignment=TA_RIGHT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='TaxVal', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=self.text_dark,
            alignment=TA_RIGHT, leading=9.5
        ))
        self.styles.add(ParagraphStyle(
            name='GrandLabel', parent=self.styles['Normal'],
            fontSize=8.5, fontName='Helvetica-Bold', textColor=self.primary_color,
            alignment=TA_RIGHT, leading=10.5
        ))
        self.styles.add(ParagraphStyle(
            name='GrandVal', parent=self.styles['Normal'],
            fontSize=9.5, fontName='Helvetica-Bold', textColor=self.primary_color,
            alignment=TA_RIGHT, leading=11
        ))

        # Signatures
        self.styles.add(ParagraphStyle(
            name='SignHeader', parent=self.styles['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=self.primary_color, leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='SignSub', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica', textColor=self.text_muted, leading=8.5
        ))
        self.styles.add(ParagraphStyle(
            name='SignFootLeft', parent=self.styles['Normal'],
            fontSize=7, fontName='Helvetica-Bold', textColor=colors.HexColor('#334155'), leading=9
        ))
        self.styles.add(ParagraphStyle(
            name='SignFootRight', parent=self.styles['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold', textColor=self.primary_dark,
            alignment=TA_RIGHT, leading=9
        ))

        # Page footnote
        self.styles.add(ParagraphStyle(
            name='FootNote', parent=self.styles['Normal'],
            fontSize=6.5, fontName='Helvetica', textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER
        ))

    def safe_str(self, value, default=''):
        return str(value) if value is not None and str(value) != 'None' else default

    def format_currency_words(self, amount):
        if num2words:
            try:
                amt = round(float(amount), 2)
                rupees = int(amt)
                paise = int(round((amt - rupees) * 100))
                words = num2words(rupees, lang='en_IN').title() + " Rupees"
                if paise > 0:
                    words += " and " + num2words(paise, lang='en_IN').title() + " Paise"
                return words + " Only"
            except Exception:
                return f"Rupees {amount:,.2f} Only"
        return f"Rupees {amount:,.2f} Only"

    def generate_challan(self, data, filename=None):
        """Generate a Delivery Challan PDF with CGST/SGST/IGST support"""
        if not filename:
            from app.config import EXPORTS_DIR
            filename = os.path.join(str(EXPORTS_DIR), f"challan_{data.get('challan_number', 'DRAFT').replace('/', '-')}.pdf")

        filepath = filename
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                rightMargin=0.35*inch, leftMargin=0.35*inch,
                                topMargin=0.35*inch, bottomMargin=0.35*inch)

        story = []

        company = data.get('company') or {}
        customer = data.get('customer') or {}
        logistics = data.get('logistics') or {}
        items = data.get('items') or []
        totals = data.get('totals') or {}

        is_interstate = data.get('is_interstate', False)

        # ==============================================================================
        # 1. HEADER: Company Info + Challan Title
        # ==============================================================================
        company_details = [
            Paragraph(f"<b>{self.safe_str(company.get('name', 'YOUR COMPANY NAME'))}</b>", self.styles['CompName']),
            Paragraph(f"{self.safe_str(company.get('address', ''))} • Phone: {self.safe_str(company.get('phone', ''))}", self.styles['CompInfo']),
            Paragraph(f"GSTIN: <b>{self.safe_str(company.get('gstin', ''))}</b> • State: {self.safe_str(company.get('state', ''))}", self.styles['CompInfo']),
            Paragraph(f"Email: {self.safe_str(company.get('email', ''))}", self.styles['CompInfo']),
        ]

        title_block = [
            Paragraph("DELIVERY CHALLAN", self.styles['ChallanTitle']),
            Spacer(1, 3),
            Paragraph("(Rule 55 of CGST Rules, 2017 • Not for Sale)", self.styles['ChallanSubTitle']),
        ]

        header_data = [[company_details, title_block]]
        header_table = Table(header_data, colWidths=[4.5*inch, 3.0*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, self.primary_color),
            ('BACKGROUND', (0, 0), (-1, -1), self.bg_light),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 5))

        # ==============================================================================
        # 2. CHALLAN DETAILS GRID
        # ==============================================================================
        def detail_cell(label, value):
            return [
                Paragraph(label, self.styles['GridLabel']),
                Paragraph(f"<b>{self.safe_str(value)}</b>", self.styles['GridValue'])
            ]

        challan_no = data.get('challan_number', '')
        challan_date = data.get('date', '')
        transport = data.get('transport_details', logistics.get('dispatched_through', ''))
        vehicle = logistics.get('vehicle_number', '')
        lr_no = logistics.get('dispatch_doc_no', '')
        eway_bill = logistics.get('waybill_no', '')
        destination = logistics.get('destination', '')

        details_grid = [
            [detail_cell("Challan No.", challan_no), detail_cell("Date", challan_date)],
            [detail_cell("Transport Mode", transport), detail_cell("Vehicle No.", vehicle)],
            [detail_cell("LR / Dispatch No.", lr_no), detail_cell("E-Way Bill No.", eway_bill)],
            [detail_cell("Destination", destination), ''],
        ]

        details_table = Table(details_grid, colWidths=[3.75*inch, 3.75*inch])
        details_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, self.border_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (0, 3), (1, 3)),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 5))

        # ==============================================================================
        # 3. PARTY DETAILS (Consignor / Consignee)
        # ==============================================================================
        consignor_name = company.get('name', 'YOUR COMPANY')
        consignor_addr = company.get('address', '')
        consignor_gstin = company.get('gstin', '')
        consignor_state = company.get('state', '')

        consignee_name = customer.get('name', '')
        consignee_addr = customer.get('address', '')
        consignee_gstin = customer.get('gstin', '')
        consignee_state = customer.get('state', '')
        ship_addr = customer.get('shipping_address') or consignee_addr

        party_data = [
            [
                Paragraph("CONSIGNOR (From)", self.styles['PartyHead']),
                Paragraph("CONSIGNEE (To)", self.styles['PartyHead'])
            ],
            [
                Paragraph(f"<b>{self.safe_str(consignor_name)}</b>", self.styles['PartyText']),
                Paragraph(f"<b>{self.safe_str(consignee_name)}</b>", self.styles['PartyText'])
            ],
            [
                Paragraph(self.safe_str(consignor_addr), self.styles['PartyText']),
                Paragraph(self.safe_str(ship_addr), self.styles['PartyText'])
            ],
            [
                Paragraph(f"GSTIN: <b>{self.safe_str(consignor_gstin)}</b> | State: {self.safe_str(consignor_state)}", self.styles['PartyMuted']),
                Paragraph(f"GSTIN: <b>{self.safe_str(consignee_gstin)}</b> | State: {self.safe_str(consignee_state)}", self.styles['PartyMuted'])
            ],
        ]

        party_table = Table(party_data, colWidths=[3.75*inch, 3.75*inch])
        party_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, self.border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.border_subtle),
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_light),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(party_table)
        story.append(Spacer(1, 5))

        # ==============================================================================
        # 4. ITEMS TABLE with CGST/SGST/IGST columns (Full 7.5 Inch Grid)
        # ==============================================================================
        if is_interstate:
            headers = [
                Paragraph('Sl<br/>No.', self.styles['TH']),
                Paragraph('Description of Goods', self.styles['TH']),
                Paragraph('HSN/SAC', self.styles['TH']),
                Paragraph('Qty', self.styles['TH']),
                Paragraph('Rate (Rs.)', self.styles['TH']),
                Paragraph('Unit', self.styles['TH']),
                Paragraph('IGST<br/>%', self.styles['TH']),
                Paragraph('Amount (Rs.)', self.styles['TH']),
            ]
            col_widths = [0.35*inch, 3.05*inch, 0.75*inch, 0.55*inch, 0.75*inch, 0.50*inch, 0.55*inch, 1.00*inch]
        else:
            headers = [
                Paragraph('Sl<br/>No.', self.styles['TH']),
                Paragraph('Description of Goods', self.styles['TH']),
                Paragraph('HSN/SAC', self.styles['TH']),
                Paragraph('Qty', self.styles['TH']),
                Paragraph('Rate (Rs.)', self.styles['TH']),
                Paragraph('Unit', self.styles['TH']),
                Paragraph('CGST<br/>%', self.styles['TH']),
                Paragraph('SGST<br/>%', self.styles['TH']),
                Paragraph('Amount (Rs.)', self.styles['TH']),
            ]
            col_widths = [0.35*inch, 2.50*inch, 0.75*inch, 0.55*inch, 0.75*inch, 0.50*inch, 0.55*inch, 0.55*inch, 1.00*inch]

        table_data = [headers]

        total_qty = 0
        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_igst = 0

        for idx, item in enumerate(items, 1):
            product_name = self.safe_str(item.get('product_name') or item.get('item_description', ''))
            desc = f"<b>{product_name}</b>"
            if item.get('description'):
                desc += f"<br/><font size=\"6.5\" color=\"#64748B\">{item.get('description')}</font>"

            qty = float(item.get('quantity', 0))
            rate = float(item.get('unit_price', 0))
            tax_rate = float(item.get('tax_rate', 0))
            taxable_amt = qty * rate
            unit = self.safe_str(item.get('unit') or 'Nos')

            cgst_amt = float(item.get('cgst_amount', 0))
            sgst_amt = float(item.get('sgst_amount', 0))
            igst_amt = float(item.get('igst_amount', 0))

            total_qty += qty
            total_taxable += taxable_amt
            total_cgst += cgst_amt
            total_sgst += sgst_amt
            total_igst += igst_amt

            row = [
                Paragraph(str(idx), self.styles['TCellCenter']),
                Paragraph(desc, self.styles['TCell']),
                Paragraph(self.safe_str(item.get('hsn_code')), self.styles['TCellCenter']),
                Paragraph(f"{qty:g}", self.styles['TCellCenter']),
                Paragraph(f"{rate:,.2f}", self.styles['TCellRight']),
                Paragraph(unit, self.styles['TCellCenter']),
            ]

            if is_interstate:
                row.extend([
                    Paragraph(f"{tax_rate:g}%", self.styles['TCellCenter']),
                    Paragraph(f"{taxable_amt:,.2f}", self.styles['TCellRight'])
                ])
            else:
                half_rate = tax_rate / 2
                row.extend([
                    Paragraph(f"{half_rate:g}%", self.styles['TCellCenter']),
                    Paragraph(f"{half_rate:g}%", self.styles['TCellCenter']),
                    Paragraph(f"{taxable_amt:,.2f}", self.styles['TCellRight'])
                ])

            table_data.append(row)

        # Pad empty rows to cover the full A4 page on single-page challans
        if len(items) <= 12:
            extra_lines = sum(1 for item in items if item.get('description'))
            target_rows = max(len(items), 14 - extra_lines)
            while (len(table_data) - 1) < target_rows:
                table_data.append([''] * len(headers))

        # Totals / Subtotal row
        if is_interstate:
            total_row = [
                '',
                Paragraph("<b>Total</b>", self.styles['TCellBoldRight']),
                '',
                Paragraph(f"<b>{total_qty:g}</b>", self.styles['TCellBoldCenter']),
                '',
                '',
                '',
                Paragraph(f"<b>Rs. {total_taxable:,.2f}</b>", self.styles['TCellBoldRight']),
            ]
        else:
            total_row = [
                '',
                Paragraph("<b>Total</b>", self.styles['TCellBoldRight']),
                '',
                Paragraph(f"<b>{total_qty:g}</b>", self.styles['TCellBoldCenter']),
                '',
                '',
                '',
                '',
                Paragraph(f"<b>Rs. {total_taxable:,.2f}</b>", self.styles['TCellBoldRight']),
            ]
        table_data.append(total_row)

        item_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -2), 0.5, self.border_subtle),
            ('BOX', (0, 0), (-1, -1), 1, self.primary_color),
            ('TOPPADDING', (0, 1), (-1, -2), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, self.primary_color),
            ('TOPPADDING', (0, -1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 4),
        ]

        # Alternating row background for data rows
        for r_idx in range(1, len(table_data) - 1):
            bg = colors.white if r_idx % 2 == 1 else self.bg_light
            style_cmds.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg))

        item_table.setStyle(TableStyle(style_cmds))
        story.append(item_table)
        story.append(Spacer(1, 5))

        # ==============================================================================
        # 5. UNIFIED SUMMARY: Amount in Words (Left) + Tax Calculation (Right)
        # ==============================================================================
        taxable_val = float(totals.get('taxable_amount', total_taxable))
        cgst_val = float(totals.get('cgst_amount', total_cgst))
        sgst_val = float(totals.get('sgst_amount', total_sgst))
        igst_val = float(totals.get('igst_amount', total_igst))
        tax_val = float(totals.get('tax_amount', cgst_val + sgst_val + igst_val))
        grand_total_val = float(totals.get('grand_total', taxable_val + tax_val))

        amt_words = data.get('amount_in_words') or self.format_currency_words(grand_total_val)

        # Left sub-panel: Amount in words & Delivery conditions
        left_box_data = [
            [Paragraph("AMOUNT IN WORDS", self.styles['WordsLabel'])],
            [Paragraph(f"<b>{amt_words}</b>", self.styles['WordsText'])],
            [Spacer(1, 4)],
            [Paragraph("TERMS & CONDITIONS:", self.styles['TermsLabel'])],
            [Paragraph("1. Goods received in good condition. Not for resale.<br/>2. Delivery challan issued under Rule 55 of CGST Rules, 2017.<br/>3. Verify materials and quantity immediately upon receipt.", self.styles['TermsText'])],
        ]
        left_sub_tbl = Table(left_box_data, colWidths=[4.1*inch])
        left_sub_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        # Right sub-panel: Tax breakdown
        tax_rows = [
            [Paragraph("Taxable Amount:", self.styles['TaxLabel']), Paragraph(f"Rs. {taxable_val:,.2f}", self.styles['TaxVal'])],
        ]
        if is_interstate:
            tax_rows.append([Paragraph("IGST:", self.styles['TaxLabel']), Paragraph(f"Rs. {igst_val:,.2f}", self.styles['TaxVal'])])
        else:
            tax_rows.append([Paragraph("CGST:", self.styles['TaxLabel']), Paragraph(f"Rs. {cgst_val:,.2f}", self.styles['TaxVal'])])
            tax_rows.append([Paragraph("SGST:", self.styles['TaxLabel']), Paragraph(f"Rs. {sgst_val:,.2f}", self.styles['TaxVal'])])

        tax_rows.append([Paragraph("Total Tax Amount:", self.styles['TaxLabel']), Paragraph(f"Rs. {tax_val:,.2f}", self.styles['TaxVal'])])
        tax_rows.append([Paragraph("<b>Grand Total:</b>", self.styles['GrandLabel']), Paragraph(f"<b>Rs. {grand_total_val:,.2f}</b>", self.styles['GrandVal'])])

        tax_sub_tbl = Table(tax_rows, colWidths=[1.8*inch, 1.4*inch])
        tax_sub_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -2), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 2),
            ('LINEABOVE', (0, -1), (-1, -1), 1, self.primary_color),
            ('BACKGROUND', (0, -1), (-1, -1), self.primary_light),
            ('TOPPADDING', (0, -1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        summary_data = [[left_sub_tbl, tax_sub_tbl]]
        summary_table = Table(summary_data, colWidths=[4.3*inch, 3.2*inch])
        summary_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, self.border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), self.bg_light),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 6))

        # ==============================================================================
        # 6. SIGNATURES & AUTHORIZATION
        # ==============================================================================
        company_sign_name = self.safe_str(company.get('name', 'COMPANY NAME'))

        left_sign = [
            [Paragraph("Receiver's Acknowledgement", self.styles['SignHeader'])],
            [Paragraph("Received above mentioned goods in good order and full quantity.", self.styles['SignSub'])],
            [Spacer(1, 32)],
            [Paragraph("Date: _________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Receiver's Signature & Seal", self.styles['SignFootLeft'])],
        ]
        left_sign_tbl = Table(left_sign, colWidths=[3.55*inch])
        left_sign_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        right_sign = [
            [Paragraph(f"For {company_sign_name}", self.styles['SignHeader'])],
            [Paragraph("Authorized Supplier / Consignor", self.styles['SignSub'])],
            [Spacer(1, 32)],
            [Paragraph("Authorised Signatory", self.styles['SignFootRight'])],
        ]
        right_sign_tbl = Table(right_sign, colWidths=[3.55*inch])
        right_sign_tbl.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        sign_data = [[left_sign_tbl, right_sign_tbl]]
        sign_table = Table(sign_data, colWidths=[3.75*inch, 3.75*inch])
        sign_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, self.border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), self.bg_light),
            ('BACKGROUND', (1, 0), (1, 0), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(sign_table)
        story.append(Spacer(1, 4))

        # ==============================================================================
        # 7. DOCUMENT FOOTNOTE
        # ==============================================================================
        story.append(Paragraph("This is a Computer Generated Delivery Challan • Generated by Accounting Software", self.styles['FootNote']))

        doc.build(story)
        return filepath