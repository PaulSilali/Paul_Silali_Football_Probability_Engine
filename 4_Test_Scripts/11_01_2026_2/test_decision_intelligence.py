"""
Decision Intelligence Core Tests
==================================

Tests for EV-weighted scoring, hard contradiction detection,
structural penalties, and threshold gating.
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

from app.decision_intelligence.contradictions import is_hard_contradiction
from app.decision_intelligence.ev_scoring import pick_decision_value, xg_confidence
from app.decision_intelligence.penalties import structural_penalty


def test_hard_contradiction_draw_with_high_home_prob():
    """Test that draw picks with high home probability are detected as contradictions."""
    match = {
        "pick": "X",
        "market_prob_home": 0.60,  # > 0.55 threshold
        "xg_home": 1.8,
        "xg_away": 0.6,
        "market_odds": {"home": 1.67, "draw": 3.6, "away": 5.0}
    }
    
    assert is_hard_contradiction(match) is True


def test_hard_contradiction_draw_with_high_xg_diff():
    """Test that draw picks with high xG difference are detected as contradictions."""
    match = {
        "pick": "X",
        "market_prob_home": 0.50,
        "xg_home": 2.0,
        "xg_away": 1.4,  # |diff| = 0.6 > 0.45 threshold
        "market_odds": {"home": 2.0, "draw": 3.2, "away": 3.5}
    }
    
    assert is_hard_contradiction(match) is True


def test_hard_contradiction_away_with_high_odds():
    """Test that away picks with high odds and high home prob are detected as contradictions."""
    match = {
        "pick": "2",
        "market_prob_home": 0.52,  # > 0.50 threshold
        "market_odds": {"home": 1.92, "draw": 3.4, "away": 3.5},  # away > 3.2
        "xg_home": 1.5,
        "xg_away": 1.2
    }
    
    assert is_hard_contradiction(match) is True


def test_no_contradiction_valid_draw():
    """Test that valid draw picks are not flagged as contradictions."""
    match = {
        "pick": "X",
        "market_prob_home": 0.45,  # < 0.55 threshold
        "xg_home": 1.2,
        "xg_away": 1.1,  # |diff| = 0.1 < 0.45 threshold
        "market_odds": {"home": 2.22, "draw": 3.2, "away": 3.2}
    }
    
    assert is_hard_contradiction(match) is False


def test_ev_weighted_scoring_monotonicity():
    """Test that EV score increases with confidence (monotonicity)."""
    # Same model prob and odds, different confidence
    high_conf = pick_decision_value(
        model_prob=0.55,
        market_odds=2.2,
        confidence=1.0,
        structural_penalty=0.0,
        is_hard_contradiction=False
    )
    
    low_conf = pick_decision_value(
        model_prob=0.55,
        market_odds=2.2,
        confidence=0.4,
        structural_penalty=0.0,
        is_hard_contradiction=False
    )
    
    assert high_conf > low_conf, "Higher confidence should yield higher EV score"


def test_ev_weighted_scoring_penalty_impact():
    """Test that structural penalties reduce EV score."""
    no_penalty = pick_decision_value(
        model_prob=0.55,
        market_odds=2.2,
        confidence=0.8,
        structural_penalty=0.0,
        is_hard_contradiction=False
    )
    
    with_penalty = pick_decision_value(
        model_prob=0.55,
        market_odds=2.2,
        confidence=0.8,
        structural_penalty=0.15,
        is_hard_contradiction=False
    )
    
    assert no_penalty > with_penalty, "Penalty should reduce EV score"


def test_ev_weighted_scoring_contradiction_blocks():
    """Test that hard contradictions result in negative infinity EV."""
    contradiction_ev = pick_decision_value(
        model_prob=0.55,
        market_odds=2.2,
        confidence=0.8,
        structural_penalty=0.0,
        is_hard_contradiction=True
    )
    
    assert contradiction_ev == float('-inf'), "Hard contradictions should block with -inf EV"


def test_structural_penalty_high_draw_odds():
    """Test that draw picks with high odds (> 3.4) get penalty."""
    match = {
        "pick": "X",
        "market_odds": {"home": 2.0, "draw": 3.6, "away": 3.5},  # draw > 3.4
        "xg_home": 1.2,
        "xg_away": 1.1
    }
    
    penalty = structural_penalty(match)
    assert penalty >= 0.15, "High-odds draw should get penalty"


def test_structural_penalty_draw_high_xg_diff():
    """Test that draw picks with high xG difference get penalty."""
    match = {
        "pick": "X",
        "market_odds": {"home": 2.0, "draw": 3.2, "away": 3.5},
        "xg_home": 2.0,
        "xg_away": 1.4  # |diff| = 0.6 > 0.45
    }
    
    penalty = structural_penalty(match)
    assert penalty >= 0.20, "High xG diff draw should get penalty"


def test_structural_penalty_away_high_odds():
    """Test that away picks with high odds (> 3.2) get penalty."""
    match = {
        "pick": "2",
        "market_odds": {"home": 1.8, "draw": 3.4, "away": 3.5},  # away > 3.2
        "xg_home": 1.5,
        "xg_away": 1.2
    }
    
    penalty = structural_penalty(match)
    assert penalty >= 0.10, "High-odds away should get penalty"


def test_structural_penalty_no_penalty_valid_pick():
    """Test that valid picks get no penalty."""
    match = {
        "pick": "1",
        "market_odds": {"home": 1.8, "draw": 3.4, "away": 4.0},
        "xg_home": 1.5,
        "xg_away": 1.2
    }
    
    penalty = structural_penalty(match)
    assert penalty == 0.0, "Valid home pick should have no penalty"


def test_xg_confidence_function():
    """Test xG confidence calculation function."""
    # Balanced teams (high confidence)
    conf1 = xg_confidence(1.2, 1.2)
    
    # Unbalanced teams (low confidence)
    conf2 = xg_confidence(2.0, 0.5)
    
    assert 0.0 <= conf1 <= 1.0
    assert 0.0 <= conf2 <= 1.0
    assert conf1 > conf2, "Balanced teams should have higher confidence"


def test_xg_confidence_bounds():
    """Test that xG confidence is always within [0, 1] bounds."""
    test_cases = [
        (1.0, 1.0),   # Perfect balance
        (2.0, 0.5),   # Very unbalanced
        (0.0, 1.0),   # Extreme case
        (1.5, 1.5),   # High scoring balanced
    ]
    
    for xg_home, xg_away in test_cases:
        conf = xg_confidence(xg_home, xg_away)
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of bounds for xG ({xg_home}, {xg_away})"


def test_ev_score_positive_value():
    """Test that positive EV picks have positive scores."""
    ev = pick_decision_value(
        model_prob=0.60,  # High probability
        market_odds=2.0,  # Decent odds
        confidence=0.9,   # High confidence
        structural_penalty=0.0,
        is_hard_contradiction=False
    )
    
    assert ev > 0, "Positive EV pick should have positive score"


def test_ev_score_negative_value():
    """Test that negative EV picks have negative scores."""
    ev = pick_decision_value(
        model_prob=0.30,  # Low probability
        market_odds=2.0,  # But odds don't compensate
        confidence=0.8,
        structural_penalty=0.0,
        is_hard_contradiction=False
    )
    
    assert ev < 0, "Negative EV pick should have negative score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

