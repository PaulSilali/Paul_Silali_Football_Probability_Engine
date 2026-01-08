-- ============================================================================
-- RUN SCHEMA ON EXISTING DATABASE
-- ============================================================================
-- 
-- This script is for running the complete schema on an EXISTING database.
-- It includes all migrations and is idempotent (safe to run multiple times).
-- 
-- Instructions:
--   1. Connect to your existing 'football_probability_engine' database
--   2. Run this entire script
--   3. All tables, columns, indexes, and constraints will be created/updated
-- 
-- ============================================================================

-- Connect to your database first (in pgAdmin, right-click database → Query Tool)
-- Then run the main schema file:

-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)

-- OR copy-paste the contents of 3_Database_Football_Probability_Engine.sql here

-- ============================================================================
-- VERIFICATION AFTER RUNNING
-- ============================================================================

-- Run this to verify everything was created:

SELECT 
    COUNT(*) as total_tables,
    COUNT(*) FILTER (WHERE tablename IN (
        'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
        'predictions', 'models', 'training_runs', 'league_draw_priors',
        'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
        'referee_stats', 'team_rest_days', 'team_rest_days_historical',
        'odds_movement', 'odds_movement_historical', 'league_structure',
        'match_xg', 'match_xg_historical', 'team_h2h_stats',
        'saved_jackpot_templates', 'saved_probability_results'
    )) as critical_tables
FROM pg_tables
WHERE schemaname = 'public';

-- Should return: total_tables >= 32, critical_tables = 24

-- Verify entropy columns
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'training_runs' 
AND column_name IN ('avg_entropy', 'temperature', 'alpha_mean')
ORDER BY column_name;

-- Should return 3 rows

-- Verify alternative_names column
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'teams' 
AND column_name = 'alternative_names';

-- Should return 1 row

-- Verify matches columns
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'matches' 
AND column_name IN ('ht_home_goals', 'ht_away_goals', 'match_time', 'venue', 
                     'source_file', 'matchday', 'round_name')
ORDER BY column_name;

-- Should return 7 rows

