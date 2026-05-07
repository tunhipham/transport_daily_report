@echo off
title Weekly Plan Generator

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Weekly Transport Plan
echo    Mode: Generate Excel from schedule
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

echo  Generating weekly plan...
echo.

python script\domains\weekly_plan\generate_excel.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Generation failed! Check error above.
    echo  Tip: Report this error to Antigravity for fix.
    pause
    exit /b 1
)

echo.
echo  [OK] Done!
echo.

pause
