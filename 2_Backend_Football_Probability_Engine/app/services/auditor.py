"""
Auditor Diagnostics Service

Provides explainability and diagnostics for ticket generation decisions.
Used for auditing, debugging, and understanding why tickets differ.
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def ticket_diagnostics(
    ticket: Dict,
    fixtures: List[Dict],
    corr_matrix: List[List[float]]
) -> Dict:
    """
    Generate diagnostics for a single ticket.
    
    Args:
        ticket: Ticket dict with 'picks' and 'setKey'
        fixtures: List of fixture dicts
        corr_matrix: Correlation matrix
        
    Returns:
        Dict with diagnostic information
    """
    picks = ticket.get("picks", [])
    set_key = ticket.get("setKey", "UNKNOWN")
    
    draw_count = picks.count("X")
    
    # Count favorites (prob >= 0.65)
    favorites = []
    underdogs = []
    
    for i, pick in enumerate(picks):
        if i < len(fixtures):
            fx = fixtures[i]
            probs = fx.get("probabilities", {})
            max_prob = max(probs.values()) if probs else 0.0
            max_outcome = max(probs, key=probs.get) if probs else None
            
            if max_prob >= 0.65:
                favorites.append({
                    "fixture": i + 1,
                    "outcome": max_outcome,
                    "probability": max_prob,
                    "picked": pick,
                    "hedged": pick != max_outcome
                })
            else:
                underdogs.append({
                    "fixture": i + 1,
                    "picked": pick
                })
    
    # Find correlation conflicts
    correlation_conflicts = []
    n = len(picks)
    for i in range(n):
        for j in range(i + 1, n):
            if corr_matrix[i][j] > 0.7 and picks[i] == picks[j]:
                correlation_conflicts.append({
                    "fixture1": i + 1,
                    "fixture2": j + 1,
                    "correlation": corr_matrix[i][j],
                    "both_picked": picks[i]
                })
    
    # Calculate entropy
    entropy = None
    try:
        from app.models.uncertainty import normalized_entropy
        
        ticket_probs = []
        for i, pick in enumerate(picks):
            if i < len(fixtures):
                fx = fixtures[i]
                probs = fx.get("probabilities", {})
                prob = probs.get(pick, 0.33) if pick in ("1", "X", "2") else 0.33
                ticket_probs.append(prob)
        
        if ticket_probs:
            entropy = normalized_entropy(ticket_probs)
    except Exception as e:
        logger.debug(f"Could not calculate entropy: {e}")
    
    return {
        "setKey": set_key,
        "draw_count": draw_count,
        "favorite_count": len(favorites),
        "underdog_count": len(underdogs),
        "favorites": favorites[:5],  # Limit to first 5 for readability
        "correlation_conflicts": correlation_conflicts,
        "entropy": round(entropy, 4) if entropy is not None else None,
        "constraints_met": {
            "draw_count": draw_count,
            "favorite_count": len(favorites),
            "underdog_count": len(underdogs)
        }
    }


def bundle_diagnostics(
    bundle: Dict,
    fixtures: List[Dict],
    corr_matrix: List[List[float]]
) -> Dict:
    """
    Generate diagnostics for entire ticket bundle.
    
    Args:
        bundle: Bundle dict with 'tickets' list
        fixtures: List of fixture dicts
        corr_matrix: Correlation matrix
        
    Returns:
        Dict with portfolio-level diagnostics
    """
    tickets = bundle.get("tickets", [])
    
    if not tickets:
        return {
            "portfolio_size": 0,
            "tickets": []
        }
    
    # Generate diagnostics for each ticket
    ticket_diags = []
    for ticket in tickets:
        diag = ticket_diagnostics(ticket, fixtures, corr_matrix)
        ticket_diags.append(diag)
    
    # Portfolio-level statistics
    total_draws = sum(t["draw_count"] for t in ticket_diags)
    avg_draws = total_draws / len(ticket_diags) if ticket_diags else 0
    
    total_favorites = sum(t["favorite_count"] for t in ticket_diags)
    avg_favorites = total_favorites / len(ticket_diags) if ticket_diags else 0
    
    total_conflicts = sum(len(t["correlation_conflicts"]) for t in ticket_diags)
    
    # Entropy statistics
    entropies = [t["entropy"] for t in ticket_diags if t["entropy"] is not None]
    avg_entropy = sum(entropies) / len(entropies) if entropies else None
    min_entropy = min(entropies) if entropies else None
    max_entropy = max(entropies) if entropies else None
    
    return {
        "portfolio_size": len(tickets),
        "roles": list(set(t["setKey"] for t in ticket_diags)),
        "statistics": {
            "avg_draws_per_ticket": round(avg_draws, 2),
            "avg_favorites_per_ticket": round(avg_favorites, 2),
            "total_correlation_conflicts": total_conflicts,
            "avg_entropy": round(avg_entropy, 4) if avg_entropy else None,
            "min_entropy": round(min_entropy, 4) if min_entropy else None,
            "max_entropy": round(max_entropy, 4) if max_entropy else None
        },
        "tickets": ticket_diags
    }

