"""
Draw diagnostics API endpoints

Provides endpoints for draw probability diagnostics, calibration metrics,
and component analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.jackpot import ApiResponse
from typing import Optional, List, Dict
from app.models.calibration_draw import (
    calculate_draw_brier_score,
    calculate_draw_reliability_curve,
    load_training_data_from_predictions,
    train_draw_calibrator
)
from app.db.models import Prediction, JackpotFixture
from sqlalchemy import text, func
import numpy as np
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/draw", tags=["draw"])


@router.get("/diagnostics", response_model=ApiResponse)
async def get_draw_diagnostics(
    model_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get draw probability diagnostics including Brier score and reliability curve.
    """
    try:
        # Load training data
        predicted_probs, actual_outcomes = load_training_data_from_predictions(
            db, model_id, limit=10000
        )
        
        if len(predicted_probs) == 0:
            return ApiResponse(
                data={
                    "brier_score": None,
                    "reliability_curve": [],
                    "sample_count": 0,
                    "message": "No validation data available"
                },
                success=True
            )
        
        # Calculate Brier score
        brier_score = calculate_draw_brier_score(predicted_probs, actual_outcomes)
        
        # Calculate reliability curve
        reliability_curve = calculate_draw_reliability_curve(
            predicted_probs, actual_outcomes, n_bins=10
        )
        
        # Calculate additional metrics
        mean_predicted = float(np.mean(predicted_probs))
        mean_actual = float(np.mean(actual_outcomes))
        calibration_error = abs(mean_predicted - mean_actual)
        
        return ApiResponse(
            data={
                "brier_score": round(brier_score, 4),
                "reliability_curve": reliability_curve,
                "sample_count": len(predicted_probs),
                "mean_predicted": round(mean_predicted, 4),
                "mean_actual": round(mean_actual, 4),
                "calibration_error": round(calibration_error, 4)
            },
            success=True
        )
    except Exception as e:
        logger.error(f"Error calculating draw diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/{fixture_id}", response_model=ApiResponse)
async def get_draw_components(
    fixture_id: int,
    db: Session = Depends(get_db)
):
    """
    Get draw structural components for a specific fixture.
    """
    try:
        from app.features.draw_features import compute_draw_components
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(
            JackpotFixture.id == fixture_id
        ).first()
        
        if not fixture:
            raise HTTPException(status_code=404, detail="Fixture not found")
        
        # Compute components
        components = compute_draw_components(
            db=db,
            fixture_id=fixture_id,
            league_id=getattr(fixture, 'league_id', None),
            home_team_id=getattr(fixture, 'home_team_id', None),
            away_team_id=getattr(fixture, 'away_team_id', None),
            match_date=None
        )
        
        return ApiResponse(
            data=components.to_dict(),
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting draw components: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ApiResponse)
async def get_draw_stats(
    db: Session = Depends(get_db)
):
    """
    Get aggregate draw statistics.
    """
    try:
        # Get average draw multiplier
        result = db.execute(
            text("""
                SELECT 
                    AVG((draw_components->>'total_multiplier')::float) as avg_multiplier,
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN draw_components IS NOT NULL THEN 1 END) as with_components
                FROM predictions
                WHERE created_at > NOW() - INTERVAL '30 days'
            """)
        ).fetchone()
        
        # Get draw probability distribution
        distribution = db.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN prob_draw < 0.20 THEN 'Low'
                        WHEN prob_draw < 0.30 THEN 'Medium'
                        ELSE 'High'
                    END as category,
                    COUNT(*) as count
                FROM predictions
                WHERE created_at > NOW() - INTERVAL '30 days'
                GROUP BY category
            """)
        ).fetchall()
        
        return ApiResponse(
            data={
                "avg_multiplier": float(result.avg_multiplier) if result.avg_multiplier else None,
                "total_predictions": result.total_predictions or 0,
                "with_components": result.with_components or 0,
                "distribution": [
                    {"category": row.category, "count": row.count}
                    for row in distribution
                ]
            },
            success=True
        )
    except Exception as e:
        logger.error(f"Error getting draw stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibrate", response_model=ApiResponse)
async def train_draw_calibrator_endpoint(
    model_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Train draw-only isotonic calibrator.
    """
    try:
        calibrator = train_draw_calibrator(db, model_id)
        
        return ApiResponse(
            data={
                "is_fitted": calibrator.is_fitted,
                "message": "Calibrator trained successfully" if calibrator.is_fitted else "Insufficient training data"
            },
            success=True
        )
    except Exception as e:
        logger.error(f"Error training draw calibrator: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

