@echo off
chcp 65001 >nul 2>&1
cls

echo.
echo ================================================================
echo           Redis Server - Clean Startup Script
echo ================================================================
echo   Press Ctrl+C to gracefully shutdown Redis
echo ================================================================
echo.

rem Change to script directory
cd /d "%~dp0"

rem ========================================
rem Pre-flight checks
rem ========================================

echo [1/4] Checking redis-server.exe...
if not exist "redis-server.exe" (
    echo [ERROR] redis-server.exe not found in current directory!
    echo         Path: %CD%
    pause
    exit /b 1
)
echo       OK

echo [2/4] Checking redis.conf...
if not exist "redis.conf" (
    echo [ERROR] redis.conf not found in current directory!
    pause
    exit /b 1
)
echo       OK

echo [3/4] Checking if Redis is already running...
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | findstr /I "redis-server.exe" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [ERROR] Redis is already running!
    echo         Please stop the existing instance first.
    echo.
    echo         To stop: taskkill /IM redis-server.exe /F
    pause
    exit /b 1
)
echo       OK

echo [4/4] Checking port 6379...
netstat -ano 2>NUL | findstr ":6379.*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [ERROR] Port 6379 is already in use!
    echo         Find the process: netstat -ano ^| findstr :6379
    pause
    exit /b 1
)
echo       OK

echo.
echo ================================================================
echo   Starting Redis Server...
echo ================================================================
echo.
echo   Host: 127.0.0.1
echo   Port: 6379
echo   Config: %CD%\redis.conf
echo   Data: %CD%
echo.
echo   [Ctrl+C] Graceful Shutdown
echo.
echo ----------------------------------------------------------------
echo.

rem Run Redis in foreground - Using PowerShell to handle Ctrl+C without prompt
powershell -NoProfile -ExecutionPolicy Bypass -Command ".\redis-server.exe redis.conf"

rem This line runs after Redis exits
echo.
echo ================================================================
echo   Redis Server Stopped
echo ================================================================
echo.
