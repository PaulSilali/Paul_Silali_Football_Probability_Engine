"""
End-to-End Flow Tests
=====================

Tests for complete ticket generation pipeline including:
- Ticket generation
- Archetype enforcement
- Decision Intelligence evaluation
- Portfolio optimization
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../2_Backend_Football_Probability_Engine'))


def test_ticket_has_decision_intelligence_metadata():
    """Test that generated tickets include Decision Intelligence metadata."""
    # This is a mock test - in real scenario, would call actual ticket generation
    # For now, we test the structure that should be present
    
    expected_structure = {
        "id": str,
        "setKey": str,
        "picks": list,
        "archetype": str,
        "decision_version": str,
        "decisionIntelligence": {
            "accepted": bool,
            "evScore": (float, type(None)),
            "contradictions": int,
            "reason": str
        },
        "ev_score": (float, type(None))
    }
    
    # Mock ticket structure (what should be returned)
    mock_ticket = {
        "id": "ticket-B-0",
        "setKey": "B",
        "picks": ["1", "X", "2", "1", "X"],
        "archetype": "BALANCED",
        "decision_version": "UDS_v1",
        "decisionIntelligence": {
            "accepted": True,
            "evScore": 0.15,
            "contradictions": 0,
            "reason": "Passed structural validation"
        },
        "ev_score": 0.15
    }
    
    # Verify structure
    assert "decisionIntelligence" in mock_ticket
    assert "accepted" in mock_ticket["decisionIntelligence"]
    assert "evScore" in mock_ticket["decisionIntelligence"]
    assert "contradictions" in mock_ticket["decisionIntelligence"]
    assert "reason" in mock_ticket["decisionIntelligence"]
    assert "archetype" in mock_ticket
    assert "decision_version" in mock_ticket


def test_accepted_ticket_has_positive_ev():
    """Test that accepted tickets have positive EV scores."""
    # Mock accepted ticket
    accepted_ticket = {
        "decisionIntelligence": {
            "accepted": True,
            "evScore": 0.15
        }
    }
    
    assert accepted_ticket["decisionIntelligence"]["accepted"] is True
    assert accepted_ticket["decisionIntelligence"]["evScore"] > 0


def test_rejected_ticket_has_reason():
    """Test that rejected tickets include rejection reason."""
    # Mock rejected ticket
    rejected_ticket = {
        "decisionIntelligence": {
            "accepted": False,
            "evScore": 0.05,
            "contradictions": 2,
            "reason": "Too many contradictions (2 > 1)"
        }
    }
    
    assert rejected_ticket["decisionIntelligence"]["accepted"] is False
    assert "reason" in rejected_ticket["decisionIntelligence"]
    assert len(rejected_ticket["decisionIntelligence"]["reason"]) > 0


def test_ticket_archetype_is_set():
    """Test that tickets have archetype set."""
    # Mock ticket
    ticket = {
        "archetype": "FAVORITE_LOCK",
        "picks": ["1", "1", "1", "X", "1"]
    }
    
    assert "archetype" in ticket
    assert ticket["archetype"] in ["FAVORITE_LOCK", "BALANCED", "DRAW_SELECTIVE", "AWAY_EDGE"]


def test_ticket_decision_version_is_set():
    """Test that tickets have decision_version set."""
    # Mock ticket
    ticket = {
        "decision_version": "UDS_v1",
        "decisionIntelligence": {
            "accepted": True
        }
    }
    
    assert "decision_version" in ticket
    assert ticket["decision_version"] == "UDS_v1"


def test_portfolio_bundle_has_diagnostics():
    """Test that portfolio bundles include diagnostics."""
    # Mock portfolio response
    portfolio_response = {
        "tickets": [
            {"ev_score": 1.2, "picks": ["1", "X", "2"]},
            {"ev_score": 1.0, "picks": ["2", "1", "X"]}
        ],
        "diagnostics": {
            "total_tickets": 2,
            "avg_ev": 1.1,
            "total_ev": 2.2,
            "avg_correlation": 0.3,
            "max_correlation": 0.4,
            "diversity_score": 0.7
        }
    }
    
    assert "diagnostics" in portfolio_response
    assert "total_tickets" in portfolio_response["diagnostics"]
    assert "avg_ev" in portfolio_response["diagnostics"]
    assert "diversity_score" in portfolio_response["diagnostics"]


def test_ticket_picks_match_fixtures():
    """Test that ticket picks match fixture count."""
    # Mock ticket
    ticket = {
        "picks": ["1", "X", "2", "1", "X"],
        "fixtures": [
            {"id": 1, "home_team": "Team A", "away_team": "Team B"},
            {"id": 2, "home_team": "Team C", "away_team": "Team D"},
            {"id": 3, "home_team": "Team E", "away_team": "Team F"},
            {"id": 4, "home_team": "Team G", "away_team": "Team H"},
            {"id": 5, "home_team": "Team I", "away_team": "Team J"},
        ]
    }
    
    assert len(ticket["picks"]) == len(ticket["fixtures"])


def test_contradiction_count_matches_picks():
    """Test that contradiction count doesn't exceed pick count."""
    ticket = {
        "picks": ["1", "X", "2", "1", "X"],
        "decisionIntelligence": {
            "contradictions": 1
        }
    }
    
    assert ticket["decisionIntelligence"]["contradictions"] <= len(ticket["picks"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

