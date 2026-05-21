@echo off
chcp 65001 >nul
cd /d "g:\My Drive\DOCS\transport_daily_report"
"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe" script\data_pipeline\sync_status.py
echo.
pause
