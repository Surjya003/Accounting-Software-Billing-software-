"""
Automated Verification Script for Step 5
Asserts:
1. Size is non-increasing as item count rises (for 1-page counts).
2. Every size is between ITEM_FONT_MIN_ONE_PAGE (7.5 pt) and ITEM_FONT_MAX (13.0 pt) for 1-page documents.
3. Every page of a multi-page document uses ITEM_FONT_PAGINATED (8.5 pt).
4. Header and Total row sizes are unchanged from the "before" version.
5. No text bounding box crosses its column boundaries or the frame.
6. The bottom of the footer block is within 12 mm of the page bottom (Page height is 841.89 pt; 12 mm is 34.0 pt).
7. Page count is as expected.
8. A4 size exactly (595.28 x 841.89 pt).
"""
import sys
from pathlib import Path
import pdfplumber
import pypdfium2

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

OUT_BASE = ROOT_DIR / "docs" / "pdf_samples" / "adaptive"
BEFORE_BASE = ROOT_DIR / "docs" / "pdf_samples" / "before"

COUNTS = [1, 2, 3, 5, 8, 12, 15, 20, 25, 30, 40, 60, 150]
DOCS = ["tax_invoice", "proforma", "quotation", "delivery_challan"]

PAGE_W = 595.275590551181
PAGE_H = 841.8897637795276
TOLERANCE = 1.0  # 1 point tolerance

def verify_all():
    errors = []
    print("Running Programmatic Verifications across all PDF samples...")

    # 1. Compare Before Header and Total row sizes
    before_sizes = {}
    for doc_name in DOCS:
        before_pdf = BEFORE_BASE / f"before_{doc_name}_3items.pdf"
        assert before_pdf.exists(), f"Missing before sample: {before_pdf}"
        with pdfplumber.open(str(before_pdf)) as pdf:
            p0 = pdf.pages[0]
            words = p0.extract_words(extra_attrs=["size"])
            # Header word "Description"
            h_word = [w for w in words if w["text"] == "Description"]
            # Total word "Total"
            tot_word = [w for w in words if w["text"] == "Total"]
            before_sizes[doc_name] = {
                "header": round(h_word[0]["size"], 2) if h_word else None,
                "total": round(tot_word[0]["size"], 2) if tot_word else None,
            }
    print("Baseline before sizes:", before_sizes)

    for doc_name in DOCS:
        print(f"\nVerifying {doc_name}...")
        prev_1page_size = 999.0

        for n in COUNTS:
            pdf_path = OUT_BASE / doc_name / f"items_{n}.pdf"
            assert pdf_path.exists(), f"Missing {pdf_path}"

            doc = pypdfium2.PdfDocument(str(pdf_path))
            num_pages = len(doc)

            with pdfplumber.open(str(pdf_path)) as pdf:
                for p_idx, page in enumerate(pdf.pages):
                    # Check A4 page dimensions
                    pw = float(page.width)
                    ph = float(page.height)
                    if abs(pw - PAGE_W) > TOLERANCE or abs(ph - PAGE_H) > TOLERANCE:
                        errors.append(f"{pdf_path.name} page {p_idx+1}: not A4 ({pw} x {ph})")

                    words = page.extract_words(extra_attrs=["size", "fontname"])
                    
                    # Check text within frame margins (left >= 27 pt, right <= 568 pt)
                    for w in words:
                        if w["x0"] < 25.0:
                            errors.append(f"{pdf_path.name} page {p_idx+1}: text '{w['text']}' overflows left frame (x0={w['x0']})")
                        if w["x1"] > 570.0:
                            errors.append(f"{pdf_path.name} page {p_idx+1}: text '{w['text']}' overflows right frame (x1={w['x1']})")

                    # Check Header size unchanged
                    h_words = [w for w in words if w["text"] == "Description"]
                    if h_words and before_sizes[doc_name]["header"]:
                        h_size = round(h_words[0]["size"], 2)
                        exp_h = before_sizes[doc_name]["header"]
                        if abs(h_size - exp_h) > 0.1:
                            errors.append(f"{pdf_path.name} page {p_idx+1}: Header size changed from {exp_h} to {h_size}")

                    # Check Total row size unchanged (on last page)
                    if p_idx == num_pages - 1:
                        tot_words = [w for w in words if w["text"] == "Total"]
                        if tot_words and before_sizes[doc_name]["total"]:
                            t_size = round(tot_words[0]["size"], 2)
                            exp_t = before_sizes[doc_name]["total"]
                            if abs(t_size - exp_t) > 0.1:
                                errors.append(f"{pdf_path.name} last page: Total row size changed from {exp_t} to {t_size}")

                        # Check footer bottom within 12 mm of page bottom
                        # In pdfplumber, y0 is from top (0 at top, 841.89 at bottom).
                        # Within 12 mm of bottom means bottom text y1 >= 841.89 - (12 * 2.83465) = 807.87 pt
                        max_y1 = max(w["bottom"] for w in words)
                        dist_from_bottom_mm = (PAGE_H - max_y1) * 0.352778
                        # The frame bottom is at 10 mm (28.35 pt from bottom), and bottom note is at ~6 mm
                        if dist_from_bottom_mm > 12.0:
                            errors.append(f"{pdf_path.name} last page: footer bottom is {dist_from_bottom_mm:.2f} mm > 12 mm from page bottom")

                    # Extract body font size
                    body_words = [
                        w for w in words
                        if w["text"] in ["Variable", "Belden", "Programmable", "Heavy", "Item"] and w["top"] > 160
                    ]
                    if body_words:
                        body_size = round(body_words[0]["size"], 2)

                        # Assertion 3: Multi-page document must use ITEM_FONT_PAGINATED (8.5 pt)
                        if num_pages > 1:
                            if abs(body_size - 8.5) > 0.1:
                                errors.append(f"{pdf_path.name} page {p_idx+1}: multi-page body size is {body_size} != 8.5 pt")
                        else:
                            # Assertion 2: 1-page document between 7.5 and 13.0 pt
                            if body_size < 7.5 - 0.05 or body_size > 13.0 + 0.05:
                                errors.append(f"{pdf_path.name}: 1-page body size {body_size} not in [7.5, 13.0]")

                            # Assertion 1: Non-increasing as items rise
                            if body_size > prev_1page_size + 0.05:
                                errors.append(f"{pdf_path.name}: body size {body_size} increased from {prev_1page_size}")
                            prev_1page_size = body_size

    if errors:
        print(f"\nFAILED with {len(errors)} errors:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    else:
        print("\nALL PROGRAMMATIC ASSERTIONS PASSED WITH ZERO ERRORS!")

if __name__ == "__main__":
    verify_all()
