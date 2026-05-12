@echo off
title Performance Report Runner

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Performance Report (Monthly)
echo    Mode: Generate only (no Telegram)
echo    Requires: ClickHouse server online
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

REM Check ClickHouse connectivity
echo  Checking ClickHouse server...
python -c "import requests; r=requests.get('http://103.140.248.114:32015/', timeout=5); print('  [OK] ClickHouse online')" 2>nul
if errorlevel 1 (
    echo  [ERROR] ClickHouse server unreachable!
    echo  Need internet + VPN to connect.
    pause
    exit /b 1
)

REM ── Auto-detect current month/year ──
for /f %%m in ('python -c "from datetime import date; print(date.today().month)"') do set CUR_MONTH=%%m
for /f %%y in ('python -c "from datetime import date; print(date.today().year)"') do set CUR_YEAR=%%y
for /f %%s in ('python -c "print(','.join(str(m) for m in range(3, %CUR_MONTH%+1)))"') do set MONTHS=%%s

echo  Current month: T%CUR_MONTH%/%CUR_YEAR%
echo  Report range:  months=%MONTHS%
echo.

REM ── Step 1: Fetch ONLY current month (old months already cached) ──
echo  [1/3] Fetching plan data for T%CUR_MONTH%/%CUR_YEAR% only...
echo        (old months use cached monthly_plan_T*.json)
echo.

python -u script\domains\performance\fetch_monthly.py --month %CUR_MONTH% --year %CUR_YEAR%

if errorlevel 1 (
    echo  [WARN] Fetch failed, continuing with cached data...
)

REM ── Step 2: Generate report (uses cached trip data + plan for all months) ──
echo.
echo  [2/3] Running performance report...
echo.

python -u script\domains\performance\generate.py --months %MONTHS% --year %CUR_YEAR% --sla-weeks auto

if errorlevel 1 (
    echo.
    echo  [ERROR] Report failed! Check error above.
    echo  Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

REM ── Step 3: Export dashboard data ──
echo.
echo  [3/3] Exporting dashboard data...
python script\dashboard\export_data.py --domain performance >nul 2>&1

echo.
echo  [OK] Done!
echo  - HTML report: output\artifacts\performance\
echo  - Excel exports: output\artifacts\performance\SLA_ONTIME_*.xlsx
echo  - Excel exports: output\artifacts\performance\RAW_DATA_*.xlsx
echo  - Dashboard data: docs\data\performance.json
echo  - Refresh localhost:8080 to see updated dashboard
echo.

pause
