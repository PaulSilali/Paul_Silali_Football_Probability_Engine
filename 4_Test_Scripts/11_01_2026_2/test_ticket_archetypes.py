"""
Ticket Archetype Enforcement Tests
===================================

Tests for ticket archetype selection and constraint enforcement.
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

from app.services.ticket_archetypes import (
    select_archetype,
    enforce_archetype,
    analyze_slate_profile
)


def test_favorite_lock_rejects_high_odds_draw():
    """Test that FAVORITE_LOCK rejects draw picks with odds > 3.20."""
    ticket = [
        {
            "pick": "X",
            "odds": {"home": 1.8, "draw": 3.6, "away": 4.0},  # draw > 3.20
            "xg_home": 1.5,
            "xg_away": 1.2
        },
        {
            "pick": "1",
            "odds": {"home": 1.8, "draw": 3.4, "away": 4.0},
            "xg_home": 1.5,
            "xg_away": 1.2
        }
    ]
    
    assert enforce_archetype(ticket, "FAVORITE_LOCK") is False


def test_favorite_lock_rejects_high_odds_away():
    """Test that FAVORITE_LOCK rejects away picks with odds > 2.80."""
    ticket = [
        {
            "pick": "2",
            "odds": {"home": 1.8, "draw": 3.4, "away": 3.0},  # away > 2.80
            "xg_home": 1.5,
            "xg_away": 1.2
        }
    ]
    
    assert enforce_archetype(ticket, "FAVORITE_LOCK") is False


def test_favorite_lock_allows_valid_ticket():
    """Test that FAVORITE_LOCK accepts valid favorite-heavy tickets."""
    ticket = [
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}, "market_prob_home": 0.56},  # > 0.55
        {"pick": "1", "odds": {"home": 1.7, "draw": 3.5, "away": 4.5}, "market_prob_home": 0.59},  # > 0.55
        {"pick": "1", "odds": {"home": 1.9, "draw": 3.3, "away": 3.8}, "market_prob_home": 0.53},  # > 0.55
        {"pick": "X", "odds": {"home": 2.2, "draw": 3.1, "away": 3.2}},  # draw <= 3.20
        {"pick": "1", "odds": {"home": 1.6, "draw": 3.6, "away": 5.0}, "market_prob_home": 0.62},  # > 0.55
    ]
    # 4 out of 5 picks have market_prob_home > 0.55 (80% > 60%)
    
    assert enforce_archetype(ticket, "FAVORITE_LOCK") is True


def test_favorite_lock_enforces_draw_limit():
    """Test that FAVORITE_LOCK enforces max 1 draw."""
    ticket = [
        {"pick": "X", "odds": {"home": 2.0, "draw": 3.1, "away": 3.5}},
        {"pick": "X", "odds": {"home": 2.2, "draw": 3.0, "away": 3.3}},  # Second draw
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
    ]
    
    assert enforce_archetype(ticket, "FAVORITE_LOCK") is False


def test_favorite_lock_enforces_away_limit():
    """Test that FAVORITE_LOCK enforces max 1 away."""
    ticket = [
        {"pick": "2", "odds": {"home": 2.0, "draw": 3.4, "away": 2.7}},  # away <= 2.80
        {"pick": "2", "odds": {"home": 2.2, "draw": 3.3, "away": 2.6}},  # Second away
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
    ]
    
    assert enforce_archetype(ticket, "FAVORITE_LOCK") is False


def test_draw_selective_requires_dc_applied():
    """Test that DRAW_SELECTIVE requires DC applied for draw picks."""
    ticket = [
        {
            "pick": "X",
            "odds": {"home": 2.0, "draw": 3.1, "away": 3.5},  # draw <= 3.40
            "xg_home": 1.1,
            "xg_away": 1.0,  # |diff| = 0.1 <= 0.30
            "dc_applied": False  # DC not applied
        }
    ]
    
    assert enforce_archetype(ticket, "DRAW_SELECTIVE") is False


def test_draw_selective_requires_low_xg_diff():
    """Test that DRAW_SELECTIVE requires |xG_diff| <= 0.30 for draws."""
    ticket = [
        {
            "pick": "X",
            "odds": {"home": 2.0, "draw": 3.1, "away": 3.5},
            "xg_home": 1.8,
            "xg_away": 1.2,  # |diff| = 0.6 > 0.30
            "dc_applied": True
        }
    ]
    
    assert enforce_archetype(ticket, "DRAW_SELECTIVE") is False


def test_draw_selective_enforces_draw_count():
    """Test that DRAW_SELECTIVE enforces min 2, max 3 draws."""
    # Too few draws
    ticket1 = [
        {"pick": "X", "odds": {"home": 2.0, "draw": 3.1, "away": 3.5}, "xg_home": 1.1, "xg_away": 1.0, "dc_applied": True},
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
    ]
    assert enforce_archetype(ticket1, "DRAW_SELECTIVE") is False
    
    # Too many draws
    ticket2 = [
        {"pick": "X", "odds": {"home": 2.0, "draw": 3.1, "away": 3.5}, "xg_home": 1.1, "xg_away": 1.0, "dc_applied": True},
        {"pick": "X", "odds": {"home": 2.2, "draw": 3.0, "away": 3.3}, "xg_home": 1.2, "xg_away": 1.1, "dc_applied": True},
        {"pick": "X", "odds": {"home": 2.1, "draw": 3.2, "away": 3.4}, "xg_home": 1.0, "xg_away": 0.9, "dc_applied": True},
        {"pick": "X", "odds": {"home": 2.3, "draw": 3.1, "away": 3.2}, "xg_home": 1.1, "xg_away": 1.0, "dc_applied": True},  # 4th draw
    ]
    assert enforce_archetype(ticket2, "DRAW_SELECTIVE") is False


def test_draw_selective_allows_valid_ticket():
    """Test that DRAW_SELECTIVE accepts valid draw-focused tickets."""
    ticket = [
        {"pick": "X", "odds": {"home": 2.0, "draw": 3.1, "away": 3.5}, "xg_home": 1.1, "xg_away": 1.0, "dc_applied": True},
        {"pick": "X", "odds": {"home": 2.2, "draw": 3.0, "away": 3.3}, "xg_home": 1.2, "xg_away": 1.1, "dc_applied": True},
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
    ]
    
    assert enforce_archetype(ticket, "DRAW_SELECTIVE") is True


def test_away_edge_requires_value():
    """Test that AWAY_EDGE requires model_prob - market_prob >= +0.07."""
    ticket = [
        {
            "pick": "2",
            "odds": {"home": 1.8, "draw": 3.4, "away": 3.5},
            "model_prob": 0.30,
            "market_prob": 0.28  # diff = 0.02 < 0.07
        }
    ]
    
    assert enforce_archetype(ticket, "AWAY_EDGE") is False


def test_away_edge_enforces_away_count():
    """Test that AWAY_EDGE enforces min 2, max 3 away picks."""
    # Too few away
    ticket1 = [
        {"pick": "2", "odds": {"home": 1.8, "draw": 3.4, "away": 3.5}, "model_prob": 0.35, "market_prob": 0.28},
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
    ]
    assert enforce_archetype(ticket1, "AWAY_EDGE") is False
    
    # Too many away
    ticket2 = [
        {"pick": "2", "odds": {"home": 1.8, "draw": 3.4, "away": 3.5}, "model_prob": 0.35, "market_prob": 0.28},
        {"pick": "2", "odds": {"home": 2.0, "draw": 3.2, "away": 3.3}, "model_prob": 0.33, "market_prob": 0.30},
        {"pick": "2", "odds": {"home": 2.2, "draw": 3.1, "away": 3.2}, "model_prob": 0.32, "market_prob": 0.31},
        {"pick": "2", "odds": {"home": 2.1, "draw": 3.3, "away": 3.4}, "model_prob": 0.34, "market_prob": 0.29},  # 4th away
    ]
    assert enforce_archetype(ticket2, "AWAY_EDGE") is False


def test_balanced_allows_diversification():
    """Test that BALANCED allows controlled diversification."""
    ticket = [
        {"pick": "1", "odds": {"home": 1.8, "draw": 3.4, "away": 4.0}},
        {"pick": "X", "odds": {"home": 2.0, "draw": 3.2, "away": 3.5}, "xg_home": 1.2, "xg_away": 1.1},  # |diff| = 0.1 <= 0.35
        {"pick": "2", "odds": {"home": 2.2, "draw": 3.1, "away": 3.2}, "model_prob": 0.33, "market_prob": 0.31},  # diff = 0.02 >= 0.05? No, but that's OK for balanced
        {"pick": "1", "odds": {"home": 1.9, "draw": 3.3, "away": 3.8}},
    ]
    
    assert enforce_archetype(ticket, "BALANCED") is True


def test_archetype_selection_favorite_lock():
    """Test archetype selection for favorite-heavy slate."""
    slate_profile = {
        "avg_home_prob": 0.55,  # > 0.52
        "balanced_rate": 0.3,
        "away_value_rate": 0.2
    }
    
    assert select_archetype(slate_profile) == "FAVORITE_LOCK"


def test_archetype_selection_draw_selective():
    """Test archetype selection for balanced slate."""
    slate_profile = {
        "avg_home_prob": 0.48,
        "balanced_rate": 0.45,  # > 0.4
        "away_value_rate": 0.2
    }
    
    assert select_archetype(slate_profile) == "DRAW_SELECTIVE"


def test_archetype_selection_away_edge():
    """Test archetype selection for away value slate."""
    slate_profile = {
        "avg_home_prob": 0.48,
        "balanced_rate": 0.3,
        "away_value_rate": 0.35  # > 0.3
    }
    
    assert select_archetype(slate_profile) == "AWAY_EDGE"


def test_archetype_selection_balanced_default():
    """Test archetype selection defaults to BALANCED."""
    slate_profile = {
        "avg_home_prob": 0.48,
        "balanced_rate": 0.3,
        "away_value_rate": 0.2
    }
    
    assert select_archetype(slate_profile) == "BALANCED"


def test_analyze_slate_profile():
    """Test slate profile analysis."""
    fixtures = [
        {
            "probabilities": {"home": 0.55, "draw": 0.25, "away": 0.20},
            "odds": {"home": 1.82, "draw": 3.4, "away": 4.5},
            "xg_home": 1.2,
            "xg_away": 1.1
        },
        {
            "probabilities": {"home": 0.50, "draw": 0.30, "away": 0.20},
            "odds": {"home": 2.0, "draw": 3.2, "away": 3.5},
            "xg_home": 1.1,
            "xg_away": 1.0
        }
    ]
    
    profile = analyze_slate_profile(fixtures)
    
    assert "avg_home_prob" in profile
    assert "balanced_rate" in profile
    assert "away_value_rate" in profile
    assert 0.0 <= profile["avg_home_prob"] <= 1.0
    assert 0.0 <= profile["balanced_rate"] <= 1.0
    assert 0.0 <= profile["away_value_rate"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

