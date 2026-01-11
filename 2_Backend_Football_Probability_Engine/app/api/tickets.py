"""
Ticket Generation API Endpoints

Provides endpoints for generating jackpot tickets with draw constraints.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.services.ticket_generation_service import TicketGenerationService
from app.api.probabilities import calculate_probabilities
from app.db.models import Jackpot as JackpotModel, JackpotFixture, SavedProbabilityResult, Model, ModelStatus
from app.schemas.jackpot import ApiResponse
from datetime import datetime
import logging
import os
import re

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
        
        # Validate set_keys - A-M are valid (K, L, M are generated in frontend)
        valid_set_keys = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"}
        set_keys = [key.upper() for key in request.set_keys if key.upper() in valid_set_keys]
        
        # Log if invalid keys were filtered out
        invalid_keys = [key for key in request.set_keys if key.upper() not in valid_set_keys]
        if invalid_keys:
            logger.warning(f"Filtered out invalid set_keys: {invalid_keys}. Valid keys are: A, B, C, D, E, F, G, H, I, J, K, L, M")
        
        if not set_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid set_keys: {request.set_keys}. Valid keys are: A, B, C, D, E, F, G, H, I, J, K, L, M"
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


class AnalyzeTicketsRequest(BaseModel):
    tickets: List[Dict[str, Any]]  # List of tickets with picks, setKey, etc.
    actual_results: List[str]  # Actual results for each match ('1', 'X', '2')
    fixtures: List[Dict[str, Any]]  # Fixture information (teams, odds, etc.)
    ticket_performance: List[Dict[str, Any]]  # Performance metrics per ticket


@router.post("/analyze-performance", response_model=ApiResponse)
async def analyze_ticket_performance(
    request: AnalyzeTicketsRequest,
    db: Session = Depends(get_db)
):
    """
    Use LLM to analyze ticket performance and suggest improvements.
    
    Compares generated tickets against actual results and provides:
    - Pattern analysis (which sets performed best/worst)
    - Common mistakes identification
    - Suggestions for ticket enhancement
    - Recommendations for which sets to use/avoid
    """
    try:
        # Try importing OpenAI package first
        try:
            import openai
            from openai import OpenAI
            # Log version if available
            if hasattr(openai, '__version__'):
                logger.debug(f"OpenAI package version: {openai.__version__}")
        except ImportError as e:
            error_msg = (
                "LLM analysis not available: OpenAI package not installed.\n\n"
                "To install:\n"
                "1. Open terminal in the backend directory\n"
                "2. Run: pip install openai>=1.12.0\n"
                "Or run: install_openai.bat\n\n"
                f"Error details: {str(e)}"
            )
            logger.error(error_msg)
            return ApiResponse(
                success=False,
                message=error_msg,
                data={"analysis": None}
            )
        
        # Now try to get client with API keys
        try:
            from app.config.openai_keys import get_openai_client
            client = get_openai_client()
            
            if not client:
                logger.warning("No working OpenAI API key found, skipping LLM analysis")
                return ApiResponse(
                    success=False,
                    message="LLM analysis not available: No working API key found. The system tried all configured keys but none are valid.",
                    data={"analysis": None}
                )
        except ImportError as e:
            error_msg = (
                f"LLM analysis not available: Configuration import error.\n\n"
                f"Failed to import openai_keys module: {str(e)}\n\n"
                f"Please ensure app/config/__init__.py exists and the module structure is correct."
            )
            logger.error(error_msg)
            return ApiResponse(
                success=False,
                message=error_msg,
                data={"analysis": None}
            )
        except Exception as e:
            error_msg = (
                f"LLM analysis not available: Unexpected configuration error.\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check the logs for more details."
            )
            logger.error(f"Unexpected error in OpenAI config: {e}", exc_info=True)
            return ApiResponse(
                success=False,
                message=error_msg,
                data={"analysis": None}
            )
        
        # Format data for LLM analysis
        analysis_prompt = format_ticket_analysis_prompt(
            request.tickets,
            request.actual_results,
            request.fixtures,
            request.ticket_performance
        )
        
        # Call OpenAI API with error handling for invalid keys and quota issues
        max_retries = 10  # Try up to 10 different keys (to handle quota issues)
        last_error = None
        keys_tried = 0
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # Using mini for cost efficiency
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a football betting analyst expert. Analyze ticket performance data and provide actionable insights on which probability sets performed best, common prediction mistakes, and recommendations for improving ticket generation."
                        },
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                # Success! Break out of retry loop
                break
            except Exception as api_error:
                error_str = str(api_error)
                last_error = api_error
                keys_tried += 1
                
                # Check if it's an authentication error (401)
                is_auth_error = (
                    "401" in error_str or 
                    "authentication" in error_str.lower() or 
                    "invalid_api_key" in error_str.lower() or
                    hasattr(api_error, 'status_code') and api_error.status_code == 401
                )
                
                # Check if it's a quota error (429)
                is_quota_error = (
                    "429" in error_str or 
                    "quota" in error_str.lower() or 
                    "insufficient_quota" in error_str.lower() or
                    "rate_limit" in error_str.lower() or
                    hasattr(api_error, 'status_code') and api_error.status_code == 429
                )
                
                # Try next key if it's an auth or quota error
                if (is_auth_error or is_quota_error) and attempt < max_retries - 1:
                    error_type = "quota" if is_quota_error else "authentication"
                    logger.warning(f"OpenAI API key {error_type} failed (attempt {attempt + 1}/{max_retries}, key #{keys_tried}). Trying next key...")
                    # Try to get a new client (will try next key)
                    from app.config.openai_keys import get_openai_client
                    client = get_openai_client()
                    if not client:
                        error_msg = "LLM analysis not available: All OpenAI API keys failed."
                        if is_quota_error:
                            error_msg += " All keys have exceeded their quota. Please add keys with available quota to app/config/openai_keys.py"
                        else:
                            error_msg += " All keys failed authentication. Please configure a valid OPENAI_API_KEY environment variable or update the hardcoded keys in app/config/openai_keys.py"
                        return ApiResponse(
                            success=False,
                            message=error_msg,
                            data={"analysis": None}
                        )
                    # Continue to next iteration to retry with new key
                    continue
                else:
                    # Either not a retryable error, or we've exhausted retries
                    if is_auth_error or is_quota_error:
                        error_msg = "LLM analysis not available: All OpenAI API keys failed."
                        if is_quota_error:
                            error_msg += f" All {keys_tried} keys have exceeded their quota. Please add keys with available quota to app/config/openai_keys.py or set OPENAI_API_KEY environment variable with a key that has quota."
                        else:
                            error_msg += " All keys failed authentication. Please set a valid OPENAI_API_KEY environment variable or add valid keys to app/config/openai_keys.py"
                        return ApiResponse(
                            success=False,
                            message=error_msg,
                            data={"analysis": None}
                        )
                    else:
                        # Re-raise if it's not a retryable error
                        raise
        
        # If we get here without breaking, all retries failed
        if last_error:
            return ApiResponse(
                success=False,
                message=f"LLM analysis failed after {max_retries} attempts ({keys_tried} keys tried): {str(last_error)[:200]}",
                data={"analysis": None}
            )
        
        analysis_text = response.choices[0].message.content
        
        # Parse structured insights (if LLM returns structured format)
        insights = {
            "analysis": analysis_text,
            "best_performing_sets": extract_best_sets(analysis_text),
            "worst_performing_sets": extract_worst_sets(analysis_text),
            "common_mistakes": extract_common_mistakes(analysis_text),
            "recommendations": extract_recommendations(analysis_text)
        }
        
        return ApiResponse(
            success=True,
            message="Ticket performance analysis completed",
            data=insights
        )
        
    except Exception as e:
        logger.error(f"Error analyzing ticket performance: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message=f"Failed to analyze tickets: {str(e)}",
            data={"analysis": None}
        )


def format_ticket_analysis_prompt(
    tickets: List[Dict[str, Any]],
    actual_results: List[str],
    fixtures: List[Dict[str, Any]],
    ticket_performance: List[Dict[str, Any]]
) -> str:
    """Format ticket comparison data into a prompt for LLM analysis."""
    
    prompt = f"""Analyze the following football jackpot ticket performance data and provide insights:

**MATCH RESULTS (Actual):**
"""
    for idx, (fixture, actual) in enumerate(zip(fixtures, actual_results), 1):
        home = fixture.get('homeTeam', 'Team A')
        away = fixture.get('awayTeam', 'Team B')
        prompt += f"Match {idx}: {home} vs {away} → Actual Result: {actual}\n"
    
    prompt += f"\n**TICKET PERFORMANCE:**\n"
    for perf in ticket_performance:
        ticket_idx = ticket_performance.index(perf)
        ticket = tickets[ticket_idx]
        set_key = ticket.get('setKey', 'Unknown')
        accuracy = perf.get('accuracy', 0)
        correct = perf.get('correct', 0)
        total = perf.get('total', 0)
        
        prompt += f"\nSet {set_key}: {correct}/{total} correct ({accuracy:.1f}% accuracy)\n"
        prompt += f"  Predictions: {' '.join(ticket.get('picks', []))}\n"
    
    prompt += """
**ANALYSIS REQUEST:**

Please provide:
1. **Best Performing Sets**: Which probability sets (A-M) performed best and why?
2. **Worst Performing Sets**: Which sets underperformed and what patterns caused failures?
3. **Common Mistakes**: What types of predictions were frequently wrong? (e.g., over-predicting home wins, missing draws)
4. **Improvement Recommendations**: 
   - Which sets should be prioritized for future ticket generation?
   - What adjustments could improve accuracy?
   - Are there specific match types or patterns where certain sets excel/fail?
5. **Strategic Insights**: Any patterns in successful vs unsuccessful tickets?

Format your response clearly with sections for each point above.
"""
    
    return prompt


def extract_best_sets(analysis_text: str) -> List[str]:
    """Extract best performing sets from LLM analysis."""
    sets = []
    # Look for patterns like "Set B", "Set K", etc.
    matches = re.findall(r'Set\s+([A-M])', analysis_text, re.IGNORECASE)
    return list(set(matches))[:5]  # Return up to 5 unique sets


def extract_worst_sets(analysis_text: str) -> List[str]:
    """Extract worst performing sets from LLM analysis."""
    # Similar to extract_best_sets but look for negative context
    # This is a simple extraction - could be enhanced with NLP
    matches = re.findall(r'Set\s+([A-M])', analysis_text, re.IGNORECASE)
    return list(set(matches))[:3]


def extract_common_mistakes(analysis_text: str) -> List[str]:
    """Extract common mistakes from LLM analysis."""
    mistakes = []
    # Look for sentences mentioning mistakes
    lines = analysis_text.split('\n')
    for line in lines:
        if any(word in line.lower() for word in ['mistake', 'error', 'wrong', 'failed', 'missed']):
            mistakes.append(line.strip())
    return mistakes[:5]


def extract_recommendations(analysis_text: str) -> List[str]:
    """Extract recommendations from LLM analysis."""
    recommendations = []
    lines = analysis_text.split('\n')
    for line in lines:
        if any(word in line.lower() for word in ['recommend', 'suggest', 'should', 'consider', 'improve']):
            recommendations.append(line.strip())
    return recommendations[:5]


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

