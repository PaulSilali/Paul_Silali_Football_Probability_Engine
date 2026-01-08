@echo off
REM Complete ETL Pipeline - Windows Batch Script
REM This script runs the complete extraction and population process
REM Usage: RUN_ALL.bat [db_url]

echo ========================================
echo Football Data ETL Pipeline
echo ========================================
echo.

REM Step 1: Extraction
echo [1/3] Running extraction...
cd /d "%~dp0\01_extruction_Script"
call run_extraction.bat
if %ERRORLEVEL% NEQ 0 (
    echo Extraction failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

REM Step 2: Schema Enhancements
echo.
echo [2/3] Applying schema enhancements...
cd /d "%~dp0\02_Db populating_Script"
if "%1"=="" (
    echo Database URL not provided. Skipping schema enhancements.
    echo You can run apply_schema_enhancements.bat manually.
) else (
    call apply_schema_enhancements.bat
    if %ERRORLEVEL% NEQ 0 (
        echo Schema enhancement failed! Continuing anyway...
    )
)

REM Step 3: Population
echo.
echo [3/3] Populating database...
if "%1"=="" (
    echo ERROR: Database URL required for population
    echo Usage: RUN_ALL.bat postgresql://user:pass@localhost/dbname
    echo.
    set /p DB_URL="Enter database URL: "
    call run_population.bat %DB_URL%
) else (
    call run_population.bat %1
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ETL Pipeline completed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ETL Pipeline failed at population step
    echo ========================================
)

pause

