"""
Automated Training API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.mlops.training_pipeline import AutomatedTrainingPipeline
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["automated-training"])


@router.post("/automated/run")
async def run_automated_training(
    leagues: Optional[List[str]] = None,
    seasons: Optional[List[str]] = None,
    auto_promote: bool = True,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Run automated training pipeline
    
    Args:
        leagues: List of league codes (None = all)
        seasons: List of seasons (None = all)
        auto_promote: Automatically promote if metrics improve
        background_tasks: FastAPI background tasks
        
    Returns:
        Training status and results
    """
    try:
        pipeline = AutomatedTrainingPipeline(db)
        
        # Run training in background if requested
        if background_tasks:
            background_tasks.add_task(
                pipeline.train_and_promote,
                leagues=leagues,
                seasons=seasons,
                auto_promote=auto_promote
            )
            return {
                "success": True,
                "message": "Training started in background",
                "status": "running"
            }
        else:
            # Run synchronously
            result = pipeline.train_and_promote(
                leagues=leagues,
                seasons=seasons,
                auto_promote=auto_promote
            )
            return {
                "success": result.get("success", False),
                "trained": result.get("trained", False),
                "promoted": result.get("promoted", False),
                "current_brier": result.get("current_brier"),
                "new_brier": result.get("new_brier"),
                "status": "completed" if result.get("trained") else "skipped"
            }
    
    except Exception as e:
        logger.error(f"Error running automated training: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automated/status")
async def get_training_status(
    db: Session = Depends(get_db)
):
    """Get status of automated training (should retrain?)"""
    try:
        pipeline = AutomatedTrainingPipeline(db)
        should_retrain = pipeline.should_retrain()
        
        # Get current model info
        from app.db.models import Model, ModelStatus
        current_model = db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == 'calibration'
        ).order_by(Model.training_completed_at.desc()).first()
        
        return {
            "success": True,
            "should_retrain": should_retrain,
            "current_model": {
                "version": current_model.version if current_model else None,
                "brier_score": current_model.brier_score if current_model else None,
                "last_trained": current_model.training_completed_at.isoformat() if current_model and current_model.training_completed_at else None,
                "days_since_training": (
                    (datetime.utcnow() - current_model.training_completed_at).days
                    if current_model and current_model.training_completed_at
                    else None
                )
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting training status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

