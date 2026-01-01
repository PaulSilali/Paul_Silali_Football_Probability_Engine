"""
FastAPI Router for Probability Calculations

CRITICAL: This endpoint now uses trained models (Poisson/Blending/Calibration)
instead of hardcoded parameters or team table ratings.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.prediction import (
    JackpotInput, PredictionResponse, MatchProbabilitiesOutput, PredictionWarning
)
from app.schemas.jackpot import ApiResponse
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models.dixon_coles import (
    TeamStrength, DixonColesParams, calculate_match_probabilities, MatchProbabilities
)
from app.models.probability_sets import generate_all_probability_sets, PROBABILITY_SET_METADATA, blend_probabilities, odds_to_implied_probabilities
from app.models.calibration import Calibrator
from app.db.models import (
    Model, ModelStatus, Jackpot as JackpotModel, JackpotFixture, Prediction, Team, 
    SavedProbabilityResult, ValidationResult, PredictionSet, CalibrationData, MatchResult
)
from app.models.calibration import calculate_brier_score, calculate_log_loss
from app.services.team_resolver import resolve_team_safe
from datetime import datetime
import logging
import pickle
import base64
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/probabilities", tags=["probabilities"])


@router.get("/{jackpot_id}/probabilities")
async def calculate_probabilities(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Calculate probabilities for a jackpot - returns all sets (A-G)"""
    logger.info(f"=== COMPUTE PROBABILITIES REQUEST ===")
    logger.info(f"Jackpot ID: {jackpot_id}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Get jackpot by jackpot_id (string field)
        jackpot = db.query(JackpotModel).filter(
            JackpotModel.jackpot_id == jackpot_id
        ).first()
        
        if not jackpot:
            logger.error(f"Jackpot {jackpot_id} not found")
            raise HTTPException(status_code=404, detail=f"Jackpot {jackpot_id} not found")
        
        logger.info(f"Found jackpot: ID={jackpot.id}, created_at={jackpot.created_at}")
        
        # Get fixtures for this jackpot
        fixtures = db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot.id
        ).order_by(JackpotFixture.match_order).all()
        
        if not fixtures:
            logger.error(f"No fixtures found for jackpot {jackpot_id}")
            raise HTTPException(status_code=400, detail="No fixtures found for jackpot")
        
        logger.info(f"Found {len(fixtures)} fixtures for jackpot {jackpot_id}")
        logger.info(f"Fixture teams: {[(f.home_team, f.away_team) for f in fixtures[:3]]}...")  # Log first 3
        
        # Get active model (prefer calibration -> blending -> poisson)
        logger.info("Loading active model...")
        model = None
        poisson_model = None
        
        # Try to find calibration model first
        calibration_model = db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == "calibration"
        ).order_by(Model.training_completed_at.desc()).first()
        
        if calibration_model:
            model = calibration_model
            logger.info(f"Found calibration model: {calibration_model.version}")
            # Calibration model references a base model (could be blending or poisson)
            base_model_id = calibration_model.model_weights.get('base_model_id')
            if base_model_id:
                base_model = db.query(Model).filter(Model.id == base_model_id).first()
                logger.info(f"Calibration model references base model ID: {base_model_id} (type: {base_model.model_type if base_model else 'unknown'})")
                
                # If base model is blending, get its poisson model
                if base_model and base_model.model_type == "blending":
                    # Blending model stores poisson_model_id in model_weights
                    logger.info(f"Blending model weights keys: {list(base_model.model_weights.keys()) if base_model.model_weights else 'None'}")
                    poisson_model_id = base_model.model_weights.get('poisson_model_id') or base_model.model_weights.get('base_model_id')
                    logger.info(f"Looking for poisson_model_id, found: {poisson_model_id}")
                    if poisson_model_id:
                        poisson_model = db.query(Model).filter(Model.id == poisson_model_id).first()
                        if poisson_model:
                            logger.info(f"✓ Found poisson model: ID={poisson_model_id}, version={poisson_model.version}, type={poisson_model.model_type}")
                            # Check if poisson model has team_strengths
                            if poisson_model.model_weights:
                                team_strengths_count = len(poisson_model.model_weights.get('team_strengths', {}))
                                logger.info(f"Poisson model has {team_strengths_count} team strengths in model_weights")
                        else:
                            logger.error(f"✗ Poisson model ID {poisson_model_id} not found in database")
                    else:
                        logger.error(f"✗ Blending model {base_model.version} has no poisson_model_id in model_weights")
                elif base_model and base_model.model_type == "poisson":
                    poisson_model = base_model
                    logger.info(f"Base model is poisson model: {poisson_model.version}")
        
        # If no calibration, try blending model
        if not model:
            blending_model = db.query(Model).filter(
                Model.status == ModelStatus.active,
                Model.model_type == "blending"
            ).order_by(Model.training_completed_at.desc()).first()
            
            if blending_model:
                model = blending_model
                logger.info(f"Found blending model: {blending_model.version}")
                # Blending model references a poisson model (stored as poisson_model_id)
                poisson_model_id = blending_model.model_weights.get('poisson_model_id') or blending_model.model_weights.get('base_model_id')
                if poisson_model_id:
                    poisson_model = db.query(Model).filter(Model.id == poisson_model_id).first()
                    if poisson_model:
                        logger.info(f"Blending model references poisson model ID: {poisson_model_id} ({poisson_model.version})")
                    else:
                        logger.warning(f"Poisson model ID {poisson_model_id} not found in database")
                else:
                    logger.warning(f"Blending model {blending_model.version} has no poisson_model_id in model_weights")
        
        # If still no model, try poisson model
        if not model:
            poisson_model = db.query(Model).filter(
                Model.status == ModelStatus.active,
                Model.model_type == "poisson"
            ).order_by(Model.training_completed_at.desc()).first()
            if poisson_model:
                model = poisson_model
                logger.info(f"Found poisson model: {poisson_model.version}")
        
        if not model:
            logger.warning("No active model found, using default parameters")
        
        # Load team strengths from POISSON model (not blending/calibration)
        team_strengths_dict = {}
        model_params = {}
        
        if poisson_model and poisson_model.model_weights:
            team_strengths_dict = poisson_model.model_weights.get('team_strengths', {})
            team_count = len(team_strengths_dict)
            logger.info(f"Loaded {team_count} team strengths from POISSON model {poisson_model.version}")
            
            # Use parameters from poisson model with validation
            raw_home_advantage = poisson_model.model_weights.get('home_advantage', 0.35)
            raw_rho = poisson_model.model_weights.get('rho', -0.13)
            
            # Validate and clamp home_advantage (should be positive, typically 0.3-0.5)
            if raw_home_advantage < 0 or raw_home_advantage > 1.0:
                logger.warning(f"⚠️ Invalid home_advantage from model: {raw_home_advantage}. Clamping to default 0.35")
                home_advantage = 0.35
            else:
                home_advantage = raw_home_advantage
            
            # Validate rho (should be negative, typically -0.13 to -0.1)
            if raw_rho > 0 or raw_rho < -0.5:
                logger.warning(f"⚠️ Invalid rho from model: {raw_rho}. Using default -0.13")
                rho = -0.13
            else:
                rho = raw_rho
            
            model_params = {
                'rho': rho,
                'home_advantage': home_advantage,
                'xi': poisson_model.model_weights.get('xi', 0.0065)
            }
            logger.info(f"Model parameters from poisson model: rho={model_params['rho']}, home_advantage={model_params['home_advantage']}, xi={model_params['xi']}")
            if raw_home_advantage != home_advantage or raw_rho != rho:
                logger.warning(f"⚠️ Model parameters were clamped: home_advantage {raw_home_advantage} -> {home_advantage}, rho {raw_rho} -> {rho}")
        else:
            # Default parameters if no poisson model
            logger.warning("No poisson model found for team strengths, using default parameters")
            model_params = {
                'rho': -0.13,
                'home_advantage': 0.35,
                'xi': 0.0065
            }
        
        # Helper function to get team strength (using fuzzy matching like old code)
        def get_team_strength_for_fixture(team_name: str, team_id_from_fixture: Optional[int] = None) -> TeamStrength:
            """Get team strength from model or database using fuzzy matching"""
            # Try to find team in model's team_strengths by ID first (handle both int and string keys)
            if team_id_from_fixture:
                # Try integer key first
                if team_id_from_fixture in team_strengths_dict:
                    strengths = team_strengths_dict[team_id_from_fixture]
                    logger.debug(f"Found team {team_id_from_fixture} in model strengths: attack={strengths.get('attack', 1.0)}, defense={strengths.get('defense', 1.0)}")
                    return TeamStrength(
                        team_id=team_id_from_fixture,
                        attack=float(strengths.get('attack', 1.0)),
                        defense=float(strengths.get('defense', 1.0))
                    )
                # Try string key
                if str(team_id_from_fixture) in team_strengths_dict:
                    strengths = team_strengths_dict[str(team_id_from_fixture)]
                    logger.debug(f"Found team {team_id_from_fixture} (as string) in model strengths: attack={strengths.get('attack', 1.0)}, defense={strengths.get('defense', 1.0)}")
                    return TeamStrength(
                        team_id=team_id_from_fixture,
                        attack=float(strengths.get('attack', 1.0)),
                        defense=float(strengths.get('defense', 1.0))
                    )
            
            # Use fuzzy matching to find team in database (like old code)
            if team_name:
                team = resolve_team_safe(db, team_name)
                
                if team:
                    logger.debug(f"Found team '{team_name}' -> DB team '{team.canonical_name}' (ID: {team.id})")
                    # Check if this team is in model's team_strengths (handle both int and string keys)
                    if team.id in team_strengths_dict:
                        strengths = team_strengths_dict[team.id]
                        logger.debug(f"Using model strengths for team {team.id}: attack={strengths.get('attack', 1.0)}, defense={strengths.get('defense', 1.0)}")
                        return TeamStrength(
                            team_id=team.id,
                            attack=float(strengths.get('attack', 1.0)),
                            defense=float(strengths.get('defense', 1.0))
                        )
                    elif str(team.id) in team_strengths_dict:
                        strengths = team_strengths_dict[str(team.id)]
                        logger.debug(f"Using model strengths (string key) for team {team.id}: attack={strengths.get('attack', 1.0)}, defense={strengths.get('defense', 1.0)}")
                        return TeamStrength(
                            team_id=team.id,
                            attack=float(strengths.get('attack', 1.0)),
                            defense=float(strengths.get('defense', 1.0))
                        )
                    else:
                        # Use database ratings (like old code)
                        logger.debug(f"Using DB ratings for team {team.id}: attack={team.attack_rating}, defense={team.defense_rating}")
                        return TeamStrength(
                            team_id=team.id,
                            attack=float(team.attack_rating) if team.attack_rating else 1.0,
                            defense=float(team.defense_rating) if team.defense_rating else 1.0
                        )
                else:
                    logger.warning(f"Team '{team_name}' not found in database (fuzzy match failed), using default strengths (1.0, 1.0)")
            
            # Fallback to default
            logger.warning(f"Using default team strengths for '{team_name}' (ID: {team_id_from_fixture})")
            return TeamStrength(
                team_id=team_id_from_fixture or 0,
                attack=1.0,
                defense=1.0
            )
        
        # Prepare fixtures data
        fixtures_data = []
        for fixture in fixtures:
            # JackpotFixture uses odds_home, odds_draw, odds_away
            odds_data = {
                "home": float(fixture.odds_home) if fixture.odds_home else 2.0,
                "draw": float(fixture.odds_draw) if fixture.odds_draw else 3.0,
                "away": float(fixture.odds_away) if fixture.odds_away else 2.5
            }
            
            fixture_dict = {
                "id": str(fixture.id),
                "homeTeam": fixture.home_team or "",
                "awayTeam": fixture.away_team or "",
                "odds": odds_data
            }
            fixtures_data.append(fixture_dict)
        
        # Generate probability sets for all fixtures
        probability_sets: Dict[str, List[Dict]] = {}
        
        for set_id in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
            probability_sets[set_id] = []
        
        # For each fixture, generate probabilities
        logger.info(f"Processing {len(fixtures)} fixtures...")
        team_match_stats = {"found": 0, "not_found": 0, "model_strengths": 0, "db_strengths": 0, "default_strengths": 0}
        
        for idx, fixture_obj in enumerate(fixtures):
            logger.debug(f"Processing fixture {idx + 1}/{len(fixtures)}: {fixture_obj.home_team} vs {fixture_obj.away_team}")
            
            # Get team IDs from fixture if available
            home_team_id = getattr(fixture_obj, 'home_team_id', None)
            away_team_id = getattr(fixture_obj, 'away_team_id', None)
            
            # Get team strengths from model or database
            home_team_strength = get_team_strength_for_fixture(
                fixture_obj.home_team or "",
                home_team_id
            )
            away_team_strength = get_team_strength_for_fixture(
                fixture_obj.away_team or "",
                away_team_id
            )
            
            # Track statistics
            if home_team_strength.attack == 1.0 and home_team_strength.defense == 1.0:
                team_match_stats["default_strengths"] += 1
            elif home_team_strength.team_id in team_strengths_dict or str(home_team_strength.team_id) in team_strengths_dict:
                team_match_stats["model_strengths"] += 1
            else:
                team_match_stats["db_strengths"] += 1
            
            if away_team_strength.attack == 1.0 and away_team_strength.defense == 1.0:
                team_match_stats["default_strengths"] += 1
            elif away_team_strength.team_id in team_strengths_dict or str(away_team_strength.team_id) in team_strengths_dict:
                team_match_stats["model_strengths"] += 1
            else:
                team_match_stats["db_strengths"] += 1
            
            # Calculate base probabilities using Dixon-Coles with model parameters
            params = DixonColesParams(
                rho=model_params['rho'],
                home_advantage=model_params['home_advantage'],
                xi=model_params.get('xi', 0.0065)
            )
            base_probs = calculate_match_probabilities(
                home_team_strength,
                away_team_strength,
                params
            )
            
            # ============================================================
            # DRAW PRIOR INJECTION (Fix structural draw underestimation)
            # ============================================================
            # Apply per-league draw prior adjustment upstream
            from app.models.draw_prior import inject_draw_prior
            
            # Get league code from fixture if available
            league_code = None
            if hasattr(fixture_obj, 'league_id') and fixture_obj.league_id:
                # Try to get league code from database
                from app.db.models import League
                league = db.query(League).filter(League.id == fixture_obj.league_id).first()
                if league:
                    league_code = league.code
            
            # Inject draw prior before temperature scaling
            adjusted_home, adjusted_draw, adjusted_away = inject_draw_prior(
                base_probs.home,
                base_probs.draw,
                base_probs.away,
                league_code=league_code
            )
            
            # Update base_probs with draw-prior-adjusted values
            base_probs = MatchProbabilities(
                home=adjusted_home,
                draw=adjusted_draw,
                away=adjusted_away,
                entropy=base_probs.entropy,  # Recalculate after adjustment
                lambda_home=base_probs.lambda_home,
                lambda_away=base_probs.lambda_away
            )
            
            # Recalculate entropy after draw prior injection
            base_probs.entropy = -sum(
                p * math.log2(p) if p > 0 else 0
                for p in [base_probs.home, base_probs.draw, base_probs.away]
            )
            
            # ============================================================
            # TEMPERATURE SCALING (Probability Softening)
            # ============================================================
            # Apply temperature scaling to reduce overconfidence
            from app.models.uncertainty import temperature_scale
            
            # Get temperature from model (learned during training) or use default
            temperature = 1.2  # Default
            if model and model.model_weights:
                temperature = model.model_weights.get('temperature', 1.2)
                # Also check base model if this is a calibration model
                if model.model_type == "calibration":
                    base_model_id = model.model_weights.get('base_model_id')
                    if base_model_id:
                        base_model = db.query(Model).filter(Model.id == base_model_id).first()
                        if base_model and base_model.model_weights:
                            temperature = base_model.model_weights.get('temperature', temperature)
            
            # Apply temperature scaling to base probabilities
            raw_model_probs = (base_probs.home, base_probs.draw, base_probs.away)
            model_probs_scaled = temperature_scale(raw_model_probs, temperature)
            
            # Create temperature-scaled MatchProbabilities object
            from app.models.uncertainty import entropy
            
            base_probs_scaled = MatchProbabilities(
                home=model_probs_scaled[0],
                draw=model_probs_scaled[1],
                away=model_probs_scaled[2],
                entropy=entropy(model_probs_scaled),
                lambda_home=base_probs.lambda_home if hasattr(base_probs, 'lambda_home') else None,
                lambda_away=base_probs.lambda_away if hasattr(base_probs, 'lambda_away') else None
            )
            
            # Use scaled probabilities for blending
            base_probs_for_blending = base_probs_scaled
            
            # Get market odds from fixture
            market_odds = None
            if fixture_obj.odds_home:
                market_odds = {
                    "home": float(fixture_obj.odds_home),
                    "draw": float(fixture_obj.odds_draw),
                    "away": float(fixture_obj.odds_away)
                }
            
            # Get blend alpha from blending model if available (for Set B)
            blend_alpha = 0.6  # Default
            if model and model.model_type == "blending" and model.model_weights:
                blend_alpha = model.model_weights.get('blend_alpha', 0.6)
                logger.debug(f"Using trained blend_alpha={blend_alpha} from blending model")
            elif model and model.model_type == "calibration":
                # Calibration model references a blending model
                base_model_id = model.model_weights.get('base_model_id')
                if base_model_id:
                    base_model = db.query(Model).filter(Model.id == base_model_id).first()
                    if base_model and base_model.model_type == "blending" and base_model.model_weights:
                        blend_alpha = base_model.model_weights.get('blend_alpha', 0.6)
                        logger.debug(f"Using trained blend_alpha={blend_alpha} from blending model (via calibration)")
            
            # Generate all probability sets with draw model integration
            # Extract lambda values from base_probs for draw model
            lambda_home = base_probs.lambda_home if hasattr(base_probs, 'lambda_home') and base_probs.lambda_home is not None else None
            lambda_away = base_probs.lambda_away if hasattr(base_probs, 'lambda_away') and base_probs.lambda_away is not None else None
            
            # If lambda values not available, calculate from expected goals
            if lambda_home is None or lambda_away is None:
                from app.models.dixon_coles import calculate_expected_goals
                expectations = calculate_expected_goals(home_team_strength, away_team_strength, params)
                lambda_home = expectations.lambda_home
                lambda_away = expectations.lambda_away
            
            # Compute draw components using draw model if market odds are available
            draw_components = None
            if market_odds:
                try:
                    from app.models.draw_model import compute_draw_probability, DrawModelConfig
                    draw_result = compute_draw_probability(
                        lambda_home=lambda_home,
                        lambda_away=lambda_away,
                        rho=model_params['rho'],
                        odds=market_odds,
                        config=DrawModelConfig()
                    )
                    draw_components = draw_result["components"]
                    logger.debug(f"Draw model components: {draw_components}")
                except Exception as e:
                    logger.warning(f"Draw model computation failed: {e}, continuing without draw components")
            
            # Use original base_probs for Set A (pure model), but scaled for blending
            all_sets = generate_all_probability_sets(
                base_probs,  # Set A uses original (for display of pure model)
                market_odds,
                calibration_curves=None,
                return_metadata=False,
                use_draw_model=True,
                rho=model_params['rho'],
                lambda_home=lambda_home,
                lambda_away=lambda_away
            )
            
            # Override Set B with entropy-weighted blending using temperature-scaled probabilities
            if market_odds and (model and model.model_type in ["blending", "calibration"]):
                from app.models.probability_sets import blend_probabilities, odds_to_implied_probabilities
                from app.models.uncertainty import entropy_weighted_alpha, normalized_entropy, overround_aware_market_weight
                
                market_probs = odds_to_implied_probabilities(market_odds)
                
                # Calculate overround from odds
                overround = (1.0 / market_odds["home"] + 1.0 / market_odds["draw"] + 1.0 / market_odds["away"]) - 1.0
                
                # Use entropy-weighted blending (v2)
                alpha_eff = entropy_weighted_alpha(
                    base_alpha=blend_alpha,
                    model_probs=(base_probs_for_blending.home, base_probs_for_blending.draw, base_probs_for_blending.away)
                )
                
                # Apply overround-aware market weight adjustment
                market_weight_base = 1.0 - alpha_eff
                market_weight_adj = overround_aware_market_weight(market_weight_base, overround, k=2.0)
                
                # Renormalize weights after overround adjustment
                total_weight = alpha_eff + market_weight_adj
                if total_weight > 0:
                    alpha_eff_normalized = alpha_eff / total_weight
                    market_weight_normalized = market_weight_adj / total_weight
                else:
                    alpha_eff_normalized = alpha_eff
                    market_weight_normalized = market_weight_base
                
                # Blend with adjusted weights
                blended_home = alpha_eff_normalized * base_probs_for_blending.home + market_weight_normalized * market_probs.home
                blended_draw = alpha_eff_normalized * base_probs_for_blending.draw + market_weight_normalized * market_probs.draw
                blended_away = alpha_eff_normalized * base_probs_for_blending.away + market_weight_normalized * market_probs.away
                
                # Normalize
                total = blended_home + blended_draw + blended_away
                if total > 0:
                    blended_home /= total
                    blended_draw /= total
                    blended_away /= total
                
                # Create blended probabilities with metadata
                set_b_probs = MatchProbabilities(
                    home=blended_home,
                    draw=blended_draw,
                    away=blended_away,
                    entropy=entropy((blended_home, blended_draw, blended_away))
                )
                
                # Store metadata as attributes (will be extracted later)
                set_b_probs.alpha_effective = alpha_eff
                set_b_probs.temperature = temperature
                set_b_probs.model_entropy = normalized_entropy((base_probs_for_blending.home, base_probs_for_blending.draw, base_probs_for_blending.away))
                
                all_sets["B"] = set_b_probs
                logger.debug(f"Set B recalculated with entropy-weighted alpha_eff={alpha_eff:.3f}, temperature={temperature:.2f}")
            
            # Convert to output format (as dictionaries for JSON serialization)
            for set_id, probs in all_sets.items():
                output = {
                    "homeWinProbability": round(probs.home * 100, 2),
                    "drawProbability": round(probs.draw * 100, 2),
                    "awayWinProbability": round(probs.away * 100, 2),
                    "entropy": round(probs.entropy, 4) if hasattr(probs, 'entropy') and probs.entropy is not None else None,
                    "calibrated": PROBABILITY_SET_METADATA.get(set_id, {}).get("calibrated", True),
                    "heuristic": PROBABILITY_SET_METADATA.get(set_id, {}).get("heuristic", False),
                    "allowedForDecisionSupport": PROBABILITY_SET_METADATA.get(set_id, {}).get("allowed_for_decision_support", True)
                }
                
                # Add uncertainty metadata for Set B (entropy-weighted blending)
                if set_id == "B" and hasattr(probs, 'alpha_effective'):
                    output["alphaEffective"] = round(probs.alpha_effective, 4)
                    output["temperature"] = round(probs.temperature, 3)
                    output["modelEntropy"] = round(probs.model_entropy, 4) if hasattr(probs, 'model_entropy') else None
                
                # Add draw components for explainability (only for Set A, B, C which use draw model)
                if draw_components and set_id in ["A", "B", "C"]:
                    output["drawComponents"] = {
                        "poisson": round(draw_components.get("poisson", 0.0), 4),
                        "dixonColes": round(draw_components.get("dixon_coles", 0.0), 4),
                        "market": round(draw_components.get("market", 0.0), 4) if draw_components.get("market") is not None else None
                    }
                
                probability_sets[set_id].append(output)
            
        # Log summary statistics
        logger.info(f"=== PROBABILITY CALCULATION COMPLETE ===")
        logger.info(f"Team matching stats: {team_match_stats}")
        logger.info(f"Total fixtures processed: {len(fixtures)}")
        logger.info(f"Teams using default strengths: {team_match_stats['default_strengths']}")
        logger.info(f"Teams using model strengths: {team_match_stats['model_strengths']}")
        logger.info(f"Teams using DB strengths: {team_match_stats['db_strengths']}")
        
        # Return in format expected by frontend
        return {
            "predictionId": f"{jackpot_id}-{datetime.now().isoformat()}",
            "modelVersion": model.version if model else "unknown",
            "createdAt": datetime.now().isoformat(),
            "fixtures": fixtures_data,
            "probabilitySets": probability_sets,
            "confidenceFlags": {},
            "warnings": []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating probabilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-results/all", response_model=ApiResponse)
async def get_all_saved_results(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all saved probability results across all jackpots"""
    try:
        saved_results = db.query(SavedProbabilityResult).order_by(
            SavedProbabilityResult.created_at.desc()
        ).limit(limit).all()
        
        results = [{
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "jackpotId": r.jackpot_id,
            "selections": r.selections,
            "actualResults": r.actual_results or {},
            "scores": r.scores or {},
            "modelVersion": r.model_version,
            "totalFixtures": r.total_fixtures,
            "createdAt": r.created_at.isoformat(),
            "updatedAt": r.updated_at.isoformat()
        } for r in saved_results]
        
        return ApiResponse(
            success=True,
            message=f"Found {len(results)} saved results",
            data={"results": results}
        )
    except Exception as e:
        logger.error(f"Error fetching all saved results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-results/latest", response_model=ApiResponse)
async def get_latest_saved_result(
    db: Session = Depends(get_db)
):
    """Get the most recent saved probability result across all jackpots"""
    try:
        latest_result = db.query(SavedProbabilityResult).order_by(
            SavedProbabilityResult.created_at.desc()
        ).first()
        
        if not latest_result:
            return ApiResponse(
                success=True,
                message="No saved results found",
                data={"result": None}
            )
        
        result = {
            "id": latest_result.id,
            "name": latest_result.name,
            "description": latest_result.description,
            "jackpotId": latest_result.jackpot_id,
            "selections": latest_result.selections,
            "actualResults": latest_result.actual_results or {},
            "scores": latest_result.scores or {},
            "modelVersion": latest_result.model_version,
            "totalFixtures": latest_result.total_fixtures,
            "createdAt": latest_result.created_at.isoformat(),
            "updatedAt": latest_result.updated_at.isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Latest saved result retrieved",
            data={"result": result}
        )
    except Exception as e:
        logger.error(f"Error fetching latest saved result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{jackpot_id}/saved-results", response_model=ApiResponse)
async def get_saved_results(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Get all saved probability results for a jackpot"""
    try:
        saved_results = db.query(SavedProbabilityResult).filter(
            SavedProbabilityResult.jackpot_id == jackpot_id
        ).order_by(SavedProbabilityResult.created_at.desc()).all()
        
        results = [{
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "jackpotId": r.jackpot_id,
            "selections": r.selections,
            "actualResults": r.actual_results or {},
            "scores": r.scores or {},
            "modelVersion": r.model_version,
            "totalFixtures": r.total_fixtures,
            "createdAt": r.created_at.isoformat(),
            "updatedAt": r.updated_at.isoformat()
        } for r in saved_results]
        
        return ApiResponse(
            success=True,
            message=f"Found {len(results)} saved results",
            data={"results": results}
        )
    except Exception as e:
        logger.error(f"Error fetching saved results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{jackpot_id}/save-result", response_model=ApiResponse)
async def save_probability_result(
    jackpot_id: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Save probability results with selections, actual results, and scores.
    
    Args:
        jackpot_id: The jackpot ID
        data: Dictionary containing:
            - name: Name of the saved result
            - description: Optional description
            - selections: Dict mapping set_id to fixture selections {"A": {"fixtureId": "1", ...}, ...}
            - actual_results: Optional dict mapping fixture IDs to actual results
            - scores: Optional dict mapping set_id to score {"A": {"correct": 10, "total": 15}, ...}
    
    Returns:
        ApiResponse with saved result data
    """
    try:
        logger.info(f"=== SAVE PROBABILITY RESULT REQUEST ===")
        logger.info(f"Jackpot ID: {jackpot_id}")
        logger.info(f"Data keys: {list(data.keys())}")
        
        # Validate required fields
        if not data.get("name"):
            raise HTTPException(status_code=400, detail="Name is required")
        
        if not data.get("selections"):
            raise HTTPException(status_code=400, detail="Selections are required")
        
        # Get active model version
        model = db.query(Model).filter(Model.status == ModelStatus.active).first()
        model_version = model.version if model else None
        
        # Count total fixtures from selections
        total_fixtures = 0
        if data.get("selections"):
            # Get the first set to count fixtures
            first_set = list(data["selections"].values())[0] if data["selections"] else {}
            total_fixtures = len(first_set)
        
        # Create saved result
        saved_result = SavedProbabilityResult(
            jackpot_id=jackpot_id,
            user_id=None,  # TODO: Get from auth context if available
            name=data["name"],
            description=data.get("description"),
            selections=data["selections"],
            actual_results=data.get("actual_results"),
            scores=data.get("scores"),
            model_version=model_version,
            total_fixtures=total_fixtures
        )
        
        db.add(saved_result)
        db.commit()
        db.refresh(saved_result)
        
        logger.info(f"Saved probability result: ID={saved_result.id}, name={saved_result.name}, fixtures={total_fixtures}")
        
        return ApiResponse(
            success=True,
            message="Probability result saved successfully",
            data={
                "id": saved_result.id,
                "name": saved_result.name,
                "description": saved_result.description,
                "jackpotId": saved_result.jackpot_id,
                "selections": saved_result.selections,
                "actualResults": saved_result.actual_results or {},
                "scores": saved_result.scores or {},
                "modelVersion": saved_result.model_version,
                "totalFixtures": saved_result.total_fixtures,
                "createdAt": saved_result.created_at.isoformat(),
                "updatedAt": saved_result.updated_at.isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving probability result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validation/export", response_model=ApiResponse)
async def export_validation_to_training(
    validation_ids: List[str] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Export validation data to validation_results table for calibration training.
    
    Args:
        validation_ids: List of validation IDs in format "savedResultId-setId" (e.g., ["2-B", "3-A"])
    
    Returns:
        ApiResponse with export results
    """
    try:
        exported_count = 0
        errors = []
        
        # Get active model for reference
        model = db.query(Model).filter(Model.status == ModelStatus.active).first()
        
        for validation_id_str in validation_ids:
            try:
                # Parse validation ID: "savedResultId-setId"
                parts = validation_id_str.split('-')
                if len(parts) != 2:
                    errors.append(f"Invalid validation_id format: {validation_id_str}")
                    continue
                
                saved_result_id = int(parts[0])
                set_id = parts[1].upper()
                
                # Validate set_id
                if set_id not in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                    errors.append(f"Invalid set_id: {set_id} in {validation_id_str}")
                    continue
                
                # Load saved result
                saved_result = db.query(SavedProbabilityResult).filter(
                    SavedProbabilityResult.id == saved_result_id
                ).first()
                
                if not saved_result:
                    errors.append(f"Saved result {saved_result_id} not found")
                    continue
                
                # Get jackpot
                jackpot = db.query(JackpotModel).filter(
                    JackpotModel.jackpot_id == saved_result.jackpot_id
                ).first()
                
                if not jackpot:
                    errors.append(f"Jackpot {saved_result.jackpot_id} not found for saved result {saved_result_id}")
                    continue
                
                # Get fixtures
                fixtures = db.query(JackpotFixture).filter(
                    JackpotFixture.jackpot_id == jackpot.id
                ).order_by(JackpotFixture.match_order).all()
                
                if not fixtures:
                    errors.append(f"No fixtures found for jackpot {jackpot.jackpot_id}")
                    continue
                
                # Re-calculate probabilities for this jackpot to get set probabilities
                # This ensures we have the correct probabilities for the set
                prob_response = await calculate_probabilities(saved_result.jackpot_id, db)
                all_probability_sets = prob_response.get("probabilitySets", {})
                
                set_probabilities = all_probability_sets.get(set_id)
                if not set_probabilities or len(set_probabilities) != len(fixtures):
                    errors.append(f"Probabilities for set {set_id} not found or mismatch for jackpot {saved_result.jackpot_id}")
                    continue
                
                # Calculate metrics
                total_matches = 0
                correct_predictions = 0
                total_brier = 0.0
                total_log_loss = 0.0
                
                home_correct = 0
                home_total = 0
                draw_correct = 0
                draw_total = 0
                away_correct = 0
                away_total = 0
                
                # Helper to convert result format
                def convert_result(result_str: str) -> str:
                    """Convert 1/X/2 to H/D/A"""
                    if result_str == "1":
                        return "H"
                    elif result_str == "X":
                        return "D"
                    elif result_str == "2":
                        return "A"
                    return result_str.upper()
                
                for idx, fixture in enumerate(fixtures):
                    fixture_id = str(fixture.id)
                    actual_result_str = saved_result.actual_results.get(fixture_id) if saved_result.actual_results else None
                    
                    if not actual_result_str:
                        continue
                    
                    total_matches += 1
                    actual_result = convert_result(actual_result_str)
                    
                    # Get prediction for this set
                    prediction_for_fixture = None
                    if saved_result.selections and saved_result.selections.get(set_id):
                        prediction_for_fixture = saved_result.selections[set_id].get(fixture_id)
                    
                    # If no saved selection, use highest probability
                    if not prediction_for_fixture:
                        prob_output = set_probabilities[idx]
                        if prob_output:
                            if prob_output["homeWinProbability"] >= prob_output["drawProbability"] and \
                               prob_output["homeWinProbability"] >= prob_output["awayWinProbability"]:
                                prediction_for_fixture = "1"
                            elif prob_output["awayWinProbability"] >= prob_output["homeWinProbability"] and \
                                 prob_output["awayWinProbability"] >= prob_output["drawProbability"]:
                                prediction_for_fixture = "2"
                            else:
                                prediction_for_fixture = "X"
                    
                    if not prediction_for_fixture:
                        continue
                    
                    predicted_outcome = convert_result(prediction_for_fixture)
                    
                    # Check if correct
                    if predicted_outcome == actual_result:
                        correct_predictions += 1
                    
                    # Update outcome breakdown
                    if actual_result == 'H':
                        home_total += 1
                        if predicted_outcome == 'H':
                            home_correct += 1
                    elif actual_result == 'D':
                        draw_total += 1
                        if predicted_outcome == 'D':
                            draw_correct += 1
                    elif actual_result == 'A':
                        away_total += 1
                        if predicted_outcome == 'A':
                            away_correct += 1
                    
                    # Calculate Brier score and log loss
                    prob_output = set_probabilities[idx]
                    predictedH = prob_output["homeWinProbability"] / 100
                    predictedD = prob_output["drawProbability"] / 100
                    predictedA = prob_output["awayWinProbability"] / 100
                    
                    actualH = 1 if actual_result == 'H' else 0
                    actualD = 1 if actual_result == 'D' else 0
                    actualA = 1 if actual_result == 'A' else 0
                    
                    # Brier score
                    brier = (predictedH - actualH)**2 + (predictedD - actualD)**2 + (predictedA - actualA)**2
                    total_brier += brier
                    
                    # Log loss
                    log_loss = -(
                        actualH * math.log(max(predictedH, 1e-10)) +
                        actualD * math.log(max(predictedD, 1e-10)) +
                        actualA * math.log(max(predictedA, 1e-10))
                    )
                    total_log_loss += log_loss
                
                if total_matches > 0:
                    accuracy = (correct_predictions / total_matches) * 100
                    brier_score = total_brier / total_matches
                    log_loss = total_log_loss / total_matches
                    
                    # Convert set_id to PredictionSet enum
                    set_enum_map = {
                        "A": PredictionSet.A,
                        "B": PredictionSet.B,
                        "C": PredictionSet.C,
                        "D": PredictionSet.D,
                        "E": PredictionSet.E,
                        "F": PredictionSet.F,
                        "G": PredictionSet.G,
                        "H": PredictionSet.H,
                        "I": PredictionSet.I,
                        "J": PredictionSet.J,
                    }
                    
                    # Store in ValidationResult table
                    validation_entry = ValidationResult(
                        jackpot_id=jackpot.id,
                        set_type=set_enum_map[set_id],
                        model_id=model.id if model else None,
                        total_matches=total_matches,
                        correct_predictions=correct_predictions,
                        accuracy=accuracy,
                        brier_score=brier_score,
                        log_loss=log_loss,
                        home_correct=home_correct,
                        home_total=home_total,
                        draw_correct=draw_correct,
                        draw_total=draw_total,
                        away_correct=away_correct,
                        away_total=away_total,
                        exported_to_training=True,
                        exported_at=datetime.now()
                    )
                    db.add(validation_entry)
                    exported_count += 1
                    logger.info(f"Exported validation: saved_result_id={saved_result_id}, set={set_id}, matches={total_matches}, accuracy={accuracy:.2f}%")
            
            except Exception as e:
                error_msg = f"Error processing validation {validation_id_str}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        db.commit()
        
        message = f"Successfully exported {exported_count} validation results to training."
        if errors:
            message += f" {len(errors)} errors occurred: {', '.join(errors[:5])}"
        
        return ApiResponse(
            success=True,
            message=message,
            data={
                "exported_count": exported_count,
                "errors": errors if errors else None
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error exporting validation data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
