@echo off
REM Football Data Extraction - Windows Batch Script
REM Usage: run_extraction.bat

echo ========================================
echo Football Data Extraction
echo ========================================
echo.

cd /d "%~dp0"

python extract_football_data.py --data-dir .. --output-dir output

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Extraction completed successfully!
    echo Output: output\matches_extracted.csv
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Extraction failed with error code %ERRORLEVEL%
    echo ========================================
    pause
    exit /b %ERRORLEVEL%
)

pause

