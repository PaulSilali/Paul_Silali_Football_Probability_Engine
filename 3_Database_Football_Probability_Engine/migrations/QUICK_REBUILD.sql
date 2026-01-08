-- ============================================================================
-- QUICK DATABASE REBUILD - COPY THIS INTO pgAdmin
-- ============================================================================
-- 
-- Instructions:
--   1. Open pgAdmin
--   2. Connect to PostgreSQL server
--   3. Right-click "Databases" → Query Tool
--   4. Run Step 1 (drop database)
--   5. Run Step 2 (create database)
--   6. Right-click new database → Query Tool
--   7. Use File → Open to load 3_Database_Football_Probability_Engine.sql
--   8. Execute (F5)
--   9. Use File → Open to load each migration file
--   10. Execute each migration
-- 
-- ============================================================================

-- ============================================================================
-- STEP 1: DROP EXISTING DATABASE
-- ============================================================================
-- Run this while connected to 'postgres' database

SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'football_probability_engine'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS football_probability_engine;

-- ============================================================================
-- STEP 2: CREATE NEW DATABASE
-- ============================================================================
-- Run this while connected to 'postgres' database

CREATE DATABASE football_probability_engine
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- ============================================================================
-- STEP 3: VERIFY DATABASE CREATED
-- ============================================================================
-- Run this to verify

SELECT datname FROM pg_database WHERE datname = 'football_probability_engine';

-- ============================================================================
-- STEP 4: NOW SWITCH TO NEW DATABASE
-- ============================================================================
-- In pgAdmin:
-- 1. Right-click "football_probability_engine" database
-- 2. Select "Query Tool"
-- 3. Use File → Open to load: 3_Database_Football_Probability_Engine.sql
-- 4. Execute (F5)
-- 
-- Then run each migration file in order:
-- - migrations/4_ALL_LEAGUES_FOOTBALL_DATA.sql
-- - migrations/2025_01_draw_structural_extensions.sql
-- - migrations/2025_01_add_historical_tables.sql
-- - migrations/2025_01_add_league_structure.sql
-- - migrations/2025_01_add_odds_movement_historical.sql
-- - migrations/2025_01_add_xg_data.sql
-- - migrations/add_h2h_stats.sql
-- - migrations/add_saved_jackpot_templates.sql
-- - migrations/add_saved_probability_results.sql
-- - migrations/add_entropy_metrics.sql
-- - migrations/add_unique_partial_index_models.sql
-- - migrations/add_draw_model_support.sql
-- - migrations/fix_matchresult_enum.sql
-- 
-- ============================================================================
-- STEP 5: VERIFY ALL TABLES CREATED
-- ============================================================================
-- Run this after all migrations

SELECT 
    COUNT(*) as total_tables,
    COUNT(*) FILTER (WHERE tablename IN (
        'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
        'predictions', 'models', 'training_runs', 'league_draw_priors',
        'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
        'referee_stats', 'team_rest_days', 'team_rest_days_historical',
        'odds_movement', 'odds_movement_historical', 'league_structure',
        'match_xg', 'match_xg_historical'
    )) as critical_tables
FROM pg_tables
WHERE schemaname = 'public';

-- Should return: total_tables >= 32, critical_tables = 21

