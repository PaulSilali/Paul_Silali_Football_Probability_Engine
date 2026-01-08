-- ============================================================================
-- MIGRATE DATA FROM OLD DATABASE
-- ============================================================================
-- 
-- This script migrates valuable computed data from the old database
-- to the new database schema.
-- 
-- IMPORTANT:
-- 1. Run this AFTER running the new schema (3_Database_Football_Probability_Engine.sql)
-- 2. Run this BEFORE re-ingesting matches/teams/leagues
-- 3. This script uses ID mapping to preserve foreign key relationships
-- 
-- WHAT THIS MIGRATES:
-- - models (trained models)
-- - calibration_data (calibration curves)
-- - league_draw_priors (historical draw rates)
-- - h2h_draw_stats (head-to-head statistics)
-- - team_elo (Elo ratings)
-- - referee_stats (referee statistics)
-- - league_structure (league metadata)
-- - jackpots & fixtures (user data)
-- - saved templates & results (user data)
-- - training_runs (training history)
-- 
-- WHAT THIS DOES NOT MIGRATE:
-- - matches (re-ingest to get new columns)
-- - teams (re-ingest for better normalization)
-- - leagues (re-ingest for consistency)
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: CREATE TEMPORARY ID MAPPING TABLES
-- ============================================================================
-- These will be populated as we migrate data

CREATE TEMP TABLE IF NOT EXISTS league_id_map (
    old_id INTEGER,
    new_id INTEGER,
    code VARCHAR
);

CREATE TEMP TABLE IF NOT EXISTS team_id_map (
    old_id INTEGER,
    new_id INTEGER,
    canonical_name VARCHAR,
    league_id INTEGER
);

CREATE TEMP TABLE IF NOT EXISTS model_id_map (
    old_id INTEGER,
    new_id INTEGER,
    version VARCHAR
);

-- ============================================================================
-- STEP 2: MAP LEAGUES (by code)
-- ============================================================================
-- Map old league IDs to new league IDs using league code

INSERT INTO league_id_map (old_id, new_id, code)
SELECT 
    old.id as old_id,
    new.id as new_id,
    old.code
FROM (
    -- OLD DATABASE: Replace with your old database connection
    -- For now, we'll use a placeholder that you'll need to update
    SELECT id, code FROM leagues WHERE id IN (
        -- List of old league IDs from your export
        SELECT DISTINCT league_id FROM old_db.leagues
    )
) old
JOIN leagues new ON old.code = new.code
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 3: MAP TEAMS (by canonical_name + league_id)
-- ============================================================================
-- Map old team IDs to new team IDs using canonical name and league

INSERT INTO team_id_map (old_id, new_id, canonical_name, league_id)
SELECT 
    old.id as old_id,
    new.id as new_id,
    old.canonical_name,
    new.league_id
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT id, canonical_name, league_id FROM teams WHERE id IN (
        SELECT DISTINCT team_id FROM old_db.teams
    )
) old
JOIN teams new 
    ON old.canonical_name = new.canonical_name
    AND new.league_id IN (SELECT new_id FROM league_id_map WHERE old_id = old.league_id)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 4: MIGRATE MODELS
-- ============================================================================
-- Migrate trained models (preserve model weights and metadata)

INSERT INTO models (
    version, model_type, status,
    training_started_at, training_completed_at,
    training_matches, training_leagues, training_seasons,
    decay_rate, blend_alpha,
    brier_score, log_loss, draw_accuracy, overall_accuracy,
    model_weights, created_at, updated_at
)
SELECT 
    version, model_type, status::model_status,
    training_started_at, training_completed_at,
    training_matches, training_leagues, training_seasons,
    decay_rate, blend_alpha,
    brier_score, log_loss, draw_accuracy, overall_accuracy,
    model_weights, created_at, updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.models
) old
ON CONFLICT (version) DO UPDATE SET
    model_type = EXCLUDED.model_type,
    status = EXCLUDED.status,
    training_completed_at = EXCLUDED.training_completed_at,
    model_weights = EXCLUDED.model_weights,
    updated_at = now();

-- Map model IDs
INSERT INTO model_id_map (old_id, new_id, version)
SELECT old.id, new.id, old.version
FROM (
    SELECT id, version FROM old_db.models
) old
JOIN models new ON old.version = new.version;

-- ============================================================================
-- STEP 5: MIGRATE CALIBRATION DATA
-- ============================================================================
-- Migrate calibration curves (map model_id and league_id)

INSERT INTO calibration_data (
    model_id, league_id, outcome_type,
    predicted_prob_bucket, actual_frequency, sample_count, created_at
)
SELECT 
    COALESCE(m.new_id, NULL) as model_id,
    COALESCE(l.new_id, NULL) as league_id,
    old.outcome_type::match_result,
    old.predicted_prob_bucket,
    old.actual_frequency,
    old.sample_count,
    old.created_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.calibration_data
) old
LEFT JOIN model_id_map m ON old.model_id = m.old_id
LEFT JOIN league_id_map l ON old.league_id = l.old_id
ON CONFLICT (model_id, league_id, outcome_type, predicted_prob_bucket) DO UPDATE SET
    actual_frequency = EXCLUDED.actual_frequency,
    sample_count = EXCLUDED.sample_count;

-- ============================================================================
-- STEP 6: MIGRATE LEAGUE DRAW PRIORS
-- ============================================================================
-- Migrate historical draw rates (map league_id)

INSERT INTO league_draw_priors (
    league_id, season, draw_rate, sample_size, updated_at
)
SELECT 
    l.new_id as league_id,
    old.season,
    old.draw_rate,
    old.sample_size,
    old.updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.league_draw_priors
) old
JOIN league_id_map l ON old.league_id = l.old_id
ON CONFLICT (league_id, season) DO UPDATE SET
    draw_rate = EXCLUDED.draw_rate,
    sample_size = EXCLUDED.sample_size,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- STEP 7: MIGRATE H2H DRAW STATS
-- ============================================================================
-- Migrate head-to-head statistics (map team_id)

INSERT INTO h2h_draw_stats (
    team_home_id, team_away_id,
    matches_played, draw_count, avg_goals, last_updated
)
SELECT 
    th.new_id as team_home_id,
    ta.new_id as team_away_id,
    old.matches_played,
    old.draw_count,
    old.avg_goals,
    old.last_updated
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.h2h_draw_stats
) old
JOIN team_id_map th ON old.team_home_id = th.old_id
JOIN team_id_map ta ON old.team_away_id = ta.old_id
ON CONFLICT (team_home_id, team_away_id) DO UPDATE SET
    matches_played = EXCLUDED.matches_played,
    draw_count = EXCLUDED.draw_count,
    avg_goals = EXCLUDED.avg_goals,
    last_updated = EXCLUDED.last_updated;

-- ============================================================================
-- STEP 8: MIGRATE TEAM ELO
-- ============================================================================
-- Migrate Elo ratings (map team_id)

INSERT INTO team_elo (
    team_id, date, elo_rating, created_at
)
SELECT 
    t.new_id as team_id,
    old.date,
    old.elo_rating,
    old.created_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.team_elo
) old
JOIN team_id_map t ON old.team_id = t.old_id
ON CONFLICT (team_id, date) DO UPDATE SET
    elo_rating = EXCLUDED.elo_rating;

-- ============================================================================
-- STEP 9: MIGRATE REFEREE STATS
-- ============================================================================
-- Migrate referee statistics (no dependencies)

INSERT INTO referee_stats (
    referee_id, referee_name, matches, avg_cards, avg_penalties, draw_rate, updated_at
)
SELECT 
    referee_id, referee_name, matches, avg_cards, avg_penalties, draw_rate, updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.referee_stats
) old
ON CONFLICT (referee_id) DO UPDATE SET
    referee_name = EXCLUDED.referee_name,
    matches = EXCLUDED.matches,
    avg_cards = EXCLUDED.avg_cards,
    avg_penalties = EXCLUDED.avg_penalties,
    draw_rate = EXCLUDED.draw_rate,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- STEP 10: MIGRATE LEAGUE STRUCTURE
-- ============================================================================
-- Migrate league metadata (map league_id)

INSERT INTO league_structure (
    league_id, season, total_teams, relegation_zones, promotion_zones, playoff_zones,
    created_at, updated_at
)
SELECT 
    l.new_id as league_id,
    old.season,
    old.total_teams,
    old.relegation_zones,
    old.promotion_zones,
    old.playoff_zones,
    old.created_at,
    old.updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.league_structure
) old
JOIN league_id_map l ON old.league_id = l.old_id
ON CONFLICT (league_id, season) DO UPDATE SET
    total_teams = EXCLUDED.total_teams,
    relegation_zones = EXCLUDED.relegation_zones,
    promotion_zones = EXCLUDED.promotion_zones,
    playoff_zones = EXCLUDED.playoff_zones,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- STEP 11: MIGRATE JACKPOTS & FIXTURES
-- ============================================================================
-- Migrate user-created jackpots (map team_id and league_id)

-- First, migrate jackpots (no dependencies)
INSERT INTO jackpots (
    jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at
)
SELECT 
    jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.jackpots
) old
ON CONFLICT (jackpot_id) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    updated_at = EXCLUDED.updated_at;

-- Then, migrate fixtures (map team_id and league_id)
INSERT INTO jackpot_fixtures (
    jackpot_id, match_order, home_team, away_team,
    odds_home, odds_draw, odds_away,
    home_team_id, away_team_id, league_id,
    actual_result, actual_home_goals, actual_away_goals, created_at
)
SELECT 
    jf.jackpot_id,
    jf.match_order,
    jf.home_team,
    jf.away_team,
    jf.odds_home,
    jf.odds_draw,
    jf.odds_away,
    th.new_id as home_team_id,
    ta.new_id as away_team_id,
    l.new_id as league_id,
    jf.actual_result::match_result,
    jf.actual_home_goals,
    jf.actual_away_goals,
    jf.created_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.jackpot_fixtures
) jf
LEFT JOIN jackpots j ON jf.jackpot_id = j.jackpot_id
LEFT JOIN team_id_map th ON jf.home_team_id = th.old_id
LEFT JOIN team_id_map ta ON jf.away_team_id = ta.old_id
LEFT JOIN league_id_map l ON jf.league_id = l.old_id;

-- ============================================================================
-- STEP 12: MIGRATE SAVED TEMPLATES & RESULTS
-- ============================================================================
-- Migrate user data (no dependencies)

INSERT INTO saved_jackpot_templates (
    user_id, name, description, fixtures, fixture_count, created_at, updated_at
)
SELECT 
    user_id, name, description, fixtures, fixture_count, created_at, updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.saved_jackpot_templates
) old
ON CONFLICT DO NOTHING;

INSERT INTO saved_probability_results (
    user_id, jackpot_id, name, description, selections, actual_results, scores,
    model_version, total_fixtures, created_at, updated_at
)
SELECT 
    user_id, jackpot_id, name, description, selections, actual_results, scores,
    model_version, total_fixtures, created_at, updated_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.saved_probability_results
) old
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 13: MIGRATE TRAINING RUNS
-- ============================================================================
-- Migrate training history (map model_id)
-- Note: entropy columns will be NULL (not in old DB)

INSERT INTO training_runs (
    model_id, run_type, status, started_at, completed_at,
    match_count, date_from, date_to,
    brier_score, log_loss, validation_accuracy,
    avg_entropy, p10_entropy, p90_entropy, temperature, alpha_mean,
    error_message, logs, created_at
)
SELECT 
    m.new_id as model_id,
    old.run_type,
    old.status::model_status,
    old.started_at,
    old.completed_at,
    old.match_count,
    old.date_from,
    old.date_to,
    old.brier_score,
    old.log_loss,
    old.validation_accuracy,
    NULL as avg_entropy,  -- Not in old DB
    NULL as p10_entropy,  -- Not in old DB
    NULL as p90_entropy,  -- Not in old DB
    NULL as temperature,  -- Not in old DB
    NULL as alpha_mean,  -- Not in old DB
    old.error_message,
    old.logs,
    old.created_at
FROM (
    -- OLD DATABASE: Replace with your old database connection
    SELECT * FROM old_db.training_runs
) old
LEFT JOIN model_id_map m ON old.model_id = m.old_id;

-- ============================================================================
-- STEP 14: VERIFICATION
-- ============================================================================

-- Count migrated records
DO $$
DECLARE
    models_count INTEGER;
    calibration_count INTEGER;
    draw_priors_count INTEGER;
    h2h_count INTEGER;
    elo_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO models_count FROM models;
    SELECT COUNT(*) INTO calibration_count FROM calibration_data;
    SELECT COUNT(*) INTO draw_priors_count FROM league_draw_priors;
    SELECT COUNT(*) INTO h2h_count FROM h2h_draw_stats;
    SELECT COUNT(*) INTO elo_count FROM team_elo;
    
    RAISE NOTICE 'Migration Summary:';
    RAISE NOTICE '  Models: %', models_count;
    RAISE NOTICE '  Calibration Data: %', calibration_count;
    RAISE NOTICE '  League Draw Priors: %', draw_priors_count;
    RAISE NOTICE '  H2H Draw Stats: %', h2h_count;
    RAISE NOTICE '  Team Elo: %', elo_count;
END $$;

COMMIT;

-- ============================================================================
-- IMPORTANT NOTES
-- ============================================================================
-- 
-- 1. This script uses placeholder "old_db" schema name.
--    You need to replace it with your actual old database connection.
-- 
-- 2. If using a different database, use:
--    FROM dblink('dbname=old_db', 'SELECT * FROM models') AS old(...)
-- 
-- 3. If using exported SQL files, you'll need to:
--    - Import them into a temporary schema first
--    - Then run this migration script
-- 
-- 4. After migration:
--    - Re-ingest matches/teams/leagues using populate_database.py
--    - Update foreign keys in migrated tables
--    - Recalculate statistics
-- 
-- ============================================================================

