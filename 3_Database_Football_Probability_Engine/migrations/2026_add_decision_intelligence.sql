-- ============================================================================
-- DECISION INTELLIGENCE TABLES MIGRATION
-- ============================================================================
-- Date: 2026-01-11
-- Purpose: Add decision intelligence layer for EV-weighted scoring and 
--          automatic threshold learning
-- 
-- This migration adds:
-- 1. prediction_snapshot - Snapshot of beliefs at decision time
-- 2. ticket - Ticket as first-class object with decision scores
-- 3. ticket_pick - Pick-level reasoning and EV scores
-- 4. ticket_outcome - Outcome closure for learning
--
-- NON-DESTRUCTIVE: Only adds new tables, does not modify existing ones
-- Safe to run in production
-- 
-- IMPORTANT: If you get a transaction error, you must rollback first:
--   ROLLBACK;
-- Then re-run this entire migration
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PREDICTION SNAPSHOT TABLE
-- ============================================================================
-- Snapshot of beliefs at decision time for auditability

CREATE TABLE IF NOT EXISTS prediction_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    fixture_id INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    model_version TEXT NOT NULL,
    prob_home DOUBLE PRECISION NOT NULL CHECK (prob_home >= 0 AND prob_home <= 1),
    prob_draw DOUBLE PRECISION NOT NULL CHECK (prob_draw >= 0 AND prob_draw <= 1),
    prob_away DOUBLE PRECISION NOT NULL CHECK (prob_away >= 0 AND prob_away <= 1),
    xg_home DOUBLE PRECISION CHECK (xg_home >= 0),
    xg_away DOUBLE PRECISION CHECK (xg_away >= 0),
    xg_confidence DOUBLE PRECISION CHECK (xg_confidence >= 0 AND xg_confidence <= 1),
    dc_applied BOOLEAN DEFAULT FALSE,
    league TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_prob_sum CHECK (abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001)
);

CREATE INDEX IF NOT EXISTS idx_prediction_snapshot_fixture ON prediction_snapshot(fixture_id);
CREATE INDEX IF NOT EXISTS idx_prediction_snapshot_model ON prediction_snapshot(model_version);
CREATE INDEX IF NOT EXISTS idx_prediction_snapshot_created ON prediction_snapshot(created_at DESC);

COMMENT ON TABLE prediction_snapshot IS 'Snapshot of model beliefs at decision time for auditability and learning';
COMMENT ON COLUMN prediction_snapshot.xg_confidence IS 'Confidence factor based on xG variance: 1 / (1 + abs(xg_home - xg_away))';
COMMENT ON COLUMN prediction_snapshot.dc_applied IS 'Whether Dixon-Coles adjustment was applied to this prediction';

-- ============================================================================
-- 2. TICKET TABLE
-- ============================================================================
-- Ticket as first-class object with decision intelligence metadata

CREATE TABLE IF NOT EXISTS ticket (
    ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jackpot_id INTEGER REFERENCES jackpots(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ticket_type TEXT NOT NULL DEFAULT 'standard',  -- 'standard', 'high_confidence', 'experimental'
    archetype TEXT,  -- FAVORITE_LOCK, BALANCED, DRAW_SELECTIVE, AWAY_EDGE
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    ev_score DOUBLE PRECISION,  -- Total EV-weighted score (UDS)
    contradictions INTEGER NOT NULL DEFAULT 0 CHECK (contradictions >= 0),
    max_contradictions_allowed INTEGER NOT NULL DEFAULT 1,
    ev_threshold_used DOUBLE PRECISION,  -- Threshold used at decision time
    decision_version TEXT NOT NULL DEFAULT 'UDS_v1',  -- Version of decision scoring algorithm
    notes TEXT,
    created_by_user_id VARCHAR,
    
    CONSTRAINT chk_contradictions CHECK (contradictions <= max_contradictions_allowed OR NOT accepted)
);

CREATE INDEX IF NOT EXISTS idx_ticket_jackpot ON ticket(jackpot_id);
CREATE INDEX IF NOT EXISTS idx_ticket_created ON ticket(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ticket_accepted ON ticket(accepted);
CREATE INDEX IF NOT EXISTS idx_ticket_ev_score ON ticket(ev_score) WHERE ev_score IS NOT NULL;

COMMENT ON TABLE ticket IS 'Ticket as first-class object with decision intelligence metadata';
COMMENT ON COLUMN ticket.ev_score IS 'Unified Decision Score (UDS) - EV-weighted score with structural penalties';
COMMENT ON COLUMN ticket.contradictions IS 'Number of hard contradictions detected in ticket';
COMMENT ON COLUMN ticket.ev_threshold_used IS 'EV threshold used at decision time (for auditability)';

-- ============================================================================
-- 3. TICKET PICK TABLE
-- ============================================================================
-- Pick-level reasoning and EV scores

CREATE TABLE IF NOT EXISTS ticket_pick (
    ticket_id UUID NOT NULL REFERENCES ticket(ticket_id) ON DELETE CASCADE,
    fixture_id INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    pick CHAR(1) NOT NULL CHECK (pick IN ('1', 'X', '2')),  -- 1=Home, X=Draw, 2=Away
    market_odds DOUBLE PRECISION NOT NULL CHECK (market_odds > 1.0),
    model_prob DOUBLE PRECISION NOT NULL CHECK (model_prob >= 0 AND model_prob <= 1),
    ev_score DOUBLE PRECISION,  -- Pick-level EV (PDV)
    xg_diff DOUBLE PRECISION,  -- abs(xg_home - xg_away)
    confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
    structural_penalty DOUBLE PRECISION DEFAULT 0 CHECK (structural_penalty >= 0),
    league_weight DOUBLE PRECISION DEFAULT 1.0 CHECK (league_weight > 0),
    is_contradiction BOOLEAN NOT NULL DEFAULT FALSE,
    is_hard_contradiction BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (ticket_id, fixture_id)
);

CREATE INDEX IF NOT EXISTS idx_ticket_pick_ticket ON ticket_pick(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_pick_fixture ON ticket_pick(fixture_id);
CREATE INDEX IF NOT EXISTS idx_ticket_pick_contradiction ON ticket_pick(is_hard_contradiction) WHERE is_hard_contradiction = TRUE;
CREATE INDEX IF NOT EXISTS idx_ticket_pick_ev_score ON ticket_pick(ev_score) WHERE ev_score IS NOT NULL;

COMMENT ON TABLE ticket_pick IS 'Pick-level reasoning and EV scores for each match in a ticket';
COMMENT ON COLUMN ticket_pick.ev_score IS 'Pick Decision Value (PDV) - EV-weighted score for this pick';
COMMENT ON COLUMN ticket_pick.is_hard_contradiction IS 'Hard contradiction flag - if TRUE, pick should be rejected';
COMMENT ON COLUMN ticket_pick.structural_penalty IS 'Structural penalty applied (draw odds > 3.4, etc.)';

-- ============================================================================
-- 4. TICKET OUTCOME TABLE
-- ============================================================================
-- Outcome closure for threshold learning

CREATE TABLE IF NOT EXISTS ticket_outcome (
    ticket_id UUID PRIMARY KEY REFERENCES ticket(ticket_id) ON DELETE CASCADE,
    correct_picks INTEGER NOT NULL DEFAULT 0 CHECK (correct_picks >= 0),
    total_picks INTEGER NOT NULL DEFAULT 0 CHECK (total_picks > 0),
    hit_rate DOUBLE PRECISION NOT NULL CHECK (hit_rate >= 0 AND hit_rate <= 1),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actual_results JSONB,  -- Store actual match results for analysis
    
    CONSTRAINT chk_hit_rate CHECK (hit_rate = correct_picks::DOUBLE PRECISION / total_picks)
);

CREATE INDEX IF NOT EXISTS idx_ticket_outcome_hit_rate ON ticket_outcome(hit_rate);
CREATE INDEX IF NOT EXISTS idx_ticket_outcome_evaluated ON ticket_outcome(evaluated_at DESC);

COMMENT ON TABLE ticket_outcome IS 'Outcome closure for threshold learning and performance tracking';
COMMENT ON COLUMN ticket_outcome.hit_rate IS 'Hit rate: correct_picks / total_picks';
COMMENT ON COLUMN ticket_outcome.actual_results IS 'JSON object mapping fixture_id to actual result (1/X/2)';

-- ============================================================================
-- 5. DECISION THRESHOLDS TABLE
-- ============================================================================
-- Learned thresholds for automatic tuning

CREATE TABLE IF NOT EXISTS decision_thresholds (
    id SERIAL PRIMARY KEY,
    threshold_type TEXT NOT NULL UNIQUE,  -- 'ev_threshold', 'max_contradictions', etc.
    value DOUBLE PRECISION NOT NULL,
    learned_from_samples INTEGER DEFAULT 0,
    learned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_decision_thresholds_type ON decision_thresholds(threshold_type);
CREATE INDEX IF NOT EXISTS idx_decision_thresholds_active ON decision_thresholds(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE decision_thresholds IS 'Learned thresholds for decision intelligence (auto-tuned from historical data)';
COMMENT ON COLUMN decision_thresholds.threshold_type IS 'Type of threshold: ev_threshold, max_contradictions, etc.';
COMMENT ON COLUMN decision_thresholds.value IS 'Threshold value (learned from historical performance)';

-- Insert default thresholds (will be updated by learning process)
DO $$
BEGIN
    INSERT INTO decision_thresholds (threshold_type, value, notes) VALUES
        ('ev_threshold', 0.12, 'Default EV threshold - will be learned from data'),
        ('max_contradictions', 1, 'Maximum allowed hard contradictions per ticket'),
        ('entropy_penalty', 0.05, 'Entropy penalty coefficient (mu)'),
        ('contradiction_penalty', 10.0, 'Hard penalty for contradictions (lambda)')
    ON CONFLICT (threshold_type) DO NOTHING;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not insert decision thresholds: %', SQLERRM;
END $$;

-- ============================================================================
-- 6. LEAGUE RELIABILITY WEIGHTS TABLE
-- ============================================================================
-- League-specific reliability weights for UDS calculation

CREATE TABLE IF NOT EXISTS league_reliability_weights (
    league_code VARCHAR(10) PRIMARY KEY REFERENCES leagues(code) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (weight > 0),
    learned_from_samples INTEGER DEFAULT 0,
    learned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_league_weights_code ON league_reliability_weights(league_code);
CREATE INDEX IF NOT EXISTS idx_league_weights_weight ON league_reliability_weights(weight);

COMMENT ON TABLE league_reliability_weights IS 'League-specific reliability weights for UDS calculation';
COMMENT ON COLUMN league_reliability_weights.weight IS 'Reliability weight (w_L) - typically 0.9-1.1';

-- Insert default weights for major leagues (using DO block to handle errors gracefully)
DO $$
BEGIN
    INSERT INTO league_reliability_weights (league_code, weight) VALUES
        ('E0', 1.00),
        ('SP1', 0.97),
        ('D1', 0.95),
        ('I1', 1.02),
        ('I2', 1.05),
        ('F1', 1.00),
        ('F2', 1.04)
    ON CONFLICT (league_code) DO NOTHING;
EXCEPTION WHEN OTHERS THEN
    -- If table doesn't exist yet or other error, continue
    RAISE NOTICE 'Could not insert league weights: %', SQLERRM;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'prediction_snapshot', 'ticket', 'ticket_pick', 
        'ticket_outcome', 'decision_thresholds', 'league_reliability_weights'
    ];
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
        RAISE NOTICE 'All decision intelligence tables created successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

