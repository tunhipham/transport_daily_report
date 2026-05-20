@echo off
title Backup Inject - DRY Sang + DRY Toi
chcp 65001 >nul 2>&1

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Backup Inject - DRY Sang + DRY Toi
echo    Compose + Inject thu cong sau cutoff
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

REM ==========================================
REM  Step 1: Check status
REM ==========================================
echo  [Step 1] Kiem tra status cac kho...
echo  -------------------------------------------
echo.
python -u script\compose\auto_compose.py --status
echo.
echo  -------------------------------------------
echo.

REM ==========================================
REM  Step 2: Calculate dates and week
REM ==========================================
echo  [Step 2] Tinh ngay giao va tuan...
echo.

REM DRY Sang = D+1
for /f "delims=" %%i in ('python -c "from datetime import date,timedelta;d=date.today()+timedelta(days=1);print(str(d.day).zfill(2)+chr(47)+str(d.month).zfill(2)+chr(47)+str(d.year))"') do set "DATE_SANG=%%i"

REM DRY Toi = D (hom nay)
for /f "delims=" %%i in ('python -c "from datetime import date;d=date.today();print(str(d.day).zfill(2)+chr(47)+str(d.month).zfill(2)+chr(47)+str(d.year))"') do set "DATE_TOI=%%i"

REM Week
for /f "delims=" %%i in ('python -c "from datetime import date;print(chr(87)+str(date.today().isocalendar()[1]))"') do set "DEFAULT_WEEK=%%i"

echo  Hom nay: %date%
echo  DRY Sang (D+1): %DATE_SANG%
echo  DRY Toi  (D):   %DATE_TOI%
echo  Tuan:           %DEFAULT_WEEK%
echo.

set /p WEEK_NUM="  Tuan [%DEFAULT_WEEK%]: "
if "%WEEK_NUM%"=="" set "WEEK_NUM=%DEFAULT_WEEK%"

echo.
echo  ============================================
echo   DRY Sang date: %DATE_SANG%
echo   DRY Toi date:  %DATE_TOI%
echo   Tuan:          %WEEK_NUM%
echo  ============================================
echo.

REM ==========================================
REM  Step 3: Fetch data cho ca 2 ngay
REM ==========================================
echo  [Step 3] Fetch data...
echo  -------------------------------------------
echo.
echo  Fetch DRY Sang (date=%DATE_SANG%)...
python -u script\domains\performance\fetch_weekly.py --week %WEEK_NUM% --date %DATE_SANG%
if errorlevel 1 (
    echo  [ERROR] Fetch data DRY Sang that bai!
    pause
    exit /b 1
)
echo.
echo  Fetch DRY Toi (date=%DATE_TOI%)...
python -u script\domains\performance\fetch_weekly.py --week %WEEK_NUM% --date %DATE_TOI%
if errorlevel 1 (
    echo  [ERROR] Fetch data DRY Toi that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] Data fetched!
echo.

REM ==========================================
REM  Step 4: Compose + Inject DRY Sang
REM ==========================================
echo.
echo  --------------------------------------
echo   COMPOSE: DRY Sang (date=%DATE_SANG%)
echo  --------------------------------------
python -u script\compose\compose_mail.py --kho DRY --session sang --date %DATE_SANG%
if errorlevel 1 (
    echo  [ERROR] Compose DRY Sang that bai!
    pause
    exit /b 1
)
echo.
echo  --------------------------------------
echo   INJECT: DRY Sang (date=%DATE_SANG%)
echo  --------------------------------------
python -u script\compose\inject_haraworks.py --kho DRY --session sang --date %DATE_SANG% --week %WEEK_NUM%
if errorlevel 1 (
    echo  [ERROR] Inject DRY Sang that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] DRY Sang done!
echo.

REM ==========================================
REM  Step 5: Compose + Inject DRY Toi
REM ==========================================
echo.
echo  --------------------------------------
echo   COMPOSE: DRY Toi (date=%DATE_TOI%)
echo  --------------------------------------
python -u script\compose\compose_mail.py --kho DRY --session toi --date %DATE_TOI%
if errorlevel 1 (
    echo  [ERROR] Compose DRY Toi that bai!
    pause
    exit /b 1
)
echo.
echo  --------------------------------------
echo   INJECT: DRY Toi (date=%DATE_TOI%)
echo  --------------------------------------
python -u script\compose\inject_haraworks.py --kho DRY --session toi --date %DATE_TOI% --week %WEEK_NUM%
if errorlevel 1 (
    echo  [ERROR] Inject DRY Toi that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] DRY Toi done!
echo.

REM ==========================================
REM  DONE
REM ==========================================
echo.
echo  ===========================================
echo    HOAN TAT! DRY Sang + DRY Toi
echo  ===========================================
echo.
echo  Vao Haraworks kiem tra draft roi gui.
echo.
pause
