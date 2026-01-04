"""
Head-to-Head (H2H) Statistics Service

Computes and retrieves historical match statistics between team pairs.
Used for draw eligibility in ticket construction, NOT for probability modification.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, Dict
from datetime import datetime, date
from app.db.models import TeamH2HStats, Match, Team, League, MatchResult


def get_h2h_stats(
    db: Session,
    team_home_id: int,
    team_away_id: int
) -> Optional[Dict]:
    """
    Get H2H statistics for a team pair.
    
    Returns None if insufficient data (< 8 meetings or > 5 years old).
    """
    # Check if stats exist in cache table
    h2h = db.query(TeamH2HStats).filter(
        and_(
            TeamH2HStats.team_home_id == team_home_id,
            TeamH2HStats.team_away_id == team_away_id
        )
    ).first()
    
    if h2h:
        # Check if data is still valid
        current_year = datetime.now().year
        last_year = h2h.last_meeting_date.year if h2h.last_meeting_date else 0
        
        if h2h.meetings >= 8 and (current_year - last_year) <= 5:
            return {
                "meetings": h2h.meetings,
                "draws": h2h.draws,
                "home_draws": h2h.home_draws,
                "away_draws": h2h.away_draws,
                "draw_rate": float(h2h.draw_rate),
                "home_draw_rate": float(h2h.home_draw_rate),
                "away_draw_rate": float(h2h.away_draw_rate),
                "league_draw_rate": float(h2h.league_draw_rate),
                "h2h_draw_index": float(h2h.h2h_draw_index),
                "last_meeting_date": h2h.last_meeting_date.isoformat() if h2h.last_meeting_date else None,
                "last_meeting_year": last_year
            }
    
    return None


def compute_h2h_stats(
    db: Session,
    team_home_id: int,
    team_away_id: int,
    league_id: Optional[int] = None
) -> Optional[Dict]:
    """
    Compute H2H statistics from match history.
    
    Only computes if >= 8 meetings and last meeting within 5 years.
    """
    # Get all matches between these teams (both directions)
    matches = db.query(Match).filter(
        or_(
            and_(Match.home_team_id == team_home_id, Match.away_team_id == team_away_id),
            and_(Match.home_team_id == team_away_id, Match.away_team_id == team_home_id)
        ),
        Match.result.isnot(None)  # Only completed matches
    ).order_by(Match.match_date.desc()).all()
    
    if len(matches) < 8:
        return None
    
    # Check if last meeting is within 5 years
    last_match = matches[0]
    if last_match.match_date:
        years_ago = (date.today() - last_match.match_date).days / 365.25
        if years_ago > 5:
            return None
    
    # Calculate statistics
    total_meetings = len(matches)
    total_draws = sum(1 for m in matches if m.result == MatchResult.D)
    home_draws = sum(1 for m in matches if m.result == MatchResult.D and m.home_team_id == team_home_id)
    away_draws = sum(1 for m in matches if m.result == MatchResult.D and m.home_team_id == team_away_id)
    
    draw_rate = total_draws / total_meetings if total_meetings > 0 else 0.0
    home_draw_rate = home_draws / sum(1 for m in matches if m.home_team_id == team_home_id) if any(m.home_team_id == team_home_id for m in matches) else 0.0
    away_draw_rate = away_draws / sum(1 for m in matches if m.home_team_id == team_away_id) if any(m.home_team_id == team_away_id for m in matches) else 0.0
    
    # Get league draw rate
    if league_id:
        league_matches = db.query(Match).filter(
            Match.league_id == league_id,
            Match.result.isnot(None)
        ).all()
        if league_matches:
            league_draws = sum(1 for m in league_matches if m.result == MatchResult.D)
            league_draw_rate = league_draws / len(league_matches)
        else:
            league_draw_rate = 0.27  # Default league draw rate
    else:
        league_draw_rate = 0.27  # Default
    
    h2h_draw_index = draw_rate / league_draw_rate if league_draw_rate > 0 else 1.0
    
    # Store in cache table
    h2h = db.query(TeamH2HStats).filter(
        and_(
            TeamH2HStats.team_home_id == team_home_id,
            TeamH2HStats.team_away_id == team_away_id
        )
    ).first()
    
    if h2h:
        # Update existing
        h2h.meetings = total_meetings
        h2h.draws = total_draws
        h2h.home_draws = home_draws
        h2h.away_draws = away_draws
        h2h.draw_rate = draw_rate
        h2h.home_draw_rate = home_draw_rate
        h2h.away_draw_rate = away_draw_rate
        h2h.league_draw_rate = league_draw_rate
        h2h.h2h_draw_index = h2h_draw_index
        h2h.last_meeting_date = last_match.match_date
        h2h.updated_at = datetime.now()
    else:
        # Create new
        h2h = TeamH2HStats(
            team_home_id=team_home_id,
            team_away_id=team_away_id,
            meetings=total_meetings,
            draws=total_draws,
            home_draws=home_draws,
            away_draws=away_draws,
            draw_rate=draw_rate,
            home_draw_rate=home_draw_rate,
            away_draw_rate=away_draw_rate,
            league_draw_rate=league_draw_rate,
            h2h_draw_index=h2h_draw_index,
            last_meeting_date=last_match.match_date
        )
        db.add(h2h)
    
    db.commit()
    
    return {
        "meetings": total_meetings,
        "draws": total_draws,
        "home_draws": home_draws,
        "away_draws": away_draws,
        "draw_rate": draw_rate,
        "home_draw_rate": home_draw_rate,
        "away_draw_rate": away_draw_rate,
        "league_draw_rate": league_draw_rate,
        "h2h_draw_index": h2h_draw_index,
        "last_meeting_date": last_match.match_date.isoformat() if last_match.match_date else None,
        "last_meeting_year": last_match.match_date.year if last_match.match_date else None
    }

