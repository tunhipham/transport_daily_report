@echo off
REM ══════════════════════════════════════════════════════════
REM  Inventory Watch - launched by Task Scheduler on Mondays
REM  Uses --watch mode (long-running poll loop, 1h interval).
REM  Script itself handles instance locking via lock file.
REM ══════════════════════════════════════════════════════════
cd /d "g:\My Drive\DOCS\transport_daily_report"
python "script\dashboard\auto_inventory_watch.py" --watch
