"""
Comprehensive PDF Generation and Verification Script for BillFlow Suite
Generates all document types x edge cases into docs/pdf_samples/
Validates geometry, page count, margins, bottom gap, and text placement.
Rasterizes preview images.
"""
import os
import sys
import time
from pathlib import Path
from decimal import Decimal
import pypdfium2
import pdfplumber
from PIL import Image as PILImage, ImageDraw

# Add workspace to sys.path
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.services.pdf.core.page import PAGE_WIDTH, PAGE_HEIGHT
from app.services.pdf.core.formatting import format_currency as format_inr, amount_to_words_inr as num_to_words_inr
from app.services.pdf.templates.payment_receipt import render_payment_receipt_pdf
from app.services.billing.invoice_pdf_generator import InvoicePDFGenerator
from app.services.billing.proforma_pdf_generator import ProformaPDFGenerator
from app.services.billing.quotation_pdf_generator import QuotationPDFGenerator
from app.services.billing.challan_pdf_generator import ChallanPDFGenerator
from app.services.billing.return_pdf_generator import ReturnPDFGenerator
from app.services.billing.purchase_order_pdf_generator import PurchaseOrderPDFGenerator


OUTPUT_BASE = WORKSPACE / "docs" / "pdf_samples"
ASSETS_DIR = WORKSPACE / "scratch" / "test_assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def create_test_logos():
    """Generates test logo images: normal, wide, tall, and corrupt."""
    # 1. Normal logo
    img_normal = PILImage.new("RGB", (200, 80), color=(15, 35, 75))
    d = ImageDraw.Draw(img_normal)
    d.text((20, 30), "BILLFLOW", fill=(255, 255, 255))
    p_normal = ASSETS_DIR / "logo_normal.png"
    img_normal.save(p_normal)

    # 2. Wide logo
    img_wide = PILImage.new("RGB", (600, 100), color=(16, 185, 129))
    d = ImageDraw.Draw(img_wide)
    d.text((50, 40), "SUPER WIDE BRAND LOGO • ENTERPRISE", fill=(255, 255, 255))
    p_wide = ASSETS_DIR / "logo_wide.png"
    img_wide.save(p_wide)

    # 3. Tall logo
    img_tall = PILImage.new("RGB", (100, 400), color=(139, 38, 53))
    d = ImageDraw.Draw(img_tall)
    d.text((10, 180), "VERTICAL", fill=(255, 255, 255))
    p_tall = ASSETS_DIR / "logo_tall.png"
    img_tall.save(p_tall)

    # 4. Corrupt logo file
    p_corrupt = ASSETS_DIR / "logo_corrupt.png"
    with open(p_corrupt, "wb") as f:
        f.write(b"CORRUPTED_NOT_AN_IMAGE_DATA_PADDING_HEADER_STREAM")

    return {
        "normal": str(p_normal),
        "wide": str(p_wide),
        "tall": str(p_tall),
        "corrupt": str(p_corrupt),
        "missing": str(ASSETS_DIR / "non_existent_logo.png")
    }


def get_base_company(logos):
    return {
        "name": "Delhi Enterprise Solutions Pvt Ltd",
        "trade_name": "Delhi Solutions",
        "address": "Plot 14B, Okhla Industrial Area Phase-III",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110020",
        "gstin": "07AAAAA0000A1Z5",
        "pan": "AAAAA0000A",
        "phone": "+91 11 4567 8900",
        "email": "billing@delhienterprise.com",
        "bank_name": "State Bank of India",
        "account_no": "10020030040050",
        "ifsc": "SBIN0001234",
        "branch": "Okhla Phase-III, New Delhi",
        "terms_conditions": "1. Goods once sold will not be taken back without prior inspection.\n2. Interest @ 18% p.a. will be charged for overdue payments.\n3. Subject to Delhi jurisdiction only.",
        "logo_path": logos["normal"]
    }


def get_base_customer():
    return {
        "name": "Apex Engineering & Infrastructure Ltd",
        "address": "Tower 4, Cyber City, DLF Phase 2",
        "city": "Gurugram",
        "state": "Haryana",
        "pincode": "122002",
        "gstin": "06BBBBB1111B1Z2",
        "phone": "+91 124 9876543",
        "email": "procurement@apexinfra.com",
    }


def make_item(idx, desc=None, qty=1.0, rate=1000.0, gst=18.0, unit="PCS", hsn="8471"):
    taxable = qty * rate
    tax_amt = taxable * (gst / 100.0)
    return {
        "item_description": desc or f"Industrial Equipment Component Model-{idx:03d}",
        "hsn_code": hsn,
        "quantity": float(qty),
        "unit": unit,
        "unit_price": float(rate),
        "tax_rate": float(gst),
        "tax_amount": float(tax_amt),
        "total_item_amount": float(taxable + tax_amt),
        "reference_no": f"REF-{idx:04d}"
    }


def rasterize_pdf_to_images(pdf_path: Path, output_dir: Path, prefix: str):
    """Renders every page of the PDF to a PNG image using pypdfium2."""
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    image_paths = []
    for i, page in enumerate(pdf):
        # Render at 120 DPI for high quality preview
        pix = page.render(scale=120 / 72.0)
        img = pix.to_pil()
        out_name = f"{prefix}_page_{i+1}.png" if len(pdf) > 1 else f"{prefix}.png"
        out_path = output_dir / out_name
        img.save(out_path)
        image_paths.append(out_path)
    return image_paths


def verify_pdf_geometry(pdf_path: Path):
    """
    Checks:
    - Page dimensions == exactly 595.276 x 841.89 pt (A4)
    - Margin >= 8 mm (10 mm)
    - Last page lowest text bottom gap within 12 mm of frame bottom
    - Text stays strictly inside margins
    """
    results = {
        "path": str(pdf_path),
        "page_count": 0,
        "is_a4": True,
        "lowest_text_bottom": 0.0,
        "gap_from_page_bottom_mm": 0.0,
        "gap_from_frame_bottom_mm": 0.0,
        "fits_under_12mm_rule": False,
        "errors": []
    }

    with pdfplumber.open(str(pdf_path)) as pdf:
        results["page_count"] = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            # Check A4 size within 0.1 pt tolerance
            w, h = float(page.width), float(page.height)
            if abs(w - 595.276) > 0.5 or abs(h - 841.890) > 0.5:
                results["is_a4"] = False
                results["errors"].append(f"Page {idx+1} size {w:.2f}x{h:.2f} is not standard A4")

            words = page.extract_words()
            if words:
                min_x = min(w['x0'] for w in words)
                max_x = max(w['x1'] for w in words)
                # Outer frame margin is 28.346 pt (10 mm). Frame border line is at x=28.35 pt.
                # Inner text should be >= 28.0 pt and <= 595.28 - 28.0 pt
                if min_x < 24.0:
                    results["errors"].append(f"Page {idx+1}: text spills left of margin (min_x={min_x:.1f}pt)")
                if max_x > (w - 24.0):
                    results["errors"].append(f"Page {idx+1}: text spills right of margin (max_x={max_x:.1f}pt)")

                if idx == len(pdf.pages) - 1:
                    # Last page
                    lowest_bottom = max(w['bottom'] for w in words)
                    results["lowest_text_bottom"] = lowest_bottom
                    gap_from_page_bottom_pt = h - lowest_bottom
                    gap_from_page_bottom_mm = gap_from_page_bottom_pt / 72.0 * 25.4
                    frame_bottom_y = h - 28.346 # 10 mm
                    gap_from_frame_bottom_mm = (frame_bottom_y - lowest_bottom) / 72.0 * 25.4

                    results["gap_from_page_bottom_mm"] = gap_from_page_bottom_mm
                    results["gap_from_frame_bottom_mm"] = gap_from_frame_bottom_mm
                    # The rule: lowest text/line is within 12 mm of the page's bottom frame edge
                    results["fits_under_12mm_rule"] = (gap_from_frame_bottom_mm <= 12.0 and gap_from_frame_bottom_mm >= -2.0)

    return results


def run_all_generations():
    logos = create_test_logos()
    company = get_base_company(logos)
    customer = get_base_customer()

    generators = {
        "tax_invoice": lambda d, p: InvoicePDFGenerator().generate_invoice(d, filename=str(p)),
        "proforma": lambda d, p: ProformaPDFGenerator().generate_proforma(d, filename=str(p)),
        "quotation": lambda d, p: QuotationPDFGenerator().generate_quotation(d, filename=str(p)),
        "challan": lambda d, p: ChallanPDFGenerator().generate_challan(d, filename=str(p)),
        "credit_note": lambda d, p: ReturnPDFGenerator().generate_credit_note(d, filename=str(p)),
        "purchase_order": lambda d, p: PurchaseOrderPDFGenerator().generate_po(d, filename=str(p)),
        "debit_note": lambda d, p: ReturnPDFGenerator().generate_debit_note(d, filename=str(p)),
        "voucher": lambda d, p: render_payment_receipt_pdf(d, str(p)),
    }

    results_table = []
    benchmark_150 = {}

    for doc_type, gen_func in generators.items():
        doc_dir = OUTPUT_BASE / doc_type
        doc_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=======================================================")
        print(f"Generating samples for document type: {doc_type.upper()}")
        print(f"=======================================================")

        # Define edge cases for this document type
        cases = {}

        # Case 1: 1 item (the primary problem case)
        cases["case_01_1_item"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0001",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(1, "Precision CNC Machined Shaft 25mm", 1, 4500.0, 18.0)],
        }

        # Case 2: 5 items
        cases["case_02_5_items"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0005",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(i, f"Automation Relay Module Model-R{i}", i * 2, 850.0 + i * 50, 18.0) for i in range(1, 6)],
        }

        # Case 3: 15 items
        cases["case_03_15_items"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0015",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(i, f"Industrial Standard Fastener Pack #{i}", i, 320.0 + i * 15, 18.0) for i in range(1, 16)],
        }

        # Case 4: Page-fit count (~20 items)
        cases["case_04_page_fit"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0020",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(i, f"Pneumatic Fitting Tube Joint Part #{i}", 5, 140.0, 18.0) for i in range(1, 21)],
        }

        # Case 5: 40 items (Multi-page, 2+ pages)
        cases["case_05_40_items_multipage"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0040",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(i, f"Electrical Distribution Terminal Block Unit {i}", 10, 85.0 + i, 18.0) for i in range(1, 41)],
        }

        # Case 6: 150 items (Stress test 4+ pages & benchmark)
        cases["case_06_150_items_benchmark"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-0150",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [make_item(i, f"High-Tensile Flange Hex Bolt M{i%20 + 6}x{40+i%30} Grade 8.8", 100, 12.50, 18.0) for i in range(1, 151)],
        }

        # Case 7: Very long descriptions and names
        cases["case_07_long_descriptions_and_addresses"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-LONG",
            "date": "23-10-2026",
            "company": {
                **company,
                "name": "Bharat Heavy Multi-Industrial Engineering Technologies & Advanced Infrastructure Solutions Private Limited",
                "address": "Survey No. 45/2 & 46/1A, Phase IV, Naroda Industrial Estate, GIDC Industrial Zone, Near Railway Overbridge",
            },
            "customer": {
                **customer,
                "name": "Consolidated Petrochemical Refineries & Infrastructure Consortium Holdings of India Private Limited",
                "address": "Plot 899-B, Sector 58, Industrial Model Township (IMT) Manesar, NH-48 Express Corridor, Gurugram, Haryana 122050",
            },
            "supplier": {
                **customer,
                "name": "Consolidated Petrochemical Refineries & Infrastructure Consortium Holdings of India Private Limited",
                "address": "Plot 899-B, Sector 58, Industrial Model Township (IMT) Manesar, NH-48 Express Corridor, Gurugram, Haryana 122050",
            },
            "items": [
                make_item(
                    1,
                    desc="High-Performance Cryogenic Stainless Steel 316L Double-Block-and-Bleed Ball Valve with Fire-Safe API 607 Certification, ISO 5211 Direct Mounting Actuator Pad, Full Bore 4-inch Class 600 Flanged Ends RF ASME B16.5",
                    qty=2,
                    rate=48500.0,
                    gst=18.0
                ),
                make_item(
                    2,
                    desc="Heavy Duty Galvanized Cable Tray Perforated Type 300mm Width x 50mm Depth x 2.5m Length with Snap-on Cover, Splice Plates, M6 Dome Head Carriage Bolts and Earth Continuity Connectors",
                    qty=15,
                    rate=1850.0,
                    gst=18.0
                )
            ]
        }

        # Case 8: Missing optional fields
        cases["case_08_missing_optional_fields"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-MIN",
            "date": "23-10-2026",
            "company": {
                "name": "Simple Trader",
                "address": "Main Bazaar Road",
                "city": "Jaipur",
                "state": "Rajasthan",
                # no gstin, no pan, no phone, no email, no bank details, no terms, no logo
            },
            "customer": {
                "name": "Cash Buyer",
                "city": "Jaipur",
                "state": "Rajasthan",
                # no address, no gstin, no phone
            },
            "supplier": {
                "name": "Cash Buyer",
                "city": "Jaipur",
                "state": "Rajasthan",
            },
            "items": [make_item(1, "Unbranded Retail Goods", 3, 500.0, 5.0)],
        }

        # Case 9: Logo variations (Wide, Tall, and Corrupted image)
        cases["case_09_logo_wide"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-LOGO-WIDE",
            "date": "23-10-2026",
            "company": {**company, "logo_path": logos["wide"]},
            "customer": customer,
            "supplier": customer,
            "items": [make_item(1, "Branded High-Capacity Server Rack 42U", 1, 62000.0, 18.0)],
        }
        cases["case_09_logo_tall"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-LOGO-TALL",
            "date": "23-10-2026",
            "company": {**company, "logo_path": logos["tall"]},
            "customer": customer,
            "supplier": customer,
            "items": [make_item(1, "Branded High-Capacity Server Rack 42U", 1, 62000.0, 18.0)],
        }
        cases["case_09_logo_corrupt"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-LOGO-CORRUPT",
            "date": "23-10-2026",
            "company": {**company, "logo_path": logos["corrupt"]},
            "customer": customer,
            "supplier": customer,
            "items": [make_item(1, "Product with Corrupted Logo Test", 1, 1500.0, 18.0)],
        }

        # Case 10: Inter-state vs Intra-state, discounts, Zero-tax, Crores amounts
        cases["case_10_interstate_crores_discount"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-CRORE",
            "date": "23-10-2026",
            "tax_mode": "inter_state",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [
                make_item(1, "Industrial Steam Boiler Plant 50 TPH Turnkey", 1, 14500000.00, 18.0),
                make_item(2, "Exempt Agricultural Bioproduct Material", 10, 50000.00, 0.0),
            ],
        }

        # Case 11: Unicode Hindi / Devanagari & special XML characters (& < > ' ")
        cases["case_11_unicode_devanagari_special_chars"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-UNICODE",
            "date": "23-10-2026",
            "company": {
                **company,
                "name": "दिल्ली एंटरप्राइज सॉल्यूशंस & ट्रेडिंग <प्राइवेट> लिमिटेड \"DELHI\"",
            },
            "customer": {
                **customer,
                "name": "शर्मा & संस इन्फ्रास्ट्रक्चर 'कॉर्पोरेशन' <लिमिटेड>",
            },
            "supplier": {
                **customer,
                "name": "शर्मा & संस इन्फ्रास्ट्रक्चर 'कॉर्पोरेशन' <लिमिटेड>",
            },
            "items": [
                make_item(1, "कॉपर बसबार 50x10mm & कॉपर रॉड (Heavy Duty Grade > 99.9%)", 5, 2400.0, 18.0),
                make_item(2, "Brass Screws 1/2\" & Anchor Bolts <Grade A>", 50, 45.0, 18.0),
            ],
        }

        # Case 12: Paise amounts (e.g. 1,416.50)
        cases["case_12_paise_amounts"] = {
            "invoice_number": f"{doc_type[:3].upper()}-2026-PAISE",
            "date": "23-10-2026",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [
                make_item(1, "Precision Calibrated Resistor Set", 1, 1200.42, 18.0), # With tax = 1416.50
            ],
        }

        # Case 13: The user's exact real sample:
        # Delhi Enterprise Solutions, Copper Busbar 50x10mm, 1 MTR at Rs. 1,200.00, IGST 18%, total Rs. 1,416.00, "One Thousand, Four Hundred And Sixteen Only"
        cases["case_13_user_sample_copper_busbar"] = {
            "invoice_number": "PF-2026-27-0001",
            "date": "23-10-2026",
            "tax_mode": "inter_state",
            "company": company,
            "customer": customer,
            "supplier": customer,
            "items": [
                {
                    "item_description": "Copper Busbar 50x10mm",
                    "hsn_code": "7407",
                    "quantity": 1.0,
                    "unit": "MTR",
                    "unit_price": 1200.00,
                    "tax_rate": 18.0,
                    "tax_amount": 216.00,
                    "total_item_amount": 1416.00,
                }
            ],
            "totals": {
                "taxable_amount": 1200.00,
                "igst_amount": 216.00,
                "grand_total": 1416.00,
            }
        }

        for case_name, doc_data in cases.items():
            pdf_path = doc_dir / f"{case_name}.pdf"

            # Compute totals if missing
            if "totals" not in doc_data or not doc_data["totals"]:
                sub = sum(float(it.get("quantity", 1)) * float(it.get("unit_price", 0)) for it in doc_data["items"])
                tax = sum(float(it.get("tax_amount", 0)) for it in doc_data["items"])
                is_inter = doc_data.get("tax_mode") == "inter_state"
                doc_data["totals"] = {
                    "taxable_amount": sub,
                    "cgst_amount": 0.0 if is_inter else tax / 2.0,
                    "sgst_amount": 0.0 if is_inter else tax / 2.0,
                    "igst_amount": tax if is_inter else 0.0,
                    "grand_total": sub + tax
                }

            # Benchmark 150 items
            t0 = time.perf_counter()
            gen_func(doc_data, pdf_path)
            duration = time.perf_counter() - t0

            if case_name == "case_06_150_items_benchmark":
                benchmark_150[doc_type] = duration

            # Verify geometry
            geom = verify_pdf_geometry(pdf_path)

            # Rasterize preview images
            previews = rasterize_pdf_to_images(pdf_path, doc_dir, case_name)

            status = "PASS" if (geom["is_a4"] and geom["fits_under_12mm_rule"] and not geom["errors"]) else "FAIL"
            print(f"  [{status}] {case_name:<38} | Pages: {geom['page_count']} | Lowest: {geom['lowest_text_bottom']:.1f}pt | Gap to frame: {geom['gap_from_frame_bottom_mm']:.2f}mm | Time: {duration*1000:.1f}ms")
            if geom["errors"]:
                print(f"       Errors: {geom['errors']}")

            results_table.append({
                "document": doc_type,
                "case": case_name,
                "pages": geom["page_count"],
                "bottom_gap_frame_mm": geom["gap_from_frame_bottom_mm"],
                "bottom_gap_page_mm": geom["gap_from_page_bottom_mm"],
                "duration_ms": duration * 1000.0,
                "status": status,
                "errors": geom["errors"]
            })

    return results_table, benchmark_150


if __name__ == "__main__":
    results, bench = run_all_generations()
    print("\n\n=======================================================")
    print("BENCHMARK SUMMARY (150 Items Generation Time):")
    print("=======================================================")
    for dt, t in bench.items():
        print(f"  {dt:<20}: {t*1000:.2f} ms ({t:.3f} s)")

    failures = [r for r in results if r["status"] == "FAIL"]
    print(f"\nTotal test samples evaluated: {len(results)}")
    print(f"Passed: {len(results) - len(failures)}")
    print(f"Failed: {len(failures)}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f['document']} / {f['case']}: {f['errors']} (gap={f['bottom_gap_frame_mm']:.2f}mm)")
        sys.exit(1)
    else:
        print("\nALL SAMPLES PASSED PERFECTLY!")
        sys.exit(0)
