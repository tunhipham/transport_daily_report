@echo off
title Inventory Report Runner

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Inventory Reconciliation Report
echo    Mode: Generate only (no Telegram)
echo  ===========================================
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    pause
    exit /b 1
)

echo  Running inventory report...
echo.

python script\domains\inventory\generate.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Report failed! Check error above.
    echo  Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  Exporting dashboard data...
python script\dashboard\export_data.py --domain inventory >nul 2>&1

echo.
echo  [OK] Done!
echo  - HTML report: output\artifacts\inventory\
echo  - Dashboard data: docs\data\inventory.json
echo  - Refresh localhost:8080 to see updated dashboard
echo.

pause
