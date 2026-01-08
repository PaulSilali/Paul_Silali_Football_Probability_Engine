"""
Draw Structural Feature Engineering Module

Provides optional feature engineering for draw structural data:
- xG Symmetry Index
- Referee Strictness Index
- Odds Volatility Index
"""
import logging
from typing import Optional, Dict
import numpy as np

logger = logging.getLogger(__name__)


def calculate_xg_symmetry_index(xg_home: float, xg_away: float) -> float:
    """
    Calculate xG symmetry index for draw probability.
    
    Higher symmetry (teams have similar xG) → higher draw probability.
    
    Formula:
    symmetry = 1.0 - abs(xg_home - xg_away) / max(xg_home + xg_away, 0.1)
    
    Examples:
    - xg_home=1.0, xg_away=1.0 → symmetry=1.0 (perfect symmetry, high draw probability)
    - xg_home=2.0, xg_away=0.5 → symmetry=0.4 (low symmetry, lower draw probability)
    - xg_home=0.5, xg_away=0.5 → symmetry=1.0 (perfect symmetry)
    
    Args:
        xg_home: Home team xG
        xg_away: Away team xG
    
    Returns:
        Symmetry index (0.0-1.0), where 1.0 = perfect symmetry
    """
    if xg_home is None or xg_away is None:
        return 0.5  # Default neutral symmetry
    
    xg_total = xg_home + xg_away
    if xg_total < 0.1:
        return 0.5  # Default for very low xG
    
    xg_diff = abs(xg_home - xg_away)
    symmetry = 1.0 - (xg_diff / xg_total)
    
    return float(np.clip(symmetry, 0.0, 1.0))


def calculate_referee_strictness_index(
    avg_cards_per_match: float,
    avg_goals_per_match: float
) -> float:
    """
    Calculate referee strictness index for draw probability.
    
    Stricter referees (more cards, fewer goals) → higher draw probability.
    
    Formula:
    strictness = (avg_cards / 3.0) * (1.0 / max(avg_goals, 0.5))
    
    Examples:
    - avg_cards=4.0, avg_goals=2.0 → strictness=0.67 (moderate strictness)
    - avg_cards=6.0, avg_goals=1.5 → strictness=1.33 (very strict, high draw probability)
    - avg_cards=2.0, avg_goals=3.0 → strictness=0.22 (lenient, lower draw probability)
    
    Args:
        avg_cards_per_match: Average cards per match
        avg_goals_per_match: Average goals per match
    
    Returns:
        Strictness index (typically 0.0-2.0), higher = stricter
    """
    if avg_cards_per_match is None or avg_goals_per_match is None:
        return 1.0  # Default neutral strictness
    
    if avg_goals_per_match < 0.5:
        avg_goals_per_match = 0.5  # Prevent division by zero
    
    strictness = (avg_cards_per_match / 3.0) * (1.0 / avg_goals_per_match)
    
    return float(np.clip(strictness, 0.0, 3.0))


def calculate_odds_volatility_index(
    odds_open: Optional[float],
    odds_close: Optional[float]
) -> float:
    """
    Calculate odds volatility index for draw probability.
    
    Higher volatility (large odds movement) → market uncertainty → potential draw.
    
    Formula:
    volatility = abs(odds_close - odds_open) / odds_open
    
    Examples:
    - odds_open=3.0, odds_close=3.5 → volatility=0.167 (moderate volatility)
    - odds_open=3.0, odds_close=4.0 → volatility=0.333 (high volatility, high uncertainty)
    - odds_open=3.0, odds_close=3.0 → volatility=0.0 (no movement, low uncertainty)
    
    Args:
        odds_open: Opening draw odds
        odds_close: Closing draw odds
    
    Returns:
        Volatility index (0.0-1.0+), higher = more volatile
    """
    if odds_open is None or odds_close is None:
        return 0.0  # No volatility if data missing
    
    if odds_open <= 1.0:
        return 0.0  # Invalid odds
    
    volatility = abs(odds_close - odds_open) / odds_open
    
    return float(np.clip(volatility, 0.0, 2.0))  # Cap at 200% change


def calculate_draw_adjustment_from_features(
    xg_symmetry: Optional[float] = None,
    referee_strictness: Optional[float] = None,
    odds_volatility: Optional[float] = None
) -> float:
    """
    Calculate combined draw probability adjustment from engineered features.
    
    Args:
        xg_symmetry: xG symmetry index (0.0-1.0)
        referee_strictness: Referee strictness index (0.0-3.0)
        odds_volatility: Odds volatility index (0.0-2.0)
    
    Returns:
        Combined adjustment multiplier (typically 0.9-1.1)
    """
    multiplier = 1.0
    
    # xG symmetry contribution (higher symmetry = higher draw probability)
    if xg_symmetry is not None:
        # Map symmetry (0.0-1.0) to adjustment (-0.1 to +0.1)
        symmetry_adj = (xg_symmetry - 0.5) * 0.2  # -0.1 to +0.1
        multiplier *= (1.0 + symmetry_adj)
    
    # Referee strictness contribution (stricter = higher draw probability)
    if referee_strictness is not None:
        # Map strictness (0.0-3.0) to adjustment (-0.05 to +0.1)
        strictness_adj = (referee_strictness - 1.0) * 0.05  # -0.05 to +0.1
        multiplier *= (1.0 + strictness_adj)
    
    # Odds volatility contribution (higher volatility = higher draw probability)
    if odds_volatility is not None:
        # Map volatility (0.0-2.0) to adjustment (0.0 to +0.05)
        volatility_adj = odds_volatility * 0.025  # 0.0 to +0.05
        multiplier *= (1.0 + volatility_adj)
    
    # Bound the multiplier
    return float(np.clip(multiplier, 0.85, 1.15))


def enhance_xg_data_with_symmetry(
    xg_home: float,
    xg_away: float
) -> Dict[str, float]:
    """
    Enhance xG data with symmetry index.
    
    Args:
        xg_home: Home team xG
        xg_away: Away team xG
    
    Returns:
        Dictionary with enhanced features:
        - xg_home: Original home xG
        - xg_away: Original away xG
        - xg_total: Total xG
        - xg_symmetry_index: Symmetry index (0.0-1.0)
    """
    xg_symmetry = calculate_xg_symmetry_index(xg_home, xg_away)
    
    return {
        "xg_home": xg_home,
        "xg_away": xg_away,
        "xg_total": xg_home + xg_away if xg_home is not None and xg_away is not None else None,
        "xg_symmetry_index": xg_symmetry
    }


def enhance_referee_stats_with_strictness(
    avg_cards_per_match: float,
    avg_goals_per_match: float
) -> Dict[str, float]:
    """
    Enhance referee stats with strictness index.
    
    Args:
        avg_cards_per_match: Average cards per match
        avg_goals_per_match: Average goals per match
    
    Returns:
        Dictionary with enhanced features:
        - avg_cards_per_match: Original cards average
        - avg_goals_per_match: Original goals average
        - referee_strictness_index: Strictness index (0.0-3.0)
    """
    strictness = calculate_referee_strictness_index(
        avg_cards_per_match,
        avg_goals_per_match
    )
    
    return {
        "avg_cards_per_match": avg_cards_per_match,
        "avg_goals_per_match": avg_goals_per_match,
        "referee_strictness_index": strictness
    }


def enhance_odds_movement_with_volatility(
    odds_open: Optional[float],
    odds_close: Optional[float],
    odds_delta: Optional[float] = None
) -> Dict[str, Optional[float]]:
    """
    Enhance odds movement with volatility index.
    
    Args:
        odds_open: Opening draw odds
        odds_close: Closing draw odds
        odds_delta: Odds delta (optional, will be calculated if not provided)
    
    Returns:
        Dictionary with enhanced features:
        - odds_open: Original opening odds
        - odds_close: Original closing odds
        - odds_delta: Odds delta
        - odds_volatility_index: Volatility index (0.0-2.0)
    """
    if odds_delta is None and odds_open is not None and odds_close is not None:
        odds_delta = odds_close - odds_open
    
    volatility = calculate_odds_volatility_index(odds_open, odds_close)
    
    return {
        "odds_open": odds_open,
        "odds_close": odds_close,
        "odds_delta": odds_delta,
        "odds_volatility_index": volatility
    }

