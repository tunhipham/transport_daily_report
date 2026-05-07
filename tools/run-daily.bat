@echo off
chcp 65001 >nul
title Daily Report Runner

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Daily Transport Report                 ║
echo  ║   Mode: Generate only (no Telegram)      ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found!
    pause
    exit /b 1
)

REM Check dependencies
python -c "import pandas, openpyxl, requests, matplotlib" >nul 2>&1
if errorlevel 1 (
    echo  ⚠ Missing Python dependencies. Installing...
    pip install pandas openpyxl requests matplotlib
    echo.
)

echo  📅 Report date: today (%date%)
echo  ⏳ Running...
echo.

python script\domains\daily\generate.py

if errorlevel 1 (
    echo.
    echo  ❌ Report failed! Check error above.
    echo  💡 Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  ✅ Done!
echo.

REM Open output folder
set "OUTPUT_DIR=output\artifacts\daily"
if exist "%OUTPUT_DIR%" (
    echo  📂 Opening report folder...
    start "" "%OUTPUT_DIR%"
)

pause
