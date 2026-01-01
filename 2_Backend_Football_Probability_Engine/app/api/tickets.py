"""
Ticket Generation API Endpoints

Provides endpoints for generating jackpot tickets with draw constraints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.db.session import get_db
from app.services.ticket_generation_service import TicketGenerationService
from app.api.probabilities import calculate_probabilities
from app.db.models import Jackpot as JackpotModel, JackpotFixture
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


class GenerateTicketsRequest(BaseModel):
    jackpot_id: str
    set_keys: List[str] = ["B"]
    n_tickets: Optional[int] = None
    league_code: Optional[str] = "DEFAULT"


@router.post("/generate")
async def generate_tickets(
    request: GenerateTicketsRequest,
    db: Session = Depends(get_db)
):
    """
    Generate jackpot tickets with draw constraints and H2H-aware eligibility.
    """
    try:
        # Get jackpot and fixtures
        jackpot = db.query(JackpotModel).filter(
            JackpotModel.jackpot_id == request.jackpot_id
        ).first()
        if not jackpot:
            raise HTTPException(status_code=404, detail=f"Jackpot {request.jackpot_id} not found")
        
        # Get probabilities for the jackpot
        prob_response = await calculate_probabilities(request.jackpot_id, db)
        # calculate_probabilities returns a dict directly, not ApiResponse
        fixtures_data = prob_response.get("fixtures", [])
        probability_sets = prob_response.get("probabilitySets", {})
        
        if not fixtures_data:
            raise HTTPException(status_code=400, detail="No fixtures found for jackpot")
        
        # Get jackpot fixtures from database to get team IDs
        jackpot_fixtures = db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot.id
        ).order_by(JackpotFixture.match_order).all()
        
        # Prepare fixtures (without probabilities - will be set per set)
        fixtures = []
        for idx, fixture_data in enumerate(fixtures_data):
            # Match with database fixture to get team IDs
            db_fixture = jackpot_fixtures[idx] if idx < len(jackpot_fixtures) else None
            
            fixtures.append({
                "id": fixture_data.get("id", str(idx)),
                "home_team": fixture_data.get("homeTeam", ""),
                "away_team": fixture_data.get("awayTeam", ""),
                "home_team_id": db_fixture.home_team_id if db_fixture else None,
                "away_team_id": db_fixture.away_team_id if db_fixture else None,
                "league_id": db_fixture.league_id if db_fixture else None,
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
        
        return {
            "success": True,
            "data": bundle
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate tickets: {str(e)}")


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

