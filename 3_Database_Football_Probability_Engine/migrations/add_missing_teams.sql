-- Migration: Add Missing Teams to Database
-- This script adds teams that frequently appear in jackpots but are missing from the database
-- Run this script directly in your PostgreSQL database

-- First, ensure leagues exist (create if they don't)
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
VALUES 
    ('ALLSVENSKAN', 'Allsvenskan', 'Sweden', 1, 0.26, 0.35, TRUE),
    ('EREDIVISIE', 'Eredivisie', 'Netherlands', 1, 0.26, 0.35, TRUE),
    ('EERSTEDIV', 'Eerste Divisie', 'Netherlands', 2, 0.26, 0.35, TRUE),
    ('LALIGA', 'La Liga', 'Spain', 1, 0.26, 0.35, TRUE),
    ('AUTBUND', 'Austrian Bundesliga', 'Austria', 1, 0.26, 0.35, TRUE),
    ('RUSPL', 'Russian Premier League', 'Russia', 1, 0.26, 0.35, TRUE),
    ('BUNDESLIGA', 'Bundesliga', 'Germany', 1, 0.26, 0.35, TRUE),
    ('EPL', 'Premier League', 'England', 1, 0.26, 0.35, TRUE)
ON CONFLICT (code) DO NOTHING;

-- Add teams (using canonical_name normalization - matches Python normalize_team_name function)
-- Note: canonical_name should be lowercase, with special chars removed, matching the resolver logic
-- Swedish Allsvenskan
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Norrkoping FK', 'norrkoping fk', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'ALLSVENSKAN'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'IK Sirius', 'ik sirius', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'ALLSVENSKAN'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Dutch Eredivisie / Eerste Divisie
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Excelsior Rotterdam', 'excelsior rotterdam', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Heracles Almelo', 'heracles almelo', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'NAC Breda', 'nac breda', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EERSTEDIV'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Go Ahead Eagles', 'go ahead eagles', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'SC Telstar', 'sc telstar', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EERSTEDIV'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'FC Groningen', 'fc groningen', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'FC Twente', 'fc twente', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'PEC Zwolle', 'pec zwolle', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EREDIVISIE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Spanish La Liga
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Celta Vigo', 'celta vigo', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Levante', 'levante', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Alaves', 'alaves', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Espanyol', 'espanyol', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Real Sociedad', 'real sociedad', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Athletic Bilbao', 'athletic bilbao', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'LALIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Austrian Bundesliga
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'SK Rapid', 'sk rapid', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'AUTBUND'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'SK Sturm Graz', 'sk sturm graz', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'AUTBUND'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Russian Premier League
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'FK Krasnodar', 'fk krasnodar', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'RUSPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'FK Spartak Moscow', 'fk spartak moscow', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'RUSPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- German Bundesliga (common teams that might be missing)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Union Berlin', 'union berlin', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Freiburg', 'freiburg', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Leipzig', 'leipzig', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Stuttgart', 'stuttgart', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Wolfsburg', 'wolfsburg', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Hoffenheim', 'hoffenheim', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'BUNDESLIGA'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- English Premier League
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Nottingham', 'nottingham', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Man Utd', 'man utd', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Tottenham', 'tottenham', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Chelsea', 'chelsea', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'EPL'
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Summary
SELECT 
    'Migration complete' as status,
    COUNT(*) FILTER (WHERE name IN ('Norrkoping FK', 'IK Sirius', 'Excelsior Rotterdam', 'Heracles Almelo', 'Celta Vigo', 'SK Rapid', 'SK Sturm Graz', 'FK Krasnodar', 'FK Spartak Moscow')) as missing_teams_added
FROM teams;

