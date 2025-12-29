-- ============================================================================
-- FOOTBALL JACKPOT PROBABILITY ENGINE - SEED DATA
-- ============================================================================
-- 
-- Initial data for development and testing
-- Run AFTER database_schema.sql
-- 
-- ============================================================================

BEGIN;

-- ============================================================================
-- LEAGUES
-- ============================================================================

INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active) VALUES
    -- Top 5 European Leagues
    ('E0', 'Premier League', 'England', 1, 0.26, 0.35, TRUE),
    ('E1', 'Championship', 'England', 2, 0.27, 0.33, TRUE),
    ('SP1', 'La Liga', 'Spain', 1, 0.25, 0.30, TRUE),
    ('D1', 'Bundesliga', 'Germany', 1, 0.24, 0.32, TRUE),
    ('I1', 'Serie A', 'Italy', 1, 0.27, 0.28, TRUE),
    ('F1', 'Ligue 1', 'France', 1, 0.26, 0.33, TRUE),
    
    -- Additional European Leagues
    ('N1', 'Eredivisie', 'Netherlands', 1, 0.25, 0.31, TRUE),
    ('P1', 'Primeira Liga', 'Portugal', 1, 0.26, 0.34, TRUE),
    ('SC0', 'Scottish Premiership', 'Scotland', 1, 0.24, 0.36, TRUE),
    ('T1', 'Super Lig', 'Turkey', 1, 0.27, 0.37, TRUE),
    ('G1', 'Super League 1', 'Greece', 1, 0.28, 0.38, TRUE),
    ('B1', 'Pro League', 'Belgium', 1, 0.25, 0.32, TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active;

-- ============================================================================
-- TEAMS (PREMIER LEAGUE SAMPLE)
-- ============================================================================

-- Get Premier League ID
DO $$
DECLARE
    premier_league_id INTEGER;
BEGIN
    SELECT id INTO premier_league_id FROM leagues WHERE code = 'E0';
    
    -- Insert Premier League teams
    INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating) VALUES
        (premier_league_id, 'Arsenal', 'arsenal', 1.15, 0.92),
        (premier_league_id, 'Aston Villa', 'aston villa', 1.02, 1.01),
        (premier_league_id, 'Bournemouth', 'bournemouth', 0.93, 1.08),
        (premier_league_id, 'Brentford', 'brentford', 0.98, 1.04),
        (premier_league_id, 'Brighton', 'brighton', 1.05, 0.98),
        (premier_league_id, 'Chelsea', 'chelsea', 1.08, 0.96),
        (premier_league_id, 'Crystal Palace', 'crystal palace', 0.94, 1.03),
        (premier_league_id, 'Everton', 'everton', 0.89, 1.11),
        (premier_league_id, 'Fulham', 'fulham', 0.96, 1.05),
        (premier_league_id, 'Liverpool', 'liverpool', 1.18, 0.88),
        (premier_league_id, 'Luton', 'luton', 0.85, 1.15),
        (premier_league_id, 'Manchester City', 'manchester city', 1.22, 0.85),
        (premier_league_id, 'Manchester United', 'manchester united', 1.06, 1.02),
        (premier_league_id, 'Newcastle', 'newcastle', 1.10, 0.94),
        (premier_league_id, 'Nottingham Forest', 'nottingham forest', 0.91, 1.09),
        (premier_league_id, 'Sheffield United', 'sheffield united', 0.82, 1.18),
        (premier_league_id, 'Tottenham', 'tottenham', 1.12, 0.97),
        (premier_league_id, 'West Ham', 'west ham', 0.97, 1.06),
        (premier_league_id, 'Wolves', 'wolves', 0.92, 1.07),
        (premier_league_id, 'Burnley', 'burnley', 0.88, 1.12)
    ON CONFLICT (league_id, canonical_name) DO UPDATE SET
        name = EXCLUDED.name,
        attack_rating = EXCLUDED.attack_rating,
        defense_rating = EXCLUDED.defense_rating;
END $$;

-- ============================================================================
-- TEAMS (LA LIGA SAMPLE)
-- ============================================================================

DO $$
DECLARE
    la_liga_id INTEGER;
BEGIN
    SELECT id INTO la_liga_id FROM leagues WHERE code = 'SP1';
    
    INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating) VALUES
        (la_liga_id, 'Real Madrid', 'real madrid', 1.20, 0.87),
        (la_liga_id, 'Barcelona', 'barcelona', 1.17, 0.90),
        (la_liga_id, 'Atletico Madrid', 'atletico madrid', 1.10, 0.88),
        (la_liga_id, 'Sevilla', 'sevilla', 1.02, 0.98),
        (la_liga_id, 'Real Sociedad', 'real sociedad', 1.05, 0.96),
        (la_liga_id, 'Real Betis', 'real betis', 1.01, 1.00),
        (la_liga_id, 'Villarreal', 'villarreal', 1.03, 0.97),
        (la_liga_id, 'Athletic Bilbao', 'athletic bilbao', 0.99, 1.01),
        (la_liga_id, 'Valencia', 'valencia', 0.96, 1.04),
        (la_liga_id, 'Girona', 'girona', 1.08, 0.95)
    ON CONFLICT (league_id, canonical_name) DO NOTHING;
END $$;

-- ============================================================================
-- DATA SOURCES
-- ============================================================================

INSERT INTO data_sources (name, source_type, status, config) VALUES
    (
        'Football-Data.co.uk',
        'football-data',
        'fresh',
        '{"base_url": "https://www.football-data.co.uk", "format": "csv"}'::jsonb
    ),
    (
        'API-Football',
        'api-football',
        'fresh',
        '{"base_url": "https://v3.football.api-sports.io", "requires_key": true}'::jsonb
    )
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- INITIAL MODEL (PLACEHOLDER)
-- ============================================================================

-- Insert a placeholder model for development
INSERT INTO models (
    version,
    model_type,
    status,
    training_completed_at,
    training_matches,
    training_leagues,
    training_seasons,
    decay_rate,
    blend_alpha,
    brier_score,
    log_loss,
    model_weights
) VALUES (
    'v1.0.0-dev',
    'dixon-coles',
    'active',
    now(),
    5000,
    ARRAY['E0', 'SP1', 'D1', 'I1', 'F1'],
    ARRAY['2020-21', '2021-22', '2022-23', '2023-24'],
    0.0065,  -- xi (time decay)
    0.6,     -- alpha (model weight in blending)
    0.187,   -- Brier score
    0.523,   -- Log loss
    '{
        "rho": -0.13,
        "xi": 0.0065,
        "home_advantage": 0.35,
        "team_strengths": {},
        "calibration_curves": {
            "H": {"bins": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "frequencies": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0]},
            "D": {"bins": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "frequencies": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0]},
            "A": {"bins": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "frequencies": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0]}
        }
    }'::jsonb
)
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Display summary of seeded data
DO $$
DECLARE
    league_count INTEGER;
    team_count INTEGER;
    source_count INTEGER;
    model_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO league_count FROM leagues;
    SELECT COUNT(*) INTO team_count FROM teams;
    SELECT COUNT(*) INTO source_count FROM data_sources;
    SELECT COUNT(*) INTO model_count FROM models;
    
    RAISE NOTICE '===================================';
    RAISE NOTICE 'SEED DATA SUMMARY';
    RAISE NOTICE '===================================';
    RAISE NOTICE 'Leagues seeded: %', league_count;
    RAISE NOTICE 'Teams seeded: %', team_count;
    RAISE NOTICE 'Data sources: %', source_count;
    RAISE NOTICE 'Models: %', model_count;
    RAISE NOTICE '===================================';
END $$;

-- Display league breakdown
SELECT 
    l.code,
    l.name,
    l.country,
    COUNT(t.id) as team_count,
    l.home_advantage
FROM leagues l
LEFT JOIN teams t ON t.league_id = l.id
WHERE l.is_active = TRUE
GROUP BY l.id, l.code, l.name, l.country, l.home_advantage
ORDER BY team_count DESC, l.name;

-- ============================================================================
-- END OF SEED DATA
-- ============================================================================
