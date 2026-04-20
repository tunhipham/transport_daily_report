@echo off
chcp 65001 >nul
cd /d "g:\My Drive\DOCS\transport_daily_report"
echo ════════════════════════════════════════
echo   NSO Mail Scanner — %date% %time%
echo ════════════════════════════════════════
python script/domains/nso/fetch_nso_mail.py %*
echo.
echo Done. Press any key to close...
pause >nul
