@echo off
REM Database Rebuild Script for Windows
REM This script rebuilds the entire database from scratch

echo ========================================
echo DATABASE REBUILD SCRIPT
echo ========================================
echo.
echo WARNING: This will DROP all existing data!
echo.
echo Make sure you have:
echo 1. Backed up your database
echo 2. All migration files are in the migrations folder
echo 3. PostgreSQL is running
echo.
pause

cd /d "%~dp0"

echo.
echo Step 1: Dropping existing database...
psql -U postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'football_probability_engine' AND pid <> pg_backend_pid();"
psql -U postgres -c "DROP DATABASE IF EXISTS football_probability_engine;"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to drop database
    pause
    exit /b 1
)

echo.
echo Step 2: Creating new database...
psql -U postgres -c "CREATE DATABASE football_probability_engine WITH OWNER = postgres ENCODING = 'UTF8';"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create database
    pause
    exit /b 1
)

echo.
echo Step 3: Running main schema...
psql -U postgres -d football_probability_engine -f "3_Database_Football_Probability_Engine.sql"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to run main schema
    pause
    exit /b 1
)

echo.
echo Step 4: Running migrations...
echo Running: 4_ALL_LEAGUES_FOOTBALL_DATA.sql
psql -U postgres -d football_probability_engine -f "migrations\4_ALL_LEAGUES_FOOTBALL_DATA.sql"

echo Running: 2025_01_draw_structural_extensions.sql
psql -U postgres -d football_probability_engine -f "migrations\2025_01_draw_structural_extensions.sql"

echo Running: 2025_01_add_historical_tables.sql
psql -U postgres -d football_probability_engine -f "migrations\2025_01_add_historical_tables.sql"

echo Running: 2025_01_add_league_structure.sql
psql -U postgres -d football_probability_engine -f "migrations\2025_01_add_league_structure.sql"

echo Running: 2025_01_add_odds_movement_historical.sql
psql -U postgres -d football_probability_engine -f "migrations\2025_01_add_odds_movement_historical.sql"

echo Running: 2025_01_add_xg_data.sql
psql -U postgres -d football_probability_engine -f "migrations\2025_01_add_xg_data.sql"

echo Running: add_h2h_stats.sql
psql -U postgres -d football_probability_engine -f "migrations\add_h2h_stats.sql"

echo Running: add_saved_jackpot_templates.sql
psql -U postgres -d football_probability_engine -f "migrations\add_saved_jackpot_templates.sql"

echo Running: add_saved_probability_results.sql
psql -U postgres -d football_probability_engine -f "migrations\add_saved_probability_results.sql"

echo Running: add_entropy_metrics.sql
psql -U postgres -d football_probability_engine -f "migrations\add_entropy_metrics.sql"

echo Running: add_unique_partial_index_models.sql
psql -U postgres -d football_probability_engine -f "migrations\add_unique_partial_index_models.sql"

echo Running: add_draw_model_support.sql
psql -U postgres -d football_probability_engine -f "migrations\add_draw_model_support.sql"

echo Running: fix_matchresult_enum.sql
psql -U postgres -d football_probability_engine -f "migrations\fix_matchresult_enum.sql"

echo.
echo ========================================
echo Database rebuild completed!
echo ========================================
echo.
echo Next steps:
echo 1. Run data extraction: extract_football_data.py
echo 2. Run data population: populate_database.py
echo 3. Run model training: update_teams_ratings.py
echo 4. Run league statistics: update_league_statistics.py
echo.
pause

