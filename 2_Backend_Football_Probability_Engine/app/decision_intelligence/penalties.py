"""
Structural Penalties Module
===========================

Calculates structural penalties based on market conditions and pick characteristics.
"""
from typing import Dict, Any


def structural_penalty(match: Dict[str, Any]) -> float:
    """
    Calculate structural penalty for a match pick.
    
    Penalties apply when:
    - Draw odds > 3.4 (high draw odds)
    - Draw pick with large xG difference (> 0.45)
    - Away pick with high away odds (> 3.2)
    
    Args:
        match: Match dictionary with:
            - pick: '1', 'X', or '2'
            - market_odds: Dict with 'home', 'draw', 'away' odds
            - xg_home: Expected goals home
            - xg_away: Expected goals away
    
    Returns:
        Structural penalty (>= 0)
    """
    penalty = 0.0
    
    pick = match.get('pick', '')
    market_odds = match.get('market_odds', {})
    xg_home = match.get('xg_home', 0.0)
    xg_away = match.get('xg_away', 0.0)
    xg_diff = abs(xg_home - xg_away) if xg_home and xg_away else 0.0
    
    # Draw penalties
    if pick == 'X':
        draw_odds = market_odds.get('draw') or market_odds.get('X')
        if draw_odds and draw_odds > 3.4:
            penalty += 0.15
        
        if xg_diff > 0.45:
            penalty += 0.20
    
    # Away penalties
    if pick == '2':
        away_odds = market_odds.get('away') or market_odds.get('2')
        if away_odds and away_odds > 3.2:
            penalty += 0.10
    
    return penalty

