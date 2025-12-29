"""
Model Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Model, ModelStatus
from app.schemas.prediction import ModelVersionResponse
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["model"])


@router.get("/status")
async def get_model_status(
    db: Session = Depends(get_db)
):
    """Get detailed model status"""
    model = db.query(Model).filter(Model.status == ModelStatus.active).first()
    
    if not model:
        return {
            "status": "no_model",
            "message": "No active model found"
        }
    
    return {
        "version": model.version,
        "status": model.status.value,
        "trainedAt": model.training_completed_at.isoformat() if model.training_completed_at else None,
        "brierScore": model.brier_score,
        "logLoss": model.log_loss,
        "accuracy": model.overall_accuracy,
        "drawAccuracy": model.draw_accuracy,
        "trainingMatches": model.training_matches
    }


@router.post("/train")
async def train_model(
    db: Session = Depends(get_db)
):
    """
    Trigger model training
    
    Returns task ID for async processing
    """
    # TODO: Implement actual training logic
    # For now, return task ID
    task_id = f"task-{int(datetime.now().timestamp())}"
    
    # In production, this would:
    # 1. Queue a Celery task
    # 2. Return task ID immediately
    # 3. Process training asynchronously
    
    return {
        "taskId": task_id,
        "status": "queued",
        "message": "Model training queued. Use /api/tasks/{taskId} to check status."
    }


@router.post("/versions/{version_id}/activate")
async def activate_model_version(
    version_id: str,
    db: Session = Depends(get_db)
):
    """Activate a specific model version"""
    # Find model by version string or ID
    model = db.query(Model).filter(
        (Model.id == int(version_id)) | (Model.version == version_id)
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found")
    
    # Deactivate all other models
    db.query(Model).filter(Model.status == ModelStatus.active).update(
        {"status": ModelStatus.archived}
    )
    
    # Activate selected model
    model.status = ModelStatus.active
    db.commit()
    
    return {
        "data": {
            "id": str(model.id),
            "version": model.version,
            "isActive": True,
            "activatedAt": datetime.now().isoformat()
        },
        "success": True
    }

