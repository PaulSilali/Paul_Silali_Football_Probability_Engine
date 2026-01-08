"""
Draw Structural Adjustment Service

Implements production-safe probability adjustment pipeline for draw-aware
Home/Away probability redistribution.

CRITICAL PRINCIPLES:
- Never adjust probabilities additively
- Adjust latent variables, not outputs
- Draw is a structural constraint, not an outcome
- Every adjustment must preserve entropy
- Calibration happens last—always

This module implements the Home-Away Compression mechanism, which is the
most important draw-aware H/A adjustment.
"""

from typing import Dict, Optional
import math
import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy not available, using fallback implementations")


def apply_draw_structural_adjustments(
    base_home: float,
    base_draw: float,
    base_away: float,
    lambda_home: float,
    lambda_away: float,
    draw_signal: float,
    *,
    compression_strength: float = 0.5,
    draw_floor: float = 0.18,
    draw_cap: float = 0.38,
) -> Dict:
    """
    Apply draw-aware structural adjustments to Home/Away probabilities
    BEFORE draw mass reallocation and calibration.

    This function implements the critical Home-Away Compression mechanism:
    - When draw signal is high, compress H/A toward each other
    - Prevents false favorites and jackpot busts
    - Maintains probability coherence

    Parameters
    ----------
    base_home : float
        Raw home win probability from Poisson / Dixon-Coles
    base_draw : float
        Raw draw probability from Poisson / Dixon-Coles
    base_away : float
        Raw away win probability from Poisson / Dixon-Coles
    lambda_home : float
        Expected home goals (λ_h)
    lambda_away : float
        Expected away goals (λ_a)
    draw_signal : float
        Normalized draw signal in [0, 1]
    compression_strength : float
        Maximum compression applied to H/A spread (0.3–0.6 safe)
    draw_floor : float
        Minimum allowed draw probability
    draw_cap : float
        Maximum allowed draw probability

    Returns
    -------
    dict
        {
            "home": adjusted_home,
            "draw": adjusted_draw,
            "away": adjusted_away,
            "meta": {
                "draw_signal": float,
                "compression": float,
                "lambda_gap": float,
            }
        }
    """
    # --- 0. Defensive checks ---
    draw_signal = max(0.0, min(1.0, draw_signal))

    total = base_home + base_draw + base_away
    if total <= 0:
        raise ValueError("Invalid base probabilities")

    # Normalize defensively
    base_home /= total
    base_draw /= total
    base_away /= total

    # --- 1. Home/Away compression (draw-aware) ---
    ha_sum = base_home + base_away
    if ha_sum <= 0:
        # Degenerate case: force draw
        return {
            "home": 0.0,
            "draw": 1.0,
            "away": 0.0,
            "meta": {"reason": "degenerate_ha_sum"},
        }

    mean_ha = ha_sum / 2.0
    spread = base_home - base_away

    # Compression factor shrinks spread toward zero
    # Higher draw_signal → more compression
    compression = 1.0 - compression_strength * draw_signal
    compression = max(0.4, min(1.0, compression))  # hard safety bounds

    comp_home = mean_ha + 0.5 * spread * compression
    comp_away = mean_ha - 0.5 * spread * compression

    # --- 2. Lambda symmetry dampening (extra safety) ---
    # If λ_home ≈ λ_away, teams are evenly matched → compress further
    lambda_gap = abs(lambda_home - lambda_away)
    gap_factor = min(1.0, max(0.75, 1.0 - 0.15 * lambda_gap))

    comp_home *= gap_factor
    comp_away *= gap_factor

    # Re-normalize H/A after dampening
    ha_sum_adj = comp_home + comp_away
    if ha_sum_adj > 0:
        comp_home /= ha_sum_adj
        comp_away /= ha_sum_adj
    else:
        # Fallback if sum becomes zero
        comp_home = comp_away = 0.5

    # --- 3. Draw mass adjustment (controlled) ---
    # Conservative draw boost based on draw signal
    draw_boost = draw_signal * 0.08  # conservative, jackpot-safe
    new_draw = base_draw + draw_boost
    new_draw = max(draw_floor, min(draw_cap, new_draw))

    # Redistribute remaining mass proportionally
    remaining = 1.0 - new_draw
    adj_home = remaining * comp_home
    adj_away = remaining * comp_away

    # Final normalization (floating-point safety)
    final_total = adj_home + new_draw + adj_away
    if final_total > 0:
        adj_home /= final_total
        new_draw /= final_total
        adj_away /= final_total
    else:
        # Fallback: uniform distribution
        adj_home = adj_away = new_draw = 1.0 / 3.0

    # Final safety check
    assert abs(adj_home + new_draw + adj_away - 1.0) < 1e-6, \
        f"Probabilities don't sum to 1.0: {adj_home + new_draw + adj_away}"

    return {
        "home": float(adj_home),
        "draw": float(new_draw),
        "away": float(adj_away),
        "meta": {
            "draw_signal": float(draw_signal),
            "compression": float(compression),
            "lambda_gap": float(lambda_gap),
            "gap_factor": float(gap_factor),
        },
    }


def calculate_draw_signal(
    lambda_total: float,
    market_draw_prob: Optional[float],
    weather_factor: Optional[float],
    h2h_draw_rate: Optional[float],
    league_draw_rate: Optional[float] = None,
) -> float:
    """
    Calculate draw signal strength (0.0 to 1.0) from multiple sources.

    Combines signals from:
    - Low total goals (λ_total < 2.1 → high draw signal)
    - Market draw probability (if market sees high draw)
    - Weather conditions (extreme weather → randomness)
    - H2H draw rate (if teams historically draw often)
    - League draw rate (structural tendency)

    Parameters
    ----------
    lambda_total : float
        Total expected goals (λ_home + λ_away)
    market_draw_prob : Optional[float]
        Market-implied draw probability (0.0-1.0)
    weather_factor : Optional[float]
        Weather impact factor (0.0-1.0, higher = more extreme)
    h2h_draw_rate : Optional[float]
        Historical H2H draw rate (0.0-1.0)
    league_draw_rate : Optional[float]
        League average draw rate (0.0-1.0)

    Returns
    -------
    float
        Normalized draw signal in [0.0, 1.0]
    """
    signals = []

    # 1. Low total goals → high draw signal
    if lambda_total < 2.1:
        signals.append(0.8)
    elif lambda_total < 2.5:
        signals.append(0.6)
    else:
        signals.append(0.4)

    # 2. Market sees high draw
    if market_draw_prob is not None:
        if market_draw_prob > 0.28:
            signals.append(0.7)
        elif market_draw_prob > 0.25:
            signals.append(0.5)
        else:
            signals.append(0.3)

    # 3. Weather increases randomness
    if weather_factor is not None:
        if weather_factor > 0.6:  # Extreme weather
            signals.append(0.6)
        elif weather_factor > 0.4:
            signals.append(0.4)
        else:
            signals.append(0.2)

    # 4. H2H high draw rate
    if h2h_draw_rate is not None:
        if h2h_draw_rate > 0.30:
            signals.append(0.5)
        elif h2h_draw_rate > 0.25:
            signals.append(0.3)
        else:
            signals.append(0.1)

    # 5. League draw rate (structural tendency)
    if league_draw_rate is not None:
        if league_draw_rate > 0.28:
            signals.append(0.4)
        elif league_draw_rate > 0.25:
            signals.append(0.2)
        else:
            signals.append(0.1)

    # Average all signals (or return neutral if no signals)
    if signals:
        return float(sum(signals) / len(signals))
    else:
        return 0.5  # Neutral signal if no data available

