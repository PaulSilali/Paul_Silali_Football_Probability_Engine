"""
Ticket Generation Service

Generates jackpot tickets with draw constraints and H2H-aware eligibility.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import random
from app.services.h2h_service import get_h2h_stats, compute_h2h_stats
from app.services.draw_policy import h2h_draw_eligible, get_draw_rank
from app.models.uncertainty import normalized_entropy


# League-specific draw limits (min_draws, max_draws) for 15-match jackpots
LEAGUE_DRAW_LIMITS = {
    "E0": (2, 4),   # Premier League
    "SP1": (2, 4),  # La Liga
    "D1": (3, 5),   # Bundesliga
    "I1": (3, 5),   # Serie A
    "F1": (3, 5),   # Ligue 1
    "N1": (3, 6),   # Eredivisie
    "E1": (2, 4),   # Championship
    "E2": (2, 4),   # League One
    "E3": (2, 5),   # League Two
    "DEFAULT": (2, 5)
}


class TicketGenerationService:
    """Service for generating jackpot tickets with draw constraints"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_ticket(
        self,
        fixtures: List[Dict],
        league_code: str = "DEFAULT",
        set_key: str = "B"
    ) -> Dict:
        """
        Generate a single jackpot ticket with draw constraints.
        
        Args:
            fixtures: List of fixture dicts with probabilities
            league_code: League code for draw limits
            set_key: Probability set to use (A-G)
            
        Returns:
            Dict with picks array and metadata
        """
        min_draws, max_draws = LEAGUE_DRAW_LIMITS.get(
            league_code,
            LEAGUE_DRAW_LIMITS["DEFAULT"]
        )
        
        draw_candidates = []
        non_draw_candidates = []
        
        # Classify fixtures by draw eligibility
        for fx in fixtures:
            probs = fx.get("probabilities", {})
            home_prob = probs.get("home", 0.33)
            draw_prob = probs.get("draw", 0.33)
            away_prob = probs.get("away", 0.33)
            
            # Calculate entropy
            entropy = normalized_entropy((home_prob, draw_prob, away_prob))
            
            # Get H2H stats
            home_team_id = fx.get("home_team_id")
            away_team_id = fx.get("away_team_id")
            h2h = None
            
            if home_team_id and away_team_id:
                # Try to get cached H2H stats
                h2h = get_h2h_stats(self.db, home_team_id, away_team_id)
                
                # If not cached, try to compute
                if not h2h:
                    league_id = fx.get("league_id")
                    h2h = compute_h2h_stats(self.db, home_team_id, away_team_id, league_id)
            
            # Check draw eligibility
            if h2h_draw_eligible(draw_prob, entropy, h2h):
                draw_candidates.append({
                    "fixture": fx,
                    "draw_prob": draw_prob,
                    "entropy": entropy,
                    "h2h": h2h
                })
            else:
                non_draw_candidates.append({
                    "fixture": fx,
                    "home_prob": home_prob,
                    "away_prob": away_prob
                })
        
        # Determine number of draws to include
        available_draws = len(draw_candidates)
        if available_draws == 0:
            # No eligible draws - use argmax for all
            draw_count = 0
        else:
            # Randomly select between min and max (or available)
            draw_count = random.randint(
                min(min_draws, available_draws),
                min(max_draws, available_draws)
            )
        
        # Select draws
        selected_draws = []
        if draw_count > 0:
            # Sort by draw probability (highest first)
            draw_candidates.sort(key=lambda x: x["draw_prob"], reverse=True)
            selected_draws = random.sample(
                draw_candidates[:min(draw_count * 2, len(draw_candidates))],  # Prefer higher prob draws
                k=min(draw_count, len(draw_candidates))
            )
        
        # Build ticket
        ticket_picks = []
        selected_draw_fixtures = {s["fixture"]["id"] for s in selected_draws}
        
        for fx in fixtures:
            fx_id = fx.get("id")
            probs = fx.get("probabilities", {})
            home_prob = probs.get("home", 0.33)
            draw_prob = probs.get("draw", 0.33)
            away_prob = probs.get("away", 0.33)
            
            if fx_id in selected_draw_fixtures:
                ticket_picks.append("X")
            else:
                # Use argmax for non-draw picks
                if home_prob >= away_prob:
                    ticket_picks.append("1")
                else:
                    ticket_picks.append("2")
        
        return {
            "picks": ticket_picks,
            "drawCount": ticket_picks.count("X"),
            "setKey": set_key
        }
    
    def generate_bundle(
        self,
        fixtures: List[Dict],
        league_code: str = "DEFAULT",
        set_keys: List[str] = ["B"],
        n_tickets: Optional[int] = None,
        probability_sets: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict:
        """
        Generate multiple tickets (bundle) with diversification.
        
        Args:
            fixtures: List of fixture dicts
            league_code: League code
            set_keys: List of probability sets to use
            n_tickets: Number of tickets per set (defaults to 1)
            probability_sets: Optional dict mapping set keys to probability arrays
            
        Returns:
            Dict with tickets array and coverage diagnostics
        """
        if n_tickets is None:
            n_tickets = 1
        
        all_tickets = []
        
        # Generate tickets for each set
        for set_key in set_keys:
            # Update fixtures with probabilities for this set
            set_fixtures = fixtures.copy()
            if probability_sets and set_key in probability_sets:
                probs_array = probability_sets[set_key]
                for idx, fx in enumerate(set_fixtures):
                    if idx < len(probs_array):
                        prob = probs_array[idx]
                        fx["probabilities"] = {
                            "home": prob.get("homeWinProbability", 33) / 100.0,
                            "draw": prob.get("drawProbability", 33) / 100.0,
                            "away": prob.get("awayWinProbability", 33) / 100.0
                        }
            
            for _ in range(n_tickets):
                ticket = self.generate_ticket(set_fixtures, league_code, set_key)
                ticket["id"] = f"ticket-{set_key}-{len(all_tickets)}"
                all_tickets.append(ticket)
        
        # Calculate coverage diagnostics
        from app.services.coverage import coverage_diagnostics
        diagnostics = coverage_diagnostics([t["picks"] for t in all_tickets])
        
        return {
            "tickets": all_tickets,
            "coverage": diagnostics
        }

