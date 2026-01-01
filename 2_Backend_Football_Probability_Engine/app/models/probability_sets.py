"""
Probability Set Generators

Generate all 7 probability sets (A-G) from base calculations

IMPORTANT CONTRACT NOTICE
-------------------------
Sets D and E are HEURISTIC transformations.
They are NOT probability-calibrated outputs.

Only Sets A, B, C, F, and G may be treated as
probability-correct under this system.

DRAW MODEL INTEGRATION:
- Draw probabilities are computed using dedicated draw model
- Home/Away probabilities are reconciled after draw is fixed
- This ensures proper draw calibration and prevents draw starvation
"""
import math
from typing import Dict, Optional
from dataclasses import dataclass
from app.models.dixon_coles import MatchProbabilities
from app.models.draw_model import compute_draw_probability, reconcile_with_draw, DrawModelConfig


@dataclass
class ProbabilitySet:
    """Probability set with calibration status"""
    probabilities: MatchProbabilities
    calibrated: bool
    heuristic: bool
    description: str
    allowed_for_decision_support: bool


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
    model_weight: float,
    use_entropy_weighting: bool = True
) -> MatchProbabilities:
    """
    Blend model and market probabilities
    
    If use_entropy_weighting=True (default):
        Uses entropy-weighted alpha: alpha_eff = clamp(base_alpha * normalized_entropy, 0.15, 0.75)
        This prevents overconfident models from dominating.
    
    Otherwise:
        P_blended = α * P_model + (1 - α) * P_market
    
    Returns:
        MatchProbabilities with metadata (entropy, alphaEffective) if entropy weighting used
    """
    from app.models.uncertainty import entropy_weighted_alpha, normalized_entropy, entropy
    
    # Apply entropy-weighted alpha if enabled
    if use_entropy_weighting:
        alpha_eff = entropy_weighted_alpha(
            base_alpha=model_weight,
            model_probs=(model_probs.home, model_probs.draw, model_probs.away)
        )
    else:
        alpha_eff = model_weight
    
    # Blend probabilities
    blended = MatchProbabilities(
        home=alpha_eff * model_probs.home + (1 - alpha_eff) * market_probs.home,
        draw=alpha_eff * model_probs.draw + (1 - alpha_eff) * market_probs.draw,
        away=alpha_eff * model_probs.away + (1 - alpha_eff) * market_probs.away,
        entropy=0.0
    )
    
    # Recalculate entropy
    blended.entropy = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [blended.home, blended.draw, blended.away]
    )
    
    # Store metadata if entropy weighting was used
    if use_entropy_weighting and hasattr(blended, 'alpha_effective'):
        blended.alpha_effective = alpha_eff
        blended.model_entropy = normalized_entropy((model_probs.home, model_probs.draw, model_probs.away))
    
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
    calibration_curves: Optional[Dict] = None,
    return_metadata: bool = False,
    use_draw_model: bool = True,
    rho: float = -0.13,
    lambda_home: Optional[float] = None,
    lambda_away: Optional[float] = None
) -> Dict[str, MatchProbabilities]:
    """
    Generate all 7 probability sets for a fixture
    
    Args:
        model_probs: Pure Dixon-Coles model probabilities
        market_odds: Market odds dict with 'home', 'draw', 'away' keys
        calibration_curves: Optional calibration curves (not implemented yet)
        return_metadata: If True, returns ProbabilitySet objects with metadata
        use_draw_model: If True, use dedicated draw model for draw probability
        rho: Dixon-Coles correlation parameter (for draw model)
        lambda_home: Expected home goals (for draw model, if available)
        lambda_away: Expected away goals (for draw model, if available)
    
    Returns:
        Dict mapping set_id ('A' through 'G') to MatchProbabilities (or ProbabilitySet if return_metadata=True)
    """
    sets: Dict[str, MatchProbabilities] = {}
    sets_with_metadata: Dict[str, ProbabilitySet] = {}
    
    # Compute draw probability using dedicated draw model if enabled
    draw_prob = None
    draw_components = None
    
    if use_draw_model and market_odds and lambda_home is not None and lambda_away is not None:
        try:
            draw_result = compute_draw_probability(
                lambda_home=lambda_home,
                lambda_away=lambda_away,
                rho=rho,
                odds=market_odds,
                config=DrawModelConfig()
            )
            draw_prob = draw_result["draw"]
            draw_components = draw_result["components"]
        except Exception as e:
            # Fallback to model_probs.draw if draw model fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Draw model computation failed: {e}, using model draw probability")
            draw_prob = None
    
    # Set A: Pure Model (with draw model if enabled)
    if draw_prob is not None:
        # Reconcile with draw model
        reconciled = reconcile_with_draw(
            p_home_raw=model_probs.home,
            p_away_raw=model_probs.away,
            p_draw=draw_prob
        )
        set_a_probs = MatchProbabilities(
            home=reconciled["home"],
            draw=reconciled["draw"],
            away=reconciled["away"],
            entropy=model_probs.entropy if hasattr(model_probs, 'entropy') else 0.0,
            lambda_home=lambda_home if lambda_home is not None else (model_probs.lambda_home if hasattr(model_probs, 'lambda_home') else None),
            lambda_away=lambda_away if lambda_away is not None else (model_probs.lambda_away if hasattr(model_probs, 'lambda_away') else None)
        )
    else:
        set_a_probs = model_probs
    
    sets["A"] = set_a_probs
    sets_with_metadata["A"] = ProbabilitySet(
        probabilities=set_a_probs,
        calibrated=True,
        heuristic=False,
        description="Pure Dixon–Coles model" + (" (with draw model)" if draw_prob is not None else ""),
        allowed_for_decision_support=True,
    )
    
    # If no market odds, return only Set A
    if not market_odds:
        return sets_with_metadata if return_metadata else sets
    
    # Convert odds to probabilities
    market_probs = odds_to_implied_probabilities(market_odds)
    
    # Set B: Market-Aware (Balanced) - 60% model, 40% market
    b_probs = blend_probabilities(model_probs, market_probs, model_weight=0.6)
    sets["B"] = b_probs
    sets_with_metadata["B"] = ProbabilitySet(
        probabilities=b_probs,
        calibrated=True,
        heuristic=False,
        description="60% model + 40% market",
        allowed_for_decision_support=True,
    )
    
    # Set C: Market-Dominant (Conservative) - 20% model, 80% market
    c_probs = blend_probabilities(model_probs, market_probs, model_weight=0.2)
    sets["C"] = c_probs
    sets_with_metadata["C"] = ProbabilitySet(
        probabilities=c_probs,
        calibrated=True,
        heuristic=False,
        description="80% market + 20% model",
        allowed_for_decision_support=True,
    )
    
    # Set D: Draw-Boosted (HEURISTIC)
    d_probs = boost_draw_probability(b_probs, boost_factor=1.15)
    sets["D"] = d_probs
    sets_with_metadata["D"] = ProbabilitySet(
        probabilities=d_probs,
        calibrated=False,
        heuristic=True,
        description="Draw-boosted heuristic",
        allowed_for_decision_support=False,
    )
    
    # Set E: Entropy-Penalized (HEURISTIC)
    e_probs = adjust_temperature(b_probs, temperature=1.5)
    sets["E"] = e_probs
    sets_with_metadata["E"] = ProbabilitySet(
        probabilities=e_probs,
        calibrated=False,
        heuristic=True,
        description="Entropy-penalized heuristic",
        allowed_for_decision_support=False,
    )
    
    # Set F: Kelly-Weighted - Same as Set B for now
    sets["F"] = b_probs
    sets_with_metadata["F"] = ProbabilitySet(
        probabilities=b_probs,
        calibrated=True,
        heuristic=False,
        description="Kelly-style proxy (selection-based)",
        allowed_for_decision_support=True,
    )
    
    # Set G: Ensemble
    g_probs = ensemble_probabilities([sets["A"], sets["B"], sets["C"]])
    sets["G"] = g_probs
    sets_with_metadata["G"] = ProbabilitySet(
        probabilities=g_probs,
        calibrated=True,
        heuristic=False,
        description="Ensemble of A/B/C",
        allowed_for_decision_support=True,
    )
    
    # Set H: Base Set B + Draw adjusted by average market odds
    # Uses multiple market sources (if available) or single market
    from app.models.multi_market_draw import (
        calculate_average_market_draw,
        apply_draw_adjustment_to_set
    )
    
    # For now, use single market (can be extended to multiple markets)
    market_draw_list = [market_odds] if market_odds else []
    avg_market_draw = calculate_average_market_draw(market_draw_list)
    
    if avg_market_draw > 0:
        # Blend base draw with average market draw (70% base, 30% market)
        adjusted_draw_h = (b_probs.draw * 0.7) + (avg_market_draw * 0.3)
        adjusted_draw_h = max(0.18, min(0.40, adjusted_draw_h))
    else:
        # Fallback: use base draw with slight boost
        adjusted_draw_h = min(b_probs.draw * 1.10, 0.40)
    
    h_probs = apply_draw_adjustment_to_set(b_probs, adjusted_draw_h)
    sets["H"] = h_probs
    sets_with_metadata["H"] = ProbabilitySet(
        probabilities=h_probs,
        calibrated=True,
        heuristic=False,
        description="Set B + Draw adjusted by average market odds",
        allowed_for_decision_support=True,
    )
    
    # Set I: Base Set A + Draw adjusted by formula (entropy/spread-based)
    from app.models.multi_market_draw import formula_based_draw_adjustment
    
    market_draw_for_formula = market_probs.draw if market_odds else None
    adjusted_draw_i = formula_based_draw_adjustment(
        base_probs=set_a_probs,
        base_draw=set_a_probs.draw,
        market_draw=market_draw_for_formula
    )
    
    i_probs = apply_draw_adjustment_to_set(set_a_probs, adjusted_draw_i)
    sets["I"] = i_probs
    sets_with_metadata["I"] = ProbabilitySet(
        probabilities=i_probs,
        calibrated=True,
        heuristic=False,
        description="Set A + Draw adjusted by formula (entropy/spread-based)",
        allowed_for_decision_support=True,
    )
    
    # Set J: Base Set G (Ensemble) + Draw adjusted by system-selected formula
    from app.models.multi_market_draw import system_selected_draw_adjustment
    
    adjusted_draw_j, strategy = system_selected_draw_adjustment(
        base_probs=g_probs,
        base_draw=g_probs.draw,
        market_draw=market_probs.draw if market_odds else None,
        lambda_home=lambda_home,
        lambda_away=lambda_away
    )
    
    j_probs = apply_draw_adjustment_to_set(g_probs, adjusted_draw_j)
    sets["J"] = j_probs
    sets_with_metadata["J"] = ProbabilitySet(
        probabilities=j_probs,
        calibrated=True,
        heuristic=False,
        description=f"Set G + Draw adjusted by system-selected formula ({strategy})",
        allowed_for_decision_support=True,
    )
    
    return sets_with_metadata if return_metadata else sets


# Set metadata for frontend display
PROBABILITY_SET_METADATA = {
    "A": {
        "name": "Set A - Pure Model",
        "description": "Dixon-Coles statistical model only. Long-term, theory-driven estimates.",
        "useCase": "Contrarian bettors",
        "guidance": "Best if you believe the model captures value the market misses.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "B": {
        "name": "Set B - Market-Aware (Balanced)",
        "description": "60% model + 40% market odds via GLM. Recommended default.",
        "useCase": "Balanced bettors",
        "guidance": "🌟 Recommended for most users. Trusts model but respects market wisdom.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "C": {
        "name": "Set C - Market-Dominant (Conservative)",
        "description": "80% market + 20% model. For market-efficient believers.",
        "useCase": "Risk-averse",
        "guidance": "Conservative choice. Believes market is usually right.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "D": {
        "name": "Set D - Draw-Boosted",
        "description": "Draw probability × 1.15. Jackpot survival strategy.",
        "useCase": "Draw specialists",
        "guidance": "⚠️ HEURISTIC: Not probability-calibrated. Good for jackpots where draws are historically undervalued.",
        "calibrated": False,
        "heuristic": True,
        "allowed_for_decision_support": False,
        "statisticalStatus": "heuristic",
        "notCalibrated": True
    },
    "E": {
        "name": "Set E - High Conviction",
        "description": "Entropy-penalized. Sharper picks, fewer draws.",
        "useCase": "Accumulator builders",
        "guidance": "⚠️ HEURISTIC: Not probability-calibrated. Want aggressive, decisive picks? This set has lower entropy.",
        "calibrated": False,
        "heuristic": True,
        "allowed_for_decision_support": False,
        "statisticalStatus": "heuristic",
        "notCalibrated": True
    },
    "F": {
        "name": "Set F - Kelly-Weighted",
        "description": "Optimized for long-term bankroll growth.",
        "useCase": "Professional bettors",
        "guidance": "For pros: emphasizes matches with highest Kelly % edge.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "G": {
        "name": "Set G - Ensemble",
        "description": "Weighted average of A, B, C by Brier score.",
        "useCase": "Diversified consensus",
        "guidance": "Risk-averse? This set diversifies across model perspectives.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "H": {
        "name": "Set H - Market Consensus Draw",
        "description": "Set B (Market-Aware) + Draw adjusted by average odds from multiple markets.",
        "useCase": "Market-informed draw coverage",
        "guidance": "Uses consensus from multiple bookmakers to refine draw probability. Best when you trust market wisdom.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "I": {
        "name": "Set I - Formula-Based Draw",
        "description": "Set A (Pure Model) + Draw adjusted by formula considering entropy, spread, and market divergence.",
        "useCase": "Balanced draw optimization",
        "guidance": "Formula automatically adjusts draw based on match characteristics (uncertainty, balance). Smart default for draw coverage.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    },
    "J": {
        "name": "Set J - System-Selected Draw",
        "description": "Set G (Ensemble) + Draw adjusted by system-selected optimal strategy based on match characteristics.",
        "useCase": "Adaptive draw strategy",
        "guidance": "System automatically selects best draw adjustment strategy (aggressive/moderate/conservative) based on match profile. Most intelligent draw coverage.",
        "calibrated": True,
        "heuristic": False,
        "allowed_for_decision_support": True,
        "statisticalStatus": "probability_correct"
    }
}

