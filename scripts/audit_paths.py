import os
import re
from pathlib import Path

app_dir = Path("app")
patterns = {
    "__file__": re.compile(r"__file__"),
    "os.getcwd": re.compile(r"getcwd\(\)"),
    "sys._MEIPASS": re.compile(r"sys\._MEIPASS"),
    "data/": re.compile(r'["\'](?:[^\s"\']*\/)?data(?:[/\"\']|$)'),
    "backups/": re.compile(r'["\'](?:[^\s"\']*\/)?backups(?:[/\"\']|$)'),
    "exports/": re.compile(r'["\'](?:[^\s"\']*\/)?exports(?:[/\"\']|$)'),
    "logs/": re.compile(r'["\'](?:[^\s"\']*\/)?logs(?:[/\"\']|$)'),
    "assets/": re.compile(r'["\'](?:[^\s"\']*\/)?assets(?:[/\"\']|$)'),
    "themes/": re.compile(r'["\'](?:[^\s"\']*\/)?themes(?:[/\"\']|$)'),
    "importlib": re.compile(r"importlib|__import__"),
    ".qss": re.compile(r"\.qss"),
    ".json": re.compile(r'["\'][^"\']*\.json["\']'),
    ".svg": re.compile(r'["\'][^"\']*\.svg["\']'),
}

results = {k: [] for k in patterns}

for root, dirs, files in os.walk(app_dir):
    for f in files:
        if f.endswith(".py"):
            p = Path(root) / f
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                for idx, line in enumerate(fp, 1):
                    for k, pat in patterns.items():
                        if pat.search(line):
                            results[k].append(f"{p}:{idx}: {line.strip()[:100]}")

for k, matches in results.items():
    print(f"=== Pattern: {k} ({len(matches)} matches) ===")
    for m in matches:
        print("  " + m)
