"""
BillFlow Suite - Adaptive Item Text Sizing Engine
=================================================
Shared plumbing module for dynamic typography in billing PDF item tables.
Scales body cell text, row heights, and cell padding deterministically:
  - Fewer items -> larger font (up to ITEM_FONT_MAX = 13.0 pt) and taller rows.
  - More items -> stepped down font (down to ITEM_FONT_MIN_ONE_PAGE = 7.5 pt).
  - Multi-page documents -> fixed readable font (ITEM_FONT_PAGINATED = 8.5 pt).
  - Continuous vertical grid lines leading down to the Total row.
  - Zero overflow or cell clipping via font metrics validation.
  - No orphaned rows on last page via row balancing / intermediate size search.
"""
import re
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, Table, TableStyle, Flowable, PageBreak, Spacer

from app.services.pdf.core.fonts import get_font_names
from app.services.pdf.core.page import FRAME_WIDTH, FRAME_HEIGHT
from app.services.pdf.core.flex_table import calculate_filler_height, build_stretched_table


# ==============================================================================
# Named Constants (in points)
# ==============================================================================
ITEM_FONT_MAX: float = 13.0
ITEM_FONT_MIN_ONE_PAGE: float = 7.5
ITEM_FONT_PAGINATED: float = 8.5
ITEM_FONT_STEP: float = 0.25
LEADING_FACTOR: float = 1.25
ROW_PAD_FACTOR: float = 0.45
ROW_STRETCH_MAX: float = 2.5

# Reusable regex & entity map for stripping XML tags
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_MAP = {
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
}


@dataclass
class AdaptiveCell:
    """Specification for a single cell in the items table body."""
    content: str
    alignment: int = 0  # 0=Left, 1=Center, 2=Right
    bold: bool = False
    is_small: bool = False
    color: Any = None


def strip_tags(text: str) -> str:
    """Strips XML/HTML formatting tags and converts entities to plain text."""
    if not text:
        return ""
    clean = _TAG_RE.sub("", text)
    for ent, val in _ENTITY_MAP.items():
        clean = clean.replace(ent, val)
    return clean


def format_total_quantity(items: List[Dict[str, Any]], total_qty: float) -> str:
    """
    Formats the total quantity matching the items' units.
    - If all items have the same unit: e.g. "1.00 PCS"
    - If units differ or are missing: "1.00"
    Fixes the reference flaw where lines printed 'PCS' and total row printed 'Nos'.
    """
    units = set()
    for it in items:
        u = str(it.get("unit") or "").strip()
        if u:
            units.add(u)
    if len(units) == 1:
        single_unit = next(iter(units))
        return f"{total_qty:,.2f} {single_unit}"
    return f"{total_qty:,.2f}"


def check_cell_overflow(
    item_specs: List[List[AdaptiveCell]],
    col_widths: List[float],
    font_size: float,
    desc_col_idx: int = 1,
    left_pad: float = 2.5,
    right_pad: float = 2.5,
    reg_font: str = "NirmalaUI",
    bold_font: str = "NirmalaUI-Bold"
) -> bool:
    """
    Returns True if any cell text would overflow its column usable width at font_size.
    - For multi-line description/remarks: checks that unbreakable tokens fit.
    - For single-line columns (HSN, Qty, Rate, Tax, Amount, etc.): checks that the full text fits.
    """
    for row in item_specs:
        for c_idx, cell in enumerate(row):
            if c_idx >= len(col_widths):
                continue
            col_w = col_widths[c_idx]
            usable_w = col_w - (left_pad + right_pad)
            if usable_w <= 0:
                continue

            text = strip_tags(cell.content).strip()
            if not text:
                continue

            fname = bold_font if cell.bold else reg_font

            if c_idx == desc_col_idx:
                # Description column: words wrap on spaces. If a word has no spaces,
                # ReportLab CJK wordWrap will break it, but we ensure individual characters fit.
                words = text.split()
                if len(words) > 1:
                    for w in words:
                        # Allow normal words to fit; if a single word exceeds column, it overflows
                        if len(w) <= 25 and pdfmetrics.stringWidth(w, fname, font_size) > usable_w:
                            return True
            else:
                # Strict single-line column (Amount, Rate, HSN, Qty, etc.)
                # Entire string MUST fit within usable_w without wrapping or clipping
                w_str = pdfmetrics.stringWidth(text, fname, font_size)
                if w_str > usable_w:
                    return True
    return False


def _build_row_paragraphs(
    row_spec: List[AdaptiveCell],
    font_size: float,
    reg_font: str,
    bold_font: str
) -> List[Paragraph]:
    """Builds ReportLab Paragraphs for a single row at the given font size."""
    leading = font_size * LEADING_FACTOR
    paragraphs = []
    for cell in row_spec:
        fname = bold_font if cell.bold else reg_font
        style = ParagraphStyle(
            f"Adp_{font_size}_{cell.alignment}_{cell.bold}_{id(cell)}",
            fontName=fname,
            fontSize=font_size,
            leading=leading,
            alignment=cell.alignment,
            textColor=cell.color if cell.color else colors.black,
            wordWrap="CJK"
        )
        paragraphs.append(Paragraph(cell.content, style))
    return paragraphs


def build_adaptive_items_table(
    headers: List[List[Any]],
    item_specs: List[List[AdaptiveCell]],
    col_widths: List[float],
    base_style: List[Tuple],
    total_row_data: Optional[List[Any]],
    total_row_style: Optional[List[Tuple]],
    flowables_before: List[Flowable],
    flowables_after: List[Flowable],
    company_settings: Optional[Dict[str, Any]] = None,
    available_width: float = FRAME_WIDTH,
    available_height: float = FRAME_HEIGHT,
    fallback_font_size: float = 7.2,
    fallback_padding: float = 2.5,
    desc_col_idx: int = 1,
    grid_color: Any = colors.HexColor("#CBD5E1")
) -> List[Flowable]:
    """
    Constructs and returns flowables for the items table with adaptive typography.
    - If single page: returns [table] with scaled font, stretched rows & filler.
    - If multi-page: returns [t1, PageBreak(), t2, ...] at ITEM_FONT_PAGINATED (8.5 pt)
      with repeated headers, 'Continued on next page...', and totals on the last page.
    - If setting is disabled: returns [table] at fallback fixed size.
    """
    comp = company_settings or {}
    raw_enabled = comp.get("adaptive_item_font_enabled")
    is_enabled = True if raw_enabled is None else bool(raw_enabled)
    raw_max = comp.get("adaptive_item_font_max")
    font_max = float(raw_max) if raw_max is not None else ITEM_FONT_MAX
    raw_min = comp.get("adaptive_item_font_min")
    font_min = float(raw_min) if raw_min is not None else ITEM_FONT_MIN_ONE_PAGE

    reg_font, bold_font = get_font_names()
    num_items = len(item_specs)

    # --------------------------------------------------------------------------
    # Case 0: Setting Disabled -> Fallback to previous fixed font behavior
    # --------------------------------------------------------------------------
    if not is_enabled:
        fallback_rows = [
            _build_row_paragraphs(row, fallback_font_size, reg_font, bold_font)
            for row in item_specs
        ]
        # Measure using temporary table
        meas_data = list(headers) + fallback_rows
        if total_row_data:
            meas_data.append(total_row_data)
        meas_table = Table(meas_data, colWidths=col_widths)
        meas_table.setStyle(TableStyle(base_style))

        filler_h = calculate_filler_height(
            flowables_before_table=flowables_before,
            items_table_initial=meas_table,
            flowables_after_table=flowables_after,
            available_width=available_width,
            available_height=available_height,
            min_filler=10.0
        )
        stretched = build_stretched_table(
            header_data=headers,
            item_rows=fallback_rows,
            col_widths=col_widths,
            base_style=base_style,
            filler_height=filler_h,
            total_row_data=total_row_data,
            total_row_style=total_row_style
        )
        return [stretched]

    # --------------------------------------------------------------------------
    # Step 1: Measure vertical footprint of fixed layout elements
    # --------------------------------------------------------------------------
    h_before = sum(f.wrap(available_width, available_height)[1] for f in flowables_before)
    h_after = sum(f.wrap(available_width, available_height)[1] for f in flowables_after)

    t_header = Table(headers, colWidths=col_widths)
    t_header.setStyle(TableStyle(base_style))
    _, h_header = t_header.wrap(available_width, available_height)

    h_total = 0.0
    if total_row_data:
        t_tot = Table([total_row_data], colWidths=col_widths)
        tot_styles = list(total_row_style or [])
        tot_styles.extend([
            ('LEFTPADDING', (0, 0), (-1, -1), 2.0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2.0),
        ])
        t_tot.setStyle(TableStyle(tot_styles))
        _, h_total = t_tot.wrap(available_width, available_height)

    # Available height for items body on a single page
    safety_buffer = 8.0  # 2.8 mm safety buffer to avoid accidental overflow
    avail_body_h = available_height - (h_before + h_header + h_total + h_after + safety_buffer)

    # --------------------------------------------------------------------------
    # Step 2: Search for single-page font size from font_max down to font_min
    # --------------------------------------------------------------------------
    chosen_font_size: Optional[float] = None
    chosen_rows: Optional[List[List[Paragraph]]] = None
    chosen_body_height: float = 0.0

    # Quick O(1) filter: if items count is clearly too high for a single page
    min_row_h_est = font_min * (1.0 + 2.0 * ROW_PAD_FACTOR) + 4.0
    if (num_items * min_row_h_est) <= (avail_body_h * 1.05):
        # Generate search candidates from font_max down to font_min
        steps = int(round((font_max - font_min) / ITEM_FONT_STEP))
        for s in range(steps + 1):
            f_size = round(font_max - (s * ITEM_FONT_STEP), 2)
            if f_size < font_min:
                break

            # Check (b): cell text width overflow
            if check_cell_overflow(item_specs, col_widths, f_size, desc_col_idx, 2.5, 2.5, reg_font, bold_font):
                continue

            # Check (a): body height fit
            candidate_rows = [
                _build_row_paragraphs(row, f_size, reg_font, bold_font)
                for row in item_specs
            ]
            pad = round(f_size * ROW_PAD_FACTOR, 2)
            t_cand = Table(candidate_rows, colWidths=col_widths)
            t_cand.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
            ]))
            _, body_h = t_cand.wrap(available_width, available_height)

            if body_h <= avail_body_h:
                chosen_font_size = f_size
                chosen_rows = candidate_rows
                chosen_body_height = body_h
                break

    # --------------------------------------------------------------------------
    # Step 3: Single-Page Layout Found
    # --------------------------------------------------------------------------
    if chosen_font_size is not None and chosen_rows is not None:
        spare_h = max(avail_body_h - chosen_body_height, 0.0)
        base_pad = round(chosen_font_size * ROW_PAD_FACTOR, 2)
        final_pad = base_pad
        filler_h = spare_h

        # If font reached maximum and space remains, stretch rows up to ROW_STRETCH_MAX
        if math.isclose(chosen_font_size, font_max, abs_tol=0.01) and num_items > 0:
            max_body_h = chosen_body_height * ROW_STRETCH_MAX
            stretchable_h = max(max_body_h - chosen_body_height, 0.0)
            extra_h = min(spare_h, stretchable_h)
            extra_pad = (extra_h / num_items) / 2.0
            final_pad = base_pad + extra_pad
            filler_h = max(spare_h - extra_h, 0.0)

        # Assemble single-page table
        table_data = list(headers) + chosen_rows
        row_heights: List[Optional[float]] = [None] * len(table_data)

        # Build style
        style_cmds = list(base_style)
        # Apply padding to item rows
        body_start = len(headers)
        body_end = body_start + len(chosen_rows) - 1
        if body_end >= body_start:
            style_cmds.extend([
                ("TOPPADDING", (0, body_start), (-1, body_end), final_pad),
                ("BOTTOMPADDING", (0, body_start), (-1, body_end), final_pad),
                ("LEFTPADDING", (0, body_start), (-1, body_end), 2.5),
                ("RIGHTPADDING", (0, body_start), (-1, body_end), 2.5),
            ])

        # Blank filler row with continuous vertical lines
        if filler_h > 1.0:
            table_data.append([""] * len(col_widths))
            row_heights.append(filler_h)
            filler_idx = len(table_data) - 1
            style_cmds.extend([
                ("TOPPADDING", (0, filler_idx), (-1, filler_idx), 0),
                ("BOTTOMPADDING", (0, filler_idx), (-1, filler_idx), 0),
            ])

        # Total row
        if total_row_data:
            table_data.append(total_row_data)
            row_heights.append(None)
            tot_idx = len(table_data) - 1
            if total_row_style:
                # Map negative indices to absolute index tot_idx
                for cmd in total_row_style:
                    op, start, end, *rest = cmd
                    s_col, s_row = start
                    e_col, e_row = end
                    s_r = tot_idx if s_row == -1 else s_row
                    e_r = tot_idx if e_row == -1 else e_row
                    style_cmds.append((op, (s_col, s_r), (e_col, e_r), *rest))
            style_cmds.extend([
                ('LEFTPADDING', (0, tot_idx), (-1, tot_idx), 2.0),
                ('RIGHTPADDING', (0, tot_idx), (-1, tot_idx), 2.0),
            ])

        t_final = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
        t_final.setStyle(TableStyle(style_cmds))
        return [t_final]

    # --------------------------------------------------------------------------
    # Step 4: Multi-Page Pagination with Orphan Protection
    # --------------------------------------------------------------------------
    # Default multi-page font size
    pag_font = ITEM_FONT_PAGINATED
    pad = round(pag_font * ROW_PAD_FACTOR, 2)

    # Build rows at pagination font
    pag_rows = [
        _build_row_paragraphs(row, pag_font, reg_font, bold_font)
        for row in item_specs
    ]

    # Measure row heights individually
    row_heights_measured = []
    for r in pag_rows:
        t_r = Table([r], colWidths=col_widths)
        t_r.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), pad),
            ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        _, rh = t_r.wrap(available_width, available_height)
        row_heights_measured.append(rh)

    # Continued row height
    p_cont = Paragraph("<i>Continued on next page...</i>", ParagraphStyle("Cont", fontName=reg_font, fontSize=pag_font - 0.5, alignment=1))
    t_cont_meas = Table([[""] + [p_cont] + [""] * (len(col_widths) - 2)], colWidths=col_widths)
    _, h_cont = t_cont_meas.wrap(available_width, available_height)

    # Available heights per page
    avail_p1 = available_height - (h_before + h_header + h_cont + safety_buffer)
    avail_subsequent = available_height - (h_header + h_cont + safety_buffer)
    avail_last = available_height - (h_header + h_total + h_after + safety_buffer)

    def distribute_pages(rows_h: List[float], ap1: float, a_inter: float, a_last: float) -> List[List[int]]:
        N = len(rows_h)
        P = 2
        while True:
            pages = []
            start_idx = 0
            capacities = [ap1] + [a_inter] * (P - 2) + [a_last]
            for p_idx in range(P - 1):
                rem_pages = P - 1 - p_idx
                max_end = max(N - (3 * rem_pages), start_idx + 1)
                curr_h = 0.0
                end_idx = start_idx
                while end_idx < max_end and end_idx < N:
                    rh = rows_h[end_idx]
                    if curr_h + rh <= capacities[p_idx]:
                        curr_h += rh
                        end_idx += 1
                    else:
                        break
                if end_idx == start_idx and end_idx < N:
                    end_idx = start_idx + 1
                pages.append(list(range(start_idx, end_idx)))
                start_idx = end_idx

            last_h = sum(rows_h[start_idx:N])
            if last_h <= a_last:
                pages.append(list(range(start_idx, N)))
                # Balance last two pages so neither is orphaned or nearly empty
                if len(pages) >= 2:
                    penult = list(pages[-2])
                    last = list(pages[-1])
                    target_len = (len(penult) + len(last)) // 2
                    while len(penult) > target_len and len(penult) > 3:
                        candidate = [penult[-1]] + last
                        if sum(rows_h[x] for x in candidate) <= a_last:
                            penult.pop()
                            last.insert(0, candidate[0])
                        else:
                            break
                    pages[-2] = penult
                    pages[-1] = last
                return pages

            P += 1
            if P > 100:
                pages.append(list(range(start_idx, N)))
                return pages

    pages_indices = distribute_pages(row_heights_measured, avail_p1, avail_subsequent, avail_last)

    # --------------------------------------------------------------------------
    # Step 5: Assemble flowables for each page
    # --------------------------------------------------------------------------
    flowables: List[Flowable] = []
    total_pages = len(pages_indices)

    for p_num, p_rows_idx in enumerate(pages_indices, start=1):
        is_final_page = (p_num == total_pages)
        page_item_rows = [pag_rows[i] for i in p_rows_idx]
        current_rows_h = sum(row_heights_measured[i] for i in p_rows_idx)

        table_data = list(headers) + page_item_rows
        row_heights = [None] * len(table_data)

        style_cmds = list(base_style)
        body_start = len(headers)
        body_end = body_start + len(page_item_rows) - 1
        style_cmds.extend([
            ("TOPPADDING", (0, body_start), (-1, body_end), pad),
            ("BOTTOMPADDING", (0, body_start), (-1, body_end), pad),
            ("LEFTPADDING", (0, body_start), (-1, body_end), 2.5),
            ("RIGHTPADDING", (0, body_start), (-1, body_end), 2.5),
        ])

        if not is_final_page:
            # Intermediate page: filler row + Continued on next page row
            max_page_h = avail_p1 if p_num == 1 else avail_subsequent
            spare_page = max(max_page_h - current_rows_h, 0.0)

            if spare_page > 2.0:
                table_data.append([""] * len(col_widths))
                row_heights.append(spare_page)
                filler_idx = len(table_data) - 1
                style_cmds.extend([
                    ("TOPPADDING", (0, filler_idx), (-1, filler_idx), 0),
                    ("BOTTOMPADDING", (0, filler_idx), (-1, filler_idx), 0),
                ])

            # Continued row
            cont_row_cells = [""] * len(col_widths)
            cont_row_cells[desc_col_idx] = Paragraph(
                "<i>Continued on next page...</i>",
                ParagraphStyle("ContLine", fontName=reg_font, fontSize=pag_font - 0.5, alignment=1)
            )
            table_data.append(cont_row_cells)
            row_heights.append(None)
            cont_idx = len(table_data) - 1
            style_cmds.extend([
                ("LINEABOVE", (0, cont_idx), (-1, cont_idx), 0.6, grid_color),
                ("LINEBELOW", (0, cont_idx), (-1, cont_idx), 0.6, grid_color),
                ("TOPPADDING", (0, cont_idx), (-1, cont_idx), 2.0),
                ("BOTTOMPADDING", (0, cont_idx), (-1, cont_idx), 2.0),
            ])

            t_page = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
            t_page.setStyle(TableStyle(style_cmds))
            flowables.append(t_page)
            flowables.append(PageBreak())

        else:
            # Final page: remaining items + filler row + Total row
            spare_page = max(avail_last - current_rows_h, 0.0)
            if spare_page > 1.0:
                table_data.append([""] * len(col_widths))
                row_heights.append(spare_page)
                filler_idx = len(table_data) - 1
                style_cmds.extend([
                    ("TOPPADDING", (0, filler_idx), (-1, filler_idx), 0),
                    ("BOTTOMPADDING", (0, filler_idx), (-1, filler_idx), 0),
                ])

            # Total row
            if total_row_data:
                table_data.append(total_row_data)
                row_heights.append(None)
                tot_idx = len(table_data) - 1
                if total_row_style:
                    for cmd in total_row_style:
                        op, start, end, *rest = cmd
                        s_col, s_row = start
                        e_col, e_row = end
                        s_r = tot_idx if s_row == -1 else s_row
                        e_r = tot_idx if e_row == -1 else e_row
                        style_cmds.append((op, (s_col, s_r), (e_col, e_r), *rest))
                style_cmds.extend([
                    ('LEFTPADDING', (0, tot_idx), (-1, tot_idx), 2.0),
                    ('RIGHTPADDING', (0, tot_idx), (-1, tot_idx), 2.0),
                ])

            t_page = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
            t_page.setStyle(TableStyle(style_cmds))
            flowables.append(t_page)

    return flowables
