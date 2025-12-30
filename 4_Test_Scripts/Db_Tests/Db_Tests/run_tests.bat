@echo off
REM Run all tests script for Windows

echo ==========================================
echo Football Probability Engine - Test Suite
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "test_database_schema.py" (
    echo Error: Please run this script from the Db_Tests directory
    exit /b 1
)

REM Run Python tests
echo Running Python tests...
echo ----------------------------------------
python -m pytest . -v --tb=short

REM Check if frontend tests exist
if exist "test_frontend_logic.test.ts" (
    echo.
    echo Running TypeScript tests...
    echo ----------------------------------------
    REM Check if npx is available
    where npx >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        npx vitest run test_frontend_logic.test.ts
    ) else (
        echo ⚠ Skipping TypeScript tests (npx not available)
    )
)

echo.
echo ==========================================
echo Tests complete!
echo ==========================================

