"""
Fixture Correlation Scoring

Computes correlation scores between fixtures to identify which matches
are likely to fail together. Used for portfolio diversification in ticket generation.

Correlation factors:
- Same league (teams know each other, similar styles)
- Kickoff window (same time = similar conditions, news impact)
- Odds shape (similar market expectations)
- Draw regime (similar draw likelihood)
- Total goals (similar expected goal totals)
"""

from typing import Dict, List
from app.services.league_corr_weights import get_corr_weights
import logging

logger = logging.getLogger(__name__)


def fixture_correlation(
    f1: Dict,
    f2: Dict,
    weights: Dict[str, float] = None
) -> float:
    """
    Compute correlation score between two fixtures.
    
    Returns value in [0.0, 1.0] where:
    - 0.0 = completely independent
    - 1.0 = highly correlated (likely to fail together)
    
    Args:
        f1: First fixture dict with keys:
            - league_id: League ID
            - kickoff_ts: Kickoff timestamp (Unix seconds)
            - odds: Dict with 'home', 'draw', 'away' keys
            - draw_signal: Draw signal [0.0, 1.0]
            - lambda_total: Total expected goals
        f2: Second fixture dict (same structure)
        weights: Optional custom weights dict (if None, uses defaults)
        
    Returns:
        Correlation score [0.0, 1.0]
        
    Example:
        >>> f1 = {
        ...     "league_id": 1,
        ...     "kickoff_ts": 1704067200,
        ...     "odds": {"home": 2.0, "draw": 3.0, "away": 2.5},
        ...     "draw_signal": 0.6,
        ...     "lambda_total": 2.5
        ... }
        >>> f2 = {
        ...     "league_id": 1,
        ...     "kickoff_ts": 1704067200 + 3600,  # 1 hour later
        ...     "odds": {"home": 2.1, "draw": 3.1, "away": 2.4},
        ...     "draw_signal": 0.65,
        ...     "lambda_total": 2.6
        ... }
        >>> corr = fixture_correlation(f1, f2)
        >>> corr > 0.5  # Should be moderately correlated
        True
    """
    if weights is None:
        weights = {
            "same_league": 0.25,
            "kickoff_window": 0.20,
            "odds_shape": 0.35,
            "draw_regime": 0.20,
            "total_goals": 0.15
        }
    
    score = 0.0
    
    # Factor 1: Same league
    if f1.get("league_id") == f2.get("league_id"):
        score += weights.get("same_league", 0.25)
    
    # Factor 2: Kickoff window (±90 minutes)
    kickoff1 = f1.get("kickoff_ts", 0)
    kickoff2 = f2.get("kickoff_ts", 0)
    if kickoff1 > 0 and kickoff2 > 0:
        time_diff_seconds = abs(kickoff1 - kickoff2)
        if time_diff_seconds <= 90 * 60:  # 90 minutes in seconds
            score += weights.get("kickoff_window", 0.20)
    
    # Factor 3: Odds shape similarity
    def odds_shape(f):
        """Extract odds shape features."""
        o = f.get("odds", {})
        home = o.get("home", 2.0)
        away = o.get("away", 2.0)
        draw = o.get("draw", 3.0)
        
        # Home-away spread (how balanced)
        ha_spread = abs(home - away)
        
        # Draw relative to favorites (how draw-friendly)
        fav_odds = min(home, away)
        draw_relative = abs(draw - fav_odds)
        
        return ha_spread, draw_relative
    
    s1 = odds_shape(f1)
    s2 = odds_shape(f2)
    
    # Similar home-away spread
    if abs(s1[0] - s2[0]) < 0.25:
        score += weights.get("odds_shape", 0.35) * 0.5
    
    # Similar draw positioning
    if abs(s1[1] - s2[1]) < 0.25:
        score += weights.get("odds_shape", 0.35) * 0.5
    
    # Factor 4: Draw regime similarity
    draw_signal1 = f1.get("draw_signal", 0.5)
    draw_signal2 = f2.get("draw_signal", 0.5)
    if abs(draw_signal1 - draw_signal2) < 0.15:
        score += weights.get("draw_regime", 0.20)
    
    # Factor 5: Total goals similarity (lambda_total)
    lambda_total1 = f1.get("lambda_total", 2.5)
    lambda_total2 = f2.get("lambda_total", 2.5)
    if abs(lambda_total1 - lambda_total2) < 0.5:
        score += weights.get("total_goals", 0.15)
    
    # Clamp to [0.0, 1.0]
    return min(max(score, 0.0), 1.0)


def build_correlation_matrix(
    fixtures: List[Dict],
    league_code: str = "DEFAULT"
) -> List[List[float]]:
    """
    Build correlation matrix for all fixture pairs.
    
    Args:
        fixtures: List of fixture dicts (each with league_id, kickoff_ts, odds, draw_signal, lambda_total)
        league_code: League code for weight lookup (e.g., 'E0', 'SP1')
        
    Returns:
        N×N matrix where matrix[i][j] = correlation(fixtures[i], fixtures[j])
        Diagonal elements are 1.0 (self-correlation)
        
    Example:
        >>> fixtures = [f1, f2, f3]
        >>> matrix = build_correlation_matrix(fixtures, "E0")
        >>> len(matrix) == 3
        True
        >>> matrix[0][0] == 1.0  # Self-correlation
        True
        >>> matrix[0][1] == matrix[1][0]  # Symmetric
        True
    """
    n = len(fixtures)
    if n == 0:
        return []
    
    weights = get_corr_weights(league_code)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0  # Self-correlation
            else:
                matrix[i][j] = fixture_correlation(fixtures[i], fixtures[j], weights)
    
    return matrix


def get_highly_correlated_pairs(
    fixtures: List[Dict],
    correlation_matrix: List[List[float]],
    threshold: float = 0.7
) -> List[tuple]:
    """
    Get pairs of fixtures with correlation above threshold.
    
    Args:
        fixtures: List of fixture dicts
        correlation_matrix: Correlation matrix from build_correlation_matrix()
        threshold: Correlation threshold (default 0.7)
        
    Returns:
        List of (i, j, correlation_score) tuples where correlation > threshold
    """
    pairs = []
    n = len(fixtures)
    
    for i in range(n):
        for j in range(i + 1, n):
            corr = correlation_matrix[i][j]
            if corr > threshold:
                pairs.append((i, j, corr))
    
    return pairs

