-- Migration: Add Team Form Historical Table
-- Date: 2025-01-09
-- Description: Adds table for storing team form data for historical matches (from matches table)

-- Team Form Historical Table (for historical matches)
CREATE TABLE IF NOT EXISTS team_form_historical (
    id SERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
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
    CONSTRAINT uix_team_form_historical_match_team UNIQUE (match_id, team_id)
);

CREATE INDEX IF NOT EXISTS idx_team_form_historical_match ON team_form_historical(match_id);
CREATE INDEX IF NOT EXISTS idx_team_form_historical_team ON team_form_historical(team_id);
CREATE INDEX IF NOT EXISTS idx_team_form_historical_rating ON team_form_historical(form_rating);
CREATE INDEX IF NOT EXISTS idx_team_form_historical_date ON team_form_historical(last_match_date);

-- Comments
COMMENT ON TABLE team_form_historical IS 'Team form metrics for historical matches (from matches table)';
COMMENT ON COLUMN team_form_historical.form_rating IS 'Normalized form rating (0.0-1.0), where 1.0 = perfect form (3 points per match)';
COMMENT ON COLUMN team_form_historical.attack_form IS 'Goals scored per match, normalized (0.0-1.0)';
COMMENT ON COLUMN team_form_historical.defense_form IS 'Goals conceded per match, normalized and inverted (lower is better)';

