@echo off
title Metabase Server

echo.
echo  ===========================================
echo    Metabase v0.60.3
echo    http://localhost:3000
echo    Login: admin@kfm.local
echo  ===========================================
echo.

REM Check if already running
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue) { Write-Host '  Metabase already running at :3000'; Start-Process 'http://localhost:3000'; exit 0 } else { exit 1 }"
if %errorlevel% equ 0 goto :done

REM Refresh PATH for Java
set "PATH=%PATH%;C:\Program Files\Microsoft\jdk-21.0.11.9-hotspot\bin"

REM Check Java
java --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Java not found!
    echo  Install: winget install Microsoft.OpenJDK.21
    pause
    exit /b 1
)

REM Check metabase.jar
if not exist "C:\metabase\metabase.jar" (
    echo  [ERROR] metabase.jar not found at C:\metabase\
    pause
    exit /b 1
)

REM Set PostgreSQL backend
set MB_DB_TYPE=postgres
set MB_DB_DBNAME=metabase
set MB_DB_PORT=5432
set MB_DB_USER=metabase
set MB_DB_PASS=metabase123
set MB_DB_HOST=localhost

echo  Starting Metabase...

REM Auto-open browser
start "" /min cmd /c "timeout /t 15 >nul & start http://localhost:3000"

cd /d C:\metabase
java -jar metabase.jar

:done
pause
