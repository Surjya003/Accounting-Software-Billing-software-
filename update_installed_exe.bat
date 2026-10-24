@echo off
REM =====================================================================
REM BillFlow Suite - Update Installed Executable Helper
REM Auto-elevates to Administrator to update C:\Program Files\Billflow\
REM with the standalone single-file BillFlow.exe.
REM =====================================================================
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
set "SRC=%ROOT%\dist\BillFlow.exe"

if not exist "%SRC%" (
    echo [ERROR] %SRC% not found.
    echo Please run build_release.bat first.
    pause
    exit /b 1
)

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator elevation to update Program Files...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo =====================================================================
echo  Updating BillFlow in Program Files with standalone BillFlow.exe...
echo =====================================================================

set "COPIED=0"

if exist "C:\Program Files\Billflow" (
    echo Copying to C:\Program Files\Billflow\BillFlow.exe...
    copy /y "%SRC%" "C:\Program Files\Billflow\BillFlow.exe"
    if %errorLevel% equ 0 (
        echo [SUCCESS] Updated C:\Program Files\Billflow\BillFlow.exe
        set "COPIED=1"
    )
)

if exist "C:\Program Files\BillFlow Suite" (
    echo Copying to C:\Program Files\BillFlow Suite\BillFlow.exe...
    copy /y "%SRC%" "C:\Program Files\BillFlow Suite\BillFlow.exe"
    if %errorLevel% equ 0 (
        echo [SUCCESS] Updated C:\Program Files\BillFlow Suite\BillFlow.exe
        set "COPIED=1"
    )
)

if "%COPIED%"=="0" (
    echo Creating C:\Program Files\Billflow directory...
    mkdir "C:\Program Files\Billflow" 2>nul
    copy /y "%SRC%" "C:\Program Files\Billflow\BillFlow.exe"
    if %errorLevel% equ 0 (
        echo [SUCCESS] Installed to C:\Program Files\Billflow\BillFlow.exe
    )
)

echo.
echo =====================================================================
echo  Update Complete! You can now launch BillFlow from Program Files.
echo =====================================================================
pause
