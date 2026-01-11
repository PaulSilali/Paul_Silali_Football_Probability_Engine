"""
Portfolio-Level Correlation & EV Scoring Tests
===============================================

Tests for portfolio-level optimization, correlation calculation,
and bundle selection.
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))

from app.services.portfolio_scoring import (
    ticket_correlation,
    portfolio_score,
    select_optimal_bundle,
    calculate_portfolio_diagnostics
)


def test_ticket_correlation_identical_picks():
    """Test that identical tickets have correlation = 1.0."""
    t1 = {"picks": ["1", "X", "2", "1", "X"]}
    t2 = {"picks": ["1", "X", "2", "1", "X"]}
    
    corr = ticket_correlation(t1, t2)
    assert corr == 1.0, "Identical tickets should have correlation = 1.0"


def test_ticket_correlation_no_overlap():
    """Test that completely different tickets have correlation = 0.0."""
    t1 = {"picks": ["1", "1", "1", "1", "1"]}
    t2 = {"picks": ["2", "2", "2", "2", "2"]}
    
    corr = ticket_correlation(t1, t2)
    assert corr == 0.0, "Completely different tickets should have correlation = 0.0"


def test_ticket_correlation_partial_overlap():
    """Test that partial overlap gives correlation between 0 and 1."""
    t1 = {"picks": ["1", "X", "2", "1", "X"]}
    t2 = {"picks": ["1", "X", "1", "2", "2"]}  # 2 matches out of 5
    
    corr = ticket_correlation(t1, t2)
    assert 0.0 < corr < 1.0, "Partial overlap should give correlation between 0 and 1"
    assert abs(corr - 0.4) < 0.01, f"Expected correlation ~0.4, got {corr}"


def test_ticket_correlation_with_dict_picks():
    """Test correlation calculation with dict-based picks."""
    t1 = {"picks": [{"pick": "1"}, {"pick": "X"}, {"pick": "2"}]}
    t2 = {"picks": [{"pick": "1"}, {"pick": "X"}, {"pick": "1"}]}
    
    corr = ticket_correlation(t1, t2)
    assert 0.0 <= corr <= 1.0
    assert abs(corr - (2/3)) < 0.01, f"Expected correlation ~0.667, got {corr}"


def test_portfolio_score_penalizes_overlap():
    """Test that portfolio score penalizes high correlation."""
    t1 = {"ev_score": 1.2, "picks": ["1", "1", "1", "1", "1"]}
    t2 = {"ev_score": 1.1, "picks": ["1", "1", "1", "1", "1"]}  # Identical picks
    
    score = portfolio_score([t1, t2])
    total_ev = t1["ev_score"] + t2["ev_score"]
    
    assert score < total_ev, "High correlation should reduce portfolio score"


def test_portfolio_score_rewards_diversity():
    """Test that portfolio score rewards diverse tickets."""
    t1 = {"ev_score": 1.2, "picks": ["1", "X", "2", "1", "X"]}
    t2 = {"ev_score": 1.1, "picks": ["2", "1", "X", "2", "1"]}  # Different picks
    
    score = portfolio_score([t1, t2])
    total_ev = t1["ev_score"] + t2["ev_score"]
    
    # Low correlation should result in score close to total EV
    assert score >= total_ev * 0.9, "Diverse tickets should maintain high portfolio score"


def test_portfolio_score_single_ticket():
    """Test portfolio score for single ticket."""
    t1 = {"ev_score": 1.2, "picks": ["1", "X", "2"]}
    
    score = portfolio_score([t1])
    assert score == t1["ev_score"], "Single ticket portfolio score should equal ticket EV"


def test_portfolio_score_empty_list():
    """Test portfolio score for empty ticket list."""
    score = portfolio_score([])
    assert score == 0.0, "Empty portfolio should have score = 0"


def test_select_optimal_bundle_chooses_highest_ev():
    """Test that optimal bundle selection starts with highest EV ticket."""
    candidates = [
        {"ev_score": 0.8, "picks": ["1", "1", "1"]},
        {"ev_score": 1.2, "picks": ["1", "X", "2"]},  # Highest EV
        {"ev_score": 1.0, "picks": ["2", "2", "2"]},
    ]
    
    bundle = select_optimal_bundle(candidates, n_tickets=1)
    assert len(bundle) == 1
    assert bundle[0]["ev_score"] == 1.2, "Should select highest EV ticket"


def test_select_optimal_bundle_prefers_diversity():
    """Test that optimal bundle prefers diverse tickets over correlated ones."""
    candidates = [
        {"ev_score": 1.2, "picks": ["1", "1", "1", "1", "1"]},  # High EV but correlated
        {"ev_score": 1.1, "picks": ["1", "X", "2", "1", "X"]},  # Slightly lower EV but diverse
        {"ev_score": 1.15, "picks": ["1", "1", "1", "1", "1"]},  # High EV but same as first
    ]
    
    bundle = select_optimal_bundle(candidates, n_tickets=2)
    assert len(bundle) == 2
    
    # Should prefer diverse ticket over second correlated one
    picks_in_bundle = [t["picks"] for t in bundle]
    # At least one ticket should be diverse
    has_diverse = any(len(set(picks)) > 1 for picks in picks_in_bundle)
    assert has_diverse, "Bundle should include diverse ticket"


def test_select_optimal_bundle_returns_all_if_less_than_n():
    """Test that optimal bundle returns all tickets if fewer than requested."""
    candidates = [
        {"ev_score": 1.2, "picks": ["1", "X", "2"]},
        {"ev_score": 1.0, "picks": ["2", "1", "X"]},
    ]
    
    bundle = select_optimal_bundle(candidates, n_tickets=5)
    assert len(bundle) == 2, "Should return all tickets if fewer than requested"


def test_calculate_portfolio_diagnostics():
    """Test portfolio diagnostics calculation."""
    tickets = [
        {"ev_score": 1.2, "picks": ["1", "X", "2"]},
        {"ev_score": 1.0, "picks": ["2", "1", "X"]},
        {"ev_score": 0.9, "picks": ["1", "1", "1"]},
    ]
    
    diagnostics = calculate_portfolio_diagnostics(tickets)
    
    assert "total_tickets" in diagnostics
    assert "avg_ev" in diagnostics
    assert "total_ev" in diagnostics
    assert "avg_correlation" in diagnostics
    assert "max_correlation" in diagnostics
    assert "diversity_score" in diagnostics
    
    assert diagnostics["total_tickets"] == 3
    assert diagnostics["total_ev"] == pytest.approx(3.1, abs=0.01)
    assert diagnostics["avg_ev"] == pytest.approx(1.033, abs=0.01)
    assert 0.0 <= diagnostics["avg_correlation"] <= 1.0
    assert 0.0 <= diagnostics["max_correlation"] <= 1.0
    assert 0.0 <= diagnostics["diversity_score"] <= 1.0


def test_calculate_portfolio_diagnostics_empty():
    """Test portfolio diagnostics for empty ticket list."""
    diagnostics = calculate_portfolio_diagnostics([])
    
    assert diagnostics["total_tickets"] == 0
    assert diagnostics["avg_ev"] == 0.0
    assert diagnostics["total_ev"] == 0.0
    assert diagnostics["avg_correlation"] == 0.0
    assert diagnostics["max_correlation"] == 0.0
    assert diagnostics["diversity_score"] == 0.0


def test_calculate_portfolio_diagnostics_single_ticket():
    """Test portfolio diagnostics for single ticket."""
    tickets = [
        {"ev_score": 1.2, "picks": ["1", "X", "2"]}
    ]
    
    diagnostics = calculate_portfolio_diagnostics(tickets)
    
    assert diagnostics["total_tickets"] == 1
    assert diagnostics["total_ev"] == 1.2
    assert diagnostics["avg_ev"] == 1.2
    # Single ticket has no correlation
    assert diagnostics["avg_correlation"] == 0.0
    assert diagnostics["max_correlation"] == 0.0
    assert diagnostics["diversity_score"] == 1.0


def test_portfolio_score_correlation_threshold():
    """Test that correlation penalty only applies above 0.5 threshold."""
    # Low correlation (< 0.5) should not be penalized
    t1 = {"ev_score": 1.2, "picks": ["1", "X", "2", "1", "X"]}
    t2 = {"ev_score": 1.1, "picks": ["1", "X", "1", "2", "2"]}  # 2/5 overlap = 0.4
    
    score = portfolio_score([t1, t2])
    total_ev = t1["ev_score"] + t2["ev_score"]
    
    # Correlation 0.4 < 0.5, so no penalty
    assert abs(score - total_ev) < 0.01, "Low correlation should not be penalized"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

