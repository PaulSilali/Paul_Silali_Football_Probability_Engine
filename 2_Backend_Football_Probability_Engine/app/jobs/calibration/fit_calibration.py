"""
Fit Isotonic Calibration
=========================

Fits isotonic regression calibration curves for each outcome (H/D/A).
"""
import uuid
import pickle
from datetime import datetime, timezone
from typing import Optional, List
from sklearn.isotonic import IsotonicRegression
import numpy as np
import logging

from app.jobs.calibration.load_data import load_calibration_dataset
from app.jobs.calibration.persist import persist_calibration
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def fit_isotonic_for_outcome(df, outcome: str) -> IsotonicRegression:
    """
    Fit isotonic regression for a specific outcome.
    
    Args:
        df: DataFrame with prob_* and y_* columns
        outcome: 'H', 'D', or 'A'
    
    Returns:
        Fitted IsotonicRegression model
    """
    if outcome == "H":
        probs = df["prob_home"].values
        y = df["y_home"].values
    elif outcome == "D":
        probs = df["prob_draw"].values
        y = df["y_draw"].values
    elif outcome == "A":
        probs = df["prob_away"].values
        y = df["y_away"].values
    else:
        raise ValueError(f"Invalid outcome: {outcome}. Must be 'H', 'D', or 'A'")
    
    # Filter valid probabilities
    mask = (probs >= 0.0) & (probs <= 1.0) & np.isfinite(probs)
    probs = probs[mask]
    y = y[mask]
    
    if len(probs) < 50:
        raise ValueError(f"Insufficient valid samples for outcome {outcome}: {len(probs)} < 50")
    
    # Check class balance
    if outcome == "D" and y.mean() < 0.05:
        raise ValueError(f"Outcome {outcome} too rare to calibrate safely (rate={y.mean():.3f} < 0.05)")
    
    # Fit isotonic regression
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(probs, y)
    
    # Validate monotonicity
    if len(iso.f_) > 1:
        if not all(iso.f_[i] <= iso.f_[i+1] for i in range(len(iso.f_)-1)):
            raise ValueError(f"Isotonic regression failed monotonicity check for outcome {outcome}")
    
    logger.info(f"Fitted isotonic regression for outcome {outcome}: {len(probs)} samples")
    
    return iso


def run_calibration_job(
    engine: Engine,
    model_version: str,
    league: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_samples: int = 200
) -> List[str]:
    """
    Run calibration job to fit and persist calibration curves.
    
    Args:
        engine: SQLAlchemy engine
        model_version: Model version string (e.g., "poisson-v1.0")
        league: League code for league-specific calibration (None for global)
        start_date: Filter by created_at >= start_date
        end_date: Filter by created_at <= end_date
        min_samples: Minimum samples required
    
    Returns:
        List of calibration_id UUIDs created
    
    Raises:
        RuntimeError: If insufficient data or fitting fails
    """
    logger.info(f"Starting calibration job: model_version={model_version}, league={league}")
    
    # Load dataset
    df = load_calibration_dataset(
        engine=engine,
        start_date=start_date,
        end_date=end_date,
        min_samples=min_samples,
        league=league
    )
    
    # Filter by model_version if specified
    if model_version:
        df = df[df["model_version"] == model_version]
        if len(df) < min_samples:
            raise RuntimeError(
                f"Insufficient samples for model_version {model_version}: {len(df)} < {min_samples}"
            )
    
    calibration_ids = []
    
    # Fit for each outcome
    for outcome in ["H", "D", "A"]:
        try:
            # Fit isotonic regression
            iso = fit_isotonic_for_outcome(df, outcome)
            
            # Prepare payload
            payload = {
                "calibration_id": str(uuid.uuid4()),
                "outcome": outcome,
                "league": league,
                "model_version": model_version,
                "created_at": datetime.now(timezone.utc),
                "valid_from": datetime.now(timezone.utc),
                "calibration_blob": pickle.dumps(iso),
                "samples_used": len(df),
                "is_active": False,  # Never auto-activate
                "notes": f"Fitted from {len(df)} samples"
            }
            
            # Persist
            persist_calibration(engine, payload)
            calibration_ids.append(payload["calibration_id"])
            
            logger.info(f"✓ Calibration fitted for outcome {outcome}: {payload['calibration_id']}")
            
        except Exception as e:
            logger.error(f"Failed to fit calibration for outcome {outcome}: {e}")
            # Continue with other outcomes
            continue
    
    if not calibration_ids:
        raise RuntimeError("Failed to fit any calibration curves")
    
    logger.info(f"Calibration job complete: {len(calibration_ids)} curves fitted")
    
    return calibration_ids

