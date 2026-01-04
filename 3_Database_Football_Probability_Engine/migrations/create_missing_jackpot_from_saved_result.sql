-- ============================================================================
-- Create Missing Jackpot from Saved Result: JK-2024-1236
-- ============================================================================
-- This script creates a jackpot entry for JK-2024-1236 based on the
-- saved_probability_results data.
--
-- WARNING: This creates a jackpot WITHOUT fixtures because team names
-- are not stored in saved_probability_results. You'll need to manually
-- add fixtures or re-import the jackpot results.
-- ============================================================================

-- Step 1: Check if saved result exists
SELECT 
    id,
    jackpot_id,
    name,
    total_fixtures,
    actual_results,
    created_at
FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236';

-- Step 2: Create missing jackpot entry
DO $$
DECLARE
    saved_result RECORD;
    new_jackpot_id VARCHAR := 'JK-2024-1236';
    new_jackpot_record_id INTEGER;
    fixture_count INTEGER;
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
            -- Get fixture count from actual_results
            fixture_count := saved_result.total_fixtures;
            IF fixture_count IS NULL OR fixture_count = 0 THEN
                -- Try to count from actual_results JSONB
                SELECT jsonb_object_keys(saved_result.actual_results) INTO fixture_count;
                IF fixture_count IS NULL THEN
                    fixture_count := 15; -- Default to 15 fixtures
                END IF;
            END IF;
            
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
            RAISE NOTICE 'Fixture count: %', fixture_count;
            RAISE NOTICE '';
            RAISE NOTICE 'WARNING: You need to add fixtures for this jackpot manually!';
            RAISE NOTICE 'Team names are not stored in saved_probability_results, so fixtures cannot be auto-created.';
            RAISE NOTICE '';
            RAISE NOTICE 'To add fixtures, use:';
            RAISE NOTICE 'INSERT INTO jackpot_fixtures (jackpot_id, match_order, home_team, away_team, odds_home, odds_draw, odds_away)';
            RAISE NOTICE 'VALUES ((SELECT id FROM jackpots WHERE jackpot_id = ''%''), 1, ''Home Team Name'', ''Away Team Name'', 2.0, 3.0, 2.5);', new_jackpot_id;
        ELSE
            RAISE NOTICE 'Jackpot % already exists', new_jackpot_id;
        END IF;
    ELSE
        RAISE NOTICE 'No saved_probability_results found for jackpot_id %', new_jackpot_id;
    END IF;
END $$;

-- Step 3: Verify the jackpot was created
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

-- Step 4: Show actual results for reference (to help recreate fixtures)
SELECT 
    jsonb_object_keys(actual_results) as match_number,
    actual_results->jsonb_object_keys(actual_results) as result
FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236'
ORDER BY jsonb_object_keys(actual_results)::int;

-- ============================================================================
-- NOTES:
-- ============================================================================
-- 1. This script creates the jackpot entry but NOT the fixtures
-- 2. You need to manually add fixtures with correct team names
-- 3. The actual_results JSONB shows match numbers and results:
--    - Match numbers: 1, 2, 3, ...
--    - Results: "1" (home win), "X" (draw), "2" (away win)
-- 4. To get team names, you may need to:
--    - Check the original CSV import
--    - Look at other jackpots created around the same time
--    - Re-import the jackpot results (recommended)
-- ============================================================================

