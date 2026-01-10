"""
Draw Signal Calculator Service

Fetches draw structural data from the database and computes a normalized
draw signal (0.0 to 1.0) for use in draw-aware probability adjustments.
"""

from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

# Import calculate_draw_signal from draw_structural_adjustment
# (defined there to avoid circular imports)
from app.services.draw_structural_adjustment import calculate_draw_signal


def fetch_draw_structural_data_for_fixture(
    db: Session,
    fixture_id: int,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    league_id: Optional[int],
    lambda_home: float,
    lambda_away: float,
    market_odds: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Fetch all draw structural data for a fixture and compute draw signal.

    Parameters
    ----------
    db : Session
        Database session
    fixture_id : int
        Fixture ID
    home_team_id : Optional[int]
        Home team ID
    away_team_id : Optional[int]
        Away team ID
    league_id : Optional[int]
        League ID
    lambda_home : float
        Expected home goals (λ_h)
    lambda_away : float
        Expected away goals (λ_a)
    market_odds : Optional[Dict[str, float]]
        Market odds dict with keys 'home', 'draw', 'away'

    Returns
    -------
    dict
        {
            "draw_signal": float,  # Normalized draw signal [0.0, 1.0]
            "lambda_total": float,  # Total expected goals
            "market_draw_prob": Optional[float],
            "weather_factor": Optional[float],
            "h2h_draw_rate": Optional[float],
            "league_draw_rate": Optional[float],
        }
    """
    lambda_total = lambda_home + lambda_away

    # 1. Market draw probability
    market_draw_prob = None
    if market_odds and all(k in market_odds for k in ("home", "draw", "away")):
        try:
            total = 1.0 / market_odds["home"] + 1.0 / market_odds["draw"] + 1.0 / market_odds["away"]
            if total > 0:
                market_draw_prob = (1.0 / market_odds["draw"]) / total
        except (ZeroDivisionError, KeyError, TypeError):
            pass

    # 2. Weather factor
    weather_factor = None
    try:
        from app.db.models import MatchWeather
        weather = db.query(MatchWeather).filter(
            MatchWeather.fixture_id == fixture_id
        ).first()
        if weather and weather.weather_draw_index is not None:
            # Convert weather_draw_index (0.95-1.10) to factor (0.0-1.0)
            # Higher index = more extreme weather = higher factor
            weather_factor = min(1.0, max(0.0, (weather.weather_draw_index - 0.95) / 0.15))
    except Exception as e:
        logger.debug(f"Could not fetch weather data: {e}")

    # 3. H2H draw rate
    h2h_draw_rate = None
    if home_team_id and away_team_id:
        try:
            from app.db.models import H2HDrawStats
            h2h = db.query(H2HDrawStats).filter(
                H2HDrawStats.team_home_id == home_team_id,
                H2HDrawStats.team_away_id == away_team_id
            ).first()
            if h2h and h2h.matches_played >= 3:  # Minimum sample size
                h2h_draw_rate = h2h.draw_count / h2h.matches_played if h2h.matches_played > 0 else None
        except Exception as e:
            logger.debug(f"Could not fetch H2H data: {e}")

    # 4. League draw rate
    league_draw_rate = None
    if league_id:
        try:
            from app.db.models import League, LeagueDrawPrior
            # Check if this is INT league (international matches)
            league = db.query(League).filter(League.id == league_id).first()
            if league and league.code == 'INT':
                # For international matches, use default draw rate or calculate from all INT matches
                # Default: 0.25 (typical international draw rate)
                # Or calculate from historical INT matches if available
                try:
                    # Try to get draw rate from all INT matches
                    from app.db.models import Match
                    int_matches = db.query(Match).join(League).filter(
                        League.code == 'INT',
                        Match.result.isnot(None)
                    ).all()
                    if int_matches and len(int_matches) >= 10:  # Minimum sample size
                        draws = sum(1 for m in int_matches if m.result == 'D')
                        league_draw_rate = draws / len(int_matches)
                        logger.debug(f"Calculated INT league draw rate from {len(int_matches)} matches: {league_draw_rate:.3f}")
                    else:
                        # Use default for international matches
                        league_draw_rate = 0.25
                        logger.debug(f"Using default INT league draw rate: {league_draw_rate}")
                except Exception as e:
                    logger.debug(f"Could not calculate INT draw rate: {e}, using default 0.25")
                    league_draw_rate = 0.25
            else:
                # Normal league prior lookup
                league_prior = db.query(LeagueDrawPrior).filter(
                    LeagueDrawPrior.league_id == league_id
                ).order_by(LeagueDrawPrior.updated_at.desc()).first()
                
                if league_prior:
                    league_draw_rate = float(league_prior.draw_rate)
                elif league and hasattr(league, 'avg_draw_rate') and league.avg_draw_rate is not None:
                    # Fallback to league's avg_draw_rate if available
                    league_draw_rate = float(league.avg_draw_rate)
        except Exception as e:
            logger.debug(f"Could not fetch league draw rate: {e}")

    # Calculate draw signal
    draw_signal = calculate_draw_signal(
        lambda_total=lambda_total,
        market_draw_prob=market_draw_prob,
        weather_factor=weather_factor,
        h2h_draw_rate=h2h_draw_rate,
        league_draw_rate=league_draw_rate,
    )

    return {
        "draw_signal": draw_signal,
        "lambda_total": lambda_total,
        "market_draw_prob": market_draw_prob,
        "weather_factor": weather_factor,
        "h2h_draw_rate": h2h_draw_rate,
        "league_draw_rate": league_draw_rate,
    }

