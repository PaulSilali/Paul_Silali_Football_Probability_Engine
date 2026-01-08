"""
Admin API endpoints for system maintenance and configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.session import get_db
from app.services.league_statistics import LeagueStatisticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/leagues/update-statistics")
def update_league_statistics(
    league_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update league statistics (avg_draw_rate, home_advantage) from match data.
    
    Args:
        league_code: Optional league code to update specific league.
                     If None, updates all leagues.
    
    Returns:
        Status message with update count
    """
    try:
        service = LeagueStatisticsService(db)
        
        if league_code:
            updated = service.update_league_by_code(league_code)
            if updated:
                return {
                    "status": "success",
                    "message": f"Updated statistics for league {league_code}",
                    "league_code": league_code
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"League {league_code} not found or has no matches"
                )
        else:
            count = service.update_all_leagues()
            return {
                "status": "success",
                "message": f"Updated statistics for {count} leagues",
                "updated_count": count
            }
    except Exception as e:
        logger.error(f"Error updating league statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update league statistics: {str(e)}"
        )


@router.get("/leagues/statistics")
def get_league_statistics(
    league_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get current league statistics.
    
    Args:
        league_code: Optional league code to get specific league.
                     If None, returns all leagues.
    
    Returns:
        League statistics data
    """
    from app.db.models import League
    
    query = db.query(League)
    
    if league_code:
        query = query.filter(League.code == league_code)
    
    leagues = query.all()
    
    if not leagues:
        raise HTTPException(
            status_code=404,
            detail=f"No leagues found" + (f" for code {league_code}" if league_code else "")
        )
    
    return {
        "leagues": [
            {
                "id": league.id,
                "code": league.code,
                "name": league.name,
                "country": league.country,
                "avg_draw_rate": league.avg_draw_rate,
                "home_advantage": league.home_advantage,
                "is_active": league.is_active
            }
            for league in leagues
        ]
    }

