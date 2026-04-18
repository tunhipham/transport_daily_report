@echo off
REM ══════════════════════════════════════════════════════════
REM  Auto Compose Task - launched by Task Scheduler
REM  Uses --watch mode (long-running poll loop).
REM  Script itself handles instance locking via lock file.
REM ══════════════════════════════════════════════════════════
cd /d "g:\My Drive\DOCS\transport_daily_report"
python "script\compose\auto_compose.py" --watch
