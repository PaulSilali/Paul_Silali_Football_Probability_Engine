-- Fix MatchResult Enum Type
-- The database has 'match_result' but SQLAlchemy expects 'matchresult'
-- This script creates the enum with the correct name

-- Check if matchresult enum exists, if not create it
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'matchresult') THEN
        CREATE TYPE matchresult AS ENUM ('H', 'D', 'A');
        RAISE NOTICE 'Created enum type matchresult';
    ELSE
        RAISE NOTICE 'Enum type matchresult already exists';
    END IF;
END $$;

-- If match_result exists but matchresult doesn't, we can migrate
-- But for now, just create matchresult to match SQLAlchemy's expectation

