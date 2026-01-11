"""
Hard Contradiction Detection Module
====================================

Detects hard contradictions that should cause immediate ticket rejection.
"""
from typing import Dict, Any


def is_hard_contradiction(match: Dict[str, Any]) -> bool:
    """
    Detect hard contradictions that should cause ticket rejection.
    
    Hard contradictions:
    1. Draw pick when market_prob_home > 0.55 (strong home favorite)
    2. Draw pick when xG difference > 0.45 (one-sided match)
    3. Away pick when away_odds > 3.2 AND market_prob_home > 0.50
    
    Args:
        match: Match dictionary with:
            - pick: '1', 'X', or '2'
            - market_odds: Dict with odds
            - market_prob_home: Market-implied probability for home
            - xg_home: Expected goals home
            - xg_away: Expected goals away
    
    Returns:
        True if hard contradiction detected, False otherwise
    """
    pick = match.get('pick', '')
    market_odds = match.get('market_odds', {})
    market_prob_home = match.get('market_prob_home')
    xg_home = match.get('xg_home')
    xg_away = match.get('xg_away')
    
    # Calculate market probabilities if not provided
    if market_prob_home is None and market_odds:
        home_odds = market_odds.get('home') or market_odds.get('1')
        draw_odds = market_odds.get('draw') or market_odds.get('X')
        away_odds = market_odds.get('away') or market_odds.get('2')
        
        if home_odds and draw_odds and away_odds:
            # Simple margin removal (assume 5% margin)
            total_implied = (1/home_odds + 1/draw_odds + 1/away_odds)
            if total_implied > 0:
                market_prob_home = (1/home_odds) / total_implied
    
    # Draw contradictions
    if pick == 'X':
        # Draw when home is strong favorite
        if market_prob_home and market_prob_home > 0.55:
            return True
        
        # Draw when xG difference is large (one-sided match)
        if xg_home is not None and xg_away is not None:
            xg_diff = abs(xg_home - xg_away)
            if xg_diff > 0.45:
                return True
    
    # Away contradictions
    if pick == '2':
        away_odds = market_odds.get('away') or market_odds.get('2')
        if away_odds and away_odds > 3.2:
            if market_prob_home and market_prob_home > 0.50:
                return True
    
    return False

