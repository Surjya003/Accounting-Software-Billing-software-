import os
import re

pattern_hex = re.compile(r'#[0-9a-fA-F]{3,8}')
pattern_style = re.compile(r'setStyleSheet\(')
pattern_qcolor = re.compile(r'QColor\([\'\"]#')

ui_dir = 'app/ui'
violations = []
for root, dirs, files in os.walk(ui_dir):
    rel = root.replace('\\', '/')
    if 'app/ui/theme' in rel:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fh:
            for i, line in enumerate(fh, 1):
                clean = line.strip()
                if clean.startswith('#') or clean.startswith('"""') or clean.startswith("'''"):
                    continue
                # If line is a comment or in a docstring, ignore
                # Check for setStyleSheet
                if pattern_style.search(clean):
                    violations.append((p, i, 'setStyleSheet', clean))
                elif pattern_qcolor.search(clean):
                    violations.append((p, i, 'QColor(#...)', clean))
                else:
                    # Look for string literals containing hex
                    # find all quotes
                    matches = re.findall(r'[\'"](#[0-9a-fA-F]{3,8})[\'"]', clean)
                    if matches:
                        violations.append((p, i, f'Hex literal {matches}', clean))

print(f"Total violations outside app/ui/theme/: {len(violations)}")
for v in violations:
    print(f"{v[0]}:{v[1]} [{v[2]}] -> {v[3]}")
