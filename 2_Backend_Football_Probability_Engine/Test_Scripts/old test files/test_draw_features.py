"""
Unit tests for draw structural features

Tests invariants and correctness, not accuracy.
"""
import pytest
import numpy as np
from app.features.draw_features import (
    DrawComponents,
    compute_draw_components,
    adjust_draw_probability
)
from app.db.session import SessionLocal
from app.db.models import (
    LeagueDrawPrior, H2HDrawStats, TeamElo, MatchWeather,
    RefereeStats, TeamRestDays, OddsMovement, League, Team, JackpotFixture, Jackpot
)
from datetime import date, datetime


class TestDrawComponents:
    """Test DrawComponents data class"""
    
    def test_default_components(self):
        """Test that default components are all 1.0"""
        components = DrawComponents()
        assert components.league_prior == 1.0
        assert components.elo_symmetry == 1.0
        assert components.h2h_factor == 1.0
        assert components.weather_factor == 1.0
        assert components.fatigue_factor == 1.0
        assert components.referee_factor == 1.0
        assert components.odds_drift_factor == 1.0
    
    def test_total_multiplier_default(self):
        """Test that default total multiplier is 1.0"""
        components = DrawComponents()
        assert abs(components.total() - 1.0) < 1e-6
    
    def test_total_multiplier_bounded(self):
        """Test that total multiplier is bounded"""
        # Test minimum bound
        components = DrawComponents(
            league_prior=0.5,
            elo_symmetry=0.5,
            h2h_factor=0.5,
            weather_factor=0.5,
            fatigue_factor=0.5,
            referee_factor=0.5,
            odds_drift_factor=0.5
        )
        assert components.total() >= 0.75
        
        # Test maximum bound
        components = DrawComponents(
            league_prior=2.0,
            elo_symmetry=2.0,
            h2h_factor=2.0,
            weather_factor=2.0,
            fatigue_factor=2.0,
            referee_factor=2.0,
            odds_drift_factor=2.0
        )
        assert components.total() <= 1.35
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        components = DrawComponents(league_prior=1.2, elo_symmetry=1.1)
        result = components.to_dict()
        
        assert 'league_prior' in result
        assert 'elo_symmetry' in result
        assert 'total_multiplier' in result
        assert isinstance(result['league_prior'], float)
        assert isinstance(result['total_multiplier'], float)


class TestAdjustDrawProbability:
    """Test draw probability adjustment function"""
    
    def test_probabilities_sum_to_one(self):
        """CRITICAL: Probabilities must sum to 1.0"""
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base=0.4,
            p_draw_base=0.3,
            p_away_base=0.3,
            draw_multiplier=1.2
        )
        
        total = p_home + p_draw + p_away
        assert abs(total - 1.0) < 1e-6, f"Probabilities sum to {total}, not 1.0"
    
    def test_home_away_ordering_preserved(self):
        """Test that home/away relative ordering is preserved"""
        # Home stronger than away
        p_home_base = 0.5
        p_away_base = 0.2
        p_draw_base = 0.3
        
        p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, draw_multiplier=1.2
        )
        
        # Home should still be stronger than away
        assert p_home_adj > p_away_adj, "Home/away ordering not preserved"
        
        # Ratio should be approximately maintained
        original_ratio = p_home_base / p_away_base
        adjusted_ratio = p_home_adj / p_away_adj
        assert abs(original_ratio - adjusted_ratio) < 0.1, "Home/away ratio changed significantly"
    
    def test_draw_bounds_enforced(self):
        """Test that draw probability is bounded"""
        # Test minimum bound
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base=0.4,
            p_draw_base=0.1,  # Very low base
            p_away_base=0.5,
            draw_multiplier=0.5  # Strong decrease
        )
        assert p_draw >= 0.12, f"Draw probability {p_draw} below minimum 0.12"
        
        # Test maximum bound
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base=0.3,
            p_draw_base=0.4,  # High base
            p_away_base=0.3,
            draw_multiplier=1.5  # Strong increase
        )
        assert p_draw <= 0.38, f"Draw probability {p_draw} above maximum 0.38"
    
    def test_neutral_multiplier(self):
        """Test that multiplier of 1.0 doesn't change probabilities (except rounding)"""
        p_home_base = 0.4
        p_draw_base = 0.3
        p_away_base = 0.3
        
        p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, draw_multiplier=1.0
        )
        
        # Draw should be approximately the same
        assert abs(p_draw_adj - p_draw_base) < 0.01, "Neutral multiplier changed draw probability"
        
        # Home/away should be approximately the same
        assert abs(p_home_adj - p_home_base) < 0.01, "Neutral multiplier changed home probability"
        assert abs(p_away_adj - p_away_base) < 0.01, "Neutral multiplier changed away probability"
    
    def test_increase_draw_decreases_home_away(self):
        """Test that increasing draw decreases home/away proportionally"""
        p_home_base = 0.5
        p_draw_base = 0.2
        p_away_base = 0.3
        
        p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, draw_multiplier=1.3
        )
        
        # Draw should increase
        assert p_draw_adj > p_draw_base, "Draw probability did not increase"
        
        # Home and away should decrease
        assert p_home_adj < p_home_base, "Home probability did not decrease"
        assert p_away_adj < p_away_base, "Away probability did not decrease"
        
        # But ratio should be preserved
        original_ratio = p_home_base / p_away_base
        adjusted_ratio = p_home_adj / p_away_adj
        assert abs(original_ratio - adjusted_ratio) < 0.05, "Home/away ratio not preserved"
    
    def test_decrease_draw_increases_home_away(self):
        """Test that decreasing draw increases home/away proportionally"""
        p_home_base = 0.4
        p_draw_base = 0.3
        p_away_base = 0.3
        
        p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, draw_multiplier=0.8
        )
        
        # Draw should decrease
        assert p_draw_adj < p_draw_base, "Draw probability did not decrease"
        
        # Home and away should increase
        assert p_home_adj > p_home_base, "Home probability did not increase"
        assert p_away_adj > p_away_base, "Away probability did not increase"
    
    def test_edge_case_zero_base_win_prob(self):
        """Test edge case where base win probability is 0"""
        # This shouldn't happen in practice, but test for robustness
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base=0.0,
            p_draw_base=1.0,
            p_away_base=0.0,
            draw_multiplier=1.0
        )
        
        # Should still sum to 1.0
        assert abs(p_home + p_draw + p_away - 1.0) < 1e-6
        # Draw should be 1.0 (or close to it)
        assert p_draw >= 0.99


class TestComputeDrawComponents:
    """Test compute_draw_components function with database"""
    
    @pytest.fixture
    def db(self):
        """Create database session"""
        db = SessionLocal()
        yield db
        db.close()
    
    def test_missing_data_is_neutral(self, db):
        """Test that missing data results in neutral components"""
        components = compute_draw_components(
            db=db,
            fixture_id=999999,  # Non-existent fixture
            league_id=999999,   # Non-existent league
            home_team_id=None,
            away_team_id=None,
            match_date=date.today()
        )
        
        # All components should be 1.0 (neutral)
        assert components.league_prior == 1.0
        assert components.elo_symmetry == 1.0
        assert components.h2h_factor == 1.0
        assert components.weather_factor == 1.0
        assert components.fatigue_factor == 1.0
        assert components.referee_factor == 1.0
        assert components.odds_drift_factor == 1.0
        assert abs(components.total() - 1.0) < 1e-6
    
    def test_h2h_threshold_enforced(self, db):
        """Test that H2H with low sample is ignored"""
        # Create test data with low sample
        # (This would require setting up test database)
        # For now, test that function handles missing/low sample gracefully
        
        components = compute_draw_components(
            db=db,
            fixture_id=999999,
            league_id=1,
            home_team_id=999999,
            away_team_id=999998,
            match_date=date.today()
        )
        
        # H2H factor should be 1.0 (neutral) if sample too low
        assert components.h2h_factor == 1.0
    
    def test_component_bounds(self, db):
        """Test that all components are bounded"""
        # Test with various inputs
        components = compute_draw_components(
            db=db,
            fixture_id=999999,
            league_id=1,
            home_team_id=1,
            away_team_id=2,
            match_date=date.today()
        )
        
        # All components should be within reasonable bounds
        assert 0.5 <= components.league_prior <= 2.0
        assert 0.5 <= components.elo_symmetry <= 2.0
        assert 0.5 <= components.h2h_factor <= 2.0
        assert 0.5 <= components.weather_factor <= 2.0
        assert 0.5 <= components.fatigue_factor <= 2.0
        assert 0.5 <= components.referee_factor <= 2.0
        assert 0.5 <= components.odds_drift_factor <= 2.0


class TestIntegration:
    """Integration tests for full draw adjustment pipeline"""
    
    def test_full_pipeline_probability_sum(self):
        """Test that full pipeline maintains probability sum"""
        # Simulate full pipeline
        p_home_base = 0.45
        p_draw_base = 0.25
        p_away_base = 0.30
        
        # Create components with various multipliers
        components = DrawComponents(
            league_prior=1.1,
            elo_symmetry=1.05,
            h2h_factor=1.02,
            weather_factor=1.0,
            fatigue_factor=1.03,
            referee_factor=0.98,
            odds_drift_factor=1.01
        )
        
        # Adjust
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, components.total()
        )
        
        # Must sum to 1.0
        total = p_home + p_draw + p_away
        assert abs(total - 1.0) < 1e-6, f"Full pipeline: probabilities sum to {total}"
        
        # Draw should be adjusted
        assert p_draw != p_draw_base, "Draw probability was not adjusted"
        
        # Home/away should be renormalized
        assert p_home != p_home_base or p_away != p_away_base, "Home/away were not renormalized"
    
    def test_no_signal_leakage(self):
        """Test that home/away never receive direct signals"""
        # Start with equal probabilities
        p_home_base = 0.33
        p_draw_base = 0.34
        p_away_base = 0.33
        
        # Apply strong draw adjustment
        components = DrawComponents(
            league_prior=1.3,  # Strong increase
            elo_symmetry=1.0,
            h2h_factor=1.0,
            weather_factor=1.0,
            fatigue_factor=1.0,
            referee_factor=1.0,
            odds_drift_factor=1.0
        )
        
        p_home, p_draw, p_away = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, components.total()
        )
        
        # Home and away should change proportionally (not independently)
        # Their ratio should be preserved
        original_ratio = p_home_base / p_away_base
        adjusted_ratio = p_home_adj / p_away_adj if p_away_adj > 0 else 1.0
        
        # Ratio should be approximately the same
        assert abs(original_ratio - adjusted_ratio) < 0.1, "Home/away ratio changed (signal leakage)"
        
        # Neither should be boosted independently
        # If home was stronger, it should remain stronger (or vice versa)
        if p_home_base > p_away_base:
            assert p_home > p_away, "Home/away ordering reversed"
        elif p_away_base > p_home_base:
            assert p_away > p_home, "Home/away ordering reversed"
    
    def test_no_signal_leakage_fixed(self):
        """Test that home/away never receive direct signals (fixed version)"""
        # Start with equal probabilities
        p_home_base = 0.33
        p_draw_base = 0.34
        p_away_base = 0.33
        
        # Apply strong draw adjustment
        components = DrawComponents(
            league_prior=1.3,  # Strong increase
            elo_symmetry=1.0,
            h2h_factor=1.0,
            weather_factor=1.0,
            fatigue_factor=1.0,
            referee_factor=1.0,
            odds_drift_factor=1.0
        )
        
        p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
            p_home_base, p_draw_base, p_away_base, components.total()
        )
        
        # Home and away should change proportionally (not independently)
        # Their ratio should be preserved
        original_ratio = p_home_base / p_away_base if p_away_base > 0 else 1.0
        adjusted_ratio = p_home_adj / p_away_adj if p_away_adj > 0 else 1.0
        
        # Ratio should be approximately the same
        assert abs(original_ratio - adjusted_ratio) < 0.1, "Home/away ratio changed (signal leakage)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

