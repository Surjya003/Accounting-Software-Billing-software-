import os
import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"

test_files = sorted([f for f in TESTS_DIR.glob("test_*.py")])

print(f"| Test File | Passed | Failed | Skipped | Time (s) | Status |", flush=True)
print(f"|:---|:---:|:---:|:---:|:---:|:---|", flush=True)

total_passed = 0
total_failed = 0
total_skipped = 0

for tf in test_files:
    t0 = time.time()
    try:
        cmd = [sys.executable, "-m", "pytest", str(tf), "-q", "--tb=no"]
        proc = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, timeout=60)
        dur = round(time.time() - t0, 2)
        out = proc.stdout.strip().split("\n")[-1] if proc.stdout.strip() else ""
        err = proc.stderr.strip()
        
        passed = 0
        failed = 0
        skipped = 0
        
        for p in out.split(","):
            p = p.strip()
            if "passed" in p:
                try: passed = int(p.split()[0])
                except: pass
            elif "failed" in p:
                try: failed = int(p.split()[0])
                except: pass
            elif "skipped" in p:
                try: skipped = int(p.split()[0])
                except: pass

        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        status = "PASSED" if failed == 0 and passed > 0 else ("FAILED" if failed > 0 else "NO_TESTS")
        print(f"| `{tf.name}` | {passed} | {failed} | {skipped} | {dur}s | {status} |", flush=True)
    except subprocess.TimeoutExpired:
        dur = round(time.time() - t0, 2)
        print(f"| `{tf.name}` | 0 | 1 | 0 | {dur}s | TIMEOUT |", flush=True)
        total_failed += 1
    except Exception as e:
        print(f"| `{tf.name}` | 0 | 1 | 0 | 0.0s | ERROR: {e} |", flush=True)
        total_failed += 1

print(f"\n**TOTAL:** {total_passed} passed, {total_failed} failed, {total_skipped} skipped across {len(test_files)} test files.", flush=True)
