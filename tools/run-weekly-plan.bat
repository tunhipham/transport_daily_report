@echo off
chcp 65001 >nul
title Weekly Plan Generator

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Weekly Transport Plan                  ║
echo  ║   Mode: Generate Excel from schedule     ║
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

echo  ⏳ Generating weekly plan...
echo.

python script\domains\weekly_plan\generate_excel.py

if errorlevel 1 (
    echo.
    echo  ❌ Generation failed! Check error above.
    echo  💡 Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  ✅ Done!
echo.

set "OUTPUT_DIR=output\artifacts\weekly transport plan"
if exist "%OUTPUT_DIR%" (
    echo  📂 Opening plan folder...
    start "" "%OUTPUT_DIR%"
)

pause
