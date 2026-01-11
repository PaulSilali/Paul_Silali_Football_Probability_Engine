-- ============================================================================
-- UPDATE FIXTURE LIMITS
-- ============================================================================
-- Increase fixture limits from 20 to 200 to support larger jackpots
-- This allows importing jackpots with up to 200 fixtures

-- Update saved_probability_results constraint
ALTER TABLE saved_probability_results 
DROP CONSTRAINT IF EXISTS chk_total_fixtures;

ALTER TABLE saved_probability_results 
ADD CONSTRAINT chk_total_fixtures CHECK (total_fixtures >= 1 AND total_fixtures <= 200);

-- Update saved_jackpot_templates constraint
ALTER TABLE saved_jackpot_templates 
DROP CONSTRAINT IF EXISTS chk_fixture_count;

ALTER TABLE saved_jackpot_templates 
ADD CONSTRAINT chk_fixture_count CHECK (fixture_count >= 1 AND fixture_count <= 200);

COMMENT ON CONSTRAINT chk_total_fixtures ON saved_probability_results IS 'Total fixtures must be between 1 and 200';
COMMENT ON CONSTRAINT chk_fixture_count ON saved_jackpot_templates IS 'Fixture count must be between 1 and 200';

