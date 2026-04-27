@echo off
chcp 65001 >nul
cd /d "g:\My Drive\DOCS\transport_daily_report"

REM ════════════════════════════════════════════════
REM  NSO Auto Pipeline — mode-based
REM  Manual: auto_nso_watch.bat [scan|track|finalize]
REM  Auto:   detects mode from day+time
REM ════════════════════════════════════════════════

set MODE=%~1

REM Auto-detect mode if not specified
if "%MODE%"=="" (
    for /f %%d in ('powershell -nologo -noprofile -command "(Get-Date).DayOfWeek"') do set DOW=%%d
    for /f %%h in ('powershell -nologo -noprofile -command "(Get-Date).Hour"') do set HOUR=%%h

    if "%DOW%"=="Tuesday" (
        if %HOUR% GEQ 9 (
            if %HOUR% LSS 10 (
                REM Tue 09:00-09:59 could be scan or finalize
                for /f %%m in ('powershell -nologo -noprofile -command "(Get-Date).Minute"') do set MIN=%%m
                if %MIN% GEQ 25 (
                    set MODE=finalize
                ) else (
                    set MODE=scan
                )
            ) else (
                set MODE=finalize
            )
        ) else (
            set MODE=scan
        )
    ) else if "%DOW%"=="Monday" (
        if %HOUR% GEQ 14 (
            set MODE=track
        ) else (
            set MODE=scan
        )
    ) else (
        set MODE=scan
    )
)

echo ════════════════════════════════════════
echo   NSO Auto — %MODE% — %date% %time%
echo ════════════════════════════════════════

REM ─── MODE: scan ───
REM Mon 10:00 / Tue 09:00: Full scan + deploy + Telegram group + remind
if "%MODE%"=="scan" (
    echo.
    echo   [1/3] Scanning NSO mail...
    python -u script/domains/nso/fetch_nso_mail.py
    if errorlevel 1 goto :done

    echo.
    echo   [2/3] Sending Telegram group summary...
    python -u script/domains/nso/generate.py --send-telegram

    echo.
    echo   [3/3] Sending personal reminder...
    python -u script/domains/nso/nso_remind.py
    goto :done
)

REM ─── MODE: track ───
REM Mon 15:00: Re-scan, only deploy + notify if changes
if "%MODE%"=="track" (
    echo.
    echo   [1/2] Tracking NSO mail changes...
    python -u script/domains/nso/fetch_nso_mail.py --no-deploy

    REM Check if changes were found
    if exist "output\state\nso\.has_changes" (
        set /p HAS_CHANGES=<"output\state\nso\.has_changes"
    ) else (
        set HAS_CHANGES=0
    )
    if "%HAS_CHANGES%"=="1" (
        echo.
        echo   [2/2] Changes detected! Deploying + notifying...
        python -u script/dashboard/export_data.py --domain nso
        python -u script/dashboard/deploy.py --domain nso
        python -u script/domains/nso/generate.py --send-telegram
    ) else (
        echo.
        echo   [2/2] No changes detected. Skipping deploy.
    )
    goto :done
)

REM ─── MODE: finalize ───
REM Tue 09:30: Final deploy + generate cham hang Excel (local only)
if "%MODE%"=="finalize" (
    echo.
    echo   [1/2] Final NSO export + deploy...
    python -u script/dashboard/export_data.py --domain nso
    python -u script/dashboard/deploy.py --domain nso

    echo.
    echo   [2/2] Generating cham hang Excel...
    python -u script/domains/weekly_plan/generate_excel.py
    goto :done
)

echo   Unknown mode: %MODE%
echo   Usage: auto_nso_watch.bat [scan^|track^|finalize]

:done
echo.
echo   Done — %time%
echo ════════════════════════════════════════
