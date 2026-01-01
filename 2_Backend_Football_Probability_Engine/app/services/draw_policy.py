"""
Draw Eligibility Policy

Determines when Draw (X) is allowed in ticket construction based on:
- Predicted draw probability
- Entropy (uncertainty)
- H2H historical draw tendency

IMPORTANT: This does NOT modify probabilities. It only determines eligibility.
"""
from typing import Optional, Dict
from datetime import datetime
from app.models.uncertainty import normalized_entropy


def h2h_draw_eligible(
    predicted_draw: float,
    entropy: float,
    h2h: Optional[Dict] = None
) -> bool:
    """
    Determine if Draw is eligible for ticket construction.
    
    Args:
        predicted_draw: Predicted draw probability (0.0-1.0)
        entropy: Normalized entropy of probability distribution (0.0-1.0)
        h2h: Optional H2H statistics dict
        
    Returns:
        True if draw is eligible, False otherwise
    """
    # Base probability gate - draw must be at least 28%
    if predicted_draw < 0.28:
        return False
    
    # Entropy gate - must have high uncertainty (85%+)
    if entropy < 0.85:
        return False
    
    # No H2H data - still allowed if entropy and probability gates pass
    if not h2h:
        return True
    
    # H2H safety rules
    if h2h.get("meetings", 0) < 8:
        return True  # Not enough data, use entropy/probability only
    
    last_year = h2h.get("last_meeting_year", 0)
    current_year = datetime.now().year
    if last_year and (current_year - last_year) > 5:
        return True  # Data too old, use entropy/probability only
    
    # H2H draw tendency check
    h2h_draw_index = h2h.get("h2h_draw_index", 1.0)
    if h2h_draw_index >= 1.15:  # 15% above league average
        return True
    
    # If draw is the highest probability, always allow
    # (This check should be done at ticket generation level)
    
    return False


def get_draw_rank(
    home_prob: float,
    draw_prob: float,
    away_prob: float
) -> int:
    """
    Get the rank of draw probability (1 = highest, 2 = second, 3 = lowest).
    """
    probs = [
        ("home", home_prob),
        ("draw", draw_prob),
        ("away", away_prob)
    ]
    probs.sort(key=lambda x: x[1], reverse=True)
    
    for idx, (outcome, _) in enumerate(probs):
        if outcome == "draw":
            return idx + 1
    
    return 3

