import json
from collections import defaultdict
from pathlib import Path

data = json.loads(Path("scratch_audit_results.json").read_text(encoding="utf-8"))

print("=== WIDGETS AND WINDOWS IN APP/UI ===")
by_file = defaultdict(list)
for w in data["widgets_and_windows"]:
    by_file[w["file"]].append(f"{w['name']} ({w['bases']}) [line {w['line']}]")

for f, wlist in sorted(by_file.items()):
    print(f"\n{f}:")
    for w in wlist:
        print(f"  - {w}")

print("\n=== SETSTYLESHEET CALLS BY FILE ===")
ss_by_file = defaultdict(list)
for s in data["set_style_sheet"]:
    ss_by_file[s["file"]].append((s["line"], s["content"]))

for f, slist in sorted(ss_by_file.items()):
    print(f"\n{f} ({len(slist)} calls):")
    for line, content in slist[:5]:
        print(f"  line {line}: {content[:90]}")
    if len(slist) > 5:
        print(f"  ... and {len(slist)-5} more")

print("\n=== HARDCODED COLORS BY FILE (Top files) ===")
color_by_file = defaultdict(list)
for c in data["hardcoded_colors"]:
    if "theme.py" not in c["file"]:
        color_by_file[c["file"]].append((c["line"], c["match"], c["content"]))

for f, clist in sorted(color_by_file.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"{f}: {len(clist)} occurrences")

print("\n=== ICONS & EMOJIS FOUND ===")
icon_by_file = defaultdict(set)
for i in data["icons_and_emojis"]:
    icon_by_file[i["file"]].add(i["match"])

for f, ilist in sorted(icon_by_file.items()):
    print(f"{f}: {ilist}")
