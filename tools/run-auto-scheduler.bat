@echo off
chcp 65001 >nul 2>&1
setlocal

set "PROJECT=G:\My Drive\DOCS\transport_daily_report"
set "PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"
set "SCRIPT=%PROJECT%\script\telegram\auto_scheduler.py"
set "LOGFILE=%PROJECT%\logs\auto_scheduler_runner.log"
set "PYTHONIOENCODING=utf-8"

:: Ensure log dir exists
if not exist "%PROJECT%\logs" mkdir "%PROJECT%\logs"

:: Check if already running (match by script name in command line)
wmic process where "commandline like '%%auto_scheduler.py%%' and name='python.exe'" get processid 2>nul | findstr /r "[0-9]" >nul
if not errorlevel 1 (
    echo [%date% %time%] [SKIP] auto_scheduler.py is already running. >> "%LOGFILE%"
    exit /b 0
)

echo [%date% %time%] Starting Auto-Scheduler... >> "%LOGFILE%"

:: ── Watchdog loop: restart if process dies unexpectedly ──
:: Max 5 restarts per session to avoid infinite crash loops
set RESTART_COUNT=0
set MAX_RESTARTS=5

:loop
set /a RESTART_COUNT+=1
if %RESTART_COUNT% gtr %MAX_RESTARTS% (
    echo [%date% %time%] [ABORT] Max restarts (%MAX_RESTARTS%) reached. Giving up. >> "%LOGFILE%"
    exit /b 1
)

if %RESTART_COUNT% gtr 1 (
    echo [%date% %time%] [RESTART] Attempt %RESTART_COUNT%/%MAX_RESTARTS% — waiting 30s... >> "%LOGFILE%"
    timeout /t 30 /nobreak >nul
)

echo [%date% %time%] [RUN] Starting auto_scheduler.py (attempt %RESTART_COUNT%) >> "%LOGFILE%"
cd /d "%PROJECT%"
"%PYTHON%" -u "%SCRIPT%"

:: If we reach here, the process exited
echo [%date% %time%] [EXIT] auto_scheduler.py exited with code %ERRORLEVEL% >> "%LOGFILE%"

:: Only restart if it exited abnormally (non-zero) and during working hours
for /f "tokens=1 delims=:" %%h in ("%time: =0%") do set HOUR=%%h
if %ERRORLEVEL% neq 0 (
    if %HOUR% geq 8 if %HOUR% leq 18 (
        echo [%date% %time%] [WARN] Abnormal exit during working hours, restarting... >> "%LOGFILE%"
        goto loop
    )
)

echo [%date% %time%] [DONE] Scheduler exited normally or outside working hours. >> "%LOGFILE%"
