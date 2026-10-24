import os
import re
from pathlib import Path
import json

base_dir = Path("c:/Users/surjy/OneDrive/Desktop/Accounting Software")
app_ui_dir = base_dir / "app" / "ui"
app_services_dir = base_dir / "app" / "services"

audit = {
    "widgets_and_windows": [],
    "set_style_sheet": [],
    "hardcoded_colors": [],
    "hardcoded_fonts": [],
    "qpalette": [],
    "icons_and_emojis": [],
    "chart_colors": [],
    "table_colors": [],
    "status_colors": [],
    "export_colors": []
}

# Regex patterns
HEX_COLOR_RE = re.compile(r'#[0-9a-fA-F]{3,8}\b')
RGB_COLOR_RE = re.compile(r'rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+[^)]*\)')
QCOLOR_RE = re.compile(r'QColor\s*\([^)]*\)')
QBRUSH_RE = re.compile(r'QBrush\s*\([^)]*\)')
QT_COLOR_RE = re.compile(r'Qt\.(?:white|black|red|green|blue|gray|lightGray|darkGray|cyan|magenta|yellow|darkRed|darkGreen|darkBlue|darkCyan|darkMagenta|darkYellow)\b')
QFONT_RE = re.compile(r'QFont\s*\([^)]*\)')
FONT_CSS_RE = re.compile(r'font-(?:family|size|weight)\s*:\s*[^;"]+')
QPALETTE_RE = re.compile(r'QPalette\b')
EMOJI_RE = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]')
ICON_FILE_RE = re.compile(r'[\'"][^\'"]+\.(?:png|jpg|jpeg|svg|ico)[\'"]')

# 1. First audit app/ui for classes
for root, dirs, files in os.walk(app_ui_dir):
    for f in files:
        if f.endswith('.py'):
            p = Path(root) / f
            rel = p.relative_to(base_dir).as_posix()
            lines = p.read_text(encoding='utf-8').splitlines()
            for idx, line in enumerate(lines, 1):
                class_match = re.search(r'class\s+([A-Za-z0-9_]+)\s*\(([^)]+)\):', line)
                if class_match:
                    audit["widgets_and_windows"].append({
                        "file": rel,
                        "line": idx,
                        "name": class_match.group(1),
                        "bases": class_match.group(2)
                    })

# 2. Audit app/ui and app/services
all_files = list(app_ui_dir.rglob("*.py")) + list(app_services_dir.rglob("*.py"))
for p in all_files:
    rel = p.relative_to(base_dir).as_posix()
    is_ui = "app/ui" in rel
    is_service = "app/services" in rel
    lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
    for idx, line in enumerate(lines, 1):
        s_line = line.strip()
        # setStyleSheet
        if "setStyleSheet(" in line:
            audit["set_style_sheet"].append({"file": rel, "line": idx, "content": s_line})

        # Colors
        for m in HEX_COLOR_RE.finditer(line):
            col = m.group(0)
            target = audit["export_colors"] if is_service else audit["hardcoded_colors"]
            target.append({"file": rel, "line": idx, "match": col, "content": s_line})
        for m in RGB_COLOR_RE.finditer(line):
            col = m.group(0)
            target = audit["export_colors"] if is_service else audit["hardcoded_colors"]
            target.append({"file": rel, "line": idx, "match": col, "content": s_line})
        for m in QCOLOR_RE.finditer(line):
            col = m.group(0)
            target = audit["export_colors"] if is_service else audit["hardcoded_colors"]
            target.append({"file": rel, "line": idx, "match": col, "content": s_line})
        for m in QBRUSH_RE.finditer(line):
            col = m.group(0)
            target = audit["export_colors"] if is_service else audit["hardcoded_colors"]
            target.append({"file": rel, "line": idx, "match": col, "content": s_line})
        for m in QT_COLOR_RE.finditer(line):
            col = m.group(0)
            target = audit["export_colors"] if is_service else audit["hardcoded_colors"]
            target.append({"file": rel, "line": idx, "match": col, "content": s_line})

        # Fonts
        for m in QFONT_RE.finditer(line):
            audit["hardcoded_fonts"].append({"file": rel, "line": idx, "match": m.group(0), "content": s_line})
        for m in FONT_CSS_RE.finditer(line):
            if "theme.py" not in rel:
                audit["hardcoded_fonts"].append({"file": rel, "line": idx, "match": m.group(0), "content": s_line})

        # QPalette
        if QPALETTE_RE.search(line):
            audit["qpalette"].append({"file": rel, "line": idx, "content": s_line})

        # Icons / Emojis
        if is_ui:
            for m in EMOJI_RE.finditer(line):
                audit["icons_and_emojis"].append({"file": rel, "line": idx, "match": m.group(0), "content": s_line})
            for m in ICON_FILE_RE.finditer(line):
                audit["icons_and_emojis"].append({"file": rel, "line": idx, "match": m.group(0), "content": s_line})

        # Specific domains
        if "dashboard_view.py" in rel and ("paintEvent" in line or "QPainter" in line or "draw" in line or "pen" in line.lower() or "brush" in line.lower() or "#" in line):
            audit["chart_colors"].append({"file": rel, "line": idx, "content": s_line})

        if is_ui and ("setItem" in line or "setForeground" in line or "setBackground" in line or "TableWidget" in line or "TableView" in line):
            if any(k in line for k in ["QColor", "Qt.", "color", "badge", "HTML", "html", "style"]):
                audit["table_colors"].append({"file": rel, "line": idx, "content": s_line})

        if is_ui and any(k in line.lower() for k in ["paid", "unpaid", "overdue", "partial", "status", "draft", "cancelled"]):
            if any(k in line for k in ["QColor", "#", "badge", "color", "style", "Dr", "Cr"]):
                audit["status_colors"].append({"file": rel, "line": idx, "content": s_line})

out_file = base_dir / "scratch_audit_results.json"
out_file.write_text(json.dumps(audit, indent=2), encoding='utf-8')
print("Audit complete! Saved to", out_file)
print(f"Total widgets/windows: {len(audit['widgets_and_windows'])}")
print(f"Total setStyleSheet calls: {len(audit['set_style_sheet'])}")
print(f"Total hardcoded colors in UI: {len(audit['hardcoded_colors'])}")
print(f"Total hardcoded fonts in UI: {len(audit['hardcoded_fonts'])}")
print(f"Total QPalette usages: {len(audit['qpalette'])}")
print(f"Total icons/emojis: {len(audit['icons_and_emojis'])}")
print(f"Total chart color lines in dashboard: {len(audit['chart_colors'])}")
print(f"Total table color lines: {len(audit['table_colors'])}")
print(f"Total status color lines: {len(audit['status_colors'])}")
print(f"Total export color lines: {len(audit['export_colors'])}")
