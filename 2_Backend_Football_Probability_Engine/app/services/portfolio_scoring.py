"""
Portfolio-Level Correlation & EV Scoring
=========================================

Calculates portfolio-level scores to ensure diverse, non-correlated ticket bundles.
This is the final professional hardening step.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def ticket_correlation(ticket1: Dict[str, Any], ticket2: Dict[str, Any]) -> float:
    """
    Calculate correlation between two tickets based on pick overlap.
    
    Correlation is overlap of risky structure, not exact picks.
    
    Args:
        ticket1: Ticket dictionary with 'picks' list
        ticket2: Ticket dictionary with 'picks' list
    
    Returns:
        Correlation score (0.0 to 1.0), where 1.0 = identical picks
    """
    picks1 = ticket1.get("picks", [])
    picks2 = ticket2.get("picks", [])
    
    if not picks1 or not picks2:
        return 0.0
    
    # Handle both string lists and dict lists
    if isinstance(picks1[0], str):
        # Simple string list: ['1', 'X', '2', ...]
        overlap = sum(1 for p1, p2 in zip(picks1, picks2) if p1 == p2)
        total = max(len(picks1), len(picks2))
    else:
        # Dict list: [{'pick': '1', ...}, ...]
        overlap = 0
        min_len = min(len(picks1), len(picks2))
        for i in range(min_len):
            pick1 = picks1[i].get("pick") if isinstance(picks1[i], dict) else picks1[i]
            pick2 = picks2[i].get("pick") if isinstance(picks2[i], dict) else picks2[i]
            if pick1 == pick2:
                overlap += 1
        total = max(len(picks1), len(picks2))
    
    return overlap / total if total > 0 else 0.0


def portfolio_score(tickets: List[Dict[str, Any]], correlation_penalty_weight: float = 0.2) -> float:
    """
    Calculate portfolio-level score combining EV and correlation penalty.
    
    Args:
        tickets: List of ticket dictionaries with:
            - ev_score: EV score for ticket
            - picks: List of picks
        correlation_penalty_weight: Weight for correlation penalty (default 0.2)
    
    Returns:
        Portfolio score (higher is better)
    """
    if not tickets:
        return 0.0
    
    # Total EV across all tickets
    total_ev = sum(ticket.get("ev_score", 0) or 0 for ticket in tickets)
    
    # Correlation penalty
    corr_penalty = 0.0
    for i in range(len(tickets)):
        for j in range(i + 1, len(tickets)):
            corr = ticket_correlation(tickets[i], tickets[j])
            # Penalize correlations above 0.5 (50% overlap)
            if corr > 0.5:
                corr_penalty += (corr - 0.5) * correlation_penalty_weight
    
    return total_ev - corr_penalty


def select_optimal_bundle(
    candidate_tickets: List[Dict[str, Any]],
    n_tickets: int,
    correlation_penalty_weight: float = 0.2
) -> List[Dict[str, Any]]:
    """
    Select optimal bundle of tickets from candidates.
    
    Uses portfolio scoring to balance:
    - High EV
    - Low correlation
    - Structural diversity
    
    Args:
        candidate_tickets: List of accepted tickets
        n_tickets: Number of tickets to select
        correlation_penalty_weight: Weight for correlation penalty
    
    Returns:
        List of selected tickets (best bundle)
    """
    if len(candidate_tickets) <= n_tickets:
        return candidate_tickets
    
    # Simple greedy selection (can be improved with optimization)
    selected = []
    remaining = candidate_tickets.copy()
    
    # First, select ticket with highest EV
    if remaining:
        best = max(remaining, key=lambda t: t.get("ev_score", 0) or 0)
        selected.append(best)
        remaining.remove(best)
    
    # Then, iteratively add tickets that maximize portfolio score
    for _ in range(min(n_tickets - 1, len(remaining))):
        best_candidate = None
        best_score = float('-inf')
        
        for candidate in remaining:
            # Try adding this candidate
            test_bundle = selected + [candidate]
            score = portfolio_score(test_bundle, correlation_penalty_weight)
            
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        if best_candidate:
            selected.append(best_candidate)
            remaining.remove(best_candidate)
        else:
            break
    
    return selected


def calculate_portfolio_diagnostics(tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate portfolio-level diagnostics.
    
    Args:
        tickets: List of ticket dictionaries
    
    Returns:
        Dictionary with portfolio metrics
    """
    if not tickets:
        return {
            "total_tickets": 0,
            "avg_ev": 0.0,
            "total_ev": 0.0,
            "avg_correlation": 0.0,
            "max_correlation": 0.0,
            "diversity_score": 0.0
        }
    
    total_ev = sum(t.get("ev_score", 0) or 0 for t in tickets)
    avg_ev = total_ev / len(tickets) if tickets else 0.0
    
    # Calculate pairwise correlations
    correlations = []
    for i in range(len(tickets)):
        for j in range(i + 1, len(tickets)):
            corr = ticket_correlation(tickets[i], tickets[j])
            correlations.append(corr)
    
    avg_correlation = sum(correlations) / len(correlations) if correlations else 0.0
    max_correlation = max(correlations) if correlations else 0.0
    
    # Diversity score: inverse of average correlation
    diversity_score = 1.0 - avg_correlation if avg_correlation > 0 else 1.0
    
    return {
        "total_tickets": len(tickets),
        "avg_ev": round(avg_ev, 4),
        "total_ev": round(total_ev, 4),
        "avg_correlation": round(avg_correlation, 4),
        "max_correlation": round(max_correlation, 4),
        "diversity_score": round(diversity_score, 4)
    }

