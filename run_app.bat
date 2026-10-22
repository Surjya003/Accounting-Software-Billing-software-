@echo off
title Starting VyaparLedger Pro...
cd /d "%~dp0"
echo ===================================================
echo   Launching VyaparLedger Pro...
echo ===================================================
python app\main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error. Press any key to close.
    pause
)
