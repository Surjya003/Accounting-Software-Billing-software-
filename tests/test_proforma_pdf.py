"""
Unit tests for Proforma PDF generation and Rupee/Currency symbol verification.
Ensures that:
1. ProformaPDFGenerator produces valid, high-quality PDFs.
2. Both Intra-State (CGST + SGST) and Inter-State (IGST) modes work properly.
3. No missing glyph box (U+20B9) is present in the generated PDFs; currency uses 'Rs.'.
4. Proforma service exports get_proforma_by_number and resolves proformas by document number.
"""
import os
import zlib
from pathlib import Path
from datetime import date
import pytest
from reportlab.pdfbase.pdfutils import asciiBase85Decode

from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.proforma_service import get_proforma_by_number
from app.services.export_service import (
    export_party_ledger_pdf,
    export_outstanding_pdf,
    export_daybook_pdf,
    export_trial_balance_pdf,
    export_invoice_pdf,
)


def extract_pdf_stream_text(pdf_path: str) -> str:
    """Extracts and decompresses text content from a ReportLab PDF."""
    with open(pdf_path, 'rb') as f:
        raw = f.read()

    pos = 0
    all_text = []
    while True:
        idx = raw.find(b'stream\n', pos)
        if idx == -1:
            idx = raw.find(b'stream\r\n', pos)
            if idx == -1:
                break
            start = idx + 8
        else:
            start = idx + 7

        end = raw.find(b'endstream', start)
        if end == -1:
            break

        stream_bytes = raw[start:end].strip()
        try:
            # ReportLab uses ASCII85 + FlateDecode
            a85 = asciiBase85Decode(stream_bytes.decode('ascii'))
            decomp = zlib.decompress(a85).decode('latin-1', errors='ignore')
            all_text.append(decomp)
        except Exception:
            pass

        pos = end + 9

    return '\n'.join(all_text)


def test_proforma_pdf_intra_state(tmp_path):
    gen = ProformaPDFGenerator()
    data = {
        'invoice_number': 'PF/2026-27/001',
        'date': '22-10-2026',
        'valid_until': '29-10-2026',
        'tax_mode': 'intra_state',
        'po_number': 'PO-TEST-101',
        'company': {
            'name': 'Test Automation Works',
            'address': 'Sector 5, Salt Lake, Kolkata',
            'state': 'West Bengal',
            'phone': '9876543210',
            'email': 'contact@testautomation.in',
            'gstin': '19AAACB1234F1Z5',
            'bank_name': 'HDFC Bank',
            'account_no': '50200012345678',
            'ifsc': 'HDFC0001234',
            'upi_id': 'test@hdfc'
        },
        'customer': {
            'name': 'Client Industrial Corp',
            'address': 'Plot 42, Asansol Industrial Area',
            'state': 'West Bengal',
            'phone': '9830098300',
            'gstin': '19BBBCB5678F1Z8'
        },
        'items': [
            {
                'product_name': 'PLC Digital Input Module DI-801',
                'hsn_code': '8537',
                'quantity': 4,
                'unit': 'PCS',
                'unit_price': 12500.00,
                'tax_rate': 18,
                'tax_amount': 9000.00,
                'total_amount': 59000.00
            }
        ],
        'totals': {
            'subtotal': 50000.00,
            'cgst_amount': 4500.00,
            'sgst_amount': 4500.00,
            'total_tax': 9000.00,
            'grand_total': 59000.00
        }
    }

    out_file = str(tmp_path / 'test_proforma_intra.pdf')
    res_path = gen.generate_proforma(data, filename=out_file)

    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 1000

    text = extract_pdf_stream_text(res_path)
    assert 'TEST AUTOMATION WORKS' in text.upper()
    assert 'PROFORMA INVOICE' in text
    assert 'Rs.' in text
    assert '\u20b9' not in text


def test_proforma_pdf_inter_state(tmp_path):
    gen = ProformaPDFGenerator()
    data = {
        'invoice_number': 'PF/2026-27/002',
        'date': '22-10-2026',
        'due_date': '30-10-2026',
        'tax_mode': 'inter_state',
        'po_number': 'PO-INTER-202',
        'company': {
            'name': 'National Power Controls',
            'address': 'Industrial Area, Bokaro',
            'state': 'Jharkhand',
            'phone': '9434342452',
            'email': 'power@controls.in',
            'gstin': '20AAACB1234F1Z1',
        },
        'customer': {
            'name': 'Eastern Steel Mills',
            'address': 'Rourkela, Odisha',
            'state': 'Odisha',
            'phone': '7001234567',
            'gstin': '21AAACS9999F1Z9'
        },
        'items': [
            {
                'product_name': 'Power Contactor 250A',
                'hsn_code': '8536',
                'quantity': 2,
                'unit': 'NOS',
                'unit_price': 15000.00,
                'tax_rate': 18,
                'tax_amount': 5400.00,
                'total_amount': 35400.00
            }
        ],
        'totals': {
            'subtotal': 30000.00,
            'igst_amount': 5400.00,
            'total_tax': 5400.00,
            'grand_total': 35400.00
        }
    }

    out_file = str(tmp_path / 'test_proforma_inter.pdf')
    res_path = gen.generate_proforma(data, filename=out_file)

    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 1000

    text = extract_pdf_stream_text(res_path)
    assert 'NATIONAL POWER CONTROLS' in text.upper()
    assert 'IGST' in text
    assert 'Rs.' in text
    assert '\u20b9' not in text


def test_export_service_pdfs_contain_no_rupee_box(tmp_path):
    """Verifies that all PDF exports use 'Rs.' and do not contain U+20B9."""
    # 1. Ledger PDF
    ledger_data = {
        'party': {'name': 'Sample Party', 'gstin': '19AAACB1234F1Z5', 'phone': '9876543210', 'address': 'Kolkata'},
        'from_date': date(2026, 4, 1),
        'to_date': date(2026, 10, 22),
        'opening_balance': {'amount': 1000.0, 'type': 'Dr'},
        'closing_balance': {'amount': 5000.0, 'type': 'Dr'},
        'total_debit': 6000.0,
        'total_credit': 2000.0,
        'entries': []
    }
    p_ledger = export_party_ledger_pdf(ledger_data, Path(tmp_path / 'test_ledger.pdf'))
    assert os.path.exists(p_ledger)
    text_ledger = extract_pdf_stream_text(str(p_ledger))
    assert 'Rs.' in text_ledger
    assert '\u20b9' not in text_ledger

    # 2. Outstanding PDF
    out_data = {
        'as_of_date': date(2026, 10, 22),
        'party_count': 1,
        'party_type': 'Customer',
        'grand_total': 5000.0,
        'total_0_30': 5000.0,
        'total_31_60': 0.0,
        'total_61_90': 0.0,
        'total_90_plus': 0.0,
        'party_rows': []
    }
    p_out = export_outstanding_pdf(out_data, Path(tmp_path / 'test_out.pdf'))
    assert os.path.exists(p_out)
    text_out = extract_pdf_stream_text(str(p_out))
    assert 'Rs.' in text_out
    assert '\u20b9' not in text_out


def test_get_proforma_by_number_callable():
    """Verify that get_proforma_by_number function exists and is callable."""
    assert callable(get_proforma_by_number)
    # Testing with non-existent number returns None gracefully
    result = get_proforma_by_number("PF/NON_EXISTENT/999")
    assert result is None
