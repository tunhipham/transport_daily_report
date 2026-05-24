@echo off
title Backup Inject - Haraworks Mail
chcp 65001 >nul 2>&1

REM Add Python to PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python310"

echo.
echo  ===========================================
echo    Backup Inject - Haraworks Mail
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
python -u script\compose\auto_compose.py --status < nul
echo.
echo  -------------------------------------------
echo.

REM ==========================================
REM  Step 2: Calculate D+1 and Week via Python
REM ==========================================
echo  [Step 2] Tinh ngay giao va tuan...
echo.

for /f "delims=" %%i in ('python -c "from datetime import date,timedelta;d=date.today()+timedelta(days=1);print(str(d.day).zfill(2)+chr(47)+str(d.month).zfill(2)+chr(47)+str(d.year))"') do set "DEFAULT_DATE=%%i"

for /f "delims=" %%i in ('python -c "from datetime import date;print(chr(87)+str(date.today().isocalendar()[1]))"') do set "DEFAULT_WEEK=%%i"

echo  Hom nay: %date%
echo  D+1 mac dinh: %DEFAULT_DATE%
echo  Tuan mac dinh: %DEFAULT_WEEK%
echo.

set /p DELIVERY_DATE="  Ngay giao hang [%DEFAULT_DATE%]: "
if "%DELIVERY_DATE%"=="" set "DELIVERY_DATE=%DEFAULT_DATE%"

set /p WEEK_NUM="  Tuan [%DEFAULT_WEEK%]: "
if "%WEEK_NUM%"=="" set "WEEK_NUM=%DEFAULT_WEEK%"

echo.
echo  ============================================
echo   Ngay giao: %DELIVERY_DATE%
echo   Tuan:      %WEEK_NUM%
echo  ============================================
echo.

REM ==========================================
REM  Step 2b: Fetch data
REM ==========================================
echo  [Step 2b] Fetch data ngay %DELIVERY_DATE%...
echo  -------------------------------------------
echo.
python -u script\domains\performance\fetch_weekly.py --week %WEEK_NUM% --date %DELIVERY_DATE% < nul
if errorlevel 1 (
    echo  [ERROR] Fetch data that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] Data fetched!
echo.

REM ==========================================
REM  Step 3: Determine which kho to process
REM ==========================================

if not "%~1"=="" goto :PARSE_ARG

echo  [Step 3] Chon kho can backup inject
echo.
echo    1. KRC
echo    2. DONG MAT
echo    3. THIT CA
echo    4. DRY Sang
echo    5. DRY Toi
echo    6. Tat ca
echo    0. Thoat
echo.
set /p KHO_CHOICE="  Chon (1-6): "

if "%KHO_CHOICE%"=="0" (
    echo  [CANCELLED]
    pause
    exit /b 0
)

echo.
echo  BAT DAU COMPOSE + INJECT
echo.

echo %KHO_CHOICE% | findstr "6" >nul && goto :ALL_KHO

for %%s in (%KHO_CHOICE%) do (
    if "%%s"=="1" call :DO_KHO KRC
    if "%%s"=="2" call :DO_KHO "DONG MAT"
    if "%%s"=="3" call :DO_KHO "THIT CA"
    if "%%s"=="4" call :DO_KHO_DRY sang
    if "%%s"=="5" call :DO_KHO_DRY toi
)
goto :DONE

:PARSE_ARG
set "ARG=%~1"
echo.
echo  BAT DAU COMPOSE + INJECT: %ARG%
echo.

if /i "%ARG%"=="KRC"       ( call :DO_KHO KRC & goto :DONE )
if /i "%ARG%"=="DONG MAT"  ( call :DO_KHO "DONG MAT" & goto :DONE )
if /i "%ARG%"=="DONGMAT"   ( call :DO_KHO "DONG MAT" & goto :DONE )
if /i "%ARG%"=="DM"        ( call :DO_KHO "DONG MAT" & goto :DONE )
if /i "%ARG%"=="THIT CA"   ( call :DO_KHO "THIT CA" & goto :DONE )
if /i "%ARG%"=="THITCA"    ( call :DO_KHO "THIT CA" & goto :DONE )
if /i "%ARG%"=="TC"        ( call :DO_KHO "THIT CA" & goto :DONE )
if /i "%ARG%"=="DRY_SANG"  ( call :DO_KHO_DRY sang & goto :DONE )
if /i "%ARG%"=="DRY_TOI"   ( call :DO_KHO_DRY toi & goto :DONE )
if /i "%ARG%"=="ALL"        goto :ALL_KHO

echo  [ERROR] Khong biet kho: %ARG%
echo  Usage: run-backup-inject.bat [KRC / DM / TC / DRY_SANG / DRY_TOI / ALL]
pause
exit /b 1

:ALL_KHO
call :DO_KHO KRC
if errorlevel 1 goto :ERR
call :DO_KHO "DONG MAT"
if errorlevel 1 goto :ERR
call :DO_KHO "THIT CA"
if errorlevel 1 goto :ERR
call :DO_KHO_DRY sang
if errorlevel 1 goto :ERR
goto :DONE

:DO_KHO
echo.
echo  --------------------------------------
echo   COMPOSE: %~1
echo  --------------------------------------
python -u script\compose\compose_mail.py --kho %1 --date %DELIVERY_DATE%
if errorlevel 1 (
    echo  [ERROR] Compose %~1 that bai!
    pause
    exit /b 1
)
echo.
echo  --------------------------------------
echo   INJECT: %~1
echo  --------------------------------------
python -u script\compose\inject_haraworks.py --kho %1 --date %DELIVERY_DATE% --week %WEEK_NUM%
if errorlevel 1 (
    echo  [ERROR] Inject %~1 that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] %~1 done!
echo.
exit /b 0

:DO_KHO_DRY
echo.
echo  --------------------------------------
echo   COMPOSE: DRY %1
echo  --------------------------------------
python -u script\compose\compose_mail.py --kho DRY --session %1 --date %DELIVERY_DATE%
if errorlevel 1 (
    echo  [ERROR] Compose DRY %1 that bai!
    pause
    exit /b 1
)
echo.
echo  --------------------------------------
echo   INJECT: DRY %1
echo  --------------------------------------
python -u script\compose\inject_haraworks.py --kho DRY --session %1 --date %DELIVERY_DATE% --week %WEEK_NUM%
if errorlevel 1 (
    echo  [ERROR] Inject DRY %1 that bai!
    pause
    exit /b 1
)
echo.
echo  [OK] DRY %1 done!
echo.
exit /b 0

:ERR
echo.
echo  [ERROR] Co loi xay ra! Check output phia tren.
pause
exit /b 1

:DONE
echo.
echo  ===========================================
echo    HOAN TAT!
echo  ===========================================
echo.
echo  Vao Haraworks kiem tra draft roi gui.
echo.
pause
