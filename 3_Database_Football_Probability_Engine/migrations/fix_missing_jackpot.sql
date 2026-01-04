-- ============================================================================
-- Fix Missing Jackpot: JK-2024-1236
-- ============================================================================
-- This script helps diagnose and fix the issue where saved_probability_results
-- references a jackpot_id that doesn't exist in the jackpots table.
--
-- Problem: Frontend is trying to access JK-2024-1236 but it doesn't exist
-- Solution: Find the correct jackpot ID or create a mapping
-- ============================================================================

-- ============================================================================
-- STEP 1: Check if JK-2024-1236 exists in saved_probability_results
-- ============================================================================
SELECT 
    id,
    jackpot_id,
    name,
    total_fixtures,
    created_at,
    actual_results
FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236';

-- ============================================================================
-- STEP 2: Check if any jackpot exists with similar ID or recent creation
-- ============================================================================
SELECT 
    id,
    jackpot_id,
    name,
    created_at,
    (SELECT COUNT(*) FROM jackpot_fixtures WHERE jackpot_id = jackpots.id) as fixture_count
FROM jackpots
WHERE jackpot_id LIKE 'JK-%'
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================================
-- STEP 3: Find saved_probability_results that reference non-existent jackpots
-- ============================================================================
SELECT 
    spr.id,
    spr.jackpot_id,
    spr.name,
    spr.total_fixtures,
    spr.created_at,
    CASE 
        WHEN j.id IS NULL THEN 'MISSING'
        ELSE 'EXISTS'
    END as jackpot_status
FROM saved_probability_results spr
LEFT JOIN jackpots j ON spr.jackpot_id = j.jackpot_id
WHERE j.id IS NULL
ORDER BY spr.created_at DESC;

-- ============================================================================
-- STEP 4: Option A - Create missing jackpot from saved_probability_results
-- ============================================================================
-- This creates a jackpot entry for JK-2024-1236 based on saved_probability_results
-- Note: This creates a jackpot WITHOUT fixtures. You'll need to add fixtures separately.

DO $$
DECLARE
    saved_result RECORD;
    new_jackpot_id VARCHAR := 'JK-2024-1236';
    new_jackpot_record_id INTEGER;
BEGIN
    -- Get the saved result
    SELECT * INTO saved_result
    FROM saved_probability_results
    WHERE jackpot_id = new_jackpot_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- If saved result exists and jackpot doesn't exist, create it
    IF saved_result.id IS NOT NULL THEN
        -- Check if jackpot already exists
        IF NOT EXISTS (SELECT 1 FROM jackpots WHERE jackpot_id = new_jackpot_id) THEN
            -- Create jackpot entry
            INSERT INTO jackpots (jackpot_id, user_id, name, status, model_version, created_at, updated_at)
            VALUES (
                new_jackpot_id,
                saved_result.user_id,
                saved_result.name,
                'draft',
                saved_result.model_version,
                saved_result.created_at,
                NOW()
            )
            RETURNING id INTO new_jackpot_record_id;
            
            RAISE NOTICE 'Created jackpot % with ID %', new_jackpot_id, new_jackpot_record_id;
            
            -- Note: You'll need to manually add fixtures for this jackpot
            -- The fixtures should match the actual_results in saved_probability_results
            RAISE NOTICE 'WARNING: You need to add fixtures for this jackpot manually!';
            RAISE NOTICE 'Check saved_probability_results.actual_results for match numbers';
        ELSE
            RAISE NOTICE 'Jackpot % already exists', new_jackpot_id;
        END IF;
    ELSE
        RAISE NOTICE 'No saved_probability_results found for jackpot_id %', new_jackpot_id;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Option B - Update saved_probability_results to use correct jackpot_id
-- ============================================================================
-- If you found the correct jackpot_id in STEP 2, update saved_probability_results
-- Replace 'JK-CORRECT-ID' with the actual correct jackpot_id

-- UPDATE saved_probability_results
-- SET jackpot_id = 'JK-CORRECT-ID'  -- Replace with actual correct ID
-- WHERE jackpot_id = 'JK-2024-1236';

-- ============================================================================
-- STEP 6: Verify the fix
-- ============================================================================
SELECT 
    spr.id,
    spr.jackpot_id,
    spr.name,
    j.id as jackpot_db_id,
    j.jackpot_id as jackpot_db_jackpot_id,
    CASE 
        WHEN j.id IS NULL THEN 'STILL MISSING'
        ELSE 'FIXED'
    END as status
FROM saved_probability_results spr
LEFT JOIN jackpots j ON spr.jackpot_id = j.jackpot_id
WHERE spr.jackpot_id = 'JK-2024-1236';

-- ============================================================================
-- STEP 7: Find all jackpots that need fixtures
-- ============================================================================
-- This shows jackpots that exist but have no fixtures
SELECT 
    j.id,
    j.jackpot_id,
    j.name,
    j.created_at,
    COUNT(jf.id) as fixture_count
FROM jackpots j
LEFT JOIN jackpot_fixtures jf ON j.id = jf.jackpot_id
WHERE j.jackpot_id = 'JK-2024-1236'
GROUP BY j.id, j.jackpot_id, j.name, j.created_at;

-- ============================================================================
-- NOTES:
-- ============================================================================
-- 1. If the jackpot was created during import, it should have fixtures
-- 2. If fixtures are missing, you may need to recreate them from actual_results
-- 3. The actual_results JSONB contains match numbers -> results mapping
-- 4. You'll need team names from somewhere (maybe from the original import CSV)
--
-- To add fixtures manually:
-- INSERT INTO jackpot_fixtures (jackpot_id, match_order, home_team, away_team, odds_home, odds_draw, odds_away)
-- VALUES (
--     (SELECT id FROM jackpots WHERE jackpot_id = 'JK-2024-1236'),
--     1,  -- match_order
--     'Home Team Name',
--     'Away Team Name',
--     2.0,  -- odds_home
--     3.0,  -- odds_draw
--     2.5   -- odds_away
-- );
-- ============================================================================

