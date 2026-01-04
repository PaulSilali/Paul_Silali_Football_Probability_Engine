-- ============================================================================
-- MIGRATION: Add Odds Movement Historical Table
-- ============================================================================
-- Date: 2025-01-04
-- Purpose: Add table for storing odds movement data for historical matches
--          (from matches table) for draw probability modeling
--
-- This migration:
-- 1. Creates odds_movement_historical table
-- 2. Safely handles existing tables/indexes
-- ============================================================================

BEGIN;

-- ============================================================================
-- ODDS MOVEMENT HISTORICAL TABLE
-- ============================================================================
-- Purpose: Store odds movement data for historical matches (from matches table)
--          This is separate from odds_movement which stores data for 
--          future fixtures (from jackpot_fixtures table)

-- Drop indexes first (if they exist)
DROP INDEX IF EXISTS idx_odds_movement_historical_match;
DROP INDEX IF EXISTS idx_odds_movement_historical_delta;

-- Drop table if exists (will cascade to constraints)
DROP TABLE IF EXISTS odds_movement_historical CASCADE;

-- Create table
CREATE TABLE odds_movement_historical (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    draw_open       DOUBLE PRECISION CHECK (draw_open > 1.0),
    draw_close      DOUBLE PRECISION CHECK (draw_close > 1.0),
    draw_delta      DOUBLE PRECISION,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_odds_movement_historical_match UNIQUE (match_id)
);

-- Create indexes
CREATE INDEX idx_odds_movement_historical_match ON odds_movement_historical(match_id);
CREATE INDEX idx_odds_movement_historical_delta ON odds_movement_historical(draw_delta);

-- Add comments
COMMENT ON TABLE odds_movement_historical IS 'Odds movement data for historical matches (from matches table)';
COMMENT ON COLUMN odds_movement_historical.match_id IS 'References matches.id (historical match data)';
COMMENT ON COLUMN odds_movement_historical.draw_open IS 'Opening draw odds (must be > 1.0)';
COMMENT ON COLUMN odds_movement_historical.draw_close IS 'Closing draw odds (must be > 1.0)';
COMMENT ON COLUMN odds_movement_historical.draw_delta IS 'Change in draw odds (close - open), positive = draw odds increased';
COMMENT ON COLUMN odds_movement_historical.recorded_at IS 'Timestamp when the odds movement was recorded';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify table exists
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = 'odds_movement_historical'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'Table odds_movement_historical was not created';
    ELSE
        RAISE NOTICE 'Table odds_movement_historical created successfully ✓';
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
-- EXPLANATION
-- ============================================================================
-- 
-- ODDS MOVEMENT HISTORICAL TABLE:
-- -------------------------------
-- This table stores odds movement data for HISTORICAL matches (from the 
-- matches table) for draw probability modeling and backtesting.
--
-- KEY FIELDS:
-- - match_id: Links to matches.id (historical match data)
-- - draw_open: Opening draw odds (when odds first became available)
-- - draw_close: Closing draw odds (just before match start)
-- - draw_delta: Change in odds (close - open), positive = odds increased
--
-- USE CASES:
-- - Historical analysis of odds movement patterns
-- - Backtesting draw probability models
-- - Training models on odds movement features
-- - Identifying market inefficiencies
--
-- RELATIONSHIP TO OTHER TABLES:
-- - odds_movement: For FUTURE fixtures (jackpot_fixtures)
-- - odds_movement_historical: For HISTORICAL matches (matches)
-- - Both tables have the same structure but different foreign keys
--
-- DATA SOURCE:
-- - Historical match data from matches table
-- - Odds data from matches.odds_draw column
-- - Can be enhanced with opening odds tracking from external APIs
--
-- ============================================================================

