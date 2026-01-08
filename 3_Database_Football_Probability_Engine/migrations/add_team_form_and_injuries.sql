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

