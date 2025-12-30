"""
Team Search API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.team_resolver import search_teams, suggest_team_names
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/search")
async def search_teams_endpoint(
    q: str = Query(..., min_length=2, description="Search query"),
    league_id: Optional[int] = Query(None, description="Filter by league ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Search for teams by name
    
    Returns teams matching the query with similarity scores
    """
    matches = search_teams(db, q, league_id, limit)
    
    return {
        "data": [
            {
                "id": team.id,
                "name": team.name,
                "canonicalName": team.canonical_name,
                "leagueId": team.league_id,
                "similarity": float(score)
            }
            for team, score in matches
        ],
        "success": True,
        "query": q,
        "count": len(matches)
    }


@router.get("/suggestions")
async def get_team_suggestions(
    q: str = Query(..., min_length=1),
    league_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get team name suggestions for autocomplete"""
    suggestions = suggest_team_names(db, q, league_id, limit)
    
    return {
        "data": suggestions,
        "success": True
    }


@router.get("/all")
async def get_all_teams(
    league_id: Optional[int] = Query(None, description="Filter by league ID"),
    db: Session = Depends(get_db)
):
    """
    Get all teams from database
    
    Useful for team mapping interface to show all available teams
    """
    from app.db.models import Team
    
    query = db.query(Team)
    if league_id:
        query = query.filter(Team.league_id == league_id)
    
    teams = query.order_by(Team.canonical_name.asc()).all()
    
    return {
        "data": [
            {
                "id": team.id,
                "name": team.name,
                "canonicalName": team.canonical_name,
                "leagueId": team.league_id,
                "leagueName": team.league.name if team.league else None
            }
            for team in teams
        ],
        "success": True,
        "count": len(teams)
    }
