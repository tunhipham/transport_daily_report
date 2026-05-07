@echo off
title KFM Dashboard Server (port 8080)

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    KFM Logistics Dashboard
echo    http://localhost:8080
echo    Press Ctrl+C to stop
echo  ===========================================
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Python path: %LOCALAPPDATA%\Programs\Python
    pause
    exit /b 1
)

echo  Starting server...

REM Auto-open browser after 2 seconds
start "" /min cmd /c "timeout /t 2 >nul & start http://localhost:8080/dashboard/dashboard.html"

REM Serve entire output/ so iframes can reach ../artifacts/
python -m http.server 8080 --directory "output"
