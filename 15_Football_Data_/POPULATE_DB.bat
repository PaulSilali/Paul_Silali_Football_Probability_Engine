@echo off
REM Database Population Script
REM Run this from the 15_Football_Data_ folder

echo ========================================
echo Database Population
echo ========================================
echo.

cd /d "%~dp0\02_Db populating_Script"

REM Check if CSV exists
if not exist "..\01_extruction_Script\output\matches_extracted.csv" (
    echo ERROR: CSV file not found!
    echo Expected: ..\01_extruction_Script\output\matches_extracted.csv
    echo.
    echo Please run the extraction script first.
    pause
    exit /b 1
)

echo Database: football_probability_engine
echo CSV File: ..\01_extruction_Script\output\matches_extracted.csv
echo.

python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Database populated.
    echo ========================================
    echo.
    echo Check population_report.json for details.
) else (
    echo.
    echo ========================================
    echo ERROR: Population failed
    echo ========================================
    echo.
    echo Check error messages above.
)

pause

