@echo off
REM Apply Schema Enhancements - Windows Batch Script
REM Usage: apply_schema_enhancements.bat [db_name] [user] [host]
REM Example: apply_schema_enhancements.bat football_probability_engine postgres localhost

echo ========================================
echo Apply Schema Enhancements
echo ========================================
echo.

cd /d "%~dp0"

if "%1"=="" (
    set DB_NAME=football_probability_engine
) else (
    set DB_NAME=%1
)

if "%2"=="" (
    set DB_USER=postgres
) else (
    set DB_USER=%2
)

if "%3"=="" (
    set DB_HOST=localhost
) else (
    set DB_HOST=%3
)

echo Database: %DB_NAME%
echo User: %DB_USER%
echo Host: %DB_HOST%
echo.

REM Check if psql is available
where psql >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: psql command not found!
    echo Please ensure PostgreSQL is installed and in your PATH.
    echo.
    echo Alternative: Run the SQL file manually in pgAdmin or another SQL client:
    echo   File: schema_enhancements.sql
    pause
    exit /b 1
)

echo Applying schema enhancements...
psql -h %DB_HOST% -U %DB_USER% -d %DB_NAME% -f schema_enhancements.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Schema enhancements applied successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Schema enhancement failed!
    echo ========================================
    pause
    exit /b %ERRORLEVEL%
)

pause

