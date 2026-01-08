"""
Team Strength Adjustments

Applies rest days, form, and injuries to adjust team strengths before probability calculation.
"""
from typing import Optional, Tuple
from datetime import date
import logging
import math

logger = logging.getLogger(__name__)


def adjust_strength_for_rest_days(
    base_attack: float,
    base_defense: float,
    rest_days: Optional[int],
    is_home: bool = True
) -> Tuple[float, float]:
    """
    Adjust team strength based on rest days.
    
    Research shows:
    - Teams with < 3 days rest perform worse
    - Teams with 3-4 days rest are optimal
    - Teams with > 7 days rest may be rusty
    
    Args:
        base_attack: Base attack strength
        base_defense: Base defense strength
        rest_days: Number of rest days (None = use default)
        is_home: Whether team is playing at home
    
    Returns:
        Tuple of (adjusted_attack, adjusted_defense)
    """
    if rest_days is None:
        rest_days = 7  # Default
    
    # Rest day adjustment factors
    # Optimal: 3-4 days rest
    if rest_days >= 3 and rest_days <= 4:
        # Optimal rest - slight boost
        adjustment = 1.02
    elif rest_days == 2:
        # Short rest - slight penalty
        adjustment = 0.96
    elif rest_days == 1:
        # Very short rest - larger penalty
        adjustment = 0.92
    elif rest_days == 0:
        # No rest (back-to-back) - significant penalty
        adjustment = 0.88
    elif rest_days >= 5 and rest_days <= 7:
        # Good rest - neutral
        adjustment = 1.0
    elif rest_days > 7:
        # Too much rest - slight penalty (rust)
        adjustment = 0.98
    else:
        # Fallback
        adjustment = 1.0
    
    # Home teams benefit more from rest
    if is_home:
        adjustment *= 1.01
    
    # Clamp to reasonable range
    adjustment = max(0.85, min(1.05, adjustment))
    
    adjusted_attack = base_attack * adjustment
    adjusted_defense = base_defense * adjustment
    
    return adjusted_attack, adjusted_defense


def adjust_strength_for_injuries(
    base_attack: float,
    base_defense: float,
    key_players_missing: Optional[int] = None,
    injury_severity: Optional[float] = None  # 0.0-1.0, where 1.0 = critical players missing
) -> Tuple[float, float]:
    """
    Adjust team strength based on injuries.
    
    Args:
        base_attack: Base attack strength
        base_defense: Base defense strength
        key_players_missing: Number of key players missing (None = no data)
        injury_severity: Overall injury severity (0.0-1.0, None = no data)
    
    Returns:
        Tuple of (adjusted_attack, adjusted_defense)
    """
    if key_players_missing is None and injury_severity is None:
        return base_attack, base_defense
    
    # Calculate adjustment based on injuries
    if injury_severity is not None:
        # Use severity directly
        adjustment = 1.0 - (injury_severity * 0.15)  # Max 15% reduction
    elif key_players_missing is not None:
        # Estimate from number of key players missing
        # Assume each key player missing = ~3% reduction
        adjustment = 1.0 - (key_players_missing * 0.03)
        adjustment = max(0.85, adjustment)  # Cap at 15% reduction
    else:
        adjustment = 1.0
    
    # Attack affected more by attacking player injuries
    # Defense affected more by defensive player injuries
    # For now, apply equally (can be refined with position-specific data)
    attack_adjustment = adjustment
    defense_adjustment = adjustment
    
    adjusted_attack = base_attack * attack_adjustment
    adjusted_defense = base_defense * defense_adjustment
    
    return adjusted_attack, adjusted_defense


def apply_all_adjustments(
    base_attack: float,
    base_defense: float,
    rest_days: Optional[int] = None,
    is_home: bool = True,
    form_attack_adjustment: Optional[float] = None,  # Pre-calculated form adjustment
    form_defense_adjustment: Optional[float] = None,
    key_players_missing: Optional[int] = None,
    injury_severity: Optional[float] = None
) -> Tuple[float, float]:
    """
    Apply all adjustments to team strength.
    
    Order of application:
    1. Form adjustments
    2. Rest days adjustments
    3. Injury adjustments
    
    Args:
        base_attack: Base attack strength from model
        base_defense: Base defense strength from model
        rest_days: Rest days before match
        is_home: Whether playing at home
        form_attack_adjustment: Form-based attack multiplier (None = no adjustment)
        form_defense_adjustment: Form-based defense multiplier (None = no adjustment)
        key_players_missing: Number of key players missing
        injury_severity: Injury severity (0.0-1.0)
    
    Returns:
        Tuple of (final_attack, final_defense)
    """
    attack = base_attack
    defense = base_defense
    
    # 1. Apply form adjustments
    if form_attack_adjustment is not None:
        attack *= form_attack_adjustment
    if form_defense_adjustment is not None:
        defense *= form_defense_adjustment
    
    # 2. Apply rest days adjustments
    attack, defense = adjust_strength_for_rest_days(attack, defense, rest_days, is_home)
    
    # 3. Apply injury adjustments
    attack, defense = adjust_strength_for_injuries(attack, defense, key_players_missing, injury_severity)
    
    # Final clamp to prevent extreme values
    attack = max(0.5, min(2.0, attack))
    defense = max(0.5, min(2.0, defense))
    
    return attack, defense

