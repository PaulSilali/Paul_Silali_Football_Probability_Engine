-- ============================================================================
-- Add 4 Missing Teams from Jackpot Input
-- ============================================================================
-- This script adds teams that were flagged as "not found" during jackpot input
-- 
-- Teams to add:
-- 1. SC Sao Joao de Ver (Portuguese lower league)
-- 2. Amarante FC (Portuguese lower league)
-- 3. Hellas Verona (Italian Serie A)
-- 4. CD Leganes (Spanish La Liga 2)
--
-- Run this script in your PostgreSQL database:
-- psql -U your_user -d your_database -f add_4_missing_teams.sql
-- Or in psql: \i add_4_missing_teams.sql
-- ============================================================================

-- ============================================================================
-- 1. SC Sao Joao de Ver (Portuguese Liga 3 or lower)
-- ============================================================================
-- Canonical name: "sc sao joao de ver" (normalize_team_name keeps "sc" prefix)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'SC Sao Joao de Ver', 'sc sao joao de ver', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'P1'  -- Primeira Liga (Portugal)
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- If team wasn't added above, try with a more specific league
-- You may need to create a Portuguese Liga 3 league first if it doesn't exist
DO $$
DECLARE
    portugal_league_id INTEGER;
BEGIN
    -- Try to find Portuguese league
    SELECT id INTO portugal_league_id 
    FROM leagues 
    WHERE code = 'P1' OR code = 'PORTUGAL_LEAGUE' OR name ILIKE '%portugal%'
    LIMIT 1;
    
    -- If no league found, create a placeholder (adjust as needed)
    IF portugal_league_id IS NULL THEN
        INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
        VALUES ('P3', 'Liga 3', 'Portugal', 3, 0.26, 0.35, TRUE)
        ON CONFLICT (code) DO NOTHING
        RETURNING id INTO portugal_league_id;
        
        SELECT id INTO portugal_league_id FROM leagues WHERE code = 'P3';
    END IF;
    
    -- Add team (canonical name matches normalize_team_name output)
    INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
    VALUES (portugal_league_id, 'SC Sao Joao de Ver', 'sc sao joao de ver', 1.0, 1.0, 0.0)
    ON CONFLICT (canonical_name, league_id) DO NOTHING;
END $$;

-- ============================================================================
-- 2. Amarante FC (Portuguese Liga 3 or lower)
-- ============================================================================
-- Canonical name: "amarante" (normalize_team_name removes " fc" suffix)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Amarante FC', 'amarante', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'P1'  -- Primeira Liga (Portugal)
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- If team wasn't added above, use the same logic as SC Sao Joao de Ver
DO $$
DECLARE
    portugal_league_id INTEGER;
BEGIN
    SELECT id INTO portugal_league_id 
    FROM leagues 
    WHERE code = 'P1' OR code = 'P3' OR code = 'PORTUGAL_LEAGUE' OR name ILIKE '%portugal%'
    LIMIT 1;
    
    IF portugal_league_id IS NULL THEN
        INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
        VALUES ('P3', 'Liga 3', 'Portugal', 3, 0.26, 0.35, TRUE)
        ON CONFLICT (code) DO NOTHING
        RETURNING id INTO portugal_league_id;
        
        SELECT id INTO portugal_league_id FROM leagues WHERE code = 'P3';
    END IF;
    
    INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
    VALUES (portugal_league_id, 'Amarante FC', 'amarante', 1.0, 1.0, 0.0)
    ON CONFLICT (canonical_name, league_id) DO NOTHING;
END $$;

-- ============================================================================
-- 3. Hellas Verona (Italian Serie A - I1)
-- ============================================================================
-- Canonical name: "hellas verona" (no suffix to remove)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Hellas Verona', 'hellas verona', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'I1'  -- Serie A (Italy)
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Alternative: Try with FC suffix (canonical will be same: "hellas verona")
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Hellas Verona FC', 'hellas verona', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'I1'
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- ============================================================================
-- 4. CD Leganes (Spanish La Liga 2 - SP2)
-- ============================================================================
-- Canonical name: "cd leganes" (CD is not a common suffix, so it stays)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'CD Leganes', 'cd leganes', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'SP2'  -- La Liga 2 (Spain)
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- Alternative: Try without CD prefix (canonical will be "leganes")
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Leganes', 'leganes', 1.0, 1.0, 0.0
FROM leagues 
WHERE code = 'SP2'
LIMIT 1
ON CONFLICT (canonical_name, league_id) DO NOTHING;

-- ============================================================================
-- Verification: Check if teams were added successfully
-- ============================================================================
SELECT 
    t.name,
    t.canonical_name,
    l.code as league_code,
    l.name as league_name,
    t.attack_rating,
    t.defense_rating
FROM teams t
JOIN leagues l ON t.league_id = l.id
WHERE t.canonical_name IN (
    'sc sao joao de ver',
    'amarante',
    'hellas verona',
    'cd leganes',
    'leganes'
)
ORDER BY t.name;

-- ============================================================================
-- Expected Output:
-- ============================================================================
-- If successful, you should see 4-6 rows (some teams may have multiple entries
-- if alternative names were added). The important thing is that at least one
-- entry exists for each of the 4 teams.
--
-- After adding teams:
-- 1. Go back to Jackpot Input page
-- 2. Click "Validate All Teams" button
-- 3. Teams should now show green checkmarks ✅
-- 4. You can proceed with probability calculation
-- ============================================================================

