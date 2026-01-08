"""
League-Specific Correlation Weights

Different leagues exhibit different correlation patterns. This module provides
league-specific weight overrides for correlation scoring.

Example:
    - Premier League: More emphasis on draw regime (draw-heavy league)
    - Serie A: Higher draw regime weight (defensive league)
    - La Liga: More emphasis on odds shape (market efficiency)
"""

DEFAULT_WEIGHTS = {
    "same_league": 0.25,
    "kickoff_window": 0.20,
    "odds_shape": 0.35,
    "draw_regime": 0.20,
    "total_goals": 0.15
}

LEAGUE_OVERRIDES = {
    # Premier League - Draw-heavy, market-efficient
    "E0": {
        "odds_shape": 0.25,
        "draw_regime": 0.30
    },
    # Serie A - Defensive, high draw rate
    "I1": {
        "draw_regime": 0.35,
        "odds_shape": 0.25
    },
    # La Liga - Market-efficient, odds shape matters more
    "SP1": {
        "odds_shape": 0.30,
        "draw_regime": 0.25
    },
    # Bundesliga - Synchronized kickoffs, kickoff window matters more
    "D1": {
        "kickoff_window": 0.30,
        "odds_shape": 0.25
    },
    # Ligue 1 - Balanced
    "F1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Eredivisie - High scoring, total goals matters more
    "N1": {
        "total_goals": 0.25,
        "draw_regime": 0.15
    },
    # Championship - Similar to Premier League
    "E1": {
        "odds_shape": 0.25,
        "draw_regime": 0.30
    },
    # League One
    "E2": {
        "odds_shape": 0.30,
        "draw_regime": 0.25
    },
    # League Two
    "E3": {
        "odds_shape": 0.30,
        "draw_regime": 0.25
    },
    # Scottish Premiership - High home advantage
    "SC0": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Pro League (Belgium)
    "B1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Super Lig (Turkey) - High home advantage
    "T1": {
        "draw_regime": 0.20,
        "odds_shape": 0.35
    },
    # Super League 1 (Greece)
    "G1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Ekstraklasa (Poland)
    "PL1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Superliga (Denmark)
    "DK1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Eliteserien (Norway)
    "NO1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # Liga MX (Mexico)
    "MEX1": {
        "draw_regime": 0.20,
        "odds_shape": 0.35
    },
    # MLS (USA) - Low draw rate
    "USA1": {
        "draw_regime": 0.15,
        "odds_shape": 0.40
    },
    # Super League (China)
    "CHN1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # J-League (Japan)
    "JPN1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    },
    # A-League (Australia)
    "AUS1": {
        "draw_regime": 0.25,
        "odds_shape": 0.30
    }
}


def get_corr_weights(league_code: str) -> dict:
    """
    Get correlation weights for a specific league.
    
    Args:
        league_code: League code (e.g., 'E0', 'SP1', 'I1')
        
    Returns:
        Dictionary with correlation weights for:
        - same_league: Weight for same league correlation
        - kickoff_window: Weight for kickoff time proximity
        - odds_shape: Weight for odds shape similarity
        - draw_regime: Weight for draw signal similarity
        - total_goals: Weight for expected goals similarity
        
    Example:
        >>> weights = get_corr_weights("E0")
        >>> weights["draw_regime"]
        0.30  # Premier League emphasizes draw regime
    """
    w = DEFAULT_WEIGHTS.copy()
    w.update(LEAGUE_OVERRIDES.get(league_code, {}))
    
    # Normalize weights to sum to 1.0 (optional, but ensures consistency)
    total = sum(w.values())
    if total > 0:
        w = {k: v / total for k, v in w.items()}
    
    return w

