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
    
    CONSTRAINT chk_fixture_count CHECK (fixture_count >= 1 AND fixture_count <= 200)
);

CREATE INDEX idx_saved_templates_user ON saved_jackpot_templates(user_id);
CREATE INDEX idx_saved_templates_created ON saved_jackpot_templates(created_at DESC);

COMMENT ON TABLE saved_jackpot_templates IS 'Saved fixture lists for reuse';
COMMENT ON COLUMN saved_jackpot_templates.fixtures IS 'JSON array of fixtures: [{"homeTeam": "...", "awayTeam": "...", "homeOdds": 2.0, "drawOdds": 3.0, "awayOdds": 2.5}, ...]';
COMMENT ON COLUMN saved_jackpot_templates.fixture_count IS 'Number of fixtures in the template';

