"""
Isotonic Regression for Probability Calibration

IMPORTANT CONTRACT NOTICE
-------------------------
This module performs MARGINAL calibration only.

Each outcome (H / D / A) is calibrated independently using isotonic regression.
Post-calibration renormalization preserves the probability simplex
but DOES NOT guarantee joint calibration optimality.

This is a known and accepted tradeoff in multi-class probability calibration.
"""
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve


# -----------------------------
# Configuration (NON-NEGOTIABLE)
# -----------------------------

MIN_SAMPLES_PER_OUTCOME = {
    "H": 200,
    "D": 400,   # draws are rarer → need more data
    "A": 200,
}


@dataclass
class CalibrationCurve:
    """Calibration curve data"""
    outcome: str  # 'H', 'D', or 'A'
    predicted_buckets: List[float]  # [0.0, 0.1, 0.2, ..., 1.0]
    observed_frequencies: List[float]  # Actual frequencies in each bucket
    sample_counts: List[int]  # Number of samples in each bucket


@dataclass
class CalibrationMetadata:
    """Metadata about calibration fitting"""
    fitted: bool
    skipped_reason: str | None
    sample_count: int
    method: str = "isotonic_regression"
    calibration_scope: str = "marginal_only"


class Calibrator:
    """
    Outcome-wise isotonic calibrator.

    This calibrator is:
    - deterministic
    - monotonic
    - marginal-only
    """
    
    def __init__(self):
        self.calibrators = {
            "H": IsotonicRegression(out_of_bounds="clip"),
            "D": IsotonicRegression(out_of_bounds="clip"),
            "A": IsotonicRegression(out_of_bounds="clip"),
        }
        self.metadata: Dict[str, CalibrationMetadata] = {
            "H": CalibrationMetadata(False, "not_fitted", 0),
            "D": CalibrationMetadata(False, "not_fitted", 0),
            "A": CalibrationMetadata(False, "not_fitted", 0),
        }
    
    def fit(
        self,
        predictions: List[float],
        actuals: List[int],
        outcome_type: str,
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
        
        preds = np.array(predictions)
        acts = np.array(actuals)
        
        mask = (preds >= 0.0) & (preds <= 1.0)
        preds = preds[mask]
        acts = acts[mask]
        
        sample_count = len(preds)
        
        if sample_count < MIN_SAMPLES_PER_OUTCOME[outcome_type]:
            self.metadata[outcome_type] = CalibrationMetadata(
                fitted=False,
                skipped_reason=f"insufficient_samples_{sample_count}",
                sample_count=sample_count,
            )
            return
        
        self.calibrators[outcome_type].fit(preds, acts)
        self.metadata[outcome_type] = CalibrationMetadata(
            fitted=True,
            skipped_reason=None,
            sample_count=sample_count,
        )
    
    def calibrate(self, raw_probability: float, outcome_type: str) -> float:
        """
        Apply calibration to a new prediction
        
        Args:
            raw_probability: Raw predicted probability
            outcome_type: 'H', 'D', or 'A'
        
        Returns:
            Calibrated probability
        """
        meta = self.metadata.get(outcome_type)
        
        if meta is None or not meta.fitted:
            return raw_probability
        
        raw_probability = float(np.clip(raw_probability, 0.0, 1.0))
        calibrated = self.calibrators[outcome_type].predict([raw_probability])[0]
        
        return float(np.clip(calibrated, 0.0, 1.0))
    
    def fit_draw_only(
        self,
        predictions: List[float],
        actuals: List[int],
    ) -> None:
        """
        Fit isotonic regression for draw-only calibration.
        
        Args:
            predictions: List of predicted draw probabilities
            actuals: List of 0/1 (draw occurred or not)
        """
        self.fit(predictions, actuals, "D")
    
    def calibrate_probabilities(
        self,
        home: float,
        draw: float,
        away: float,
    ) -> Tuple[float, float, float]:
        """
        Applies marginal calibration, then renormalizes.

        WARNING:
        Renormalization preserves the simplex but does NOT
        guarantee joint calibration correctness.
        """
        ch = self.calibrate(home, "H")
        cd = self.calibrate(draw, "D")
        ca = self.calibrate(away, "A")
        
        total = ch + cd + ca
        if total > 0:
            ch /= total
            cd /= total
            ca /= total
        
        return ch, cd, ca


# --------------------------------------------------

def compute_calibration_curve(
    predictions: List[float],
    actuals: List[int],
    outcome: str,
    n_bins: int = 10,
) -> CalibrationCurve:
    """
    Compute calibration curve from predictions and actuals
    
    Args:
        predictions: List of predicted probabilities
        actuals: List of 0/1 (outcome occurred or not)
        outcome: Outcome label ('H', 'D', or 'A')
        n_bins: Number of bins for calibration curve
    
    Returns:
        CalibrationCurve with buckets and observed frequencies
    """
    if len(predictions) != len(actuals):
        raise ValueError("Predictions and actuals must have same length")
    
    preds = np.array(predictions)
    acts = np.array(actuals)
    
    mask = (preds >= 0.0) & (preds <= 1.0)
    preds = preds[mask]
    acts = acts[mask]
    
    if len(preds) == 0:
        return CalibrationCurve(outcome, [], [], [])
    
    frac_pos, mean_pred = calibration_curve(
        acts, preds, n_bins=n_bins, strategy="uniform"
    )
    
    bins = np.linspace(0, 1, n_bins + 1)
    counts = [
        int(((preds >= bins[i]) & (preds < bins[i + 1])).sum())
        for i in range(n_bins)
    ]
    
    return CalibrationCurve(
        outcome=outcome,
        predicted_buckets=mean_pred.tolist(),
        observed_frequencies=frac_pos.tolist(),
        sample_counts=counts,
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
