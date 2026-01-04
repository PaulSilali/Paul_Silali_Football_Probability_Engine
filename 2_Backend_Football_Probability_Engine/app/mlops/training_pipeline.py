"""
Automated Training Pipeline
Scheduled weekly retraining with automatic model promotion
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.db.models import Model, ModelStatus, TrainingRun
from app.services.model_training import ModelTrainingService

logger = logging.getLogger(__name__)

# Optional MLflow import
try:
    from app.mlops.mlflow_client import MLflowModelRegistry
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    MLflowModelRegistry = None


class AutomatedTrainingPipeline:
    """
    Automated training pipeline for Dixon-Coles model
    
    Features:
    - Weekly automated retraining
    - Hyperparameter optimization
    - Model validation
    - Automatic promotion to production (if metrics improve)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.training_service = ModelTrainingService(db)
        self.mlflow_registry = None
        if MLFLOW_AVAILABLE:
            try:
                self.mlflow_registry = MLflowModelRegistry()
            except Exception as e:
                logger.warning(f"MLflow not available: {e}")
    
    def should_retrain(self, days_since_last_training: int = 7) -> bool:
        """Check if model should be retrained"""
        active_model = self.db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == 'calibration'
        ).order_by(Model.training_completed_at.desc()).first()
        
        if not active_model:
            return True  # No model exists, need to train
        
        if not active_model.training_completed_at:
            return True  # Model was never completed
        
        days_ago = (datetime.utcnow() - active_model.training_completed_at).days
        return days_ago >= days_since_last_training
    
    def train_and_promote(
        self,
        leagues: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
        auto_promote: bool = True
    ) -> Dict:
        """
        Train new model and optionally promote to production if better
        
        Args:
            leagues: List of league codes
            seasons: List of seasons
            auto_promote: Automatically promote if metrics improve
            
        Returns:
            Training results with promotion status
        """
        logger.info("Starting automated training pipeline")
        
        # Get current production model metrics
        current_model = self.db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == 'calibration'
        ).order_by(Model.training_completed_at.desc()).first()
        
        current_brier = current_model.brier_score if current_model else None
        
        # Train full pipeline (Poisson -> Blending -> Calibration)
        try:
            result = self.training_service.train_full_pipeline(
                leagues=leagues,
                seasons=seasons
            )
            
            new_brier = result['finalMetrics'].get('brierScore')
            
            # Check if new model is better
            should_promote = False
            if auto_promote:
                if current_brier is None:
                    should_promote = True  # No existing model
                elif new_brier and new_brier < current_brier:
                    should_promote = True  # New model is better
                    improvement = ((current_brier - new_brier) / current_brier) * 100
                    logger.info(f"New model is {improvement:.2f}% better. Brier: {current_brier:.4f} -> {new_brier:.4f}")
            
            # Promote to production if better
            if should_promote and self.mlflow_registry:
                try:
                    calibration_model_id = result['calibration']['modelId']
                    calibration_model = self.db.query(Model).filter(
                        Model.id == calibration_model_id
                    ).first()
                    
                    if calibration_model and result['calibration'].get('mlflowRunId'):
                        # Register model in MLflow
                        model_version = self.mlflow_registry.register_model(
                            run_id=result['calibration']['mlflowRunId'],
                            model_name="dixon_coles_production",
                            description=f"Auto-trained on {datetime.utcnow().isoformat()}"
                        )
                        
                        # Promote to production
                        self.mlflow_registry.promote_to_production(
                            model_name="dixon_coles_production",
                            version=model_version
                        )
                        
                        logger.info(f"Promoted model version {model_version} to production")
                except Exception as e:
                    logger.error(f"Error promoting model: {e}")
            
            return {
                "success": True,
                "trained": True,
                "promoted": should_promote,
                "current_brier": current_brier,
                "new_brier": new_brier,
                "results": result
            }
            
        except Exception as e:
            logger.error(f"Automated training failed: {e}", exc_info=True)
            return {
                "success": False,
                "trained": False,
                "error": str(e)
            }
    
    def schedule_weekly_training(self):
        """Schedule weekly training (to be called by cron/scheduler)"""
        if self.should_retrain(days_since_last_training=7):
            logger.info("Weekly training triggered")
            return self.train_and_promote()
        else:
            logger.info("Skipping training - model is still fresh")
            return {
                "success": True,
                "trained": False,
                "reason": "Model is less than 7 days old"
            }

