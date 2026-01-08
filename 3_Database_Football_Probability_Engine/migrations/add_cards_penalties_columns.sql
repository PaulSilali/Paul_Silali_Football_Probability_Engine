-- ============================================================================
-- ADD CARDS AND PENALTIES COLUMNS TO MATCHES TABLE
-- ============================================================================
-- 
-- This migration adds columns for yellow cards, red cards, and penalties
-- to support referee statistics calculation.
-- 
-- NOTE: The current Football.TXT data source does NOT include cards/penalties data.
-- These columns are added for future use if data becomes available from other sources.
-- 
-- NON-DESTRUCTIVE: Only adds nullable columns
-- Safe to run in production
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ADD CARDS COLUMNS
-- ============================================================================
-- Yellow cards (HY = Home Yellow, AY = Away Yellow)
-- Red cards (HR = Home Red, AR = Away Red)

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS hy INTEGER CHECK (hy >= 0),  -- Home team yellow cards
ADD COLUMN IF NOT EXISTS ay INTEGER CHECK (ay >= 0),  -- Away team yellow cards
ADD COLUMN IF NOT EXISTS hr INTEGER CHECK (hr >= 0),  -- Home team red cards
ADD COLUMN IF NOT EXISTS ar INTEGER CHECK (ar >= 0);  -- Away team red cards

COMMENT ON COLUMN matches.hy IS 'Home team yellow cards';
COMMENT ON COLUMN matches.ay IS 'Away team yellow cards';
COMMENT ON COLUMN matches.hr IS 'Home team red cards';
COMMENT ON COLUMN matches.ar IS 'Away team red cards';

-- ============================================================================
-- 2. ADD PENALTIES COLUMNS
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS home_penalties INTEGER CHECK (home_penalties >= 0),
ADD COLUMN IF NOT EXISTS away_penalties INTEGER CHECK (away_penalties >= 0);

COMMENT ON COLUMN matches.home_penalties IS 'Home team penalties awarded';
COMMENT ON COLUMN matches.away_penalties IS 'Away team penalties awarded';

-- ============================================================================
-- 3. ADD REFEREE_ID COLUMN (if not exists)
-- ============================================================================
-- This links matches to referees for statistics calculation

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS referee_id INTEGER;

COMMENT ON COLUMN matches.referee_id IS 'Referee ID (links to referee_stats.referee_id)';

-- Create index for referee lookups
CREATE INDEX IF NOT EXISTS idx_matches_referee_id ON matches(referee_id) WHERE referee_id IS NOT NULL;

-- ============================================================================
-- 4. ADD COMPUTED COLUMNS FOR TOTAL CARDS
-- ============================================================================
-- These can be used for quick queries

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS total_yellow_cards INTEGER 
    GENERATED ALWAYS AS (
        COALESCE(hy, 0) + COALESCE(ay, 0)
    ) STORED,
ADD COLUMN IF NOT EXISTS total_red_cards INTEGER 
    GENERATED ALWAYS AS (
        COALESCE(hr, 0) + COALESCE(ar, 0)
    ) STORED,
ADD COLUMN IF NOT EXISTS total_cards INTEGER 
    GENERATED ALWAYS AS (
        COALESCE(hy, 0) + COALESCE(ay, 0) + COALESCE(hr, 0) + COALESCE(ar, 0)
    ) STORED;

COMMENT ON COLUMN matches.total_yellow_cards IS 'Total yellow cards in match (computed)';
COMMENT ON COLUMN matches.total_red_cards IS 'Total red cards in match (computed)';
COMMENT ON COLUMN matches.total_cards IS 'Total cards in match (computed)';

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_matches_total_cards ON matches(total_cards) WHERE total_cards > 0;
CREATE INDEX IF NOT EXISTS idx_matches_total_yellow_cards ON matches(total_yellow_cards) WHERE total_yellow_cards > 0;

-- ============================================================================
-- 5. VERIFICATION
-- ============================================================================

DO $$
DECLARE
    missing_columns TEXT[];
BEGIN
    SELECT ARRAY_AGG(column_name)
    INTO missing_columns
    FROM (
        SELECT 'hy' as column_name
        UNION SELECT 'ay'
        UNION SELECT 'hr'
        UNION SELECT 'ar'
        UNION SELECT 'home_penalties'
        UNION SELECT 'away_penalties'
        UNION SELECT 'referee_id'
    ) expected
    WHERE column_name NOT IN (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'matches' AND table_schema = 'public'
    );
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'All cards/penalties columns added successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- 1. CURRENT DATA SOURCE STATUS:
--    - Football.TXT files from openfootball project do NOT include cards/penalties
--    - These columns are NULL for all existing matches
--    - Future data sources (API, CSV imports) can populate these columns
-- 
-- 2. REFEREE STATISTICS:
--    - Once referee_id is populated, referee_stats can be calculated from match data
--    - avg_cards = AVG(total_cards) per referee
--    - avg_penalties = AVG(home_penalties + away_penalties) per referee
-- 
-- 3. DATA SOURCES THAT MIGHT HAVE CARDS/PENALTIES:
--    - API-Football (requires subscription)
--    - Football-Data.co.uk (premium tier)
--    - Opta Sports (commercial)
--    - Manual entry for specific matches
-- 
-- ============================================================================

