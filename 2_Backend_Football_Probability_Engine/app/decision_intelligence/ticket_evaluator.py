"""
Ticket Evaluator Module
========================

Evaluates tickets using Unified Decision Score and applies hard gating.
"""
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.decision_intelligence.ev_scoring import unified_decision_score, pick_decision_value
from app.decision_intelligence.contradictions import is_hard_contradiction
from app.decision_intelligence.penalties import structural_penalty
from app.decision_intelligence.thresholds import load_thresholds
from app.decision_intelligence.ev_scoring import xg_confidence
from app.decision_intelligence.market_disagreement import (
    calculate_market_disagreement,
    market_disagreement_penalty,
    is_extreme_disagreement,
    get_market_favorite
)
import logging

logger = logging.getLogger(__name__)


def evaluate_ticket(
    ticket_matches: List[Dict[str, Any]],
    db: Optional[Session] = None,
    ev_threshold: Optional[float] = None,
    max_contradictions: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate ticket using Unified Decision Score.
    
    Args:
        ticket_matches: List of match dictionaries with:
            - pick: '1', 'X', or '2'
            - model_prob: Model probability for pick
            - market_odds: Market odds dict or single odds value
            - xg_home: Expected goals home
            - xg_away: Expected goals away
            - league_code: League code for weight lookup
        db: Database session (for loading thresholds/weights)
        ev_threshold: Override EV threshold (uses DB if not provided)
        max_contradictions: Override max contradictions (uses DB if not provided)
    
    Returns:
        Dictionary with:
            - accepted: bool
            - ev_score: float (UDS)
            - contradictions: int
            - picks: List of enriched picks
            - reason: str (rejection reason if not accepted)
    """
    # Load thresholds if not provided
    if db:
        thresholds = load_thresholds(db)
        if ev_threshold is None:
            ev_threshold = thresholds.get('ev_threshold', 0.12)
        if max_contradictions is None:
            max_contradictions = int(thresholds.get('max_contradictions', 1))
        entropy_penalty = thresholds.get('entropy_penalty', 0.05)
        contradiction_penalty = thresholds.get('contradiction_penalty', 10.0)
    else:
        ev_threshold = ev_threshold or 0.12
        max_contradictions = max_contradictions or 1
        entropy_penalty = 0.05
        contradiction_penalty = 10.0
    
    # Load league weights if DB available
    league_weights = {}
    if db:
        try:
            from sqlalchemy import text
            result = db.execute(text("""
                SELECT league_code, weight
                FROM league_reliability_weights
            """))
            for row in result:
                league_weights[row.league_code] = float(row.weight)
        except Exception as e:
            logger.warning(f"Could not load league weights: {e}")
    
    # Enrich picks with decision intelligence data
    enriched_picks = []
    total_contradictions = 0
    
    for match in ticket_matches:
        # Extract pick
        pick = match.get('pick', '')
        if pick not in ['1', 'X', '2']:
            continue
        
        # Get market odds for pick
        market_odds_dict = match.get('market_odds', {})
        if isinstance(market_odds_dict, dict):
            if pick == '1':
                market_odds = market_odds_dict.get('home') or market_odds_dict.get('1')
            elif pick == 'X':
                market_odds = market_odds_dict.get('draw') or market_odds_dict.get('X')
            else:  # pick == '2'
                market_odds = market_odds_dict.get('away') or market_odds_dict.get('2')
        else:
            market_odds = market_odds_dict
        
        if not market_odds or market_odds <= 1.0:
            logger.warning(f"Invalid market odds for pick {pick}: {market_odds}")
            continue
        
        # Get model probability for pick
        model_prob = match.get('model_prob')
        if model_prob is None:
            # Try to get from probability dict
            probs = match.get('probabilities', {})
            if pick == '1':
                model_prob = probs.get('home') or probs.get('1')
            elif pick == 'X':
                model_prob = probs.get('draw') or probs.get('X')
            else:
                model_prob = probs.get('away') or probs.get('2')
        
        if model_prob is None or model_prob <= 0:
            logger.warning(f"Invalid model probability for pick {pick}: {model_prob}")
            continue
        
        # Calculate xG confidence
        xg_home = match.get('xg_home')
        xg_away = match.get('xg_away')
        confidence = xg_confidence(xg_home or 0, xg_away or 0) if xg_home and xg_away else 0.5
        
        # Check for hard contradiction
        hard_contradiction = is_hard_contradiction({
            'pick': pick,
            'market_odds': market_odds_dict,
            'market_prob_home': match.get('market_prob_home'),
            'xg_home': xg_home,
            'xg_away': xg_away
        })
        
        if hard_contradiction:
            total_contradictions += 1
        
        # Calculate structural penalty
        structural_pen = structural_penalty({
            'pick': pick,
            'market_odds': market_odds_dict,
            'xg_home': xg_home,
            'xg_away': xg_away
        })
        
        # Calculate market disagreement penalty
        market_delta = calculate_market_disagreement(model_prob, market_odds)
        market_penalty = market_disagreement_penalty(market_delta)
        
        # Check for extreme disagreement (hard gate)
        market_favorite = get_market_favorite(market_odds_dict)
        if is_extreme_disagreement(model_prob, market_odds, pick, market_favorite):
            hard_contradiction = True
            total_contradictions += 1
        
        # Get league weight
        league_code = match.get('league_code') or match.get('league')
        league_weight = league_weights.get(league_code, 1.0)
        
        # Enrich pick with market disagreement data
        enriched_pick = {
            **match,
            'pick': pick,
            'market_odds': market_odds,
            'model_prob': model_prob,
            'confidence': confidence,
            'structural_penalty': structural_pen,
            'market_disagreement_penalty': market_penalty,
            'market_disagreement_delta': market_delta,
            'league_weight': league_weight,
            'is_hard_contradiction': hard_contradiction,
            'xg_diff': abs((xg_home or 0) - (xg_away or 0))
        }
        
        enriched_picks.append(enriched_pick)
    
    # Calculate UDS
    uds, contradiction_count = unified_decision_score(
        picks=enriched_picks,
        entropy_penalty=entropy_penalty,
        contradiction_penalty=contradiction_penalty
    )
    
    # Decision logic
    if uds == float('-inf'):
        accepted = False
        reason = "Hard contradiction detected - ticket rejected"
    elif contradiction_count > max_contradictions:
        accepted = False
        reason = f"Too many contradictions ({contradiction_count} > {max_contradictions})"
    elif uds < ev_threshold:
        accepted = False
        reason = f"UDS ({uds:.3f}) below threshold ({ev_threshold:.3f})"
    else:
        accepted = True
        reason = "Passed structural validation"
    
    return {
        'accepted': accepted,
        'ev_score': uds,
        'contradictions': contradiction_count,
        'picks': enriched_picks,
        'reason': reason,
        'ev_threshold_used': ev_threshold,
        'max_contradictions_allowed': max_contradictions
    }

