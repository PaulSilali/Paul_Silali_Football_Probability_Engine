-- Migration: Add Draw Model Support
-- Date: 2025-01-XX
-- Purpose: Enable model_type='draw' for dedicated draw probability models

BEGIN;

-- 1. Check if model_type is VARCHAR or ENUM
-- If it's VARCHAR, no action needed. If ENUM, add 'draw' value.

DO $$
BEGIN
    -- Check if model_type column exists and is an enum
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'models'
        AND column_name = 'model_type'
        AND data_type = 'USER-DEFINED'
    ) THEN
        -- It's an enum, add 'draw' value if it doesn't exist
        IF NOT EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = (SELECT udt_name FROM information_schema.columns 
                              WHERE table_name = 'models' AND column_name = 'model_type')
            AND e.enumlabel = 'draw'
        ) THEN
            -- Get the enum type name
            DECLARE
                enum_type_name TEXT;
            BEGIN
                SELECT udt_name INTO enum_type_name
                FROM information_schema.columns
                WHERE table_name = 'models' AND column_name = 'model_type';
                
                EXECUTE format('ALTER TYPE %I ADD VALUE IF NOT EXISTS ''draw''', enum_type_name);
            END;
        END IF;
    END IF;
END
$$;

-- 2. Create index for faster draw-model lookup (if model_type is indexed)
CREATE INDEX IF NOT EXISTS idx_models_draw_active
ON models (model_type, status)
WHERE model_type = 'draw' AND status = 'active';

-- 3. Add comment explaining draw model type
COMMENT ON COLUMN models.model_type IS 
'Model type: poisson, blending, calibration, or draw. Draw models estimate P(Draw) only.';

COMMIT;

