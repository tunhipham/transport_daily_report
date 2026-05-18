@echo off
chcp 65001 >nul
cd /d "g:\My Drive\DOCS\transport_daily_report"

REM ════════════════════════════════════════════════
REM  NSO Auto Pipeline — mode-based
REM  Manual: auto_nso_watch.bat [scan|finalize]
REM  Auto:   detects mode from day+time
REM  Scan windows: T2 10h, T2 15h, T3 9h (all same logic)
REM  Finalize:     T3 9h30
REM ════════════════════════════════════════════════

set MODE=%~1
if not "%MODE%"=="" goto :mode_ready

REM ═══ Auto-detect mode ═══
for /f %%d in ('powershell -nologo -noprofile -command "(Get-Date).DayOfWeek"') do set DOW=%%d
for /f %%h in ('powershell -nologo -noprofile -command "(Get-Date).Hour"') do set HOUR=%%h
for /f %%m in ('powershell -nologo -noprofile -command "(Get-Date).Minute"') do set MIN=%%m

if not "%DOW%"=="Tuesday" goto :mode_scan

REM Tuesday: 9:25+ → finalize, else → scan
if %HOUR% LSS 9 goto :mode_scan
if %HOUR% GEQ 10 goto :mode_finalize
if %MIN% GEQ 25 goto :mode_finalize
goto :mode_scan

:mode_scan
set MODE=scan
goto :mode_ready

:mode_finalize
set MODE=finalize
goto :mode_ready

:mode_ready
echo ════════════════════════════════════════
echo   NSO Auto — %MODE% — %date% %time%
echo ════════════════════════════════════════

if "%MODE%"=="finalize" goto :do_finalize
if "%MODE%"=="scan" goto :do_scan

echo   Unknown mode: %MODE%
echo   Usage: auto_nso_watch.bat [scan^|finalize]
goto :done

REM ─── MODE: scan ───
REM T2 10h / T2 15h / T3 9h: Scan + conditional Telegram group + remind
:do_scan
echo.
echo   [1/3] Scanning NSO mail...
python -u script/domains/nso/fetch_nso_mail.py
if errorlevel 1 goto :done

REM Check flags for telegram group decision
set MAIL_PROC=0
if exist "output\state\nso\.mail_processed" set /p MAIL_PROC=<"output\state\nso\.mail_processed"
set HAS_CHG=0
if exist "output\state\nso\.has_changes" set /p HAS_CHG=<"output\state\nso\.has_changes"

if "%MAIL_PROC%"=="1" goto :send_tele
if "%HAS_CHG%"=="1" goto :send_tele
goto :skip_tele

:send_tele
echo.
echo   [2/3] Sending Telegram group summary...
python -u script/domains/nso/generate.py --send-telegram --no-deploy
goto :do_remind

:skip_tele
echo.
echo   [2/3] No new mail or changes — skipping Telegram group

:do_remind
echo.
echo   [3/3] Sending personal reminder...
python -u script/domains/nso/nso_remind.py
goto :done

REM ─── MODE: finalize ───
REM Tue 09:30: Final deploy + generate cham hang Excel (local only)
:do_finalize
echo.
echo   [1/2] Final NSO export + deploy...
python -u script/dashboard/export_data.py --domain nso
python -u script/dashboard/deploy.py --domain nso

echo.
echo   [2/2] Generating cham hang Excel...
python -u script/domains/weekly_plan/generate_excel.py
goto :done

:done
echo.
echo   ════════════════════════════════════════
echo   Pipeline: fetch_nso_mail → nso_stores.json → export nso.json → deploy → generate → telegram/remind
echo   Done — %date% %time%
echo   ════════════════════════════════════════
