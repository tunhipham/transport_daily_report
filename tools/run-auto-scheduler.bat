@echo off
chcp 65001 >nul 2>&1
setlocal

set "PROJECT=G:\My Drive\DOCS\transport_daily_report"
set "PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"
set "SCRIPT=%PROJECT%\script\telegram\auto_scheduler.py"

:: Check if already running
tasklist /FI "WINDOWTITLE eq Auto-Scheduler*" 2>nul | find /i "python" >nul
if not errorlevel 1 (
    echo [SKIP] auto_scheduler.py is already running.
    exit /b 0
)

echo ════════════════════════════════════════════════════════════
echo  Starting Auto-Scheduler for Delivery Reports...
echo  %date% %time%
echo ════════════════════════════════════════════════════════════

cd /d "%PROJECT%"
start "Auto-Scheduler Delivery Report" /MIN "%PYTHON%" "%SCRIPT%"
echo [OK] auto_scheduler.py started in background (minimized).
