"""
Automated Pipeline API Endpoint

Triggers automated pipeline: detect → download → train → recompute
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.automated_pipeline import AutomatedPipelineService
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
import threading

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRequest(BaseModel):
    team_names: List[str]
    league_id: Optional[int] = None
    auto_download: bool = True
    auto_train: bool = True
    auto_recompute: bool = False
    jackpot_id: Optional[str] = None
    seasons: Optional[List[str]] = None
    max_seasons: int = 7
    base_model_window_years: Optional[float] = None  # Recent data focus: 2, 3, or 4 years (default: 4)


class PipelineStatusRequest(BaseModel):
    team_names: List[str]
    league_id: Optional[int] = None


# Store for pipeline task status (in production, use Redis/Celery)
pipeline_tasks = {}


@router.post("/check-status")
async def check_teams_status(
    request: PipelineStatusRequest,
    db: Session = Depends(get_db)
):
    """
    Check validation and training status for teams
    
    Returns which teams are validated, which are trained, etc.
    """
    service = AutomatedPipelineService(db)
    result = service.check_teams_status(request.team_names, request.league_id)
    
    return {
        "success": True,
        "data": result
    }


@router.post("/run")
async def run_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run automated pipeline:
    1. Check team validation and training status
    2. Download missing data (if auto_download=True)
    3. Create missing teams
    4. Retrain model (if auto_train=True)
    5. Recompute probabilities (if auto_recompute=True)
    
    Returns task ID for async execution
    """
    import uuid
    from datetime import datetime
    
    task_id = f"pipeline-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}"
    
    # Initialize task status
    pipeline_tasks[task_id] = {
        "taskId": task_id,
        "status": "queued",
        "progress": 0,
        "phase": "Initializing pipeline...",
        "startedAt": datetime.now().isoformat(),
        "steps": {}
    }
    
    # Run pipeline in background
    def run_pipeline_task():
        try:
            from app.db.session import SessionLocal
            background_db = SessionLocal()
            service = AutomatedPipelineService(background_db)
            
            # Progress callback to update pipeline_tasks
            def update_progress(progress: int, phase: str, steps: dict = None):
                pipeline_tasks[task_id]["progress"] = progress
                pipeline_tasks[task_id]["phase"] = phase
                if steps:
                    pipeline_tasks[task_id]["steps"] = steps
            
            pipeline_tasks[task_id]["status"] = "running"
            update_progress(10, "Checking team status...")
            
            result = service.run_full_pipeline(
                team_names=request.team_names,
                league_id=request.league_id,
                auto_download=request.auto_download,
                auto_train=request.auto_train,
                auto_recompute=request.auto_recompute,
                jackpot_id=request.jackpot_id,
                seasons=request.seasons,
                max_seasons=request.max_seasons,
                base_model_window_years=request.base_model_window_years,  # Recent data focus
                save_to_jackpot=True,  # Save metadata to jackpot
                progress_callback=update_progress  # Pass callback for progress updates
            )
            
            # Update final status with all steps
            pipeline_tasks[task_id]["status"] = result.get("status", "completed")
            pipeline_tasks[task_id]["progress"] = 100
            pipeline_tasks[task_id]["phase"] = "Complete"
            pipeline_tasks[task_id]["steps"] = result.get("steps", {})
            pipeline_tasks[task_id]["result"] = result
            pipeline_tasks[task_id]["completedAt"] = datetime.now().isoformat()
            
            background_db.close()
            
        except Exception as e:
            logger.error(f"Pipeline task {task_id} failed: {e}", exc_info=True)
            pipeline_tasks[task_id]["status"] = "failed"
            pipeline_tasks[task_id]["error"] = str(e)
            pipeline_tasks[task_id]["progress"] = 0
            pipeline_tasks[task_id]["phase"] = f"Error: {str(e)}"
            pipeline_tasks[task_id]["completedAt"] = datetime.now().isoformat()
            if 'background_db' in locals():
                background_db.close()
    
    # Start background thread
    thread = threading.Thread(target=run_pipeline_task, daemon=True)
    thread.start()
    
    return {
        "success": True,
        "data": {
            "taskId": task_id,
            "status": "queued",
            "message": f"Pipeline started. Use /api/pipeline/status/{task_id} to check status."
        }
    }


@router.get("/status/{task_id}")
async def get_pipeline_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get status of a pipeline task
    """
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "success": True,
        "data": pipeline_tasks[task_id]
    }


@router.post("/download-missing")
async def download_missing_data(
    request: PipelineStatusRequest,
    seasons: Optional[List[str]] = None,
    max_seasons: int = 7,
    db: Session = Depends(get_db)
):
    """
    Download missing data for teams without training data
    """
    service = AutomatedPipelineService(db)
    
    # Check status first
    status = service.check_teams_status(request.team_names, request.league_id)
    
    # Download data for missing/untrained teams
    teams_to_download = status["missing_teams"] + [
        name for name, details in status["team_details"].items()
        if details["team_id"] in status["untrained_teams"]
    ]
    
    if not teams_to_download:
        return {
            "success": True,
            "data": {
                "message": "All teams have sufficient data",
                "downloaded": []
            }
        }
    
    result = service.download_missing_team_data(
        teams_to_download,
        request.league_id,
        seasons,
        max_seasons
    )
    
    return {
        "success": True,
        "data": result
    }

