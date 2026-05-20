@echo off
chcp 65001 >nul
echo ============================================================
echo   Trip Cutoff - Quyết định trips chưa hoàn thành
echo ============================================================
echo.
echo   Notepad sẽ mở danh sách trips.
echo   GIỮ dòng = cho on-time
echo   XÓA dòng = bỏ (exclude)
echo   Save + đóng Notepad → tự generate report
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"
python script\data_pipeline\trip_cutoff.py %*

echo.
echo Done. Press any key to close...
pause >nul
