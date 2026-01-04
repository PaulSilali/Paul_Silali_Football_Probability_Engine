-- Migration: Add unique partial index for single active model per type
-- Purpose: Enforce single active model per model_type at database level
-- Date: 2025-01-01

-- Drop existing index if it exists
DROP INDEX IF EXISTS idx_models_active_per_type;

-- Create unique partial index
-- This ensures only one active model per model_type can exist
CREATE UNIQUE INDEX idx_models_active_per_type 
ON models (model_type) 
WHERE status = 'active';

-- Add comment
COMMENT ON INDEX idx_models_active_per_type IS 
'Ensures only one active model per model_type exists. Prevents multiple active models of the same type.';

-- Verify the index was created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE indexname = 'idx_models_active_per_type';

