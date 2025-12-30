"""
Draw Model
==========

Deterministic, auditable draw-probability estimator.

Responsibilities:
- Compute P(Draw) only
- Consume Poisson / Dixon–Coles outputs
- Optionally blend market draw signal
- Enforce safety bounds
- Support downstream calibration

This module DOES NOT:
- Estimate team strengths
- Predict home/away wins
- Perform model training
"""

from dataclasses import dataclass
from typing import Optional, Dict
import math

try:
    import numpy as np
    from scipy.stats import poisson
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    # Fallback for environments without scipy
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("scipy not available, draw model will use simplified calculations")


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class DrawModelConfig:
    """Configuration for draw probability model"""
    # Blending weights (must sum to 1.0)
    w_poisson: float = 0.55
    w_dixon_coles: float = 0.30
    w_market: float = 0.15

    # Hard safety bounds (jackpot-stable)
    draw_floor: float = 0.18
    draw_cap: float = 0.38

    # Goal truncation for Poisson summation
    max_goals: int = 10

    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = self.w_poisson + self.w_dixon_coles + self.w_market
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Draw model weights must sum to 1.0, got {total}")


# ---------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------

def poisson_draw_probability(
    lambda_home: float,
    lambda_away: float,
    max_goals: int = 10
) -> float:
    """
    Independent Poisson draw probability:
    P(Gh = Ga) = Σ_k P(Gh = k | λ_home) × P(Ga = k | λ_away)
    """
    if not HAS_SCIPY:
        # Fallback: approximate using basic math
        # This is less accurate but works without scipy
        p = 0.0
        for g in range(max_goals + 1):
            # Poisson PMF approximation
            p_home = (lambda_home ** g * math.exp(-lambda_home)) / math.factorial(g) if g < 20 else 0
            p_away = (lambda_away ** g * math.exp(-lambda_away)) / math.factorial(g) if g < 20 else 0
            p += p_home * p_away
        return float(p)
    
    p = 0.0
    for g in range(max_goals + 1):
        p += poisson.pmf(g, lambda_home) * poisson.pmf(g, lambda_away)
    return float(p)


def dixon_coles_draw_probability(
    lambda_home: float,
    lambda_away: float,
    rho: float,
    max_goals: int = 10
) -> float:
    """
    Dixon–Coles adjusted draw probability.

    Uses the same low-score logic as PoissonTrainer._tau():
    - Adjusts (0–0) and (1–1)
    - Leaves higher scores untouched
    """
    # Base Poisson draw
    base_draw = poisson_draw_probability(lambda_home, lambda_away, max_goals)

    # Explicit low-score terms
    if HAS_SCIPY:
        p_00 = poisson.pmf(0, lambda_home) * poisson.pmf(0, lambda_away)
        p_11 = poisson.pmf(1, lambda_home) * poisson.pmf(1, lambda_away)
    else:
        # Fallback
        p_00 = math.exp(-lambda_home) * math.exp(-lambda_away)
        p_11 = (lambda_home * math.exp(-lambda_home)) * (lambda_away * math.exp(-lambda_away))

    # DC tau adjustments (consistent with trainer)
    # tau_00 = 1 - λ_home * λ_away * rho
    # tau_11 = 1 - rho
    tau_00 = max(1.0 - lambda_home * lambda_away * rho, 1e-10)
    tau_11 = max(1.0 - rho, 1e-10)

    adj_00 = tau_00 * p_00
    adj_11 = tau_11 * p_11

    # Replace low-score mass
    corrected_draw = base_draw - p_00 - p_11 + adj_00 + adj_11
    return float(max(0.0, corrected_draw))


def market_implied_draw_probability(
    odds_home: float,
    odds_draw: float,
    odds_away: float
) -> float:
    """
    Normalized market-implied draw probability.
    Market is treated strictly as a signal, never an oracle.
    """
    if odds_home <= 0 or odds_draw <= 0 or odds_away <= 0:
        return 0.0

    inv_h = 1.0 / odds_home
    inv_d = 1.0 / odds_draw
    inv_a = 1.0 / odds_away

    total = inv_h + inv_d + inv_a
    if total <= 0:
        return 0.0

    return float(inv_d / total)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def compute_draw_probability(
    *,
    lambda_home: float,
    lambda_away: float,
    rho: float,
    odds: Optional[Dict[str, float]] = None,
    config: DrawModelConfig = DrawModelConfig()
) -> Dict[str, float]:
    """
    Compute final draw probability.

    Inputs:
    - lambda_home, lambda_away: expected goals (from Poisson model)
    - rho: Dixon–Coles correlation parameter
    - odds: optional dict {home, draw, away}
    - config: DrawModelConfig

    Returns:
    {
        "draw": P(D),
        "components": {
            "poisson": P(D)_pois,
            "dixon_coles": P(D)_dc,
            "market": P(D)_market or None
        }
    }
    """
    # --- Component probabilities ---
    p_pois = poisson_draw_probability(
        lambda_home,
        lambda_away,
        config.max_goals
    )

    p_dc = dixon_coles_draw_probability(
        lambda_home,
        lambda_away,
        rho,
        config.max_goals
    )

    p_mkt = None
    if odds and all(k in odds for k in ("home", "draw", "away")):
        p_mkt = market_implied_draw_probability(
            odds_home=odds["home"],
            odds_draw=odds["draw"],
            odds_away=odds["away"]
        )

    # --- Blending ---
    p_draw = (
        config.w_poisson * p_pois +
        config.w_dixon_coles * p_dc +
        (config.w_market * p_mkt if p_mkt is not None else 0.0)
    )

    # If no market odds, renormalize weights
    if p_mkt is None:
        total_weight = config.w_poisson + config.w_dixon_coles
        if total_weight > 0:
            p_draw = (
                (config.w_poisson / total_weight) * p_pois +
                (config.w_dixon_coles / total_weight) * p_dc
            )

    # --- Safety bounds ---
    if HAS_SCIPY:
        p_draw = float(np.clip(p_draw, config.draw_floor, config.draw_cap))
    else:
        p_draw = float(max(config.draw_floor, min(p_draw, config.draw_cap)))

    return {
        "draw": p_draw,
        "components": {
            "poisson": p_pois,
            "dixon_coles": p_dc,
            "market": p_mkt
        }
    }


# ---------------------------------------------------------------------
# Reconciliation helper
# ---------------------------------------------------------------------

def reconcile_with_draw(
    p_home_raw: float,
    p_away_raw: float,
    p_draw: float
) -> Dict[str, float]:
    """
    Redistribute remaining probability mass after draw is fixed.

    Mandatory reconciliation rule:
    - Ensures sum-to-one
    - Preserves relative H/A strength
    """
    remaining = 1.0 - p_draw
    denom = p_home_raw + p_away_raw

    if denom <= 0:
        # Degenerate fallback (should never happen)
        return {
            "home": remaining * 0.5,
            "draw": p_draw,
            "away": remaining * 0.5
        }

    scale = remaining / denom

    return {
        "home": p_home_raw * scale,
        "draw": p_draw,
        "away": p_away_raw * scale
    }

