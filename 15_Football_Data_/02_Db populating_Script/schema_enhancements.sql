-- ============================================================================
-- SCHEMA ENHANCEMENTS FOR FOOTBALL.TXT DATA INGESTION
-- ============================================================================
-- 
-- This migration adds columns to support additional data from Football.TXT files:
-- - Half-time scores (ht_home_goals, ht_away_goals)
-- - Match time/venue information
-- - Enhanced source tracking
-- 
-- NON-DESTRUCTIVE: Only adds columns, does not modify existing structure
-- Safe to run in production
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ADD HALF-TIME SCORES TO MATCHES TABLE
-- ============================================================================

ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS ht_home_goals INTEGER,
ADD COLUMN IF NOT EXISTS ht_away_goals INTEGER;

COMMENT ON COLUMN matches.ht_home_goals IS 'Half-time goals for home team';
COMMENT ON COLUMN matches.ht_away_goals IS 'Half-time goals for away team';

-- Add constraint to ensure half-time scores are valid
ALTER TABLE matches
ADD CONSTRAINT chk_ht_goals_valid 
CHECK (
    (ht_home_goals IS NULL AND ht_away_goals IS NULL) OR
    (ht_home_goals IS NOT NULL AND ht_away_goals IS NOT NULL AND 
     ht_home_goals >= 0 AND ht_away_goals >= 0)
);

-- ============================================================================
-- 2. ADD MATCH TIME/VENUE INFORMATION (OPTIONAL)
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS match_time TIME,
ADD COLUMN IF NOT EXISTS venue VARCHAR(200);

COMMENT ON COLUMN matches.match_time IS 'Match kickoff time';
COMMENT ON COLUMN matches.venue IS 'Match venue/stadium name';

-- ============================================================================
-- 3. ENHANCE SOURCE TRACKING
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS source_file TEXT,
ADD COLUMN IF NOT EXISTS ingestion_batch_id VARCHAR(50);

COMMENT ON COLUMN matches.source_file IS 'Original source file path';
COMMENT ON COLUMN matches.ingestion_batch_id IS 'Batch identifier for ingestion tracking';

-- Create index on source_file for traceability
CREATE INDEX IF NOT EXISTS idx_matches_source_file ON matches(source_file);

-- ============================================================================
-- 4. ADD MATCHDAY/ROUND INFORMATION (FOR LEAGUE STRUCTURE)
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS matchday INTEGER,
ADD COLUMN IF NOT EXISTS round_name VARCHAR(50);

COMMENT ON COLUMN matches.matchday IS 'Matchday/round number in season';
COMMENT ON COLUMN matches.round_name IS 'Round name (e.g., "Matchday 1", "Quarter-finals")';

-- Create index for matchday queries
CREATE INDEX IF NOT EXISTS idx_matches_matchday ON matches(league_id, season, matchday);

-- ============================================================================
-- 5. ENHANCE TEAM NAME MATCHING SUPPORT
-- ============================================================================

-- Add alternative names column to teams table for better matching
ALTER TABLE teams
ADD COLUMN IF NOT EXISTS alternative_names TEXT[];

COMMENT ON COLUMN teams.alternative_names IS 'Array of alternative team names for matching';

-- Create index for alternative names search
CREATE INDEX IF NOT EXISTS idx_teams_alternative_names ON teams USING GIN(alternative_names);

-- ============================================================================
-- 6. ADD MATCH QUALITY METRICS (FOR PROBABILITY MODELING)
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS total_goals INTEGER GENERATED ALWAYS AS (home_goals + away_goals) STORED,
ADD COLUMN IF NOT EXISTS goal_difference INTEGER GENERATED ALWAYS AS (home_goals - away_goals) STORED,
ADD COLUMN IF NOT EXISTS is_draw BOOLEAN GENERATED ALWAYS AS (home_goals = away_goals) STORED;

COMMENT ON COLUMN matches.total_goals IS 'Total goals in match (computed)';
COMMENT ON COLUMN matches.goal_difference IS 'Goal difference (home - away, computed)';
COMMENT ON COLUMN matches.is_draw IS 'Whether match was a draw (computed)';

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_matches_total_goals ON matches(total_goals);
CREATE INDEX IF NOT EXISTS idx_matches_is_draw ON matches(is_draw) WHERE is_draw = TRUE;

-- ============================================================================
-- 7. ADD SEASON STATISTICS VIEW (FOR QUICK ACCESS)
-- ============================================================================

CREATE OR REPLACE VIEW v_season_statistics AS
SELECT
    l.code as league_code,
    l.name as league_name,
    m.season,
    COUNT(*) as total_matches,
    SUM(CASE WHEN m.result = 'H' THEN 1 ELSE 0 END) as home_wins,
    SUM(CASE WHEN m.result = 'D' THEN 1 ELSE 0 END) as draws,
    SUM(CASE WHEN m.result = 'A' THEN 1 ELSE 0 END) as away_wins,
    AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END) as draw_rate,
    AVG(m.home_goals + m.away_goals) as avg_goals_per_match,
    AVG(m.home_goals) as avg_home_goals,
    AVG(m.away_goals) as avg_away_goals,
    MIN(m.match_date) as season_start,
    MAX(m.match_date) as season_end
FROM matches m
JOIN leagues l ON l.id = m.league_id
GROUP BY l.code, l.name, m.season
ORDER BY l.code, m.season DESC;

COMMENT ON VIEW v_season_statistics IS 'Season-level statistics for all leagues';

-- ============================================================================
-- 8. ADD TEAM SEASON STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW v_team_season_stats AS
SELECT
    t.id as team_id,
    t.name as team_name,
    l.code as league_code,
    m.season,
    COUNT(*) as matches_played,
    SUM(CASE WHEN m.home_team_id = t.id AND m.result = 'H' THEN 1
             WHEN m.away_team_id = t.id AND m.result = 'A' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN m.result = 'D' THEN 1 ELSE 0 END) as draws,
    SUM(CASE WHEN m.home_team_id = t.id AND m.result = 'A' THEN 1
             WHEN m.away_team_id = t.id AND m.result = 'H' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN m.home_team_id = t.id THEN m.home_goals ELSE m.away_goals END) as goals_for,
    SUM(CASE WHEN m.home_team_id = t.id THEN m.away_goals ELSE m.home_goals END) as goals_against,
    SUM(CASE WHEN m.home_team_id = t.id THEN m.home_goals ELSE m.away_goals END) -
    SUM(CASE WHEN m.home_team_id = t.id THEN m.away_goals ELSE m.home_goals END) as goal_difference,
    SUM(CASE WHEN m.home_team_id = t.id AND m.result = 'H' THEN 3
             WHEN m.away_team_id = t.id AND m.result = 'A' THEN 3
             WHEN m.result = 'D' THEN 1 ELSE 0 END) as points
FROM teams t
JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
JOIN leagues l ON l.id = t.league_id
GROUP BY t.id, t.name, l.code, m.season
ORDER BY l.code, m.season DESC, points DESC;

COMMENT ON VIEW v_team_season_stats IS 'Team statistics per season';

-- ============================================================================
-- 9. VERIFICATION
-- ============================================================================

-- Verify columns were added
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
    ) expected
    WHERE column_name NOT IN (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'matches' AND table_schema = 'public'
    );
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'All schema enhancements applied successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF SCHEMA ENHANCEMENTS
-- ============================================================================

