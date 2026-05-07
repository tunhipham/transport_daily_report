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

echo  Running performance report...
echo.

python script\domains\performance\generate.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Report failed! Check error above.
    echo  Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  Rebuilding dashboard...
python script\orchestrator\pipeline.py >nul 2>&1

echo.
echo  [OK] Done!
echo  Dashboard updated - refresh localhost:8080 to see.
echo.

pause
