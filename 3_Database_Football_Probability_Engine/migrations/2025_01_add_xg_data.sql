-- ============================================================================
-- XG DATA TABLE MIGRATION
-- ============================================================================
-- 
-- This migration adds tables for Expected Goals (xG) data for draw probability modeling.
-- xG data helps predict draw probability by measuring chance quality rather than actual goals.
-- Low xG matches (defensive) tend to have higher draw rates.
-- 
-- NON-DESTRUCTIVE: Only adds new tables, does not modify existing ones.
-- Safe to run in production.
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. XG DATA FOR FIXTURES (Future matches)
-- ============================================================================
-- Stores xG data for jackpot fixtures

CREATE TABLE IF NOT EXISTS match_xg (
    id              SERIAL PRIMARY KEY,
    fixture_id      INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    xg_home         DOUBLE PRECISION CHECK (xg_home >= 0),
    xg_away         DOUBLE PRECISION CHECK (xg_away >= 0),
    xg_total        DOUBLE PRECISION CHECK (xg_total >= 0),
    xg_draw_index   DOUBLE PRECISION CHECK (xg_draw_index BETWEEN 0.8 AND 1.2),
    -- xG draw index: lower xG_total = higher draw probability
    -- Formula: 1.0 + (2.5 - xg_total) * 0.08
    -- Example: xg_total=1.5 -> index=1.08 (8% boost), xg_total=3.5 -> index=0.92 (8% reduction)
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match_xg_fixture UNIQUE (fixture_id)
);

CREATE INDEX idx_match_xg_fixture ON match_xg(fixture_id);
CREATE INDEX idx_match_xg_total ON match_xg(xg_total);
CREATE INDEX idx_match_xg_draw_index ON match_xg(xg_draw_index);

COMMENT ON TABLE match_xg IS 'Expected Goals (xG) data for jackpot fixtures';
COMMENT ON COLUMN match_xg.xg_home IS 'Expected goals for home team';
COMMENT ON COLUMN match_xg.xg_away IS 'Expected goals for away team';
COMMENT ON COLUMN match_xg.xg_total IS 'Total expected goals (xg_home + xg_away)';
COMMENT ON COLUMN match_xg.xg_draw_index IS 'Draw probability adjustment factor based on xG (lower xG = higher draw probability)';

-- ============================================================================
-- 2. XG DATA FOR HISTORICAL MATCHES
-- ============================================================================
-- Stores xG data for historical matches (from matches table)

CREATE TABLE IF NOT EXISTS match_xg_historical (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    xg_home         DOUBLE PRECISION CHECK (xg_home >= 0),
    xg_away         DOUBLE PRECISION CHECK (xg_away >= 0),
    xg_total        DOUBLE PRECISION CHECK (xg_total >= 0),
    xg_draw_index   DOUBLE PRECISION CHECK (xg_draw_index BETWEEN 0.8 AND 1.2),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match_xg_historical_match UNIQUE (match_id)
);

CREATE INDEX idx_match_xg_historical_match ON match_xg_historical(match_id);
CREATE INDEX idx_match_xg_historical_total ON match_xg_historical(xg_total);
CREATE INDEX idx_match_xg_historical_draw_index ON match_xg_historical(xg_draw_index);

COMMENT ON TABLE match_xg_historical IS 'Expected Goals (xG) data for historical matches';
COMMENT ON COLUMN match_xg_historical.xg_home IS 'Expected goals for home team';
COMMENT ON COLUMN match_xg_historical.xg_away IS 'Expected goals for away team';
COMMENT ON COLUMN match_xg_historical.xg_total IS 'Total expected goals (xg_home + xg_away)';
COMMENT ON COLUMN match_xg_historical.xg_draw_index IS 'Draw probability adjustment factor based on xG (lower xG = higher draw probability)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    expected_tables TEXT[] := ARRAY['match_xg', 'match_xg_historical'];
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
        RAISE NOTICE 'All xG data tables created successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

