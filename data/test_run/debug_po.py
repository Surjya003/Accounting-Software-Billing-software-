import sys
import app.services.pdf.templates.purchase_order as po
from app.services.pdf.core import adaptive_table
from tests.test_adaptive_item_font import _build_test_invoice
from reportlab.pdfbase import pdfmetrics

orig_build = po.build_adaptive_items_table
def debug_build(*args, **kwargs):
    specs = kwargs.get('item_specs') or args[1]
    widths = kwargs.get('col_widths') or args[2]
    reg_font, bold_font = adaptive_table.get_font_names()
    for fs in [10.25, 9.75, 9.5, 9.0, 8.75, 8.5]:
        print(f"=== fs = {fs} ===")
        for r_idx, row in enumerate(specs):
            for c_idx, cell in enumerate(row):
                usable_w = widths[c_idx] - 5.0
                fname = bold_font if cell.bold else reg_font
                text = adaptive_table.strip_tags(cell.content).strip()
                if c_idx == 2:
                    for w in text.split():
                        w_w = pdfmetrics.stringWidth(w, fname, fs)
                        if w_w > usable_w:
                            print(f"  Overflow desc word: r={r_idx} word='{w}' ({w_w:.1f} > {usable_w:.1f})")
                else:
                    w_str = pdfmetrics.stringWidth(text, fname, fs)
                    if w_str > usable_w:
                        print(f"  Overflow cell: r={r_idx} c={c_idx} (col_w={widths[c_idx]}) text='{text}' ({w_str:.1f} > {usable_w:.1f})")
    return orig_build(*args, **kwargs)

po.build_adaptive_items_table = debug_build
po._build_po_story(_build_test_invoice(3))
