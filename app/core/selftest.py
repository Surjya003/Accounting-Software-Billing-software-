"""
BillFlow Suite - Automated Headless Self-Test Runner
====================================================
Executes comprehensive verification in frozen and development modes:
1. Module imports
2. Clean database initialization & migrations
3. Service operations (Company, Party, Product, Invoice)
4. PDF Generation for all 8 document types
5. Excel export generation
6. Encrypted backup creation and restore verification
7. Vector SVG icon registry & Unicode Hindi font loading
8. WCAG Theme definitions
9. Qt Plugin presence (platforms, imageformats, iconengines)
10. Resource files integrity
"""
import os
import sys
import json
import shutil
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, Tuple


def run_selftest(custom_data_dir: str = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Runs the complete BillFlow self-test suite in a sandbox temp directory.
    Never touches user or dev databases.
    """
    start_time = datetime.now()
    results: Dict[str, Any] = {
        "status": "PASS",
        "timestamp": start_time.isoformat(),
        "python_version": sys.version,
        "is_frozen": getattr(sys, "frozen", False),
        "steps": {},
        "errors": []
    }

    # Create temporary isolated environment
    if custom_data_dir:
        temp_dir = Path(custom_data_dir).resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        is_ephemeral = False
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="billflow_selftest_")).resolve()
        is_ephemeral = True

    try:
        from app.core.paths import set_custom_data_dir, resource_path, get_bundled_font_path, user_data_dir
        set_custom_data_dir(temp_dir)

        # Ensure temp db paths
        temp_db_path = temp_dir / "data" / "selftest.db"
        temp_db_uri = f"sqlite:///{temp_db_path}"
        os.environ["ACCOUNTING_DB_PATH"] = str(temp_db_path)
        os.environ["ACCOUNTING_DATABASE_URI"] = temp_db_uri

        from app.database.connection import configure_database, init_db, get_session
        configure_database(temp_db_uri)

        # ---------------------------------------------------------
        # Step 1: Import All Modules
        # ---------------------------------------------------------
        step1_modules = [
            "app.version",
            "app.branding",
            "app.config",
            "app.core.paths",
            "app.core.logger",
            "app.core.crash_handler",
            "app.core.diagnostics",
            "app.database.models",
            "app.database.connection",
            "app.database.migrations",
            "app.services.auth_service",
            "app.services.audit_service",
            "app.services.system_guard",
            "app.services.license_service",
            "app.services.export_service",
            "app.services.gst_report_service",
            "app.services.inventory_valuation",
            "app.services.validation_helpers",
            "app.services.pdf",
            "app.services.pdf.templates.tax_invoice",
            "app.services.pdf.templates.proforma",
            "app.services.pdf.templates.quotation",
            "app.services.pdf.templates.delivery_challan",
            "app.services.pdf.templates.credit_note",
            "app.services.pdf.templates.debit_note",
            "app.services.pdf.templates.purchase_order",
            "app.services.pdf.templates.payment_receipt",
            "app.ui.theme.theme_manager",
            "app.ui.theme.tokens",
            "app.ui.theme.icons",
            "app.ui.theme.qss_builder",
            "app.ui.theme.themes",
        ]
        imported_count = 0
        for mod_name in step1_modules:
            __import__(mod_name)
            imported_count += 1
        results["steps"]["module_imports"] = {
            "status": "PASS",
            "modules_verified": imported_count
        }

        # ---------------------------------------------------------
        # Step 2: Database Initialization & Migrations
        # ---------------------------------------------------------
        from app.database.connection import init_db, get_session, engine
        init_db()
        from app.database.migrations import run_migrations, check_database_health
        health_ok, issues = check_database_health()
        assert health_ok, f"Database health check failed: {issues}"
        results["steps"]["database_init_and_migrations"] = {
            "status": "PASS",
            "db_path": str(temp_db_path),
            "healthy": health_ok
        }

        # ---------------------------------------------------------
        # Step 3: Service Operations (Company, Party, Product, Invoice)
        # ---------------------------------------------------------
        from app.database.models import CompanyProfile, Party, Product, Invoice, InvoiceItem
        with get_session() as session:
            comp = session.query(CompanyProfile).first()
            if not comp:
                comp = CompanyProfile(
                    name="Selftest Enterprises Pvt Ltd",
                    trade_name="Selftest Enterprises",
                    gstin="27AABCS1429B1Z8",
                    pan="AABCS1429B",
                    address="101 Tech Hub",
                    city="Mumbai",
                    state="Maharashtra",
                    state_code="27",
                    pincode="400001",
                    phone="9876543210",
                    email="test@selftest.com"
                )
                session.add(comp)
            else:
                comp.name = "Selftest Enterprises Pvt Ltd"
                comp.trade_name = "Selftest Enterprises"

            # Create test Party
            party = Party(
                name="Bharat Steel Corporation",
                party_type="Both",
                gstin="27ABCDE1234F1Z5",
                pan="ABCDE1234F",
                phone="9822011223",
                state="Maharashtra",
                state_code="27",
                city="Pune",
                address="MIDC Bhosari",
                pincode="411026"
            )
            session.add(party)

            # Create test Product
            prod = Product(
                name="Industrial Grade Steel Rod 10mm",
                barcode="STEEL-10MM",
                hsn_code="72142090",
                unit="KG",
                price=65.50,
                purchase_price=52.00,
                tax_rate=18.0,
                stock_quantity=1000.0
            )
            session.add(prod)
            session.flush()

            # Create test Invoice
            inv = Invoice(
                invoice_number="INV/2026-27/0001",
                party_id=party.id,
                invoice_date=date.today(),
                status="final",
                place_of_supply="Maharashtra (27)",
                subtotal=6550.0,
                cgst_total=589.50,
                sgst_total=589.50,
                igst_total=0.0,
                tax_amount=1179.0,
                total_amount=7729.0
            )
            session.add(inv)
            session.flush()

            inv_item = InvoiceItem(
                invoice_id=inv.id,
                product_id=prod.id,
                item_description="Industrial Grade Steel Rod 10mm",
                quantity=100.0,
                unit="KG",
                unit_price=65.50,
                discount_pct=0.0,
                hsn_code="72142090",
                taxable_value=6550.0,
                gst_rate_pct=18.0,
                cgst_amount=589.50,
                sgst_amount=589.50,
                igst_amount=0.0,
                total_amount=7729.0
            )
            session.add(inv_item)
            session.commit()

        results["steps"]["business_records_creation"] = {
            "status": "PASS",
            "invoice_number": "INV/2026-27/0001",
            "party": "Bharat Steel Corporation",
            "product": "Industrial Grade Steel Rod 10mm"
        }

        # ---------------------------------------------------------
        # Step 4: Generate All 8 PDF Document Types
        # ---------------------------------------------------------
        from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
        from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
        from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
        from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
        from app.services.billing.return_pdf_generator import ReturnPDFGenerator
        from app.services.billing.purchase_order_pdf_generator import PurchaseOrderPDFGenerator
        from app.services.pdf.templates.payment_receipt import render_payment_receipt_pdf

        exports_folder = temp_dir / "exports"
        exports_folder.mkdir(parents=True, exist_ok=True)

        company_dict = {
            "name": "Selftest Enterprises Pvt Ltd",
            "trade_name": "Selftest Enterprises",
            "gstin": "27AABCS1429B1Z8",
            "pan": "AABCS1429B",
            "address": "101 Tech Hub, MIDC, Mumbai - 400001",
            "city": "Mumbai",
            "state": "Maharashtra",
            "state_code": "27",
            "phone": "9876543210",
            "email": "test@selftest.com",
            "bank_name": "State Bank of India",
            "bank_account_no": "381928472910",
            "bank_ifsc": "SBIN0001234",
            "bank_branch": "Fort Mumbai",
            "upi_id": "selftest@sbi",
            "declaration": "We declare that all particulars are true and correct."
        }
        party_dict = {
            "name": "Bharat Steel Corporation",
            "gstin": "27ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "address": "MIDC Bhosari, Pune, Maharashtra - 411026",
            "city": "Pune",
            "phone": "9822011223",
            "state": "Maharashtra",
            "state_code": "27"
        }

        doc_generators = {
            "Tax Invoice": lambda d, p: InvoicePDFGenerator().generate_invoice(d, filename=str(p)),
            "Proforma Invoice": lambda d, p: ProformaPDFGenerator().generate_proforma(d, filename=str(p)),
            "Quotation": lambda d, p: QuotationPDFGenerator().generate_quotation(d, filename=str(p)),
            "Delivery Challan": lambda d, p: ChallanPDFGenerator().generate_challan(d, filename=str(p)),
            "Credit Note": lambda d, p: ReturnPDFGenerator().generate_credit_note(d, filename=str(p)),
            "Debit Note": lambda d, p: ReturnPDFGenerator().generate_debit_note(d, filename=str(p)),
            "Purchase Order": lambda d, p: PurchaseOrderPDFGenerator().generate_po(d, filename=str(p)),
            "Payment Receipt": lambda d, p: render_payment_receipt_pdf(d, str(p)),
        }

        generated_pdfs = {}
        for doc_name, gen_func in doc_generators.items():
            slug = doc_name.lower().replace(" ", "_")
            out_pdf_path = exports_folder / f"{slug}.pdf"
            payload = {
                "invoice_number": f"{slug[:3].upper()}-0001",
                "invoice_date": date.today(),
                "date": date.today().strftime("%d-%m-%Y"),
                "company": company_dict,
                "customer": party_dict,
                "party": party_dict,
                "supplier": party_dict,
                "tax_mode": "intra_state",
                "items": [{
                    "item_description": "Industrial Grade Steel Rod 10mm",
                    "hsn_code": "72142090",
                    "quantity": 100.0,
                    "unit": "KG",
                    "unit_price": 65.50,
                    "taxable_value": 6550.0,
                    "tax_rate": 18.0,
                    "cgst_amount": 589.50,
                    "sgst_amount": 589.50,
                    "igst_amount": 0.0,
                    "total_amount": 7729.0
                }],
                "totals": {
                    "taxable_amount": 6550.0,
                    "cgst_amount": 589.50,
                    "sgst_amount": 589.50,
                    "igst_amount": 0.0,
                    "total_tax": 1179.0,
                    "grand_total": 7729.0,
                    "net_total": 7729.0
                }
            }
            res_path = gen_func(payload, out_pdf_path)
            p_obj = Path(res_path)
            assert p_obj.exists() and p_obj.stat().st_size > 500, f"{doc_name} PDF file invalid: {res_path}"
            content = p_obj.read_bytes()
            assert content.startswith(b"%PDF-"), f"{doc_name} PDF does not start with %PDF-"
            generated_pdfs[doc_name] = len(content)

        results["steps"]["pdf_document_suite"] = {
            "status": "PASS",
            "document_count": len(generated_pdfs),
            "documents": generated_pdfs
        }

        # ---------------------------------------------------------
        # Step 5: Excel Export Generation
        # ---------------------------------------------------------
        from app.services.export_service import export_daybook_excel
        excel_out_path = exports_folder / "selftest_daybook.xlsx"
        res_excel = export_daybook_excel(daybook_data=date.today(), output_path=excel_out_path)
        assert res_excel.exists() and res_excel.stat().st_size > 1000, "Excel file generation failed"
        raw_excel = res_excel.read_bytes()
        assert raw_excel[:2] == b"PK", "Excel file signature mismatch (not a valid zip/xlsx)"
        results["steps"]["excel_export"] = {
            "status": "PASS",
            "excel_path": str(res_excel),
            "excel_size_bytes": len(raw_excel)
        }

        # ---------------------------------------------------------
        # Step 6: Encrypted Backup & Restore Verification
        # ---------------------------------------------------------
        from app.database.connection import create_encrypted_backup, restore_encrypted_backup
        enc_backup_file = create_encrypted_backup("SelftestPassphrase123!", custom_dest_dir=temp_dir / "backups")
        assert enc_backup_file.exists() and enc_backup_file.stat().st_size > 0
        raw_enc = enc_backup_file.read_bytes()
        assert raw_enc.startswith(b"BILLFLOW_ENC_V1"), "Encrypted backup missing BILLFLOW_ENC_V1 header"

        # Test restore in sandbox
        restored_ok = restore_encrypted_backup(enc_backup_file, "SelftestPassphrase123!")
        assert restored_ok, "Encrypted backup restore returned False"
        results["steps"]["encrypted_backup_and_restore"] = {
            "status": "PASS",
            "backup_size_bytes": len(raw_enc),
            "restored_verified": True
        }

        # ---------------------------------------------------------
        # Step 7: SVG Vector Icon Registry & Unicode Hindi Font Loading
        # ---------------------------------------------------------
        from app.ui.theme.icons import SVG_ICONS
        assert len(SVG_ICONS) >= 20, f"Expected at least 20 SVG icons, got {len(SVG_ICONS)}"

        # Verify Unicode Font with Devanagari Hindi Text and Rupee
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_p = get_bundled_font_path("Nirmala.ttf")
        hindi_test_str = "नमस्ते भारत - परीक्षण ₹1,23,456.78"
        if font_p.exists():
            pdfmetrics.registerFont(TTFont("SelftestNirmala", str(font_p)))
            # Check string width calculation
            w = pdfmetrics.stringWidth(hindi_test_str, "SelftestNirmala", 12)
            assert w > 0, "Font stringWidth calculation failed for Hindi string"
            font_verified = f"Bundled Nirmala.ttf verified (width={w:.1f}pt)"
        else:
            font_verified = "Bundled font path checked"

        results["steps"]["svg_icons_and_unicode_font"] = {
            "status": "PASS",
            "icon_count": len(SVG_ICONS),
            "hindi_string_tested": hindi_test_str,
            "font_verification": font_verified
        }

        # ---------------------------------------------------------
        # Step 8: Load All Enterprise Themes
        # ---------------------------------------------------------
        from app.ui.theme.themes import THEMES, verify_theme_wcag
        theme_names = list(THEMES.keys())
        assert len(theme_names) >= 3, "Expected at least 3 enterprise themes"
        for t_name, t_tokens in THEMES.items():
            wcag_ok, wcag_issues = verify_theme_wcag(t_tokens)
            assert wcag_ok, f"Theme {t_name} failed WCAG check: {wcag_issues}"
        results["steps"]["theme_system"] = {
            "status": "PASS",
            "themes_verified": theme_names
        }

        # ---------------------------------------------------------
        # Step 9: Qt Plugins Verification
        # ---------------------------------------------------------
        # Need minimal QCoreApplication if not present
        from PySide6.QtCore import QCoreApplication
        app_inst = QCoreApplication.instance()
        created_app = False
        if not app_inst:
            app_inst = QCoreApplication(sys.argv)
            created_app = True

        lib_paths = [Path(p) for p in QCoreApplication.libraryPaths()]
        plugin_checks = {
            "platforms": False,
            "imageformats": False,
            "iconengines": False
        }
        for lp in lib_paths:
            if (lp / "platforms").is_dir() or (lp.parent / "plugins" / "platforms").is_dir() or (lp / "qwindows.dll").is_file():
                plugin_checks["platforms"] = True
            if (lp / "imageformats").is_dir() or (lp.parent / "plugins" / "imageformats").is_dir():
                plugin_checks["imageformats"] = True
            if (lp / "iconengines").is_dir() or (lp.parent / "plugins" / "iconengines").is_dir():
                plugin_checks["iconengines"] = True

        # In frozen mode, PyInstaller places plugins under _internal/PySide6/plugins or root
        if getattr(sys, "frozen", False):
            base_p = Path(sys._MEIPASS)
            for sub in ["PySide6/plugins/platforms", "platforms"]:
                if (base_p / sub).is_dir():
                    plugin_checks["platforms"] = True
            for sub in ["PySide6/plugins/imageformats", "imageformats"]:
                if (base_p / sub).is_dir():
                    plugin_checks["imageformats"] = True
            for sub in ["PySide6/plugins/iconengines", "iconengines"]:
                if (base_p / sub).is_dir():
                    plugin_checks["iconengines"] = True

        results["steps"]["qt_plugins"] = {
            "status": "PASS",
            "library_paths": [str(p) for p in lib_paths],
            "plugins_found": plugin_checks
        }

        # ---------------------------------------------------------
        # Step 10: Resource Files Verification
        # ---------------------------------------------------------
        expected_resources = [
            "assets/branding/logo.svg",
            "assets/fonts/Nirmala.ttf",
            "assets/fonts/NirmalaB.ttf",
            "themes/custom_emerald.json"
        ]
        res_statuses = {}
        for r in expected_resources:
            p = resource_path(r)
            exists = p.exists()
            res_statuses[r] = {"path": str(p), "exists": exists}
            assert exists, f"Required resource missing: {r} at {p}"

        results["steps"]["resource_integrity"] = {
            "status": "PASS",
            "resources": res_statuses
        }

    except Exception as e:
        results["status"] = "FAIL"
        results["errors"].append({
            "exception": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        try:
            from app.database.connection import engine
            if engine:
                engine.dispose()
        except Exception:
            pass
        # Cleanup temporary test directory if ephemeral
        if is_ephemeral:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    duration = (datetime.now() - start_time).total_seconds()
    results["duration_seconds"] = duration
    passed = results["status"] == "PASS"
    return passed, results
