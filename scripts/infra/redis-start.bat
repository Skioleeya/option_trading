@echo off
REM ============================================================================
REM Redis Server Start Script for SPY 0DTE Dashboard
REM ============================================================================

set REDIS_BIN=%~dp0..\..\infra\bin\redis-server.exe
set REDIS_CONF=%~dp0..\..\infra\redis\redis.conf.local

echo [Redis] Checking binary...
if not exist "%REDIS_BIN%" (
    echo [ERROR] redis-server.exe not found at %REDIS_BIN%
    echo [ERROR] Please download Redis for Windows and place it in infra\bin\
    exit /b 1
)

echo [Redis] Checking config...
if not exist "%REDIS_CONF%" (
    echo [ERROR] redis.conf.local not found at %REDIS_CONF%
    exit /b 1
)

echo [Redis] Starting on port 6380...
echo ============================================
"%REDIS_BIN%" "%REDIS_CONF%"
