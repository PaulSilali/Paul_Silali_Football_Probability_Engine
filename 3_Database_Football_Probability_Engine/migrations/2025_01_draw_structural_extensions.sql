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

-- ============================================================================
-- 8. REFEREE ASSIGNMENT (Linking referees to fixtures)
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
        'referee_stats', 'team_rest_days', 'odds_movement'
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

