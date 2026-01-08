@echo off
REM Run Updates for Leagues and Teams Tables
echo ========================================
echo Updating Leagues and Teams Tables
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Updating League Statistics...
echo ----------------------------------------
python update_league_statistics.py --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: League statistics update failed
    pause
    exit /b 1
)

echo.
echo Step 2: Updating Team Ratings (Training Model)...
echo ----------------------------------------
echo WARNING: This will train the model and may take several minutes...
echo.
pause

python update_teams_ratings.py --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Team ratings update failed
    pause
    exit /b 1
)

echo.
echo Step 3: Verifying Updates...
echo ----------------------------------------
python verify_updates.py --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"

echo.
echo ========================================
echo Updates Complete!
echo ========================================
pause

