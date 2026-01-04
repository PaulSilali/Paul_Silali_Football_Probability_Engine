-- ============================================================================
-- MIGRATION: Add League Structure Table
-- ============================================================================
-- Date: 2025-01-04
-- Purpose: Add table for storing league structural metadata (size, relegation/promotion zones)
--          for draw probability modeling
--
-- This migration:
-- 1. Creates league_structure table
-- 2. Safely handles existing tables/indexes
-- ============================================================================

BEGIN;

-- ============================================================================
-- LEAGUE STRUCTURE METADATA TABLE
-- ============================================================================
-- Purpose: Store league structural information for draw probability modeling
--          Includes league size, relegation/promotion zones, etc.

-- Drop indexes first (if they exist)
DROP INDEX IF EXISTS idx_league_structure_league;
DROP INDEX IF EXISTS idx_league_structure_season;

-- Drop table if exists (will cascade to constraints)
DROP TABLE IF EXISTS league_structure CASCADE;

-- Create table
CREATE TABLE league_structure (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season          VARCHAR(20) NOT NULL,
    total_teams     INTEGER NOT NULL CHECK (total_teams > 0),
    relegation_zones INTEGER NOT NULL DEFAULT 3 CHECK (relegation_zones >= 0),
    promotion_zones INTEGER NOT NULL DEFAULT 3 CHECK (promotion_zones >= 0),
    playoff_zones   INTEGER DEFAULT 0 CHECK (playoff_zones >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_league_structure_season UNIQUE (league_id, season)
);

-- Create indexes
CREATE INDEX idx_league_structure_league ON league_structure(league_id);
CREATE INDEX idx_league_structure_season ON league_structure(season);

-- Add comments
COMMENT ON TABLE league_structure IS 'League structural metadata for draw probability modeling';
COMMENT ON COLUMN league_structure.league_id IS 'References leagues.id';
COMMENT ON COLUMN league_structure.season IS 'Season identifier (e.g., "2425", "2324")';
COMMENT ON COLUMN league_structure.total_teams IS 'Total number of teams in the league';
COMMENT ON COLUMN league_structure.relegation_zones IS 'Number of teams that get relegated (affects late-season draw rates)';
COMMENT ON COLUMN league_structure.promotion_zones IS 'Number of teams that get promoted';
COMMENT ON COLUMN league_structure.playoff_zones IS 'Number of teams in playoff positions';

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
        AND tablename = 'league_structure'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'Table league_structure was not created';
    ELSE
        RAISE NOTICE 'Table league_structure created successfully ✓';
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
        'idx_league_structure_league',
        'idx_league_structure_season'
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
-- LEAGUE STRUCTURE TABLE:
-- -----------------------
-- This table stores structural metadata about football leagues that affects
-- draw probability modeling, particularly for late-season matches.
--
-- KEY FIELDS:
-- - total_teams: Number of teams in the league (affects match frequency)
-- - relegation_zones: Teams that get relegated (affects late-season draw rates)
-- - promotion_zones: Teams that get promoted
-- - playoff_zones: Teams in playoff positions (affects late-season incentives)
--
-- USE CASES:
-- - Late-season incentive modeling
-- - Tactical conservatism detection
-- - Relegation six-pointer identification
-- - End-season mid-table match analysis
--
-- DATA SOURCE:
-- - Default mappings provided in backend service
-- - Can be enhanced with API scraping (WorldFootball.net)
-- - Can be manually updated per league/season
--
-- ============================================================================

