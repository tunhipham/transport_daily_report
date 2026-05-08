@echo off
title Daily Report Runner

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Daily Transport Report
echo    Mode: Generate + Send Telegram
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

REM Check key dependencies
python -c "import openpyxl, requests" >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Missing Python dependencies. Installing...
    pip install openpyxl requests matplotlib
    echo.
)

echo  Date: %date%
echo  Running report...
echo.

python script\domains\daily\generate.py --send

if errorlevel 1 (
    echo.
    echo  [ERROR] Report failed! Check error above.
    echo  Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  Exporting dashboard data...
python script\dashboard\export_data.py --domain daily >nul 2>&1

echo.
echo  [OK] Done!
echo  - HTML report: output\artifacts\daily\
echo  - Dashboard data: docs\data\daily.json
echo  - Refresh localhost:8080 to see updated dashboard
echo.

pause
