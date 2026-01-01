"""
Coverage Diagnostics Service

Calculates coverage statistics for ticket bundles and provides warnings.
"""
from typing import List, Dict


def coverage_diagnostics(tickets: List[List[str]]) -> Dict:
    """
    Calculate coverage diagnostics for a bundle of tickets.
    
    Args:
        tickets: List of ticket pick arrays (e.g., [["1", "X", "2"], ...])
        
    Returns:
        Dict with coverage percentages and warnings
    """
    if not tickets or len(tickets) == 0:
        return {
            "home_pct": 0.0,
            "draw_pct": 0.0,
            "away_pct": 0.0,
            "warnings": ["No tickets generated"]
        }
    
    total_picks = sum(len(ticket) for ticket in tickets)
    if total_picks == 0:
        return {
            "home_pct": 0.0,
            "draw_pct": 0.0,
            "away_pct": 0.0,
            "warnings": ["No picks in tickets"]
        }
    
    counts = {"1": 0, "X": 0, "2": 0}
    for ticket in tickets:
        for pick in ticket:
            if pick in counts:
                counts[pick] += 1
    
    home_pct = (counts["1"] / total_picks) * 100
    draw_pct = (counts["X"] / total_picks) * 100
    away_pct = (counts["2"] / total_picks) * 100
    
    warnings = []
    
    # Check for zero draw coverage
    if draw_pct < 1.0:
        warnings.append("No draw selections detected. This reduces jackpot coverage in draw-heavy leagues.")
    
    # Check for low draw coverage (< 15%)
    if draw_pct < 15.0:
        warnings.append("Draw coverage is low. Historical jackpot draws are under-represented.")
    
    # Check for very high draw coverage (> 50%)
    if draw_pct > 50.0:
        warnings.append("Draw coverage is very high. Consider diversifying selections.")
    
    # Check for extreme imbalance
    if abs(home_pct - away_pct) > 40.0:
        warnings.append("Significant imbalance between home and away selections.")
    
    return {
        "home_pct": round(home_pct, 1),
        "draw_pct": round(draw_pct, 1),
        "away_pct": round(away_pct, 1),
        "warnings": warnings,
        "total_picks": total_picks,
        "total_tickets": len(tickets)
    }

