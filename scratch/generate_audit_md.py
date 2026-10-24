import json
from collections import defaultdict
from pathlib import Path

data = json.loads(Path("scratch_audit_results.json").read_text(encoding="utf-8"))

output_lines = []

output_lines.append("# AUDIT REPORT: BILLFLOW SUITE UI/UX & STYLING")
output_lines.append("## 1. Inventory of Windows, Views, Dialogs, and Custom Widgets")
by_file = defaultdict(list)
for w in data["widgets_and_windows"]:
    by_file[w["file"]].append(f"`{w['name']}` ({w['bases']}) - line {w['line']}")

for f, wlist in sorted(by_file.items()):
    output_lines.append(f"\n### {f}")
    for w in wlist:
        output_lines.append(f"- {w}")

output_lines.append("\n## 2. Inline Stylesheet Calls (`setStyleSheet`)")
ss_by_file = defaultdict(list)
for s in data["set_style_sheet"]:
    ss_by_file[s["file"]].append((s["line"], s["content"]))

for f, slist in sorted(ss_by_file.items()):
    output_lines.append(f"\n### {f} ({len(slist)} calls)")
    for line, content in slist:
        output_lines.append(f"- Line {line}: `{content}`")

output_lines.append("\n## 3. Hardcoded Colors in UI (`#hex`, `rgb`, `QColor`, `QBrush`, `Qt.GlobalColor`)")
color_by_file = defaultdict(list)
for c in data["hardcoded_colors"]:
    color_by_file[c["file"]].append((c["line"], c["match"], c["content"]))

for f, clist in sorted(color_by_file.items(), key=lambda x: len(x[1]), reverse=True):
    output_lines.append(f"\n### {f} ({len(clist)} occurrences)")
    for line, match, content in clist:
        output_lines.append(f"- Line {line} [{match}]: `{content}`")

output_lines.append("\n## 4. Hardcoded Fonts (`QFont`, `font-family`, `font-size`)")
font_by_file = defaultdict(list)
for font in data["hardcoded_fonts"]:
    font_by_file[font["file"]].append((font["line"], font["match"], font["content"]))

for f, flist in sorted(font_by_file.items()):
    output_lines.append(f"\n### {f} ({len(flist)} occurrences)")
    for line, match, content in flist:
        output_lines.append(f"- Line {line} [{match}]: `{content}`")

output_lines.append("\n## 5. Icon Sources & Emojis Used as Icons")
icon_by_file = defaultdict(set)
for i in data["icons_and_emojis"]:
    icon_by_file[i["file"]].add((i["line"], repr(i["match"])))

for f, ilist in sorted(icon_by_file.items()):
    output_lines.append(f"\n### {f}")
    for line, match in sorted(ilist):
        output_lines.append(f"- Line {line}: {match}")

output_lines.append("\n## 6. Dashboard Charts & Custom Paint Colors")
for c in data["chart_colors"]:
    output_lines.append(f"- Line {c['line']}: `{c['content']}`")

output_lines.append("\n## 7. Export Colors (PDF & Excel Exports)")
export_by_file = defaultdict(list)
for e in data["export_colors"]:
    export_by_file[e["file"]].append((e["line"], e["match"], e["content"]))
for f, elist in sorted(export_by_file.items()):
    output_lines.append(f"\n### {f} ({len(elist)} occurrences)")
    for line, match, content in elist:
        output_lines.append(f"- Line {line} [{match}]: `{content}`")

Path("AUDIT_REPORT.md").write_text("\n".join(output_lines), encoding="utf-8")
print("AUDIT_REPORT.md written successfully!")
