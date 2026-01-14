"""
Team Validation API Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.team_resolver import validate_team_name, search_teams
from app.db.models import Model, ModelStatus
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/validation", tags=["validation"])


class TeamValidationRequest(BaseModel):
    teamName: str
    leagueId: Optional[int] = None
    checkTraining: Optional[bool] = False  # New: Check model training status


class TeamValidationResponse(BaseModel):
    isValid: bool
    normalizedName: Optional[str] = None
    confidence: Optional[float] = None
    suggestions: Optional[List[str]] = None
    isTrained: Optional[bool] = None  # New: Whether team has model training data
    teamId: Optional[int] = None  # New: Team ID if found
    strengthSource: Optional[str] = None  # New: "model", "database", or "default"


@router.post("/team")
async def validate_team(
    request: TeamValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate team name and return suggestions if not found
    
    If checkTraining=True, also checks if team has model training data.
    
    Matches frontend API contract
    """
    result = validate_team_name(db, request.teamName, request.leagueId)
    
    response_data = {
        "isValid": result["isValid"],
        "success": True
    }
    
    if result["isValid"]:
        team = result.get("team")
        team_id = team.id if team else None
        
        response_data["data"] = {
            "isValid": True,
            "normalizedName": result["normalizedName"],
            "confidence": result.get("confidence", 1.0),
            "teamId": team_id
        }
        
        # Check model training status if requested
        if request.checkTraining and team_id:
            training_status = check_team_training_status(db, team_id)
            response_data["data"].update({
                "isTrained": training_status["isTrained"],
                "strengthSource": training_status["strengthSource"]
            })
    else:
        response_data["data"] = {
            "isValid": False,
            "suggestions": result["suggestions"]
        }
    
    return response_data


def check_team_training_status(db: Session, team_id: int) -> Dict:
    """
    Check if a team has model training data (team strengths)
    
    Returns:
        Dict with:
        - isTrained: bool - Whether team has training data
        - strengthSource: str - "model", "database", or "default"
    """
    # Get active Poisson model (where team_strengths are stored)
    poisson_model = db.query(Model).filter(
        Model.model_type == "poisson",
        Model.status == ModelStatus.active
    ).order_by(Model.training_completed_at.desc()).first()
    
    if not poisson_model or not poisson_model.model_weights:
        return {
            "isTrained": False,
            "strengthSource": "default"
        }
    
    # Check if team_id exists in model's team_strengths
    team_strengths = poisson_model.model_weights.get('team_strengths', {})
    
    # Handle both int and string keys
    is_trained = (
        team_id in team_strengths or 
        str(team_id) in team_strengths
    )
    
    if is_trained:
        return {
            "isTrained": True,
            "strengthSource": "model"
        }
    
    # Check if team has database ratings (fallback)
    from app.db.models import Team
    team = db.query(Team).filter(Team.id == team_id).first()
    if team and (team.attack_rating != 1.0 or team.defense_rating != 1.0):
        return {
            "isTrained": False,
            "strengthSource": "database"
        }
    
    return {
        "isTrained": False,
        "strengthSource": "default"
    }


@router.post("/team/batch")
async def validate_teams_batch(
    teams: List[TeamValidationRequest],
    db: Session = Depends(get_db)
):
    """
    Validate multiple teams at once, optionally checking training status
    
    Returns validation results for all teams
    """
    results = []
    for team_request in teams:
        result = validate_team_name(db, team_request.teamName, team_request.leagueId)
        
        team_data = {
            "teamName": team_request.teamName,
            "isValid": result["isValid"]
        }
        
        if result["isValid"]:
            team_data.update({
                "normalizedName": result["normalizedName"],
                "confidence": result.get("confidence", 1.0),
                "teamId": result.get("team", {}).id if result.get("team") else None
            })
            
            if team_request.checkTraining and result.get("team"):
                training_status = check_team_training_status(db, result["team"].id)
                team_data.update({
                    "isTrained": training_status["isTrained"],
                    "strengthSource": training_status["strengthSource"]
                })
        else:
            team_data["suggestions"] = result["suggestions"]
        
        results.append(team_data)
    
    return {
        "success": True,
        "data": results
    }


class TeamSearchRequest(BaseModel):
    query: str
    leagueId: Optional[int] = None
    limit: Optional[int] = 20  # More results for search


class TeamSearchResult(BaseModel):
    teamId: int
    name: str
    canonicalName: str
    leagueId: Optional[int] = None
    similarity: float


@router.post("/team/search")
async def search_team(
    request: TeamSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for teams with broader matching (lower threshold than validation)
    
    This is useful when a team is "not found" during validation but might exist
    with a different name or spelling. Uses lower similarity threshold (0.3 vs 0.7).
    
    Returns up to 20 matching teams sorted by similarity score.
    """
    if not request.query or len(request.query.strip()) < 2:
        return {
            "success": True,
            "data": []
        }
    
    # Use search_teams which has lower threshold (0.3) for broader matching
    matches = search_teams(
        db, 
        request.query.strip(), 
        request.leagueId, 
        limit=request.limit or 20
    )
    
    results = []
    for team, score in matches:
        results.append({
            "teamId": team.id,
            "name": team.name,
            "canonicalName": team.canonical_name,
            "leagueId": team.league_id,
            "similarity": round(score, 3)
        })
    
    return {
        "success": True,
        "data": results
    }

