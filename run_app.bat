@echo off
title Starting BillFlow Suite...
cd /d "%~dp0"
echo ===================================================
echo   Launching BillFlow Suite...
echo ===================================================
python -m app.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error. Press any key to close.
    pause
)
