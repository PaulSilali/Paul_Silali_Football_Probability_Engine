-- ============================================================================
-- SIMPLE IMPORT FROM SQL EXPORT FILES
-- ============================================================================
-- 
-- This script provides a simple way to import data from SQL export files.
-- 
-- IMPORTANT:
-- 1. Run this AFTER running the new schema
-- 2. You'll need to manually copy-paste INSERT statements from your export files
-- 3. Modify them to remove ID columns and use ON CONFLICT
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: IMPORT LEAGUES
-- ============================================================================
-- Copy-paste INSERT statements from leagues_202601081444.sql
-- Remove the 'id' column and add ON CONFLICT clause

-- Example (modify with your actual data):
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
VALUES 
    ('E0', 'Premier League', 'England', 1, 0.26, 0.35, true),
    ('SP1', 'La Liga', 'Spain', 1, 0.25, 0.30, true)
    -- Add more from your export file
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    tier = EXCLUDED.tier,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active,
    updated_at = now();

-- ============================================================================
-- STEP 2: IMPORT TEAMS
-- ============================================================================
-- Copy-paste INSERT statements from teams_202601081444.sql
-- Remove the 'id' column
-- Map league_id using: SELECT id FROM leagues WHERE code = 'E0'

-- Example (modify with your actual data):
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias, alternative_names)
SELECT 
    l.id as league_id,
    'Brighton' as name,
    'brighton' as canonical_name,
    1.0 as attack_rating,
    1.0 as defense_rating,
    0.0 as home_bias,
    NULL as alternative_names
FROM leagues l WHERE l.code = 'E0'
ON CONFLICT (canonical_name, league_id) DO UPDATE SET
    name = EXCLUDED.name,
    attack_rating = EXCLUDED.attack_rating,
    defense_rating = EXCLUDED.defense_rating,
    home_bias = EXCLUDED.home_bias,
    alternative_names = EXCLUDED.alternative_names,
    updated_at = now();

-- ============================================================================
-- STEP 3: IMPORT MODELS
-- ============================================================================
-- Copy-paste INSERT statements from models_202601081444.sql
-- Remove the 'id' column
-- Use ON CONFLICT (version)

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
    -- Copy-paste VALUES from models_202601081444.sql
    -- Remove 'id' column
    VALUES
        ('v1.0.0', 'poisson', 'active'::model_status, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '{}'::jsonb, now(), now())
    -- Add more from your export file
) AS old(...)
ON CONFLICT (version) DO UPDATE SET
    model_type = EXCLUDED.model_type,
    status = EXCLUDED.status,
    training_completed_at = EXCLUDED.training_completed_at,
    model_weights = EXCLUDED.model_weights,
    updated_at = now();

-- ============================================================================
-- STEP 4: IMPORT CALIBRATION DATA
-- ============================================================================
-- Copy-paste INSERT statements from calibration_data_202601081444.sql
-- Map model_id and league_id using subqueries

INSERT INTO calibration_data (
    model_id, league_id, outcome_type,
    predicted_prob_bucket, actual_frequency, sample_count, created_at
)
SELECT 
    (SELECT id FROM models WHERE version = 'v1.0.0') as model_id,  -- Map model_id
    (SELECT id FROM leagues WHERE code = 'E0') as league_id,  -- Map league_id
    outcome_type::match_result,
    predicted_prob_bucket,
    actual_frequency,
    sample_count,
    created_at
FROM (
    -- Copy-paste VALUES from calibration_data_202601081444.sql
    -- Remove 'id' column
    VALUES
        (NULL, NULL, 'H'::match_result, 0.02, 0.2973, 37, now())
    -- Add more from your export file
) AS old(model_id, league_id, outcome_type, predicted_prob_bucket, actual_frequency, sample_count, created_at)
ON CONFLICT (model_id, league_id, outcome_type, predicted_prob_bucket) DO UPDATE SET
    actual_frequency = EXCLUDED.actual_frequency,
    sample_count = EXCLUDED.sample_count;

-- ============================================================================
-- STEP 5: IMPORT OTHER TABLES
-- ============================================================================
-- Similar pattern for:
-- - league_draw_priors (map league_id)
-- - h2h_draw_stats (map team_id)
-- - team_elo (map team_id)
-- - referee_stats (no dependencies)
-- - league_structure (map league_id)
-- - jackpots & fixtures (map team_id, league_id)
-- - saved templates & results (no dependencies)
-- - training_runs (map model_id)

COMMIT;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- This is a TEMPLATE. You need to:
-- 
-- 1. Open each SQL export file in a text editor
-- 2. Copy the INSERT statements
-- 3. Remove the 'id' column (first column)
-- 4. Add ON CONFLICT clause
-- 5. Map foreign keys using subqueries
-- 
-- OR use the Python script: import_from_sql_exports.py
-- 
-- ============================================================================

