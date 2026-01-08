@echo off
REM Update League Statistics Script
REM Updates avg_draw_rate and home_advantage for all leagues

echo ========================================
echo Update League Statistics
echo ========================================
echo.
echo This will update avg_draw_rate and home_advantage
echo for all leagues based on match data (last 5 years).
echo.
echo This may take a few minutes...
echo.
pause

cd /d "%~dp0"

python update_league_statistics.py --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! League statistics updated.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Update failed
    echo ========================================
    echo.
    echo Check error messages above.
)

echo.
pause

