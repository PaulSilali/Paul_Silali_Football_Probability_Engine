"""
Draw-only isotonic calibration

Calibrates draw probabilities separately from home/away probabilities
using isotonic regression.
"""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Tuple, Dict, Optional
from app.db.models import Prediction, MatchResult, JackpotFixture
import logging

logger = logging.getLogger(__name__)


class DrawIsotonicCalibrator:
    """
    Isotonic calibrator for draw probabilities only.
    
    Trains on (predicted_draw_prob, actual_is_draw) pairs
    and outputs calibrated draw probabilities.
    """
    
    def __init__(self, out_of_bounds: str = "clip"):
        """
        Initialize calibrator.
        
        Args:
            out_of_bounds: How to handle out-of-bounds predictions
                          ('clip' or 'extrapolate')
        """
        self.model = IsotonicRegression(
            out_of_bounds=out_of_bounds,
            increasing=True
        )
        self.is_fitted = False
    
    def fit(self, predicted_probs: np.ndarray, actual_outcomes: np.ndarray):
        """
        Fit calibrator on training data.
        
        Args:
            predicted_probs: Array of predicted draw probabilities (0-1)
            actual_outcomes: Array of actual outcomes (1 for draw, 0 for not draw)
        """
        if len(predicted_probs) != len(actual_outcomes):
            raise ValueError("predicted_probs and actual_outcomes must have same length")
        
        # Filter out invalid values
        valid_mask = (
            (predicted_probs >= 0) & (predicted_probs <= 1) &
            np.isfinite(predicted_probs) &
            np.isfinite(actual_outcomes)
        )
        
        if valid_mask.sum() < 10:
            logger.warning("Too few valid samples for calibration, skipping fit")
            self.is_fitted = False
            return
        
        X = predicted_probs[valid_mask]
        y = actual_outcomes[valid_mask].astype(float)
        
        self.model.fit(X, y)
        self.is_fitted = True
        
        logger.info(f"Fitted draw isotonic calibrator on {len(X)} samples")
    
    def calibrate(self, predicted_probs: np.ndarray) -> np.ndarray:
        """
        Calibrate predicted draw probabilities.
        
        Args:
            predicted_probs: Array of predicted draw probabilities (0-1)
        
        Returns:
            Array of calibrated draw probabilities (0-1)
        """
        if not self.is_fitted:
            logger.warning("Calibrator not fitted, returning original probabilities")
            return predicted_probs
        
        # Ensure probabilities are in valid range
        predicted_probs = np.clip(predicted_probs, 0.0, 1.0)
        
        # Calibrate
        calibrated = self.model.predict(predicted_probs)
        
        # Ensure output is in valid range
        calibrated = np.clip(calibrated, 0.0, 1.0)
        
        return calibrated
    
    def calibrate_single(self, predicted_prob: float) -> float:
        """
        Calibrate a single predicted draw probability.
        
        Args:
            predicted_prob: Predicted draw probability (0-1)
        
        Returns:
            Calibrated draw probability (0-1)
        """
        return float(self.calibrate(np.array([predicted_prob]))[0])


def load_training_data_from_predictions(
    db: Session,
    model_id: Optional[int] = None,
    limit: int = 10000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load training data from predictions table.
    
    Args:
        db: Database session
        model_id: Optional model ID to filter by
        limit: Maximum number of samples
    
    Returns:
        Tuple of (predicted_probs, actual_outcomes)
    """
    query = text("""
        SELECT 
            p.prob_draw,
            CASE WHEN jf.actual_result = 'D' THEN 1 ELSE 0 END as is_draw
        FROM predictions p
        JOIN jackpot_fixtures jf ON jf.id = p.fixture_id
        WHERE jf.actual_result IS NOT NULL
          AND p.prob_draw IS NOT NULL
    """)
    
    if model_id:
        query = text("""
            SELECT 
                p.prob_draw,
                CASE WHEN jf.actual_result = 'D' THEN 1 ELSE 0 END as is_draw
            FROM predictions p
            JOIN jackpot_fixtures jf ON jf.id = p.fixture_id
            WHERE jf.actual_result IS NOT NULL
              AND p.prob_draw IS NOT NULL
              AND p.model_id = :model_id
        """)
        result = db.execute(query, {"model_id": model_id}).fetchall()
    else:
        result = db.execute(query).fetchall()
    
    if not result:
        logger.warning("No training data found")
        return np.array([]), np.array([])
    
    # Limit results
    result = result[:limit]
    
    predicted_probs = np.array([float(r.prob_draw) for r in result])
    actual_outcomes = np.array([int(r.is_draw) for r in result])
    
    return predicted_probs, actual_outcomes


def calculate_draw_brier_score(
    predicted_probs: np.ndarray,
    actual_outcomes: np.ndarray
) -> float:
    """
    Calculate Brier score for draw predictions.
    
    Args:
        predicted_probs: Array of predicted draw probabilities (0-1)
        actual_outcomes: Array of actual outcomes (1 for draw, 0 for not draw)
    
    Returns:
        Brier score (lower is better, 0 = perfect, 1 = worst)
    """
    if len(predicted_probs) != len(actual_outcomes):
        raise ValueError("Arrays must have same length")
    
    # Brier score = mean((predicted - actual)^2)
    brier = np.mean((predicted_probs - actual_outcomes) ** 2)
    
    return float(brier)


def calculate_draw_reliability_curve(
    predicted_probs: np.ndarray,
    actual_outcomes: np.ndarray,
    n_bins: int = 10
) -> List[Dict]:
    """
    Calculate reliability curve for draw predictions.
    
    Args:
        predicted_probs: Array of predicted draw probabilities (0-1)
        actual_outcomes: Array of actual outcomes (1 for draw, 0 for not draw)
        n_bins: Number of bins for calibration curve
    
    Returns:
        List of dicts with bin information
    """
    if len(predicted_probs) != len(actual_outcomes):
        raise ValueError("Arrays must have same length")
    
    # Create bins
    bin_edges = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(predicted_probs, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    curve = []
    
    for i in range(n_bins):
        mask = bin_indices == i
        if mask.sum() == 0:
            continue
        
        bin_predicted = predicted_probs[mask]
        bin_actual = actual_outcomes[mask]
        
        mean_predicted = float(np.mean(bin_predicted))
        mean_actual = float(np.mean(bin_actual))
        count = int(mask.sum())
        
        curve.append({
            "predicted_prob": mean_predicted,
            "observed_frequency": mean_actual,
            "sample_count": count,
            "bin_low": float(bin_edges[i]),
            "bin_high": float(bin_edges[i + 1])
        })
    
    return curve


def train_draw_calibrator(
    db: Session,
    model_id: Optional[int] = None
) -> DrawIsotonicCalibrator:
    """
    Train draw isotonic calibrator on historical predictions.
    
    Args:
        db: Database session
        model_id: Optional model ID to filter by
    
    Returns:
        Trained calibrator
    """
    calibrator = DrawIsotonicCalibrator()
    
    predicted_probs, actual_outcomes = load_training_data_from_predictions(
        db, model_id
    )
    
    if len(predicted_probs) == 0:
        logger.warning("No training data available, returning unfitted calibrator")
        return calibrator
    
    calibrator.fit(predicted_probs, actual_outcomes)
    
    return calibrator

