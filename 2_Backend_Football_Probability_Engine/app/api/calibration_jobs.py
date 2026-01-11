"""
Calibration Jobs API
====================

API endpoints for running calibration jobs and managing calibration curves.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from app.db.session import get_db
from app.schemas.jackpot import ApiResponse
from app.jobs.calibration.fit_calibration import run_calibration_job
from app.jobs.calibration.activate import activate_calibration, load_active_calibration
from app.db.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.post("/fit", response_model=ApiResponse)
async def fit_calibration(
    model_version: str,
    league: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_samples: int = 200,
    db: Session = Depends(get_db)
):
    """
    Fit calibration curves for a model version.
    
    This creates new calibration curves but does NOT activate them.
    Use /calibration/activate to activate after review.
    """
    try:
        calibration_ids = run_calibration_job(
            engine=engine,
            model_version=model_version,
            league=league,
            start_date=start_date,
            end_date=end_date,
            min_samples=min_samples
        )
        
        return ApiResponse(
            success=True,
            message=f"Fitted {len(calibration_ids)} calibration curves",
            data={
                "calibration_ids": calibration_ids,
                "model_version": model_version,
                "league": league
            }
        )
    except Exception as e:
        logger.error(f"Error fitting calibration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fit calibration: {str(e)}")


@router.post("/activate/{calibration_id}", response_model=ApiResponse)
async def activate_calibration_endpoint(
    calibration_id: str,
    db: Session = Depends(get_db)
):
    """
    Activate a calibration curve.
    
    This deactivates the previous active calibration for the same scope
    and activates the specified calibration.
    """
    try:
        activate_calibration(engine, calibration_id)
        
        return ApiResponse(
            success=True,
            message=f"Activated calibration {calibration_id}",
            data={"calibration_id": calibration_id}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating calibration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to activate calibration: {str(e)}")


@router.get("/active", response_model=ApiResponse)
async def get_active_calibrations(
    model_version: str,
    league: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get active calibration for a model version.
    """
    try:
        calibrations = {}
        
        for outcome in ["H", "D", "A"]:
            cal = load_active_calibration(engine, outcome, model_version, league)
            if cal:
                calibrations[outcome] = {
                    "calibration_id": cal["calibration_id"],
                    "samples_used": cal["samples_used"],
                    "created_at": cal["created_at"].isoformat(),
                    "valid_from": cal["valid_from"].isoformat()
                }
        
        return ApiResponse(
            success=True,
            message="Active calibrations loaded",
            data={
                "model_version": model_version,
                "league": league,
                "calibrations": calibrations
            }
        )
    except Exception as e:
        logger.error(f"Error loading active calibrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load calibrations: {str(e)}")

