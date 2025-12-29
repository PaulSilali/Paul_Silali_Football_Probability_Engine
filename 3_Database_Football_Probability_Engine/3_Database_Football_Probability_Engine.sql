-- ============================================================================
-- FOOTBALL JACKPOT PROBABILITY ENGINE - DATABASE SCHEMA
-- ============================================================================
-- 
-- Version: 2.0.0
-- Database: PostgreSQL 15+
-- 
-- This schema aligns with:
-- - Backend: FastAPI + SQLAlchemy 2.0 models
-- - Frontend: React + TypeScript types
-- 
-- GUARANTEES:
-- - Deterministic replay
-- - Immutable jackpot predictions
-- - Probability correctness enforced at DB level
-- - Audit-safe
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Model status enum
DO $$ BEGIN
    CREATE TYPE model_status AS ENUM ('active', 'archived', 'failed', 'training');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Prediction set enum (A-G)
DO $$ BEGIN
    CREATE TYPE prediction_set AS ENUM ('A', 'B', 'C', 'D', 'E', 'F', 'G');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Match result enum
DO $$ BEGIN
    CREATE TYPE match_result AS ENUM ('H', 'D', 'A');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Data source status enum
DO $$ BEGIN
    CREATE TYPE data_source_status AS ENUM ('fresh', 'stale', 'warning', 'error');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- REFERENCE TABLES
-- ============================================================================

-- Leagues table
CREATE TABLE IF NOT EXISTS leagues (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR NOT NULL UNIQUE,           -- 'E0', 'SP1', etc.
    name            VARCHAR NOT NULL,                   -- 'Premier League'
    country         VARCHAR NOT NULL,                   -- 'England'
    tier            INTEGER DEFAULT 1,
    avg_draw_rate   DOUBLE PRECISION DEFAULT 0.26,     -- Historical average
    home_advantage  DOUBLE PRECISION DEFAULT 0.35,      -- League-specific home advantage
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE leagues IS 'Football league reference data';
COMMENT ON COLUMN leagues.code IS 'Unique league code (e.g., E0 for Premier League)';
COMMENT ON COLUMN leagues.avg_draw_rate IS 'Historical draw rate for league (0.0-1.0)';

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    name            VARCHAR NOT NULL,                   -- Display name
    canonical_name  VARCHAR NOT NULL,                   -- Normalized for matching
    attack_rating   DOUBLE PRECISION DEFAULT 1.0,       -- From Dixon-Coles
    defense_rating  DOUBLE PRECISION DEFAULT 1.0,       -- From Dixon-Coles
    home_bias       DOUBLE PRECISION DEFAULT 0.0,       -- Team-specific home advantage
    last_calculated TIMESTAMPTZ,                         -- Last strength update
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_team_league UNIQUE (canonical_name, league_id)
);

COMMENT ON TABLE teams IS 'Team registry with Dixon-Coles strength parameters';
COMMENT ON COLUMN teams.canonical_name IS 'Normalized team name for matching across sources';
COMMENT ON COLUMN teams.attack_rating IS 'Attack strength α (log scale, ~1.0 average)';
COMMENT ON COLUMN teams.defense_rating IS 'Defense strength β (log scale, ~1.0 average)';

-- ============================================================================
-- HISTORICAL DATA
-- ============================================================================

-- Matches table (historical results for training)
CREATE TABLE IF NOT EXISTS matches (
    id              BIGSERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season          VARCHAR NOT NULL,                   -- '2023-24'
    match_date      DATE NOT NULL,
    home_team_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    away_team_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    home_goals      INTEGER NOT NULL,
    away_goals      INTEGER NOT NULL,
    result          match_result NOT NULL,              -- 'H', 'D', or 'A'
    
    -- Closing odds ONLY (no opening, no in-play)
    odds_home       DOUBLE PRECISION,
    odds_draw       DOUBLE PRECISION,
    odds_away       DOUBLE PRECISION,
    
    -- Market-implied probabilities (after margin removal)
    prob_home_market DOUBLE PRECISION,
    prob_draw_market DOUBLE PRECISION,
    prob_away_market DOUBLE PRECISION,
    
    -- Data source tracking
    source          VARCHAR DEFAULT 'football-data.co.uk',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match UNIQUE (home_team_id, away_team_id, match_date)
);

COMMENT ON TABLE matches IS 'Historical match results with closing odds (training data)';
COMMENT ON COLUMN matches.result IS 'Match result: H (home win), D (draw), A (away win)';

-- ============================================================================
-- FEATURE STORE
-- ============================================================================

-- Team features (rolling statistics)
CREATE TABLE IF NOT EXISTS team_features (
    id              BIGSERIAL PRIMARY KEY,
    team_id         INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    calculated_at   TIMESTAMPTZ NOT NULL,               -- Feature calculation date
    
    -- Rolling goal statistics
    goals_scored_5  DOUBLE PRECISION,                   -- Last 5 matches
    goals_scored_10 DOUBLE PRECISION,                    -- Last 10 matches
    goals_scored_20 DOUBLE PRECISION,                    -- Last 20 matches
    goals_conceded_5 DOUBLE PRECISION,
    goals_conceded_10 DOUBLE PRECISION,
    goals_conceded_20 DOUBLE PRECISION,
    
    -- Rolling form
    win_rate_5      DOUBLE PRECISION,
    win_rate_10     DOUBLE PRECISION,
    draw_rate_5     DOUBLE PRECISION,
    draw_rate_10    DOUBLE PRECISION,
    
    -- Home/away splits
    home_win_rate   DOUBLE PRECISION,
    away_win_rate   DOUBLE PRECISION,
    
    -- Other metrics
    avg_rest_days   DOUBLE PRECISION,
    league_position INTEGER,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE team_features IS 'Versioned team feature snapshots for reproducibility';

-- League statistics (optional - for league-level baseline stats)
CREATE TABLE IF NOT EXISTS league_stats (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season          VARCHAR NOT NULL,
    calculated_at   TIMESTAMPTZ NOT NULL,
    
    total_matches   INTEGER NOT NULL,
    home_win_rate   DOUBLE PRECISION NOT NULL,
    draw_rate       DOUBLE PRECISION NOT NULL,
    away_win_rate   DOUBLE PRECISION NOT NULL,
    avg_goals_per_match DOUBLE PRECISION NOT NULL,
    home_advantage_factor DOUBLE PRECISION NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_league_stats UNIQUE (league_id, season)
);

COMMENT ON TABLE league_stats IS 'League-level baseline statistics per season';

-- ============================================================================
-- MODEL REGISTRY
-- ============================================================================

-- Models table
CREATE TABLE IF NOT EXISTS models (
    id              SERIAL PRIMARY KEY,
    version         VARCHAR NOT NULL UNIQUE,            -- 'v2.4.1'
    model_type      VARCHAR NOT NULL,                   -- 'dixon-coles'
    status          model_status NOT NULL DEFAULT 'active',
    
    -- Training metadata
    training_started_at TIMESTAMPTZ,
    training_completed_at TIMESTAMPTZ,
    training_matches INTEGER,
    training_leagues JSONB,                             -- ['E0', 'SP1']
    training_seasons JSONB,                             -- ['2020-21', '2021-22']
    
    -- Model parameters (IMMUTABLE after training)
    decay_rate      DOUBLE PRECISION,                   -- Time decay xi
    blend_alpha     DOUBLE PRECISION,                   -- Model vs market weight
    
    -- Validation metrics
    brier_score     DOUBLE PRECISION,
    log_loss        DOUBLE PRECISION,
    draw_accuracy   DOUBLE PRECISION,
    overall_accuracy DOUBLE PRECISION,
    
    -- Stored model weights (JSON)
    model_weights   JSONB,                              -- {team_strengths, calibration_curves}
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE models IS 'Trained model registry with immutable parameters';
COMMENT ON COLUMN models.model_weights IS 'Serialized model parameters and calibration curves';

-- Training runs table
CREATE TABLE IF NOT EXISTS training_runs (
    id              SERIAL PRIMARY KEY,
    model_id        INTEGER REFERENCES models(id) ON DELETE CASCADE,
    run_type        VARCHAR NOT NULL,                   -- 'full', 'incremental'
    status          model_status DEFAULT 'active',
    
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    
    -- Data range
    match_count     INTEGER,
    date_from       DATE,
    date_to         DATE,
    
    -- Results
    brier_score     DOUBLE PRECISION,
    log_loss        DOUBLE PRECISION,
    validation_accuracy DOUBLE PRECISION,
    
    -- Diagnostics
    error_message   TEXT,
    logs            JSONB,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE training_runs IS 'Training job execution history with full audit trail';

-- ============================================================================
-- USER & AUTH TABLES
-- ============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR NOT NULL UNIQUE,
    name            VARCHAR NOT NULL,
    hashed_password VARCHAR,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE users IS 'User accounts for authentication';

-- ============================================================================
-- JACKPOT TABLES
-- ============================================================================

-- Jackpots table
CREATE TABLE IF NOT EXISTS jackpots (
    id              SERIAL PRIMARY KEY,
    jackpot_id      VARCHAR NOT NULL UNIQUE,            -- 'JK-2024-1230'
    user_id         VARCHAR,                            -- User identifier (string for flexibility)
    name            VARCHAR,                            -- User-provided name
    kickoff_date    DATE,
    status          VARCHAR NOT NULL DEFAULT 'pending', -- 'pending', 'calculated', 'validated'
    model_version   VARCHAR,                            -- Model version used
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE jackpots IS 'User jackpot submissions';
COMMENT ON COLUMN jackpots.jackpot_id IS 'Human-readable jackpot identifier';

-- Jackpot fixtures table
CREATE TABLE IF NOT EXISTS jackpot_fixtures (
    id              SERIAL PRIMARY KEY,
    jackpot_id      INTEGER NOT NULL REFERENCES jackpots(id) ON DELETE CASCADE,
    match_order     INTEGER NOT NULL,                   -- Order in jackpot (1-13)
    
    -- Raw user input (preserved)
    home_team       VARCHAR NOT NULL,
    away_team       VARCHAR NOT NULL,
    
    -- User-provided odds (required in backend model)
    odds_home       DOUBLE PRECISION NOT NULL,
    odds_draw       DOUBLE PRECISION NOT NULL,
    odds_away       DOUBLE PRECISION NOT NULL,
    
    -- Resolved team IDs (after canonicalization)
    home_team_id    INTEGER REFERENCES teams(id),
    away_team_id    INTEGER REFERENCES teams(id),
    league_id       INTEGER REFERENCES leagues(id),
    
    -- Actual result (for validation after matches complete)
    actual_result   match_result,
    actual_home_goals INTEGER,
    actual_away_goals INTEGER,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE jackpot_fixtures IS 'Individual fixtures within a jackpot';
COMMENT ON COLUMN jackpot_fixtures.match_order IS 'Position in jackpot (1-based)';

-- ============================================================================
-- PREDICTIONS TABLE
-- ============================================================================

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id              SERIAL PRIMARY KEY,
    fixture_id      INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    model_id        INTEGER NOT NULL REFERENCES models(id),
    set_type        prediction_set NOT NULL,            -- A, B, C, D, E, F, or G
    
    -- Final calibrated probabilities
    prob_home       DOUBLE PRECISION NOT NULL,
    prob_draw       DOUBLE PRECISION NOT NULL,
    prob_away       DOUBLE PRECISION NOT NULL,
    
    predicted_outcome match_result NOT NULL,            -- Highest probability
    confidence      DOUBLE PRECISION NOT NULL,         -- Max probability
    entropy         DOUBLE PRECISION,                   -- Prediction entropy
    
    -- Model components (for explainability)
    expected_home_goals DOUBLE PRECISION,               -- λ_home
    expected_away_goals DOUBLE PRECISION,               -- λ_away
    
    -- Pre-blending probabilities
    model_prob_home DOUBLE PRECISION,
    model_prob_draw DOUBLE PRECISION,
    model_prob_away DOUBLE PRECISION,
    
    -- Market-implied probabilities
    market_prob_home DOUBLE PRECISION,
    market_prob_draw DOUBLE PRECISION,
    market_prob_away DOUBLE PRECISION,
    
    blend_weight    DOUBLE PRECISION,                   -- Alpha used for this set
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Probability conservation constraint
    CONSTRAINT check_prob_sum CHECK (abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001)
);

COMMENT ON TABLE predictions IS 'Predicted probabilities for all sets (A-G)';
COMMENT ON COLUMN predictions.set_type IS 'Probability set identifier (A-G)';
COMMENT ON COLUMN predictions.entropy IS 'Prediction entropy for uncertainty quantification';

-- ============================================================================
-- VALIDATION & CALIBRATION
-- ============================================================================

-- Validation results table
CREATE TABLE IF NOT EXISTS validation_results (
    id              SERIAL PRIMARY KEY,
    jackpot_id      INTEGER REFERENCES jackpots(id) ON DELETE CASCADE,
    set_type        prediction_set NOT NULL,
    model_id        INTEGER REFERENCES models(id),
    
    -- Aggregate metrics
    total_matches   INTEGER,
    correct_predictions INTEGER,
    accuracy        DOUBLE PRECISION,
    brier_score     DOUBLE PRECISION,
    log_loss        DOUBLE PRECISION,
    
    -- Breakdown by outcome
    home_correct    INTEGER,
    home_total      INTEGER,
    draw_correct    INTEGER,
    draw_total      INTEGER,
    away_correct    INTEGER,
    away_total      INTEGER,
    
    -- Export to training data
    exported_to_training BOOLEAN DEFAULT FALSE,
    exported_at     TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE validation_results IS 'Validation metrics for predictions vs actuals';

-- Calibration data table
CREATE TABLE IF NOT EXISTS calibration_data (
    id              SERIAL PRIMARY KEY,
    model_id        INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    league_id       INTEGER REFERENCES leagues(id),
    outcome_type    match_result NOT NULL,              -- 'H', 'D', or 'A'
    
    -- Isotonic regression data
    predicted_prob_bucket DOUBLE PRECISION NOT NULL,   -- e.g., 0.05, 0.10, 0.15
    actual_frequency DOUBLE PRECISION NOT NULL,         -- Observed frequency in bucket
    sample_count    INTEGER NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_calibration_data UNIQUE (model_id, league_id, outcome_type, predicted_prob_bucket)
);

COMMENT ON TABLE calibration_data IS 'Isotonic calibration curves per outcome';
COMMENT ON COLUMN calibration_data.predicted_prob_bucket IS 'Predicted probability bin (e.g., 0.05 increments)';

-- ============================================================================
-- DATA INGESTION TRACKING
-- ============================================================================

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR NOT NULL UNIQUE,
    source_type     VARCHAR NOT NULL,                   -- 'football-data', 'api-football'
    status          VARCHAR DEFAULT 'fresh',            -- 'fresh', 'stale', 'warning', 'error'
    last_sync_at    TIMESTAMPTZ,
    record_count    INTEGER DEFAULT 0,
    last_error      TEXT,
    config          JSONB,                              -- Source-specific config
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE data_sources IS 'External data source registry';

-- Ingestion logs table
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER REFERENCES data_sources(id),
    
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR DEFAULT 'running',          -- 'running', 'success', 'failed'
    
    -- Metrics
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    
    error_message   TEXT,
    logs            JSONB,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ingestion_logs IS 'Data ingestion job execution logs';

-- ============================================================================
-- AUDIT LOGGING
-- ============================================================================

-- Audit entries table
CREATE TABLE IF NOT EXISTS audit_entries (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    action          VARCHAR NOT NULL,
    model_version   VARCHAR,
    probability_set VARCHAR,
    jackpot_id      VARCHAR,
    user_id         INTEGER REFERENCES users(id),
    details         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE audit_entries IS 'System audit trail for all actions';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Matches indexes
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date DESC);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league_id, season);

-- Teams indexes
CREATE INDEX IF NOT EXISTS idx_teams_canonical ON teams(canonical_name);
CREATE INDEX IF NOT EXISTS idx_teams_league ON teams(league_id);

-- Predictions indexes
CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id);
CREATE INDEX IF NOT EXISTS idx_predictions_set ON predictions(set_type);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);

-- Jackpot indexes
CREATE INDEX IF NOT EXISTS idx_jackpot_fixtures_jackpot ON jackpot_fixtures(jackpot_id);
CREATE INDEX IF NOT EXISTS idx_jackpots_user ON jackpots(user_id);
CREATE INDEX IF NOT EXISTS idx_jackpots_status ON jackpots(status);

-- Feature store indexes
CREATE INDEX IF NOT EXISTS idx_team_features_lookup ON team_features(team_id, calculated_at DESC);

-- Validation indexes
CREATE INDEX IF NOT EXISTS idx_validation_results_jackpot ON validation_results(jackpot_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_model ON validation_results(model_id);

-- Audit indexes
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_jackpot ON audit_entries(jackpot_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_entries(user_id);

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for leagues
DROP TRIGGER IF EXISTS update_leagues_updated_at ON leagues;
CREATE TRIGGER update_leagues_updated_at
    BEFORE UPDATE ON leagues
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for teams
DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for models
DROP TRIGGER IF EXISTS update_models_updated_at ON models;
CREATE TRIGGER update_models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for jackpots
DROP TRIGGER IF EXISTS update_jackpots_updated_at ON jackpots;
CREATE TRIGGER update_jackpots_updated_at
    BEFORE UPDATE ON jackpots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for users
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for data_sources
DROP TRIGGER IF EXISTS update_data_sources_updated_at ON data_sources;
CREATE TRIGGER update_data_sources_updated_at
    BEFORE UPDATE ON data_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA (OPTIONAL - DEVELOPMENT ONLY)
-- ============================================================================

-- Insert sample leagues
INSERT INTO leagues (code, name, country, home_advantage) VALUES
    ('E0', 'Premier League', 'England', 0.35),
    ('SP1', 'La Liga', 'Spain', 0.30),
    ('D1', 'Bundesliga', 'Germany', 0.32),
    ('I1', 'Serie A', 'Italy', 0.28),
    ('F1', 'Ligue 1', 'France', 0.33)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- SCHEMA VALIDATION
-- ============================================================================

-- Verify all tables created
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'leagues', 'teams', 'matches', 'team_features', 'league_stats',
        'models', 'training_runs', 'users', 'jackpots', 'jackpot_fixtures',
        'predictions', 'validation_results', 'calibration_data',
        'data_sources', 'ingestion_logs', 'audit_entries'
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
        RAISE NOTICE 'All tables created successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

