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
-- DATABASE CREATION
-- ============================================================================
-- IMPORTANT: Database creation cannot be done inside a transaction
-- 
-- Option 1: Run this command separately (recommended):
--   psql -U postgres -c "CREATE DATABASE football_probability_engine;"
--
-- Option 2: Connect to 'postgres' database and run:
--   CREATE DATABASE football_probability_engine;
--
-- Then connect to 'football_probability_engine' database and run this schema file

-- Attempt to create database (will fail if run inside transaction, use Option 1 or 2 above)
-- Uncomment the line below if running from 'postgres' database outside a transaction:
-- CREATE DATABASE football_probability_engine;

-- ============================================================================
-- SCHEMA CREATION (Run this after connecting to football_probability_engine database)
-- ============================================================================

BEGIN;

-- ============================================================================
-- DROP EXISTING OBJECTS (CLEAN SLATE)
-- ============================================================================
-- Drop in reverse dependency order to avoid constraint violations
-- Using CASCADE to automatically drop dependent objects

-- Drop all triggers first (they depend on tables)
DROP TRIGGER IF EXISTS update_leagues_updated_at ON leagues;
DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
DROP TRIGGER IF EXISTS update_models_updated_at ON models;
DROP TRIGGER IF EXISTS update_jackpots_updated_at ON jackpots;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_team_h2h_stats_updated_at ON team_h2h_stats;
DROP TRIGGER IF EXISTS update_data_sources_updated_at ON data_sources;

-- Drop all tables (CASCADE will handle foreign keys and indexes)
DROP TABLE IF EXISTS saved_probability_results CASCADE;
DROP TABLE IF EXISTS saved_jackpot_templates CASCADE;
DROP TABLE IF EXISTS audit_entries CASCADE;
DROP TABLE IF EXISTS ingestion_logs CASCADE;
DROP TABLE IF EXISTS data_sources CASCADE;
DROP TABLE IF EXISTS calibration_data CASCADE;
DROP TABLE IF EXISTS validation_results CASCADE;
DROP TABLE IF EXISTS predictions CASCADE;
DROP TABLE IF EXISTS jackpot_fixtures CASCADE;
DROP TABLE IF EXISTS jackpots CASCADE;
DROP TABLE IF EXISTS training_runs CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS league_stats CASCADE;
DROP TABLE IF EXISTS team_features CASCADE;
DROP TABLE IF EXISTS team_h2h_stats CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS leagues CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop all custom types/enums
DROP TYPE IF EXISTS prediction_set CASCADE;
DROP TYPE IF EXISTS match_result CASCADE;
DROP TYPE IF EXISTS matchresult CASCADE;  -- SQLAlchemy compatibility enum
DROP TYPE IF EXISTS model_status CASCADE;
DROP TYPE IF EXISTS data_source_status CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop indexes (if they exist independently, though CASCADE should handle most)
DROP INDEX IF EXISTS idx_models_active_per_type;

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

-- Prediction set enum (A-J)
DO $$ BEGIN
    CREATE TYPE prediction_set AS ENUM ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J');
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

-- Team H2H (Head-to-Head) statistics table
CREATE TABLE IF NOT EXISTS team_h2h_stats (
    id              SERIAL PRIMARY KEY,
    team_home_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    team_away_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    meetings        INTEGER NOT NULL DEFAULT 0,
    draws           INTEGER NOT NULL DEFAULT 0,
    home_draws      INTEGER NOT NULL DEFAULT 0,
    away_draws      INTEGER NOT NULL DEFAULT 0,
    draw_rate       DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    home_draw_rate  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    away_draw_rate  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    league_draw_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    h2h_draw_index  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    last_meeting_date DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_h2h_pair UNIQUE (team_home_id, team_away_id)
);

COMMENT ON TABLE team_h2h_stats IS 'Head-to-head statistics for team pairs, used for draw eligibility in ticket construction';
COMMENT ON COLUMN team_h2h_stats.h2h_draw_index IS 'Ratio of H2H draw rate to league draw rate (draw_rate / league_draw_rate)';
COMMENT ON COLUMN team_h2h_stats.meetings IS 'Total number of historical meetings between these teams';
COMMENT ON COLUMN team_h2h_stats.draws IS 'Total number of draws in H2H matches';
COMMENT ON COLUMN team_h2h_stats.home_draws IS 'Number of draws when team_home_id was at home';
COMMENT ON COLUMN team_h2h_stats.away_draws IS 'Number of draws when team_away_id was at home';

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
    
    -- Entropy and temperature metrics (for uncertainty monitoring)
    avg_entropy     DOUBLE PRECISION,                   -- Average normalized entropy (0-1)
    p10_entropy     DOUBLE PRECISION,                   -- 10th percentile of entropy distribution
    p90_entropy     DOUBLE PRECISION,                   -- 90th percentile of entropy distribution
    temperature     DOUBLE PRECISION,                   -- Learned temperature parameter for probability softening
    alpha_mean      DOUBLE PRECISION,                   -- Mean effective alpha used in entropy-weighted blending
    
    -- Diagnostics
    error_message   TEXT,
    logs            JSONB,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE training_runs IS 'Training job execution history with full audit trail';
COMMENT ON COLUMN training_runs.avg_entropy IS 'Average normalized entropy (0-1) of model predictions during training';
COMMENT ON COLUMN training_runs.p10_entropy IS '10th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.p90_entropy IS '90th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.temperature IS 'Learned temperature parameter for probability softening (typically 1.0-1.5)';
COMMENT ON COLUMN training_runs.alpha_mean IS 'Mean effective alpha used in entropy-weighted blending';

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
    
    -- Draw model components (for explainability and auditing)
    -- Stores JSON: {"poisson": 0.25, "dixon_coles": 0.27, "market": 0.26}
    draw_components JSONB,
    
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

COMMENT ON TABLE predictions IS 'Predicted probabilities for all sets (A-J)';
COMMENT ON COLUMN predictions.set_type IS 'Probability set identifier (A-J)';
COMMENT ON COLUMN predictions.entropy IS 'Prediction entropy for uncertainty quantification';
COMMENT ON COLUMN predictions.draw_components IS 'Draw probability components: {"poisson": 0.25, "dixon_coles": 0.27, "market": 0.26}';

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

-- Team H2H indexes
CREATE INDEX IF NOT EXISTS idx_h2h_pair ON team_h2h_stats(team_home_id, team_away_id);
CREATE INDEX IF NOT EXISTS idx_h2h_draw_index ON team_h2h_stats(h2h_draw_index);

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

-- Training runs indexes (entropy and temperature monitoring)
CREATE INDEX IF NOT EXISTS idx_training_runs_entropy ON training_runs(avg_entropy);
CREATE INDEX IF NOT EXISTS idx_training_runs_temperature ON training_runs(temperature);

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

-- Trigger for team_h2h_stats
DROP TRIGGER IF EXISTS update_team_h2h_stats_updated_at ON team_h2h_stats;
CREATE TRIGGER update_team_h2h_stats_updated_at
    BEFORE UPDATE ON team_h2h_stats
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
-- END OF SCHEMA
-- ============================================================================

-- ============================================================================
-- COMPLETE LEAGUES LIST - FOOTBALL-DATA.CO.UK
-- ============================================================================
-- 
-- This file contains ALL leagues available on football-data.co.uk
-- Run this AFTER the main schema to add all available leagues
-- 
-- League codes match football-data.co.uk format exactly
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- ALL AVAILABLE LEAGUES FROM FOOTBALL-DATA.CO.UK
-- ============================================================================

INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active) VALUES
    -- ========================================================================
    -- ENGLAND (E0-E3)
    -- ========================================================================
    ('E0', 'Premier League', 'England', 1, 0.26, 0.35, TRUE),
    ('E1', 'Championship', 'England', 2, 0.27, 0.33, TRUE),
    ('E2', 'League One', 'England', 3, 0.28, 0.32, TRUE),
    ('E3', 'League Two', 'England', 4, 0.29, 0.31, TRUE),
    
    -- ========================================================================
    -- SPAIN (SP1-SP2)
    -- ========================================================================
    ('SP1', 'La Liga', 'Spain', 1, 0.25, 0.30, TRUE),
    ('SP2', 'La Liga 2', 'Spain', 2, 0.26, 0.29, TRUE),
    
    -- ========================================================================
    -- GERMANY (D1-D2)
    -- ========================================================================
    ('D1', 'Bundesliga', 'Germany', 1, 0.24, 0.32, TRUE),
    ('D2', '2. Bundesliga', 'Germany', 2, 0.25, 0.31, TRUE),
    
    -- ========================================================================
    -- ITALY (I1-I2)
    -- ========================================================================
    ('I1', 'Serie A', 'Italy', 1, 0.27, 0.28, TRUE),
    ('I2', 'Serie B', 'Italy', 2, 0.28, 0.27, TRUE),
    
    -- ========================================================================
    -- FRANCE (F1-F2)
    -- ========================================================================
    ('F1', 'Ligue 1', 'France', 1, 0.26, 0.33, TRUE),
    ('F2', 'Ligue 2', 'France', 2, 0.27, 0.32, TRUE),
    
    -- ========================================================================
    -- NETHERLANDS (N1)
    -- ========================================================================
    ('N1', 'Eredivisie', 'Netherlands', 1, 0.25, 0.31, TRUE),
    
    -- ========================================================================
    -- PORTUGAL (P1)
    -- ========================================================================
    ('P1', 'Primeira Liga', 'Portugal', 1, 0.26, 0.34, TRUE),
    
    -- ========================================================================
    -- SCOTLAND (SC0-SC3)
    -- ========================================================================
    ('SC0', 'Scottish Premiership', 'Scotland', 1, 0.24, 0.36, TRUE),
    ('SC1', 'Scottish Championship', 'Scotland', 2, 0.25, 0.35, TRUE),
    ('SC2', 'Scottish League One', 'Scotland', 3, 0.26, 0.34, TRUE),
    ('SC3', 'Scottish League Two', 'Scotland', 4, 0.27, 0.33, TRUE),
    
    -- ========================================================================
    -- BELGIUM (B1)
    -- ========================================================================
    ('B1', 'Pro League', 'Belgium', 1, 0.25, 0.32, TRUE),
    
    -- ========================================================================
    -- TURKEY (T1)
    -- ========================================================================
    ('T1', 'Super Lig', 'Turkey', 1, 0.27, 0.37, TRUE),
    
    -- ========================================================================
    -- GREECE (G1)
    -- ========================================================================
    ('G1', 'Super League 1', 'Greece', 1, 0.28, 0.38, TRUE),
    
    -- ========================================================================
    -- AUSTRIA (A1)
    -- ========================================================================
    ('A1', 'Bundesliga', 'Austria', 1, 0.25, 0.33, TRUE),
    
    -- ========================================================================
    -- SWITZERLAND (SW1)
    -- ========================================================================
    ('SW1', 'Super League', 'Switzerland', 1, 0.26, 0.34, TRUE),
    
    -- ========================================================================
    -- DENMARK (DK1)
    -- ========================================================================
    ('DK1', 'Superliga', 'Denmark', 1, 0.25, 0.32, TRUE),
    
    -- ========================================================================
    -- SWEDEN (SWE1)
    -- ========================================================================
    ('SWE1', 'Allsvenskan', 'Sweden', 1, 0.24, 0.31, TRUE),
    
    -- ========================================================================
    -- NORWAY (N1 - Note: conflicts with Netherlands, using NO1)
    -- ========================================================================
    ('NO1', 'Eliteserien', 'Norway', 1, 0.24, 0.30, TRUE),
    
    -- ========================================================================
    -- FINLAND (FIN1)
    -- ========================================================================
    ('FIN1', 'Veikkausliiga', 'Finland', 1, 0.25, 0.29, TRUE),
    
    -- ========================================================================
    -- POLAND (PL1)
    -- ========================================================================
    ('PL1', 'Ekstraklasa', 'Poland', 1, 0.26, 0.33, TRUE),
    
    -- ========================================================================
    -- ROMANIA (RO1)
    -- ========================================================================
    ('RO1', 'Liga 1', 'Romania', 1, 0.27, 0.35, TRUE),
    
    -- ========================================================================
    -- RUSSIA (RUS1)
    -- ========================================================================
    ('RUS1', 'Premier League', 'Russia', 1, 0.26, 0.34, TRUE),
    
    -- ========================================================================
    -- CZECH REPUBLIC (CZE1)
    -- ========================================================================
    ('CZE1', 'First League', 'Czech Republic', 1, 0.25, 0.32, TRUE),
    
    -- ========================================================================
    -- CROATIA (CRO1)
    -- ========================================================================
    ('CRO1', 'Prva HNL', 'Croatia', 1, 0.26, 0.33, TRUE),
    
    -- ========================================================================
    -- SERBIA (SRB1)
    -- ========================================================================
    ('SRB1', 'SuperLiga', 'Serbia', 1, 0.27, 0.36, TRUE),
    
    -- ========================================================================
    -- UKRAINE (UKR1)
    -- ========================================================================
    ('UKR1', 'Premier League', 'Ukraine', 1, 0.25, 0.33, TRUE),
    
    -- ========================================================================
    -- IRELAND (IRL1)
    -- ========================================================================
    ('IRL1', 'Premier Division', 'Ireland', 1, 0.26, 0.32, TRUE),
    
    -- ========================================================================
    -- ARGENTINA (ARG1)
    -- ========================================================================
    ('ARG1', 'Primera Division', 'Argentina', 1, 0.23, 0.28, TRUE),
    
    -- ========================================================================
    -- BRAZIL (BRA1)
    -- ========================================================================
    ('BRA1', 'Serie A', 'Brazil', 1, 0.24, 0.27, TRUE),
    
    -- ========================================================================
    -- MEXICO (MEX1)
    -- ========================================================================
    ('MEX1', 'Liga MX', 'Mexico', 1, 0.25, 0.29, TRUE),
    
    -- ========================================================================
    -- USA (USA1)
    -- ========================================================================
    ('USA1', 'Major League Soccer', 'USA', 1, 0.22, 0.26, TRUE),
    
    -- ========================================================================
    -- CHINA (CHN1)
    -- ========================================================================
    ('CHN1', 'Super League', 'China', 1, 0.24, 0.28, TRUE),
    
    -- ========================================================================
    -- JAPAN (JPN1)
    -- ========================================================================
    ('JPN1', 'J-League', 'Japan', 1, 0.23, 0.27, TRUE),
    
    -- ========================================================================
    -- SOUTH KOREA (KOR1)
    -- ========================================================================
    ('KOR1', 'K League 1', 'South Korea', 1, 0.24, 0.28, TRUE),
    
    -- ========================================================================
    -- AUSTRALIA (AUS1)
    -- ========================================================================
    ('AUS1', 'A-League', 'Australia', 1, 0.23, 0.26, TRUE)

ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    tier = EXCLUDED.tier,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active,
    updated_at = now();

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Count total leagues
SELECT COUNT(*) as total_leagues FROM leagues WHERE is_active = TRUE;

-- List all leagues by country
SELECT country, COUNT(*) as league_count, 
       STRING_AGG(code || ' - ' || name, ', ' ORDER BY tier) as leagues
FROM leagues 
WHERE is_active = TRUE
GROUP BY country
ORDER BY country;

-- ============================================================================
-- END OF FILE
-- ============================================================================

-- Fix MatchResult Enum Type
-- The database has 'match_result' but SQLAlchemy expects 'matchresult'
-- This script creates the enum with the correct name

-- Check if matchresult enum exists, if not create it
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'matchresult') THEN
        CREATE TYPE matchresult AS ENUM ('H', 'D', 'A');
        RAISE NOTICE 'Created enum type matchresult';
    ELSE
        RAISE NOTICE 'Enum type matchresult already exists';
    END IF;
END $$;

-- If match_result exists but matchresult doesn't, we can migrate
-- But for now, just create matchresult to match SQLAlchemy's expectation

-- Migration: Add unique partial index for single active model per type
-- Purpose: Enforce single active model per model_type at database level
-- Date: 2025-01-01

-- Drop existing index if it exists
DROP INDEX IF EXISTS idx_models_active_per_type;

-- Create unique partial index
-- This ensures only one active model per model_type can exist
CREATE UNIQUE INDEX idx_models_active_per_type 
ON models (model_type) 
WHERE status = 'active';

-- Add comment
COMMENT ON INDEX idx_models_active_per_type IS 
'Ensures only one active model per model_type exists. Prevents multiple active models of the same type.';

-- Verify the index was created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE indexname = 'idx_models_active_per_type';


-- ============================================================================
-- SAVED JACKPOT TEMPLATES TABLE
-- ============================================================================
-- Allows users to save fixture lists with names and descriptions for reuse

CREATE TABLE IF NOT EXISTS saved_jackpot_templates (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR,                            -- User identifier (string for flexibility)
    name            VARCHAR NOT NULL,                   -- Template name
    description     TEXT,                               -- Optional description
    fixtures        JSONB NOT NULL,                     -- Array of fixtures with teams and odds
    fixture_count   INTEGER NOT NULL DEFAULT 0,         -- Number of fixtures
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_fixture_count CHECK (fixture_count >= 1 AND fixture_count <= 20)
);

CREATE INDEX idx_saved_templates_user ON saved_jackpot_templates(user_id);
CREATE INDEX idx_saved_templates_created ON saved_jackpot_templates(created_at DESC);

COMMENT ON TABLE saved_jackpot_templates IS 'Saved fixture lists for reuse';
COMMENT ON COLUMN saved_jackpot_templates.fixtures IS 'JSON array of fixtures: [{"homeTeam": "...", "awayTeam": "...", "homeOdds": 2.0, "drawOdds": 3.0, "awayOdds": 2.5}, ...]';
COMMENT ON COLUMN saved_jackpot_templates.fixture_count IS 'Number of fixtures in the template';



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

COMMIT;

-- ============================================================================
-- SCHEMA VALIDATION
-- ============================================================================
-- Note: Validation runs AFTER all tables are created (including saved_jackpot_templates
-- and saved_probability_results which are created later in the file)

-- Verify all tables created
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'leagues', 'teams', 'team_h2h_stats', 'matches', 'team_features', 'league_stats',
        'models', 'training_runs', 'users', 'jackpots', 'jackpot_fixtures',
        'predictions', 'validation_results', 'calibration_data',
        'data_sources', 'ingestion_logs', 'audit_entries',
        'saved_jackpot_templates', 'saved_probability_results'
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

-- ============================================================================
-- DRAW STRUCTURAL MODELING EXTENSIONS
-- ============================================================================
-- 
-- This migration adds tables for draw-first probability enhancement
-- using league priors, Elo symmetry, H2H, weather, fatigue, referee, and odds drift.
-- 
-- NON-DESTRUCTIVE: Only adds new tables, does not modify existing ones.
-- Safe to run in production.
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. LEAGUE-LEVEL DRAW PRIORS
-- ============================================================================
-- Stores historical draw rates per league/season for use as structural priors

CREATE TABLE IF NOT EXISTS league_draw_priors (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season          VARCHAR(20) NOT NULL,
    draw_rate       DOUBLE PRECISION NOT NULL CHECK (draw_rate BETWEEN 0 AND 1),
    sample_size     INTEGER NOT NULL CHECK (sample_size > 0),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_league_draw_prior UNIQUE (league_id, season)
);

CREATE INDEX idx_league_draw_priors_league ON league_draw_priors(league_id);
CREATE INDEX idx_league_draw_priors_season ON league_draw_priors(season);

COMMENT ON TABLE league_draw_priors IS 'Historical draw rates per league/season for structural draw modeling';
COMMENT ON COLUMN league_draw_priors.draw_rate IS 'Observed draw rate (0.0-1.0)';
COMMENT ON COLUMN league_draw_priors.sample_size IS 'Number of matches used to calculate draw_rate';

-- ============================================================================
-- 2. HEAD-TO-HEAD AGGREGATES (Enhanced - separate from team_h2h_stats)
-- ============================================================================
-- Stores H2H statistics specifically for draw modeling
-- Note: team_h2h_stats already exists, but this provides additional granularity

CREATE TABLE IF NOT EXISTS h2h_draw_stats (
    id              SERIAL PRIMARY KEY,
    team_home_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    team_away_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    matches_played  INTEGER NOT NULL DEFAULT 0 CHECK (matches_played >= 0),
    draw_count      INTEGER NOT NULL DEFAULT 0 CHECK (draw_count >= 0),
    avg_goals       DOUBLE PRECISION,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_h2h_draw_pair UNIQUE (team_home_id, team_away_id),
    CONSTRAINT chk_h2h_draw_count CHECK (draw_count <= matches_played)
);

CREATE INDEX idx_h2h_draw_pair ON h2h_draw_stats(team_home_id, team_away_id);
CREATE INDEX idx_h2h_draw_matches ON h2h_draw_stats(matches_played) WHERE matches_played >= 4;

COMMENT ON TABLE h2h_draw_stats IS 'Head-to-head statistics specifically for draw probability modeling';
COMMENT ON COLUMN h2h_draw_stats.matches_played IS 'Total historical meetings between these teams';
COMMENT ON COLUMN h2h_draw_stats.draw_count IS 'Number of draws in H2H matches';

-- ============================================================================
-- 3. TEAM ELO RATINGS
-- ============================================================================
-- Stores Elo ratings over time for symmetry-based draw adjustment

CREATE TABLE IF NOT EXISTS team_elo (
    id              SERIAL PRIMARY KEY,
    team_id         INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    elo_rating      DOUBLE PRECISION NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_team_elo_date UNIQUE (team_id, date)
);

CREATE INDEX idx_team_elo_team_date ON team_elo(team_id, date DESC);
CREATE INDEX idx_team_elo_date ON team_elo(date);

COMMENT ON TABLE team_elo IS 'Team Elo ratings over time for draw symmetry modeling';
COMMENT ON COLUMN team_elo.elo_rating IS 'Elo rating (typically 1000-2000 range)';

-- ============================================================================
-- 4. WEATHER SNAPSHOT PER FIXTURE
-- ============================================================================
-- Stores weather conditions at match time for draw probability adjustment

CREATE TABLE IF NOT EXISTS match_weather (
    id                  SERIAL PRIMARY KEY,
    fixture_id          INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    temperature          DOUBLE PRECISION,
    rainfall            DOUBLE PRECISION CHECK (rainfall >= 0),
    wind_speed          DOUBLE PRECISION CHECK (wind_speed >= 0),
    weather_draw_index  DOUBLE PRECISION,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match_weather_fixture UNIQUE (fixture_id)
);

CREATE INDEX idx_match_weather_fixture ON match_weather(fixture_id);
CREATE INDEX idx_match_weather_index ON match_weather(weather_draw_index);

COMMENT ON TABLE match_weather IS 'Weather conditions at match time for draw probability adjustment';
COMMENT ON COLUMN match_weather.weather_draw_index IS 'Computed draw adjustment factor from weather (0.95-1.10 typical)';

-- Historical weather table (for matches table, not fixtures)
CREATE TABLE IF NOT EXISTS match_weather_historical (
    id                  SERIAL PRIMARY KEY,
    match_id            BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    temperature         DOUBLE PRECISION,
    rainfall            DOUBLE PRECISION CHECK (rainfall >= 0),
    wind_speed          DOUBLE PRECISION CHECK (wind_speed >= 0),
    weather_draw_index  DOUBLE PRECISION,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_match_weather_historical_match UNIQUE (match_id)
);

CREATE INDEX idx_match_weather_historical_match ON match_weather_historical(match_id);

COMMENT ON TABLE match_weather_historical IS 'Weather conditions for historical matches (from matches table)';
COMMENT ON COLUMN match_weather_historical.weather_draw_index IS 'Computed draw adjustment factor from weather (0.95-1.10 typical)';

-- ============================================================================
-- 5. REFEREE BEHAVIORAL PROFILE
-- ============================================================================
-- Stores referee statistics for draw probability modeling

CREATE TABLE IF NOT EXISTS referee_stats (
    id              SERIAL PRIMARY KEY,
    referee_id      INTEGER NOT NULL UNIQUE,
    referee_name    VARCHAR(200),
    matches         INTEGER NOT NULL DEFAULT 0 CHECK (matches >= 0),
    avg_cards       DOUBLE PRECISION CHECK (avg_cards >= 0),
    avg_penalties   DOUBLE PRECISION CHECK (avg_penalties >= 0),
    draw_rate       DOUBLE PRECISION CHECK (draw_rate BETWEEN 0 AND 1),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_referee_stats_id ON referee_stats(referee_id);
CREATE INDEX idx_referee_stats_draw_rate ON referee_stats(draw_rate);

COMMENT ON TABLE referee_stats IS 'Referee behavioral statistics for draw probability adjustment';
COMMENT ON COLUMN referee_stats.avg_cards IS 'Average cards per match';
COMMENT ON COLUMN referee_stats.draw_rate IS 'Observed draw rate in matches officiated by this referee';

-- ============================================================================
-- 6. TEAM REST & CONGESTION
-- ============================================================================
-- Stores rest days and congestion data for fatigue-based draw adjustment

CREATE TABLE IF NOT EXISTS team_rest_days (
    id              SERIAL PRIMARY KEY,
    team_id         INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    fixture_id      INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    rest_days       INTEGER NOT NULL CHECK (rest_days >= 0),
    is_midweek      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_team_rest_fixture UNIQUE (team_id, fixture_id)
);

CREATE INDEX idx_team_rest_team ON team_rest_days(team_id);
CREATE INDEX idx_team_rest_fixture ON team_rest_days(fixture_id);
CREATE INDEX idx_team_rest_days ON team_rest_days(rest_days);

COMMENT ON TABLE team_rest_days IS 'Team rest days and congestion data for fatigue-based draw adjustment';
COMMENT ON COLUMN team_rest_days.rest_days IS 'Days of rest before this fixture';
COMMENT ON COLUMN team_rest_days.is_midweek IS 'Whether match is played midweek (Tue-Thu)';

-- Historical rest days table (for matches table, not fixtures)
CREATE TABLE IF NOT EXISTS team_rest_days_historical (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id         INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    rest_days       INTEGER NOT NULL CHECK (rest_days >= 0),
    is_midweek      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_team_rest_historical_match_team UNIQUE (match_id, team_id)
);

CREATE INDEX idx_team_rest_historical_match ON team_rest_days_historical(match_id);
CREATE INDEX idx_team_rest_historical_team ON team_rest_days_historical(team_id);
CREATE INDEX idx_team_rest_historical_days ON team_rest_days_historical(rest_days);

COMMENT ON TABLE team_rest_days_historical IS 'Team rest days for historical matches (from matches table)';
COMMENT ON COLUMN team_rest_days_historical.rest_days IS 'Days of rest before this match';
COMMENT ON COLUMN team_rest_days_historical.is_midweek IS 'Whether match is played midweek (Tue-Thu)';

-- ============================================================================
-- 7. ODDS MOVEMENT (DRAW FOCUS)
-- ============================================================================
-- Stores odds movement specifically for draw probability adjustment

CREATE TABLE IF NOT EXISTS odds_movement (
    id              SERIAL PRIMARY KEY,
    fixture_id      INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    draw_open       DOUBLE PRECISION CHECK (draw_open > 1.0),
    draw_close      DOUBLE PRECISION CHECK (draw_close > 1.0),
    draw_delta      DOUBLE PRECISION,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_odds_movement_fixture UNIQUE (fixture_id)
);

CREATE INDEX idx_odds_movement_fixture ON odds_movement(fixture_id);
CREATE INDEX idx_odds_movement_delta ON odds_movement(draw_delta);

COMMENT ON TABLE odds_movement IS 'Odds movement data for draw probability adjustment';
COMMENT ON COLUMN odds_movement.draw_delta IS 'Change in draw odds (close - open), positive = draw odds increased';

-- Historical odds movement table (for matches table, not fixtures)
CREATE TABLE IF NOT EXISTS odds_movement_historical (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    draw_open       DOUBLE PRECISION CHECK (draw_open > 1.0),
    draw_close      DOUBLE PRECISION CHECK (draw_close > 1.0),
    draw_delta      DOUBLE PRECISION,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_odds_movement_historical_match UNIQUE (match_id)
);

CREATE INDEX idx_odds_movement_historical_match ON odds_movement_historical(match_id);
CREATE INDEX idx_odds_movement_historical_delta ON odds_movement_historical(draw_delta);

COMMENT ON TABLE odds_movement_historical IS 'Odds movement data for historical matches (from matches table)';
COMMENT ON COLUMN odds_movement_historical.draw_delta IS 'Change in draw odds (close - open), positive = draw odds increased';

-- ============================================================================
-- 8. LEAGUE STRUCTURE METADATA
-- ============================================================================
-- Stores league structural information for draw probability modeling
-- Includes league size, relegation/promotion zones, etc.

CREATE TABLE IF NOT EXISTS league_structure (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season          VARCHAR(20) NOT NULL,
    total_teams     INTEGER NOT NULL CHECK (total_teams > 0),
    relegation_zones INTEGER NOT NULL DEFAULT 3 CHECK (relegation_zones >= 0),
    promotion_zones INTEGER NOT NULL DEFAULT 3 CHECK (promotion_zones >= 0),
    playoff_zones   INTEGER DEFAULT 0 CHECK (playoff_zones >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT uix_league_structure_season UNIQUE (league_id, season)
);

CREATE INDEX idx_league_structure_league ON league_structure(league_id);
CREATE INDEX idx_league_structure_season ON league_structure(season);

COMMENT ON TABLE league_structure IS 'League structural metadata for draw probability modeling';
COMMENT ON COLUMN league_structure.total_teams IS 'Total number of teams in the league';
COMMENT ON COLUMN league_structure.relegation_zones IS 'Number of teams that get relegated (affects late-season draw rates)';
COMMENT ON COLUMN league_structure.promotion_zones IS 'Number of teams that get promoted';
COMMENT ON COLUMN league_structure.playoff_zones IS 'Number of teams in playoff positions';

-- ============================================================================
-- 9. REFEREE ASSIGNMENT (Linking referees to fixtures)
-- ============================================================================
-- Links referees to specific fixtures (if not already in jackpot_fixtures)

-- Note: If referee_id is already in jackpot_fixtures, this table is optional
-- Adding it for completeness and flexibility

ALTER TABLE jackpot_fixtures 
ADD COLUMN IF NOT EXISTS referee_id INTEGER REFERENCES referee_stats(referee_id);

CREATE INDEX IF NOT EXISTS idx_jackpot_fixtures_referee ON jackpot_fixtures(referee_id);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all tables created
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'league_draw_priors', 'h2h_draw_stats', 'team_elo', 'match_weather',
        'match_weather_historical', 'referee_stats', 'team_rest_days',
        'team_rest_days_historical', 'odds_movement', 'odds_movement_historical',
        'league_structure'
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
        RAISE NOTICE 'All draw structural tables created successfully ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

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

-- Add constraint to ensure half-time scores are valid (drop first if exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_ht_goals_valid' 
        AND conrelid = 'matches'::regclass
    ) THEN
        ALTER TABLE matches DROP CONSTRAINT chk_ht_goals_valid;
    END IF;
END $$;

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

-- ============================================================================
-- ADDITIONAL MIGRATIONS - ENSURE ALL FEATURES ARE INCLUDED
-- ============================================================================
-- These migrations ensure all features from migration files are included
-- Safe to run multiple times (idempotent)

BEGIN;

-- ============================================================================
-- 1. ADD ENTROPY AND TEMPERATURE METRICS TO TRAINING_RUNS
-- ============================================================================
-- From: migrations/add_entropy_metrics.sql

ALTER TABLE training_runs
ADD COLUMN IF NOT EXISTS avg_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS p10_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS p90_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS alpha_mean DOUBLE PRECISION;

-- Create indexes for entropy monitoring queries
CREATE INDEX IF NOT EXISTS idx_training_runs_entropy 
ON training_runs (avg_entropy);

CREATE INDEX IF NOT EXISTS idx_training_runs_temperature 
ON training_runs (temperature);

-- Add comments for documentation
COMMENT ON COLUMN training_runs.avg_entropy IS 'Average normalized entropy (0-1) of model predictions during training';
COMMENT ON COLUMN training_runs.p10_entropy IS '10th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.p90_entropy IS '90th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.temperature IS 'Learned temperature parameter for probability softening (typically 1.0-1.5)';
COMMENT ON COLUMN training_runs.alpha_mean IS 'Mean effective alpha used in entropy-weighted blending';

-- ============================================================================
-- 2. ADD UNIQUE PARTIAL INDEX FOR MODELS
-- ============================================================================
-- From: migrations/add_unique_partial_index_models.sql
-- Ensures only one active model per model_type exists

DROP INDEX IF EXISTS idx_models_active_per_type;

CREATE UNIQUE INDEX idx_models_active_per_type 
ON models (model_type) 
WHERE status = 'active';

COMMENT ON INDEX idx_models_active_per_type IS 
'Ensures only one active model per model_type exists. Prevents multiple active models of the same type.';

-- ============================================================================
-- 3. ADD DRAW MODEL SUPPORT
-- ============================================================================
-- From: migrations/add_draw_model_support.sql
-- Enable model_type='draw' for dedicated draw probability models

DO $$
BEGIN
    -- Check if model_type column exists and is an enum
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'models'
        AND column_name = 'model_type'
        AND data_type = 'USER-DEFINED'
    ) THEN
        -- It's an enum, add 'draw' value if it doesn't exist
        IF NOT EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = (SELECT udt_name FROM information_schema.columns 
                              WHERE table_name = 'models' AND column_name = 'model_type')
            AND e.enumlabel = 'draw'
        ) THEN
            -- Get the enum type name
            DECLARE
                enum_type_name TEXT;
            BEGIN
                SELECT udt_name INTO enum_type_name
                FROM information_schema.columns
                WHERE table_name = 'models' AND column_name = 'model_type';
                
                EXECUTE format('ALTER TYPE %I ADD VALUE IF NOT EXISTS ''draw''', enum_type_name);
            END;
        END IF;
    END IF;
END
$$;

-- Create index for faster draw-model lookup
CREATE INDEX IF NOT EXISTS idx_models_draw_active
ON models (model_type, status)
WHERE model_type = 'draw' AND status = 'active';

-- Add comment explaining draw model type
COMMENT ON COLUMN models.model_type IS 
'Model type: poisson, blending, calibration, or draw. Draw models estimate P(Draw) only.';

-- ============================================================================
-- 4. ENSURE ALL LEAGUES ARE INCLUDED
-- ============================================================================
-- From: migrations/4_ALL_LEAGUES_FOOTBALL_DATA.sql
-- This ensures all leagues from football-data.co.uk are in the database

INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active) VALUES
    -- ENGLAND (E0-E3)
    ('E0', 'Premier League', 'England', 1, 0.26, 0.35, TRUE),
    ('E1', 'Championship', 'England', 2, 0.27, 0.33, TRUE),
    ('E2', 'League One', 'England', 3, 0.28, 0.32, TRUE),
    ('E3', 'League Two', 'England', 4, 0.29, 0.31, TRUE),
    
    -- SPAIN (SP1-SP2)
    ('SP1', 'La Liga', 'Spain', 1, 0.25, 0.30, TRUE),
    ('SP2', 'La Liga 2', 'Spain', 2, 0.26, 0.29, TRUE),
    
    -- GERMANY (D1-D2)
    ('D1', 'Bundesliga', 'Germany', 1, 0.24, 0.32, TRUE),
    ('D2', '2. Bundesliga', 'Germany', 2, 0.25, 0.31, TRUE),
    
    -- ITALY (I1-I2)
    ('I1', 'Serie A', 'Italy', 1, 0.27, 0.28, TRUE),
    ('I2', 'Serie B', 'Italy', 2, 0.28, 0.27, TRUE),
    
    -- FRANCE (F1-F2)
    ('F1', 'Ligue 1', 'France', 1, 0.26, 0.33, TRUE),
    ('F2', 'Ligue 2', 'France', 2, 0.27, 0.32, TRUE),
    
    -- NETHERLANDS (N1)
    ('N1', 'Eredivisie', 'Netherlands', 1, 0.25, 0.31, TRUE),
    
    -- PORTUGAL (P1)
    ('P1', 'Primeira Liga', 'Portugal', 1, 0.26, 0.34, TRUE),
    
    -- SCOTLAND (SC0-SC3)
    ('SC0', 'Scottish Premiership', 'Scotland', 1, 0.24, 0.36, TRUE),
    ('SC1', 'Scottish Championship', 'Scotland', 2, 0.25, 0.35, TRUE),
    ('SC2', 'Scottish League One', 'Scotland', 3, 0.26, 0.34, TRUE),
    ('SC3', 'Scottish League Two', 'Scotland', 4, 0.27, 0.33, TRUE),
    
    -- BELGIUM (B1)
    ('B1', 'Pro League', 'Belgium', 1, 0.25, 0.32, TRUE),
    
    -- TURKEY (T1)
    ('T1', 'Super Lig', 'Turkey', 1, 0.27, 0.37, TRUE),
    
    -- GREECE (G1)
    ('G1', 'Super League 1', 'Greece', 1, 0.28, 0.38, TRUE),
    
    -- AUSTRIA (A1)
    ('A1', 'Bundesliga', 'Austria', 1, 0.25, 0.33, TRUE),
    
    -- SWITZERLAND (SW1)
    ('SW1', 'Super League', 'Switzerland', 1, 0.26, 0.34, TRUE),
    
    -- DENMARK (DK1)
    ('DK1', 'Superliga', 'Denmark', 1, 0.25, 0.32, TRUE),
    
    -- SWEDEN (SWE1)
    ('SWE1', 'Allsvenskan', 'Sweden', 1, 0.24, 0.31, TRUE),
    
    -- NORWAY (NO1)
    ('NO1', 'Eliteserien', 'Norway', 1, 0.24, 0.30, TRUE),
    
    -- FINLAND (FIN1)
    ('FIN1', 'Veikkausliiga', 'Finland', 1, 0.25, 0.29, TRUE),
    
    -- POLAND (PL1)
    ('PL1', 'Ekstraklasa', 'Poland', 1, 0.26, 0.33, TRUE),
    
    -- ROMANIA (RO1)
    ('RO1', 'Liga 1', 'Romania', 1, 0.27, 0.35, TRUE),
    
    -- RUSSIA (RUS1)
    ('RUS1', 'Premier League', 'Russia', 1, 0.26, 0.34, TRUE),
    
    -- CZECH REPUBLIC (CZE1)
    ('CZE1', 'First League', 'Czech Republic', 1, 0.25, 0.32, TRUE),
    
    -- CROATIA (CRO1)
    ('CRO1', 'Prva HNL', 'Croatia', 1, 0.26, 0.33, TRUE),
    
    -- SERBIA (SRB1)
    ('SRB1', 'SuperLiga', 'Serbia', 1, 0.27, 0.36, TRUE),
    
    -- UKRAINE (UKR1)
    ('UKR1', 'Premier League', 'Ukraine', 1, 0.25, 0.33, TRUE),
    
    -- IRELAND (IRL1)
    ('IRL1', 'Premier Division', 'Ireland', 1, 0.26, 0.32, TRUE),
    
    -- ARGENTINA (ARG1)
    ('ARG1', 'Primera Division', 'Argentina', 1, 0.23, 0.28, TRUE),
    
    -- BRAZIL (BRA1)
    ('BRA1', 'Serie A', 'Brazil', 1, 0.24, 0.27, TRUE),
    
    -- MEXICO (MEX1)
    ('MEX1', 'Liga MX', 'Mexico', 1, 0.25, 0.29, TRUE),
    
    -- USA (USA1)
    ('USA1', 'Major League Soccer', 'USA', 1, 0.22, 0.26, TRUE),
    
    -- CHINA (CHN1)
    ('CHN1', 'Super League', 'China', 1, 0.24, 0.28, TRUE),
    
    -- JAPAN (JPN1)
    ('JPN1', 'J-League', 'Japan', 1, 0.23, 0.27, TRUE),
    
    -- SOUTH KOREA (KOR1)
    ('KOR1', 'K League 1', 'South Korea', 1, 0.24, 0.28, TRUE),
    
    -- AUSTRALIA (AUS1)
    ('AUS1', 'A-League', 'Australia', 1, 0.23, 0.26, TRUE)

ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    tier = EXCLUDED.tier,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active,
    updated_at = now();

-- ============================================================================
-- 5. VERIFY ALL INDEXES EXIST
-- ============================================================================
-- Ensure all critical indexes are created

-- GIN index for alternative_names (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_teams_alternative_names'
        AND schemaname = 'public'
    ) THEN
        CREATE INDEX idx_teams_alternative_names ON teams USING GIN(alternative_names);
        RAISE NOTICE 'Created GIN index idx_teams_alternative_names ✓';
    END IF;
END $$;

-- ============================================================================
-- 6. FINAL VERIFICATION
-- ============================================================================

-- Verify all critical tables exist
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
        'predictions', 'models', 'training_runs', 'league_draw_priors',
        'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
        'referee_stats', 'team_rest_days', 'team_rest_days_historical',
        'odds_movement', 'odds_movement_historical', 'league_structure',
        'match_xg', 'match_xg_historical', 'team_h2h_stats',
        'saved_jackpot_templates', 'saved_probability_results'
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
        RAISE WARNING 'Missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'All expected tables exist ✓';
    END IF;
END $$;

-- Verify entropy columns exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'training_runs' 
        AND column_name = 'avg_entropy'
        AND table_schema = 'public'
    ) THEN
        RAISE WARNING 'Missing column: training_runs.avg_entropy';
    ELSE
        RAISE NOTICE 'Entropy columns in training_runs exist ✓';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- END OF COMPLETE SCHEMA
-- ============================================================================
-- 
-- This schema file now includes:
-- - All base tables
-- - All draw structural extensions
-- - All historical tables
-- - All xG tables
-- - All migrations integrated
-- - All indexes and constraints
-- 
-- You can run this file directly on your existing database.
-- All statements are idempotent (safe to run multiple times).
-- 
-- ============================================================================

-- Add pipeline_metadata column to jackpots table
-- Stores pipeline execution results: data downloaded, model trained, etc.

ALTER TABLE jackpots 
ADD COLUMN IF NOT EXISTS pipeline_metadata JSONB DEFAULT NULL;

COMMENT ON COLUMN jackpots.pipeline_metadata IS 'Stores pipeline execution results including: data_downloaded, model_trained, teams_created, download_stats, training_stats, execution_timestamp';

-- Example structure:
-- {
--   "execution_timestamp": "2024-01-01T10:00:00Z",
--   "pipeline_run": true,
--   "teams_created": ["New Team"],
--   "data_downloaded": true,
--   "download_stats": {
--     "leagues_downloaded": ["E0"],
--     "total_matches": 1520,
--     "seasons": ["2324", "2223"]
--   },
--   "model_trained": true,
--   "training_stats": {
--     "model_id": 42,
--     "model_version": "poisson-20240101-100500",
--     "teams_trained": 580
--   },
--   "probabilities_calculated_with_new_data": true,
--   "status": "completed",
--   "errors": []
-- }

-- Migration: Add Team Form and Injuries Tables
-- Date: 2025-01-08
-- Description: Adds tables for tracking team form and injuries to improve probability calculations

-- Team Form Table
CREATE TABLE IF NOT EXISTS team_form (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    fixture_id INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    matches_played INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    goals_scored DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    goals_conceded DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    points INTEGER NOT NULL DEFAULT 0,
    form_rating DOUBLE PRECISION,  -- Normalized form rating (0.0-1.0)
    attack_form DOUBLE PRECISION,   -- Goals scored per match (normalized)
    defense_form DOUBLE PRECISION,  -- Goals conceded per match (normalized, inverted)
    last_match_date DATE,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_team_form_fixture UNIQUE (team_id, fixture_id)
);

CREATE INDEX IF NOT EXISTS idx_team_form_team ON team_form(team_id);
CREATE INDEX IF NOT EXISTS idx_team_form_fixture ON team_form(fixture_id);
CREATE INDEX IF NOT EXISTS idx_team_form_rating ON team_form(form_rating);

-- Team Injuries Table
CREATE TABLE IF NOT EXISTS team_injuries (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    fixture_id INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    key_players_missing INTEGER DEFAULT 0,
    injury_severity DOUBLE PRECISION,  -- Overall injury severity (0.0-1.0)
    attackers_missing INTEGER DEFAULT 0,
    midfielders_missing INTEGER DEFAULT 0,
    defenders_missing INTEGER DEFAULT 0,
    goalkeepers_missing INTEGER DEFAULT 0,
    notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_team_injuries_fixture UNIQUE (team_id, fixture_id)
);

CREATE INDEX IF NOT EXISTS idx_team_injuries_team ON team_injuries(team_id);
CREATE INDEX IF NOT EXISTS idx_team_injuries_fixture ON team_injuries(fixture_id);
CREATE INDEX IF NOT EXISTS idx_team_injuries_severity ON team_injuries(injury_severity);

-- Comments
COMMENT ON TABLE team_form IS 'Team form metrics calculated from recent matches (last 5 matches)';
COMMENT ON TABLE team_injuries IS 'Team injury data for fixtures, used to adjust team strengths';

COMMENT ON COLUMN team_form.form_rating IS 'Normalized form rating (0.0-1.0), where 1.0 = perfect form (3 points per match)';
COMMENT ON COLUMN team_form.attack_form IS 'Goals scored per match, normalized (0.0-1.0)';
COMMENT ON COLUMN team_form.defense_form IS 'Goals conceded per match, normalized and inverted (lower is better)';

COMMENT ON COLUMN team_injuries.injury_severity IS 'Overall injury severity (0.0-1.0), where 1.0 = critical players missing';
COMMENT ON COLUMN team_injuries.key_players_missing IS 'Number of key players missing due to injury';

