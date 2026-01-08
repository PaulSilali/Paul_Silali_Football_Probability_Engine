-- Add pipeline_metadata column to jackpots table
-- Stores pipeline execution results: data downloaded, model trained, etc.

ALTER TABLE jackpots 
ADD COLUMN IF NOT EXISTS pipeline_metadata JSONB DEFAULT NULL;

COMMENT ON COLUMN jackpots.pipeline_metadata IS 'Stores pipeline execution results including: data_downloaded, model_trained, teams_created, download_stats, training_stats, execution_timestamp';

-- Example structure:
-- {
--   "execution_timestamp": "2024-01-01T10:00:00Z",
--   "pipeline_run": true,
--   "teams_created": ["New Team"],
--   "data_downloaded": true,
--   "download_stats": {
--     "leagues_downloaded": ["E0"],
--     "total_matches": 1520,
--     "seasons": ["2324", "2223"]
--   },
--   "model_trained": true,
--   "training_stats": {
--     "model_id": 42,
--     "model_version": "poisson-20240101-100500",
--     "teams_trained": 580
--   },
--   "probabilities_calculated_with_new_data": true,
--   "status": "completed",
--   "errors": []
-- }

