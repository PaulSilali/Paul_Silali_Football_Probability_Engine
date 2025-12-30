-- SQL Query to Check Model Chain
-- Run this in PostgreSQL to see the model relationships

-- Show active models
SELECT 
    id,
    version,
    model_type,
    status,
    training_completed_at,
    brier_score,
    overall_accuracy
FROM models
WHERE status = 'active'
ORDER BY model_type, training_completed_at DESC;

-- Show model chain (Calibration -> Blending -> Poisson)
WITH calibration_model AS (
    SELECT id, version, model_weights
    FROM models
    WHERE model_type = 'calibration' AND status = 'active'
    ORDER BY training_completed_at DESC
    LIMIT 1
),
blending_model AS (
    SELECT m.id, m.version, m.model_weights
    FROM models m
    JOIN calibration_model cm ON (cm.model_weights->>'base_model_id')::int = m.id
    WHERE m.model_type = 'blending'
),
poisson_model AS (
    SELECT m.id, m.version, m.status, m.model_weights
    FROM models m
    JOIN blending_model bm ON (bm.model_weights->>'poisson_model_id')::int = m.id
    WHERE m.model_type = 'poisson'
),
latest_poisson AS (
    SELECT id, version, status, training_completed_at
    FROM models
    WHERE model_type = 'poisson'
    ORDER BY training_completed_at DESC
    LIMIT 1
)
SELECT 
    'Calibration' as model_level,
    cm.version as version,
    cm.id as id,
    NULL as status
FROM calibration_model cm
UNION ALL
SELECT 
    'Blending' as model_level,
    bm.version as version,
    bm.id as id,
    NULL as status
FROM blending_model bm
UNION ALL
SELECT 
    'Poisson (Current)' as model_level,
    pm.version as version,
    pm.id as id,
    pm.status::text as status
FROM poisson_model pm
UNION ALL
SELECT 
    'Poisson (Latest)' as model_level,
    lp.version as version,
    lp.id as id,
    lp.status::text as status
FROM latest_poisson lp;

-- Check for negative home_advantage in Poisson models
SELECT 
    id,
    version,
    status,
    (model_weights->>'home_advantage')::float as home_advantage,
    (model_weights->>'rho')::float as rho,
    jsonb_array_length(model_weights->'team_strengths') as team_count
FROM models
WHERE model_type = 'poisson'
ORDER BY training_completed_at DESC;

-- Show blending model's poisson reference
SELECT 
    b.id as blending_id,
    b.version as blending_version,
    (b.model_weights->>'poisson_model_id')::int as poisson_model_id,
    p.version as poisson_version,
    p.status as poisson_status,
    p.training_completed_at as poisson_trained_at
FROM models b
LEFT JOIN models p ON p.id = (b.model_weights->>'poisson_model_id')::int
WHERE b.model_type = 'blending' AND b.status = 'active'
ORDER BY b.training_completed_at DESC;

