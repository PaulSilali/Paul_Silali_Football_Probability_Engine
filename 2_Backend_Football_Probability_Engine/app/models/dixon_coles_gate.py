"""
Dixon-Coles Conditional Gating Module
======================================

Determines when Dixon-Coles adjustment should be applied based on statistical conditions.
DC is most valid for low-scoring matches with tactical symmetry and stable lineups.
"""
from typing import Optional


def should_apply_dc(
    xg_home: float,
    xg_away: float,
    lineup_stable: bool = True
) -> bool:
    """
    Determine if Dixon-Coles adjustment should be applied.
    
    Dixon-Coles is statistically valid primarily for:
    - Low expected goal totals (< 2.4)
    - Tactical symmetry (balanced teams)
    - Stable lineups (no major injuries/suspensions)
    
    Args:
        xg_home: Expected goals for home team
        xg_away: Expected goals for away team
        lineup_stable: Whether lineups are stable (default True if unknown)
    
    Returns:
        True if DC should be applied, False otherwise
    """
    if xg_home is None or xg_away is None:
        # If xG unavailable, default to applying DC (conservative)
        return lineup_stable
    
    xg_total = xg_home + xg_away
    
    # DC is most valid for low-scoring matches
    # Threshold: 2.4 total expected goals
    return (xg_total < 2.4) and lineup_stable

