"""
Draw Prior Injection Module

Fixes structural draw underestimation in Poisson models by injecting
per-league draw priors before normalization.

This is a lightweight, legal adjustment that fixes the shape before
blending, so calibration becomes a fine-tuner, not a crutch.

Formula:
    probs.draw *= (1 + draw_prior_league)

Where draw_prior_league is learned per league from historical
draw frequency vs model draw mass.
"""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Default draw priors per league (learned from historical data)
# These are conservative estimates that can be refined during training
DEFAULT_DRAW_PRIORS: Dict[str, float] = {
    # Premier League
    "E0": 0.08,
    # La Liga
    "SP1": 0.10,
    # Serie A
    "I1": 0.09,
    # Bundesliga
    "D1": 0.07,
    # Ligue 1
    "F1": 0.08,
    # Championship
    "E1": 0.09,
    # Default for unknown leagues
    "default": 0.08,
}

# Global default (used if league not found)
GLOBAL_DEFAULT_DRAW_PRIOR = 0.08


def get_draw_prior(league_code: Optional[str] = None) -> float:
    """
    Get draw prior for a league.
    
    Args:
        league_code: League code (e.g., "E0", "SP1") or None
        
    Returns:
        Draw prior multiplier (typically 0.05-0.12)
    """
    if league_code and league_code in DEFAULT_DRAW_PRIORS:
        return DEFAULT_DRAW_PRIORS[league_code]
    
    return DEFAULT_DRAW_PRIORS.get("default", GLOBAL_DEFAULT_DRAW_PRIOR)


def inject_draw_prior(
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    league_code: Optional[str] = None
) -> tuple[float, float, float]:
    """
    Inject draw prior before normalization.
    
    This adjusts draw probability upstream to fix structural bias,
    then renormalizes to maintain probability correctness.
    
    Args:
        home_prob: Raw home win probability
        draw_prob: Raw draw probability
        away_prob: Raw away win probability
        league_code: League code for per-league adjustment
        
    Returns:
        Tuple of (home, draw, away) probabilities after draw prior injection
    """
    # Get league-specific draw prior
    draw_prior = get_draw_prior(league_code)
    
    # Apply draw prior multiplier
    adjusted_draw = draw_prob * (1.0 + draw_prior)
    
    # Renormalize to maintain probability correctness
    total = home_prob + adjusted_draw + away_prob
    
    if total <= 0:
        # Failsafe: return uniform distribution
        return (1/3, 1/3, 1/3)
    
    return (
        home_prob / total,
        adjusted_draw / total,
        away_prob / total
    )


def learn_draw_prior_from_data(
    model_draw_probs: list[float],
    actual_draw_frequency: float,
    min_samples: int = 500
) -> float:
    """
    Learn optimal draw prior from historical data.
    
    This compares model draw mass vs actual draw frequency
    to determine the correction factor.
    
    Args:
        model_draw_probs: List of model draw probabilities
        actual_draw_frequency: Actual frequency of draws (0.0-1.0)
        min_samples: Minimum samples required for learning
        
    Returns:
        Optimal draw prior multiplier
    """
    if len(model_draw_probs) < min_samples:
        logger.warning(f"Insufficient samples ({len(model_draw_probs)}) for draw prior learning. Using default.")
        return GLOBAL_DEFAULT_DRAW_PRIOR
    
    # Calculate average model draw probability
    avg_model_draw = sum(model_draw_probs) / len(model_draw_probs)
    
    if avg_model_draw <= 0:
        return GLOBAL_DEFAULT_DRAW_PRIOR
    
    # Calculate required adjustment
    # If model predicts 0.25 draws but actual is 0.28, we need:
    # draw_prior = (actual / model) - 1 = (0.28 / 0.25) - 1 = 0.12
    draw_prior = (actual_draw_frequency / avg_model_draw) - 1.0
    
    # Clamp to reasonable bounds (0.0 to 0.20)
    draw_prior = max(0.0, min(draw_prior, 0.20))
    
    logger.info(f"Learned draw prior: {draw_prior:.4f} (model avg: {avg_model_draw:.4f}, actual: {actual_draw_frequency:.4f})")
    
    return draw_prior

