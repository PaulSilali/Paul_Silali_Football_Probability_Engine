"""
Ticket Role Constraints

Defines hard behavioral constraints for each probability set (A-G).
These are NOT probability variations, but behavioral roles that enforce
different failure modes to maximize portfolio survival.

Each role has:
- min_draws / max_draws: Draw count constraints
- max_favorites: Maximum number of strong favorites (prob >= 0.65)
- min_underdogs: Minimum number of underdogs (prob < 0.65)
- entropy_range: Target entropy range for the ticket
"""
import logging

logger = logging.getLogger(__name__)

TICKET_ROLE_CONSTRAINTS = {
    "A": {
        "min_draws": 0,
        "max_draws": 3,
        "max_favorites": None,  # No limit
        "min_underdogs": 0,
        "entropy_range": (0.65, 0.75),
        "description": "Model truth - Pure model probabilities, low entropy, minimal draws"
    },
    "B": {
        "min_draws": 5,
        "max_draws": 8,
        "max_favorites": 6,
        "min_underdogs": 0,
        "entropy_range": (0.75, 0.85),
        "description": "Draw-heavy - Draw-focused, higher entropy, balanced favorites"
    },
    "C": {
        "min_draws": 2,
        "max_draws": 5,
        "max_favorites": None,  # No limit
        "min_underdogs": 0,
        "entropy_range": (0.70, 0.80),
        "description": "Market-aligned - Market-informed probabilities, moderate entropy"
    },
    "D": {
        "min_draws": 2,
        "max_draws": 5,
        "max_favorites": 5,
        "min_underdogs": 3,
        "entropy_range": (0.78, 0.88),
        "description": "Underdog hedge - Underdog-focused, high entropy, hedges favorites"
    },
    "E": {
        "min_draws": 3,
        "max_draws": 6,
        "max_favorites": 6,
        "min_underdogs": 2,
        "entropy_range": (0.80, 0.85),
        "description": "Entropy-balanced - Balanced entropy target, moderate draws"
    },
    "F": {
        "min_draws": 3,
        "max_draws": 6,
        "max_favorites": 6,
        "min_underdogs": 1,
        "entropy_range": (0.75, 0.85),
        "description": "Late shock - Reacts to late odds movement, hedges surprises"
    },
    "G": {
        "min_draws": 2,
        "max_draws": 5,
        "max_favorites": 4,
        "min_underdogs": 4,
        "entropy_range": (0.80, 0.90),
        "description": "Anti-favorite hedge - Hedges against strong favorites, high entropy"
    },
    "H": {
        "min_draws": 4,
        "max_draws": 7,
        "max_favorites": 7,
        "min_underdogs": 0,
        "entropy_range": (0.75, 0.85),
        "description": "Market consensus draw - Market-informed draw coverage, balanced"
    },
    "I": {
        "min_draws": 3,
        "max_draws": 6,
        "max_favorites": 6,
        "min_underdogs": 1,
        "entropy_range": (0.78, 0.88),
        "description": "Formula-based draw - Balanced draw optimization, entropy/spread-based"
    },
    "J": {
        "min_draws": 4,
        "max_draws": 8,
        "max_favorites": 6,
        "min_underdogs": 2,
        "entropy_range": (0.80, 0.90),
        "description": "System-selected draw - Adaptive intelligent draw strategy, maximum coverage"
    }
}


def get_role_constraints(set_key: str) -> dict:
    """
    Get constraints for a specific ticket role.
    
    Args:
        set_key: Probability set key ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J')
        
    Returns:
        Dictionary with constraint values
        
    Raises:
        KeyError: If set_key is not in TICKET_ROLE_CONSTRAINTS
    """
    if set_key not in TICKET_ROLE_CONSTRAINTS:
        raise KeyError(f"Unknown set_key: {set_key}. Must be one of {list(TICKET_ROLE_CONSTRAINTS.keys())}")
    
    return TICKET_ROLE_CONSTRAINTS[set_key].copy()


def validate_constraints(
    picks: List[str],
    probs: Dict[str, Dict[str, float]],
    constraints: dict
) -> tuple[bool, List[str]]:
    """
    Validate that picks meet role constraints.
    
    Args:
        picks: List of picks ('1', 'X', '2')
        probs: Dict mapping fixture index (str) to probability dict {'1': float, 'X': float, '2': float}
        constraints: Constraint dict from get_role_constraints()
        
    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    
    # Count draws
    draw_count = picks.count("X")
    
    # Count favorites and underdogs
    fav_count = 0
    dog_count = 0
    
    for i, pick in enumerate(picks):
        fixture_probs = probs.get(str(i + 1), {})
        if not fixture_probs:
            continue
        
        max_prob = max(fixture_probs.values())
        if max_prob >= 0.65:
            fav_count += 1
        else:
            dog_count += 1
    
    # Check draw constraints
    if constraints["min_draws"] is not None and draw_count < constraints["min_draws"]:
        violations.append(f"Draw count {draw_count} < min_draws {constraints['min_draws']}")
    
    if constraints["max_draws"] is not None and draw_count > constraints["max_draws"]:
        violations.append(f"Draw count {draw_count} > max_draws {constraints['max_draws']}")
    
    # Check favorite constraints
    if constraints["max_favorites"] is not None and fav_count > constraints["max_favorites"]:
        violations.append(f"Favorite count {fav_count} > max_favorites {constraints['max_favorites']}")
    
    # Check underdog constraints
    if constraints["min_underdogs"] is not None and dog_count < constraints["min_underdogs"]:
        violations.append(f"Underdog count {dog_count} < min_underdogs {constraints['min_underdogs']}")
    
    # Check entropy (if probs available)
    try:
        from app.models.uncertainty import normalized_entropy
        
        ticket_probs = [
            probs.get(str(i + 1), {}).get(picks[i], 0.33)
            for i in range(len(picks))
        ]
        entropy = normalized_entropy(ticket_probs)
        
        min_entropy, max_entropy = constraints["entropy_range"]
        if entropy < min_entropy:
            violations.append(f"Entropy {entropy:.3f} < min {min_entropy}")
        elif entropy > max_entropy:
            violations.append(f"Entropy {entropy:.3f} > max {max_entropy}")
    except Exception as e:
        logger.warning(f"Could not validate entropy: {e}")
    
    return len(violations) == 0, violations

