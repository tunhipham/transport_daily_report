@echo off
REM ══════════════════════════════════════════════════════════
REM  Telegram Mention Watcher - launched by Task Scheduler
REM  Auto-restarts if process crashes (e.g. from sleep,
REM  network drop, memory pressure, etc.)
REM ══════════════════════════════════════════════════════════
cd /d "g:\My Drive\DOCS\transport_daily_report"

:loop
echo [%date% %time%] Starting mention watcher...
python "script\telegram\mention_watcher.py"
echo [%date% %time%] Mention watcher exited (code %ERRORLEVEL%), restarting in 15s...
timeout /t 15 /nobreak >nul
goto loop
