-- ============================================================================
-- MIGRATION: Add Historical Tables for Weather and Rest Days
-- ============================================================================
-- Date: 2025-01-04
-- Purpose: Add tables for storing historical match data (from matches table)
--          separate from fixture data (from jackpot_fixtures table)
--
-- This migration:
-- 1. Creates match_weather_historical table (for historical matches)
-- 2. Creates team_rest_days_historical table (for historical matches)
-- 3. Safely handles existing tables/indexes
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. MATCH WEATHER HISTORICAL TABLE
-- ============================================================================
-- Purpose: Store weather data for historical matches (from matches table)
--          This is separate from match_weather which stores data for 
--          future fixtures (from jackpot_fixtures table)

-- Drop indexes first (if they exist)
DROP INDEX IF EXISTS idx_match_weather_historical_match;

-- Drop table if exists (will cascade to constraints)
DROP TABLE IF EXISTS match_weather_historical CASCADE;

-- Create table
CREATE TABLE match_weather_historical (
    id                  SERIAL PRIMARY KEY,
    match_id            BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    temperature         DOUBLE PRECISION,
    rainfall            DOUBLE PRECISION CHECK (rainfall >= 0),
    wind_speed          DOUBLE PRECISION CHECK (wind_speed >= 0),
    weather_draw_index  DOUBLE PRECISION,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match_weather_historical_match UNIQUE (match_id)
);

-- Create indexes
CREATE INDEX idx_match_weather_historical_match ON match_weather_historical(match_id);

-- Add comments
COMMENT ON TABLE match_weather_historical IS 'Weather conditions for historical matches (from matches table)';
COMMENT ON COLUMN match_weather_historical.match_id IS 'References matches.id (historical match data)';
COMMENT ON COLUMN match_weather_historical.weather_draw_index IS 'Computed draw adjustment factor from weather (0.95-1.10 typical)';

-- ============================================================================
-- 2. TEAM REST DAYS HISTORICAL TABLE
-- ============================================================================
-- Purpose: Store rest days data for historical matches (from matches table)
--          This is separate from team_rest_days which stores data for 
--          future fixtures (from jackpot_fixtures table)

-- Drop indexes first (if they exist)
DROP INDEX IF EXISTS idx_team_rest_historical_match;
DROP INDEX IF EXISTS idx_team_rest_historical_team;
DROP INDEX IF EXISTS idx_team_rest_historical_days;

-- Drop table if exists (will cascade to constraints)
DROP TABLE IF EXISTS team_rest_days_historical CASCADE;

-- Create table
CREATE TABLE team_rest_days_historical (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id         INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    rest_days       INTEGER NOT NULL CHECK (rest_days >= 0),
    is_midweek      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_team_rest_historical_match_team UNIQUE (match_id, team_id)
);

-- Create indexes
CREATE INDEX idx_team_rest_historical_match ON team_rest_days_historical(match_id);
CREATE INDEX idx_team_rest_historical_team ON team_rest_days_historical(team_id);
CREATE INDEX idx_team_rest_historical_days ON team_rest_days_historical(rest_days);

-- Add comments
COMMENT ON TABLE team_rest_days_historical IS 'Team rest days for historical matches (from matches table)';
COMMENT ON COLUMN team_rest_days_historical.match_id IS 'References matches.id (historical match data)';
COMMENT ON COLUMN team_rest_days_historical.team_id IS 'Team ID (home or away team)';
COMMENT ON COLUMN team_rest_days_historical.rest_days IS 'Days of rest before this match';
COMMENT ON COLUMN team_rest_days_historical.is_midweek IS 'Whether match is played midweek (Tue-Thu)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables exist
DO $$
DECLARE
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(table_name)
    INTO missing_tables
    FROM unnest(ARRAY['match_weather_historical', 'team_rest_days_historical', 'odds_movement_historical']) AS table_name
    WHERE table_name NOT IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    );
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'All historical tables created successfully ✓';
    END IF;
END $$;

-- Verify indexes exist
DO $$
DECLARE
    missing_indexes TEXT[];
BEGIN
    SELECT ARRAY_AGG(index_name)
    INTO missing_indexes
    FROM unnest(ARRAY[
        'idx_match_weather_historical_match',
        'idx_team_rest_historical_match',
        'idx_team_rest_historical_team',
        'idx_team_rest_historical_days',
        'idx_odds_movement_historical_match',
        'idx_odds_movement_historical_delta'
    ]) AS index_name
    WHERE index_name NOT IN (
        SELECT indexname FROM pg_indexes WHERE schemaname = 'public'
    );
    
    IF array_length(missing_indexes, 1) > 0 THEN
        RAISE EXCEPTION 'Missing indexes: %', array_to_string(missing_indexes, ', ');
    ELSE
        RAISE NOTICE 'All indexes created successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- EXPLANATION OF TABLE PURPOSES
-- ============================================================================
-- 
-- EXISTING TABLES (for FUTURE FIXTURES):
-- --------------------------------------
-- 1. match_weather
--    - Purpose: Weather data for FUTURE jackpot fixtures
--    - Links to: jackpot_fixtures.id (fixture_id)
--    - Used for: Predicting draw probability for upcoming matches
--
-- 2. team_rest_days
--    - Purpose: Rest days data for FUTURE jackpot fixtures
--    - Links to: jackpot_fixtures.id (fixture_id)
--    - Used for: Predicting draw probability based on team fatigue
--
-- NEW HISTORICAL TABLES (for PAST MATCHES):
-- ------------------------------------------
-- 1. match_weather_historical
--    - Purpose: Weather data for HISTORICAL matches (training data)
--    - Links to: matches.id (match_id)
--    - Used for: Backtesting, model training, historical analysis
--
-- 2. team_rest_days_historical
--    - Purpose: Rest days data for HISTORICAL matches (training data)
--    - Links to: matches.id (match_id)
--    - Used for: Backtesting, model training, historical analysis
--
-- 3. odds_movement_historical
--    - Purpose: Odds movement data for HISTORICAL matches (training data)
--    - Links to: matches.id (match_id)
--    - Used for: Backtesting, model training, historical analysis
--
-- WHY TWO SEPARATE TABLES?
-- ------------------------
-- - jackpot_fixtures: Future matches that users want to predict
-- - matches: Historical matches used for training and validation
-- - Different foreign key relationships require separate tables
-- - Keeps data organized and prevents confusion between future and past data
--
-- ============================================================================

