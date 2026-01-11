-- ============================================================================
-- Versioned Probability Calibration Table
-- ============================================================================
-- This table stores versioned calibration curves for safe, reversible updates.
-- Each calibration is versioned and can be activated/deactivated independently.

CREATE TABLE IF NOT EXISTS probability_calibration (
    calibration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome CHAR(1) NOT NULL CHECK (outcome IN ('H', 'D', 'A')),
    league TEXT,  -- NULL for global calibration, league code for league-specific
    model_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,  -- NULL if still valid
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_blob BYTEA NOT NULL,  -- Serialized isotonic regression model (pickle)
    samples_used INTEGER NOT NULL,
    notes TEXT,
    
    CONSTRAINT chk_outcome CHECK (outcome IN ('H', 'D', 'A'))
);

CREATE INDEX IF NOT EXISTS idx_calibration_outcome ON probability_calibration(outcome);
CREATE INDEX IF NOT EXISTS idx_calibration_model_version ON probability_calibration(model_version);
CREATE INDEX IF NOT EXISTS idx_calibration_active ON probability_calibration(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_calibration_league ON probability_calibration(league) WHERE league IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_calibration_created ON probability_calibration(created_at DESC);

COMMENT ON TABLE probability_calibration IS 'Versioned calibration curves for probability calibration (isotonic regression models)';
COMMENT ON COLUMN probability_calibration.calibration_blob IS 'Serialized sklearn.isotonic.IsotonicRegression model (pickle format)';
COMMENT ON COLUMN probability_calibration.outcome IS 'Outcome type: H (home), D (draw), A (away)';
COMMENT ON COLUMN probability_calibration.league IS 'League code for league-specific calibration, NULL for global';
COMMENT ON COLUMN probability_calibration.is_active IS 'Only one active calibration per (outcome, league, model_version)';

-- ============================================================================
-- Market Disagreement Analysis View
-- ============================================================================
-- Materialized view for analyzing model-market disagreement patterns

CREATE MATERIALIZED VIEW IF NOT EXISTS market_disagreement_analysis AS
SELECT
    ROUND(ABS(ps.prob_home - (1.0 / jf.odds_home))::numeric, 2) AS delta_home,
    ROUND(ABS(ps.prob_draw - (1.0 / jf.odds_draw))::numeric, 2) AS delta_draw,
    ROUND(ABS(ps.prob_away - (1.0 / jf.odds_away))::numeric, 2) AS delta_away,
    CASE WHEN jf.actual_result = 'H' THEN 1 ELSE 0 END AS y_home,
    CASE WHEN jf.actual_result = 'D' THEN 1 ELSE 0 END AS y_draw,
    CASE WHEN jf.actual_result = 'A' THEN 1 ELSE 0 END AS y_away,
    ps.league,
    ps.model_version,
    ps.created_at
FROM prediction_snapshot ps
JOIN jackpot_fixtures jf ON ps.fixture_id = jf.id
WHERE jf.actual_result IS NOT NULL
  AND jf.odds_home IS NOT NULL
  AND jf.odds_draw IS NOT NULL
  AND jf.odds_away IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_market_disagreement_delta_home ON market_disagreement_analysis(delta_home);
CREATE INDEX IF NOT EXISTS idx_market_disagreement_delta_draw ON market_disagreement_analysis(delta_draw);
CREATE INDEX IF NOT EXISTS idx_market_disagreement_delta_away ON market_disagreement_analysis(delta_away);
CREATE INDEX IF NOT EXISTS idx_market_disagreement_league ON market_disagreement_analysis(league);

COMMENT ON MATERIALIZED VIEW market_disagreement_analysis IS 'Analysis of model-market disagreement patterns for calibration and penalty tuning';

-- ============================================================================
-- Calibration Dataset View
-- ============================================================================
-- View for extracting calibration dataset from prediction_snapshot and actual results

CREATE OR REPLACE VIEW calibration_dataset AS
SELECT
    ps.fixture_id,
    ps.created_at,
    ps.league,
    ps.model_version,
    ps.prob_home,
    ps.prob_draw,
    ps.prob_away,
    jf.actual_result,
    CASE WHEN jf.actual_result = 'H' THEN 1 ELSE 0 END AS y_home,
    CASE WHEN jf.actual_result = 'D' THEN 1 ELSE 0 END AS y_draw,
    CASE WHEN jf.actual_result = 'A' THEN 1 ELSE 0 END AS y_away,
    jf.odds_home,
    jf.odds_draw,
    jf.odds_away,
    ABS(ps.prob_home - (1.0 / jf.odds_home)) AS market_disagreement_home,
    ABS(ps.prob_draw - (1.0 / jf.odds_draw)) AS market_disagreement_draw,
    ABS(ps.prob_away - (1.0 / jf.odds_away)) AS market_disagreement_away
FROM prediction_snapshot ps
JOIN jackpot_fixtures jf ON ps.fixture_id = jf.id
WHERE jf.actual_result IS NOT NULL;

COMMENT ON VIEW calibration_dataset IS 'Calibration dataset combining prediction_snapshot with actual results and odds';

