"""
Ticket Generation Service

Generates jackpot tickets with portfolio-level constraints, correlation awareness,
role specialization, and late-shock detection.

Phase 1 & 2 Implementation:
- Correlation scoring between fixtures
- Ticket role constraints (A-G behavioral roles)
- Portfolio-level constraints (correlation breaking, favorite hedging)
- Late-shock detection and forced hedges
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import random
import math
import logging
from app.services.h2h_service import get_h2h_stats, compute_h2h_stats
from app.services.draw_policy import h2h_draw_eligible, get_draw_rank
from app.models.uncertainty import normalized_entropy
from app.services.correlation import build_correlation_matrix
from app.services.league_corr_weights import get_corr_weights
from app.services.ticket_roles import TICKET_ROLE_CONSTRAINTS, get_role_constraints
from app.services.late_shock import compute_late_shock, LateShockSignal, should_force_hedge

logger = logging.getLogger(__name__)


# League-specific draw limits (min_draws, max_draws) for 15-match jackpots
# NOTE: These are fallback limits. Role constraints override these.
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
    """Service for generating jackpot tickets with portfolio-level constraints"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_bundle(
        self,
        fixtures: List[Dict],
        league_code: str = "DEFAULT",
        set_keys: List[str] = ["B"],
        n_tickets: Optional[int] = None,
        probability_sets: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict:
        """
        Generate portfolio of tickets with correlation awareness and role constraints.
        
        Args:
            fixtures: List of fixture dicts with:
                - id, home_team, away_team, home_team_id, away_team_id, league_id
                - probabilities: {"home": float, "draw": float, "away": float}
                - odds: {"home": float, "draw": float, "away": float}
                - odds_open: Optional[{"home": float, "draw": float, "away": float}]
                - kickoff_ts: Optional[int] (Unix timestamp)
                - draw_signal: Optional[float] (0.0-1.0)
                - lambda_total: Optional[float] (total expected goals)
            league_code: League code for correlation weights
            set_keys: List of probability sets to use (e.g., ["A", "B", "C"])
            n_tickets: Number of tickets per set (defaults to 1)
            probability_sets: Optional dict mapping set keys to probability arrays
            
        Returns:
            Dict with tickets array, diagnostics, and metadata
        """
        if n_tickets is None:
            n_tickets = 1
        
        # Step 1: Build correlation matrix (portfolio-scoped)
        logger.info(f"Building correlation matrix for {len(fixtures)} fixtures (league: {league_code})")
        corr_matrix = build_correlation_matrix(fixtures, league_code)
        
        # Step 2: Detect late shocks (fixture-scoped)
        logger.info("Detecting late shocks...")
        late_shocks = {}
        for i, f in enumerate(fixtures):
            odds_open = f.get("odds_open")
            odds_close = f.get("odds", {})
            model_probs = f.get("probabilities", {})
            
            if odds_open and odds_close:
                late_shocks[i] = compute_late_shock(
                    odds_open, odds_close, model_probs
                )
                if late_shocks[i].triggered:
                    logger.info(f"Late shock detected for fixture {i+1}: {late_shocks[i].reasons}")
            else:
                late_shocks[i] = None
        
        # Step 2.5: Analyze slate profile and select archetype
        from app.services.ticket_archetypes import analyze_slate_profile, select_archetype, enforce_archetype
        slate_profile = analyze_slate_profile(fixtures)
        selected_archetype = select_archetype(slate_profile)
        logger.info(f"Selected ticket archetype: {selected_archetype} (profile: {slate_profile})")
        
        # Step 3: Generate tickets with role constraints and archetype enforcement
        all_tickets = []
        for set_key in set_keys:
            # Get role constraints
            constraints = get_role_constraints(set_key)
            
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
            
            # Generate tickets for this set with archetype enforcement
            max_attempts = n_tickets * 3  # Allow retries for archetype enforcement
            attempts = 0
            tickets_generated = 0
            
            while tickets_generated < n_tickets and attempts < max_attempts:
                attempts += 1
                
                picks = self._generate_ticket(
                    fixtures=set_fixtures,
                    probs_dict=self._convert_probs_to_dict(set_fixtures),
                    corr_matrix=corr_matrix,
                    constraints=constraints,
                    late_shocks=late_shocks,
                    role=set_key,
                    league_code=league_code
                )
                
                # Prepare ticket matches for archetype enforcement and evaluation
                ticket_matches = []
                for i, pick in enumerate(picks):
                    if i < len(set_fixtures):
                        fixture = set_fixtures[i]
                        ticket_matches.append({
                            "pick": pick,
                            "fixture_id": fixture.get("id") or (i + 1),
                            "model_prob": fixture.get("probabilities", {}).get(
                                "home" if pick == "1" else "draw" if pick == "X" else "away", 0.33
                            ),
                            "market_odds": fixture.get("odds", {}),
                            "probabilities": fixture.get("probabilities", {}),
                            "xg_home": fixture.get("xg_home"),
                            "xg_away": fixture.get("xg_away"),
                            "dc_applied": fixture.get("dc_applied", False),
                            "league_code": league_code,
                            "market_prob_home": None,  # Will be calculated if needed
                            "market_prob": None  # Will be calculated if needed
                        })
                
                # Enforce archetype constraints (BEFORE Decision Intelligence)
                if not enforce_archetype(ticket_matches, selected_archetype):
                    logger.debug(f"Ticket rejected by archetype {selected_archetype} constraints, attempt {attempts}")
                    continue
                
                # Evaluate with decision intelligence
                try:
                    from app.decision_intelligence.ticket_evaluator import evaluate_ticket
                    evaluation = evaluate_ticket(
                        ticket_matches=ticket_matches,
                        db=self.db
                    )
                    
                    # Only add if accepted by Decision Intelligence
                    if not evaluation.get("accepted", False):
                        logger.debug(f"Ticket rejected by Decision Intelligence: {evaluation.get('reason', 'Unknown')}")
                        continue
                    
                    ticket = {
                        "id": f"ticket-{set_key}-{len(all_tickets)}",
                        "setKey": set_key,
                        "picks": picks,
                        "drawCount": picks.count("X"),
                        "archetype": selected_archetype,
                        "decision_version": "UDS_v1",  # Version of decision scoring algorithm
                        "decisionIntelligence": {
                            "accepted": evaluation.get("accepted", True),
                            "evScore": evaluation.get("ev_score"),
                            "contradictions": evaluation.get("contradictions", 0),
                            "reason": evaluation.get("reason", "Not evaluated")
                        }
                    }
                    
                    # Add ev_score to ticket for portfolio scoring
                    ticket["ev_score"] = evaluation.get("ev_score")
                    
                    all_tickets.append(ticket)
                    tickets_generated += 1
                    
                except Exception as e:
                    logger.warning(f"Decision intelligence evaluation failed: {e}, skipping ticket")
                    continue
            
            if tickets_generated < n_tickets:
                logger.warning(f"Only generated {tickets_generated}/{n_tickets} tickets for set {set_key} (archetype: {selected_archetype})")
        
        # Step 4: Portfolio-level optimization (if multiple tickets requested)
        if n_tickets > 1 and len(all_tickets) > n_tickets:
            from app.services.portfolio_scoring import select_optimal_bundle, calculate_portfolio_diagnostics
            logger.info(f"Selecting optimal bundle from {len(all_tickets)} accepted tickets")
            all_tickets = select_optimal_bundle(all_tickets, n_tickets)
            portfolio_diagnostics = calculate_portfolio_diagnostics(all_tickets)
            logger.info(f"Portfolio diagnostics: {portfolio_diagnostics}")
        else:
            portfolio_diagnostics = None
        
        # Step 5: Calculate coverage diagnostics
        from app.services.coverage import coverage_diagnostics
        diagnostics = coverage_diagnostics([t["picks"] for t in all_tickets])
        
        # Step 6: Generate portfolio diagnostics (optional, for auditor)
        try:
            from app.services.auditor import bundle_diagnostics
            auditor_diagnostics = bundle_diagnostics(
                {"tickets": all_tickets},
                fixtures,
                corr_matrix
            )
            diagnostics["portfolio"] = portfolio_diagnostics
        except ImportError:
            logger.debug("Auditor diagnostics not available (optional)")
        
        return {
            "tickets": all_tickets,
            "coverage": diagnostics,
            "meta": {
                "portfolioSize": len(all_tickets),
                "roles": set_keys,
                "correlationMatrix": corr_matrix,  # For debugging/analysis
                "lateShocks": {
                    i: {
                        "triggered": shock.triggered,
                        "score": shock.shock_score,
                        "reasons": shock.reasons
                    } if shock else None
                    for i, shock in late_shocks.items()
                }
            }
        }
    
    def _convert_probs_to_dict(self, fixtures: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Convert fixtures list to probability dict format."""
        probs_dict = {}
        for i, fx in enumerate(fixtures):
            probs = fx.get("probabilities", {})
            probs_dict[str(i + 1)] = {
                "1": probs.get("home", 0.33),
                "X": probs.get("draw", 0.33),
                "2": probs.get("away", 0.33)
            }
        return probs_dict
    
    def _generate_ticket(
        self,
        fixtures: List[Dict],
        probs_dict: Dict[str, Dict[str, float]],
        corr_matrix: List[List[float]],
        constraints: Dict,
        late_shocks: Dict[int, Optional[LateShockSignal]],
        role: str,
        league_code: str = "DEFAULT"
    ) -> List[str]:
        """
        Generate single ticket with role constraints and portfolio awareness.
        
        Args:
            fixtures: List of fixture dicts
            probs_dict: Dict mapping fixture index (str) to probability dict
            corr_matrix: Correlation matrix
            constraints: Role constraints dict
            late_shocks: Dict mapping fixture index to LateShockSignal
            role: Ticket role ('A', 'B', 'C', 'D', 'E', 'F', 'G')
            league_code: League code for fallback draw limits
            
        Returns:
            List of picks ('1', 'X', '2')
        """
        n = len(fixtures)
        picks = [None] * n
        draw_indices = []
        fav_count = 0
        dog_count = 0
        
        # Step 1: Initial picks (argmax)
        for i in range(n):
            prob_dict = probs_dict.get(str(i + 1), {"1": 0.33, "X": 0.33, "2": 0.33})
            choice = max(prob_dict, key=prob_dict.get)
            
            if choice == "X":
                draw_indices.append(i)
            elif prob_dict.get(choice, 0) >= 0.65:
                fav_count += 1
            else:
                dog_count += 1
            
            picks[i] = choice
        
        # Step 2: Enforce draw constraints
        min_draws = constraints.get("min_draws", 0)
        max_draws = constraints.get("max_draws")
        
        # Add draws if below minimum
        while len(draw_indices) < min_draws:
            i = self._best_draw_candidate(picks, probs_dict, fixtures)
            if i is not None:
                picks[i] = "X"
                draw_indices.append(i)
                # Update counts
                prob_dict = probs_dict.get(str(i + 1), {})
                if prob_dict.get("1", 0) >= 0.65 or prob_dict.get("2", 0) >= 0.65:
                    fav_count -= 1
                else:
                    dog_count -= 1
            else:
                break  # No more draw candidates
        
        # Remove draws if above maximum
        if max_draws is not None:
            while len(draw_indices) > max_draws:
                i = draw_indices.pop()
                picks[i] = self._non_draw_choice(probs_dict.get(str(i + 1), {}))
                # Update counts
                prob_dict = probs_dict.get(str(i + 1), {})
                if prob_dict.get("1", 0) >= 0.65 or prob_dict.get("2", 0) >= 0.65:
                    fav_count += 1
                else:
                    dog_count += 1
        
        # Step 3: Enforce favorite constraints
        max_favorites = constraints.get("max_favorites")
        if max_favorites is not None:
            while fav_count > max_favorites:
                i = self._strong_favorite_index(probs_dict, picks)
                if i is not None:
                    picks[i] = "X"
                    draw_indices.append(i)
                    fav_count -= 1
                else:
                    break
        
        # Step 4: Enforce underdog constraints
        min_underdogs = constraints.get("min_underdogs", 0)
        while dog_count < min_underdogs:
            i = self._best_underdog_candidate(picks, probs_dict)
            if i is not None:
                # Flip to underdog side
                prob_dict = probs_dict.get(str(i + 1), {})
                if picks[i] == "1" and prob_dict.get("2", 0) < 0.65:
                    picks[i] = "2"
                    dog_count += 1
                elif picks[i] == "2" and prob_dict.get("1", 0) < 0.65:
                    picks[i] = "1"
                    dog_count += 1
                elif picks[i] == "X":
                    # Convert draw to underdog
                    picks[i] = "1" if prob_dict.get("1", 0) < prob_dict.get("2", 0) else "2"
                    draw_indices.remove(i)
                    dog_count += 1
            else:
                break
        
        # Step 5: Late-shock hedge (for Set F/G)
        # Check if role should hedge late shocks
        if role in ("F", "G"):
            for i, shock in late_shocks.items():
                if shock and shock.triggered:
                    prob_dict = probs_dict.get(str(i + 1), {})
                    fav = max(prob_dict, key=prob_dict.get)
                    
                    # Force hedge: draw or opposite side
                    if fav != "X":
                        picks[i] = "X"
                        if i not in draw_indices:
                            draw_indices.append(i)
                    else:
                        picks[i] = "1" if picks[i] == "2" else "2"
                    logger.debug(f"Forced hedge on fixture {i+1} due to late shock (role: {role})")
                    break
        
        # Step 6: Correlation breaker
        self._break_correlation(picks, corr_matrix, probs_dict)
        
        # Step 7: Entropy adjustment
        self._adjust_entropy(picks, probs_dict, constraints.get("entropy_range", (0.65, 0.85)))
        
        # Step 8: Favorite hedge enforcement (portfolio-level)
        self._enforce_favorite_hedge(picks, probs_dict)
        
        return picks
    
    def _best_draw_candidate(
        self,
        picks: List[str],
        probs_dict: Dict[str, Dict[str, float]],
        fixtures: List[Dict]
    ) -> Optional[int]:
        """Find best fixture to convert to draw."""
        candidates = []
        for i, pick in enumerate(picks):
            if pick != "X":
                prob_dict = probs_dict.get(str(i + 1), {})
                draw_prob = prob_dict.get("X", 0.0)
                if draw_prob > 0.25:  # Minimum draw probability threshold
                    candidates.append((i, draw_prob))
        
        if candidates:
            # Sort by draw probability (highest first)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None
    
    def _non_draw_choice(self, prob_dict: Dict[str, float]) -> str:
        """Choose non-draw pick based on probabilities."""
        home_prob = prob_dict.get("1", 0.33)
        away_prob = prob_dict.get("2", 0.33)
        return "1" if home_prob >= away_prob else "2"
    
    def _strong_favorite_index(
        self,
        probs_dict: Dict[str, Dict[str, float]],
        picks: List[str]
    ) -> Optional[int]:
        """Find fixture with strong favorite that can be converted to draw."""
        candidates = []
        for i, pick in enumerate(picks):
            if pick != "X":
                prob_dict = probs_dict.get(str(i + 1), {})
                max_prob = max(prob_dict.values())
                if max_prob >= 0.70:  # Strong favorite threshold
                    candidates.append((i, max_prob))
        
        if candidates:
            # Sort by probability (highest first)
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None
    
    def _best_underdog_candidate(
        self,
        picks: List[str],
        probs_dict: Dict[str, Dict[str, float]]
    ) -> Optional[int]:
        """Find best fixture to convert to underdog."""
        candidates = []
        for i, pick in enumerate(picks):
            prob_dict = probs_dict.get(str(i + 1), {})
            max_prob = max(prob_dict.values())
            if max_prob < 0.65:  # Not a favorite
                # Prefer fixtures where we can pick the underdog side
                if pick == "X" or (pick == "1" and prob_dict.get("2", 0) < 0.65) or (pick == "2" and prob_dict.get("1", 0) < 0.65):
                    candidates.append((i, max_prob))
        
        if candidates:
            # Sort by max_prob (lowest first = most underdog)
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        return None
    
    def _break_correlation(
        self,
        picks: List[str],
        corr_matrix: List[List[float]],
        probs_dict: Dict[str, Dict[str, float]],
        threshold: float = 0.7
    ):
        """Break high correlations by flipping picks."""
        n = len(picks)
        for i in range(n):
            for j in range(i + 1, n):
                if corr_matrix[i][j] > threshold and picks[i] == picks[j]:
                    # Break correlation: flip j to draw or opposite side
                    prob_dict_j = probs_dict.get(str(j + 1), {})
                    if picks[j] != "X" and prob_dict_j.get("X", 0) > 0.25:
                        picks[j] = "X"
                        logger.debug(f"Broke correlation between fixtures {i+1} and {j+1} (corr={corr_matrix[i][j]:.3f}) by converting {j+1} to draw")
                    else:
                        # Flip to opposite side
                        picks[j] = "1" if picks[j] == "2" else "2"
                        logger.debug(f"Broke correlation between fixtures {i+1} and {j+1} (corr={corr_matrix[i][j]:.3f}) by flipping {j+1}")
    
    def _adjust_entropy(
        self,
        picks: List[str],
        probs_dict: Dict[str, Dict[str, float]],
        target_range: tuple
    ):
        """Adjust ticket entropy to target range."""
        min_entropy, max_entropy = target_range
        
        # Calculate current entropy
        ticket_probs = [
            probs_dict.get(str(i + 1), {}).get(picks[i], 0.33)
            for i in range(len(picks))
        ]
        current_entropy = normalized_entropy(ticket_probs)
        
        # Adjust if outside range
        if current_entropy < min_entropy:
            # Too low: add draws (increase uncertainty)
            for i in range(len(picks)):
                if picks[i] != "X":
                    prob_dict = probs_dict.get(str(i + 1), {})
                    if prob_dict.get("X", 0) > 0.25:
                        picks[i] = "X"
                        logger.debug(f"Adjusted entropy: added draw at fixture {i+1} (entropy: {current_entropy:.3f} -> target: {min_entropy:.3f})")
                        break
        
        elif current_entropy > max_entropy:
            # Too high: remove draws (decrease uncertainty)
            for i in range(len(picks)):
                if picks[i] == "X":
                    picks[i] = self._non_draw_choice(probs_dict.get(str(i + 1), {}))
                    logger.debug(f"Adjusted entropy: removed draw at fixture {i+1} (entropy: {current_entropy:.3f} -> target: {max_entropy:.3f})")
                    break
    
    def _enforce_favorite_hedge(
        self,
        picks: List[str],
        probs_dict: Dict[str, Dict[str, float]]
    ):
        """
        Enforce favorite hedging: for fixtures with strong favorites (prob >= 0.65),
        ensure at least one ticket takes draw or opposite side.
        
        NOTE: This is portfolio-level, so it's called per ticket but the effect
        is cumulative across the bundle. For now, we ensure this ticket hedges
        at least one strong favorite.
        """
        hedged_favorites = 0
        for i, pick in enumerate(picks):
            prob_dict = probs_dict.get(str(i + 1), {})
            max_prob = max(prob_dict.values())
            max_outcome = max(prob_dict, key=prob_dict.get)
            
            if max_prob >= 0.65:  # Strong favorite
                # Check if we're hedging (not taking the favorite)
                if pick != max_outcome:
                    hedged_favorites += 1
        
        # If no favorites are hedged, hedge at least one
        if hedged_favorites == 0:
            for i, pick in enumerate(picks):
                prob_dict = probs_dict.get(str(i + 1), {})
                max_prob = max(prob_dict.values())
                max_outcome = max(prob_dict, key=prob_dict.get)
                
                if max_prob >= 0.65 and pick == max_outcome:
                    # Hedge: prefer draw, otherwise opposite side
                    if prob_dict.get("X", 0) > 0.25:
                        picks[i] = "X"
                    else:
                        picks[i] = "1" if max_outcome == "2" else "2"
                    logger.debug(f"Forced favorite hedge on fixture {i+1} (favorite: {max_outcome}, prob: {max_prob:.3f})")
                    break
    
    # Legacy method for backward compatibility
    def generate_ticket(
        self,
        fixtures: List[Dict],
        league_code: str = "DEFAULT",
        set_key: str = "B"
    ) -> Dict:
        """
        Generate a single jackpot ticket (legacy method for backward compatibility).
        
        This method uses the new portfolio-aware generation but without correlation matrix.
        For full portfolio features, use generate_bundle().
        """
        # Build minimal correlation matrix (all zeros for single ticket)
        n = len(fixtures)
        corr_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            corr_matrix[i][i] = 1.0
        
        # No late shocks for single ticket
        late_shocks = {i: None for i in range(n)}
        
        # Get constraints
        constraints = get_role_constraints(set_key)
        
        # Convert probabilities
        probs_dict = self._convert_probs_to_dict(fixtures)
        
        # Generate ticket
        picks = self._generate_ticket(
            fixtures=fixtures,
            probs_dict=probs_dict,
            corr_matrix=corr_matrix,
            constraints=constraints,
            late_shocks=late_shocks,
            role=set_key,
            league_code=league_code
        )
        
        return {
            "picks": picks,
            "drawCount": picks.count("X"),
            "setKey": set_key
        }
