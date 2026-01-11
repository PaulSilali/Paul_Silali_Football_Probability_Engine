"""
EV-Weighted Scoring Module
===========================

Implements Unified Decision Score (UDS) with EV-weighting, confidence adjustment,
and structural penalties.
"""
from typing import Dict, Any
import math


def xg_confidence(xg_home: float, xg_away: float) -> float:
    """
    Calculate confidence factor based on xG variance.
    
    Lower variance (closer xG values) = higher confidence.
    
    Args:
        xg_home: Expected goals for home team
        xg_away: Expected goals for away team
    
    Returns:
        Confidence factor between 0 and 1
    """
    if xg_home is None or xg_away is None:
        return 0.5  # Default confidence if xG unavailable
    
    xg_diff = abs(xg_home - xg_away)
    return 1.0 / (1.0 + xg_diff)


def pick_decision_value(
    model_prob: float,
    market_odds: float,
    confidence: float,
    structural_penalty: float,
    is_hard_contradiction: bool,
    market_disagreement_penalty: float = 0.0
) -> float:
    """
    Calculate Pick Decision Value (PDV) for a single pick.
    
    Formula:
        EV = p * (o - 1) - (1 - p)
        DEV = EV / (1 + o)
        CEV = DEV * c
        SDV = CEV - s - mdp
        PDV = -∞ if hard_contradiction else SDV
    
    Args:
        model_prob: Model probability for chosen outcome
        market_odds: Market odds for chosen outcome
        confidence: Confidence factor (0-1)
        structural_penalty: Structural penalty (>= 0)
        is_hard_contradiction: Hard contradiction flag
        market_disagreement_penalty: Market disagreement penalty (>= 0)
    
    Returns:
        Pick Decision Value (PDV), or -infinity if hard contradiction
    """
    if is_hard_contradiction:
        return float('-inf')
    
    # Raw Expected Value
    ev = model_prob * (market_odds - 1) - (1 - model_prob)
    
    # Odds-Damped EV
    dev = ev / (1 + market_odds)
    
    # Confidence-Adjusted EV
    cev = dev * confidence
    
    # Structural Decision Value (with market disagreement penalty)
    sdv = cev - structural_penalty - market_disagreement_penalty
    
    return sdv


def unified_decision_score(
    picks: list[Dict[str, Any]],
    entropy_penalty: float = 0.05,
    contradiction_penalty: float = 10.0
) -> tuple[float, int]:
    """
    Calculate Unified Decision Score (UDS) for a ticket.
    
    Formula:
        UDS = Σ(w_L * PDV) - λ * Contradictions - μ * Entropy
    
    Args:
        picks: List of pick dictionaries with:
            - model_prob: Model probability
            - market_odds: Market odds
            - confidence: Confidence factor
            - structural_penalty: Structural penalty
            - league_weight: League reliability weight
            - is_hard_contradiction: Hard contradiction flag
        entropy_penalty: Entropy penalty coefficient (mu)
        contradiction_penalty: Hard penalty for contradictions (lambda)
    
    Returns:
        Tuple of (UDS score, number of contradictions)
    """
    uds = 0.0
    contradictions = 0
    draw_count = 0
    
    for pick in picks:
        # Check for hard contradiction
        if pick.get('is_hard_contradiction', False):
            contradictions += 1
            # Hard contradictions kill the ticket
            return float('-inf'), contradictions
        
        # Calculate PDV (with market disagreement penalty)
        pdv = pick_decision_value(
            model_prob=pick['model_prob'],
            market_odds=pick['market_odds'],
            confidence=pick.get('confidence', 0.5),
            structural_penalty=pick.get('structural_penalty', 0.0),
            is_hard_contradiction=False,
            market_disagreement_penalty=pick.get('market_disagreement_penalty', 0.0)
        )
        
        # Apply league weight
        league_weight = pick.get('league_weight', 1.0)
        uds += league_weight * pdv
        
        # Count draws for entropy
        if pick.get('pick') == 'X':
            draw_count += 1
    
    # Calculate entropy penalty
    total_picks = len(picks)
    if total_picks > 0:
        entropy = draw_count / total_picks
        uds -= entropy_penalty * entropy
    
    return uds, contradictions


def ev_weighted_score(
    model_prob: float,
    market_odds: float,
    confidence: float,
    structural_penalty: float
) -> float:
    """
    Legacy function name for backward compatibility.
    Delegates to pick_decision_value.
    """
    return pick_decision_value(
        model_prob=model_prob,
        market_odds=market_odds,
        confidence=confidence,
        structural_penalty=structural_penalty,
        is_hard_contradiction=False
    )

