@echo off
chcp 65001 >nul 2>&1

echo.
echo ================================================================
echo           Redis Server - Stop Script
echo ================================================================
echo.

rem Check if Redis is running
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | findstr /I "redis-server.exe" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Redis is not running.
    goto :end
)

echo [INFO] Stopping Redis server...

rem Graceful stop using taskkill
taskkill /IM redis-server.exe >nul 2>&1

rem Wait and verify
timeout /t 2 /nobreak >nul 2>&1

tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | findstr /I "redis-server.exe" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [WARN] Redis still running, forcing termination...
    taskkill /IM redis-server.exe /F >nul 2>&1
    timeout /t 1 /nobreak >nul 2>&1
)

echo.
echo [OK] Redis server stopped.

:end
echo.
