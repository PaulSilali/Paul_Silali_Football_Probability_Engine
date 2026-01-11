"""
Market Disagreement Analysis
=============================

Analyzes model-market disagreement and applies penalties.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def calculate_market_disagreement(
    model_prob: float,
    market_odds: float
) -> float:
    """
    Calculate absolute disagreement between model and market.
    
    Args:
        model_prob: Model probability (0-1)
        market_odds: Market odds (e.g., 2.0)
    
    Returns:
        Absolute difference between model and market probabilities
    """
    if market_odds is None or market_odds <= 0:
        return 0.0
    
    market_prob = 1.0 / market_odds
    return abs(model_prob - market_prob)


def market_disagreement_penalty(delta: float) -> float:
    """
    Calculate penalty based on market disagreement.
    
    Based on empirical analysis:
    - delta < 0.05: High agreement → no penalty
    - delta 0.05-0.10: OK → small penalty
    - delta 0.10-0.20: Poor → medium penalty
    - delta > 0.20: Dangerous → large penalty
    
    Args:
        delta: Absolute difference between model and market probabilities
    
    Returns:
        Penalty value (>= 0)
    """
    if delta < 0.05:
        return 0.0
    elif delta < 0.10:
        return 0.05
    elif delta < 0.20:
        return 0.15
    else:
        return 0.30


def is_extreme_disagreement(
    model_prob: float,
    market_odds: float,
    pick: str,
    market_favorite: str
) -> bool:
    """
    Check if disagreement is extreme enough to trigger hard gate.
    
    Args:
        model_prob: Model probability for pick
        market_odds: Market odds for pick
        pick: '1', 'X', or '2'
        market_favorite: Market favorite ('1', 'X', or '2')
    
    Returns:
        True if extreme disagreement and pick != market favorite
    """
    delta = calculate_market_disagreement(model_prob, market_odds)
    
    # Hard gate: extreme disagreement (>0.25) AND pick contradicts market
    if delta > 0.25 and pick != market_favorite:
        return True
    
    return False


def get_market_favorite(odds: Dict[str, float]) -> str:
    """
    Determine market favorite from odds.
    
    Args:
        odds: Dictionary with 'home', 'draw', 'away' keys
    
    Returns:
        '1' (home), 'X' (draw), or '2' (away) with lowest odds
    """
    if not odds:
        return "1"  # Default
    
    home_odds = odds.get("home") or odds.get("1")
    draw_odds = odds.get("draw") or odds.get("X")
    away_odds = odds.get("away") or odds.get("2")
    
    if home_odds is None:
        home_odds = float('inf')
    if draw_odds is None:
        draw_odds = float('inf')
    if away_odds is None:
        away_odds = float('inf')
    
    if home_odds <= draw_odds and home_odds <= away_odds:
        return "1"
    elif draw_odds <= away_odds:
        return "X"
    else:
        return "2"

