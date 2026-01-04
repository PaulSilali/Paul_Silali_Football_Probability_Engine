"""
Draw Structural Features Module

Computes draw-only probability adjustments using:
- League draw priors
- Elo symmetry
- Head-to-head draw rates
- Weather conditions
- Fatigue/rest days
- Referee behavior
- Odds movement

CRITICAL: Only adjusts draw probability. Home/away are never directly modified.
Home/away change only through renormalization to maintain probability sum = 1.0
"""
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from typing import Optional
from datetime import date

# Draw adjustment bounds
DRAW_MULTIPLIER_MIN = 0.75
DRAW_MULTIPLIER_MAX = 1.35
DRAW_PROB_MIN = 0.12
DRAW_PROB_MAX = 0.38

# Baseline draw rate (used for normalization)
BASELINE_DRAW_RATE = 0.26


@dataclass
class DrawComponents:
    """Container for all draw adjustment components"""
    league_prior: float = 1.0
    elo_symmetry: float = 1.0
    h2h_factor: float = 1.0
    weather_factor: float = 1.0
    fatigue_factor: float = 1.0
    referee_factor: float = 1.0
    odds_drift_factor: float = 1.0
    xg_factor: float = 1.0
    
    def total(self) -> float:
        """
        Compute total draw multiplier from all components.
        
        Returns:
            Bounded multiplier (0.75-1.35) for draw probability adjustment
        """
        return float(np.clip(
            self.league_prior *
            self.elo_symmetry *
            self.h2h_factor *
            self.weather_factor *
            self.fatigue_factor *
            self.referee_factor *
            self.odds_drift_factor *
            self.xg_factor,
            DRAW_MULTIPLIER_MIN,
            DRAW_MULTIPLIER_MAX
        ))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "league_prior": round(self.league_prior, 4),
            "elo_symmetry": round(self.elo_symmetry, 4),
            "h2h": round(self.h2h_factor, 4),
            "weather": round(self.weather_factor, 4),
            "fatigue": round(self.fatigue_factor, 4),
            "referee": round(self.referee_factor, 4),
            "odds_drift": round(self.odds_drift_factor, 4),
            "xg": round(self.xg_factor, 4),
            "total_multiplier": round(self.total(), 4)
        }


def compute_draw_components(
    db: Session,
    fixture_id: int,
    league_id: int,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    match_date: Optional[date] = None
) -> DrawComponents:
    """
    Compute all draw adjustment components for a fixture.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        league_id: League ID
        home_team_id: Home team ID (optional)
        away_team_id: Away team ID (optional)
        match_date: Match date (optional, defaults to today)
    
    Returns:
        DrawComponents with all multipliers (defaults to 1.0 if data missing)
    """
    components = DrawComponents()
    
    if match_date is None:
        from datetime import date as date_class
        match_date = date_class.today()
    
    # 1. League draw prior (enhanced with league structure)
    try:
        # Get league draw prior
        prior_result = db.execute(
            text("""
                SELECT draw_rate, sample_size
                FROM league_draw_priors
                WHERE league_id = :league_id
                ORDER BY updated_at DESC
                LIMIT 1
            """),
            {"league_id": league_id}
        ).fetchone()
        
        # Get league structure for additional context
        structure_result = db.execute(
            text("""
                SELECT total_teams, relegation_zones, promotion_zones
                FROM league_structure
                WHERE league_id = :league_id
                ORDER BY updated_at DESC
                LIMIT 1
            """),
            {"league_id": league_id}
        ).fetchone()
        
        base_prior = 1.0
        
        if prior_result and prior_result.sample_size >= 10:  # Minimum sample size
            # Normalize to baseline (0.26)
            base_prior = np.clip(
                prior_result.draw_rate / BASELINE_DRAW_RATE,
                0.9, 1.2
            )
        
        # Enhance with league structure
        if structure_result:
            total_teams = structure_result.total_teams or 20
            relegation_zones = structure_result.relegation_zones or 3
            
            # Larger leagues tend to have slightly higher draw rates (more competitive)
            # Smaller leagues (fewer teams) tend to have lower draw rates
            # Relegation zones affect late-season draw rates (teams play defensively)
            team_factor = 1.0 + (total_teams - 20) * 0.005  # +0.5% per team above 20
            relegation_factor = 1.0 + (relegation_zones / 3.0) * 0.02  # +2% per relegation zone
            
            # Combine factors (bounded)
            structure_multiplier = np.clip(
                team_factor * relegation_factor,
                0.95, 1.05
            )
            
            components.league_prior = np.clip(
                base_prior * structure_multiplier,
                0.9, 1.2
            )
        else:
            components.league_prior = base_prior
    except Exception:
        pass  # Missing data = neutral (1.0)
    
    # 2. Elo symmetry (only if both teams have Elo ratings)
    if home_team_id and away_team_id:
        try:
            result = db.execute(
                text("""
                    SELECT
                        MAX(CASE WHEN team_id = :home_id THEN elo_rating END) AS home_elo,
                        MAX(CASE WHEN team_id = :away_id THEN elo_rating END) AS away_elo
                    FROM team_elo
                    WHERE date <= :match_date
                      AND team_id IN (:home_id, :away_id)
                    GROUP BY team_id
                """),
                {
                    "home_id": home_team_id,
                    "away_id": away_team_id,
                    "match_date": match_date
                }
            ).fetchall()
            
            # Extract Elo ratings
            home_elo = None
            away_elo = None
            for row in result:
                if row.home_elo:
                    home_elo = row.home_elo
                if row.away_elo:
                    away_elo = row.away_elo
            
            # Alternative query if above doesn't work
            if home_elo is None or away_elo is None:
                home_result = db.execute(
                    text("""
                        SELECT elo_rating
                        FROM team_elo
                        WHERE team_id = :team_id AND date <= :match_date
                        ORDER BY date DESC
                        LIMIT 1
                    """),
                    {"team_id": home_team_id, "match_date": match_date}
                ).fetchone()
                if home_result:
                    home_elo = home_result.elo_rating
                
                away_result = db.execute(
                    text("""
                        SELECT elo_rating
                        FROM team_elo
                        WHERE team_id = :team_id AND date <= :match_date
                        ORDER BY date DESC
                        LIMIT 1
                    """),
                    {"team_id": away_team_id, "match_date": match_date}
                ).fetchone()
                if away_result:
                    away_elo = away_result.elo_rating
            
            if home_elo and away_elo:
                # Elo symmetry: closer ratings = higher draw probability
                elo_diff = abs(home_elo - away_elo)
                # Exponential decay: diff=0 -> 1.0, diff=160 -> ~0.37
                components.elo_symmetry = np.clip(
                    np.exp(-elo_diff / 160.0),
                    0.8, 1.2
                )
        except Exception:
            pass
    
    # 3. Head-to-head draw rate (minimum 4 matches)
    if home_team_id and away_team_id:
        try:
            result = db.execute(
                text("""
                    SELECT matches_played, draw_count
                    FROM h2h_draw_stats
                    WHERE team_home_id = :home_id
                      AND team_away_id = :away_id
                """),
                {"home_id": home_team_id, "away_id": away_team_id}
            ).fetchone()
            
            if result and result.matches_played >= 4:  # Minimum threshold
                h2h_draw_rate = result.draw_count / result.matches_played
                # Normalize to baseline
                components.h2h_factor = np.clip(
                    h2h_draw_rate / BASELINE_DRAW_RATE,
                    0.9, 1.15
                )
        except Exception:
            pass
    
    # 4. Weather conditions
    try:
        result = db.execute(
            text("""
                SELECT weather_draw_index
                FROM match_weather
                WHERE fixture_id = :fixture_id
            """),
            {"fixture_id": fixture_id}
        ).fetchone()
        
        if result and result.weather_draw_index is not None:
            # Weather index is already computed (0.95-1.10 typical)
            components.weather_factor = np.clip(
                result.weather_draw_index,
                0.95, 1.10
            )
    except Exception:
        pass
    
    # 5. Fatigue/rest days
    if home_team_id or away_team_id:
        try:
            team_ids = [tid for tid in [home_team_id, away_team_id] if tid]
            if team_ids:
                result = db.execute(
                    text("""
                        SELECT AVG(rest_days) AS avg_rest
                        FROM team_rest_days
                        WHERE fixture_id = :fixture_id
                          AND team_id IN :team_ids
                    """),
                    {
                        "fixture_id": fixture_id,
                        "team_ids": tuple(team_ids)
                    }
                ).fetchone()
                
                if result and result.avg_rest is not None:
                    avg_rest = float(result.avg_rest)
                    # Fatigue: less rest = higher draw probability
                    # Formula: 1 + max(0, 4 - rest_days) * 0.04
                    fatigue_penalty = max(0, 4 - avg_rest) * 0.04
                    components.fatigue_factor = np.clip(
                        1.0 + fatigue_penalty,
                        0.9, 1.12
                    )
        except Exception:
            pass
    
    # 6. Referee behavior
    try:
        result = db.execute(
            text("""
                SELECT r.avg_cards, r.avg_penalties
                FROM referee_stats r
                JOIN jackpot_fixtures jf ON jf.referee_id = r.referee_id
                WHERE jf.id = :fixture_id
            """),
            {"fixture_id": fixture_id}
        ).fetchone()
        
        if result and result.avg_cards is not None:
            # Low control (high cards/penalties) = lower draw probability
            # High control (low cards/penalties) = higher draw probability
            control_index = 1.0 / max(1.0, (result.avg_cards or 0) + (result.avg_penalties or 0))
            components.referee_factor = np.clip(
                1.0 + control_index * 0.08,
                0.95, 1.10
            )
    except Exception:
        pass
    
    # 7. Odds movement (draw drift)
    try:
        result = db.execute(
            text("""
                SELECT draw_delta
                FROM odds_movement
                WHERE fixture_id = :fixture_id
            """),
            {"fixture_id": fixture_id}
        ).fetchone()
        
        if result and result.draw_delta is not None:
            # Positive delta = draw odds increased = market sees more draw chance
            # Negative delta = draw odds decreased = market sees less draw chance
            # Scale: 0.15 per unit of delta (e.g., delta=0.1 -> +1.5%)
            components.odds_drift_factor = np.clip(
                1.0 + float(result.draw_delta) * 0.15,
                0.9, 1.15
            )
    except Exception:
        pass
    
    # 8. Expected Goals (xG) factor
    try:
        result = db.execute(
            text("""
                SELECT xg_draw_index
                FROM match_xg
                WHERE fixture_id = :fixture_id
            """),
            {"fixture_id": fixture_id}
        ).fetchone()
        
        if result and result.xg_draw_index is not None:
            # xG draw index is pre-calculated (lower xG = higher draw probability)
            components.xg_factor = np.clip(
                float(result.xg_draw_index),
                0.8, 1.2
            )
    except Exception:
        pass
    
    return components


def adjust_draw_probability(
    p_home_base: float,
    p_draw_base: float,
    p_away_base: float,
    draw_multiplier: float
) -> tuple[float, float, float]:
    """
    Adjust draw probability and renormalize home/away.
    
    CRITICAL: Only draw is directly modified. Home/away change proportionally
    to maintain probability sum = 1.0.
    
    Args:
        p_home_base: Base home win probability
        p_draw_base: Base draw probability
        p_away_base: Base away win probability
        draw_multiplier: Total draw adjustment multiplier
    
    Returns:
        Tuple of (p_home_final, p_draw_final, p_away_final)
    """
    # Adjust draw probability
    p_draw_adj = np.clip(
        p_draw_base * draw_multiplier,
        DRAW_PROB_MIN,
        DRAW_PROB_MAX
    )
    
    # Renormalize: scale home/away proportionally
    # Total probability must sum to 1.0
    remaining_prob = 1.0 - p_draw_adj
    base_win_prob = p_home_base + p_away_base
    
    if base_win_prob > 0:
        scale = remaining_prob / base_win_prob
        p_home_final = p_home_base * scale
        p_away_final = p_away_base * scale
    else:
        # Edge case: if base win prob is 0, split remaining equally
        p_home_final = remaining_prob / 2.0
        p_away_final = remaining_prob / 2.0
    
    # Ensure sum is exactly 1.0 (handle floating point errors)
    total = p_home_final + p_draw_adj + p_away_final
    if abs(total - 1.0) > 1e-6:
        # Normalize
        p_home_final /= total
        p_draw_adj /= total
        p_away_final /= total
    
    return (
        float(p_home_final),
        float(p_draw_adj),
        float(p_away_final)
    )

