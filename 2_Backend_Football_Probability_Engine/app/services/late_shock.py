"""
Late-Shock Detection

Detects late information (odds movement, draw compression, favorite drift)
that indicates market surprises or lineup changes. Used to force hedges
on at least one ticket (preferably Set F or G).

Late shocks are detected when:
- Odds move significantly (>10%)
- Draw odds collapse (market sees less draw likelihood)
- Favorite odds drift (market disagrees with model)
"""

from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class LateShockSignal:
    """Late shock signal data."""
    shock_score: float  # [0.0, 1.0] - Higher = more shocking
    reasons: Dict[str, float]  # Dict of reason -> value
    triggered: bool  # True if shock_score >= 0.5


def compute_late_shock(
    odds_open: Optional[Dict[str, float]],
    odds_close: Optional[Dict[str, float]],
    model_probs: Dict[str, float],
    *,
    odds_move_thresh: float = 0.10,  # 10% movement threshold
    draw_collapse_thresh: float = 0.08,  # 0.08 odds drop threshold
    favorite_drift_thresh: float = 0.10,  # 10% movement threshold
) -> LateShockSignal:
    """
    Detect late shocks using odds movement vs model.
    
    Args:
        odds_open: Opening odds dict with 'home', 'draw', 'away' keys
        odds_close: Closing odds dict with 'home', 'draw', 'away' keys
        model_probs: Model probabilities dict with 'home', 'draw', 'away' keys
        odds_move_thresh: Percentage movement threshold for any outcome (default 0.10 = 10%)
        draw_collapse_thresh: Absolute odds drop for draw collapse (default 0.08)
        favorite_drift_thresh: Percentage movement threshold for favorite (default 0.10 = 10%)
        
    Returns:
        LateShockSignal with shock_score, reasons, and triggered flag
        
    Example:
        >>> odds_open = {"home": 2.0, "draw": 3.0, "away": 2.5}
        >>> odds_close = {"home": 1.8, "draw": 2.7, "away": 2.8}  # Home odds dropped, draw collapsed
        >>> model_probs = {"home": 0.45, "draw": 0.30, "away": 0.25}
        >>> shock = compute_late_shock(odds_open, odds_close, model_probs)
        >>> shock.triggered
        True
        >>> shock.shock_score > 0.5
        True
    """
    if not odds_open or not odds_close:
        return LateShockSignal(0.0, {}, False)
    
    reasons = {}
    score = 0.0
    
    def pct_move(open_val, close_val):
        """Calculate percentage movement."""
        if open_val is None or close_val is None:
            return 0.0
        if open_val <= 0:
            return 0.0
        return abs(close_val - open_val) / open_val
    
    # Factor 1: Odds movement (any outcome moving significantly)
    for k in ("home", "draw", "away"):
        open_val = odds_open.get(k)
        close_val = odds_close.get(k)
        
        if open_val and close_val:
            move = pct_move(open_val, close_val)
            if move >= odds_move_thresh:
                reasons[f"odds_move_{k}"] = move
                score += 0.35
                logger.debug(f"Late shock: {k} odds moved {move:.1%}")
    
    # Factor 2: Draw compression (draw odds dropping = market sees less draw)
    draw_open = odds_open.get("draw")
    draw_close = odds_close.get("draw")
    if draw_open and draw_close:
        draw_delta = draw_open - draw_close  # Positive = draw odds dropped
        if draw_delta >= draw_collapse_thresh:
            reasons["draw_collapse"] = draw_delta
            score += 0.35
            logger.debug(f"Late shock: Draw odds collapsed by {draw_delta:.3f}")
    
    # Factor 3: Favorite drift (market disagreeing with model)
    if model_probs:
        fav = max(("home", "away"), key=lambda x: model_probs.get(x, 0.0))
        fav_open = odds_open.get(fav)
        fav_close = odds_close.get(fav)
        
        if fav_open and fav_close:
            fav_move = pct_move(fav_open, fav_close)
            if fav_move >= favorite_drift_thresh:
                reasons["favorite_drift"] = fav_move
                score += 0.30
                logger.debug(f"Late shock: Favorite ({fav}) odds drifted {fav_move:.1%}")
    
    # Clamp score to [0.0, 1.0]
    score = min(max(score, 0.0), 1.0)
    triggered = score >= 0.5
    
    return LateShockSignal(score, reasons, triggered)


def should_force_hedge(
    shock_signal: LateShockSignal,
    role: str
) -> bool:
    """
    Determine if a hedge should be forced based on late shock.
    
    Args:
        shock_signal: LateShockSignal from compute_late_shock()
        role: Ticket role ('A', 'B', 'C', 'D', 'E', 'F', 'G')
        
    Returns:
        True if hedge should be forced
        
    Note:
        Hedges are typically forced on Set F (Late shock) and Set G (Anti-favorite hedge)
    """
    if not shock_signal.triggered:
        return False
    
    # Force hedge on F and G roles
    if role in ("F", "G"):
        return True
    
    # For other roles, only force if shock is very strong
    if shock_signal.shock_score >= 0.7:
        return True
    
    return False

