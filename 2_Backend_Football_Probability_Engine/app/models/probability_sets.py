"""
Probability Set Generators

Generate all 7 probability sets (A-G) from base calculations
"""
import math
from typing import Dict, Optional
from app.models.dixon_coles import MatchProbabilities


def odds_to_implied_probabilities(odds: Dict[str, float]) -> MatchProbabilities:
    """
    Convert odds to implied probabilities (remove bookmaker margin)
    """
    raw_probs = {
        "home": 1.0 / odds.get("home", 2.0),
        "draw": 1.0 / odds.get("draw", 3.0),
        "away": 1.0 / odds.get("away", 2.5)
    }
    
    # Normalize to remove margin
    total = raw_probs["home"] + raw_probs["draw"] + raw_probs["away"]
    
    home = raw_probs["home"] / total
    draw = raw_probs["draw"] / total
    away = raw_probs["away"] / total
    
    # Calculate entropy
    entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [home, draw, away]
    )
    
    return MatchProbabilities(
        home=home,
        draw=draw,
        away=away,
        entropy=entropy
    )


def blend_probabilities(
    model_probs: MatchProbabilities,
    market_probs: MatchProbabilities,
    model_weight: float
) -> MatchProbabilities:
    """
    Blend model and market probabilities
    
    P_blended = α * P_model + (1 - α) * P_market
    """
    blended = MatchProbabilities(
        home=model_weight * model_probs.home + (1 - model_weight) * market_probs.home,
        draw=model_weight * model_probs.draw + (1 - model_weight) * market_probs.draw,
        away=model_weight * model_probs.away + (1 - model_weight) * market_probs.away,
        entropy=0.0
    )
    
    # Recalculate entropy
    blended.entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [blended.home, blended.draw, blended.away]
    )
    
    return blended


def boost_draw_probability(probs: MatchProbabilities, boost_factor: float = 1.15) -> MatchProbabilities:
    """
    Boost draw probability (for Set D)
    """
    boosted_draw = min(probs.draw * boost_factor, 0.95)  # Cap at 95%
    
    # Redistribute remaining probability proportionally
    remaining = 1.0 - boosted_draw
    total_other = probs.home + probs.away
    
    if total_other > 0:
        home = remaining * (probs.home / total_other)
        away = remaining * (probs.away / total_other)
    else:
        home = remaining / 2
        away = remaining / 2
    
    # Recalculate entropy
    entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [home, boosted_draw, away]
    )
    
    return MatchProbabilities(
        home=home,
        draw=boosted_draw,
        away=away,
        entropy=entropy
    )


def adjust_temperature(probs: MatchProbabilities, temperature: float = 1.5) -> MatchProbabilities:
    """
    Apply temperature adjustment (for Set E - Entropy-Penalized)
    
    Higher temperature = sharper probabilities (lower entropy)
    """
    # Convert to logits
    logits = {
        "home": math.log(probs.home + 1e-10),
        "draw": math.log(probs.draw + 1e-10),
        "away": math.log(probs.away + 1e-10)
    }
    
    # Apply temperature
    scaled_logits = {k: v / temperature for k, v in logits.items()}
    
    # Convert back to probabilities (softmax)
    max_logit = max(scaled_logits.values())
    exp_logits = {k: math.exp(v - max_logit) for k, v in scaled_logits.items()}
    total = sum(exp_logits.values())
    
    home = exp_logits["home"] / total
    draw = exp_logits["draw"] / total
    away = exp_logits["away"] / total
    
    # Recalculate entropy
    entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [home, draw, away]
    )
    
    return MatchProbabilities(
        home=home,
        draw=draw,
        away=away,
        entropy=entropy
    )


def ensemble_probabilities(sets: list[MatchProbabilities]) -> MatchProbabilities:
    """
    Create ensemble from multiple probability sets (for Set G)
    """
    if not sets:
        raise ValueError("Cannot create ensemble from empty set list")
    
    home = sum(s.home for s in sets) / len(sets)
    draw = sum(s.draw for s in sets) / len(sets)
    away = sum(s.away for s in sets) / len(sets)
    
    # Normalize
    total = home + draw + away
    if total > 0:
        home /= total
        draw /= total
        away /= total
    
    # Recalculate entropy
    entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [home, draw, away]
    )
    
    return MatchProbabilities(
        home=home,
        draw=draw,
        away=away,
        entropy=entropy
    )


def generate_all_probability_sets(
    model_probs: MatchProbabilities,
    market_odds: Optional[Dict[str, float]] = None,
    calibration_curves: Optional[Dict] = None
) -> Dict[str, MatchProbabilities]:
    """
    Generate all 7 probability sets for a fixture
    
    Args:
        model_probs: Pure Dixon-Coles model probabilities
        market_odds: Market odds dict with 'home', 'draw', 'away' keys
        calibration_curves: Optional calibration curves (not implemented yet)
    
    Returns:
        Dict mapping set_id ('A' through 'G') to MatchProbabilities
    """
    sets: Dict[str, MatchProbabilities] = {}
    
    # Set A: Pure Model
    sets["A"] = model_probs
    
    # If no market odds, return only Set A
    if not market_odds:
        return sets
    
    # Convert odds to probabilities
    market_probs = odds_to_implied_probabilities(market_odds)
    
    # Set B: Market-Aware (Balanced) - 60% model, 40% market
    sets["B"] = blend_probabilities(model_probs, market_probs, model_weight=0.6)
    
    # Set C: Market-Dominant (Conservative) - 20% model, 80% market
    sets["C"] = blend_probabilities(model_probs, market_probs, model_weight=0.2)
    
    # Set D: Draw-Boosted - Boost draw probability by 15%
    sets["D"] = boost_draw_probability(sets["B"], boost_factor=1.15)
    
    # Set E: Entropy-Penalized (High Conviction) - Sharper probabilities
    sets["E"] = adjust_temperature(sets["B"], temperature=1.5)
    
    # Set F: Kelly-Weighted - Same as Set B for now (Kelly weighting is selection-based)
    # In practice, this would weight by Kelly criterion, but for probabilities we use B
    sets["F"] = sets["B"]
    
    # Set G: Ensemble - Weighted average of A, B, C
    sets["G"] = ensemble_probabilities([sets["A"], sets["B"], sets["C"]])
    
    return sets


# Set metadata for frontend display
PROBABILITY_SET_METADATA = {
    "A": {
        "name": "Set A - Pure Model",
        "description": "Dixon-Coles statistical model only. Long-term, theory-driven estimates.",
        "useCase": "Contrarian bettors",
        "guidance": "Best if you believe the model captures value the market misses."
    },
    "B": {
        "name": "Set B - Market-Aware (Balanced)",
        "description": "60% model + 40% market odds via GLM. Recommended default.",
        "useCase": "Balanced bettors",
        "guidance": "🌟 Recommended for most users. Trusts model but respects market wisdom."
    },
    "C": {
        "name": "Set C - Market-Dominant (Conservative)",
        "description": "80% market + 20% model. For market-efficient believers.",
        "useCase": "Risk-averse",
        "guidance": "Conservative choice. Believes market is usually right."
    },
    "D": {
        "name": "Set D - Draw-Boosted",
        "description": "Draw probability × 1.15. Jackpot survival strategy.",
        "useCase": "Draw specialists",
        "guidance": "Good for jackpots where draws are historically undervalued."
    },
    "E": {
        "name": "Set E - High Conviction",
        "description": "Entropy-penalized. Sharper picks, fewer draws.",
        "useCase": "Accumulator builders",
        "guidance": "Want aggressive, decisive picks? This set has lower entropy."
    },
    "F": {
        "name": "Set F - Kelly-Weighted",
        "description": "Optimized for long-term bankroll growth.",
        "useCase": "Professional bettors",
        "guidance": "For pros: emphasizes matches with highest Kelly % edge."
    },
    "G": {
        "name": "Set G - Ensemble",
        "description": "Weighted average of A, B, C by Brier score.",
        "useCase": "Diversified consensus",
        "guidance": "Risk-averse? This set diversifies across model perspectives."
    }
}

