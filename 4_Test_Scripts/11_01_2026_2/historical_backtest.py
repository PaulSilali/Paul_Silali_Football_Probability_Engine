"""
Historical Backtest Script
============================

Tests Decision Intelligence effectiveness using historical jackpot results.

This script:
1. Loads historical match results
2. Generates tickets with and without Decision Intelligence
3. Scores tickets against actual results
4. Compares baseline vs DI performance
"""
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

# Historical results provided by user
HISTORICAL_RESULTS = {
    1: "D", 2: "H", 3: "D", 4: "A", 5: "A", 6: "H", 7: "H", 8: "D", 9: "H", 10: "A",
    11: "D", 12: "H", 13: "H", 14: "A", 15: "H", 16: "D", 17: "H", 18: "D", 19: "H", 20: "A",
    21: "H", 22: "H", 23: "D", 24: "H", 25: "D", 26: "D", 27: "H", 28: "H", 29: "D", 30: "H",
    31: "H", 32: "A", 33: "A", 34: "H", 35: "D", 36: "A", 37: "H", 38: "A", 39: "H", 40: "H",
    41: "A", 42: "D", 43: "A", 44: "D", 45: "A", 46: "A", 47: "H", 48: "H", 49: "H", 50: "H",
    51: "D", 52: "A", 53: "H", 54: "D", 55: "D", 56: "H", 57: "D", 58: "H", 59: "H", 60: "H",
    61: "H", 62: "A", 63: "A", 64: "A", 65: "A", 66: "H", 67: "A", 68: "A", 69: "A", 70: "H",
    71: "A", 72: "H", 73: "D", 74: "H", 75: "A"
}

# Match details (for reference - we'll need to map these to fixture IDs)
HISTORICAL_MATCHES = [
    {"id": 1, "home": "Union Berlin", "away": "Freiburg", "result": "D"},
    {"id": 2, "home": "Leipzig", "away": "Stuttgart", "result": "H"},
    {"id": 3, "home": "Nottingham", "away": "Man United", "result": "D"},
    {"id": 4, "home": "Norrkoping FK", "away": "IK Sirius", "result": "A"},
    {"id": 5, "home": "Tottenham", "away": "Chelsea", "result": "A"},
    {"id": 6, "home": "Real Sociedad", "away": "Athletic Bilbao", "result": "H"},
    {"id": 7, "home": "NAC Breda", "away": "Go Ahead Eagles", "result": "H"},
    {"id": 8, "home": "SC Telstar", "away": "Excelsior Rotterdam", "result": "D"},
    {"id": 9, "home": "Heracles Almelo", "away": "PEC Zwolle", "result": "H"},
    {"id": 10, "home": "Levante", "away": "Celta Vigo", "result": "A"},
    {"id": 11, "home": "FC Groningen", "away": "FC Twente", "result": "D"},
    {"id": 12, "home": "Alaves", "away": "Espanyol", "result": "H"},
    {"id": 13, "home": "SK Rapid", "away": "SK Sturm Graz", "result": "H"},
    {"id": 14, "home": "Wolfsburg", "away": "Hoffenheim", "result": "A"},
    {"id": 15, "home": "FK Krasnodar", "away": "FK Spartak Moscow", "result": "H"},
    {"id": 16, "home": "Tottenham", "away": "Man United", "result": "D"},
    {"id": 17, "home": "Girona", "away": "Alaves", "result": "H"},
    {"id": 18, "home": "US Lecce", "away": "Hellas Verona", "result": "D"},
    {"id": 19, "home": "Hoffenheim", "away": "Leipzig", "result": "H"},
    {"id": 20, "home": "Espanyol", "away": "Villarreal", "result": "A"},
    {"id": 21, "home": "Brentford", "away": "Newcastle", "result": "H"},
    {"id": 22, "home": "Nottingham", "away": "Leeds", "result": "H"},
    {"id": 23, "home": "Crystal Palace", "away": "Brighton", "result": "D"},
    {"id": 24, "home": "Bologna", "away": "Napoli", "result": "H"},
    {"id": 25, "home": "Genoa", "away": "ACF Fiorentina", "result": "D"},
    {"id": 26, "home": "Lorient", "away": "Toulouse", "result": "D"},
    {"id": 27, "home": "Angers", "away": "Auxerre", "result": "H"},
    {"id": 28, "home": "Strasbourg", "away": "Lille", "result": "H"},
    {"id": 29, "home": "Valencia", "away": "Betis", "result": "D"},
    {"id": 30, "home": "Mallorca", "away": "Getafe", "result": "H"},
    {"id": 31, "home": "Augsburg", "away": "Hamburg", "result": "H"},
    {"id": 32, "home": "Wolfsburg", "away": "Leverkusen", "result": "A"},
    {"id": 33, "home": "Heidenheim", "away": "Borussia Mgladbach", "result": "A"},
    {"id": 34, "home": "Fulham", "away": "Sunderland", "result": "H"},
    {"id": 35, "home": "ACF Fiorentina", "away": "Juventus", "result": "D"},
    {"id": 36, "home": "FC Cologne", "away": "Eintracht Frankfurt", "result": "A"},
    {"id": 37, "home": "Newcastle", "away": "Manchester City", "result": "H"},
    {"id": 38, "home": "Osasuna", "away": "Real Sociedad", "result": "A"},
    {"id": 39, "home": "Rennes", "away": "Monaco", "result": "H"},
    {"id": 40, "home": "Napoli", "away": "Atalanta BC", "result": "H"},
    {"id": 41, "home": "Hellas Verona", "away": "Parma", "result": "A"},
    {"id": 42, "home": "Oviedo", "away": "Rayo Vallecano", "result": "D"},
    {"id": 43, "home": "Leeds", "away": "Aston Villa", "result": "A"},
    {"id": 44, "home": "Nantes", "away": "Lorient", "result": "D"},
    {"id": 45, "home": "St Pauli", "away": "Union Berlin", "result": "A"},
    {"id": 46, "home": "West Ham", "away": "Fulham", "result": "A"},
    {"id": 47, "home": "Brentford", "away": "Bournemouth", "result": "H"},
    {"id": 48, "home": "Sunderland", "away": "Leeds", "result": "H"},
    {"id": 49, "home": "Crystal Palace", "away": "Tottenham", "result": "H"},
    {"id": 50, "home": "Parma", "away": "ACF Fiorentina", "result": "H"},
    {"id": 51, "home": "Udinese", "away": "Lazio", "result": "D"},
    {"id": 52, "home": "Atalanta BC", "away": "Inter Milano", "result": "A"},
    {"id": 53, "home": "Royal Antwerp FC", "away": "SV Zulte Waregem", "result": "H"},
    {"id": 54, "home": "RAAL La Louviere", "away": "Oud-Heverlee Leuven", "result": "D"},
    {"id": 55, "home": "Yellow-Red KV Mechelen", "away": "FCV Dender EH", "result": "D"},
    {"id": 56, "home": "KAA Gent", "away": "KVC Westerlo", "result": "H"},
    {"id": 57, "home": "Uganda", "away": "Tanzania", "result": "D"},
    {"id": 58, "home": "Nigeria", "away": "Tunisia", "result": "H"},
    {"id": 59, "home": "Equatorial Guinea", "away": "Sudan", "result": "H"},
    {"id": 60, "home": "Ivory Coast", "away": "Cameroon", "result": "H"},
    {"id": 61, "home": "Sunderland", "away": "Bournemouth", "result": "H"},
    {"id": 62, "home": "Leverkusen", "away": "Dortmund", "result": "A"},
    {"id": 63, "home": "Everton", "away": "Newcastle", "result": "A"},
    {"id": 64, "home": "Levante", "away": "Athletic Bilbao", "result": "A"},
    {"id": 65, "home": "Tottenham", "away": "Fulham", "result": "A"},
    {"id": 66, "home": "US Lecce", "away": "Torino FC", "result": "H"},
    {"id": 67, "home": "Crystal Palace", "away": "Man United", "result": "A"},
    {"id": 68, "home": "Real Sociedad", "away": "Villarreal", "result": "A"},
    {"id": 69, "home": "Nottingham", "away": "Brighton", "result": "A"},
    {"id": 70, "home": "Hamburg", "away": "Stuttgart", "result": "H"},
    {"id": 71, "home": "Sevilla", "away": "Betis", "result": "A"},
    {"id": 72, "home": "Lorient", "away": "Nice", "result": "H"},
    {"id": 73, "home": "Chelsea", "away": "Arsenal", "result": "D"},
    {"id": 74, "home": "Freiburg", "away": "Mainz", "result": "H"},
    {"id": 75, "home": "AS Roma", "away": "Napoli", "result": "A"},
]


def score_ticket(ticket: Dict[str, Any], actual_results: Dict[int, str]) -> Dict[str, Any]:
    """
    Score a ticket against actual results.
    
    Args:
        ticket: Ticket dictionary with picks
        actual_results: Dictionary mapping fixture_id to actual result (H/D/A)
    
    Returns:
        Dictionary with scoring metrics
    """
    picks = ticket.get("picks", [])
    correct = 0
    total = len(picks)
    
    # Handle both string picks and dict picks
    for i, pick in enumerate(picks):
        fixture_id = i + 1  # Assuming sequential fixture IDs
        
        # Get pick value
        if isinstance(pick, dict):
            pick_value = pick.get("pick", "")
        else:
            pick_value = str(pick)
        
        # Normalize pick value (1/H for home, X/D for draw, 2/A for away)
        if pick_value in ["1", "H"]:
            pick_value = "H"
        elif pick_value in ["X", "D"]:
            pick_value = "D"
        elif pick_value in ["2", "A"]:
            pick_value = "A"
        
        # Get actual result
        actual = actual_results.get(fixture_id, "")
        
        if actual and pick_value == actual:
            correct += 1
    
    hit_rate = correct / total if total > 0 else 0.0
    
    return {
        "correct": correct,
        "total": total,
        "hit_rate": hit_rate,
        "ticket_id": ticket.get("id", "unknown")
    }


def generate_mock_fixtures(match_list: List[Dict]) -> List[Dict]:
    """
    Generate mock fixture data for backtesting.
    
    In a real scenario, you would load actual fixture data from your database.
    """
    fixtures = []
    for match in match_list:
        fixture = {
            "id": match["id"],
            "home_team": match["home"],
            "away_team": match["away"],
            "odds": {
                "home": 2.0,  # Mock odds - in real scenario, use historical odds
                "draw": 3.2,
                "away": 3.5
            },
            "probabilities": {
                "home": 0.40,
                "draw": 0.30,
                "away": 0.30
            },
            "xg_home": 1.2,
            "xg_away": 1.1,
            "dc_applied": False
        }
        fixtures.append(fixture)
    return fixtures


def run_backtest(
    fixtures: List[Dict],
    actual_results: Dict[int, str],
    use_decision_intelligence: bool = True,
    n_tickets: int = 10
) -> List[Dict[str, Any]]:
    """
    Run backtest for a set of fixtures.
    
    Args:
        fixtures: List of fixture dictionaries
        actual_results: Dictionary mapping fixture_id to actual result
        use_decision_intelligence: Whether to use Decision Intelligence
        n_tickets: Number of tickets to generate
    
    Returns:
        List of scored ticket results
    """
    results = []
    
    # In a real scenario, you would call your actual ticket generation service
    # For now, we'll create mock tickets to demonstrate the structure
    
    # Mock ticket generation (replace with actual service call)
    for i in range(n_tickets):
        # Generate mock picks
        picks = []
        for fixture in fixtures:
            # Simple mock: randomly pick based on probabilities
            import random
            rand = random.random()
            if rand < 0.4:
                picks.append("1")  # Home
            elif rand < 0.7:
                picks.append("X")  # Draw
            else:
                picks.append("2")  # Away
        
        ticket = {
            "id": f"ticket-{'di' if use_decision_intelligence else 'baseline'}-{i}",
            "picks": picks,
            "decisionIntelligence": {
                "accepted": use_decision_intelligence and (i % 3 != 0),  # Mock: accept 2/3
                "evScore": 0.15 if use_decision_intelligence else None,
                "contradictions": 0 if use_decision_intelligence else None
            } if use_decision_intelligence else None
        }
        
        # Score the ticket
        score = score_ticket(ticket, actual_results)
        score["mode"] = "decision_intelligence" if use_decision_intelligence else "baseline"
        di_info = ticket.get("decisionIntelligence")
        score["accepted"] = di_info.get("accepted", True) if di_info else True
        
        results.append(score)
    
    return results


def analyze_backtest_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze backtest results and compute statistics.
    """
    import statistics
    
    # Separate by mode
    baseline_results = [r for r in results if r["mode"] == "baseline"]
    di_results = [r for r in results if r["mode"] == "decision_intelligence"]
    
    # Separate accepted vs rejected for DI
    di_accepted = [r for r in di_results if r.get("accepted", True)]
    di_rejected = [r for r in di_results if not r.get("accepted", True)]
    
    def compute_stats(result_list, label):
        if not result_list:
            return {
                "label": label,
                "count": 0,
                "mean_hits": 0.0,
                "std_hits": 0.0,
                "pct_5_plus": 0.0,
                "pct_6_plus": 0.0,
                "min_hits": 0,
                "max_hits": 0
            }
        
        hits = [r["correct"] for r in result_list]
        total_picks = result_list[0]["total"] if result_list else 13
        
        return {
            "label": label,
            "count": len(result_list),
            "mean_hits": statistics.mean(hits),
            "std_hits": statistics.stdev(hits) if len(hits) > 1 else 0.0,
            "pct_5_plus": sum(1 for h in hits if h >= 5) / len(hits) * 100,
            "pct_6_plus": sum(1 for h in hits if h >= 6) / len(hits) * 100,
            "min_hits": min(hits),
            "max_hits": max(hits),
            "total_picks_per_ticket": total_picks
        }
    
    baseline_stats = compute_stats(baseline_results, "Baseline (No DI)")
    di_stats = compute_stats(di_accepted, "Decision Intelligence (Accepted)")
    di_rejected_stats = compute_stats(di_rejected, "Decision Intelligence (Rejected)")
    
    # Calculate improvement
    improvement = {
        "mean_hits_lift": di_stats["mean_hits"] - baseline_stats["mean_hits"],
        "pct_5_plus_lift": di_stats["pct_5_plus"] - baseline_stats["pct_5_plus"],
        "relative_improvement": ((di_stats["mean_hits"] - baseline_stats["mean_hits"]) / baseline_stats["mean_hits"] * 100) if baseline_stats["mean_hits"] > 0 else 0.0
    }
    
    # Acceptance rate
    acceptance_rate = len(di_accepted) / len(di_results) * 100 if di_results else 0.0
    
    return {
        "baseline": baseline_stats,
        "di_accepted": di_stats,
        "di_rejected": di_rejected_stats,
        "improvement": improvement,
        "acceptance_rate": acceptance_rate,
        "summary": {
            "total_tickets_baseline": len(baseline_results),
            "total_tickets_di": len(di_results),
            "di_accepted_count": len(di_accepted),
            "di_rejected_count": len(di_rejected)
        }
    }


def main():
    """Main backtest execution."""
    print("=" * 70)
    print("HISTORICAL BACKTEST - Decision Intelligence Validation")
    print("=" * 70)
    print(f"\nExecution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Prepare fixtures
    print("Preparing fixtures...")
    fixtures = generate_mock_fixtures(HISTORICAL_MATCHES)
    print(f"✓ Loaded {len(fixtures)} fixtures\n")
    
    # Run baseline backtest (no DI)
    print("Running baseline backtest (no Decision Intelligence)...")
    baseline_results = run_backtest(
        fixtures=fixtures,
        actual_results=HISTORICAL_RESULTS,
        use_decision_intelligence=False,
        n_tickets=30
    )
    print(f"✓ Generated {len(baseline_results)} baseline tickets\n")
    
    # Run DI backtest
    print("Running Decision Intelligence backtest...")
    di_results = run_backtest(
        fixtures=fixtures,
        actual_results=HISTORICAL_RESULTS,
        use_decision_intelligence=True,
        n_tickets=30
    )
    print(f"✓ Generated {len(di_results)} DI tickets\n")
    
    # Analyze results
    print("Analyzing results...")
    all_results = baseline_results + di_results
    analysis = analyze_backtest_results(all_results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"\n{'Metric':<40} {'Baseline':<20} {'DI (Accepted)':<20}")
    print("-" * 80)
    print(f"{'Mean Hits per Ticket':<40} {analysis['baseline']['mean_hits']:<20.2f} {analysis['di_accepted']['mean_hits']:<20.2f}")
    print(f"{'Std Dev Hits':<40} {analysis['baseline']['std_hits']:<20.2f} {analysis['di_accepted']['std_hits']:<20.2f}")
    print(f"{'% Tickets with ≥5 Hits':<40} {analysis['baseline']['pct_5_plus']:<20.1f}% {analysis['di_accepted']['pct_5_plus']:<20.1f}%")
    print(f"{'% Tickets with ≥6 Hits':<40} {analysis['baseline']['pct_6_plus']:<20.1f}% {analysis['di_accepted']['pct_6_plus']:<20.1f}%")
    print(f"{'Min Hits':<40} {analysis['baseline']['min_hits']:<20} {analysis['di_accepted']['min_hits']:<20}")
    print(f"{'Max Hits':<40} {analysis['baseline']['max_hits']:<20} {analysis['di_accepted']['max_hits']:<20}")
    
    print("\n" + "-" * 80)
    print(f"{'Improvement (DI vs Baseline)':<40}")
    print(f"{'  Mean Hits Lift':<40} {analysis['improvement']['mean_hits_lift']:+.2f}")
    print(f"{'  % ≥5 Hits Lift':<40} {analysis['improvement']['pct_5_plus_lift']:+.1f}%")
    print(f"{'  Relative Improvement':<40} {analysis['improvement']['relative_improvement']:+.1f}%")
    
    print("\n" + "-" * 80)
    print(f"{'Decision Intelligence Stats':<40}")
    print(f"{'  Acceptance Rate':<40} {analysis['acceptance_rate']:.1f}%")
    print(f"{'  Accepted Tickets':<40} {analysis['summary']['di_accepted_count']}")
    print(f"{'  Rejected Tickets':<40} {analysis['summary']['di_rejected_count']}")
    
    if analysis['di_rejected']['count'] > 0:
        print(f"\n{'Rejected Tickets Performance':<40}")
        print(f"{'  Mean Hits':<40} {analysis['di_rejected']['mean_hits']:.2f}")
        print(f"{'  vs Accepted':<40} {analysis['di_accepted']['mean_hits'] - analysis['di_rejected']['mean_hits']:+.2f}")
    
    # Save results
    output_file = Path(__file__).parent / "backtest_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "raw_results": all_results[:20]  # First 20 for review
        }, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    print("\n" + "=" * 70)
    print("BACKTEST COMPLETE")
    print("=" * 70)
    
    return analysis


if __name__ == "__main__":
    main()

