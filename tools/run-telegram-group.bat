@echo off
title Telegram Group Creator - NSO
chcp 65001 >nul 2>&1

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Telegram Group Creator - NSO
echo    Tao group KRC / ABA / DC cho sieu thi moi
echo  ===========================================
echo.

cd /d "G:\My Drive\DOCS\transport_daily_report"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    pause
    exit /b 1
)

REM Check Telethon
python -c "import telethon" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Telethon not installed!
    echo  Run: pip install telethon
    pause
    exit /b 1
)

REM ==========================================
REM  Step 1: Check session
REM ==========================================
echo  [1/4] Checking Telegram session...
echo.
python -u script\telegram\_login.py --status
if errorlevel 1 (
    echo.
    echo  [ERROR] Chua login Telegram!
    echo  Chay thu cong:
    echo    python -u script\telegram\_login.py --send
    echo    python -u script\telegram\_login.py --code YOUR_OTP
    echo    python -u script\telegram\_login.py --password "YOUR_2FA"
    pause
    exit /b 1
)

REM ==========================================
REM  Step 2: Open Google Sheet
REM ==========================================
echo.
echo  [2/4] Mo Google Sheet de review data...
start "" "https://docs.google.com/spreadsheets/d/1EiqjBPu2zDBRRZhFxMNvVuBMPHqf902CR28naVyJxdU/edit"
timeout /t 3 >nul

REM ==========================================
REM  Step 3: Dry run (preview)
REM ==========================================
echo.
echo  [3/4] Dry run - Preview plan...
echo  ───────────────────────────────────────────
echo.
python -u script\telegram\batch_nso.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Dry run failed!
    pause
    exit /b 1
)

echo.
echo  ───────────────────────────────────────────
echo.
set /p CONFIRM="  Ban da review xong? Tao groups? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo  [CANCELLED] Khong tao group.
    pause
    exit /b 0
)

REM ==========================================
REM  Step 4: Execute
REM ==========================================
echo.
echo  [4/4] Dang tao groups + add members + DC notice...
echo  ───────────────────────────────────────────
echo.
python -u script\telegram\batch_nso.py --execute --notice
if errorlevel 1 (
    echo.
    echo  [ERROR] Co loi khi tao group! Check output phia tren.
    pause
    exit /b 1
)

echo.
echo  ===========================================
echo    [OK] HOAN TAT!
echo  ===========================================
echo.
echo  Kiem tra group tren Telegram hoac chay:
echo    python -u script\telegram\manage_group.py list
echo.

pause
