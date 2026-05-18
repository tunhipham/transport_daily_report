@echo off
title Daily Report Runner
setlocal enabledelayedexpansion

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

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

echo.
echo  ===========================================
echo    Daily Transport Report
echo  ===========================================
echo.
echo  [1] Hom nay (%date%) - Generate + Telegram
echo  [2] Chay bu ngay cu   - Generate only (no Telegram) + Deploy
echo  [3] Chay bu ngay cu   - Generate + Telegram + Deploy
echo.
set /p "MODE=  Chon che do [1/2/3]: "

if "!MODE!"=="1" goto :MODE_TODAY
if "!MODE!"=="2" goto :MODE_CATCHUP
if "!MODE!"=="3" goto :MODE_CATCHUP_SEND
echo  [ERROR] Lua chon khong hop le!
pause
exit /b 1

:MODE_TODAY
echo.
echo  Mode: Generate + Send Telegram (hom nay)
echo  Date: %date%
echo  Running report...
echo.

python -u script\domains\daily\generate.py --send

if errorlevel 1 (
    echo.
    echo  ============================================
    echo   Telegram bi CHAN do thieu data.
    echo   Ban co muon gui FORCE khong?
    echo   ^(Chi gui Telegram + deploy, khong chay lai^)
    echo  ============================================
    echo.
    set /p "FORCE_CHOICE=  Bam [Y] de gui force, [N] de bo qua: "
    if /i "!FORCE_CHOICE!"=="Y" (
        echo.
        echo  Sending with existing data...
        python script\domains\daily\generate.py --send-only
    ) else (
        echo.
        echo  [SKIP] Telegram skipped. Deploying dashboard only...
        python script\dashboard\deploy.py --domain daily
    )
)

goto :FINISH

:MODE_CATCHUP
echo.
set /p "CATCH_DATE=  Nhap ngay can chay (DD/MM/YYYY): "
echo.
echo  Mode: Chay bu (no Telegram)
echo  Date: !CATCH_DATE!
echo  Running report...
echo.

python -u script\domains\daily\generate.py --date !CATCH_DATE!

echo.
echo  Deploying dashboard...
python -u script\dashboard\deploy.py --domain daily

goto :FINISH

:MODE_CATCHUP_SEND
echo.
set /p "CATCH_DATE=  Nhap ngay can chay (DD/MM/YYYY): "
echo.
echo  Mode: Chay bu + Telegram
echo  Date: !CATCH_DATE!
echo  Running report...
echo.

python -u script\domains\daily\generate.py --date !CATCH_DATE! --send

if errorlevel 1 (
    echo.
    echo  ============================================
    echo   Telegram bi CHAN do thieu data.
    echo  ============================================
    echo.
    set /p "FORCE_CHOICE=  Bam [Y] de gui force, [N] de bo qua: "
    if /i "!FORCE_CHOICE!"=="Y" (
        echo.
        echo  Sending with --force...
        python -u script\domains\daily\generate.py --date !CATCH_DATE! --send --force
    ) else (
        echo.
        echo  [SKIP] Telegram skipped. Deploying dashboard only...
        python script\dashboard\deploy.py --domain daily
    )
) else (
    echo.
    echo  Deploying dashboard...
    python -u script\dashboard\deploy.py --domain daily
)

goto :FINISH

:FINISH
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
