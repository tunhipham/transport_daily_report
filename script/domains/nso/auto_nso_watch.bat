@echo off
chcp 65001 >nul
cd /d "g:\My Drive\DOCS\transport_daily_report"
echo ════════════════════════════════════════
echo   NSO Mail Scanner — %date% %time%
echo ════════════════════════════════════════

REM Step 1: Scan NSO emails (Mon + Tue)
python script/domains/nso/fetch_nso_mail.py %*

REM Step 2: Regenerate dashboard + send Telegram on Tuesday
for /f %%d in ('powershell -nologo -noprofile -command "(Get-Date).DayOfWeek"') do set DOW=%%d
if "%DOW%"=="Tuesday" (
    echo.
    echo   ══════════════════════════════════════
    echo   NSO Dashboard Generate + Telegram
    echo   ══════════════════════════════════════
    python script/domains/nso/generate.py --send-telegram
) else (
    echo.
    echo   Regenerating dashboard (no Telegram)...
    python script/domains/nso/generate.py
)

echo.
echo Done. Press any key to close...
pause >nul
