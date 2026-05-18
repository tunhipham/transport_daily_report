@echo off
chcp 65001 >nul
echo ==============================================================
echo        XUAT FILE EXCEL VA DEPLOY LICH TUAN (DASHBOARD)
echo ==============================================================
set /p week="Nhap so Tuan can update (VD: 21): "

echo.
echo [1/3]: Dang tao file Excel cho Tuan %week%...
python script\domains\weekly_plan\generate_excel.py --week %week%

echo.
echo [2/3]: Dang export du lieu ra JSON dashboard...
python script\dashboard\export_weekly_plan.py

echo.
echo [3/3]: Dang deploy len GitHub Pages...
python script\dashboard\deploy.py --domain weekly_plan

echo.
echo ==============================================================
echo HOAN TAT! Dashboard se duoc cap nhat trong vai phut toi.
echo ==============================================================
pause
