@echo off
REM Simple Database Population - Run from this directory

echo ========================================
echo Populating Database
echo ========================================
echo.

REM Set working directory
cd /d "%~dp0"

REM Check CSV exists
if not exist "..\01_extruction_Script\output\matches_extracted.csv" (
    echo ERROR: CSV file not found!
    echo.
    echo Please run extraction first:
    echo   cd ..\01_extruction_Script
    echo   run_extraction.bat
    pause
    exit /b 1
)

echo Starting database population...
echo Database: football_probability_engine
echo.

python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"

pause

