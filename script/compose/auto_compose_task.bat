@echo off
REM ══════════════════════════════════════════════════════════
REM  Auto Compose Task - launched by Task Scheduler
REM  Uses --watch mode (long-running poll loop).
REM  Auto-restarts if watch process crashes (e.g. from sleep,
REM  Google Drive conflict, network timeout, etc.)
REM  Script itself handles instance locking via lock file.
REM ══════════════════════════════════════════════════════════
cd /d "g:\My Drive\DOCS\transport_daily_report"

:loop
echo [%date% %time%] Starting watch mode...
python "script\compose\auto_compose.py" --watch
echo [%date% %time%] Watch mode exited (code %ERRORLEVEL%), restarting in 30s...
timeout /t 30 /nobreak >nul
goto loop
