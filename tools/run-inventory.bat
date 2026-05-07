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
echo  [OK] Done!
echo.

set "OUTPUT_DIR=output\artifacts\inventory"
if exist "%OUTPUT_DIR%" (
    echo  Opening report folder...
    start "" "%OUTPUT_DIR%"
)

pause
