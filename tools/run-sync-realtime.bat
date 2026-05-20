@echo off
chcp 65001 >nul
echo ============================================================
echo   Sync Realtime — Manual Run
echo ============================================================

cd /d "G:\My Drive\DOCS\transport_daily_report"
python script\data_pipeline\sync_realtime.py %*

echo.
echo Done. Press any key to close...
pause >nul
