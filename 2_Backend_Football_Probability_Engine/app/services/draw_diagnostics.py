"""
Draw Diagnostics Service

Provides league-level draw statistics for diagnostics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Match, MatchResult, League
from typing import Optional, Dict


def league_draw_stats(
    db: Session,
    league_code: str,
    season: Optional[str] = None
) -> Dict:
    """
    Get draw statistics for a league/season.
    """
    query = db.query(Match).filter(Match.league_code == league_code)
    
    if season:
        query = query.filter(Match.season == season)
    
    matches = query.filter(Match.result.isnot(None)).all()
    
    if not matches:
        return {
            "league": league_code,
            "season": season,
            "drawRate": 0.0,
            "totalMatches": 0,
            "draws": 0
        }
    
    total = len(matches)
    draws = sum(1 for m in matches if m.result == MatchResult.DRAW)
    draw_rate = draws / total if total > 0 else 0.0
    
    return {
        "league": league_code,
        "season": season,
        "drawRate": round(draw_rate, 3),
        "totalMatches": total,
        "draws": draws
    }

