"""
BillFlow Suite - Core PDF Layout Engine: Flex Table & Continuous Columns
========================================================================
Implements a dynamic two-pass height calculation to stretch the items table
with filler rows and continuous vertical lines so that the table meets the pinned
footer block, ensuring zero blank band at the page bottom.
"""
from typing import List, Tuple, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Flowable

from app.services.pdf.core.page import FRAME_HEIGHT, FRAME_WIDTH


def calculate_filler_height(
    flowables_before_table: List[Flowable],
    items_table_initial: Table,
    flowables_after_table: List[Flowable],
    available_width: float = FRAME_WIDTH,
    available_height: float = FRAME_HEIGHT,
    min_filler: float = 12.0
) -> float:
    """
    Measures the vertical footprint of the document flowables.
    If the document fits on a single page, returns the exact filler row height
    needed to push the footer flowables to the bottom of the frame (within 10-12 mm of edge).
    For multi-page documents, computes remaining space on the final page.
    """
    h_before = 0.0
    for f in flowables_before_table:
        _, h = f.wrap(available_width, available_height)
        h_before += h

    _, h_table = items_table_initial.wrap(available_width, available_height)

    h_after = 0.0
    for f in flowables_after_table:
        _, h = f.wrap(available_width, available_height)
        h_after += h

    used_total = h_before + h_table + h_after
    
    # Check if single page
    if used_total <= available_height:
        spare = available_height - used_total
        # Subtract safety buffer (4.5 pt = ~1.6 mm) so filler row + table borders do not exceed available_height
        return max(spare - 4.5, 0.0)
    else:
        # Multi-page calculation: find remainder on final page
        # Note: ReportLab splits table across pages; estimate final page overflow
        effective_rem = used_total % available_height
        spare = available_height - effective_rem
        # Only add filler if it doesn't cause an accidental extra page break
        if spare > 20.0 and (effective_rem + min_filler) < available_height:
            return max(min(spare - 8.0, 150.0), 0.0)
        return 0.0


def build_stretched_table(
    header_data: List[List[Any]],
    item_rows: List[List[Any]],
    col_widths: List[float],
    base_style: List[Tuple],
    filler_height: float = 0.0,
    total_row_data: Optional[List[Any]] = None,
    total_row_style: Optional[List[Tuple]] = None
) -> Table:
    """
    Constructs an items table with:
    1. Header rows (repeatRows=1 on every page)
    2. Data rows
    3. An optional filler row with empty cells having continuous vertical grid lines
    4. Optional summary/total row pinned at the bottom of the table
    """
    table_data = []
    # 1. Header rows
    for h in header_data:
        table_data.append(h)

    # 2. Item rows
    for r in item_rows:
        table_data.append(r)

    row_heights = [None] * len(table_data)

    # 3. Filler row (if positive filler_height calculated)
    filler_row_idx = None
    if filler_height > 1.0:
        filler_row = [""] * len(col_widths)
        table_data.append(filler_row)
        row_heights.append(filler_height)
        filler_row_idx = len(table_data) - 1

    # 4. Total row
    total_row_idx = None
    if total_row_data:
        table_data.append(total_row_data)
        row_heights.append(None)
        total_row_idx = len(table_data) - 1

    # Combine styles
    combined_style = list(base_style)
    
    # Ensure vertical lines run through the filler row
    if filler_row_idx is not None:
        # Inner vertical lines on filler row
        combined_style.append(('INNERGRID', (0, filler_row_idx), (-1, filler_row_idx), 0.5, colors.HexColor("#CBD5E1")))
        combined_style.append(('BOX', (0, filler_row_idx), (-1, filler_row_idx), 0.5, colors.HexColor("#CBD5E1")))
        
    if total_row_idx is not None and total_row_style:
        combined_style.extend(total_row_style)

    tbl = Table(
        table_data,
        colWidths=col_widths,
        rowHeights=row_heights,
        repeatRows=len(header_data),
        style=TableStyle(combined_style)
    )
    return tbl
