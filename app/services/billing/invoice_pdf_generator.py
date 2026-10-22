from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from num2words import num2words
import os
import datetime

class InvoicePDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.primary_color = colors.black # Black for text as per image
        self.line_color = colors.black
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        # Main Title "Tax Invoice"
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=2
        ))
        
        # Company Name
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leading=12
        ))
        
        # Normal Text 8pt
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            leading=10,
            textColor=colors.black
        ))
        
        # Bold Text 8pt
        self.styles.add(ParagraphStyle(
            name='BoldText',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            leading=10,
            textColor=colors.black
        ))

        # Small Label (for field names like "Invoice No.")
        self.styles.add(ParagraphStyle(
            name='SmallLabel',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica',
            leading=8,
            textColor=colors.black
        ))

        # Table Header
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_CENTER
        ))
        
        # Table Cell Center
        self.styles.add(ParagraphStyle(
            name='TableCellCenter',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_CENTER,
            leading=10
        ))
        
        # Table Cell Right
        self.styles.add(ParagraphStyle(
            name='TableCellRight',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_RIGHT,
            leading=10
        ))

    def generate_invoice(self, data, filename=None):
        """Generate a Tax Invoice PDF matching the specific template"""
        if not filename:
            from app.config import EXPORTS_DIR
            import os
            filename = os.path.join(str(EXPORTS_DIR), f"invoice_{data.get('invoice_number', 'DRAFT')}.pdf")
        
        filepath = filename
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Margins: Narrower margins to fit content
        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                rightMargin=0.4*inch, leftMargin=0.4*inch,
                                topMargin=0.4*inch, bottomMargin=0.4*inch)
        
        story = []
        
        def safe_str(value, default=''):
            return str(value) if value is not None and str(value) != 'None' else default
        
        company = data.get('company') or {}
        customer = data.get('customer') or {}
        consignee = data.get('consignee') or {} # New Consignee Data
        logistics = data.get('logistics') or {} # New Logistics Data
        items = data.get('items') or []
        totals = data.get('totals') or {}
        
        # ==============================================================================
        # 1. TOP HEADER: Document Title and Subtitle
        # ==============================================================================
        doc_title = safe_str(data.get('document_title'), 'TAX INVOICE').upper()
        sub_title = safe_str(data.get('sub_title'), '(ORIGINAL FOR RECIPIENT)' if 'INVOICE' in doc_title else '(COMMERCIAL ESTIMATE)')
        
        title_data = [
            ['', Paragraph(doc_title, self.styles['MainTitle']), 
             Paragraph(sub_title, self.styles['SmallLabel'])]
        ]
        title_table = Table(title_data, colWidths=[2*inch, 3.5*inch, 2*inch])
        title_table.setStyle(TableStyle([
            ('ALIGN', (1,0), (1,0), 'CENTER'), # Center Title
            ('ALIGN', (2,0), (2,0), 'RIGHT'),  # Right align Original...
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(title_table)
        story.append(Spacer(1, 10))

        # ==============================================================================
        # 2. MAIN HEADER GRID (Company Info vs Invoice Details)
        # ==============================================================================
        
        # --- LEFT COLUMN CONTENT ---
        # Company Details
        company_details = [
            Paragraph(safe_str(company.get('name', 'YOUR COMPANY NAME')), self.styles['CompanyName']),
            Paragraph(safe_str(company.get('address')), self.styles['NormalText']),
            Paragraph(f"GSTIN/UIN: {safe_str(company.get('gstin', ''))}", self.styles['NormalText']),
            Paragraph(f"State Name: {safe_str(company.get('state', ''))}", self.styles['NormalText']),
            Paragraph(f"Contact: {safe_str(company.get('phone', ''))}", self.styles['NormalText']),
            Paragraph(f"E-Mail: {safe_str(company.get('email', ''))}", self.styles['NormalText']),
        ]
        
        # Consignee (Ship To)
        # Use specific consignee data if available, else fallback
        ship_name = consignee.get('name') or customer.get('name')
        ship_addr = consignee.get('address') or customer.get('shipping_address') or customer.get('address')
        ship_gstin = consignee.get('gstin') or customer.get('gstin', '')
        ship_state = consignee.get('state') or customer.get('state', '')

        consignee_details = [
            Paragraph("<b>Consignee (Ship to)</b>", self.styles['NormalText']),
            Paragraph(safe_str(ship_name), self.styles['BoldText']),
            Paragraph(safe_str(ship_addr), self.styles['NormalText']),
            Paragraph(f"GSTIN/UIN: {safe_str(ship_gstin)}", self.styles['NormalText']),
            Paragraph(f"State Name: {safe_str(ship_state)}", self.styles['NormalText']),
        ]

        # Buyer (Bill To)
        buyer_details = [
            Paragraph("<b>Buyer (Bill to)</b>", self.styles['NormalText']),
            Paragraph(safe_str(customer.get('name')), self.styles['BoldText']),
            Paragraph(safe_str(customer.get('address')), self.styles['NormalText']),
            Paragraph(f"GSTIN/UIN: {safe_str(customer.get('gstin', ''))}", self.styles['NormalText']),
            Paragraph(f"State Name: {safe_str(customer.get('state', ''))}", self.styles['NormalText']),
            Paragraph(f"Contact: {safe_str(customer.get('phone', ''))}", self.styles['NormalText']),
            Paragraph(f"E-Mail: {safe_str(customer.get('email', ''))}", self.styles['NormalText']),
        ]

        # Combine Left Column
        left_col_content = []
        left_col_content.extend(company_details)
        left_col_content.append(Spacer(1, 4))
        left_col_content.append(Paragraph("_" * 60, self.styles['NormalText'])) # Separator simulation
        left_col_content.append(Spacer(1, 4))
        left_col_content.extend(consignee_details)
        left_col_content.append(Spacer(1, 4))
        left_col_content.append(Paragraph("_" * 60, self.styles['NormalText']))
        left_col_content.append(Spacer(1, 4))
        left_col_content.extend(buyer_details)

        # --- RIGHT COLUMN CONTENT (Grid) ---
        # Helper for grid cells
        def grid_cell(label, value):
            return [Paragraph(label, self.styles['SmallLabel']), Paragraph(f"<b>{value}</b>", self.styles['NormalText'])]

        # Data for the right grid
        inv_no = data.get('invoice_number', '')
        inv_date = data.get('date', '')
        po_number = data.get('po_number', '')
        pi_number = data.get('pi_number', '')
        ref_number = data.get('reference_number', '')
        valid_until = data.get('valid_until', '')
        doc_no_label = data.get('doc_no_label') or ('Quotation No.' if 'QUOTATION' in doc_title else 'Invoice No.')
        
        second_row_left = grid_cell("Delivery Note", "")
        second_row_right = grid_cell("Mode/Terms of Payment", logistics.get('payment_terms', ''))
        if valid_until:
            second_row_left = grid_cell("Valid Until", valid_until)
        elif ref_number:
            second_row_left = grid_cell("Ref No.", ref_number)
        
        right_grid_data = [
            [grid_cell(doc_no_label, inv_no), grid_cell("Dated", inv_date)],
            [second_row_left, second_row_right],
            [grid_cell("PO Number", po_number), grid_cell("PI / Ref Number", pi_number or ref_number)],
            [grid_cell("Buyer's Order No.", logistics.get('buyer_order_no', '')), grid_cell("Dated", logistics.get('po_date', ''))],
            [grid_cell("Dispatch Doc No.", logistics.get('dispatch_doc_no', '')), grid_cell("Waybill / E-Way Bill No.", logistics.get('waybill_no', ''))],
            [grid_cell("Dispatched through", logistics.get('dispatched_through', '')), grid_cell("Destination", logistics.get('destination', ''))],
            [grid_cell("Terms of Delivery", logistics.get('terms_delivery', '')), ''] # Span
        ]

        # Create Right Grid Table
        right_grid = Table(right_grid_data, colWidths=[1.9*inch, 1.9*inch])
        right_grid.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (0,6), (1,6)), # Span Terms of Delivery
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))


        # Main Header Table (Left Content | Right Grid)
        header_data = [[left_col_content, right_grid]]
        header_table = Table(header_data, colWidths=[3.7*inch, 3.8*inch])
        header_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 6), # Padding for left col
            ('RIGHTPADDING', (0,0), (0,0), 6),
            ('TOPPADDING', (0,0), (0,0), 6),
            ('BOTTOMPADDING', (0,0), (0,0), 6),
            ('LEFTPADDING', (1,0), (1,0), 0), # No padding for right col container
            ('RIGHTPADDING', (1,0), (1,0), 0),
            ('TOPPADDING', (1,0), (1,0), 0),
            ('BOTTOMPADDING', (1,0), (1,0), 0),
        ]))
        story.append(header_table)

        # ==============================================================================
        # 3. ITEMS TABLE
        # ==============================================================================
        
        # Determine Tax Mode
        tax_mode = data.get('tax_mode', 'intra_state')  # Default to intra-state
        is_intra = (tax_mode == 'intra_state')
        
        # Conditional Table Headers based on Tax Mode
        if is_intra:
            # Intra-State: Show CGST and SGST columns
            headers = ['Sl\nNo.', 'Description of Goods', 'HSN/SAC', 'Quantity', 'Rate', 'per', 'CGST\n%', 'SGST\n%', 'Amount']
            col_widths = [0.3*inch, 2.2*inch, 0.7*inch, 0.6*inch, 0.8*inch, 0.4*inch, 0.5*inch, 0.5*inch, 1.0*inch]
        else:
            # Inter-State: Show IGST column
            headers = ['Sl\nNo.', 'Description of Goods', 'HSN/SAC', 'Quantity', 'Rate', 'per', 'IGST\n%', 'Amount']
            col_widths = [0.3*inch, 2.5*inch, 0.7*inch, 0.6*inch, 0.8*inch, 0.4*inch, 0.6*inch, 1.0*inch]
        
        table_data = [headers]
        
        total_qty = 0
        total_taxable = 0
        total_tax = 0  # Track total tax amount
        
        for idx, item in enumerate(items, 1):
            desc = f"<b>{safe_str(item.get('product_name'))}</b>"
            if item.get('description'):
                desc += f"<br/>{item.get('description')}"
            
            qty = item.get('quantity', 0)
            rate = item.get('unit_price', 0)
            tax_rate = item.get('tax_rate', 0)
            tax_amount = item.get('tax_amount', 0)
            
            # Calculate taxable amount (before tax)
            taxable_amt = qty * rate
            
            total_qty += qty
            total_taxable += taxable_amt
            total_tax += tax_amount
            
            # Build row with conditional tax columns
            row = [
                str(idx),
                Paragraph(desc, self.styles['NormalText']),
                safe_str(item.get('hsn_code')),
                f"{qty:.2f}",
                f"{rate:,.2f}",
                "Nos",  # Unit
            ]
            
            # Add tax columns based on mode
            if is_intra:
                # Intra-State: Split tax into CGST and SGST (50% each)
                half_tax_rate = tax_rate / 2
                row.extend([
                    f"{half_tax_rate}%",
                    f"{half_tax_rate}%",
                    f"{taxable_amt:,.2f}"
                ])
            else:
                # Inter-State: Full IGST
                row.extend([
                    f"{tax_rate}%",
                    f"{taxable_amt:,.2f}"
                ])
            
            table_data.append(row)
            
        # Fill empty rows to maintain height
        while len(table_data) < 10:
            table_data.append([''] * len(headers))
            
        # Total Row (conditional based on number of columns)
        grand_total_val = totals.get('grand_total', 0)
        if is_intra:
            # 9 columns: Sl No, Desc, HSN, Qty, Rate, per, CGST%, SGST%, Amount
            total_row = ['', 'Total', '', f"{total_qty:.2f}", '', '', '', '', f"Rs. {grand_total_val:,.2f}"]
        else:
            # 8 columns: Sl No, Desc, HSN, Qty, Rate, per, IGST%, Amount
            total_row = ['', 'Total', '', f"{total_qty:.2f}", '', '', '', f"Rs. {grand_total_val:,.2f}"]
        table_data.append(total_row)
        
        item_table = Table(table_data, colWidths=col_widths)
        item_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-2), 0.5, colors.black), # Grid for items
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),  # Box around whole table
            ('LINEBELOW', (0,-2), (-1,-2), 0.5, colors.black), # Line above Total
            
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'), # Sl No Center
            ('ALIGN', (2,0), (4,-1), 'CENTER'), # HSN to Qty Center
            ('ALIGN', (5,0), (5,-1), 'RIGHT'),  # Rate Right
            ('ALIGN', (6,0), (7,-1), 'CENTER'), # per, Disc Center
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT'), # Amount Right
            
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            
            # Total Row Styles
            ('ALIGN', (1,-1), (1,-1), 'RIGHT'), # "Total" label
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        story.append(item_table)
        
        # Amount in Words
        amt_words = data.get('amount_in_words', '')
        if not amt_words:
            try:
                amt_words = num2words(totals.get('grand_total', 0), lang='en_IN').title() + " Only"
            except:
                pass
                
        story.append(Paragraph(f"Amount Chargeable (in words)<br/><b>{amt_words}</b>", self.styles['NormalText']))
        story.append(Spacer(1, 4))
        
        # ==============================================================================
        # 4. TAX BREAKDOWN SECTION
        # ==============================================================================
        
        story.append(Spacer(1, 6))
        
        # Tax Details Table (Right-aligned)
        tax_details_data = [
            ['', 'Taxable Amount:', f"Rs. {total_taxable:,.2f}"],
        ]
        
        if is_intra:
            # Intra-State: Split tax into CGST and SGST
            half_tax = total_tax / 2
            tax_details_data.append(['', 'Total CGST:', f"Rs. {half_tax:,.2f}"])
            tax_details_data.append(['', 'Total SGST:', f"Rs. {half_tax:,.2f}"])
        else:
            # Inter-State: Full IGST
            tax_details_data.append(['', 'Total IGST:', f"Rs. {total_tax:,.2f}"])
        
        tax_details_data.append(['', 'Grand Total:', f"Rs. {grand_total_val:,.2f}"])
        
        tax_table = Table(tax_details_data, colWidths=[4*inch, 2*inch, 1.5*inch])
        tax_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(tax_table)
        story.append(Spacer(1, 10))


        
        # ==============================================================================
        # 5. FOOTER (Bank Details, Declaration, Signature)
        # ==============================================================================
        
        # Bank Details
        bank_details = []
        if company.get('bank_name') or company.get('account_no'):
            bank_details = [
                Paragraph("<b>Company's Bank Details</b>", self.styles['NormalText']),
                Paragraph(f"Bank Name   : <b>{safe_str(company.get('bank_name', ''))}</b>", self.styles['NormalText']),
                Paragraph(f"A/c No.     : <b>{safe_str(company.get('account_no', ''))}</b>", self.styles['NormalText']),
                Paragraph(f"Branch & IFS: <b>{safe_str(company.get('ifsc', ''))}</b>", self.styles['NormalText']),
            ]
        
        # Declaration
        decl_text = data.get('declaration')
        if not decl_text:
            if 'QUOTATION' in doc_title:
                decl_text = "We declare that this quotation shows the estimated price of the goods/services described. This quotation is subject to final acceptance and standard terms and conditions."
            else:
                decl_text = "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct. Goods once sold cannot be returned."

        declaration = [
            Paragraph("<b>Declaration</b>", self.styles['NormalText']),
            Paragraph(decl_text, self.styles['SmallLabel']),
        ]
        
        # Signature
        signature = [
            Paragraph(f"for <b>{safe_str(company.get('name', 'COMPANY NAME'))}</b>", self.styles['NormalText']),
            Spacer(1, 20),
            Paragraph("Authorised Signatory", self.styles['NormalText']),
        ]
        
        # Layout: Left (Bank + Decl) | Right (Signature)
        left_footer = []
        left_footer.extend(bank_details)
        left_footer.append(Spacer(1, 6))
        left_footer.extend(declaration)
        
        footer_data = [[left_footer, signature]]
        footer_table = Table(footer_data, colWidths=[4.5*inch, 3*inch])
        footer_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(footer_table)
        
        # Footer Note
        footer_note = data.get('footer_note') or ("This is a Computer Generated Quotation" if 'QUOTATION' in doc_title else "This is a Computer Generated Invoice")
        story.append(Paragraph(footer_note, ParagraphStyle('FooterNote', parent=self.styles['NormalText'], alignment=TA_CENTER)))

        doc.build(story)
        return filepath

    def generate_quotation(self, data, filename=None):
        """Generate a Quotation / Estimate PDF."""
        if not filename:
            from app.config import EXPORTS_DIR
            import os
            q_num = data.get('invoice_number', 'DRAFT').replace('/', '-')
            filename = os.path.join(str(EXPORTS_DIR), f"quotation_{q_num}.pdf")
        data['document_title'] = data.get('document_title') or "QUOTATION"
        data['doc_no_label'] = data.get('doc_no_label') or "Quotation No."
        data['sub_title'] = data.get('sub_title') or "(COMMERCIAL ESTIMATE)"
        return self.generate_invoice(data, filename=filename)


def generate_invoice_pdf(inv_data, comp_data=None, output_path=None):
    """
    Generate an invoice PDF from invoice dictionary and optional company profile dictionary.
    """
    generator = InvoicePDFGenerator()

    if comp_data is None:
        try:
            from app.database.connection import get_session
            from app.database.models import CompanyProfile
            with get_session() as session:
                comp = session.query(CompanyProfile).first()
                comp_data = comp.to_dict() if comp else {}
        except Exception:
            comp_data = {}

    company_info = {
        'name': comp_data.get('name', ''),
        'address': comp_data.get('address', ''),
        'gstin': comp_data.get('gstin', ''),
        'state': comp_data.get('state', ''),
        'phone': comp_data.get('phone', ''),
        'email': comp_data.get('email', ''),
        'bank_name': comp_data.get('bank_name', ''),
        'account_no': comp_data.get('bank_account_no', '') or comp_data.get('account_no', ''),
        'ifsc': comp_data.get('bank_ifsc', '') or comp_data.get('ifsc', ''),
    }

    is_interstate = inv_data.get('is_interstate', False)
    tax_mode_str = 'inter_state' if is_interstate else 'intra_state'

    pdf_data = {
        'invoice_number': inv_data.get('invoice_number', 'DRAFT'),
        'date': inv_data.get('invoice_date').strftime('%d-%m-%Y') if hasattr(inv_data.get('invoice_date'), 'strftime') else str(inv_data.get('invoice_date', '')),
        'tax_mode': tax_mode_str,
        'po_number': inv_data.get('po_number', ''),
        'pi_number': inv_data.get('pi_number', ''),
        'company': company_info,
        'customer': {
            'name': inv_data.get('party_name', ''),
            'address': inv_data.get('party_address', ''),
            'gstin': inv_data.get('party_gstin', ''),
            'state': inv_data.get('party_state', ''),
            'phone': inv_data.get('party_phone', '')
        },
        'logistics': {
            'dispatch_doc_no': inv_data.get('lr_no', ''),
            'waybill_no': inv_data.get('eway_bill_no', ''),
            'dispatched_through': inv_data.get('transporter_name', ''),
            'destination': inv_data.get('destination', ''),
            'payment_terms': '',
            'po_date': '',
            'buyer_order_no': inv_data.get('po_number', ''),
            'terms_delivery': ''
        },
        'consignee': {
            'address': inv_data.get('shipping_address', '')
        },
        'items': [],
        'totals': {
            'taxable_amount': float(inv_data.get('subtotal', 0)),
            'cgst_amount': float(inv_data.get('cgst_total', 0)),
            'sgst_amount': float(inv_data.get('sgst_total', 0)),
            'igst_amount': float(inv_data.get('igst_total', 0)),
            'grand_total': float(inv_data.get('total_amount', 0)),
        }
    }

    for item in inv_data.get('items', []):
        qty = float(item.get('quantity', 0))
        unit_price = float(item.get('unit_price', 0))
        gst_rate = float(item.get('gst_rate_pct', 0))
        cgst_amt = float(item.get('cgst_amount', 0))
        sgst_amt = float(item.get('sgst_amount', 0))
        igst_amt = float(item.get('igst_amount', 0))
        item_tax_amount = cgst_amt + sgst_amt + igst_amt

        pdf_data['items'].append({
            'product_name': item.get('item_description', '') or item.get('product_name', ''),
            'description': item.get('description', ''),
            'hsn_code': item.get('hsn_code', ''),
            'quantity': qty,
            'unit': item.get('unit', 'PCS'),
            'unit_price': unit_price,
            'tax_rate': gst_rate,
            'tax_amount': item_tax_amount,
        })

    return generator.generate_invoice(pdf_data, filename=output_path)

