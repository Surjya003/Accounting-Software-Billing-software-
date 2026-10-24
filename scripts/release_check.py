#!/usr/bin/env python3
"""
BillFlow Suite - Master Production Release CI Verification Runner
================================================================
Executes the complete test and compliance pipeline for Phase 8 sign-off:
1. Dependency Security Audit (pip-audit on requirements.txt)
2. Core QA Full Test Suite (tests/test_full_qa_suite.py)
3. Deep Coverage Audit Suite (tests/test_deep_coverage_audit.py - 16 scenarios)
4. Phase 3 Data Safety Suite (tests/test_phase3_data_safety.py - 5 tests)
5. Phase 4 Security & RBAC Suite (tests/test_phase4_security_rbac.py - 5 tests)
6. Performance & Stress Test Suite (tests/test_performance_stress.py - 32,000 records)
7. Books Integrity Verification (scripts/verify_books.py on test_accounting.db)
8. Database Health Check (PRAGMA integrity_check + foreign_key_check)

Rules:
- NEVER touches data/accounting.db.
- Exits 0 only when 100% of checks pass.
"""
import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Reconfigure stdout/stderr to utf-8 with replacement for Windows cp1252 consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = ROOT_DIR / "data" / "test_accounting.db"


def run_command_gate(name: str, cmd: List[str], cwd: Path = ROOT_DIR) -> Dict[str, Any]:
    """Runs a shell command gate and returns result dictionary."""
    print(f"\n{'='*70}")
    print(f">>> EXECUTING GATE: {name}")
    print(f"    Command: {' '.join(cmd)}")
    print(f"{'='*70}")

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True
    )
    elapsed = time.perf_counter() - t0

    passed = (proc.returncode == 0)
    output = (proc.stdout + "\n" + proc.stderr).strip()

    # Print abbreviated output
    lines = output.splitlines()
    if len(lines) > 20:
        print("\n".join(lines[:10]))
        print(f"  ... [{len(lines)-20} lines truncated] ...")
        print("\n".join(lines[-10:]))
    else:
        print(output)

    status_str = "PASSED" if passed else "FAILED"
    print(f"\n--> {name}: {status_str} ({elapsed:.2f}s)")

    return {
        "name": name,
        "command": " ".join(cmd),
        "passed": passed,
        "exit_code": proc.returncode,
        "duration": elapsed,
        "output": output
    }


def main():
    print("""
========================================================================
       BILLFLOW SUITE -- MASTER PRODUCTION RELEASE VERIFICATION GATE     
========================================================================
    """)
    t_start = time.perf_counter()

    # Ensure test database exists for verification scripts
    if not TEST_DB_PATH.exists():
        # Copy from base test database or create fresh
        import shutil
        src = ROOT_DIR / "data" / "test_accounting.db"
        if not src.exists():
            print(f"ERROR: Test database not found at {TEST_DB_PATH}!")
            sys.exit(1)

    gates = [
        ("Gate 1: Dependency Security Audit", [sys.executable, "-m", "pip_audit", "-r", "requirements.txt"]),
        ("Gate 2: Core QA Test Suite (38 Tests)", [sys.executable, "tests/test_full_qa_suite.py"]),
        ("Gate 3: Deep Coverage Audit Suite (16 Scenarios)", [sys.executable, "-m", "pytest", "tests/test_deep_coverage_audit.py"]),
        ("Gate 4: Phase 3 Data Safety Suite (5 Tests)", [sys.executable, "-m", "pytest", "tests/test_phase3_data_safety.py"]),
        ("Gate 5: Phase 4 Security & RBAC Suite (5 Tests)", [sys.executable, "-m", "pytest", "tests/test_phase4_security_rbac.py"]),
        ("Gate 6: Performance & Stress Benchmarks (32k Records)", [sys.executable, "-m", "pytest", "tests/test_performance_stress.py", "-v"]),
        ("Gate 7: Books Mathematical Integrity (7 Checks)", [sys.executable, "scripts/verify_books.py", str(TEST_DB_PATH)]),
    ]

    results = []
    all_passed = True

    for name, cmd in gates:
        res = run_command_gate(name, cmd)
        results.append(res)
        if not res["passed"]:
            all_passed = False

    # Gate 8: Database Health Check in Python
    t0 = time.perf_counter()
    from app.database.migrations import check_database_health
    is_healthy, issues = check_database_health(TEST_DB_PATH)
    elapsed_health = time.perf_counter() - t0
    db_passed = is_healthy
    if not db_passed:
        all_passed = False

    results.append({
        "name": "Gate 8: Database WAL & Health Verification",
        "command": "check_database_health(test_accounting.db)",
        "passed": db_passed,
        "exit_code": 0 if db_passed else 1,
        "duration": elapsed_health,
        "output": f"Healthy: {is_healthy}, Issues: {issues}"
    })

    total_time = time.perf_counter() - t_start

    # Final Summary Table
    print("\n" + "="*80)
    print(f"{'RELEASE CANDIDATE VERIFICATION SUMMARY':^80}")
    print("="*80)
    print(f"{'#':<4} {'Gate / Test Suite Name':<52} {'Duration':<12} {'Status'}")
    print("-"*80)

    for idx, r in enumerate(results, start=1):
        status_tag = "[PASS]" if r["passed"] else "[FAIL]"
        dur_str = f"{r['duration']:.2f}s"
        print(f"{idx:<4} {r['name']:<52} {dur_str:<12} {status_tag}")

    print("="*80)
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print("="*80)

    if all_passed:
        print("\n[SUCCESS] ALL 8 QUALITY & COMPLIANCE GATES PASSED! SYSTEM IS 100% PRODUCTION READY.")
        sys.exit(0)
    else:
        print("\n[FAILURE] RELEASE VERIFICATION FAILED. Review failed gates above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
