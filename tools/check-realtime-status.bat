@echo off
chcp 65001 >nul
cd /d "G:\My Drive\DOCS\transport_daily_report"

echo ============================================================
echo   PERFORMANCE REALTIME SYNC STATUS
echo ============================================================

REM Check last sync time
if exist "output\state\.realtime_performance_last_sync" (
    echo.
    set /p LAST_SYNC=<"output\state\.realtime_performance_last_sync"
    echo   Last sync: %LAST_SYNC%
) else (
    echo.
    echo   ⚠ Never synced!
)

REM Check Task Scheduler
echo.
echo   --- Task Scheduler ---
schtasks /query /tn "RealtimePerformance" /fo LIST 2>nul
if %ERRORLEVEL% neq 0 (
    echo   ⚠ Task "RealtimePerformance" not found in Task Scheduler!
    echo   Run: schtasks /create /tn "RealtimePerformance" /xml config\realtime_performance_task.xml
)

REM Check monthly plan exists
echo.
echo   --- Monthly Plan Cache ---
for /f "tokens=*" %%m in ('python -c "from datetime import datetime; print(f'T{datetime.now().month:02d}')"') do set MONTH=%%m
if exist "output\state\monthly_plan_%MONTH%.json" (
    echo   ✅ monthly_plan_%MONTH%.json exists
) else (
    echo   ⚠ monthly_plan_%MONTH%.json NOT FOUND!
    echo   Run: python script/domains/performance/fetch_monthly.py --month XX --year YYYY
)

REM Check latest performance JSON
echo.
echo   --- Dashboard Data ---
if exist "docs\data\performance.json" (
    for %%f in (docs\data\performance.json) do echo   ✅ performance.json (%%~zf bytes, %%~tf)
) else (
    echo   ⚠ performance.json not found
)

echo.
echo ============================================================
pause
