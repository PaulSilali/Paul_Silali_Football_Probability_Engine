"""
Temperature Optimizer

Learns optimal temperature parameter during training to minimize Log Loss
on validation data.

This is NOT ML, not gradient descent, not neural calibration.
It is a controlled post-hoc uncertainty fit on a validation slice.

OBJECTIVE: Minimize Log Loss by controlling overconfidence.

Guarantees:
- Temperature ≥ 1.0 (never sharpen probabilities)
- Learned on held-out validation only
- One scalar per model version
- Stored, auditable, optional to override
"""
import math
from typing import List, Tuple
from app.models.uncertainty import temperature_scale

EPS = 1e-12


def log_loss(
    probs: Tuple[float, float, float],
    actual: Tuple[int, int, int]
) -> float:
    """
    Compute log loss (cross-entropy) for a single prediction.
    
    Args:
        probs: Predicted probabilities (home, draw, away)
        actual: Actual outcome (one-hot: [1,0,0] for home, [0,1,0] for draw, [0,0,1] for away)
    
    Returns:
        Log loss value
    """
    return -(
        actual[0] * math.log(max(probs[0], EPS)) +
        actual[1] * math.log(max(probs[1], EPS)) +
        actual[2] * math.log(max(probs[2], EPS))
    )


def learn_temperature(
    predictions: List[Tuple[float, float, float]],
    actuals: List[Tuple[int, int, int]],
    candidates: List[float] = None
) -> dict:
    """
    Learn optimal temperature on validation set ONLY.
    
    This is a grid search over candidate temperatures to find
    the value that minimizes average log loss.
    
    Args:
        predictions: List of predicted probability tuples (home, draw, away)
        actuals: List of actual outcome tuples (one-hot encoded)
        candidates: List of temperature candidates to try (default: 1.00 to 1.40)
    
    Returns:
        Dictionary with:
            - temperature: Optimal temperature (rounded to 3 decimals)
            - logLoss: Log loss at optimal temperature (rounded to 5 decimals)
    
    Safety Constraints:
        - Temperature is clamped to [1.0, 1.5]
        - Never sharpens probabilities (T < 1.0 is forbidden)
    """
    if not predictions or not actuals:
        return {"temperature": 1.0, "logLoss": None}
    
    if len(predictions) != len(actuals):
        raise ValueError("predictions and actuals must have same length")
    
    if candidates is None:
        candidates = [
            1.00, 1.05, 1.10, 1.15, 1.20,
            1.25, 1.30, 1.35, 1.40
        ]
    
    best_t = 1.0
    best_loss = float("inf")
    
    for t in candidates:
        total_loss = 0.0
        count = 0
        
        for probs, actual in zip(predictions, actuals):
            scaled = temperature_scale(probs, t)
            total_loss += log_loss(scaled, actual)
            count += 1
        
        if count == 0:
            continue
        
        avg_loss = total_loss / count
        
        if avg_loss < best_loss:
            best_loss = avg_loss
            best_t = t
    
    # HARD SAFETY CONSTRAINTS
    if best_t < 1.0:
        best_t = 1.0
    if best_t > 1.5:
        best_t = 1.5
    
    return {
        "temperature": round(best_t, 3),
        "logLoss": round(best_loss, 5)
    }

