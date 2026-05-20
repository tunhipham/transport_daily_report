@echo off
chcp 65001 >nul
echo ============================================================
echo   Trip Reminder — Monday 8:00 AM
echo ============================================================

cd /d "G:\My Drive\DOCS\transport_daily_report"
python script\telegram\trip_reminder.py

echo.
echo Done. Press any key to close...
pause >nul
