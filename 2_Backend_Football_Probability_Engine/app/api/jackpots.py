"""
FastAPI Router for Jackpot CRUD Operations
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Jackpot as JackpotModel, JackpotFixture, SavedJackpotTemplate
from app.schemas.jackpot import Jackpot, ApiResponse, PaginatedResponse
from app.schemas.prediction import FixtureInput, MarketOdds
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel
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


# ============================================================================
# SAVED JACKPOT TEMPLATES ENDPOINTS (MUST BE BEFORE /{jackpot_id} ROUTE)
# ============================================================================

class SaveTemplateRequest(BaseModel):
    """Request to save a fixture list as a template"""
    name: str
    description: Optional[str] = None
    fixtures: List[FixtureInput]


@router.post("/templates", response_model=ApiResponse)
async def save_template(
    request: SaveTemplateRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Save a fixture list as a reusable template"""
    try:
        # Validate fixtures
        if not request.fixtures or len(request.fixtures) == 0:
            raise HTTPException(status_code=400, detail="At least one fixture is required")
        
        if len(request.fixtures) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 fixtures allowed")
        
        # Convert fixtures to JSON
        fixtures_json = [
            {
                "id": f.id,
                "homeTeam": f.homeTeam,
                "awayTeam": f.awayTeam,
                "odds": f.odds.dict() if f.odds else None,
                "matchDate": f.matchDate,
                "league": f.league,
            }
            for f in request.fixtures
        ]
        
        # Create template
        template = SavedJackpotTemplate(
            user_id="anonymous",  # TODO: Get from auth
            name=request.name,
            description=request.description,
            fixtures=fixtures_json,
            fixture_count=len(request.fixtures)
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return ApiResponse(
            data={
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "fixtureCount": template.fixture_count,
                "createdAt": template.created_at.isoformat(),
            },
            success=True,
            message="Template saved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=ApiResponse)
async def get_templates(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all saved templates for the current user"""
    try:
        user_id = "anonymous"  # TODO: Get from auth
        
        templates = db.query(SavedJackpotTemplate).filter(
            SavedJackpotTemplate.user_id == user_id
        ).order_by(SavedJackpotTemplate.created_at.desc()).limit(limit).all()
        
        return ApiResponse(
            data={
                "templates": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "fixtureCount": t.fixture_count,
                        "createdAt": t.created_at.isoformat(),
                        "updatedAt": t.updated_at.isoformat(),
                    }
                    for t in templates
                ],
                "total": len(templates)
            },
            success=True
        )
    except Exception as e:
        logger.error(f"Error fetching templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=ApiResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific template with its fixtures"""
    try:
        user_id = "anonymous"  # TODO: Get from auth
        
        template = db.query(SavedJackpotTemplate).filter(
            SavedJackpotTemplate.id == template_id,
            SavedJackpotTemplate.user_id == user_id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return ApiResponse(
            data={
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "fixtures": template.fixtures,
                "fixtureCount": template.fixture_count,
                "createdAt": template.created_at.isoformat(),
                "updatedAt": template.updated_at.isoformat(),
            },
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}", response_model=ApiResponse)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Delete a saved template"""
    try:
        user_id = "anonymous"  # TODO: Get from auth
        
        template = db.query(SavedJackpotTemplate).filter(
            SavedJackpotTemplate.id == template_id,
            SavedJackpotTemplate.user_id == user_id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        db.delete(template)
        db.commit()
        
        return ApiResponse(
            data={"id": template_id},
            success=True,
            message="Template deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/calculate", response_model=ApiResponse)
async def calculate_from_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Create a jackpot from a template and calculate probabilities"""
    try:
        user_id = "anonymous"  # TODO: Get from auth
        
        # Get template
        template = db.query(SavedJackpotTemplate).filter(
            SavedJackpotTemplate.id == template_id,
            SavedJackpotTemplate.user_id == user_id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Convert template fixtures to FixtureInput format
        fixtures = []
        for f in template.fixtures:
            fixtures.append(FixtureInput(
                id=f.get("id", ""),
                homeTeam=f["homeTeam"],
                awayTeam=f["awayTeam"],
                odds=MarketOdds(**f["odds"]) if f.get("odds") else None,
                matchDate=f.get("matchDate"),
                league=f.get("league"),
            ))
        
        # Create jackpot using existing endpoint logic
        jackpot_id = f"JK-{int(datetime.now().timestamp())}"
        jackpot = JackpotModel(
            jackpot_id=jackpot_id,
            user_id=user_id,
            status="draft",
            model_version="v2.4.1",
            name=template.name  # Use template name
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
                "name": jackpot.name,
                "fixtures": [
                    {
                        "id": f.get("id", ""),
                        "homeTeam": f["homeTeam"],
                        "awayTeam": f["awayTeam"],
                        "odds": f.get("odds")
                    }
                    for f in template.fixtures
                ],
                "createdAt": jackpot.created_at.isoformat(),
                "modelVersion": jackpot.model_version,
                "status": jackpot.status
            },
            success=True,
            message="Jackpot created from template successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating jackpot from template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


class CreateJackpotRequest(BaseModel):
    """Request body for creating a jackpot"""
    fixtures: List[FixtureInput]
    jackpot_id: Optional[str] = None  # Optional: specify jackpot ID, otherwise auto-generated


@router.post("", response_model=ApiResponse)
async def create_jackpot(
    request: CreateJackpotRequest,
    db: Session = Depends(get_db)
):
    """Create a new jackpot"""
    try:
        fixtures = request.fixtures
        
        if not fixtures:
            raise HTTPException(status_code=400, detail="At least one fixture is required")
        
        logger.info(f"Creating jackpot with {len(fixtures)} fixtures")
        
        # Validate fixtures
        for idx, fixture in enumerate(fixtures):
            if not fixture.homeTeam or len(fixture.homeTeam.strip()) < 2:
                raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: Invalid home team name")
            if not fixture.awayTeam or len(fixture.awayTeam.strip()) < 2:
                raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: Invalid away team name")
            if fixture.odds:
                if fixture.odds.home < 1.01 or fixture.odds.home > 100:
                    raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: Invalid home odds")
                if fixture.odds.draw < 1.01 or fixture.odds.draw > 100:
                    raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: Invalid draw odds")
                if fixture.odds.away < 1.01 or fixture.odds.away > 100:
                    raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: Invalid away odds")
        
        # Create jackpot record
        # Use provided jackpot_id or auto-generate one
        if request.jackpot_id:
            # Check if jackpot_id already exists
            existing = db.query(JackpotModel).filter(
                JackpotModel.jackpot_id == request.jackpot_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Jackpot ID {request.jackpot_id} already exists"
                )
            jackpot_id = request.jackpot_id
        else:
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
        data={"jackpot_id": jackpot.jackpot_id, "status": jackpot.status},
        success=True,
        message="Jackpot submitted successfully"
    )
    
    return ApiResponse(
        data={
            "id": jackpot.jackpot_id,
            "status": jackpot.status
        },
        success=True,
        message="Jackpot submitted successfully"
    )

