@echo off
REM Test Runner Script for Frontend Tests (Windows)

echo ==========================================
echo Football Probability Engine - Test Suite
echo ==========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js first.
    exit /b 1
)

REM Navigate to frontend directory
cd ..\1_Frontend_Football_Probability_Engine
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not navigate to frontend directory
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    call npm install
)

REM Check if backend is running
echo [INFO] Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend is running
) else (
    echo [WARNING] Backend is not running. Some tests may fail.
    echo [INFO] Start backend with: cd 2_Backend_Football_Probability_Engine ^&^& python run.py
)

echo.
echo [INFO] Running tests...
echo.

REM Run tests
call npm test -- --coverage

echo.
echo ==========================================
echo Test execution complete
echo ==========================================
pause

