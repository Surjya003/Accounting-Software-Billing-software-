"""
BillFlow Suite - Core PDF Layout Engine: Page Geometry & Canvas
================================================================
Provides A4 dimensions, print margins, outer frame rendering, and two-pass NumberedCanvas.
"""
from typing import Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# Exactly A4 Portrait
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.2756 pt x 841.8898 pt (210 x 297 mm)

# Outer margin: Exactly 10.0 mm (strictly >= 8.0 mm safety rule)
PAGE_MARGIN_MM = 10.0
PAGE_MARGIN = PAGE_MARGIN_MM * mm  # ~28.346 pt

# Active printable outer frame coordinates
FRAME_X = PAGE_MARGIN
FRAME_Y = PAGE_MARGIN
FRAME_WIDTH = PAGE_WIDTH - (2 * PAGE_MARGIN)    # 538.5827 pt (~190 mm)
FRAME_HEIGHT = PAGE_HEIGHT - (2 * PAGE_MARGIN)  # 785.1969 pt (~277 mm)

# Outer border styling
FRAME_LINE_WIDTH = 0.8  # Standard Indian GST framed border thickness
COLOR_FRAME = colors.HexColor("#1E293B")  # Executive Slate 800


from reportlab.platypus import SimpleDocTemplate as _RLSimpleDocTemplate, PageTemplate, Frame, BaseDocTemplate
from reportlab.pdfgen import canvas

def _doNothing(canvas, doc):
    pass


class BillFlowDocTemplate(_RLSimpleDocTemplate):
    """
    Standardized A4 Billing Document Template.
    Enforces exact A4 page size, print-safe margins, zero frame padding, and NumberedCanvas.
    """
    def __init__(self, filename, **kwargs):
        kwargs.setdefault("pagesize", PAGE_SIZE)
        kwargs.setdefault("leftMargin", FRAME_X)
        kwargs.setdefault("rightMargin", FRAME_X)
        kwargs.setdefault("topMargin", FRAME_Y)
        kwargs.setdefault("bottomMargin", FRAME_Y)
        super().__init__(str(filename), **kwargs)

    def build(self, flowables, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=canvas.Canvas):
        self._calc()
        frameT = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height, id='normal',
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
        )
        self.addPageTemplates([
            PageTemplate(id='First', frames=frameT, onPage=onFirstPage, pagesize=self.pagesize),
            PageTemplate(id='Later', frames=frameT, onPage=onLaterPages, pagesize=self.pagesize)
        ])
        if onFirstPage is _doNothing and hasattr(self, 'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, 'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)


SimpleDocTemplate = BillFlowDocTemplate


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab Canvas that records all page drawings,
    determines the total page count Y, and draws clean running footers
    with 'Page X of Y' and outer border frames.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.watermark_text = None

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        """Draw outer border frame, watermark, running page numbers, and custom bottom line."""
        self.saveState()
        
        # 1. Outer Frame (clean rectangular border exactly 10 mm from page edges)
        self.setStrokeColor(COLOR_FRAME)
        self.setLineWidth(FRAME_LINE_WIDTH)
        self.rect(FRAME_X, FRAME_Y, FRAME_WIDTH, FRAME_HEIGHT, fill=0, stroke=1)

        # 2. Watermark / Status Stamp (if any)
        if self.watermark_text:
            self.saveState()
            self.setFont("Helvetica-Bold", 46)
            self.setFillColor(colors.HexColor("#E2E8F0"))
            self.translate(PAGE_WIDTH / 2.0, PAGE_HEIGHT / 2.0)
            self.rotate(45)
            self.drawCentredString(0, 0, str(self.watermark_text).upper())
            self.restoreState()
        
        # 3. Running Page Number: "Page X of Y" (bottom-right inside frame)
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawRightString(FRAME_X + FRAME_WIDTH - 6, FRAME_Y + 4, page_text)

        # 4. Continued on next page indicator on non-final pages
        if total_pages > 1 and self._pageNumber < total_pages:
            self.setFont("Helvetica-Oblique", 7.0)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(FRAME_X + 6, FRAME_Y + 4, "Continued on next page...")
        
        # 5. Optional Computer Generated Document / Invoice line (bottom-center inside frame)
        comp_gen_text = getattr(self, "_bottom_document_note", "This is a Computer Generated Document")
        if comp_gen_text:
            self.setFont("Helvetica", 7.0)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawCentredString(PAGE_WIDTH / 2.0, FRAME_Y + 4, comp_gen_text)
            
        self.restoreState()
