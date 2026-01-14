"""
Multi-Market Draw Adjustment Module

Provides functions to adjust draw probabilities using:
1. Average odds from multiple markets
2. Formula-based draw adjustments (entropy, spread, etc.)
3. System-selected optimal draw adjustments
"""
import math
from typing import Dict, Optional, List, Tuple
from app.models.dixon_coles import MatchProbabilities
from app.models.uncertainty import entropy, normalized_entropy


def calculate_average_market_draw(
    market_odds_list: List[Dict[str, float]]
) -> float:
    """
    Calculate average draw probability from multiple market sources.
    
    Args:
        market_odds_list: List of market odds dicts [{"home": 2.0, "draw": 3.0, "away": 2.5}, ...]
    
    Returns:
        Average draw probability (0.0 to 1.0)
    """
    if not market_odds_list:
        return 0.0
    
    draw_probs = []
    for odds in market_odds_list:
        if odds.get("draw") and odds["draw"] > 0:
            # Calculate implied probability
            inv_h = 1.0 / odds.get("home", 2.0) if odds.get("home", 0) > 0 else 0
            inv_d = 1.0 / odds["draw"]
            inv_a = 1.0 / odds.get("away", 2.0) if odds.get("away", 0) > 0 else 0
            
            total = inv_h + inv_d + inv_a
            if total > 0:
                draw_probs.append(inv_d / total)
    
    if not draw_probs:
        return 0.0
    
    return sum(draw_probs) / len(draw_probs)


def formula_based_draw_adjustment(
    base_probs: MatchProbabilities,
    base_draw: float,
    market_draw: Optional[float] = None
) -> float:
    """
    Calculate draw adjustment using formula based on match characteristics.
    
    Formula considers:
    - Entropy (uncertainty)
    - Home-Away spread (balance)
    - Model vs Market divergence
    
    Args:
        base_probs: Base probabilities (for entropy/spread calculation)
        base_draw: Base draw probability
        market_draw: Optional market draw probability
    
    Returns:
        Adjusted draw probability (0.0 to 1.0)
    """
    # Calculate entropy
    h = entropy((base_probs.home, base_probs.draw, base_probs.away))
    h_norm = normalized_entropy((base_probs.home, base_probs.draw, base_probs.away))
    
    # Calculate home-away spread
    spread = abs(base_probs.home - base_probs.away)
    
    # Formula: Higher entropy + Lower spread = Higher draw boost
    # Entropy factor: 0.8 to 1.2 (higher entropy = more boost)
    entropy_factor = 0.8 + (h_norm * 0.4)
    
    # Spread factor: 1.0 to 1.3 (lower spread = more boost)
    # Spread of 0% = 1.3x, spread of 50% = 1.0x
    spread_factor = 1.3 - (spread * 0.6)
    spread_factor = max(1.0, min(1.3, spread_factor))
    
    # Market divergence factor (if market draw available)
    market_factor = 1.0
    if market_draw is not None:
        # If market draw is higher than model, boost more
        if market_draw > base_draw:
            market_factor = 1.0 + ((market_draw - base_draw) * 0.5)
        else:
            market_factor = 1.0 - ((base_draw - market_draw) * 0.3)
        market_factor = max(0.8, min(1.2, market_factor))
    
    # Combined adjustment
    adjustment = entropy_factor * spread_factor * market_factor
    
    # Apply adjustment
    adjusted_draw = base_draw * adjustment
    
    # Cap at reasonable bounds
    adjusted_draw = max(0.15, min(0.45, adjusted_draw))
    
    return adjusted_draw


def system_selected_draw_adjustment(
    base_probs: MatchProbabilities,
    base_draw: float,
    market_draw: Optional[float] = None,
    lambda_home: Optional[float] = None,
    lambda_away: Optional[float] = None
) -> Tuple[float, str]:
    """
    System-selected optimal draw adjustment using multiple criteria.
    
    Selects best adjustment strategy based on match characteristics:
    - High entropy + low spread → Aggressive draw boost
    - Balanced match → Moderate draw boost
    - One-sided match → Conservative draw adjustment
    
    Args:
        base_probs: Base probabilities
        base_draw: Base draw probability
        market_draw: Optional market draw probability
        lambda_home: Expected home goals
        lambda_away: Expected away goals
    
    Returns:
        Tuple of (adjusted_draw, strategy_name)
    """
    # Calculate match characteristics
    h_norm = normalized_entropy((base_probs.home, base_probs.draw, base_probs.away))
    spread = abs(base_probs.home - base_probs.away)
    
    # Strategy selection based on characteristics
    if h_norm > 0.85 and spread < 0.10:
        # High uncertainty + balanced → Aggressive boost
        strategy = "aggressive_boost"
        adjustment_factor = 1.25
    elif h_norm > 0.70 and spread < 0.20:
        # Medium uncertainty + balanced → Moderate boost
        strategy = "moderate_boost"
        adjustment_factor = 1.15
    elif spread < 0.15:
        # Low spread (balanced) → Light boost
        strategy = "light_boost"
        adjustment_factor = 1.10
    elif market_draw and market_draw > base_draw * 1.1:
        # Market significantly higher → Trust market
        strategy = "market_trust"
        adjustment_factor = 1.0 + ((market_draw - base_draw) * 0.6)
    else:
        # Default → Conservative
        strategy = "conservative"
        adjustment_factor = 1.05
    
    # Apply adjustment
    adjusted_draw = base_draw * adjustment_factor
    
    # Cap at reasonable bounds
    adjusted_draw = max(0.18, min(0.40, adjusted_draw))
    
    return adjusted_draw, strategy


def apply_draw_adjustment_to_set(
    base_set_probs: MatchProbabilities,
    new_draw: float
) -> MatchProbabilities:
    """
    Apply new draw probability to a probability set, redistributing home/away.
    
    Args:
        base_set_probs: Base probability set
        new_draw: New draw probability to apply
    
    Returns:
        MatchProbabilities with adjusted draw
    """
    # Redistribute remaining probability proportionally
    remaining = 1.0 - new_draw
    total_other = base_set_probs.home + base_set_probs.away
    
    if total_other > 0:
        home = remaining * (base_set_probs.home / total_other)
        away = remaining * (base_set_probs.away / total_other)
    else:
        home = remaining / 2
        away = remaining / 2
    
    # Recalculate entropy
    new_entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [home, new_draw, away]
    )
    
    return MatchProbabilities(
        home=home,
        draw=new_draw,
        away=away,
        entropy=new_entropy,
        lambda_home=getattr(base_set_probs, 'lambda_home', None),
        lambda_away=getattr(base_set_probs, 'lambda_away', None)
    )






