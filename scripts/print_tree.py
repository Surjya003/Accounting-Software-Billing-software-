import os
from pathlib import Path

def get_dir_size(path):
    total = 0
    count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            p = Path(root) / f
            try:
                total += p.stat().st_size
                count += 1
            except Exception:
                pass
    return total, count

root_p = Path('.')
print(f"Project Root: {root_p.resolve()}")
print("=" * 75)
print(f"{'Directory / File':<45} | {'Files':<8} | {'Size (MB)':<12}")
print("-" * 75)

for p in sorted(root_p.iterdir()):
    if p.name.startswith(".git") and p.is_dir():
        sz, cnt = get_dir_size(p)
        print(f"{p.name:<45} | {cnt:<8} | {sz/(1024*1024):>10.2f} MB")
        continue
    if p.is_dir():
        sz, cnt = get_dir_size(p)
        print(f"{p.name + '/':<45} | {cnt:<8} | {sz/(1024*1024):>10.2f} MB")
        # Level 2
        try:
            for sub in sorted(p.iterdir()):
                if sub.is_dir():
                    sub_sz, sub_cnt = get_dir_size(sub)
                    print(f"  {sub.name + '/':<43} | {sub_cnt:<8} | {sub_sz/(1024*1024):>10.2f} MB")
        except Exception:
            pass
    else:
        try:
            sz = p.stat().st_size
            print(f"{p.name:<45} | {'1':<8} | {sz/(1024*1024):>10.2f} MB")
        except Exception:
            pass
