-- ============================================================================
-- IMPORT DATA FROM SQL EXPORT FILES
-- ============================================================================
-- 
-- This script imports data from SQL export files (DBeaver exports)
-- located in: C:\Users\Admin\Desktop\Exported_Football _DB
-- 
-- IMPORTANT:
-- 1. Run this AFTER running the new schema (3_Database_Football_Probability_Engine.sql)
-- 2. This script uses ON CONFLICT to prevent duplicates
-- 3. IDs will be regenerated (auto-increment), but relationships are preserved
-- 
-- WHAT THIS IMPORTS:
-- - Valuable computed data (models, calibration_data, etc.)
-- - User data (jackpots, templates, results)
-- - Statistics (league_draw_priors, h2h_draw_stats, etc.)
-- 
-- WHAT THIS DOES NOT IMPORT:
-- - matches (re-ingest to get new columns)
-- - teams (re-ingest for better normalization)
-- - leagues (re-ingest for consistency)
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: IMPORT LEAGUES (with ID mapping)
-- ============================================================================
-- Import leagues and create ID mapping table
-- Note: We'll use code as the key for mapping

CREATE TEMP TABLE IF NOT EXISTS league_id_map (
    old_id INTEGER,
    new_id INTEGER,
    code VARCHAR
);

-- Import leagues (ON CONFLICT updates existing)
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active, created_at, updated_at)
SELECT DISTINCT ON (code)
    code, name, country, tier, avg_draw_rate, home_advantage, is_active, created_at, updated_at
FROM (
    -- You'll need to manually copy-paste the INSERT statements from leagues_202601081444.sql
    -- Or use \i command if the file is accessible
    -- For now, this is a template
    VALUES
        ('E0', 'Premier League', 'England', 1, 0.26, 0.35, true, now(), now())
    -- Add more from your export file
) AS old_leagues(code, name, country, tier, avg_draw_rate, home_advantage, is_active, created_at, updated_at)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    tier = EXCLUDED.tier,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active,
    updated_at = now();

-- Create ID mapping for leagues
INSERT INTO league_id_map (old_id, new_id, code)
SELECT old.id, new.id, old.code
FROM (
    -- Extract from your export file
    SELECT id, code FROM (VALUES (1, 'E0'), (2, 'SP1')) AS old(id, code)
) old
JOIN leagues new ON old.code = new.code;

-- ============================================================================
-- STEP 2: IMPORT TEAMS (with ID mapping)
-- ============================================================================
-- Import teams and create ID mapping
-- Note: We'll use canonical_name + league_id as the key

CREATE TEMP TABLE IF NOT EXISTS team_id_map (
    old_id INTEGER,
    new_id INTEGER,
    canonical_name VARCHAR,
    league_id INTEGER
);

-- Import teams (ON CONFLICT updates existing)
-- You'll need to modify the INSERT statements from teams_202601081444.sql
-- Replace old league_id with new league_id using the mapping

-- Example (you'll need to adapt this):
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias, last_calculated, created_at, updated_at, alternative_names)
SELECT 
    lm.new_id as league_id,
    old.name,
    old.canonical_name,
    old.attack_rating,
    old.defense_rating,
    old.home_bias,
    old.last_calculated,
    old.created_at,
    old.updated_at,
    old.alternative_names
FROM (
    -- Extract from teams_202601081444.sql
    -- You'll need to parse the INSERT statements
    VALUES
        (1, 'Brighton', 'brighton', 1.0, 1.0, 0.0, NULL, now(), now(), NULL)
    -- Add more from your export file
) AS old(league_id, name, canonical_name, attack_rating, defense_rating, home_bias, last_calculated, created_at, updated_at, alternative_names)
JOIN league_id_map lm ON old.league_id = lm.old_id
ON CONFLICT (canonical_name, league_id) DO UPDATE SET
    name = EXCLUDED.name,
    attack_rating = EXCLUDED.attack_rating,
    defense_rating = EXCLUDED.defense_rating,
    home_bias = EXCLUDED.home_bias,
    last_calculated = EXCLUDED.last_calculated,
    alternative_names = EXCLUDED.alternative_names,
    updated_at = now();

-- Create ID mapping for teams
INSERT INTO team_id_map (old_id, new_id, canonical_name, league_id)
SELECT old.id, new.id, old.canonical_name, new.league_id
FROM (
    -- Extract from your export file
    SELECT id, canonical_name, league_id FROM (VALUES (3, 'brighton', 1)) AS old(id, canonical_name, league_id)
) old
JOIN teams new 
    ON old.canonical_name = new.canonical_name
    AND new.league_id IN (SELECT new_id FROM league_id_map WHERE old_id = old.league_id);

-- ============================================================================
-- STEP 3: IMPORT MODELS
-- ============================================================================
-- Import models (preserve model weights and metadata)

CREATE TEMP TABLE IF NOT EXISTS model_id_map (
    old_id INTEGER,
    new_id INTEGER,
    version VARCHAR
);

-- Import models
-- Copy-paste INSERT statements from models_202601081444.sql
-- Modify to use ON CONFLICT

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
    -- Extract from models_202601081444.sql
    -- You'll need to parse the INSERT statements
) AS old(...)
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
    -- Extract from your export file
) old
JOIN models new ON old.version = new.version;

-- ============================================================================
-- STEP 4: IMPORT CALIBRATION DATA
-- ============================================================================
-- Import calibration curves (map model_id and league_id)

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
    -- Extract from calibration_data_202601081444.sql
    -- Parse INSERT statements
) AS old(model_id, league_id, outcome_type, predicted_prob_bucket, actual_frequency, sample_count, created_at)
LEFT JOIN model_id_map m ON old.model_id = m.old_id
LEFT JOIN league_id_map l ON old.league_id = l.old_id
ON CONFLICT (model_id, league_id, outcome_type, predicted_prob_bucket) DO UPDATE SET
    actual_frequency = EXCLUDED.actual_frequency,
    sample_count = EXCLUDED.sample_count;

-- ============================================================================
-- STEP 5: IMPORT LEAGUE DRAW PRIORS
-- ============================================================================
-- Import historical draw rates (map league_id)

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
    -- Extract from league_draw_priors_202601081444.sql
) AS old(league_id, season, draw_rate, sample_size, updated_at)
JOIN league_id_map l ON old.league_id = l.old_id
ON CONFLICT (league_id, season) DO UPDATE SET
    draw_rate = EXCLUDED.draw_rate,
    sample_size = EXCLUDED.sample_size,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- STEP 6: IMPORT H2H DRAW STATS
-- ============================================================================
-- Import head-to-head statistics (map team_id)

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
    -- Extract from h2h_draw_stats_202601081444.sql
) AS old(team_home_id, team_away_id, matches_played, draw_count, avg_goals, last_updated)
JOIN team_id_map th ON old.team_home_id = th.old_id
JOIN team_id_map ta ON old.team_away_id = ta.old_id
ON CONFLICT (team_home_id, team_away_id) DO UPDATE SET
    matches_played = EXCLUDED.matches_played,
    draw_count = EXCLUDED.draw_count,
    avg_goals = EXCLUDED.avg_goals,
    last_updated = EXCLUDED.last_updated;

-- ============================================================================
-- STEP 7: IMPORT OTHER TABLES
-- ============================================================================
-- Similar pattern for:
-- - team_elo (map team_id)
-- - referee_stats (no dependencies)
-- - league_structure (map league_id)
-- - jackpots & fixtures (map team_id, league_id)
-- - saved templates & results (no dependencies)
-- - training_runs (map model_id)

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 
    'Migration Summary' as status,
    (SELECT COUNT(*) FROM models) as models_count,
    (SELECT COUNT(*) FROM calibration_data) as calibration_count,
    (SELECT COUNT(*) FROM league_draw_priors) as draw_priors_count,
    (SELECT COUNT(*) FROM h2h_draw_stats) as h2h_count;

COMMIT;

-- ============================================================================
-- IMPORTANT NOTES
-- ============================================================================
-- 
-- This script is a TEMPLATE. You need to:
-- 
-- 1. Extract INSERT statements from your SQL export files
-- 2. Modify them to use ON CONFLICT DO UPDATE
-- 3. Add ID mapping logic
-- 4. Run each section separately
-- 
-- OR use the Python script: import_from_sql_exports.py
-- which automates this process
-- 
-- ============================================================================

