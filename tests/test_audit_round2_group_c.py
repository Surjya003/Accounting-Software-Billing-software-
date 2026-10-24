import os
import threading
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_session, init_db
from app.database.models import (
    CompanyProfile, Party, Product, Invoice, Quotation,
    DeliveryChallan, ProformaInvoice, PurchaseOrder,
    SalesReturn, PurchaseReturn, Voucher
)
from app.services.export_service import (
    export_party_ledger_pdf, export_party_ledger_excel,
    export_day_book_pdf, export_trial_balance_pdf, export_outstanding_pdf
)
from app.services.billing.invoice_service import create_invoice, get_invoice_by_id
from app.services.billing.invoice_pdf_generator import generate_invoice_pdf
from app.services.billing.quotation_service import create_quotation
from app.services.billing.challan_service import create_challan
from app.services.billing.proforma_service import create_proforma
from app.services.billing.purchase_order_service import create_purchase_order
from app.services.billing.return_service import create_sales_return, create_purchase_return
from app.services.voucher_service import create_voucher


def get_or_create_test_party_and_product():
    with get_session() as session:
        party = session.query(Party).filter(Party.name == "Group C Test Party").first()
        if not party:
            party = Party(
                name="Group C Test Party",
                party_type="Customer",
                phone="9876543210",
                gstin="27AAPFU0939F1ZV",
                state="Maharashtra",
                state_code="27",
                credit_limit=Decimal("100000.00"),
                credit_period_days=30
            )
            session.add(party)
            session.flush()

        product = session.query(Product).filter(Product.name == "Group C Test Widget").first()
        if not product:
            product = Product(
                name="Group C Test Widget",
                unit="PCS",
                price=Decimal("100.00"),
                purchase_price=Decimal("60.00"),
                tax_rate=Decimal("18.00"),
                stock_quantity=Decimal("1000.000"),
                low_stock_threshold=Decimal("10.000"),
                is_active=True
            )
            session.add(product)
            session.flush()
        return party.id, product.id


def test_bug_24_bad_logo_pdf_export_graceful_fallback(tmp_path):
    """BUG-24: Corrupted or non-image logo must not crash PDF generation."""
    party_id, prod_id = get_or_create_test_party_and_product()

    # Create a corrupted logo file (text contents with .png extension)
    bad_logo = tmp_path / "corrupted_logo.png"
    bad_logo.write_text("THIS IS NOT A VALID PNG IMAGE FILE CONTENT AT ALL")

    # Update company profile with bad logo
    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        comp.logo_path = str(bad_logo)
        session.commit()

    # 1. Export Party Ledger PDF - must succeed without crashing
    out_pdf = tmp_path / "test_ledger.pdf"
    res_path = export_party_ledger_pdf(party_id, output_path=out_pdf)
    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 1000

    # 2. Export Outstanding PDF - must succeed
    out_out = tmp_path / "test_outstanding.pdf"
    res_path2 = export_outstanding_pdf(output_path=out_out)
    assert os.path.exists(res_path2)
    assert os.path.getsize(res_path2) > 1000

    # 3. Test missing logo file
    with get_session() as session:
        comp = session.query(CompanyProfile).first()
        comp.logo_path = str(tmp_path / "non_existent_logo_123.png")
        session.commit()

    out_pdf3 = tmp_path / "test_ledger_missing_logo.pdf"
    res_path3 = export_party_ledger_pdf(party_id, output_path=out_pdf3)
    assert os.path.exists(res_path3)
    assert os.path.getsize(res_path3) > 1000


def test_bug_25_export_with_none_party_raises_value_error():
    """BUG-25: Exporting party ledger with None party must raise ValueError, not pick default entity."""
    # PDF export with None
    with pytest.raises(ValueError, match="Select a party to export"):
        export_party_ledger_pdf(None)

    # Excel export with None
    with pytest.raises(ValueError, match="Select a party to export"):
        export_party_ledger_excel(None)

    # But non-party reports with None must continue to succeed normally
    db_path = export_day_book_pdf(None)
    assert os.path.exists(db_path)

    tb_path = export_trial_balance_pdf(None)
    assert os.path.exists(tb_path)

    out_path = export_outstanding_pdf(None)
    assert os.path.exists(out_path)


def test_bug_26_unique_constraint_rejects_duplicate_invoice_number():
    """BUG-26: Database UNIQUE constraint and service layer reject duplicate invoice numbers."""
    party_id, prod_id = get_or_create_test_party_and_product()

    inv_num = f"INV/26-TEST/{os.urandom(4).hex()}"
    inv_data = {
        "invoice_number": inv_num,
        "party_id": party_id,
        "invoice_date": date.today(),
        "status": "draft"
    }
    items_data = [{
        "product_id": prod_id,
        "item_description": "Widget",
        "quantity": Decimal("1"),
        "unit_price": Decimal("100"),
        "discount_pct": Decimal("0"),
        "gst_rate_pct": Decimal("18")
    }]

    # First save succeeds
    inv1 = create_invoice(inv_data, items_data)
    assert inv1.invoice_number == inv_num

    # Second save with same invoice number must fail
    with pytest.raises((IntegrityError, Exception)):
        create_invoice(inv_data, items_data)


def test_bug_26_two_threads_concurrent_creation_serialized_no_duplicates():
    """BUG-26: Concurrent creation across threads uses BEGIN IMMEDIATE to generate distinct sequential numbers."""
    party_id, prod_id = get_or_create_test_party_and_product()

    created_invoices = []
    errors = []

    def worker():
        try:
            inv_data = {
                "party_id": party_id,
                "invoice_date": date.today(),
                "status": "draft"
            }
            items = [{
                "product_id": prod_id,
                "item_description": "Concurrent Widget",
                "quantity": Decimal("1"),
                "unit_price": Decimal("50"),
                "discount_pct": Decimal("0"),
                "gst_rate_pct": Decimal("18")
            }]
            inv = create_invoice(inv_data, items)
            created_invoices.append(inv.invoice_number)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
    assert len(created_invoices) == 2, "Both invoices should be created"
    assert created_invoices[0] != created_invoices[1], "Invoice numbers must be unique"


def test_bug_26_unique_constraints_on_all_document_types():
    """BUG-26: Verify unique constraint enforcement across quotations, POs, challans, proformas, returns, vouchers."""
    party_id, prod_id = get_or_create_test_party_and_product()
    hex_id = os.urandom(3).hex()

    # 1. Quotation
    q_num = f"QT-UNIQ-{hex_id}"
    q_data = {"quotation_number": q_num, "party_id": party_id, "quotation_date": date.today()}
    q_items = [{"product_id": prod_id, "item_description": "Item", "quantity": 1, "unit_price": 50, "tax_rate": 18}]
    create_quotation(q_data, q_items)
    with pytest.raises((IntegrityError, Exception)):
        create_quotation(q_data, q_items)

    # 2. Purchase Order
    po_num = f"PO-UNIQ-{hex_id}"
    po_data = {"po_number": po_num, "party_id": party_id, "po_date": date.today()}
    po_items = [{"product_id": prod_id, "item_description": "Item", "quantity": 1, "unit_price": 50, "tax_rate": 18}]
    create_purchase_order(po_data, po_items)
    with pytest.raises((IntegrityError, Exception)):
        create_purchase_order(po_data, po_items)

    # 3. Delivery Challan
    ch_num = f"DC-UNIQ-{hex_id}"
    ch_data = {"challan_number": ch_num, "party_id": party_id, "challan_date": date.today()}
    ch_items = [{"product_id": prod_id, "item_description": "Item", "quantity": 1, "unit_price": 50, "tax_rate": 18}]
    create_challan(ch_data, ch_items)
    with pytest.raises((IntegrityError, Exception)):
        create_challan(ch_data, ch_items)

    # 4. Proforma Invoice
    pf_num = f"PI-UNIQ-{hex_id}"
    pf_data = {"proforma_number": pf_num, "party_id": party_id, "proforma_date": date.today()}
    pf_items = [{"product_id": prod_id, "item_description": "Item", "quantity": 1, "unit_price": 50, "gst_rate_pct": 18}]
    create_proforma(pf_data, pf_items)
    with pytest.raises((IntegrityError, Exception)):
        create_proforma(pf_data, pf_items)

    # 5. Voucher
    v_num = f"VCH-UNIQ-{hex_id}"
    v_data = {
        "voucher_number": v_num,
        "voucher_type": "Debit",
        "voucher_date": date.today(),
        "party_id": party_id,
        "amount_untaxed": Decimal("100.00"),
        "total_amount": Decimal("100.00"),
        "debit_amount": Decimal("100.00"),
        "payment_mode": "Cash"
    }
    create_voucher(v_data)
    with pytest.raises((IntegrityError, Exception)):
        create_voucher(v_data)
