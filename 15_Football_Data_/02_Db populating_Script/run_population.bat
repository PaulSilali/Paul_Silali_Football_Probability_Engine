@echo off
REM Database Population Script
REM Run this file to populate the database

echo ========================================
echo Database Population
echo ========================================
echo.
echo This will populate the football_probability_engine database
echo with 103,983 matches from the extracted CSV file.
echo.
echo This may take several minutes to complete...
echo.
pause

cd /d "%~dp0"

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

echo.
pause
