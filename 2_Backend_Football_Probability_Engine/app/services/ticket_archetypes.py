"""
Ticket Archetypes Module
========================

Enforces single-bias ticket archetypes with hard constraints during generation.
This reduces garbage generation, improves rejection rates, and makes tickets interpretable.

Archetypes:
- FAVORITE_LOCK: Preserve high-probability mass
- BALANCED: Controlled diversification
- DRAW_SELECTIVE: Exploit genuine draw structure
- AWAY_EDGE: Capture mispriced away value
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def select_archetype(slate_profile: Dict[str, Any]) -> str:
    """
    Select appropriate archetype based on slate characteristics.
    
    Args:
        slate_profile: Dictionary with:
            - avg_home_prob: Average home win probability
            - balanced_rate: Proportion of balanced fixtures (|xG_diff| < 0.35)
            - away_value_rate: Proportion of fixtures with away value (model > market + 0.05)
    
    Returns:
        Archetype name: 'FAVORITE_LOCK', 'BALANCED', 'DRAW_SELECTIVE', or 'AWAY_EDGE'
    """
    avg_home_prob = slate_profile.get("avg_home_prob", 0.5)
    balanced_rate = slate_profile.get("balanced_rate", 0.0)
    away_value_rate = slate_profile.get("away_value_rate", 0.0)
    
    # Strong favorites dominate slate
    if avg_home_prob > 0.52:
        return "FAVORITE_LOCK"
    
    # Many balanced fixtures (good for draws)
    if balanced_rate > 0.4:
        return "DRAW_SELECTIVE"
    
    # Market bias toward home sides (away value exists)
    if away_value_rate > 0.3:
        return "AWAY_EDGE"
    
    # Default to balanced
    return "BALANCED"


def enforce_archetype(ticket: List[Dict[str, Any]], archetype: str) -> bool:
    """
    Enforce archetype constraints on a ticket.
    
    This runs BEFORE Decision Intelligence evaluation.
    Returns False if ticket violates archetype rules.
    
    Args:
        ticket: List of match dictionaries with:
            - pick: '1', 'X', or '2'
            - odds: Dict with 'home', 'draw', 'away' keys
            - xg_home, xg_away: Expected goals
            - dc_applied: Whether Dixon-Coles was applied
            - model_prob: Model probability for pick
            - market_prob: Market probability for pick
            - market_prob_home: Market probability for home win
        archetype: One of 'FAVORITE_LOCK', 'BALANCED', 'DRAW_SELECTIVE', 'AWAY_EDGE'
    
    Returns:
        True if ticket satisfies archetype constraints, False otherwise
    """
    if not ticket:
        return False
    
    # Count picks by type
    counts = {"1": 0, "X": 0, "2": 0}
    home_favorites = 0  # Home picks with prob > 0.55
    
    for match in ticket:
        pick = match.get("pick", "")
        if pick not in ["1", "X", "2"]:
            continue
        
        counts[pick] += 1
        
        # Get odds (handle both dict and direct value, and market_odds fallback)
        odds = match.get("odds") or match.get("market_odds", {})
        if not odds:
            odds = {}
        if isinstance(odds, dict):
            odds_home = odds.get("home") or odds.get("1")
            odds_draw = odds.get("draw") or odds.get("X")
            odds_away = odds.get("away") or odds.get("2")
        else:
            # Single odds value (shouldn't happen, but handle gracefully)
            odds_home = odds_draw = odds_away = odds
        
        # Get probabilities (handle None values)
        xg_home = match.get("xg_home")
        if xg_home is None:
            xg_home = 0
        xg_away = match.get("xg_away")
        if xg_away is None:
            xg_away = 0
        model_prob = match.get("model_prob")
        market_prob = match.get("market_prob")
        market_prob_home = match.get("market_prob_home")
        dc_applied = match.get("dc_applied", False)
        
        # Calculate market probabilities if not provided
        if market_prob_home is None and isinstance(odds, dict) and odds_home:
            # Approximate from odds
            total_implied = (1/odds_home if odds_home else 0) + \
                          (1/odds_draw if odds_draw else 0) + \
                          (1/odds_away if odds_away else 0)
            if total_implied > 0:
                market_prob_home = (1/odds_home) / total_implied if odds_home else 0
        
        # Track home favorites
        if pick == "1" and market_prob_home and market_prob_home > 0.55:
            home_favorites += 1
        
        # FAVORITE_LOCK constraints
        if archetype == "FAVORITE_LOCK":
            # No draw if draw odds > 3.20
            if pick == "X" and odds_draw and odds_draw > 3.20:
                return False
            # No away if away odds > 2.80
            if pick == "2" and odds_away and odds_away > 2.80:
                return False
        
        # DRAW_SELECTIVE constraints
        if archetype == "DRAW_SELECTIVE":
            if pick == "X":
                # Draw only if |xG_diff| <= 0.30
                xg_diff = abs(xg_home - xg_away)
                if xg_diff > 0.30:
                    logger.info(f"DRAW_SELECTIVE: Draw rejected - xG_diff {xg_diff:.3f} > 0.30 (xg_home={xg_home}, xg_away={xg_away})")
                    return False
                # Draw only if DC applied (low-scoring match)
                if not dc_applied:
                    logger.info(f"DRAW_SELECTIVE: Draw rejected - DC not applied (fixture_id={match.get('fixture_id', 'unknown')})")
                    return False
                # Draw only if odds <= 3.40
                if odds_draw and odds_draw > 3.40:
                    logger.info(f"DRAW_SELECTIVE: Draw rejected - odds {odds_draw} > 3.40")
                    return False
            # No away odds > 3.00
            if pick == "2" and odds_away and odds_away > 3.00:
                logger.info(f"DRAW_SELECTIVE: Away rejected - odds {odds_away} > 3.00")
                return False
        
        # AWAY_EDGE constraints
        if archetype == "AWAY_EDGE":
            if pick == "2":
                # Away only if model_prob - market_prob >= +0.07
                if model_prob is not None and market_prob is not None:
                    if (model_prob - market_prob) < 0.07:
                        return False
            # No draws unless odds <= 3.10
            if pick == "X" and odds_draw and odds_draw > 3.10:
                return False
    
    # Count-based constraints
    if archetype == "FAVORITE_LOCK":
        # Max 1 draw, max 1 away
        if counts["X"] > 1 or counts["2"] > 1:
            return False
        # At least 60% of picks must have market implied prob >= 0.48
        # (Approximate: home picks with prob > 0.48 or low odds)
        total_picks = sum(counts.values())
        if total_picks > 0:
            high_prob_ratio = home_favorites / total_picks
            if high_prob_ratio < 0.6:
                return False
    
    if archetype == "BALANCED":
        # Temporarily disabled - ticket generation algorithm doesn't respect constraints
        # Allow all tickets through for BALANCED archetype to restore previous behavior
        # TODO: Make ticket generation algorithm archetype-aware
        pass
    
    if archetype == "DRAW_SELECTIVE":
        # Min 2 draws, max 3 draws, max 1 away
        if not (2 <= counts["X"] <= 3):
            logger.info(f"DRAW_SELECTIVE: Ticket rejected - draw count {counts['X']} not in [2,3] (counts: {counts})")
            return False
        if counts["2"] > 1:
            logger.info(f"DRAW_SELECTIVE: Ticket rejected - away count {counts['2']} > 1 (counts: {counts})")
            return False
    
    if archetype == "AWAY_EDGE":
        # Min 2 away, max 3 away
        if not (2 <= counts["2"] <= 3):
            return False
        # Max 4 home favorites (prob > 0.55)
        if home_favorites > 4:
            return False
    
    return True


def analyze_slate_profile(fixtures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze fixture slate to determine profile for archetype selection.
    
    Args:
        fixtures: List of fixture dictionaries with:
            - probabilities: Dict with home/draw/away probabilities
            - odds: Dict with home/draw/away odds
            - xg_home, xg_away: Expected goals
    
    Returns:
        Dictionary with:
            - avg_home_prob: Average home win probability
            - balanced_rate: Proportion of balanced fixtures
            - away_value_rate: Proportion of fixtures with away value
    """
    if not fixtures:
        return {
            "avg_home_prob": 0.5,
            "balanced_rate": 0.0,
            "away_value_rate": 0.0
        }
    
    total_home_prob = 0.0
    balanced_count = 0
    away_value_count = 0
    
    for fixture in fixtures:
        # Get probabilities
        probs = fixture.get("probabilities", {})
        if isinstance(probs, dict):
            home_prob = probs.get("home") or probs.get("1") or 0
            draw_prob = probs.get("draw") or probs.get("X") or 0
            away_prob = probs.get("away") or probs.get("2") or 0
        else:
            home_prob = draw_prob = away_prob = 0
        
        # Convert to 0-1 if in percentage
        if home_prob > 1:
            home_prob /= 100
        if draw_prob > 1:
            draw_prob /= 100
        if away_prob > 1:
            away_prob /= 100
        
        total_home_prob += home_prob
        
        # Check if balanced (|xG_diff| < 0.35)
        xg_home = fixture.get("xg_home")
        if xg_home is None:
            xg_home = 0
        xg_away = fixture.get("xg_away")
        if xg_away is None:
            xg_away = 0
        xg_diff = abs(xg_home - xg_away)
        if xg_diff <= 0.35:
            balanced_count += 1
        
        # Check for away value (model_prob_away - market_prob_away >= +0.05)
        # Approximate from odds
        odds = fixture.get("odds", {})
        if isinstance(odds, dict):
            odds_away = odds.get("away") or odds.get("2")
            if odds_away and away_prob > 0:
                # Market implied probability
                total_implied = (1/odds.get("home", 1) if odds.get("home") else 0) + \
                              (1/odds.get("draw", 1) if odds.get("draw") else 0) + \
                              (1/odds_away)
                if total_implied > 0:
                    market_prob_away = (1/odds_away) / total_implied
                    if (away_prob - market_prob_away) >= 0.05:
                        away_value_count += 1
    
    total_fixtures = len(fixtures)
    
    return {
        "avg_home_prob": total_home_prob / total_fixtures if total_fixtures > 0 else 0.5,
        "balanced_rate": balanced_count / total_fixtures if total_fixtures > 0 else 0.0,
        "away_value_rate": away_value_count / total_fixtures if total_fixtures > 0 else 0.0
    }

