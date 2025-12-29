"""
FastAPI Router for Jackpot CRUD Operations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Jackpot as JackpotModel, JackpotFixture
from app.schemas.jackpot import Jackpot, ApiResponse, PaginatedResponse
from app.schemas.prediction import FixtureInput
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jackpots", tags=["jackpots"])


@router.get("", response_model=PaginatedResponse)
async def get_jackpots(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """Get all jackpots with pagination"""
    offset = (page - 1) * page_size
    
    jackpots = db.query(JackpotModel).offset(offset).limit(page_size).all()
    total = db.query(JackpotModel).count()
    
    return PaginatedResponse(
        data=[{
            "id": j.jackpot_id,
            "name": j.name,
            "fixtures": [
                {
                    "id": str(f.id),
                    "homeTeam": f.home_team,
                    "awayTeam": f.away_team,
                    "odds": {
                        "home": f.odds_home,
                        "draw": f.odds_draw,
                        "away": f.odds_away
                    } if f.odds_home else None
                }
                for f in j.fixtures
            ],
            "createdAt": j.created_at.isoformat(),
            "modelVersion": j.model_version or "unknown",
            "status": j.status
        } for j in jackpots],
        total=total,
        page=page,
        pageSize=page_size
    )


@router.get("/{jackpot_id}", response_model=ApiResponse)
async def get_jackpot(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Get a single jackpot by ID"""
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    return ApiResponse(
        data={
            "id": jackpot.jackpot_id,
            "name": jackpot.name,
            "fixtures": [
                {
                    "id": str(f.id),
                    "homeTeam": f.home_team,
                    "awayTeam": f.away_team,
                    "odds": {
                        "home": f.odds_home,
                        "draw": f.odds_draw,
                        "away": f.odds_away
                    } if f.odds_home else None
                }
                for f in jackpot.fixtures
            ],
            "createdAt": jackpot.created_at.isoformat(),
            "modelVersion": jackpot.model_version or "unknown",
            "status": jackpot.status
        },
        success=True
    )


@router.post("", response_model=ApiResponse)
async def create_jackpot(
    fixtures: List[FixtureInput],
    db: Session = Depends(get_db)
):
    """Create a new jackpot"""
    try:
        # Create jackpot record
        jackpot_id = f"JK-{int(datetime.now().timestamp())}"
        jackpot = JackpotModel(
            jackpot_id=jackpot_id,
            user_id="anonymous",  # TODO: Get from auth
            status="draft",
            model_version="v2.4.1"
        )
        db.add(jackpot)
        db.flush()
        
        # Create fixtures
        for idx, fixture in enumerate(fixtures):
            jackpot_fixture = JackpotFixture(
                jackpot_id=jackpot.id,
                match_order=idx + 1,
                home_team=fixture.homeTeam,
                away_team=fixture.awayTeam,
                odds_home=fixture.odds.home if fixture.odds else 2.0,
                odds_draw=fixture.odds.draw if fixture.odds else 3.0,
                odds_away=fixture.odds.away if fixture.odds else 2.5
            )
            db.add(jackpot_fixture)
        
        db.commit()
        
        return ApiResponse(
            data={
                "id": jackpot.jackpot_id,
                "name": None,
                "fixtures": [
                    {
                        "id": fixture.id,
                        "homeTeam": fixture.homeTeam,
                        "awayTeam": fixture.awayTeam,
                        "odds": fixture.odds.dict() if fixture.odds else None
                    }
                    for fixture in fixtures
                ],
                "createdAt": jackpot.created_at.isoformat(),
                "modelVersion": jackpot.model_version,
                "status": jackpot.status
            },
            success=True,
            message="Jackpot created successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating jackpot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{jackpot_id}", response_model=ApiResponse)
async def update_jackpot(
    jackpot_id: str,
    fixtures: List[FixtureInput],
    db: Session = Depends(get_db)
):
    """Update an existing jackpot"""
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    try:
        # Delete existing fixtures
        db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot.id
        ).delete()
        
        # Create new fixtures
        for idx, fixture in enumerate(fixtures):
            jackpot_fixture = JackpotFixture(
                jackpot_id=jackpot.id,
                match_order=idx + 1,
                home_team=fixture.homeTeam,
                away_team=fixture.awayTeam,
                odds_home=fixture.odds.home if fixture.odds else 2.0,
                odds_draw=fixture.odds.draw if fixture.odds else 3.0,
                odds_away=fixture.odds.away if fixture.odds else 2.5
            )
            db.add(jackpot_fixture)
        
        db.commit()
        
        return ApiResponse(
            data={
                "id": jackpot.jackpot_id,
                "name": jackpot.name,
                "fixtures": [
                    {
                        "id": fixture.id,
                        "homeTeam": fixture.homeTeam,
                        "awayTeam": fixture.awayTeam,
                        "odds": fixture.odds.dict() if fixture.odds else None
                    }
                    for fixture in fixtures
                ],
                "createdAt": jackpot.created_at.isoformat(),
                "modelVersion": jackpot.model_version,
                "status": jackpot.status
            },
            success=True,
            message="Jackpot updated successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating jackpot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{jackpot_id}")
async def delete_jackpot(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Delete a jackpot"""
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    try:
        db.delete(jackpot)
        db.commit()
        return {"success": True, "message": "Jackpot deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting jackpot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{jackpot_id}/submit", response_model=ApiResponse)
async def submit_jackpot(
    jackpot_id: str,
    db: Session = Depends(get_db)
):
    """Submit a jackpot for probability calculation"""
    jackpot = db.query(JackpotModel).filter(
        JackpotModel.jackpot_id == jackpot_id
    ).first()
    
    if not jackpot:
        raise HTTPException(status_code=404, detail="Jackpot not found")
    
    jackpot.status = "submitted"
    db.commit()
    
    return ApiResponse(
        data={
            "id": jackpot.jackpot_id,
            "status": jackpot.status
        },
        success=True,
        message="Jackpot submitted successfully"
    )

