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
    SavedProbabilityResult, ValidationResult, PredictionSet, CalibrationData, MatchResult,
    MatchWeather, TeamRestDays, OddsMovement, League, TeamForm, TeamInjuries
)
from app.models.calibration import calculate_brier_score, calculate_log_loss
from app.services.team_resolver import resolve_team_safe
from datetime import datetime, date, time
import logging
import pickle
import base64
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/probabilities", tags=["probabilities"])


@router.get("/{jackpot_id}/probabilities", response_model=ApiResponse)
async def calculate_probabilities(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Calculate probabilities for a jackpot - returns all sets (A-G)"""
    logger.info(f"=== COMPUTE PROBABILITIES REQUEST ===")
    logger.info(f"Jackpot ID: {jackpot_id}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Ensure we start with a clean transaction state
    try:
        db.rollback()  # Rollback any existing transaction to start fresh
    except Exception:
        pass  # Ignore if no transaction exists
    
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
        
        # Load calibrator if calibration model is active
        calibrator = None
        if calibration_model:
            model = calibration_model
            logger.info(f"Found calibration model: {calibration_model.version}")
            
            # Load calibration curves from calibration_data table
            from app.models.calibration import Calibrator
            from app.db.models import CalibrationData, MatchResult
            import numpy as np
            
            calibrator = Calibrator()
            calibration_data_records = db.query(CalibrationData).filter(
                CalibrationData.model_id == calibration_model.id
            ).all()
            
            if calibration_data_records:
                logger.info(f"Loading {len(calibration_data_records)} calibration data records for model {calibration_model.id}")
                # Group by outcome type
                calibration_by_outcome = {"H": [], "D": [], "A": []}
                for record in calibration_data_records:
                    outcome_str = record.outcome_type.value if hasattr(record.outcome_type, 'value') else str(record.outcome_type)
                    if outcome_str in calibration_by_outcome:
                        calibration_by_outcome[outcome_str].append({
                            'predicted': record.predicted_prob_bucket,
                            'actual': record.actual_frequency,
                            'count': record.sample_count
                        })
                
                # Log summary of calibration data
                for outcome_type in ["H", "D", "A"]:
                    if calibration_by_outcome[outcome_type]:
                        buckets = calibration_by_outcome[outcome_type]
                        total_samples = sum(b['count'] for b in buckets)
                        logger.info(f"Calibration data for {outcome_type}: {len(buckets)} buckets, {total_samples} total samples")
                
                # Reconstruct IsotonicRegression from buckets
                # We create synthetic training data by replicating each bucket proportionally
                for outcome_type in ["H", "D", "A"]:
                    if calibration_by_outcome[outcome_type]:
                        # Sort by predicted probability
                        buckets = sorted(calibration_by_outcome[outcome_type], key=lambda x: x['predicted'])
                        
                        # Create synthetic training data
                        synthetic_preds = []
                        synthetic_acts = []
                        
                        for bucket in buckets:
                            # Replicate each bucket's data points proportionally
                            # Use predicted_prob_bucket as input
                            # actual_frequency tells us what proportion should be 1
                            num_samples = max(bucket['count'], 1)  # At least 1 sample per bucket
                            # Limit replication to avoid memory issues, but preserve proportions
                            num_samples = min(num_samples, 200)
                            
                            # Calculate how many should be 1 based on actual_frequency
                            num_positive = int(round(num_samples * bucket['actual']))
                            num_negative = num_samples - num_positive
                            
                            # Add positive samples
                            for _ in range(num_positive):
                                synthetic_preds.append(bucket['predicted'])
                                synthetic_acts.append(1)
                            
                            # Add negative samples
                            for _ in range(num_negative):
                                synthetic_preds.append(bucket['predicted'])
                                synthetic_acts.append(0)
                        
                        if len(synthetic_preds) > 0:
                            try:
                                calibrator.fit(synthetic_preds, synthetic_acts, outcome_type)
                                # Verify calibrator is fitted
                                meta = calibrator.metadata.get(outcome_type)
                                if meta and meta.fitted:
                                    logger.info(f"✓ Reconstructed calibrator for {outcome_type} from {len(buckets)} buckets ({len(synthetic_preds)} synthetic samples, {meta.sample_count} actual samples)")
                                else:
                                    logger.warning(f"⚠ Calibrator fit attempted for {outcome_type} but not marked as fitted")
                            except Exception as e:
                                logger.error(f"✗ Failed to reconstruct calibrator for {outcome_type}: {e}", exc_info=True)
                    else:
                        logger.warning(f"No calibration data found for outcome {outcome_type}")
            else:
                logger.warning(f"No calibration data records found for calibration model {calibration_model.id}")
            
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
        
        # Eagerly access ALL model attributes NOW to avoid lazy loading issues later
        # Store values we'll need in local variables
        model_weights_cache = {}
        model_type_cache = None
        model_version_cache = None
        model_id_cache = None
        
        if model:
            try:
                # Force access to all model attributes now, before we start processing fixtures
                # This prevents lazy loading after transaction issues
                model_weights_cache = model.model_weights or {} if hasattr(model, 'model_weights') else {}
                model_type_cache = model.model_type if hasattr(model, 'model_type') else None
                model_version_cache = model.version if hasattr(model, 'version') else None
                model_id_cache = model.id if hasattr(model, 'id') else None
                logger.debug(f"Cached model attributes: type={model_type_cache}, version={model_version_cache}, id={model_id_cache}, weights_keys={list(model_weights_cache.keys())}")
            except Exception as e:
                logger.warning(f"Failed to access model attributes upfront: {e}", exc_info=True)
                model_weights_cache = {}
                model_type_cache = None
                model_version_cache = None
                model_id_cache = None
        
        # Cache for team data (populated during team ID resolution)
        # Store primitive values instead of SQLAlchemy objects to avoid lazy loading issues
        team_cache = {}  # {team_id: {'id': int, 'attack_rating': float, 'defense_rating': float, 'canonical_name': str}}
        
        # Helper function to get team strength (using cached team data to avoid database queries)
        def get_team_strength_for_fixture(team_name: str, team_id_from_fixture: Optional[int] = None) -> TeamStrength:
            """Get team strength from model or cached team data"""
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
            
                # Try to get team from cache (avoid database query)
                if team_id_from_fixture in team_cache:
                    team_data = team_cache[team_id_from_fixture]
                    logger.debug(f"Found team {team_id_from_fixture} in cache: '{team_data.get('canonical_name', 'unknown')}'")
                    # Use database ratings from cached team data (primitive values, no lazy loading)
                    return TeamStrength(
                        team_id=team_data['id'],
                        attack=float(team_data.get('attack_rating', 1.0)) if team_data.get('attack_rating') else 1.0,
                        defense=float(team_data.get('defense_rating', 1.0)) if team_data.get('defense_rating') else 1.0
                    )
            
            # Fallback: try to resolve team name (only if not in cache and transaction is OK)
            if team_name:
                try:
                    team = resolve_team_safe(db, team_name)
                    if team:
                        team_id = team.id
                        # Extract all attributes NOW before any commits
                        team_data = {
                            'id': team_id,
                            'attack_rating': float(team.attack_rating) if team.attack_rating else None,
                            'defense_rating': float(team.defense_rating) if team.defense_rating else None,
                            'canonical_name': team.canonical_name or team_name
                        }
                        logger.debug(f"Found team '{team_name}' -> DB team '{team_data['canonical_name']}' (ID: {team_id})")
                        # Cache primitive values for future use
                        team_cache[team_id] = team_data
                        # Check if this team is in model's team_strengths
                        if team_id in team_strengths_dict:
                            strengths = team_strengths_dict[team_id]
                            return TeamStrength(
                                team_id=team_id,
                                attack=float(strengths.get('attack', 1.0)),
                                defense=float(strengths.get('defense', 1.0))
                            )
                        elif str(team_id) in team_strengths_dict:
                            strengths = team_strengths_dict[str(team_id)]
                            return TeamStrength(
                                team_id=team_id,
                                attack=float(strengths.get('attack', 1.0)),
                                defense=float(strengths.get('defense', 1.0))
                            )
                        else:
                            # Use database ratings from extracted data
                            return TeamStrength(
                                team_id=team_id,
                                attack=team_data['attack_rating'] if team_data['attack_rating'] else 1.0,
                                defense=team_data['defense_rating'] if team_data['defense_rating'] else 1.0
                            )
                except Exception as e:
                    # If database query fails (transaction aborted), use defaults
                    logger.warning(f"Could not resolve team '{team_name}' (transaction may be aborted): {e}")
            
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
                "homeTeamId": fixture.home_team_id,  # Include team IDs for injury tracking
                "awayTeamId": fixture.away_team_id,  # Include team IDs for injury tracking
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
        
        # Cache all fixture attributes upfront to avoid lazy loading after commits
        fixture_cache = []
        for fixture_obj in fixtures:
            fixture_cache.append({
                'id': fixture_obj.id,
                'home_team': fixture_obj.home_team,
                'away_team': fixture_obj.away_team,
                'odds_home': fixture_obj.odds_home,
                'odds_draw': fixture_obj.odds_draw,
                'odds_away': fixture_obj.odds_away,
                'home_team_id': getattr(fixture_obj, 'home_team_id', None),
                'away_team_id': getattr(fixture_obj, 'away_team_id', None),
                'league_id': getattr(fixture_obj, 'league_id', None),
                'fixture_obj': fixture_obj  # Keep reference for updates
            })
        
        # Resolve ALL team IDs and cache team objects upfront BEFORE processing fixtures to avoid transaction issues
        logger.info("Resolving team IDs and caching team objects for all fixtures...")
        
        for fixture_data in fixture_cache:
            fixture_obj = fixture_data['fixture_obj']
            team_ids_updated = False
            
            # Resolve team IDs if missing and cache team data (primitive values, not objects)
            if not fixture_data.get('home_team_id') and fixture_data['home_team']:
                try:
                    home_team = resolve_team_safe(db, fixture_data['home_team'])
                    if home_team:
                        home_team_id = home_team.id
                        fixture_obj.home_team_id = home_team_id
                        fixture_data['home_team_id'] = home_team_id
                        # Extract all attributes NOW before any commits (avoid lazy loading later)
                        team_cache[home_team_id] = {
                            'id': home_team_id,
                            'attack_rating': float(home_team.attack_rating) if home_team.attack_rating else None,
                            'defense_rating': float(home_team.defense_rating) if home_team.defense_rating else None,
                            'canonical_name': home_team.canonical_name or fixture_data['home_team']
                        }
                        team_ids_updated = True
                        logger.debug(f"Resolved home team '{fixture_data['home_team']}' -> ID {home_team_id}")
                except Exception as e:
                    logger.warning(f"Failed to resolve home team '{fixture_data['home_team']}': {e}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
            
            if not fixture_data.get('away_team_id') and fixture_data['away_team']:
                try:
                    away_team = resolve_team_safe(db, fixture_data['away_team'])
                    if away_team:
                        away_team_id = away_team.id
                        fixture_obj.away_team_id = away_team_id
                        fixture_data['away_team_id'] = away_team_id
                        # Extract all attributes NOW before any commits (avoid lazy loading later)
                        team_cache[away_team_id] = {
                            'id': away_team_id,
                            'attack_rating': float(away_team.attack_rating) if away_team.attack_rating else None,
                            'defense_rating': float(away_team.defense_rating) if away_team.defense_rating else None,
                            'canonical_name': away_team.canonical_name or fixture_data['away_team']
                        }
                        team_ids_updated = True
                        logger.debug(f"Resolved away team '{fixture_data['away_team']}' -> ID {away_team_id}")
                except Exception as e:
                    logger.warning(f"Failed to resolve away team '{fixture_data['away_team']}': {e}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
            
            # Commit team ID updates if they were resolved (use savepoint)
            if team_ids_updated:
                try:
                    savepoint = db.begin_nested()
                    try:
                        savepoint.commit()
                        logger.debug(f"✓ Updated team IDs for fixture {fixture_data['id']}: home={fixture_data.get('home_team_id')}, away={fixture_data.get('away_team_id')}")
                    except Exception as e:
                        savepoint.rollback()
                        logger.warning(f"Failed to commit team ID updates: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"Failed to create savepoint for team ID updates: {e}", exc_info=True)
                    try:
                        db.rollback()
                    except Exception:
                        pass
        
        logger.info(f"✓ Completed team ID resolution for {len(fixture_cache)} fixtures, cached {len(team_cache)} team objects")
        
        for idx, fixture_data in enumerate(fixture_cache):
            fixture_obj = fixture_data['fixture_obj']
            logger.debug(f"Processing fixture {idx + 1}/{len(fixture_cache)}: {fixture_data['home_team']} vs {fixture_data['away_team']}")
            
            # Get team IDs from cache (already resolved)
            home_team_id = fixture_data.get('home_team_id')
            away_team_id = fixture_data.get('away_team_id')
            
            # Get team strengths from model or database
            home_team_strength_base = get_team_strength_for_fixture(
                fixture_data['home_team'] or "",
                home_team_id
            )
            away_team_strength_base = get_team_strength_for_fixture(
                fixture_data['away_team'] or "",
                away_team_id
            )
            
            # Apply team-specific adjustments (rest days, form, injuries)
            from app.services.team_adjustments import apply_all_adjustments
            from app.services.team_form_calculator import get_team_form_for_fixture, adjust_team_strength_with_form
            
            # Get rest days for both teams
            home_rest_days = None
            away_rest_days = None
            if fixture_data.get('id'):
                home_rest = db.query(TeamRestDays).filter(
                    TeamRestDays.fixture_id == fixture_data['id'],
                    TeamRestDays.team_id == home_team_id
                ).first()
                if home_rest:
                    home_rest_days = home_rest.rest_days
                
                away_rest = db.query(TeamRestDays).filter(
                    TeamRestDays.fixture_id == fixture_data['id'],
                    TeamRestDays.team_id == away_team_id
                ).first()
                if away_rest:
                    away_rest_days = away_rest.rest_days
            
            # Get team form for both teams
            fixture_date = fixture_data.get('match_date') or (jackpot.kickoff_date if jackpot else None)
            home_form = get_team_form_for_fixture(db, home_team_id, fixture_date) if home_team_id else None
            away_form = get_team_form_for_fixture(db, away_team_id, fixture_date) if away_team_id else None
            
            # Calculate form adjustments
            home_attack_adj, home_defense_adj = adjust_team_strength_with_form(
                home_team_strength_base.attack,
                home_team_strength_base.defense,
                home_form,
                form_weight=0.15
            )
            home_form_attack_mult = home_attack_adj / home_team_strength_base.attack if home_team_strength_base.attack > 0 else 1.0
            home_form_defense_mult = home_defense_adj / home_team_strength_base.defense if home_team_strength_base.defense > 0 else 1.0
            
            away_attack_adj, away_defense_adj = adjust_team_strength_with_form(
                away_team_strength_base.attack,
                away_team_strength_base.defense,
                away_form,
                form_weight=0.15
            )
            away_form_attack_mult = away_attack_adj / away_team_strength_base.attack if away_team_strength_base.attack > 0 else 1.0
            away_form_defense_mult = away_defense_adj / away_team_strength_base.defense if away_team_strength_base.defense > 0 else 1.0
            
            # Get injury data for both teams
            home_injuries = None
            away_injuries = None
            if fixture_data.get('id'):
                home_inj = db.query(TeamInjuries).filter(
                    TeamInjuries.fixture_id == fixture_data['id'],
                    TeamInjuries.team_id == home_team_id
                ).first()
                if home_inj:
                    home_injuries = {
                        'key_players_missing': home_inj.key_players_missing,
                        'injury_severity': home_inj.injury_severity
                    }
                
                away_inj = db.query(TeamInjuries).filter(
                    TeamInjuries.fixture_id == fixture_data['id'],
                    TeamInjuries.team_id == away_team_id
                ).first()
                if away_inj:
                    away_injuries = {
                        'key_players_missing': away_inj.key_players_missing,
                        'injury_severity': away_inj.injury_severity
                    }
            
            # Apply all adjustments
            home_attack_final, home_defense_final = apply_all_adjustments(
                home_team_strength_base.attack,
                home_team_strength_base.defense,
                rest_days=home_rest_days,
                is_home=True,
                form_attack_adjustment=home_form_attack_mult,
                form_defense_adjustment=home_form_defense_mult,
                key_players_missing=home_injuries['key_players_missing'] if home_injuries else None,
                injury_severity=home_injuries['injury_severity'] if home_injuries else None
            )
            
            away_attack_final, away_defense_final = apply_all_adjustments(
                away_team_strength_base.attack,
                away_team_strength_base.defense,
                rest_days=away_rest_days,
                is_home=False,
                form_attack_adjustment=away_form_attack_mult,
                form_defense_adjustment=away_form_defense_mult,
                key_players_missing=away_injuries['key_players_missing'] if away_injuries else None,
                injury_severity=away_injuries['injury_severity'] if away_injuries else None
            )
            
            # Create adjusted team strengths
            home_team_strength = TeamStrength(
                team_id=home_team_strength_base.team_id,
                attack=home_attack_final,
                defense=home_defense_final,
                league_id=home_team_strength_base.league_id
            )
            away_team_strength = TeamStrength(
                team_id=away_team_strength_base.team_id,
                attack=away_attack_final,
                defense=away_defense_final,
                league_id=away_team_strength_base.league_id
            )
            
            # Track statistics (using base strengths before adjustments)
            if home_team_strength_base.attack == 1.0 and home_team_strength_base.defense == 1.0:
                team_match_stats["default_strengths"] += 1
            elif home_team_strength_base.team_id in team_strengths_dict or str(home_team_strength_base.team_id) in team_strengths_dict:
                team_match_stats["model_strengths"] += 1
            else:
                team_match_stats["db_strengths"] += 1
            
            if away_team_strength_base.attack == 1.0 and away_team_strength_base.defense == 1.0:
                team_match_stats["default_strengths"] += 1
            elif away_team_strength_base.team_id in team_strengths_dict or str(away_team_strength_base.team_id) in team_strengths_dict:
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
            if fixture_data.get('league_id'):
                # Try to get league code from database
                from app.db.models import League
                try:
                    league = db.query(League).filter(League.id == fixture_data['league_id']).first()
                    if league:
                        league_code = league.code
                except Exception as e:
                    logger.debug(f"Could not load league: {e}")
            
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
            # AUTOMATIC INGESTION: Weather, Rest Days, Odds Movement
            # ============================================================
            # Automatically ingest missing draw structural features before calculating probabilities
            # Use a savepoint to isolate ingestion errors from main transaction
            # Note: MatchWeather, TeamRestDays, OddsMovement are already imported at top of file
            try:
                from app.services.ingestion.ingest_weather import ingest_weather_from_open_meteo
                from app.services.ingestion.ingest_rest_days import ingest_rest_days_for_fixture
                from app.services.ingestion.ingest_odds_movement import track_odds_movement
                from sqlalchemy import text
                
                # Create a savepoint for this fixture's ingestion
                savepoint = db.begin_nested()
                
                try:
                    # Get fixture date for weather/rest days
                    fixture_date = None
                    if hasattr(fixture_obj, 'match_date') and fixture_obj.match_date:
                        fixture_date = fixture_obj.match_date
                    elif hasattr(fixture_obj, 'jackpot') and fixture_obj.jackpot and fixture_obj.jackpot.kickoff_date:
                        fixture_date = fixture_obj.jackpot.kickoff_date
                    else:
                        fixture_date = date.today()
                    
                    match_datetime = datetime.combine(fixture_date, time(hour=15, minute=0))  # Default to 3 PM
                    
                    # 1. Auto-ingest weather if missing
                    weather_exists = db.query(MatchWeather).filter(
                        MatchWeather.fixture_id == fixture_data['id']
                    ).first()
                    
                    if not weather_exists:
                        try:
                            # Try to get stadium coordinates (use league country capital as fallback)
                            league = db.query(League).filter(League.id == getattr(fixture_obj, 'league_id', None)).first() if getattr(fixture_obj, 'league_id', None) else None
                            
                            # Fallback coordinates (country capitals)
                            country_coords = {
                                'England': {'lat': 51.5074, 'lon': -0.1278},
                                'Spain': {'lat': 40.4168, 'lon': -3.7038},
                                'Germany': {'lat': 52.5200, 'lon': 13.4050},
                                'Italy': {'lat': 41.9028, 'lon': 12.4964},
                                'France': {'lat': 48.8566, 'lon': 2.3522},
                                'Netherlands': {'lat': 52.3676, 'lon': 4.9041},
                                'Portugal': {'lat': 38.7223, 'lon': -9.1393},
                                'Scotland': {'lat': 55.9533, 'lon': -3.1883},
                                'Belgium': {'lat': 50.8503, 'lon': 4.3517},
                                'Turkey': {'lat': 41.0082, 'lon': 28.9784},
                                'Greece': {'lat': 37.9838, 'lon': 23.7275},
                                'Mexico': {'lat': 19.4326, 'lon': -99.1332},
                                'USA': {'lat': 38.9072, 'lon': -77.0369},
                                'China': {'lat': 39.9042, 'lon': 116.4074},
                                'Japan': {'lat': 35.6762, 'lon': 139.6503},
                                'Australia': {'lat': -33.8688, 'lon': 151.2093},
                            }
                            
                            default_coords = country_coords.get(league.country if league else 'England', {'lat': 51.5074, 'lon': -0.1278})
                            
                            weather_result = ingest_weather_from_open_meteo(
                                db=db,
                                fixture_id=fixture_data['id'],
                                latitude=default_coords['lat'],
                                longitude=default_coords['lon'],
                                match_datetime=match_datetime
                            )
                            
                            if weather_result.get("success"):
                                logger.debug(f"✓ Auto-ingested weather for fixture {fixture_data['id']}")
                            else:
                                logger.debug(f"⚠ Weather auto-ingestion failed for fixture {fixture_data['id']}: {weather_result.get('error', 'Unknown error')}")
                        except Exception as e:
                            logger.debug(f"⚠ Weather auto-ingestion error for fixture {fixture_data['id']}: {e}")
                            try:
                                savepoint.rollback()
                                savepoint = db.begin_nested()  # Start new savepoint
                            except Exception:
                                # Savepoint may already be closed, create a new one
                                savepoint = db.begin_nested()
                    
                    # 2. Auto-calculate rest days if missing
                    rest_days_exist = db.query(TeamRestDays).filter(
                        TeamRestDays.fixture_id == fixture_data['id']
                    ).first()
                    
                    home_team_id_val = getattr(fixture_obj, 'home_team_id', None)
                    away_team_id_val = getattr(fixture_obj, 'away_team_id', None)
                    
                    if not rest_days_exist:
                        if home_team_id_val and away_team_id_val:
                            try:
                                rest_days_result = ingest_rest_days_for_fixture(
                                    db=db,
                                    fixture_id=fixture_data['id'],
                                    home_team_id=home_team_id_val,
                                    away_team_id=away_team_id_val
                                )
                                
                                if rest_days_result.get("success"):
                                    logger.info(f"✓ Auto-calculated rest days for fixture {fixture_data['id']}: home={rest_days_result.get('home_rest_days', 'N/A')}, away={rest_days_result.get('away_rest_days', 'N/A')}")
                                else:
                                    logger.warning(f"⚠ Rest days auto-calculation failed for fixture {fixture_data['id']}: {rest_days_result.get('error', 'Unknown error')}")
                                    try:
                                        savepoint.rollback()
                                        savepoint = db.begin_nested()  # Start new savepoint
                                    except Exception:
                                        # Savepoint may already be closed, create a new one
                                        savepoint = db.begin_nested()
                            except Exception as e:
                                logger.warning(f"⚠ Rest days auto-calculation error for fixture {fixture_data['id']}: {e}", exc_info=True)
                                try:
                                    savepoint.rollback()
                                    savepoint = db.begin_nested()  # Start new savepoint
                                except Exception:
                                    # Savepoint may already be closed, create a new one
                                    savepoint = db.begin_nested()
                        else:
                            logger.debug(f"⚠ Skipping rest days calculation for fixture {fixture_data['id']}: home_team_id={home_team_id_val}, away_team_id={away_team_id_val}")
                    
                    # 2b. Auto-calculate team form if missing
                    if home_team_id_val and away_team_id_val:
                        try:
                            from app.services.team_form_service import calculate_and_store_team_form
                            
                            fixture_date = fixture_data.get('match_date') or (jackpot.kickoff_date if jackpot else None)
                            
                            # Calculate form for home team
                            home_form_exist = db.query(TeamForm).filter(
                                TeamForm.fixture_id == fixture_data['id'],
                                TeamForm.team_id == home_team_id_val
                            ).first()
                            
                            if not home_form_exist:
                                home_form_result = calculate_and_store_team_form(
                                    db=db,
                                    team_id=home_team_id_val,
                                    fixture_id=fixture_data['id'],
                                    fixture_date=fixture_date,
                                    matches_count=5
                                )
                                if home_form_result.get("success"):
                                    logger.debug(f"✓ Auto-calculated form for home team {home_team_id_val} in fixture {fixture_data['id']}")
                            
                            # Calculate form for away team
                            away_form_exist = db.query(TeamForm).filter(
                                TeamForm.fixture_id == fixture_data['id'],
                                TeamForm.team_id == away_team_id_val
                            ).first()
                            
                            if not away_form_exist:
                                away_form_result = calculate_and_store_team_form(
                                    db=db,
                                    team_id=away_team_id_val,
                                    fixture_id=fixture_data['id'],
                                    fixture_date=fixture_date,
                                    matches_count=5
                                )
                                if away_form_result.get("success"):
                                    logger.debug(f"✓ Auto-calculated form for away team {away_team_id_val} in fixture {fixture_data['id']}")
                        except Exception as e:
                            logger.debug(f"⚠ Team form auto-calculation error for fixture {fixture_data['id']}: {e}", exc_info=True)
                            # Don't fail the whole request if form calculation fails
                    
                    # 3. Auto-track odds movement if missing and odds available
                    odds_movement_exists = db.query(OddsMovement).filter(
                        OddsMovement.fixture_id == fixture_obj.id
                    ).first()
                    
                    if not odds_movement_exists and fixture_data.get('odds_draw'):
                        try:
                            # Track current draw odds (will calculate delta if opening odds exist later)
                            odds_result = track_odds_movement(
                                db=db,
                                fixture_id=fixture_data['id'],
                                draw_odds=float(fixture_data['odds_draw'])
                            )
                            
                            if odds_result.get("success"):
                                logger.debug(f"✓ Auto-tracked odds movement for fixture {fixture_data['id']}")
                            else:
                                logger.debug(f"⚠ Odds movement auto-tracking failed for fixture {fixture_data['id']}: {odds_result.get('error', 'Unknown error')}")
                                savepoint.rollback()
                                savepoint = db.begin_nested()  # Start new savepoint
                        except Exception as e:
                            logger.debug(f"⚠ Odds movement auto-tracking error for fixture {fixture_data['id']}: {e}")
                            try:
                                savepoint.rollback()
                                savepoint = db.begin_nested()  # Start new savepoint
                            except Exception:
                                # Savepoint may already be closed, create a new one
                                savepoint = db.begin_nested()
                    
                    # Note: ingestion functions call db.commit() themselves, which commits the outer transaction
                    # So we can't commit the savepoint - it's already committed
                    # Just mark it as done
                    try:
                        savepoint.commit()
                    except Exception as commit_err:
                        # If savepoint was already committed by ingestion function, that's OK
                        logger.debug(f"Savepoint commit note (may be already committed): {commit_err}")
                    
                except Exception as e:
                    # Rollback savepoint on any error
                    try:
                        savepoint.rollback()
                    except Exception:
                        pass
                    logger.debug(f"⚠ Automatic ingestion error for fixture {fixture_data['id']}: {e}", exc_info=True)
                    # If transaction was aborted, rollback and continue
                    try:
                        db.rollback()
                    except Exception:
                        pass
            
            except Exception as e:
                # Outer exception handler - log but don't fail the whole request
                logger.warning(f"⚠ Automatic ingestion setup error for fixture {fixture_data['id']}: {e}", exc_info=True)
                # Rollback to ensure clean state
                try:
                    db.rollback()
                except Exception:
                    pass
            
            # ============================================================
            # DRAW STRUCTURAL ADJUSTMENT (CRITICAL: Home-Away Compression)
            # ============================================================
            # Apply draw-aware structural adjustments that compress H/A when draw signal is high
            # This prevents false favorites and jackpot busts
            try:
                from app.services.draw_structural_adjustment import apply_draw_structural_adjustments
                from app.services.draw_signal_calculator import fetch_draw_structural_data_for_fixture
                
                # Get lambda values for draw signal calculation
                lambda_home_val = base_probs.lambda_home if hasattr(base_probs, 'lambda_home') and base_probs.lambda_home is not None else None
                lambda_away_val = base_probs.lambda_away if hasattr(base_probs, 'lambda_away') and base_probs.lambda_away is not None else None
                
                # If lambda values not available, calculate from expected goals
                if lambda_home_val is None or lambda_away_val is None:
                    from app.models.dixon_coles import calculate_expected_goals
                    expectations = calculate_expected_goals(home_team_strength, away_team_strength, params)
                    lambda_home_val = expectations.lambda_home
                    lambda_away_val = expectations.lambda_away
                
                # Get market odds for draw signal calculation
                market_odds_for_signal = None
                if fixture_data.get('odds_home'):
                    market_odds_for_signal = {
                        "home": float(fixture_data['odds_home']),
                        "draw": float(fixture_data['odds_draw']),
                        "away": float(fixture_data['odds_away'])
                    }
                
                # Fetch draw structural data and compute draw signal
                draw_data = fetch_draw_structural_data_for_fixture(
                    db=db,
                    fixture_id=fixture_data['id'],
                    home_team_id=fixture_data.get('home_team_id'),
                    away_team_id=fixture_data.get('away_team_id'),
                    league_id=fixture_data.get('league_id'),
                    lambda_home=lambda_home_val,
                    lambda_away=lambda_away_val,
                    market_odds=market_odds_for_signal,
                )
                
                # Apply draw structural adjustments (includes H/A compression)
                adjustment_result = apply_draw_structural_adjustments(
                    base_home=base_probs.home,
                    base_draw=base_probs.draw,
                    base_away=base_probs.away,
                    lambda_home=lambda_home_val,
                    lambda_away=lambda_away_val,
                    draw_signal=draw_data["draw_signal"],
                    compression_strength=0.5,  # Default compression strength
                    draw_floor=0.18,
                    draw_cap=0.38,
                )
                
                # Update base_probs with draw-structurally-adjusted values
                base_probs = MatchProbabilities(
                    home=adjustment_result["home"],
                    draw=adjustment_result["draw"],
                    away=adjustment_result["away"],
                    entropy=-sum(
                        p * math.log2(p) if p > 0 else 0
                        for p in [adjustment_result["home"], adjustment_result["draw"], adjustment_result["away"]]
                    ),
                    lambda_home=lambda_home_val,
                    lambda_away=lambda_away_val
                )
                
                # Store draw structural metadata for later use in output
                draw_structural_components = {
                    "draw_signal": round(draw_data["draw_signal"], 4),
                    "compression": round(adjustment_result["meta"]["compression"], 4),
                    "lambda_gap": round(adjustment_result["meta"]["lambda_gap"], 4),
                    "lambda_total": round(draw_data["lambda_total"], 4),
                    "market_draw_prob": round(draw_data["market_draw_prob"], 4) if draw_data["market_draw_prob"] else None,
                    "weather_factor": round(draw_data["weather_factor"], 4) if draw_data["weather_factor"] else None,
                    "h2h_draw_rate": round(draw_data["h2h_draw_rate"], 4) if draw_data["h2h_draw_rate"] else None,
                    "league_draw_rate": round(draw_data["league_draw_rate"], 4) if draw_data["league_draw_rate"] else None,
                }
                logger.debug(f"Draw structural adjustment applied: draw_signal={draw_data['draw_signal']:.4f}, compression={adjustment_result['meta']['compression']:.4f}, components={draw_structural_components}")
            except Exception as e:
                # If draw structural adjustment fails, continue with base probabilities
                logger.warning(f"Draw structural adjustment failed: {e}, continuing with base probabilities", exc_info=True)
                draw_structural_components = None
            
            # ============================================================
            # TEMPERATURE SCALING (Probability Softening)
            # ============================================================
            # Apply temperature scaling to reduce overconfidence
            from app.models.uncertainty import temperature_scale
            
            # Get temperature from model (learned during training) or use default
            temperature = 1.2  # Default
            if model_weights_cache:
                temperature = model_weights_cache.get('temperature', 1.2)
                # Also check base model if this is a calibration model
                if model_type_cache == "calibration":
                    base_model_id = model_weights_cache.get('base_model_id')
                    if base_model_id:
                        try:
                            base_model = db.query(Model).filter(Model.id == base_model_id).first()
                            if base_model and hasattr(base_model, 'model_weights') and base_model.model_weights:
                                temperature = base_model.model_weights.get('temperature', temperature)
                        except Exception as e:
                            logger.debug(f"Could not load base model for temperature: {e}")
            
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
            if fixture_data.get('odds_home'):
                market_odds = {
                    "home": float(fixture_data['odds_home']),
                    "draw": float(fixture_data['odds_draw']),
                    "away": float(fixture_data['odds_away'])
                }
            
            # Get blend alpha from blending model if available (for Set B)
            blend_alpha = 0.6  # Default
            if model_type_cache == "blending" and model_weights_cache:
                blend_alpha = model_weights_cache.get('blend_alpha', 0.6)
                logger.debug(f"Using trained blend_alpha={blend_alpha} from blending model")
            elif model_type_cache == "calibration" and model_weights_cache:
                # Calibration model references a blending model
                base_model_id = model_weights_cache.get('base_model_id')
                if base_model_id:
                    try:
                        base_model = db.query(Model).filter(Model.id == base_model_id).first()
                        if base_model and base_model.model_type == "blending" and hasattr(base_model, 'model_weights') and base_model.model_weights:
                            blend_alpha = base_model.model_weights.get('blend_alpha', 0.6)
                            logger.debug(f"Using trained blend_alpha={blend_alpha} from blending model (via calibration)")
                    except Exception as e:
                        logger.debug(f"Could not load base model for blend_alpha: {e}")
            
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
            if market_odds and (model_type_cache in ["blending", "calibration"]):
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
            
            # Apply calibration if calibrator is available
            # Calibration should be applied to sets that use model probabilities (A, B, C, F, G)
            calibrated_sets = {}
            calibration_applied = False
            for set_id, probs in all_sets.items():
                if calibrator and set_id in ["A", "B", "C", "F", "G"]:
                    # Check if calibrator is actually fitted for at least one outcome
                    meta_h = calibrator.metadata.get("H")
                    meta_d = calibrator.metadata.get("D")
                    meta_a = calibrator.metadata.get("A")
                    is_fitted = (meta_h and meta_h.fitted) or (meta_d and meta_d.fitted) or (meta_a and meta_a.fitted)
                    
                    if is_fitted:
                        # Apply calibration using joint renormalization
                        try:
                            ch, cd, ca = calibrator.calibrate_probabilities(
                                probs.home,
                                probs.draw,
                                probs.away,
                                use_joint_renormalization=True
                            )
                            calibrated_sets[set_id] = MatchProbabilities(
                                home=ch,
                                draw=cd,
                                away=ca,
                                entropy=-sum(
                                    p * math.log2(p) if p > 0 else 0
                                    for p in [ch, cd, ca]
                                ),
                                lambda_home=probs.lambda_home if hasattr(probs, 'lambda_home') else None,
                                lambda_away=probs.lambda_away if hasattr(probs, 'lambda_away') else None
                            )
                            if not calibration_applied:
                                logger.info(f"✓ Applying calibration to Set {set_id}: ({probs.home:.3f}, {probs.draw:.3f}, {probs.away:.3f}) -> ({ch:.3f}, {cd:.3f}, {ca:.3f})")
                                calibration_applied = True
                            else:
                                logger.debug(f"Applied calibration to Set {set_id}: ({probs.home:.3f}, {probs.draw:.3f}, {probs.away:.3f}) -> ({ch:.3f}, {cd:.3f}, {ca:.3f})")
                        except Exception as e:
                            logger.warning(f"Failed to apply calibration to Set {set_id}: {e}, using uncalibrated probabilities")
                            calibrated_sets[set_id] = probs
                    else:
                        logger.debug(f"Calibrator not fitted for Set {set_id}, skipping calibration")
                        calibrated_sets[set_id] = probs
                else:
                    calibrated_sets[set_id] = probs
            
            # Log calibration summary for this fixture
            if calibrator:
                meta_h = calibrator.metadata.get("H")
                meta_d = calibrator.metadata.get("D")
                meta_a = calibrator.metadata.get("A")
                is_fitted = (meta_h and meta_h.fitted) or (meta_d and meta_d.fitted) or (meta_a and meta_a.fitted)
                
                if is_fitted and calibration_applied:
                    logger.debug(f"✓ Calibration applied to fixture {idx + 1}/{len(fixtures)}")
                elif is_fitted and not calibration_applied:
                    logger.warning(f"⚠ Calibrator fitted but not applied to fixture {idx + 1}/{len(fixtures)}. Sets processed: {list(all_sets.keys())}")
                elif not is_fitted:
                    logger.debug(f"Calibrator not fitted for fixture {idx + 1}/{len(fixtures)}")
            
            if calibrator and not calibration_applied:
                # Check if calibrator is actually fitted
                meta_h = calibrator.metadata.get("H")
                meta_d = calibrator.metadata.get("D")
                meta_a = calibrator.metadata.get("A")
                is_fitted = (meta_h and meta_h.fitted) or (meta_d and meta_d.fitted) or (meta_a and meta_a.fitted)
                
                if is_fitted:
                    logger.warning(f"Calibrator loaded and fitted but calibration was not applied to fixture {idx + 1}. Metadata: H={meta_h.fitted if meta_h else False}, D={meta_d.fitted if meta_d else False}, A={meta_a.fitted if meta_a else False}")
                else:
                    logger.warning(f"Calibrator loaded but not fitted for fixture {idx + 1} - calibration data may be missing or insufficient")
            
            # Convert to output format (as dictionaries for JSON serialization)
            for set_id, probs in calibrated_sets.items():
                output = {
                    "homeWinProbability": round(probs.home * 100, 2),
                    "drawProbability": round(probs.draw * 100, 2),
                    "awayWinProbability": round(probs.away * 100, 2),
                    "entropy": round(probs.entropy, 4) if hasattr(probs, 'entropy') and probs.entropy is not None else None,
                    "calibrated": PROBABILITY_SET_METADATA.get(set_id, {}).get("calibrated", True) and (calibrator is not None and set_id in ["A", "B", "C", "F", "G"]),
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
                
                # Add draw structural components for explainability (all sets)
                if 'draw_structural_components' in locals() and draw_structural_components and set_id in ["A", "B", "C"]:
                    if "drawStructuralComponents" not in output:
                        output["drawStructuralComponents"] = {}
                    output["drawStructuralComponents"].update(draw_structural_components)
                
                probability_sets[set_id].append(output)
            
        # Log summary statistics
        logger.info(f"=== PROBABILITY CALCULATION COMPLETE ===")
        logger.info(f"Team matching stats: {team_match_stats}")
        logger.info(f"Total fixtures processed: {len(fixtures)}")
        logger.info(f"Teams using default strengths: {team_match_stats['default_strengths']}")
        logger.info(f"Teams using model strengths: {team_match_stats['model_strengths']}")
        logger.info(f"Teams using DB strengths: {team_match_stats['db_strengths']}")
        
        # Log calibration summary
        if calibrator:
            meta_h = calibrator.metadata.get("H")
            meta_d = calibrator.metadata.get("D")
            meta_a = calibrator.metadata.get("A")
            is_fitted = (meta_h and meta_h.fitted) or (meta_d and meta_d.fitted) or (meta_a and meta_a.fitted)
            if is_fitted:
                logger.info(f"✓ Calibration model active: H={meta_h.fitted if meta_h else False}, D={meta_d.fitted if meta_d else False}, A={meta_a.fitted if meta_a else False}")
                logger.info(f"  Calibration applied to {len(fixtures)} fixtures for sets A, B, C, F, G")
            else:
                logger.warning(f"⚠ Calibration model loaded but not fitted - calibration not applied")
        
        # Return in format expected by frontend (wrapped in ApiResponse)
        return ApiResponse(
            success=True,
            message="Probabilities calculated successfully",
            data={
            "predictionId": f"{jackpot_id}-{datetime.now().isoformat()}",
            "modelVersion": model_version_cache if model_version_cache else "unknown",
            "createdAt": datetime.now().isoformat(),
            "fixtures": fixtures_data,
            "probabilitySets": probability_sets,
            "confidenceFlags": {},
            "warnings": []
        }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating probabilities: {e}", exc_info=True)
        # Ensure we rollback on any error to prevent transaction issues
        try:
            db.rollback()
        except Exception:
            pass
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


@router.get("/saved-results/{result_id}", response_model=ApiResponse)
async def get_saved_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific saved probability result by ID"""
    try:
        saved_result = db.query(SavedProbabilityResult).filter(
            SavedProbabilityResult.id == result_id
        ).first()
        
        if not saved_result:
            raise HTTPException(status_code=404, detail=f"Saved result {result_id} not found")
        
        result = {
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
        
        return ApiResponse(
            success=True,
            message="Saved result retrieved",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching saved result {result_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/imported-jackpots", response_model=ApiResponse)
async def get_imported_jackpots(
    db: Session = Depends(get_db)
):
    """Get all imported jackpots with summary information"""
    try:
        # Query saved probability results grouped by jackpot_id
        # Get the most recent result for each jackpot
        from sqlalchemy import func
        
        # First, get distinct jackpot_ids with their most recent saved_result
        subquery = db.query(
            SavedProbabilityResult.jackpot_id,
            func.max(SavedProbabilityResult.created_at).label('max_created_at')
        ).group_by(SavedProbabilityResult.jackpot_id).subquery()
        
        # Then join back to get full details
        saved_results = db.query(SavedProbabilityResult).join(
            subquery,
            (SavedProbabilityResult.jackpot_id == subquery.c.jackpot_id) &
            (SavedProbabilityResult.created_at == subquery.c.max_created_at)
        ).all()
        
        # Also get jackpot information
        jackpot_ids = [sr.jackpot_id for sr in saved_results]
        jackpots_map = {}
        if jackpot_ids:
            jackpots = db.query(JackpotModel).filter(
                JackpotModel.jackpot_id.in_(jackpot_ids)
            ).all()
            jackpots_map = {j.jackpot_id: j for j in jackpots}
        
        results = []
        for sr in saved_results:
            jackpot = jackpots_map.get(sr.jackpot_id)
            results.append({
                'id': sr.id,
                'jackpot_id': sr.jackpot_id,
                'name': sr.name,
                'total_fixtures': sr.total_fixtures,
                'actual_results': sr.actual_results,
                'scores': sr.scores,
                'selections': sr.selections,  # Include selections to check if probabilities computed
                'created_at': sr.created_at,
                'kickoff_date': jackpot.kickoff_date if jackpot else None,
                'jackpot_created_at': jackpot.created_at if jackpot else None
            })
        
        imported_jackpots = []
        for row in results:
            jackpot_id = row['jackpot_id']
            total_fixtures = row['total_fixtures'] or 0
            
            # Determine status
            # "validated" = has actual_results AND scores calculated
            # "probabilities_computed" = has actual_results AND selections with actual data (probabilities computed but not validated)
            # "imported" = has actual_results but no selections/scores yet
            # "pending" = no actual_results
            has_actual_results = bool(row['actual_results'])
            has_scores = bool(row['scores'])
            # Check if selections exist AND contain actual data (not empty dict)
            selections = row['selections'] or {}
            has_selections = bool(selections) and isinstance(selections, dict) and len(selections) > 0
            
            if has_actual_results and has_scores:
                status = "validated"
            elif has_actual_results and has_selections:
                status = "probabilities_computed"
            elif has_actual_results:
                status = "imported"
            else:
                status = "pending"
            
            # Calculate correct predictions from scores
            # Try to get from scores first (most accurate)
            correct_predictions = None
            if row['scores']:
                # Get the first set's score (usually Set A)
                scores_dict = row['scores'] if isinstance(row['scores'], dict) else {}
                first_set_score = None
                for set_id in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
                    if set_id in scores_dict:
                        first_set_score = scores_dict[set_id]
                        break
                
                if first_set_score and isinstance(first_set_score, dict):
                    correct_predictions = first_set_score.get('correct')
            
            # Get date (prefer kickoff_date, fallback to created_at)
            date_value = row['kickoff_date'] or row['jackpot_created_at'] or row['created_at']
            
            imported_jackpots.append({
                "id": str(row['id']),
                "jackpotId": jackpot_id,
                "date": date_value.isoformat() if date_value else None,
                "matches": total_fixtures,
                "status": status,
                "correctPredictions": correct_predictions
            })
        
        # Sort by date descending (most recent first)
        imported_jackpots.sort(key=lambda x: x.get("date") or "", reverse=True)
        
        return ApiResponse(
            success=True,
            message=f"Found {len(imported_jackpots)} imported jackpots",
            data={"jackpots": imported_jackpots}
        )
    except Exception as e:
        logger.error(f"Error fetching imported jackpots: {e}", exc_info=True)
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
                # Extract data from ApiResponse if needed
                prob_data = prob_response.data if hasattr(prob_response, 'data') else prob_response
                all_probability_sets = prob_data.get("probabilitySets", {})
                
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
                    match_number = str(idx + 1)  # 1-indexed match number (from CSV: "1", "2", "3", ...)
                    
                    # actual_results uses match numbers (1-indexed) as keys from CSV import, not fixture IDs
                    # Priority: match number (1-indexed) > fixture ID > index (0-indexed) > by position
                    actual_result_str = None
                    if saved_result.actual_results:
                        actual_result_str = (
                            saved_result.actual_results.get(match_number) or
                            saved_result.actual_results.get(fixture_id) or
                            saved_result.actual_results.get(str(idx)) or
                            (list(saved_result.actual_results.values())[idx] if idx < len(saved_result.actual_results) else None)
                        )
                    
                    if not actual_result_str:
                        logger.warning(f"No actual result found for fixture {fixture_id} (match {match_number}) in saved_result {saved_result_id}")
                        continue
                    
                    total_matches += 1
                    actual_result = convert_result(actual_result_str)
                    
                    # Get prediction for this set
                    # selections also use match numbers (1-indexed) as keys
                    prediction_for_fixture = None
                    if saved_result.selections and saved_result.selections.get(set_id):
                        set_selections = saved_result.selections[set_id]
                        prediction_for_fixture = (
                            set_selections.get(match_number) or
                            set_selections.get(fixture_id) or
                            set_selections.get(str(idx)) or
                            (list(set_selections.values())[idx] if idx < len(set_selections) else None)
                        )
                    
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
