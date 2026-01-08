-- ============================================================================
-- DATABASE REBUILD SCRIPT
-- ============================================================================
-- 
-- This script rebuilds the entire database from scratch.
-- WARNING: This will DROP all existing data!
-- 
-- Usage:
--   1. Backup your database first!
--   2. Connect to PostgreSQL as superuser
--   3. Run: psql -U postgres -f rebuild_database.sql
-- 
-- ============================================================================

-- ============================================================================
-- STEP 1: DROP EXISTING DATABASE
-- ============================================================================

-- Disconnect all users from the database
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'football_probability_engine'
  AND pid <> pg_backend_pid();

-- Drop database
DROP DATABASE IF EXISTS football_probability_engine;

-- ============================================================================
-- STEP 2: CREATE NEW DATABASE
-- ============================================================================

CREATE DATABASE football_probability_engine
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- ============================================================================
-- STEP 3: CONNECT TO NEW DATABASE
-- ============================================================================

\c football_probability_engine

-- ============================================================================
-- STEP 4: RUN MAIN SCHEMA
-- ============================================================================

\i 3_Database_Football_Probability_Engine.sql

-- ============================================================================
-- STEP 5: RUN ALL MIGRATIONS IN ORDER
-- ============================================================================

-- Migration 1: All leagues
\i migrations/4_ALL_LEAGUES_FOOTBALL_DATA.sql

-- Migration 2: Draw structural extensions
\i migrations/2025_01_draw_structural_extensions.sql

-- Migration 3: Historical tables
\i migrations/2025_01_add_historical_tables.sql

-- Migration 4: League structure
\i migrations/2025_01_add_league_structure.sql

-- Migration 5: Odds movement historical
\i migrations/2025_01_add_odds_movement_historical.sql

-- Migration 6: xG data
\i migrations/2025_01_add_xg_data.sql

-- Migration 7: H2H stats
\i migrations/add_h2h_stats.sql

-- Migration 8: Saved templates
\i migrations/add_saved_jackpot_templates.sql

-- Migration 9: Saved probability results
\i migrations/add_saved_probability_results.sql

-- Migration 10: Entropy metrics
\i migrations/add_entropy_metrics.sql

-- Migration 11: Unique partial index
\i migrations/add_unique_partial_index_models.sql

-- Migration 12: Draw model support
\i migrations/add_draw_model_support.sql

-- Migration 13: Fix matchresult enum
\i migrations/fix_matchresult_enum.sql

-- ============================================================================
-- STEP 6: VERIFICATION
-- ============================================================================

-- Count all tables
SELECT 
    COUNT(*) as total_tables,
    COUNT(*) FILTER (WHERE schemaname = 'public') as public_tables
FROM pg_tables
WHERE schemaname = 'public';

-- List all tables
SELECT 
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify critical tables exist
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
        'predictions', 'models', 'training_runs', 'league_draw_priors',
        'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
        'referee_stats', 'team_rest_days', 'team_rest_days_historical',
        'odds_movement', 'odds_movement_historical', 'league_structure',
        'match_xg', 'match_xg_historical'
    ];
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(table_name)
    INTO missing_tables
    FROM unnest(expected_tables) AS table_name
    WHERE table_name NOT IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    );
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'All expected tables created successfully ✓';
    END IF;
END $$;

-- ============================================================================
-- STEP 7: VERIFY COLUMNS
-- ============================================================================

-- Verify matches table has all columns
DO $$
DECLARE
    missing_columns TEXT[];
BEGIN
    SELECT ARRAY_AGG(column_name)
    INTO missing_columns
    FROM (
        SELECT 'ht_home_goals' as column_name
        UNION SELECT 'ht_away_goals'
        UNION SELECT 'match_time'
        UNION SELECT 'venue'
        UNION SELECT 'source_file'
        UNION SELECT 'matchday'
        UNION SELECT 'round_name'
    ) expected
    WHERE column_name NOT IN (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'matches' AND table_schema = 'public'
    );
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing columns in matches table: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'All expected columns in matches table ✓';
    END IF;
END $$;

-- Verify teams table has alternative_names
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'teams' 
        AND column_name = 'alternative_names'
        AND table_schema = 'public'
    ) THEN
        RAISE EXCEPTION 'Missing column: teams.alternative_names';
    ELSE
        RAISE NOTICE 'teams.alternative_names column exists ✓';
    END IF;
END $$;

-- ============================================================================
-- STEP 8: VERIFY INDEXES
-- ============================================================================

-- Verify GIN index for alternative_names
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_indexes 
        WHERE indexname = 'idx_teams_alternative_names'
        AND schemaname = 'public'
    ) THEN
        RAISE WARNING 'GIN index idx_teams_alternative_names not found. Create it manually:';
        RAISE WARNING 'CREATE INDEX idx_teams_alternative_names ON teams USING GIN(alternative_names);';
    ELSE
        RAISE NOTICE 'GIN index idx_teams_alternative_names exists ✓';
    END IF;
END $$;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

SELECT 'Database rebuild completed successfully!' as status;

