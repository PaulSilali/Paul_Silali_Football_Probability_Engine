@echo off
REM Quick Start Database Population Script
REM Database: football_probability_engine
REM Password: 11403775411

echo ========================================
echo Database Population - Quick Start
echo ========================================
echo.

cd /d "%~dp0"

REM Set PostgreSQL password
set PGPASSWORD=11403775411

REM Step 1: Apply schema enhancements
echo [1/2] Applying schema enhancements...
psql -U postgres -d football_probability_engine -f schema_enhancements.sql
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Schema enhancements may have failed or already applied
    echo Continuing anyway...
)
echo.

REM Step 2: Populate database
echo [2/2] Populating database...
if not exist "..\01_extruction_Script\output\matches_extracted.csv" (
    echo ERROR: CSV file not found!
    echo Expected: ..\01_extruction_Script\output\matches_extracted.csv
    echo.
    echo Please run the extraction script first:
    echo   cd ..\01_extruction_Script
    echo   run_extraction.bat
    pause
    exit /b 1
)

python populate_database.py --csv ..\01_extruction_Script\output\matches_extracted.csv --db-url postgresql://postgres:11403775411@localhost/football_probability_engine

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Population completed successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo   1. Check population_report.json for details
    echo   2. Verify data in database using SQL queries
    echo   3. Train models using the populated data
) else (
    echo.
    echo ========================================
    echo Population failed!
    echo ========================================
    echo.
    echo Check the error messages above.
    echo Common issues:
    echo   - PostgreSQL not running
    echo   - Wrong password or database name
    echo   - Schema not applied
    echo   - Missing Python packages (psycopg2-binary)
)

pause

