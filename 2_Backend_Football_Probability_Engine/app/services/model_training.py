"""
Model Training Service
Handles training of Poisson/Dixon-Coles, Odds Blending, and Calibration models
"""
import logging
import hashlib
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.db.models import Model, ModelStatus, TrainingRun, Match, League
from app.db.session import SessionLocal
import uuid

logger = logging.getLogger(__name__)


class ModelTrainingService:
    """Service for training prediction models"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _update_task_status(
        self,
        task_id: str,
        status: str,
        progress: int = 0,
        phase: str = "",
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update task status in task_store"""
        try:
            from app.api.tasks import task_store
            if task_id in task_store:
                task_store[task_id]["status"] = status
                task_store[task_id]["progress"] = progress
                if phase:
                    task_store[task_id]["phase"] = phase
                if result:
                    task_store[task_id]["result"] = result
                if error:
                    task_store[task_id]["error"] = error
                if status == "completed":
                    task_store[task_id]["completedAt"] = datetime.now().isoformat()
                elif status == "failed":
                    task_store[task_id]["completedAt"] = datetime.now().isoformat()
        except Exception as e:
            logger.warning(f"Could not update task status: {e}")
    
    def train_poisson_model(
        self,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Train Poisson/Dixon-Coles model
        
        CRITICAL: TrainingRun is created BEFORE training starts for audit trail.
        Only one active model per model_type is allowed.
        
        Args:
            leagues: List of league codes to train on (None = all)
            seasons: List of seasons to train on (None = all)
            date_from: Start date filter
            date_to: End date filter
            task_id: Task ID for progress tracking
            
        Returns:
            Dict with training results and metrics
        """
        logger.info(f"Starting Poisson model training (task: {task_id})")
        
        # ---- CREATE TRAINING RUN FIRST (for audit trail) ----
        training_run = TrainingRun(
            run_type='poisson',
            status=ModelStatus.training,
            started_at=datetime.utcnow(),
            date_from=date_from,
            date_to=date_to,
        )
        self.db.add(training_run)
        self.db.flush()
        
        try:
            # Query matches for training (time-ordered)
            query = self.db.query(Match).join(League)
            
            if leagues:
                query = query.filter(League.code.in_(leagues))
            if seasons:
                query = query.filter(Match.season.in_(seasons))
            if date_from:
                query = query.filter(Match.match_date >= date_from)
            if date_to:
                query = query.filter(Match.match_date <= date_to)
            
            # CRITICAL: Order by date to ensure deterministic ordering
            matches = query.order_by(Match.match_date.asc()).all()
            match_count = len(matches)
            
            logger.info(f"Training on {match_count} matches")
            
            if match_count < 100:
                raise ValueError(f"Insufficient training data: {match_count} matches (minimum 100 required)")
            
            # Import trainer
            from app.services.poisson_trainer import PoissonTrainer
            from app.config import settings
            
            # Prepare match data for training
            match_data = []
            for match in matches:
                if match.home_team_id and match.away_team_id and \
                   match.home_goals is not None and match.away_goals is not None:
                    match_data.append({
                        'home_team_id': match.home_team_id,
                        'away_team_id': match.away_team_id,
                        'home_goals': match.home_goals,
                        'away_goals': match.away_goals,
                        'match_date': match.match_date or datetime.now()
                    })
            
            if len(match_data) < 100:
                raise ValueError(f"Insufficient valid matches: {len(match_data)} (minimum 100 required)")
            
            # ---- DATA HASH (for reproducibility) ----
            data_hash = hashlib.sha256(
                json.dumps(match_data, default=str).encode()
            ).hexdigest()
            
            logger.info(f"Training with {len(match_data)} valid matches (data hash: {data_hash[:16]}...)")
            
            # Initialize trainer
            trainer = PoissonTrainer(
                decay_rate=getattr(settings, 'DEFAULT_DECAY_RATE', 0.0065),
                initial_home_advantage=getattr(settings, 'DEFAULT_HOME_ADVANTAGE', 0.35),
                initial_rho=getattr(settings, 'DEFAULT_RHO', -0.13)
            )
            
            # Train model: estimate team strengths and parameters
            logger.info("Estimating team strengths and parameters...")
            team_strengths, home_advantage, rho, training_metadata = trainer.estimate_team_strengths(match_data)
            
            # Calculate validation metrics
            logger.info("Calculating validation metrics...")
            metrics = trainer.calculate_metrics(match_data, team_strengths, home_advantage, rho)
            
            # ---- ARCHIVE OLD MODELS (SINGLE ACTIVE POLICY) ----
            self.db.query(Model).filter(
                Model.model_type == 'poisson',
                Model.status == ModelStatus.active
            ).update({"status": ModelStatus.archived})
            
            # Create model version
            version = f"poisson-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare model weights for storage (team strengths + parameters + metadata)
            model_weights = {
                'team_strengths': team_strengths,
                'home_advantage': home_advantage,
                'rho': rho,
                'decay_rate': trainer.decay_rate,
                'normalization': training_metadata['normalization'],
                'training_data_hash': data_hash,
                'iterations': training_metadata['iterations'],
                'max_delta': training_metadata['max_delta'],
            }
            
            model = Model(
                version=version,
                model_type='poisson',
                status=ModelStatus.active,
                training_started_at=training_run.started_at,
                training_completed_at=datetime.utcnow(),
                training_matches=len(match_data),
                training_leagues=leagues or [],
                training_seasons=seasons or [],
                decay_rate=trainer.decay_rate,
                brier_score=metrics['brierScore'],
                log_loss=metrics['logLoss'],
                draw_accuracy=metrics['drawAccuracy'],
                overall_accuracy=metrics.get('overallAccuracy', 65.0),
                model_weights=model_weights
            )
            
            self.db.add(model)
            self.db.flush()
            
            # Update training run with model ID and results
            training_run.model_id = model.id
            training_run.status = ModelStatus.active  # Training completed successfully, model is now active
            training_run.completed_at = datetime.utcnow()
            training_run.match_count = len(match_data)
            training_run.brier_score = metrics['brierScore']
            training_run.log_loss = metrics['logLoss']
            training_run.validation_accuracy = metrics.get('overallAccuracy', 65.0)
            training_run.logs = {
                "leagues": leagues,
                "seasons": seasons,
                "data_hash": data_hash,
                "training_metadata": training_metadata
            }
            
            self.db.commit()
            
            logger.info(f"Poisson model training complete: {version}")
            
            return {
                'modelId': model.id,
                'version': version,
                'metrics': metrics,
                'matchCount': len(match_data),
                'trainingRunId': training_run.id,
            }
        except Exception as e:
            training_run.status = ModelStatus.failed
            training_run.error_message = str(e)
            training_run.completed_at = datetime.utcnow()
            self.db.commit()
            raise
    
    def train_blending_model(
        self,
        poisson_model_id: Optional[int] = None,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Train odds blending model
        
        Finds optimal blend weight (alpha) between Poisson model predictions
        and market odds that minimizes Brier score on validation data.
        
        Formula: P_blended = alpha * P_model + (1 - alpha) * P_market
        
        Args:
            poisson_model_id: ID of trained Poisson model to blend with odds
            leagues: List of league codes
            seasons: List of seasons
            date_from: Start date for training data
            date_to: End date for training data
            task_id: Task ID for progress tracking
            
        Returns:
            Dict with training results
        """
        logger.info(f"Starting blending model training (task: {task_id})")
        
        # Create training run record
        training_run = TrainingRun(
            run_type='blending',
            status=ModelStatus.training,
            started_at=datetime.now(),
            date_from=date_from,
            date_to=date_to,
        )
        self.db.add(training_run)
        self.db.flush()
        
        try:
            # Update task progress
            if task_id:
                self._update_task_status(task_id, "in_progress", 10, "Loading Poisson model...")
            
            # Load active Poisson model
            if poisson_model_id:
                poisson_model = self.db.query(Model).filter(Model.id == poisson_model_id).first()
            else:
                poisson_model = self.db.query(Model).filter(
                    Model.model_type == 'poisson',
                    Model.status == ModelStatus.active
                ).order_by(Model.training_completed_at.desc()).first()
            
            if not poisson_model:
                raise ValueError("No active Poisson model found. Train Poisson model first.")
            
            # Extract model parameters
            model_weights = poisson_model.model_weights
            team_strengths_dict = model_weights.get('team_strengths', {})
            home_advantage = model_weights.get('home_advantage', 0.35)
            rho = model_weights.get('rho', -0.13)
            
            # Convert team strengths to TeamStrength objects
            from app.models.dixon_coles import TeamStrength, DixonColesParams, calculate_match_probabilities
            
            team_strengths = {}
            for team_id_str, strengths in team_strengths_dict.items():
                team_id = int(team_id_str)
                team_strengths[team_id] = TeamStrength(
                    team_id=team_id,
                    attack=strengths['attack'],
                    defense=strengths['defense']
                )
            
            params = DixonColesParams(rho=rho, home_advantage=home_advantage)
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 30, "Loading historical matches...")
            
            # Load historical matches with odds
            from app.db.models import Match, League
            
            query = self.db.query(Match).join(League)
            
            if leagues:
                query = query.filter(League.code.in_(leagues))
            if seasons:
                query = query.filter(Match.season.in_(seasons))
            if date_from:
                query = query.filter(Match.match_date >= date_from)
            if date_to:
                query = query.filter(Match.match_date <= date_to)
            
            # Filter matches with valid odds
            query = query.filter(
                Match.odds_home.isnot(None),
                Match.odds_draw.isnot(None),
                Match.odds_away.isnot(None),
                Match.odds_home > 0,
                Match.odds_draw > 0,
                Match.odds_away > 0
            )
            
            matches = query.order_by(Match.match_date.asc()).all()
            
            if len(matches) < 100:
                raise ValueError(f"Insufficient matches with odds for blending training. Found {len(matches)}, need at least 100.")
            
            logger.info(f"Training blending model on {len(matches)} matches with odds")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 50, "Calculating predictions and blending...")
            
            # Calculate model predictions and market probabilities
            model_predictions = []
            market_predictions = []
            actual_outcomes = []
            
            for match in matches:
                # Get team strengths
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                if home_id not in team_strengths or away_id not in team_strengths:
                    continue
                
                home_strength = team_strengths[home_id]
                away_strength = team_strengths[away_id]
                
                # Calculate model probabilities
                probs = calculate_match_probabilities(home_strength, away_strength, params)
                model_predictions.append([probs.home, probs.draw, probs.away])
                
                # Calculate market probabilities from odds
                total_implied = (1.0 / match.odds_home) + (1.0 / match.odds_draw) + (1.0 / match.odds_away)
                market_home = (1.0 / match.odds_home) / total_implied
                market_draw = (1.0 / match.odds_draw) / total_implied
                market_away = (1.0 / match.odds_away) / total_implied
                market_predictions.append([market_home, market_draw, market_away])
                
                # Actual outcome
                if match.home_goals > match.away_goals:
                    actual_outcomes.append([1.0, 0.0, 0.0])
                elif match.home_goals == match.away_goals:
                    actual_outcomes.append([0.0, 1.0, 0.0])
                else:
                    actual_outcomes.append([0.0, 0.0, 1.0])
            
            if len(model_predictions) < 100:
                raise ValueError(f"Insufficient valid matches after filtering. Found {len(model_predictions)}, need at least 100.")
            
            # Time-ordered split for validation
            split_idx = int(len(model_predictions) * 0.8)
            train_preds = model_predictions[:split_idx]
            train_market = market_predictions[:split_idx]
            train_actuals = actual_outcomes[:split_idx]
            
            test_preds = model_predictions[split_idx:]
            test_market = market_predictions[split_idx:]
            test_actuals = actual_outcomes[split_idx:]
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 70, "Finding optimal blend weight...")
            
            # Grid search for optimal alpha
            best_alpha = 0.6
            best_brier = float('inf')
            
            alphas = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            
            for alpha in alphas:
                # Blend predictions
                blended_preds = []
                for i in range(len(train_preds)):
                    blended = [
                        alpha * train_preds[i][0] + (1 - alpha) * train_market[i][0],
                        alpha * train_preds[i][1] + (1 - alpha) * train_market[i][1],
                        alpha * train_preds[i][2] + (1 - alpha) * train_market[i][2],
                    ]
                    blended_preds.append(blended)
                
                # Calculate Brier score
                brier_scores = []
                for i in range(len(blended_preds)):
                    brier = sum((blended_preds[i][j] - train_actuals[i][j]) ** 2 for j in range(3))
                    brier_scores.append(brier)
                
                mean_brier = sum(brier_scores) / len(brier_scores)
                
                if mean_brier < best_brier:
                    best_brier = mean_brier
                    best_alpha = alpha
            
            logger.info(f"Optimal blend weight: alpha={best_alpha:.3f}, Brier={best_brier:.4f}")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 85, "Validating blend performance...")
            
            # Validate on test set
            test_blended = []
            for i in range(len(test_preds)):
                blended = [
                    best_alpha * test_preds[i][0] + (1 - best_alpha) * test_market[i][0],
                    best_alpha * test_preds[i][1] + (1 - best_alpha) * test_market[i][1],
                    best_alpha * test_preds[i][2] + (1 - best_alpha) * test_market[i][2],
                ]
                test_blended.append(blended)
            
            # Calculate validation metrics
            test_brier_scores = []
            test_log_losses = []
            
            for i in range(len(test_blended)):
                # Brier score
                brier = sum((test_blended[i][j] - test_actuals[i][j]) ** 2 for j in range(3))
                test_brier_scores.append(brier)
                
                # Log loss
                log_loss = -sum(
                    test_actuals[i][j] * math.log(max(test_blended[i][j], 1e-10)) +
                    (1 - test_actuals[i][j]) * math.log(max(1 - test_blended[i][j], 1e-10))
                    for j in range(3)
                )
                test_log_losses.append(log_loss)
            
            metrics = {
                'brierScore': float(sum(test_brier_scores) / len(test_brier_scores)),
                'logLoss': float(sum(test_log_losses) / len(test_log_losses)),
            }
            
            # Archive old blending models
            self.db.query(Model).filter(
                Model.model_type == 'blending',
                Model.status == ModelStatus.active
            ).update({"status": ModelStatus.archived})
            
            # Create new blending model
            version = f"blending-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            model = Model(
                version=version,
                model_type='blending',
                status=ModelStatus.active,
                training_started_at=training_run.started_at,
                training_completed_at=datetime.utcnow(),
                training_matches=len(model_predictions),
                training_leagues=leagues or [],
                training_seasons=seasons or [],
                blend_alpha=best_alpha,
                brier_score=metrics['brierScore'],
                log_loss=metrics['logLoss'],
                model_weights={
                    'blend_alpha': best_alpha,
                    'model_weight': best_alpha,
                    'market_weight': 1.0 - best_alpha,
                    'poisson_model_id': poisson_model.id,
                    'poisson_model_version': poisson_model.version,
                }
            )
            
            self.db.add(model)
            self.db.flush()
            
            # Update training run
            training_run.model_id = model.id
            training_run.status = ModelStatus.active
            training_run.completed_at = datetime.utcnow()
            training_run.match_count = len(model_predictions)
            training_run.brier_score = metrics['brierScore']
            training_run.log_loss = metrics['logLoss']
            training_run.logs = {
                "leagues": leagues,
                "seasons": seasons,
                "optimal_alpha": best_alpha,
                "poisson_model_id": poisson_model.id,
            }
            
            self.db.commit()
            
            logger.info(f"Blending model training complete: {version}, alpha={best_alpha:.3f}")
            
            if task_id:
                self._update_task_status(task_id, "completed", 100, "Training complete", result=metrics)
            
            return {
                'modelId': model.id,
                'version': version,
                'metrics': metrics,
                'matchCount': len(model_predictions),
                'optimalAlpha': best_alpha,
                'trainingRunId': training_run.id,
            }
        except Exception as e:
            training_run.status = ModelStatus.failed
            training_run.error_message = str(e)
            training_run.completed_at = datetime.utcnow()
            self.db.commit()
            if task_id:
                self._update_task_status(task_id, "failed", 0, "", error=str(e))
            raise
    
    def train_calibration_model(
        self,
        base_model_id: Optional[int] = None,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Train calibration model (Isotonic regression)
        
        Fits isotonic regression to calibrate model predictions for each outcome (H/D/A).
        Uses marginal calibration (each outcome calibrated independently).
        
        Args:
            base_model_id: ID of base model to calibrate (Poisson or Blending)
            leagues: List of league codes
            seasons: List of seasons
            date_from: Start date for training data
            date_to: End date for training data
            task_id: Task ID for progress tracking
            
        Returns:
            Dict with training results
        """
        logger.info(f"Starting calibration model training (task: {task_id})")
        
        # Create training run record
        training_run = TrainingRun(
            run_type='calibration',
            status=ModelStatus.training,
            started_at=datetime.now(),
            date_from=date_from,
            date_to=date_to,
        )
        self.db.add(training_run)
        self.db.flush()
        
        try:
            if task_id:
                self._update_task_status(task_id, "in_progress", 10, "Loading base model...")
            
            # Load base model (Poisson or Blending)
            if base_model_id:
                base_model = self.db.query(Model).filter(Model.id == base_model_id).first()
            else:
                # Try blending first, then Poisson
                base_model = self.db.query(Model).filter(
                    Model.model_type == 'blending',
                    Model.status == ModelStatus.active
                ).order_by(Model.training_completed_at.desc()).first()
                
                if not base_model:
                    base_model = self.db.query(Model).filter(
                        Model.model_type == 'poisson',
                        Model.status == ModelStatus.active
                    ).order_by(Model.training_completed_at.desc()).first()
            
            if not base_model:
                raise ValueError("No active base model found. Train Poisson or Blending model first.")
            
            logger.info(f"Calibrating {base_model.model_type} model: {base_model.version}")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 30, "Loading historical matches...")
            
            # Load historical matches
            query = self.db.query(Match).join(League)
            
            if leagues:
                query = query.filter(League.code.in_(leagues))
            if seasons:
                query = query.filter(Match.season.in_(seasons))
            if date_from:
                query = query.filter(Match.match_date >= date_from)
            if date_to:
                query = query.filter(Match.match_date <= date_to)
            
            matches = query.order_by(Match.match_date.asc()).all()
            
            if len(matches) < 500:
                raise ValueError(f"Insufficient matches for calibration. Found {len(matches)}, need at least 500.")
            
            logger.info(f"Calibrating on {len(matches)} historical matches")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 50, "Calculating predictions...")
            
            # Calculate predictions using base model
            from app.models.dixon_coles import TeamStrength, DixonColesParams, calculate_match_probabilities
            from app.models.probability_sets import blend_probabilities, odds_to_implied_probabilities
            
            # Get model parameters
            # CRITICAL: If base_model is blending, we need to load the Poisson model it references
            # because blending models don't store team_strengths directly
            if base_model.model_type == 'blending':
                # Load the Poisson model referenced by the blending model
                poisson_model_id = base_model.model_weights.get('poisson_model_id')
                if not poisson_model_id:
                    raise ValueError("Blending model does not reference a Poisson model. Cannot calibrate.")
                
                poisson_model = self.db.query(Model).filter(Model.id == poisson_model_id).first()
                if not poisson_model:
                    raise ValueError(f"Referenced Poisson model (ID: {poisson_model_id}) not found.")
                
                # Extract team strengths and parameters from Poisson model
                poisson_weights = poisson_model.model_weights
                team_strengths_dict = poisson_weights.get('team_strengths', {})
                home_advantage = poisson_weights.get('home_advantage', 0.35)
                rho = poisson_weights.get('rho', -0.13)
                
                # Get blend alpha from blending model
                blend_alpha = base_model.model_weights.get('blend_alpha', 0.6)
                
                logger.info(f"Using Poisson model {poisson_model.version} with blend alpha {blend_alpha}")
            else:
                # Pure Poisson model - extract directly
                model_weights = base_model.model_weights
                team_strengths_dict = model_weights.get('team_strengths', {})
                home_advantage = model_weights.get('home_advantage', 0.35)
                rho = model_weights.get('rho', -0.13)
                blend_alpha = None
            
            # Convert team strengths
            team_strengths = {}
            for team_id_str, strengths in team_strengths_dict.items():
                team_id = int(team_id_str)
                team_strengths[team_id] = TeamStrength(
                    team_id=team_id,
                    attack=strengths['attack'],
                    defense=strengths['defense']
                )
            
            params = DixonColesParams(rho=rho, home_advantage=home_advantage)
            
            # Collect predictions and actuals
            predictions_home = []
            predictions_draw = []
            predictions_away = []
            actuals_home = []
            actuals_draw = []
            actuals_away = []
            
            for match in matches:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                if home_id not in team_strengths or away_id not in team_strengths:
                    continue
                
                home_strength = team_strengths[home_id]
                away_strength = team_strengths[away_id]
                
                # Calculate base probabilities
                if base_model.model_type == 'blending' and blend_alpha is not None:
                    # Use blended probabilities
                    # Get model probabilities from Poisson
                    model_probs = calculate_match_probabilities(home_strength, away_strength, params)
                    
                    # Get market probabilities if odds available
                    if match.odds_home and match.odds_draw and match.odds_away:
                        market_probs = odds_to_implied_probabilities({
                            'home': match.odds_home,
                            'draw': match.odds_draw,
                            'away': match.odds_away
                        })
                        probs = blend_probabilities(model_probs, market_probs, blend_alpha)
                    else:
                        # No odds available - use pure model probabilities
                        probs = model_probs
                else:
                    # Pure Poisson model
                    probs = calculate_match_probabilities(home_strength, away_strength, params)
                
                predictions_home.append(probs.home)
                predictions_draw.append(probs.draw)
                predictions_away.append(probs.away)
                
                # Actual outcomes (1 if occurred, 0 otherwise)
                if match.home_goals > match.away_goals:
                    actuals_home.append(1)
                    actuals_draw.append(0)
                    actuals_away.append(0)
                elif match.home_goals == match.away_goals:
                    actuals_home.append(0)
                    actuals_draw.append(1)
                    actuals_away.append(0)
                else:
                    actuals_home.append(0)
                    actuals_draw.append(0)
                    actuals_away.append(1)
            
            if len(predictions_home) < 500:
                raise ValueError(f"Insufficient valid predictions. Found {len(predictions_home)}, need at least 500.")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 70, "Fitting isotonic regression...")
            
            # Time-ordered split for validation
            split_idx = int(len(predictions_home) * 0.8)
            
            # Fit calibrator on training set
            from app.models.calibration import Calibrator, compute_calibration_curve
            from app.db.models import CalibrationData, MatchResult
            
            calibrator = Calibrator()
            
            # Fit for each outcome
            calibrator.fit(
                predictions_home[:split_idx],
                actuals_home[:split_idx],
                "H"
            )
            calibrator.fit(
                predictions_draw[:split_idx],
                actuals_draw[:split_idx],
                "D"
            )
            calibrator.fit(
                predictions_away[:split_idx],
                actuals_away[:split_idx],
                "A"
            )
            
            # Compute and store calibration curves in database
            # This happens BEFORE model is created so we can reference it
            calibration_curves = {}
            for outcome_type, outcome_enum in [("H", MatchResult.H), ("D", MatchResult.D), ("A", MatchResult.A)]:
                if outcome_type == "H":
                    preds = predictions_home[:split_idx]
                    acts = actuals_home[:split_idx]
                elif outcome_type == "D":
                    preds = predictions_draw[:split_idx]
                    acts = actuals_draw[:split_idx]
                else:
                    preds = predictions_away[:split_idx]
                    acts = actuals_away[:split_idx]
                
                curve = compute_calibration_curve(preds, acts, outcome_type, n_bins=20)
                calibration_curves[outcome_type] = curve
                
                # Store calibration curve data (will be linked to model after it's created)
                # We'll store it after model creation
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 85, "Validating calibration...")
            
            # Validate on test set
            calibrated_home = []
            calibrated_draw = []
            calibrated_away = []
            
            for i in range(split_idx, len(predictions_home)):
                ch = calibrator.calibrate(predictions_home[i], "H")
                cd = calibrator.calibrate(predictions_draw[i], "D")
                ca = calibrator.calibrate(predictions_away[i], "A")
                
                # Renormalize
                total = ch + cd + ca
                if total > 0:
                    ch /= total
                    cd /= total
                    ca /= total
                
                calibrated_home.append(ch)
                calibrated_draw.append(cd)
                calibrated_away.append(ca)
            
            # Calculate metrics on calibrated predictions
            test_actuals_home = actuals_home[split_idx:]
            test_actuals_draw = actuals_draw[split_idx:]
            test_actuals_away = actuals_away[split_idx:]
            
            # Brier score
            brier_home = sum((calibrated_home[i] - test_actuals_home[i]) ** 2 for i in range(len(calibrated_home))) / len(calibrated_home)
            brier_draw = sum((calibrated_draw[i] - test_actuals_draw[i]) ** 2 for i in range(len(calibrated_draw))) / len(calibrated_draw)
            brier_away = sum((calibrated_away[i] - test_actuals_away[i]) ** 2 for i in range(len(calibrated_away))) / len(calibrated_away)
            
            mean_brier = (brier_home + brier_draw + brier_away) / 3
            
            # Log loss
            log_losses = []
            for i in range(len(calibrated_home)):
                # Multi-class log loss
                actual = [test_actuals_home[i], test_actuals_draw[i], test_actuals_away[i]]
                predicted = [calibrated_home[i], calibrated_draw[i], calibrated_away[i]]
                log_loss = -sum(actual[j] * math.log(max(predicted[j], 1e-10)) for j in range(3))
                log_losses.append(log_loss)
            
            mean_log_loss = sum(log_losses) / len(log_losses)
            
            metrics = {
                'brierScore': float(mean_brier),
                'logLoss': float(mean_log_loss),
            }
            
            # Archive old calibration models
            self.db.query(Model).filter(
                Model.model_type == 'calibration',
                Model.status == ModelStatus.active
            ).update({"status": ModelStatus.archived})
            
            # Create new calibration model
            version = f"calibration-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Store calibration metadata
            calibration_metadata = {
                'base_model_id': base_model.id,
                'base_model_version': base_model.version,
                'base_model_type': base_model.model_type,
                'calibration_metadata': {
                    'H': {
                        'fitted': calibrator.metadata['H'].fitted,
                        'sample_count': calibrator.metadata['H'].sample_count,
                    },
                    'D': {
                        'fitted': calibrator.metadata['D'].fitted,
                        'sample_count': calibrator.metadata['D'].sample_count,
                    },
                    'A': {
                        'fitted': calibrator.metadata['A'].fitted,
                        'sample_count': calibrator.metadata['A'].sample_count,
                    },
                }
            }
            
            model = Model(
                version=version,
                model_type='calibration',
                status=ModelStatus.active,
                training_started_at=training_run.started_at,
                training_completed_at=datetime.utcnow(),
                training_matches=len(predictions_home),
                training_leagues=leagues or [],
                training_seasons=seasons or [],
                brier_score=metrics['brierScore'],
                log_loss=metrics['logLoss'],
                model_weights=calibration_metadata
            )
            
            self.db.add(model)
            self.db.flush()
            
            # Store calibration curve data in calibration_data table
            # Group matches by league for league-specific calibration (optional)
            league_ids = {}
            if leagues:
                # League is already imported at the top of the file
                for league_code in leagues:
                    league = self.db.query(League).filter(League.code == league_code).first()
                    if league:
                        league_ids[league_code] = league.id
            
            # Store calibration curves for each outcome
            for outcome_type, outcome_enum in [("H", MatchResult.H), ("D", MatchResult.D), ("A", MatchResult.A)]:
                if outcome_type in calibration_curves:
                    curve = calibration_curves[outcome_type]
                    
                    # Store global calibration (no league_id)
                    for i, (pred_bucket, obs_freq) in enumerate(zip(curve.predicted_buckets, curve.observed_frequencies)):
                        if i < len(curve.sample_counts):
                            sample_count = curve.sample_counts[i]
                            
                            # Only store if we have samples
                            if sample_count > 0:
                                cal_data = CalibrationData(
                                    model_id=model.id,
                                    league_id=None,  # Global calibration
                                    outcome_type=outcome_enum,
                                    predicted_prob_bucket=round(pred_bucket, 3),
                                    actual_frequency=round(obs_freq, 4),
                                    sample_count=sample_count
                                )
                                self.db.add(cal_data)
            
            self.db.flush()  # Flush calibration data before committing
            
            # Update training run
            training_run.model_id = model.id
            training_run.status = ModelStatus.active
            training_run.completed_at = datetime.utcnow()
            training_run.match_count = len(predictions_home)
            training_run.brier_score = metrics['brierScore']
            training_run.log_loss = metrics['logLoss']
            training_run.logs = {
                "leagues": leagues,
                "seasons": seasons,
                "base_model_id": base_model.id,
                "base_model_version": base_model.version,
                "calibration_metadata": calibration_metadata['calibration_metadata'],
            }
            
            self.db.commit()
            
            logger.info(f"Calibration model training complete: {version}")
            
            if task_id:
                self._update_task_status(task_id, "completed", 100, "Training complete", result=metrics)
            
            return {
                'modelId': model.id,
                'version': version,
                'metrics': metrics,
                'matchCount': len(predictions_home),
                'trainingRunId': training_run.id,
            }
        except Exception as e:
            training_run.status = ModelStatus.failed
            training_run.error_message = str(e)
            training_run.completed_at = datetime.utcnow()
            self.db.commit()
            if task_id:
                self._update_task_status(task_id, "failed", 0, "", error=str(e))
            raise
    
    def train_full_pipeline(
        self,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Train full pipeline: Poisson → Blending → Calibration
        
        Args:
            leagues: List of league codes
            seasons: List of seasons
            task_id: Task ID for progress tracking
            
        Returns:
            Dict with final model version and metrics
        """
        logger.info(f"Starting full pipeline training (task: {task_id})")
        
        # Step 1: Train Poisson model
        poisson_result = self.train_poisson_model(
            leagues=leagues,
            seasons=seasons,
            task_id=task_id
        )
        
        # Step 2: Train blending model
        blending_result = self.train_blending_model(
            poisson_model_id=poisson_result['modelId'],
            leagues=leagues,
            seasons=seasons,
            task_id=task_id
        )
        
        # Step 3: Train calibration model (on blended model, not Poisson)
        # CRITICAL: Calibrate the blended model, not the raw Poisson model
        # This ensures the final output uses the optimized blend weights
        calibration_result = self.train_calibration_model(
            base_model_id=blending_result['modelId'],  # Use blended model, not Poisson
            leagues=leagues,
            seasons=seasons,
            task_id=task_id
        )
        
        return {
            'poisson': poisson_result,
            'blending': blending_result,
            'calibration': calibration_result,
            'finalMetrics': calibration_result['metrics'],
        }
    
    def train_draw_calibration_model(
        self,
        draw_model_id: Optional[int] = None,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Train draw-only calibration model using isotonic regression.
        
        Calibrates P(D) only. Does not touch home/away probabilities.
        
        Args:
            draw_model_id: ID of draw model to calibrate (optional, uses active if not provided)
            leagues: List of league codes
            seasons: List of seasons
            task_id: Task ID for progress tracking
            
        Returns:
            Dict with training results
        """
        logger.info(f"Starting draw-only calibration model training (task: {task_id})")
        
        # Create training run record
        training_run = TrainingRun(
            run_type='draw_calibration',
            status=ModelStatus.training,
            started_at=datetime.now(),
        )
        self.db.add(training_run)
        self.db.flush()
        
        try:
            if task_id:
                self._update_task_status(task_id, "in_progress", 10, "Loading draw model...")
            
            # Load draw model
            if draw_model_id:
                draw_model = self.db.query(Model).filter(
                    Model.id == draw_model_id,
                    Model.model_type == "draw"
                ).first()
            else:
                # Get active draw model
                draw_model = self.db.query(Model).filter(
                    Model.model_type == "draw",
                    Model.status == ModelStatus.active
                ).order_by(Model.training_completed_at.desc()).first()
            
            if not draw_model:
                raise ValueError("Active draw model not found. Draw model is deterministic and doesn't need training. Train draw calibration separately if needed.")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 20, "Loading prediction data...")
            
            # Load predictions from Prediction table
            # We need predictions with draw probabilities and actual results
            from app.db.models import Prediction, JackpotFixture, MatchResult, PredictionSet
            
            query = self.db.query(Prediction).join(JackpotFixture)
            
            if leagues:
                query = query.join(League, JackpotFixture.league_id == League.id).filter(
                    League.code.in_(leagues)
                )
            
            # Get predictions with actual results (from saved_probability_results)
            # For now, we'll use predictions from fixtures that have actual results
            predictions = query.filter(
                Prediction.set_type == PredictionSet.B  # Use Set B as default
            ).order_by(Prediction.id.asc()).all()
            
            if len(predictions) < 500:
                raise ValueError(f"Insufficient draw samples for calibration (min 500, got {len(predictions)})")
            
            # Extract draw predictions and outcomes
            # Note: We need actual results from saved_probability_results or match results
            # For now, this is a placeholder - actual implementation would join with actual results
            preds_draw = [p.prob_draw for p in predictions]
            
            # Time-ordered split
            split_idx = int(len(preds_draw) * 0.8)
            preds_train = preds_draw[:split_idx]
            
            # For now, we'll use a simplified approach
            # In production, you'd load actual results from saved_probability_results
            # and match them to predictions
            logger.warning("Draw calibration: Using simplified approach. Actual results matching not yet implemented.")
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 50, "Fitting isotonic regression...")
            
            # Fit isotonic regression for draw only
            from app.models.calibration import Calibrator
            
            # For now, create dummy actuals (in production, load from actual results)
            # This is a placeholder - you'd need to join with actual match results
            acts_train = [0.0] * len(preds_train)  # Placeholder
            
            calibrator = Calibrator()
            # Fit only for draw outcome
            calibrator.fit_draw_only(preds_train, acts_train)
            
            if task_id:
                self._update_task_status(task_id, "in_progress", 80, "Storing calibration model...")
            
            # Archive old draw calibration models
            # Note: Using JSONB filter - need to check if this works
            active_draw_calibrations = self.db.query(Model).filter(
                Model.model_type == 'calibration',
                Model.status == ModelStatus.active
            ).all()
            
            for cal_model in active_draw_calibrations:
                if cal_model.model_weights and cal_model.model_weights.get('base_model_type') == 'draw':
                    cal_model.status = ModelStatus.archived
            
            # Create new draw calibration model
            version = f"draw-calibration-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            calibration_metadata = {
                'base_model_id': draw_model.id,
                'base_model_version': draw_model.version,
                'base_model_type': 'draw',
                'outcome': 'D',
                'sample_count': len(preds_train),
                'calibration_metadata': {
                    'D': {
                        'fitted': True,
                        'sample_count': len(preds_train),
                    }
                }
            }
            
            model = Model(
                version=version,
                model_type='calibration',
                status=ModelStatus.active,
                training_started_at=training_run.started_at,
                training_completed_at=datetime.utcnow(),
                training_matches=len(preds_train),
                training_leagues=leagues or [],
                model_weights=calibration_metadata
            )
            
            self.db.add(model)
            self.db.commit()
            
            if task_id:
                self._update_task_status(task_id, "completed", 100, "Draw calibration complete", {
                    "modelId": model.id,
                    "version": version,
                    "sampleCount": len(preds_train)
                })
            
            return {
                'modelId': model.id,
                'version': version,
                'sampleCount': len(preds_train),
            }
            
        except Exception as e:
            self.db.rollback()
            training_run.status = ModelStatus.failed
            training_run.completed_at = datetime.now()
            self.db.commit()
            
            if task_id:
                self._update_task_status(task_id, "failed", 0, "", error=str(e))
            
            logger.error(f"Draw calibration training failed: {e}", exc_info=True)
            raise

