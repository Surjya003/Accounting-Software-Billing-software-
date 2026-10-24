import app.services.pdf.templates.tax_invoice as ti
from app.services.pdf.core import adaptive_table
from reportlab.pdfbase import pdfmetrics

def debug_build(*args, **kwargs):
    specs = kwargs.get("item_specs") or args[1]
    widths = kwargs.get("col_widths") or args[2]
    reg_font, bold_font = adaptive_table.get_font_names()
    for fs in [11.25, 10.5, 9.5, 8.5]:
        print(f"=== Testing font size: {fs} ===")
        for row_idx, row in enumerate(specs):
            for col_idx, cell in enumerate(row):
                usable_w = widths[col_idx] - 5.0
                fname = bold_font if cell.bold else reg_font
                text = adaptive_table.strip_tags(cell.content).strip()
                if col_idx == 1:
                    for w in text.split():
                        w_w = pdfmetrics.stringWidth(w, fname, fs)
                        if w_w > usable_w:
                            print(f"Overflow desc: r={row_idx} word={w} w={w_w:.2f} usable={usable_w:.2f}")
                else:
                    w_str = pdfmetrics.stringWidth(text, fname, fs)
                    if w_str > usable_w:
                        print(f"Overflow: r={row_idx} col={col_idx} (col_w={widths[col_idx]}) text='{text}' str_w={w_str:.2f} usable={usable_w:.2f}")

ti.build_adaptive_items_table = debug_build
from tests.test_adaptive_item_font import _build_test_invoice
ti._build_tax_invoice_story(_build_test_invoice(3))
