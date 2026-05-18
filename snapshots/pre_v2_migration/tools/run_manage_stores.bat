@echo off
chcp 65001 >nul
echo ==============================================================
echo        QUAN LY SIEU THI NSO / MASTER SCHEDULE
echo ==============================================================
python script\domains\weekly_plan\manage_stores.py
echo.
pause
