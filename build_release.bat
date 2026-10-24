@echo off
REM =====================================================================
REM BillFlow Suite - Release Build Batch Wrapper
REM =====================================================================
setlocal enabledelayedexpansion

echo =====================================================================
echo  Starting BillFlow Suite Release Build Process...
echo =====================================================================

python scripts\build_release.py %*
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Build completed successfully.
exit /b 0
