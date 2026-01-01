-- Add H2H (Head-to-Head) statistics table for draw eligibility
CREATE TABLE IF NOT EXISTS team_h2h_stats (
    id SERIAL PRIMARY KEY,
    team_home_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    team_away_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    meetings INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    home_draws INTEGER NOT NULL DEFAULT 0,
    away_draws INTEGER NOT NULL DEFAULT 0,
    draw_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    home_draw_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    away_draw_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    league_draw_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    h2h_draw_index DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    last_meeting_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uniq_h2h_pair UNIQUE (team_home_id, team_away_id)
);

CREATE INDEX IF NOT EXISTS idx_h2h_pair ON team_h2h_stats (team_home_id, team_away_id);
CREATE INDEX IF NOT EXISTS idx_h2h_draw_index ON team_h2h_stats (h2h_draw_index);

COMMENT ON TABLE team_h2h_stats IS 'Head-to-head statistics for team pairs, used for draw eligibility in ticket construction';
COMMENT ON COLUMN team_h2h_stats.h2h_draw_index IS 'Ratio of H2H draw rate to league draw rate (draw_rate / league_draw_rate)';
COMMENT ON COLUMN team_h2h_stats.meetings IS 'Total number of historical meetings between these teams';
COMMENT ON COLUMN team_h2h_stats.draws IS 'Total number of draws in H2H matches';
COMMENT ON COLUMN team_h2h_stats.home_draws IS 'Number of draws when team_home_id was at home';
COMMENT ON COLUMN team_h2h_stats.away_draws IS 'Number of draws when team_away_id was at home';

