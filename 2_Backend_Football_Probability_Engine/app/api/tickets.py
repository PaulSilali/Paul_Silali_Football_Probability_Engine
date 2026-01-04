"""
Ticket Generation API Endpoints

Provides endpoints for generating jackpot tickets with draw constraints.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.db.session import get_db
from app.services.ticket_generation_service import TicketGenerationService
from app.api.probabilities import calculate_probabilities
from app.db.models import Jackpot as JackpotModel, JackpotFixture, SavedProbabilityResult, Model, ModelStatus
from app.schemas.jackpot import ApiResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


class GenerateTicketsRequest(BaseModel):
    jackpot_id: str
    set_keys: List[str] = ["B"]
    n_tickets: Optional[int] = None
    league_code: Optional[str] = "DEFAULT"


class SaveTicketsRequest(BaseModel):
    jackpot_id: str
    name: str
    description: Optional[str] = None
    tickets: List[Dict]  # List of ticket objects with picks, setKey, etc.


@router.post("/generate", response_model=ApiResponse)
async def generate_tickets(
    request: GenerateTicketsRequest,
    db: Session = Depends(get_db)
):
    """
    Generate jackpot tickets with draw constraints and H2H-aware eligibility.
    """
    try:
        # Ensure clean transaction state
        db.rollback()
        
        # Get jackpot and fixtures
        jackpot = db.query(JackpotModel).filter(
            JackpotModel.jackpot_id == request.jackpot_id
        ).first()
        if not jackpot:
            raise HTTPException(status_code=404, detail=f"Jackpot {request.jackpot_id} not found")
        
        # Extract jackpot.id immediately to avoid lazy loading after calculate_probabilities
        # calculate_probabilities may commit/rollback transactions, which would expire the jackpot object
        jackpot_id = jackpot.id
        
        # Get probabilities for the jackpot
        prob_response = await calculate_probabilities(request.jackpot_id, db)
        # calculate_probabilities returns ApiResponse, extract data
        if not prob_response.success or not prob_response.data:
            raise HTTPException(status_code=500, detail="Failed to calculate probabilities")
        
        prob_data = prob_response.data
        fixtures_data = prob_data.get("fixtures", [])
        probability_sets = prob_data.get("probabilitySets", {})
        
        if not fixtures_data:
            raise HTTPException(status_code=400, detail="No fixtures found for jackpot")
        
        # Rollback to ensure clean transaction state after calculate_probabilities
        # calculate_probabilities may have aborted the transaction
        try:
            db.rollback()
        except Exception:
            pass  # Ignore if already rolled back
        
        # Get jackpot fixtures from database to get team IDs
        # Use cached jackpot_id instead of jackpot.id to avoid lazy loading
        jackpot_fixtures = db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot_id
        ).order_by(JackpotFixture.match_order).all()
        
        # Extract fixture attributes immediately to avoid lazy loading issues
        # Store as dictionaries with primitive values
        fixture_cache = []
        for db_fixture in jackpot_fixtures:
            fixture_cache.append({
                'home_team_id': db_fixture.home_team_id,
                'away_team_id': db_fixture.away_team_id,
                'league_id': db_fixture.league_id,
            })
        
        # Prepare fixtures (without probabilities - will be set per set)
        fixtures = []
        for idx, fixture_data in enumerate(fixtures_data):
            # Match with database fixture to get team IDs
            db_fixture_data = fixture_cache[idx] if idx < len(fixture_cache) else {}
            
            fixtures.append({
                "id": fixture_data.get("id", str(idx)),
                "home_team": fixture_data.get("homeTeam", ""),
                "away_team": fixture_data.get("awayTeam", ""),
                "home_team_id": db_fixture_data.get('home_team_id'),
                "away_team_id": db_fixture_data.get('away_team_id'),
                "league_id": db_fixture_data.get('league_id'),
                "probabilities": {"home": 0.33, "draw": 0.33, "away": 0.33},  # Placeholder
                "odds": fixture_data.get("odds", {})
            })
        
        # Determine league code from fixtures if not provided
        league_code = request.league_code
        if not league_code or league_code == "DEFAULT":
            # Try to infer from first fixture
            if fixtures and fixtures[0].get("league_id"):
                # Would need to query league table - for now use DEFAULT
                league_code = "DEFAULT"
        
        # Generate tickets with probability sets
        service = TicketGenerationService(db)
        bundle = service.generate_bundle(
            fixtures=fixtures,
            league_code=league_code,
            set_keys=request.set_keys,
            n_tickets=request.n_tickets,
            probability_sets=probability_sets
        )
        
        return ApiResponse(
            success=True,
            message=f"Generated {len(bundle.get('tickets', []))} tickets",
            data=bundle
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate tickets: {str(e)}")


@router.post("/save", response_model=ApiResponse)
async def save_tickets(
    request: SaveTicketsRequest,
    db: Session = Depends(get_db)
):
    """
    Save generated tickets for a jackpot.
    
    Args:
        request: SaveTicketsRequest with jackpot_id, name, description, and tickets list
    
    Returns:
        ApiResponse with saved ticket data
    """
    try:
        # Validate required fields
        if not request.name:
            raise HTTPException(status_code=400, detail="Name is required")
        
        if not request.tickets or len(request.tickets) == 0:
            raise HTTPException(status_code=400, detail="At least one ticket is required")
        
        # Get active model version
        model = db.query(Model).filter(Model.status == ModelStatus.active).first()
        model_version = model.version if model else None
        
        # Convert tickets to selections format (compatible with SavedProbabilityResult)
        # Format: {"A": {"1": "1", "2": "X", ...}, "B": {...}}
        selections = {}
        
        for ticket in request.tickets:
            set_key = ticket.get("setKey", "B")
            picks = ticket.get("picks", [])
            
            if set_key not in selections:
                selections[set_key] = {}
            
            # Convert picks array to fixture selections
            for idx, pick in enumerate(picks):
                fixture_id = str(idx + 1)  # Use 1-indexed fixture numbers
                selections[set_key][fixture_id] = pick
        
        # Count total fixtures from first ticket
        total_fixtures = len(request.tickets[0].get("picks", [])) if request.tickets else 0
        
        # Create saved result
        saved_result = SavedProbabilityResult(
            jackpot_id=request.jackpot_id,
            user_id=None,  # TODO: Get from auth context if available
            name=request.name,
            description=request.description,
            selections=selections,
            actual_results=None,
            scores=None,
            model_version=model_version,
            total_fixtures=total_fixtures
        )
        
        db.add(saved_result)
        db.commit()
        db.refresh(saved_result)
        
        logger.info(f"Saved tickets: ID={saved_result.id}, name={saved_result.name}, tickets={len(request.tickets)}")
        
        return ApiResponse(
            success=True,
            message=f"Saved {len(request.tickets)} tickets successfully",
            data={
                "id": saved_result.id,
                "name": saved_result.name,
                "description": saved_result.description,
                "jackpotId": saved_result.jackpot_id,
                "tickets": request.tickets,
                "modelVersion": saved_result.model_version,
                "totalFixtures": saved_result.total_fixtures,
                "createdAt": saved_result.created_at.isoformat(),
                "updatedAt": saved_result.updated_at.isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save tickets: {str(e)}")


@router.get("/draw-diagnostics")
async def draw_diagnostics(
    league: str,
    season: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get draw diagnostics for a league/season.
    """
    from app.services.draw_diagnostics import league_draw_stats
    
    try:
        stats = league_draw_stats(db, league, season or "2023-24")
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting draw diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get draw diagnostics: {str(e)}")

