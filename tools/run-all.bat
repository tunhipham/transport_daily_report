@echo off
title Run All Reports

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Run All Reports
echo    Daily + Inventory + Weekly Plan
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

echo ==========================================
echo  1/3  Daily Report
echo ==========================================
python script\domains\daily\generate.py
if errorlevel 1 (
    echo  [WARN] Daily report failed, continuing...
)

echo.
echo ==========================================
echo  2/3  Inventory Report
echo ==========================================
python script\domains\inventory\generate.py
if errorlevel 1 (
    echo  [WARN] Inventory report failed, continuing...
)

echo.
echo ==========================================
echo  3/3  Weekly Plan
echo ==========================================
python script\domains\weekly_plan\generate_excel.py
if errorlevel 1 (
    echo  [WARN] Weekly plan failed, continuing...
)

echo.
echo ==========================================
echo  Rebuilding Dashboard...
echo ==========================================
python script\orchestrator\pipeline.py
if errorlevel 1 (
    echo  [WARN] Dashboard build failed, continuing...
)

echo.
echo  [OK] All done!
echo  Output: output\artifacts\
echo.

pause
