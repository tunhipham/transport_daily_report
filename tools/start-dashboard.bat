@echo off
chcp 65001 >nul
title KFM Dashboard Server (port 8080)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   KFM Logistics Dashboard                ║
echo  ║   http://localhost:8080                   ║
echo  ║   Ctrl+C to stop                          ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found! Please install Python first.
    pause
    exit /b 1
)

REM Auto-open browser after 2 seconds
start "" /min cmd /c "timeout /t 2 >nul & start http://localhost:8080/dashboard/dashboard.html"

REM Serve entire output/ so iframes can reach ../artifacts/
python -m http.server 8080 --directory "output"
