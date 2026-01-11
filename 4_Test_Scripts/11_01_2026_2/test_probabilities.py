"""
Probability & Model Tests
=========================

Tests for probability calculation correctness, xG confidence propagation,
and Dixon-Coles conditional gating.
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

from app.models.dixon_coles import MatchProbabilities, calculate_match_probabilities
from app.models.dixon_coles_gate import should_apply_dc


def test_xg_confidence_calculation():
    """Test that xG confidence is calculated correctly and is monotonic."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    
    # Balanced match (high confidence)
    home_team1 = TeamStrength(team_id=1, attack=1.2, defense=1.0)
    away_team1 = TeamStrength(team_id=2, attack=1.1, defense=1.0)
    result1 = calculate_match_probabilities(home_team1, away_team1, params)
    
    # Unbalanced match (low confidence)
    home_team2 = TeamStrength(team_id=3, attack=2.0, defense=0.8)
    away_team2 = TeamStrength(team_id=4, attack=0.5, defense=1.2)
    result2 = calculate_match_probabilities(home_team2, away_team2, params)
    
    assert result1.xg_confidence is not None
    assert result2.xg_confidence is not None
    assert 0.0 <= result1.xg_confidence <= 1.0
    assert 0.0 <= result2.xg_confidence <= 1.0
    # Balanced match should have higher confidence
    assert result1.xg_confidence > result2.xg_confidence


def test_xg_confidence_bounds():
    """Test that xG confidence is always within valid bounds."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    
    # Test various scenarios
    scenarios = [
        (1.0, 1.0, 1.0, 1.0),  # Perfect balance
        (2.0, 0.8, 0.5, 1.2),  # Very unbalanced
        (1.5, 1.0, 1.5, 1.0),  # High scoring balanced
        (0.8, 1.0, 0.9, 1.0),  # Low scoring balanced
    ]
    
    for attack_home, defense_home, attack_away, defense_away in scenarios:
        home_team = TeamStrength(team_id=1, attack=attack_home, defense=defense_home)
        away_team = TeamStrength(team_id=2, attack=attack_away, defense=defense_away)
        result = calculate_match_probabilities(home_team, away_team, params)
        
        # Check confidence bounds
        if result.xg_confidence is not None:
            assert 0.0 <= result.xg_confidence <= 1.0


def test_dc_gating_low_score():
    """Test Dixon-Coles gating for low-scoring matches."""
    # Low total xG (< 2.4) with stable lineup -> should apply
    assert should_apply_dc(1.1, 1.0, lineup_stable=True) is True
    assert should_apply_dc(1.2, 1.1, lineup_stable=True) is True
    
    # Low total xG but unstable lineup -> should NOT apply
    assert should_apply_dc(1.1, 1.0, lineup_stable=False) is False


def test_dc_gating_high_score():
    """Test Dixon-Coles gating for high-scoring matches."""
    # High total xG (>= 2.4) -> should NOT apply even with stable lineup
    assert should_apply_dc(2.0, 1.8, lineup_stable=True) is False
    assert should_apply_dc(1.5, 1.0, lineup_stable=True) is False  # Total = 2.5


def test_dc_applied_flag_propagation():
    """Test that dc_applied flag is set correctly in MatchProbabilities."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    
    # Low xG scenario (should apply DC)
    home_team = TeamStrength(team_id=1, attack=1.0, defense=1.0)
    away_team = TeamStrength(team_id=2, attack=0.9, defense=1.0)
    result = calculate_match_probabilities(home_team, away_team, params)
    
    # Check that dc_applied is a boolean
    assert isinstance(result.dc_applied, bool)


def test_probability_sum_constraint():
    """Test that probabilities sum to 1.0 (within tolerance)."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    home_team = TeamStrength(team_id=1, attack=1.2, defense=1.0)
    away_team = TeamStrength(team_id=2, attack=1.1, defense=1.0)
    result = calculate_match_probabilities(home_team, away_team, params)
    
    total = result.home + result.draw + result.away
    assert abs(total - 1.0) < 0.001, f"Probabilities sum to {total}, not 1.0"


def test_probability_bounds():
    """Test that all probabilities are between 0 and 1."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    home_team = TeamStrength(team_id=1, attack=1.2, defense=1.0)
    away_team = TeamStrength(team_id=2, attack=1.1, defense=1.0)
    result = calculate_match_probabilities(home_team, away_team, params)
    
    assert 0.0 <= result.home <= 1.0
    assert 0.0 <= result.draw <= 1.0
    assert 0.0 <= result.away <= 1.0


def test_entropy_calculation():
    """Test that entropy is calculated and is non-negative."""
    from app.models.dixon_coles import (
        calculate_match_probabilities,
        TeamStrength,
        DixonColesParams
    )
    
    params = DixonColesParams(home_advantage=0.35)
    home_team = TeamStrength(team_id=1, attack=1.2, defense=1.0)
    away_team = TeamStrength(team_id=2, attack=1.1, defense=1.0)
    result = calculate_match_probabilities(home_team, away_team, params)
    
    assert result.entropy is not None
    assert result.entropy >= 0.0
    # Maximum entropy for 3 outcomes is log2(3) ≈ 1.585
    assert result.entropy <= 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

