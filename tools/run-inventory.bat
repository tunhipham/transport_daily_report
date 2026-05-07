@echo off
chcp 65001 >nul
title Inventory Report Runner

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Inventory Reconciliation Report        ║
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

echo  ⏳ Running inventory report...
echo.

python script\domains\inventory\generate.py

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

set "OUTPUT_DIR=output\artifacts\inventory"
if exist "%OUTPUT_DIR%" (
    echo  📂 Opening report folder...
    start "" "%OUTPUT_DIR%"
)

pause
