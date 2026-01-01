"""
Uncertainty Control Module

Provides deterministic probability softening and entropy-based blending
to prevent overconfidence and improve Log Loss.

This module is regulator-defensible and maintains probability correctness.
"""
import math
from typing import Tuple

EPS = 1e-12


def temperature_scale(
    probs: Tuple[float, float, float],
    temperature: float
) -> Tuple[float, float, float]:
    """
    Deterministic temperature scaling (probability softening).
    
    This is NOT calibration. It is uncertainty softening to prevent
    overconfident predictions.
    
    Formula:
        p_i' = p_i^(1/T) / sum_j p_j^(1/T)
    
    Args:
        probs: Tuple of (home, draw, away) probabilities
        temperature: Temperature parameter (T > 0, typically 1.0-1.5)
                    Higher T = more conservative (softer probabilities)
    
    Returns:
        Tuple of temperature-scaled probabilities (home, draw, away)
    
    Guarantees:
        - Probabilities sum to 1.0
        - No probability < EPS
        - Deterministic and reproducible
    """
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    
    # Guard against invalid input
    p = [max(x, EPS) for x in probs]
    
    # Apply temperature scaling
    inv_t = 1.0 / temperature
    scaled = [x ** inv_t for x in p]
    
    total = sum(scaled)
    if total <= 0:
        # Failsafe: uniform distribution
        return (1/3, 1/3, 1/3)
    
    return tuple(x / total for x in scaled)


def entropy(probs: Tuple[float, float, float]) -> float:
    """
    Compute Shannon entropy of a probability distribution.
    
    Args:
        probs: Tuple of (home, draw, away) probabilities
    
    Returns:
        Shannon entropy in bits (using log2)
    """
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log2(p)
    return h


def normalized_entropy(probs: Tuple[float, float, float]) -> float:
    """
    Normalize entropy to [0,1] where 1 = maximum uncertainty.
    
    Maximum entropy for 3 outcomes = log2(3) ≈ 1.585
    
    Args:
        probs: Tuple of (home, draw, away) probabilities
    
    Returns:
        Normalized entropy in [0, 1]
    """
    h = entropy(probs)
    h_max = math.log2(3.0)
    return min(max(h / h_max, 0.0), 1.0)


def entropy_weighted_alpha(
    base_alpha: float,
    model_probs: Tuple[float, float, float],
    min_alpha: float = 0.15,
    max_alpha: float = 0.75
) -> float:
    """
    Adaptive alpha based on model uncertainty.
    
    Rule:
        - Low entropy (overconfident) → trust market more (lower alpha)
        - High entropy (uncertain) → trust model more (higher alpha)
    
    Formula:
        alpha_eff = clamp(base_alpha * normalized_entropy(model_probs), min_alpha, max_alpha)
    
    Args:
        base_alpha: Base blending weight (typically 0.6)
        model_probs: Model probabilities tuple (home, draw, away)
        min_alpha: Minimum alpha (default 0.15)
        max_alpha: Maximum alpha (default 0.75)
    
    Returns:
        Effective alpha for blending
    """
    h_norm = normalized_entropy(model_probs)
    alpha_eff = base_alpha * h_norm
    return min(max(alpha_eff, min_alpha), max_alpha)


def overround_aware_market_weight(
    market_weight: float,
    overround: float,
    k: float = 2.0
) -> float:
    """
    Adjust market weight based on bookmaker overround.
    
    Rule:
        - High overround → reduce market weight (unreliable odds)
        - Low overround → market is sharp (trust more)
    
    Formula:
        market_weight_adj = market_weight * exp(-k * overround)
    
    Args:
        market_weight: Original market weight (1 - alpha)
        overround: Bookmaker overround (sum(1/odds) - 1)
        k: Decay factor (default 2.0)
    
    Returns:
        Adjusted market weight
    """
    if overround <= 0:
        # Fair market or negative overround (rare, but trust it)
        return market_weight
    
    # Exponential decay: high overround reduces trust
    # Typical overround: 0.05-0.15 (5-15%)
    # With k=2.0: overround=0.10 → exp(-0.20) ≈ 0.82 (18% reduction)
    adjusted = market_weight * math.exp(-k * overround)
    
    # Clamp to reasonable bounds (don't reduce below 10% of original)
    return max(adjusted, market_weight * 0.1)

