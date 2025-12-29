"""
Team Validation API Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.team_resolver import validate_team_name
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/validation", tags=["validation"])


class TeamValidationRequest(BaseModel):
    teamName: str
    leagueId: Optional[int] = None


@router.post("/team")
async def validate_team(
    request: TeamValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate team name and return suggestions if not found
    
    Matches frontend API contract
    """
    result = validate_team_name(db, request.teamName, request.leagueId)
    
    if result["isValid"]:
        return {
            "data": {
                "isValid": True,
                "normalizedName": result["normalizedName"],
                "confidence": result.get("confidence", 1.0)
            },
            "success": True
        }
    else:
        return {
            "data": {
                "isValid": False,
                "suggestions": result["suggestions"]
            },
            "success": True
        }

