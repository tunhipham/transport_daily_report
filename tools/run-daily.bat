@echo off
title Daily Report Runner
setlocal enabledelayedexpansion

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
    echo  ============================================
    echo   Telegram bi CHAN do thieu data.
    echo   Ban co muon gui FORCE khong?
    echo  ============================================
    echo.
    set /p "FORCE_CHOICE=  Bam [Y] de gui force, [N] de bo qua: "
    if /i "!FORCE_CHOICE!"=="Y" (
        echo.
        echo  Re-running with --force...
        python script\domains\daily\generate.py --send --force
    ) else (
        echo.
        echo  [SKIP] Telegram skipped.
    )
)

REM Always deploy dashboard (regardless of Telegram result)
echo.
echo  Deploying dashboard...
python script\dashboard\deploy.py --domain daily

echo.
echo  Exporting dashboard data...
python script\dashboard\export_data.py --domain daily >nul 2>&1

echo.
echo  [OK] Done!
echo  - HTML report + Capacity Forecast: output\artifacts\daily\
echo  - Dashboard data: docs\data\daily.json
echo  - Capacity forecast: docs\data\capacity_forecast.json
echo  - Dashboard: https://tunhipham.github.io/transport_daily_report/
echo.

pause
