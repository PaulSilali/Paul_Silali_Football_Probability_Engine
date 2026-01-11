@echo off
REM Run all tests and generate report
echo Running Football Probability Engine Test Suite...
echo.

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install pytest if not available
python -m pip install pytest --quiet

REM Run test suite
python run_all_tests.py

echo.
echo Test execution complete. Check TEST_REPORT.md for results.
pause

