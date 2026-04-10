@echo off
REM Auto Compose Mail - Scheduled Task Runner
REM Runs auto_compose.py to check delivery data and compose emails
REM Called by Windows Task Scheduler every 15 minutes (12:00-20:00)

cd /d "c:\Users\admin\Downloads\transport_daily_report"
"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe" -u script\auto_compose.py
