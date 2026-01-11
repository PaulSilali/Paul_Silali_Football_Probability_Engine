-- ============================================================================
-- SAVED SURE BET LISTS TABLE
-- ============================================================================
-- Allows users to save sure bet lists for later reloading

CREATE TABLE IF NOT EXISTS saved_sure_bet_lists (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR,                            -- User identifier (string for flexibility)
    name            VARCHAR NOT NULL,                   -- User-provided name
    description     TEXT,                               -- Optional description
    
    -- Sure bet games data
    games           JSONB NOT NULL,                     -- Array of game objects with predictions, odds, probabilities
    
    -- Betting details
    bet_amount_kshs FLOAT,                              -- Bet amount in Kenyan Shillings
    selected_game_ids JSONB,                            -- Array of selected game IDs
    
    -- Metadata
    total_odds      FLOAT,                              -- Total combined odds
    total_probability FLOAT,                            -- Total combined probability
    expected_amount_kshs FLOAT,                         -- Expected winnings in KShs
    weighted_amount_kshs FLOAT,                         -- Weighted expected amount in KShs
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_saved_sure_bets_user ON saved_sure_bet_lists(user_id);
CREATE INDEX idx_saved_sure_bets_created ON saved_sure_bet_lists(created_at DESC);

COMMENT ON TABLE saved_sure_bet_lists IS 'Saved sure bet lists for reloading';
COMMENT ON COLUMN saved_sure_bet_lists.games IS 'Array of game objects with predictions, odds, probabilities';
COMMENT ON COLUMN saved_sure_bet_lists.selected_game_ids IS 'Array of selected game IDs from the sure bet list';
COMMENT ON COLUMN saved_sure_bet_lists.bet_amount_kshs IS 'Bet amount in Kenyan Shillings';

