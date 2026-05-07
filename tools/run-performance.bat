@echo off
chcp 65001 >nul
title Performance Report Runner

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Performance Report (Monthly)           ║
echo  ║   Mode: Generate only (no Telegram)      ║
echo  ║   ⚠ Requires: ClickHouse server online  ║
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

REM Check ClickHouse connectivity
echo  🔍 Checking ClickHouse server...
python -c "import requests; r=requests.get('http://103.140.248.114:32015/', timeout=5); print('  ✅ ClickHouse OK')" 2>nul
if errorlevel 1 (
    echo  ❌ ClickHouse server unreachable!
    echo  💡 Need internet + VPN to connect.
    pause
    exit /b 1
)

echo  ⏳ Running performance report...
echo.

python script\domains\performance\generate.py

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

set "OUTPUT_DIR=output\artifacts\performance"
if exist "%OUTPUT_DIR%" (
    echo  📂 Opening report folder...
    start "" "%OUTPUT_DIR%"
)

pause
