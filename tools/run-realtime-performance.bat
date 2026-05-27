@echo off
chcp 65001 >nul
cd /d "G:\My Drive\DOCS\transport_daily_report"

echo ============================================================
echo   REALTIME PERFORMANCE REPORT
echo   %date% %time%
echo ============================================================

REM 1. Generate performance (DB + incremental plan)
echo.
echo [1/2] Generating performance report (realtime)...
python -u script/domains/performance/generate.py --realtime
if %ERRORLEVEL% neq 0 (
    echo ERROR: generate.py failed!
    pause
    exit /b 1
)

REM 2. Deploy to GitHub
echo.
echo [2/2] Deploying to GitHub...
python -u script/dashboard/deploy.py --domain performance
if %ERRORLEVEL% neq 0 (
    echo ERROR: deploy.py failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   DONE! Dashboard updated.
echo ============================================================

REM Write sync timestamp
echo %date% %time% > output\state\.realtime_performance_last_sync
