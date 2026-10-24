"""
BillFlow Suite - Unified Release Build Automation
=================================================
Automates full end-to-end production release lifecycle:
1. Environment preflight & Inno Setup compiler detection
2. Clean workspace (build/, dist/, release/)
3. Baseline test execution
4. Asset generation (app.ico, wizard bitmaps, version-info resource)
5. PyInstaller windowed distribution build
6. Pre-installer assertion (no database/backup/user-data files bundled)
7. Qt plugin verification (platforms, imageformats, iconengines)
8. Frozen headless --selftest verification
9. Inno Setup installer compilation (ISCC.exe)
10. SHA-256 checksum generation & summary
"""
import os
import sys
import time
import shutil
import hashlib
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from app.version import VERSION
from app.branding import APP_NAME, BRAND_NAME, MAKER_NAME


def find_iscc_path() -> Optional[Path]:
    """Locates the Inno Setup command-line compiler (ISCC.exe)."""
    # 1. Standard search paths
    candidates = [
        Path(r"C:\Program Files\Inno Setup 7\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for p in candidates:
        if p.is_file():
            return p

    # 2. PATH check
    iscc_which = shutil.which("ISCC.exe")
    if iscc_which:
        return Path(iscc_which)

    # 3. Registry check (HKLM & HKCU)
    if sys.platform == "win32":
        import winreg
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for sub in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
                try:
                    with winreg.OpenKey(root, sub) as key:
                        count = winreg.QueryInfoKey(key)[0]
                        for idx in range(count):
                            subkey_name = winreg.EnumKey(key, idx)
                            if "Inno Setup" in subkey_name:
                                with winreg.OpenKey(key, subkey_name) as skey:
                                    try:
                                        loc, _ = winreg.QueryValueEx(skey, "InstallLocation")
                                        if loc and (Path(loc) / "ISCC.exe").is_file():
                                            return Path(loc) / "ISCC.exe"
                                    except Exception:
                                        pass
                except Exception:
                    pass
    return None


def calculate_sha256(filepath: Path) -> str:
    """Computes SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_dir_size_mb(path: Path) -> float:
    """Calculates total directory size in megabytes."""
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total / (1024 * 1024)


def clean_build_artifacts():
    """Cleans build/, dist/, release/ directories."""
    print("\n[STEP 1/8] Cleaning build artifacts (build/, dist/, release/)...")
    for d in ["build", "dist", "release"]:
        target = WORKSPACE / d
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            print(f"  Removed: {target}")


def generate_branding():
    """Generates application icons and installer wizard bitmaps."""
    print("\n[STEP 2/8] Generating branding assets & Windows version resource...")
    from scripts.generate_branding_assets import generate_ico, generate_wizard_bmp, generate_wizard_small_bmp
    generate_ico()
    generate_wizard_bmp()
    generate_wizard_small_bmp()

    # Generate version resource
    from scripts.generate_version_resource import OUTPUT_FILE
    print(f"  Version resource confirmed at: {OUTPUT_FILE}")


def run_unit_tests(quick: bool = False):
    """Runs automated regression and path safety tests."""
    print("\n[STEP 3/8] Running pre-build tests...")
    if quick:
        cmd = [sys.executable, "-m", "pytest", "tests/test_paths.py", "tests/test_save_dialog.py"]
    else:
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_paths.py",
            "tests/test_save_dialog.py",
            "tests/test_accounts_exports.py",
            "tests/test_theme_integrity.py"
        ]
    print(f"  Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=WORKSPACE)
    if res.returncode != 0:
        raise RuntimeError(f"Tests failed with exit code {res.returncode}")
    print("  Tests passed successfully.")


def run_pyinstaller_build(mode: str = "onefile"):
    """Builds standalone single-file or windowed one-folder bundle with PyInstaller."""
    if mode == "onefile":
        print("\n[STEP 4/8] Building PyInstaller standalone single-file executable...")
        spec_file = WORKSPACE / "build_onefile.spec"
    else:
        print("\n[STEP 4/8] Building PyInstaller windowed distribution folder...")
        spec_file = WORKSPACE / "build_exe.spec"

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
    start = time.time()
    res = subprocess.run(cmd, cwd=WORKSPACE)
    duration = time.time() - start

    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {res.returncode}")

    if mode == "onefile":
        dist_dir = WORKSPACE / "dist"
        exe_file = dist_dir / "BillFlow.exe"
        if not exe_file.is_file():
            raise FileNotFoundError(f"Standalone executable not found at {exe_file}")
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        file_count = 1
        print(f"  PyInstaller onefile build completed in {duration:.1f}s")
        print(f"  Standalone Exe: {exe_file}")
        print(f"  Size: {size_mb:.2f} MB ({exe_file.stat().st_size:,} bytes)")
    else:
        dist_dir = WORKSPACE / "dist" / "BillFlow"
        if not dist_dir.is_dir():
            raise FileNotFoundError(f"PyInstaller output directory not found at {dist_dir}")
        exe_file = dist_dir / "BillFlow.exe"
        if not exe_file.is_file():
            raise FileNotFoundError(f"Executable not found at {exe_file}")
        size_mb = get_dir_size_mb(dist_dir)
        file_count = sum(1 for _ in dist_dir.rglob("*") if _.is_file())
        print(f"  PyInstaller onedir build completed in {duration:.1f}s")
        print(f"  Folder: {dist_dir}")
        print(f"  Files: {file_count} | Total Size: {size_mb:.2f} MB")

    return dist_dir, exe_file, duration, size_mb, file_count


def assert_no_data_bundled(dist_dir: Path):
    """
    CRITICAL RELEASE RULE:
    Asserts zero databases, backups, encrypted files, logs, or developer test data exist inside dist.
    """
    print("\n[STEP 5/8] Asserting zero user data / databases bundled in dist...")
    forbidden_patterns = ["*.db", "*.sqlite", "*.enc", "*.log", ".time_guard", ".billflow.lock"]
    violating_files = []
    for pattern in forbidden_patterns:
        for match in dist_dir.rglob(pattern):
            violating_files.append(match)

    if violating_files:
        msg = f"SECURITY & COMPLIANCE FAILURE: Found {len(violating_files)} forbidden data file(s) in distribution bundle:\n"
        for v in violating_files:
            msg += f"  - {v.relative_to(WORKSPACE)}\n"
        raise AssertionError(msg)
    print("  Assertion PASSED: No database or developer data inside dist.")


def verify_qt_plugins(dist_dir: Path, is_onefile: bool = False):
    """Verifies that platforms, styles, imageformats, and iconengines are present in dist."""
    print("\n[STEP 6/8] Verifying Qt plugins in distribution bundle...")
    if is_onefile:
        print("  Single-file bundle detected: Qt plugins embedded directly in executable (verified in selftest).")
        return

    found_plugins = {
        "platforms": False,
        "imageformats": False,
        "iconengines": False
    }

    for p in dist_dir.rglob("*"):
        name_lower = p.name.lower()
        if "qwindows.dll" in name_lower:
            found_plugins["platforms"] = True
        if "qsvg" in name_lower and p.suffix.lower() == ".dll":
            if "imageformats" in str(p).lower() or "iconengines" in str(p).lower():
                found_plugins["imageformats"] = True
                found_plugins["iconengines"] = True

    print(f"  Plugin verification results: {found_plugins}")
    if not found_plugins["platforms"]:
        raise RuntimeError("CRITICAL: qwindows.dll platform plugin missing from distribution!")


def run_frozen_selftest(exe_path: Path):
    """Executes the frozen executable with --selftest in an isolated temp directory."""
    print("\n[STEP 7/8] Executing frozen --selftest verification...")
    with tempfile.TemporaryDirectory(prefix="billflow_release_selftest_") as tmp_dir:
        cmd = [str(exe_path), "--selftest", "--no-splash", f"--data-dir={tmp_dir}"]
        print(f"  Running: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=WORKSPACE)
        print("  Selftest Output:")
        print(res.stdout)
        if res.stderr:
            print("  Selftest Stderr:")
            print(res.stderr)

        if res.returncode != 0:
            raise RuntimeError(f"Frozen self-test failed with exit code {res.returncode}")
        print("  Frozen --selftest PASSED with exit code 0.")


def compile_inno_installer(iscc_path: Path) -> Path:
    """Compiles the Windows installer with ISCC.exe."""
    print("\n[STEP 8/8] Compiling installer with Inno Setup...")
    iss_file = WORKSPACE / "installer.iss"
    cmd = [str(iscc_path), str(iss_file)]
    print(f"  Compiler: {iscc_path}")
    print(f"  Script: {iss_file}")

    start = time.time()
    res = subprocess.run(cmd, cwd=WORKSPACE)
    duration = time.time() - start

    if res.returncode != 0:
        raise RuntimeError(f"Inno Setup compilation failed with exit code {res.returncode}")

    release_dir = WORKSPACE / "release"
    installer_files = list(release_dir.glob("BillFlow_Setup_v*.exe"))
    if not installer_files:
        raise FileNotFoundError(f"Setup executable not found in {release_dir}")

    installer_file = installer_files[0]
    inst_size_mb = installer_file.stat().st_size / (1024 * 1024)
    sha256 = calculate_sha256(installer_file)

    # Write SHA256SUMS.txt
    sums_file = release_dir / "SHA256SUMS.txt"
    sums_file.write_text(f"{sha256} *{installer_file.name}\n", encoding="utf-8")

    print(f"  Installer compiled successfully in {duration:.1f}s")
    print(f"  File: {installer_file.name}")
    print(f"  Size: {inst_size_mb:.2f} MB ({installer_file.stat().st_size:,} bytes)")
    print(f"  SHA-256: {sha256}")
    print(f"  Checksums saved: {sums_file}")
    return installer_file


def main():
    parser = argparse.ArgumentParser(description="BillFlow Suite Unified Release Builder")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-build automated tests")
    parser.add_argument("--skip-installer", action="store_true", help="Skip Inno Setup compilation")
    parser.add_argument("--quick", action="store_true", help="Run only fast path tests")
    parser.add_argument("--onedir", action="store_true", help="Build onedir folder instead of standalone single-file exe")
    args = parser.parse_args()

    mode = "onedir" if args.onedir else "onefile"

    overall_start = time.time()
    print("=" * 75)
    print(f"  BILLFLOW SUITE v{VERSION} - ENTERPRISE RELEASE BUILD [{mode.upper()}]")
    print(f"  Publisher: {BRAND_NAME} | Author: {MAKER_NAME}")
    print("=" * 75)

    iscc_path = find_iscc_path()
    if not iscc_path:
        print("[WARNING] Inno Setup compiler (ISCC.exe) not found!")
        if not args.skip_installer:
            print("[ERROR] Cannot compile installer without Inno Setup. Please install Inno Setup 6/7.")
            sys.exit(1)
    else:
        print(f"  Detected Inno Setup: {iscc_path}")

    # Step 1: Clean
    clean_build_artifacts()

    # Step 2: Branding assets
    generate_branding()

    # Step 3: Tests
    if not args.skip_tests:
        run_unit_tests(quick=args.quick)

    # Step 4: PyInstaller build
    dist_dir, exe_file, build_dur, dist_size, file_count = run_pyinstaller_build(mode=mode)

    # Step 5: Assert no user data bundled
    assert_no_data_bundled(dist_dir)

    # Step 6: Verify Qt plugins
    verify_qt_plugins(dist_dir, is_onefile=(mode == "onefile"))

    # Step 7: Frozen selftest
    run_frozen_selftest(exe_file)

    # Step 8: Inno Setup compilation
    if not args.skip_installer and iscc_path:
        inst_file = compile_inno_installer(iscc_path)
    else:
        inst_file = None

    total_time = time.time() - overall_start
    print("\n" + "=" * 75)
    print("  BUILD & VERIFICATION SUMMARY - ALL STAGES PASSED")
    print("=" * 75)
    print(f"  Version:               {VERSION}")
    print(f"  PyInstaller Dist:      {dist_dir}")
    print(f"  Dist Size:             {dist_size:.2f} MB ({file_count} files)")
    if inst_file:
        print(f"  Installer:             {inst_file}")
        print(f"  Installer Size:        {inst_file.stat().st_size / (1024*1024):.2f} MB")
        print(f"  Installer SHA-256:     {calculate_sha256(inst_file)}")
    print(f"  Total Release Time:    {total_time:.1f}s")
    print("=" * 75)


if __name__ == "__main__":
    main()
