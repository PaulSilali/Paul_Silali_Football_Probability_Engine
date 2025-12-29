"""
Isotonic Regression for Probability Calibration

Maps predicted probabilities → calibrated probabilities
to ensure P(outcome | prediction=p) ≈ p
"""
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve


@dataclass
class CalibrationCurve:
    """Calibration curve data"""
    outcome: str  # 'H', 'D', or 'A'
    predicted_buckets: List[float]  # [0.0, 0.1, 0.2, ..., 1.0]
    observed_frequencies: List[float]  # Actual frequencies in each bucket
    sample_counts: List[int]  # Number of samples in each bucket


class Calibrator:
    """Isotonic regression calibrator for match outcomes"""
    
    def __init__(self):
        self.calibrators = {
            'H': IsotonicRegression(out_of_bounds='clip'),
            'D': IsotonicRegression(out_of_bounds='clip'),
            'A': IsotonicRegression(out_of_bounds='clip')
        }
        self.is_fitted = False
    
    def fit(
        self,
        predictions: List[float],
        actuals: List[int],
        outcome_type: str
    ) -> None:
        """
        Fit isotonic regression from historical data
        
        Args:
            predictions: List of predicted probabilities
            actuals: List of 0/1 (outcome occurred or not)
            outcome_type: 'H', 'D', or 'A'
        """
        if outcome_type not in self.calibrators:
            raise ValueError(f"Invalid outcome type: {outcome_type}")
        
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")
        
        # Filter out invalid predictions
        valid_mask = np.array([0 <= p <= 1 for p in predictions])
        pred_array = np.array(predictions)[valid_mask]
        act_array = np.array(actuals)[valid_mask]
        
        if len(pred_array) < 10:
            # Not enough data to calibrate
            return
        
        # Fit isotonic regression
        self.calibrators[outcome_type].fit(pred_array, act_array)
        self.is_fitted = True
    
    def calibrate(
        self,
        raw_probability: float,
        outcome_type: str
    ) -> float:
        """
        Apply calibration to a new prediction
        
        Args:
            raw_probability: Raw predicted probability
            outcome_type: 'H', 'D', or 'A'
        
        Returns:
            Calibrated probability
        """
        if outcome_type not in self.calibrators:
            return raw_probability
        
        if not self.is_fitted:
            return raw_probability
        
        # Clip to valid range
        raw_probability = max(0.0, min(1.0, raw_probability))
        
        # Apply calibration
        calibrated = self.calibrators[outcome_type].predict([raw_probability])[0]
        
        # Ensure valid range
        return max(0.0, min(1.0, calibrated))
    
    def calibrate_probabilities(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float
    ) -> Tuple[float, float, float]:
        """
        Calibrate all three outcome probabilities
        
        Returns:
            Tuple of (calibrated_home, calibrated_draw, calibrated_away)
        """
        cal_home = self.calibrate(home_prob, 'H')
        cal_draw = self.calibrate(draw_prob, 'D')
        cal_away = self.calibrate(away_prob, 'A')
        
        # Renormalize to ensure they sum to 1.0
        total = cal_home + cal_draw + cal_away
        if total > 0:
            cal_home /= total
            cal_draw /= total
            cal_away /= total
        
        return cal_home, cal_draw, cal_away


def compute_calibration_curve(
    predictions: List[float],
    actuals: List[int],
    n_bins: int = 10
) -> CalibrationCurve:
    """
    Compute calibration curve from predictions and actuals
    
    Args:
        predictions: List of predicted probabilities
        actuals: List of 0/1 (outcome occurred or not)
        n_bins: Number of bins for calibration curve
    
    Returns:
        CalibrationCurve with buckets and observed frequencies
    """
    if len(predictions) != len(actuals):
        raise ValueError("Predictions and actuals must have same length")
    
    # Filter valid predictions
    valid_mask = np.array([0 <= p <= 1 for p in predictions])
    pred_array = np.array(predictions)[valid_mask]
    act_array = np.array(actuals)[valid_mask]
    
    if len(pred_array) == 0:
        return CalibrationCurve(
            outcome='',
            predicted_buckets=[],
            observed_frequencies=[],
            sample_counts=[]
        )
    
    # Compute calibration curve using sklearn
    fraction_of_positives, mean_predicted_value = calibration_curve(
        act_array, pred_array, n_bins=n_bins, strategy='uniform'
    )
    
    # Calculate sample counts per bin
    bin_edges = np.linspace(0, 1, n_bins + 1)
    sample_counts = []
    for i in range(n_bins):
        mask = (pred_array >= bin_edges[i]) & (pred_array < bin_edges[i + 1])
        if i == n_bins - 1:  # Include upper bound for last bin
            mask = (pred_array >= bin_edges[i]) & (pred_array <= bin_edges[i + 1])
        sample_counts.append(int(np.sum(mask)))
    
    return CalibrationCurve(
        outcome='',
        predicted_buckets=mean_predicted_value.tolist(),
        observed_frequencies=fraction_of_positives.tolist(),
        sample_counts=sample_counts
    )


def calculate_brier_score(
    predictions: List[float],
    actuals: List[int]
) -> float:
    """
    Calculate Brier score
    
    Brier Score = (1/N) * Σ (p_pred - y_actual)²
    
    Lower is better (perfect = 0.0)
    """
    if len(predictions) != len(actuals):
        raise ValueError("Predictions and actuals must have same length")
    
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    
    # Filter valid predictions
    valid_mask = (predictions >= 0) & (predictions <= 1)
    predictions = predictions[valid_mask]
    actuals = actuals[valid_mask]
    
    if len(predictions) == 0:
        return 1.0  # Worst possible score
    
    brier = np.mean((predictions - actuals) ** 2)
    return float(brier)


def calculate_log_loss(
    predictions: List[float],
    actuals: List[int],
    epsilon: float = 1e-15
) -> float:
    """
    Calculate log loss (cross-entropy)
    
    Log Loss = -(1/N) * Σ [y*log(p) + (1-y)*log(1-p)]
    
    Lower is better
    """
    if len(predictions) != len(actuals):
        raise ValueError("Predictions and actuals must have same length")
    
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    
    # Clip predictions to avoid log(0)
    predictions = np.clip(predictions, epsilon, 1 - epsilon)
    
    # Filter valid predictions
    valid_mask = (predictions >= epsilon) & (predictions <= 1 - epsilon)
    predictions = predictions[valid_mask]
    actuals = actuals[valid_mask]
    
    if len(predictions) == 0:
        return float('inf')
    
    log_loss = -np.mean(
        actuals * np.log(predictions) + (1 - actuals) * np.log(1 - predictions)
    )
    return float(log_loss)

