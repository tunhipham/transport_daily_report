@echo off
title NSO Scan - Paste Mail
setlocal enabledelayedexpansion
chcp 65001 >nul

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

cd /d "G:\My Drive\DOCS\transport_daily_report"

echo.
echo  =============================================
echo    NSO Scan - Copy Mail Mode
echo    Paste noi dung mail NSO vao file text
echo  =============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    pause
    exit /b 1
)

REM Determine week number
for /f %%w in ('powershell -nologo -noprofile -command "(Get-Culture).Calendar.GetWeekOfYear((Get-Date), [System.Globalization.CalendarWeekRule]::FirstFourDayWeek, [DayOfWeek]::Monday)"') do set WEEK_NUM=%%w

set "MAIL_FILE=data\nso\mail_w%WEEK_NUM%.txt"

echo  Week: W%WEEK_NUM%
echo  Mail file: %MAIL_FILE%
echo.

REM Check if mail file already exists
if exist "%MAIL_FILE%" (
    echo  [INFO] File %MAIL_FILE% da ton tai.
    echo.
    set /p "OVERWRITE=  [Y] Ghi de, [N] Dung file cu, [Q] Thoat: "
    if /i "!OVERWRITE!"=="Q" (
        echo  Thoat.
        pause
        exit /b 0
    )
    if /i "!OVERWRITE!"=="N" (
        echo.
        echo  Dung file mail co san...
        goto :run_pipeline
    )
    echo.
)

REM Create file and open Notepad for paste
echo  Mo Notepad de paste mail...
echo.
echo  1. PASTE noi dung mail NSO vao Notepad
echo  2. LUU lai - Ctrl+S
echo  3. DONG Notepad de tiep tuc
echo.

REM Create empty UTF-8 file
powershell -nologo -noprofile -command "[System.IO.File]::WriteAllText((Join-Path '%CD%' '%MAIL_FILE%'), '', [System.Text.UTF8Encoding]::new($true))"

REM Open in notepad and wait for it to close
start /wait notepad "%MAIL_FILE%"

REM Verify file has content
for %%A in ("%MAIL_FILE%") do set FILE_SIZE=%%~zA
if "%FILE_SIZE%"=="" set FILE_SIZE=0
if %FILE_SIZE% LSS 50 (
    echo.
    echo  [ERROR] File trong hoac qua nho - %FILE_SIZE% bytes
    echo.
    set /p "RETRY=  [R] Mo lai Notepad, [Q] Thoat: "
    if /i "!RETRY!"=="R" (
        start /wait notepad "%MAIL_FILE%"
        for %%A in ("%MAIL_FILE%") do set FILE_SIZE=%%~zA
        if !FILE_SIZE! LSS 50 (
            echo  [ERROR] Van trong. Thoat.
            pause
            exit /b 1
        )
    ) else (
        pause
        exit /b 1
    )
)

echo.
echo  File saved: %FILE_SIZE% bytes

:run_pipeline
echo.
echo  ============================================
echo   Parse mail + Merge master + Deploy
echo  ============================================
echo.

python -u script\domains\nso\inject_mail_text.py --file "%MAIL_FILE%"

if errorlevel 1 (
    echo.
    echo  [ERROR] Pipeline failed! Check error above.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Gui Telegram?
echo  ============================================
echo.
set /p "SEND_TELE=  [Y] Gui Telegram, [N] Bo qua: "
if /i "!SEND_TELE!"=="Y" (
    echo.
    echo  Sending...
    python -u script\domains\nso\inject_mail_text.py --send-only
) else (
    echo.
    echo  [SKIP] Telegram skipped.
)

echo.
echo  ============================================
echo   [OK] NSO Scan Done!
echo  ============================================
echo.
echo  - Master:    data\nso\nso_stores.json
echo  - Calendar:  output\state\nso\nso_calendar.png
echo  - Dashboard: https://tunhipham.github.io/transport_daily_report/
echo.

pause
