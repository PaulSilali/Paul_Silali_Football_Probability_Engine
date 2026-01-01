"""
Model Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Model, ModelStatus
from app.schemas.prediction import ModelVersionResponse
from datetime import datetime
from typing import List, Dict, Optional
import logging
import uuid
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["model"])


@router.get("/status")
async def get_model_status(
    db: Session = Depends(get_db)
):
    """Get detailed model status for all model types"""
    logger.info("=== GET MODEL STATUS REQUEST ===")
    logger.info(f"Request time (UTC): {datetime.utcnow().isoformat()}")
    logger.info(f"Request time (Local): {datetime.now().isoformat()}")
    
    # Get active models for each type
    poisson_model = db.query(Model).filter(
        Model.model_type == "poisson",
        Model.status == ModelStatus.active
    ).order_by(Model.training_completed_at.desc()).first()
    
    blending_model = db.query(Model).filter(
        Model.model_type == "blending",
        Model.status == ModelStatus.active
    ).order_by(Model.training_completed_at.desc()).first()
    
    calibration_model = db.query(Model).filter(
        Model.model_type == "calibration",
        Model.status == ModelStatus.active
    ).order_by(Model.training_completed_at.desc()).first()
    
    # Log what models were found
    logger.info(f"Poisson model found: {poisson_model.version if poisson_model else 'None'}")
    if poisson_model:
        logger.info(f"  - ID: {poisson_model.id}")
        if poisson_model.training_completed_at:
            logger.info(f"  - training_completed_at (UTC): {poisson_model.training_completed_at.isoformat()}")
        else:
            logger.info(f"  - training_completed_at: None")
    
    logger.info(f"Blending model found: {blending_model.version if blending_model else 'None'}")
    if blending_model:
        logger.info(f"  - ID: {blending_model.id}")
        if blending_model.training_completed_at:
            logger.info(f"  - training_completed_at (UTC): {blending_model.training_completed_at.isoformat()}")
        else:
            logger.info(f"  - training_completed_at: None")
    
    logger.info(f"Calibration model found: {calibration_model.version if calibration_model else 'None'}")
    if calibration_model:
        logger.info(f"  - ID: {calibration_model.id}")
        if calibration_model.training_completed_at:
            logger.info(f"  - training_completed_at (UTC): {calibration_model.training_completed_at.isoformat()}")
        else:
            logger.info(f"  - training_completed_at: None")
    
    # Return status for Poisson model (primary model) or first available
    model = poisson_model or blending_model or calibration_model
    
    if not model:
        logger.warning("No active model found")
        return {
            "success": True,
            "data": {
                "status": "no_model",
                "message": "No active model found"
            }
        }
    
    # Build response with all model types
    response_data = {
        "version": model.version,
        "status": model.status.value,
        "trainedAt": model.training_completed_at.isoformat() if model.training_completed_at else None,
        "brierScore": model.brier_score,
        "logLoss": model.log_loss,
        "accuracy": model.overall_accuracy,
        "drawAccuracy": model.draw_accuracy,
        "trainingMatches": model.training_matches,
        "modelType": model.model_type
    }
    
    # Add Poisson-specific data if available
    if poisson_model:
        poisson_trained_at = poisson_model.training_completed_at.isoformat() if poisson_model.training_completed_at else None
        response_data["poisson"] = {
            "version": poisson_model.version,
            "trainedAt": poisson_trained_at,
            "brierScore": poisson_model.brier_score,
            "logLoss": poisson_model.log_loss,
            "drawAccuracy": poisson_model.draw_accuracy,
            "trainingMatches": poisson_model.training_matches
        }
        logger.info(f"Poisson trainedAt in response: {poisson_trained_at}")
    
    # Add Blending-specific data if available
    if blending_model:
        blending_trained_at = blending_model.training_completed_at.isoformat() if blending_model.training_completed_at else None
        response_data["blending"] = {
            "version": blending_model.version,
            "trainedAt": blending_trained_at,
            "brierScore": blending_model.brier_score,
            "logLoss": blending_model.log_loss,
            "trainingMatches": blending_model.training_matches
        }
        logger.info(f"Blending trainedAt in response: {blending_trained_at}")
    
    # Add Calibration-specific data if available
    if calibration_model:
        calibration_trained_at = calibration_model.training_completed_at.isoformat() if calibration_model.training_completed_at else None
        response_data["calibration"] = {
            "version": calibration_model.version,
            "trainedAt": calibration_trained_at,
            "brierScore": calibration_model.brier_score,
            "logLoss": calibration_model.log_loss,
            "trainingMatches": calibration_model.training_matches
        }
        logger.info(f"Calibration trainedAt in response: {calibration_trained_at}")
    
    logger.info("=== MODEL STATUS RESPONSE SENT ===")
    
    return {
        "success": True,
        "data": response_data
    }


@router.post("/train")
async def train_model(
    request: Dict = Body(default={}),
    db: Session = Depends(get_db)
):
    """
    Trigger model training
    
    Request body:
    {
        "modelType": "poisson" | "blending" | "calibration" | "draw" | "full",
        "leagues": ["E0", "SP1", ...],  # Optional
        "seasons": ["2324", "2223", ...],  # Optional
        "dateFrom": "2020-01-01",  # Optional
        "dateTo": "2024-12-31"  # Optional
    }
    
    Returns task ID for async processing
    """
    from app.services.model_training import ModelTrainingService
    from app.api.tasks import task_store
    import threading
    
    model_type = request.get("modelType", "full")
    leagues = request.get("leagues")
    seasons = request.get("seasons")
    date_from = request.get("dateFrom")
    date_to = request.get("dateTo")
    
    # Generate task ID
    task_id = f"train-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}"
    
    # Initialize task in store
    task_store[task_id] = {
        "taskId": task_id,
        "status": "queued",
        "progress": 0,
        "phase": "Initializing training...",
        "message": f"Training {model_type} model",
        "startedAt": datetime.now().isoformat(),
    }
    
    # Start async training (in production, use Celery)
    def run_training():
        try:
            task_store[task_id]["status"] = "running"
            task_store[task_id]["progress"] = 5
            task_store[task_id]["phase"] = "Loading training data..."
            
            # Create new DB session for background task
            from app.db.session import SessionLocal
            background_db = SessionLocal()
            service = ModelTrainingService(background_db)
            
            # Parse dates if provided
            date_from_obj = datetime.fromisoformat(date_from) if date_from else None
            date_to_obj = datetime.fromisoformat(date_to) if date_to else None
            
            if model_type == "poisson":
                result = service.train_poisson_model(
                    leagues=leagues,
                    seasons=seasons,
                    date_from=date_from_obj,
                    date_to=date_to_obj,
                    task_id=task_id
                )
                task_store[task_id]["result"] = {
                    "modelId": result["modelId"],
                    "version": result["version"],
                    "metrics": result["metrics"],
                }
            elif model_type == "blending":
                result = service.train_blending_model(
                    leagues=leagues,
                    seasons=seasons,
                    date_from=date_from_obj,
                    date_to=date_to_obj,
                    task_id=task_id
                )
                task_store[task_id]["result"] = {
                    "modelId": result.get("modelId"),
                    "version": result["version"],
                    "metrics": result["metrics"],
                    "optimalAlpha": result.get("optimalAlpha"),
                }
            elif model_type == "calibration":
                result = service.train_calibration_model(
                    leagues=leagues,
                    seasons=seasons,
                    date_from=date_from_obj,
                    date_to=date_to_obj,
                    task_id=task_id
                )
                task_store[task_id]["result"] = {
                    "modelId": result.get("modelId"),
                    "version": result["version"],
                    "metrics": result["metrics"],
                }
            elif model_type == "draw":
                # Draw model is deterministic - it doesn't need training
                # Draw calibration can be trained separately if needed
                task_store[task_id]["status"] = "failed"
                task_store[task_id]["error"] = "Draw model is deterministic and doesn't need training. Draw model computes P(Draw) from Poisson outputs at inference time. If you need draw calibration, train it separately."
                task_store[task_id]["completedAt"] = datetime.now().isoformat()
                background_db.close()
                return
            else:  # full pipeline
                result = service.train_full_pipeline(
                    leagues=leagues,
                    seasons=seasons,
                    task_id=task_id
                )
                task_store[task_id]["result"] = {
                    "poisson": result["poisson"],
                    "blending": result["blending"],
                    "calibration": result["calibration"],
                    "metrics": result["finalMetrics"],
                }
            
            task_store[task_id]["status"] = "completed"
            task_store[task_id]["progress"] = 100
            task_store[task_id]["phase"] = "Complete"
            task_store[task_id]["completedAt"] = datetime.now().isoformat()
            
            background_db.close()
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            task_store[task_id]["status"] = "failed"
            task_store[task_id]["error"] = str(e)
            task_store[task_id]["completedAt"] = datetime.now().isoformat()
            if 'background_db' in locals():
                background_db.close()
    
    # Run training in background thread (in production, use Celery)
    thread = threading.Thread(target=run_training, daemon=True)
    thread.start()
    
    return {
        "success": True,
        "data": {
            "taskId": task_id,
            "status": "queued",
            "message": f"Model training queued. Use /api/tasks/{task_id} to check status."
        }
    }


@router.get("/versions")
async def get_model_versions(
    db: Session = Depends(get_db)
):
    """Get all model versions"""
    models = db.query(Model).order_by(Model.training_completed_at.desc()).all()
    
    return {
        "data": [
            {
                "id": str(model.id),
                "version": model.version,
                "modelType": model.model_type,
                "status": model.status.value,
                "trainedAt": model.training_completed_at.isoformat() if model.training_completed_at else None,
                "brierScore": model.brier_score,
                "logLoss": model.log_loss,
                "drawAccuracy": model.draw_accuracy,
                "trainingMatches": model.training_matches,
                "trainingLeagues": model.training_leagues,
                "trainingSeasons": model.training_seasons,
                "isActive": model.status == ModelStatus.active,
            }
            for model in models
        ],
        "success": True,
        "count": len(models)
    }


@router.get("/training-history")
async def get_training_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get training run history from database with actual model status"""
    from app.db.models import TrainingRun, Model
    
    runs = db.query(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(limit).all()
    
    # Build response with actual model status
    results = []
    for run in runs:
        # Get actual model status if model_id exists
        model_status = None
        if run.model_id:
            model = db.query(Model).filter(Model.id == run.model_id).first()
            if model:
                model_status = model.status.value  # This shows if model is active/archived
        
        # Use model status if available, otherwise use training run status
        # Training run status shows if training completed/failed
        # Model status shows if model is currently active or archived
        display_status = model_status if model_status else (run.status.value if run.status else "unknown")
        
        results.append({
            "id": str(run.id),
            "modelId": str(run.model_id) if run.model_id else None,
            "runType": run.run_type,
            "status": display_status,  # Shows actual model status (active/archived) if model exists
            "trainingStatus": run.status.value if run.status else "unknown",  # Training run status (completed/failed)
            "startedAt": run.started_at.isoformat() if run.started_at else None,
            "completedAt": run.completed_at.isoformat() if run.completed_at else None,
            "matchCount": run.match_count,
            "dateFrom": run.date_from.isoformat() if run.date_from else None,
            "dateTo": run.date_to.isoformat() if run.date_to else None,
            "brierScore": run.brier_score,
            "logLoss": run.log_loss,
            "validationAccuracy": run.validation_accuracy,
            "errorMessage": run.error_message,
            "duration": (
                (run.completed_at - run.started_at).total_seconds() / 60
                if run.completed_at and run.started_at
                else None
            ),
        })
    
    return {
        "success": True,
        "data": results,
        "count": len(results)
    }


@router.get("/leagues")
async def get_leagues(
    db: Session = Depends(get_db)
):
    """Get all available leagues for training configuration"""
    from app.db.models import League
    
    leagues = db.query(League).filter(League.is_active == True).order_by(League.code).all()
    
    return {
        "success": True,
        "data": [
            {
                "code": league.code,
                "name": league.name,
                "country": league.country,
                "tier": league.tier,
            }
            for league in leagues
        ],
        "count": len(leagues)
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

