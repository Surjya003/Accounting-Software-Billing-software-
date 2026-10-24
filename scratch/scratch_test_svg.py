import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

app = QGuiApplication([])

svg_data = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect width="7" height="9" x="3" y="3" rx="1"/>
<rect width="7" height="5" x="14" y="3" rx="1"/>
<rect width="7" height="9" x="14" y="12" rx="1"/>
<rect width="7" height="5" x="3" y="16" rx="1"/>
</svg>"""

renderer = QSvgRenderer(QByteArray(svg_data.replace("currentColor", "#B45309").encode('utf-8')))
pixmap = QPixmap(24, 24)
pixmap.fill(Qt.transparent)
painter = QPainter(pixmap)
renderer.render(painter)
painter.end()

print("SVG rendering works! Pixmap size:", pixmap.size(), "isNull:", pixmap.isNull())
