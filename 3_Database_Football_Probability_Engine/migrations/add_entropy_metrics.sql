-- Migration: Add Entropy and Temperature Metrics
-- Date: 2026-01-01
-- Purpose: Support uncertainty monitoring and temperature learning

-- Add entropy and temperature columns to training_runs table
ALTER TABLE training_runs
ADD COLUMN IF NOT EXISTS avg_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS p10_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS p90_entropy DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS alpha_mean DOUBLE PRECISION;

-- Add entropy and uncertainty metadata to predictions table (optional, for audit)
-- Note: This is optional as it may be large. Only add if you need per-prediction audit.
-- ALTER TABLE predictions
-- ADD COLUMN IF NOT EXISTS entropy DOUBLE PRECISION,
-- ADD COLUMN IF NOT EXISTS alpha_effective DOUBLE PRECISION,
-- ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION;

-- Create index for entropy monitoring queries
CREATE INDEX IF NOT EXISTS idx_training_runs_entropy 
ON training_runs (avg_entropy);

CREATE INDEX IF NOT EXISTS idx_training_runs_temperature 
ON training_runs (temperature);

-- Add comments for documentation
COMMENT ON COLUMN training_runs.avg_entropy IS 'Average normalized entropy (0-1) of model predictions during training';
COMMENT ON COLUMN training_runs.p10_entropy IS '10th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.p90_entropy IS '90th percentile of entropy distribution';
COMMENT ON COLUMN training_runs.temperature IS 'Learned temperature parameter for probability softening (typically 1.0-1.5)';
COMMENT ON COLUMN training_runs.alpha_mean IS 'Mean effective alpha used in entropy-weighted blending';

