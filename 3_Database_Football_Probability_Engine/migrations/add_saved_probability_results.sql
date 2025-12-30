-- ============================================================================
-- SAVED PROBABILITY RESULTS TABLE
-- ============================================================================
-- Allows users to save their probability output selections and actual results
-- for backtesting and performance tracking

CREATE TABLE IF NOT EXISTS saved_probability_results (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR,                            -- User identifier (string for flexibility)
    jackpot_id      VARCHAR NOT NULL,                   -- Reference to jackpot
    name            VARCHAR NOT NULL,                   -- User-provided name
    description     TEXT,                               -- Optional description
    
    -- Probability set selections (user picks per set)
    selections      JSONB NOT NULL,                      -- {"A": {"1": "1", "2": "X", ...}, "B": {...}}
    
    -- Actual results (entered after matches complete)
    actual_results  JSONB,                              -- {"1": "X", "2": "1", ...} (fixture_id -> result)
    
    -- Score tracking per set
    scores          JSONB,                              -- {"A": {"correct": 10, "total": 15}, "B": {...}}
    
    -- Metadata
    model_version   VARCHAR,                            -- Model version used
    total_fixtures  INTEGER NOT NULL DEFAULT 0,         -- Number of fixtures
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_total_fixtures CHECK (total_fixtures >= 1 AND total_fixtures <= 20)
);

CREATE INDEX idx_saved_results_user ON saved_probability_results(user_id);
CREATE INDEX idx_saved_results_jackpot ON saved_probability_results(jackpot_id);
CREATE INDEX idx_saved_results_created ON saved_probability_results(created_at DESC);

COMMENT ON TABLE saved_probability_results IS 'Saved probability output selections and actual results for backtesting';
COMMENT ON COLUMN saved_probability_results.selections IS 'User selections per probability set: {"A": {"fixture_1": "1", "fixture_2": "X"}, "B": {...}}';
COMMENT ON COLUMN saved_probability_results.actual_results IS 'Actual match results: {"fixture_1": "X", "fixture_2": "1"}';
COMMENT ON COLUMN saved_probability_results.scores IS 'Score tracking per set: {"A": {"correct": 10, "total": 15}, "B": {...}}';

