-- Create International League for handling international matches
-- This allows the system to handle country vs country games

INSERT INTO leagues (code, name, country, tier, is_active)
VALUES ('INT', 'International Matches', 'World', 0, TRUE)
ON CONFLICT (code) DO NOTHING;

-- Note: Tier 0 indicates special league type (not a regular club league)
-- This allows filtering in queries if needed

