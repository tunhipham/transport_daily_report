@echo off
chcp 65001 >nul
cd /d "G:\My Drive\DOCS\transport_daily_report"

echo ============================================================
echo   TRIP CUTOFF — TUESDAY 09:00
echo   %date% %time%
echo ============================================================

python -u script/telegram/trip_cutoff_export.py
pause
