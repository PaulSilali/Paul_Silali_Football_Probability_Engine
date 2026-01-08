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
        probability_sets_raw = prob_data.get("probabilitySets", {})
        
        if not fixtures_data:
            raise HTTPException(status_code=400, detail="No fixtures found for jackpot")
        
        # Validate set_keys - A-J are valid
        valid_set_keys = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J"}
        set_keys = [key.upper() for key in request.set_keys if key.upper() in valid_set_keys]
        
        # Log if invalid keys were filtered out
        invalid_keys = [key for key in request.set_keys if key.upper() not in valid_set_keys]
        if invalid_keys:
            logger.warning(f"Filtered out invalid set_keys: {invalid_keys}. Valid keys are: A, B, C, D, E, F, G, H, I, J")
        
        if not set_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid set_keys: {request.set_keys}. Valid keys are: A, B, C, D, E, F, G, H, I, J"
            )
        
        # Filter probability_sets to only include valid set keys
        invalid_prob_keys = [key for key in probability_sets_raw.keys() if key.upper() not in valid_set_keys]
        if invalid_prob_keys:
            logger.warning(f"Filtered out invalid probability set keys: {invalid_prob_keys}")
        
        probability_sets = {
            key: value for key, value in probability_sets_raw.items() 
            if key.upper() in valid_set_keys
        }
        
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
        
        # Fetch opening odds from odds_movement table for late-shock detection
        from app.db.models import OddsMovement, League
        fixture_ids = [f.id for f in jackpot_fixtures]
        odds_movements = db.query(OddsMovement).filter(
            OddsMovement.fixture_id.in_(fixture_ids)
        ).all()
        odds_movement_map = {om.fixture_id: om for om in odds_movements}
        
        # Get league code from request or first fixture
        league_code = request.league_code
        if not league_code or league_code == "DEFAULT":
            if fixtures_data and fixtures_data[0].get("league_id"):
                league = db.query(League).filter(League.id == fixtures_data[0]["league_id"]).first()
                if league:
                    league_code = league.code
            else:
                league_code = "DEFAULT"  # Ensure it has a value
        
        # Prepare fixtures (without probabilities - will be set per set)
        fixtures = []
        for idx, fixture_data in enumerate(fixtures_data):
            # Match with database fixture to get team IDs
            db_fixture_data = fixture_cache[idx] if idx < len(fixture_cache) else {}
            db_fixture = jackpot_fixtures[idx] if idx < len(jackpot_fixtures) else None
            
            # Get opening odds from odds_movement table
            odds_open = None
            if db_fixture:
                odds_movement = odds_movement_map.get(db_fixture.id)
                if odds_movement and odds_movement.draw_open:
                    # Reconstruct opening odds (we only have draw_open, estimate home/away)
                    current_odds = fixture_data.get("odds", {})
                    if current_odds.get("draw"):
                        # Estimate opening odds based on draw movement
                        draw_ratio = odds_movement.draw_open / current_odds.get("draw", odds_movement.draw_open)
                        odds_open = {
                            "home": current_odds.get("home", 2.0) * draw_ratio if current_odds.get("home") else None,
                            "draw": odds_movement.draw_open,
                            "away": current_odds.get("away", 2.0) * draw_ratio if current_odds.get("away") else None
                        }
            
            # Get kickoff timestamp (combine match_date from jackpot with match_time if available)
            kickoff_ts = None
            if db_fixture:
                from datetime import datetime, time, date
                # Try to get kickoff_date from jackpot
                kickoff_date = getattr(jackpot, 'kickoff_date', None)
                if not kickoff_date:
                    # Fallback to created_at date
                    kickoff_date = jackpot.created_at.date() if hasattr(jackpot, 'created_at') and jackpot.created_at else date.today()
                
                # If match_time available, combine; otherwise use default time
                match_time = getattr(db_fixture, 'match_time', None) if hasattr(db_fixture, 'match_time') else None
                if match_time:
                    kickoff_datetime = datetime.combine(kickoff_date, match_time)
                else:
                    kickoff_datetime = datetime.combine(kickoff_date, time(15, 0))  # Default 3 PM
                kickoff_ts = int(kickoff_datetime.timestamp())
            
            # Get draw structural components for correlation scoring
            draw_signal = fixture_data.get("drawStructuralComponents", {}).get("draw_signal", 0.5)
            lambda_total = fixture_data.get("drawStructuralComponents", {}).get("lambda_total", 2.5)
            
            fixtures.append({
                "id": fixture_data.get("id", str(idx)),
                "home_team": fixture_data.get("homeTeam", ""),
                "away_team": fixture_data.get("awayTeam", ""),
                "home_team_id": db_fixture_data.get('home_team_id'),
                "away_team_id": db_fixture_data.get('away_team_id'),
                "league_id": db_fixture_data.get('league_id'),
                "probabilities": {"home": 0.33, "draw": 0.33, "away": 0.33},  # Placeholder
                "odds": fixture_data.get("odds", {}),
                "odds_open": odds_open,  # NEW: Opening odds for late-shock detection
                "kickoff_ts": kickoff_ts,  # NEW: Kickoff timestamp for correlation
                "draw_signal": draw_signal,  # NEW: Draw signal for correlation
                "lambda_total": lambda_total  # NEW: Total expected goals for correlation
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
            set_keys=set_keys,  # Use validated set_keys
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
        # Format: {"ticket-0": {"setKey": "B", "1": "1", "2": "X", ...}, "ticket-1": {...}}
        # This preserves all tickets even if they share the same setKey
        selections = {}
        
        for ticket_idx, ticket in enumerate(request.tickets):
            set_key = ticket.get("setKey", "B")
            picks = ticket.get("picks", [])
            ticket_key = f"ticket-{ticket_idx}"
            
            # Store ticket metadata and picks
            selections[ticket_key] = {
                "setKey": set_key,
                **{str(idx + 1): pick for idx, pick in enumerate(picks)}  # Convert picks array to fixture selections
            }
        
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

