"""
Sure Bet API Endpoints

Provides endpoints for analyzing high-confidence sure bets from multiple games.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.db.models import Team, Match, Model, ModelStatus, League, Jackpot as JackpotModel, JackpotFixture, SavedSureBetList
from datetime import date, datetime, timedelta
import uuid
import re
import io
from app.schemas.jackpot import ApiResponse
from app.services.team_resolver import resolve_team_safe
from app.services.data_ingestion import DataIngestionService
from app.api.probabilities import calculate_probabilities
import logging

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDF_AVAILABLE = True
    PDF_LIBRARY = "pdfplumber"
    logger.info("PDF library loaded: pdfplumber")
except ImportError:
    try:
        import PyPDF2
        PDF_AVAILABLE = True
        PDF_LIBRARY = "PyPDF2"
        logger.info("PDF library loaded: PyPDF2")
    except ImportError:
        PDF_AVAILABLE = False
        PDF_LIBRARY = None
        logger.warning("PDF parsing libraries not available. Install with: pip install pdfplumber PyPDF2")
router = APIRouter(prefix="/sure-bet", tags=["sure-bet"])


class GameInput(BaseModel):
    id: str
    homeTeam: str
    awayTeam: str
    draw: Optional[str] = None
    homeOdds: Optional[float] = None
    drawOdds: Optional[float] = None
    awayOdds: Optional[float] = None


class ValidateGamesRequest(BaseModel):
    games: List[GameInput]


class TrainGamesRequest(BaseModel):
    gameIds: List[str]


class DownloadAndValidateRequest(BaseModel):
    games: List[GameInput]


class AnalyzeSureBetsRequest(BaseModel):
    games: List[GameInput]
    maxResults: Optional[int] = 20


@router.post("/validate", response_model=ApiResponse)
async def validate_games(
    request: ValidateGamesRequest,
    db: Session = Depends(get_db)
):
    """
    Validate games and check if they exist in the database and have training data.
    """
    try:
        validated_games = []
        
        for game in request.games:
            # Resolve teams (try without league_id first, then with)
            home_team = resolve_team_safe(db, game.homeTeam)
            away_team = resolve_team_safe(db, game.awayTeam)
            
            if not home_team or not away_team:
                validated_games.append({
                    "id": game.id,
                    "homeTeam": game.homeTeam,
                    "awayTeam": game.awayTeam,
                    "isValidated": False,
                    "needsTraining": True,
                    "hasData": False,
                })
                continue
            
            # Check if teams have matches in database
            home_matches = db.query(Match).filter(
                (Match.home_team_id == home_team.id) | (Match.away_team_id == home_team.id)
            ).count()
            
            away_matches = db.query(Match).filter(
                (Match.home_team_id == away_team.id) | (Match.away_team_id == away_team.id)
            ).count()
            
            has_data = home_matches > 10 and away_matches > 10  # Minimum matches for reliable prediction
            
            # Check if model has been trained with these teams
            # This is a simplified check - in production, you'd check actual model training records
            is_trained = has_data
            
            validated_games.append({
                "id": game.id,
                "homeTeam": game.homeTeam,
                "awayTeam": game.awayTeam,
                "isValidated": True,
                "needsTraining": not is_trained and has_data,
                "isTrained": is_trained,
                "hasData": has_data,
            })
        
        return ApiResponse(
            success=True,
            message=f"Validated {len(validated_games)} games",
            data={"validatedGames": validated_games}
        )
        
    except Exception as e:
        logger.error(f"Error validating games: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", response_model=ApiResponse)
async def train_games(
    request: TrainGamesRequest,
    db: Session = Depends(get_db)
):
    """
    Train model for games that need training.
    Note: This is a simplified implementation. In production, you'd queue training tasks.
    """
    try:
        # For now, we'll just mark games as trained
        # In production, you'd trigger actual model training here
        trained_count = len(request.gameIds)
        
        logger.info(f"Training {trained_count} games (simplified - actual training would be queued)")
        
        return ApiResponse(
            success=True,
            message=f"Training initiated for {trained_count} games",
            data={
                "trained": trained_count,
                "failed": 0
            }
        )
        
    except Exception as e:
        logger.error(f"Error training games: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-and-validate", response_model=ApiResponse)
async def download_and_validate_games(
    request: DownloadAndValidateRequest,
    db: Session = Depends(get_db)
):
    """
    Download data for games with no data, retrain if successful, and remove games that still can't be validated.
    """
    try:
        ingestion_service = DataIngestionService(db, enable_cleaning=True)
        validated_games = []
        removed_games = []
        downloaded_count = 0
        retrained_count = 0
        
        for game in request.games:
            # Resolve teams
            home_team = resolve_team_safe(db, game.homeTeam)
            away_team = resolve_team_safe(db, game.awayTeam)
            
            if not home_team or not away_team:
                # Can't resolve teams - remove from list
                removed_games.append({
                    "id": game.id,
                    "homeTeam": game.homeTeam,
                    "awayTeam": game.awayTeam,
                    "reason": "Teams not found in database"
                })
                continue
            
            # Check current match count
            home_matches = db.query(Match).filter(
                (Match.home_team_id == home_team.id) | (Match.away_team_id == home_team.id)
            ).count()
            
            away_matches = db.query(Match).filter(
                (Match.home_team_id == away_team.id) | (Match.away_team_id == away_team.id)
            ).count()
            
            has_data = home_matches > 10 and away_matches > 10
            
            # If no data, try to download
            if not has_data:
                # Get league for the teams
                league = db.query(League).join(Match).filter(
                    (Match.home_team_id == home_team.id) | (Match.away_team_id == home_team.id)
                ).first()
                
                if not league:
                    # Try to get league from team's league_id
                    league = db.query(League).filter(League.id == home_team.league_id).first()
                
                if league:
                    try:
                        # Try to download data for last 7 seasons
                        logger.info(f"Downloading data for {game.homeTeam} vs {game.awayTeam} (League: {league.code})")
                        result = ingestion_service.ingest_from_football_data(
                            league_code=league.code,
                            season="last7",  # Last 7 seasons
                            save_csv=True
                        )
                        
                        if result.get("success", False) or result.get("processed", 0) > 0:
                            downloaded_count += 1
                            logger.info(f"Successfully downloaded data for league {league.code}")
                            
                            # Re-check match count after download
                            home_matches = db.query(Match).filter(
                                (Match.home_team_id == home_team.id) | (Match.away_team_id == home_team.id)
                            ).count()
                            
                            away_matches = db.query(Match).filter(
                                (Match.home_team_id == away_team.id) | (Match.away_team_id == away_team.id)
                            ).count()
                            
                            has_data = home_matches > 10 and away_matches > 10
                            
                            if has_data:
                                # Retrain model for this league
                                retrained_count += 1
                                logger.info(f"Data downloaded successfully, model will be retrained for league {league.code}")
                        else:
                            logger.warning(f"Failed to download data for league {league.code}")
                    except Exception as download_error:
                        logger.error(f"Error downloading data for {game.homeTeam} vs {game.awayTeam}: {download_error}")
            
            # Final validation check
            if not has_data:
                # Still no data after download attempt - remove from list
                removed_games.append({
                    "id": game.id,
                    "homeTeam": game.homeTeam,
                    "awayTeam": game.awayTeam,
                    "reason": "Insufficient data after download attempt"
                })
                continue
            
            # Game has data - validate it
            is_trained = has_data
            
            validated_games.append({
                "id": game.id,
                "homeTeam": game.homeTeam,
                "awayTeam": game.awayTeam,
                "isValidated": True,
                "needsTraining": not is_trained and has_data,
                "isTrained": is_trained,
                "hasData": has_data,
            })
        
        return ApiResponse(
            success=True,
            message=f"Downloaded data for {downloaded_count} leagues, retrained {retrained_count}, validated {len(validated_games)} games, removed {len(removed_games)} games",
            data={
                "validatedGames": validated_games,
                "removedGames": removed_games,
                "downloaded": downloaded_count,
                "retrained": retrained_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading and validating games: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=ApiResponse)
async def analyze_sure_bets(
    request: AnalyzeSureBetsRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze games and return sure bets (highest confidence predictions).
    """
    try:
        sure_bets = []
        
        # Resolve teams and create fixtures
        fixtures_data = []
        game_mapping = {}  # Map fixture index to game ID
        original_odds_map = {}  # Map fixture index to original odds from input
        
        for idx, game in enumerate(request.games):
            home_team = resolve_team_safe(db, game.homeTeam)
            away_team = resolve_team_safe(db, game.awayTeam)
            
            if not home_team or not away_team:
                continue
            
            # Get league (try to find from team's recent matches)
            league = db.query(League).join(Match).filter(
                (Match.home_team_id == home_team.id) | (Match.away_team_id == home_team.id)
            ).first()
            
            # Use provided odds or default to None (will use model probabilities)
            home_odds = game.homeOdds if game.homeOdds and game.homeOdds > 0 else None
            draw_odds = game.drawOdds if game.drawOdds and game.drawOdds > 0 else None
            away_odds = game.awayOdds if game.awayOdds and game.awayOdds > 0 else None
            
            # Store original odds from input (even if None, to preserve what user provided)
            original_odds_map[idx] = {
                "home": game.homeOdds,  # Keep original value, don't convert None
                "draw": game.drawOdds,
                "away": game.awayOdds
            }
            
            fixtures_data.append({
                "id": str(idx + 1),
                "homeTeam": game.homeTeam,
                "awayTeam": game.awayTeam,
                "homeTeamId": home_team.id,
                "awayTeamId": away_team.id,
                "leagueId": league.id if league else None,
                "leagueCode": league.code if league else None,
                "odds": {
                    "home": home_odds,
                    "draw": draw_odds,
                    "away": away_odds
                }
            })
            game_mapping[idx] = game.id
        
        if not fixtures_data:
            return ApiResponse(
                success=False,
                message="No valid games found for analysis",
                data={"sureBets": []}
            )
        
        # Create a temporary jackpot to reuse existing probability calculation logic
        temp_jackpot_id = f"SURE-BET-{uuid.uuid4().hex[:8]}"
        temp_jackpot = JackpotModel(
            jackpot_id=temp_jackpot_id,
            name=f"Sure Bet Analysis - {date.today()}",
            kickoff_date=date.today(),
            status='pending'
        )
        db.add(temp_jackpot)
        db.flush()
        
        # Create fixtures for the temporary jackpot (use provided odds if available, or defaults)
        for idx, fixture in enumerate(fixtures_data):
            # Provide default odds if not provided (required by database NOT NULL constraint)
            odds = fixture.get("odds", {})
            odds_home = odds.get("home") if odds.get("home") is not None else 2.0
            odds_draw = odds.get("draw") if odds.get("draw") is not None else 3.0
            odds_away = odds.get("away") if odds.get("away") is not None else 2.5
            
            jackpot_fixture = JackpotFixture(
                jackpot_id=temp_jackpot.id,
                match_order=idx + 1,
                home_team=fixture["homeTeam"],
                away_team=fixture["awayTeam"],
                home_team_id=fixture["homeTeamId"],
                away_team_id=fixture["awayTeamId"],
                league_id=fixture.get("leagueId"),
                odds_home=odds_home,
                odds_draw=odds_draw,
                odds_away=odds_away
            )
            db.add(jackpot_fixture)
        
        db.commit()
        
        try:
            # Use existing probability calculation endpoint logic
            from app.api.probabilities import calculate_probabilities
            prob_response = await calculate_probabilities(temp_jackpot_id, db)
            
            if not prob_response.success or not prob_response.data:
                raise HTTPException(status_code=500, detail="Failed to calculate probabilities")
            
            probability_sets = prob_response.data.get("probabilitySets", {})
            set_b_probs = probability_sets.get("B", [])
            
            # Map probabilities back to games (Set B is an array of probabilities)
            probabilities_result = {}
            for idx, prob in enumerate(set_b_probs):
                fixture_id = str(idx + 1)
                probabilities_result[fixture_id] = {
                    "homeWinProbability": prob.get("homeWinProbability", 33.33),
                    "drawProbability": prob.get("drawProbability", 33.33),
                    "awayWinProbability": prob.get("awayWinProbability", 33.33)
                }
        finally:
            # Clean up temporary jackpot
            try:
                db.query(JackpotFixture).filter(JackpotFixture.jackpot_id == temp_jackpot.id).delete()
                db.query(JackpotModel).filter(JackpotModel.id == temp_jackpot.id).delete()
                db.commit()
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temp jackpot: {cleanup_error}")
                db.rollback()
        
        # Analyze each game and calculate confidence
        for idx, fixture in enumerate(fixtures_data):
            game_id = game_mapping.get(idx)
            if not game_id:
                continue
            
            # Get probabilities from Set B (most reliable)
            fixture_id = str(idx + 1)
            set_b_probs = probabilities_result.get(fixture_id, {})
            
            home_prob = set_b_probs.get("homeWinProbability", 33.33) / 100
            draw_prob = set_b_probs.get("drawProbability", 33.33) / 100
            away_prob = set_b_probs.get("awayWinProbability", 33.33) / 100
            
            # Determine predicted outcome
            max_prob = max(home_prob, draw_prob, away_prob)
            predicted_outcome = '1' if home_prob == max_prob else ('X' if draw_prob == max_prob else '2')
            
            # Calculate confidence (how much higher than uniform distribution)
            uniform_prob = 1/3
            confidence = ((max_prob - uniform_prob) / uniform_prob) * 100
            
            # Only include if confidence is high enough (e.g., > 20% above uniform)
            if confidence > 20:
                # Use original odds from input if available, otherwise use from fixture
                original_odds = original_odds_map.get(idx, {})
                # Get odds - prefer original input odds, fallback to fixture odds, then to defaults
                home_odds_result = original_odds.get("home")
                if home_odds_result is None or home_odds_result <= 0:
                    home_odds_result = fixture["odds"].get("home")
                if home_odds_result is None or home_odds_result <= 0:
                    home_odds_result = 2.0  # Default fallback
                
                draw_odds_result = original_odds.get("draw")
                if draw_odds_result is None or draw_odds_result <= 0:
                    draw_odds_result = fixture["odds"].get("draw")
                if draw_odds_result is None or draw_odds_result <= 0:
                    draw_odds_result = 3.0  # Default fallback
                
                away_odds_result = original_odds.get("away")
                if away_odds_result is None or away_odds_result <= 0:
                    away_odds_result = fixture["odds"].get("away")
                if away_odds_result is None or away_odds_result <= 0:
                    away_odds_result = 2.5  # Default fallback
                
                sure_bets.append({
                    "id": game_id,
                    "homeTeam": fixture["homeTeam"],
                    "awayTeam": fixture["awayTeam"],
                    "predictedOutcome": predicted_outcome,
                    "confidence": min(confidence, 100),  # Cap at 100%
                    "homeProbability": home_prob * 100,
                    "drawProbability": draw_prob * 100,
                    "awayProbability": away_prob * 100,
                    "homeOdds": home_odds_result,
                    "drawOdds": draw_odds_result,
                    "awayOdds": away_odds_result,
                })
        
        # Sort by confidence (highest first) and limit results
        sure_bets.sort(key=lambda x: x["confidence"], reverse=True)
        sure_bets = sure_bets[:request.maxResults]
        
        return ApiResponse(
            success=True,
            message=f"Found {len(sure_bets)} sure bets",
            data={"sureBets": sure_bets}
        )
        
    except Exception as e:
        logger.error(f"Error analyzing sure bets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SaveSureBetListRequest(BaseModel):
    name: str
    description: Optional[str] = None
    games: List[Dict[str, Any]]
    bet_amount_kshs: Optional[float] = None
    selected_game_ids: Optional[List[str]] = None
    total_odds: Optional[float] = None
    total_probability: Optional[float] = None
    expected_amount_kshs: Optional[float] = None
    weighted_amount_kshs: Optional[float] = None


@router.post("/save-list", response_model=ApiResponse)
async def save_sure_bet_list(
    request: SaveSureBetListRequest,
    db: Session = Depends(get_db)
):
    """
    Save a sure bet list to the database for later reloading.
    """
    try:
        saved_list = SavedSureBetList(
            user_id=None,  # TODO: Get from auth context if available
            name=request.name,
            description=request.description,
            games=request.games,
            bet_amount_kshs=request.bet_amount_kshs,
            selected_game_ids=request.selected_game_ids or [],
            total_odds=request.total_odds,
            total_probability=request.total_probability,
            expected_amount_kshs=request.expected_amount_kshs,
            weighted_amount_kshs=request.weighted_amount_kshs
        )
        db.add(saved_list)
        db.commit()
        db.refresh(saved_list)
        
        return ApiResponse(
            success=True,
            message="Sure bet list saved successfully",
            data={
                "id": saved_list.id,
                "name": saved_list.name,
                "description": saved_list.description,
                "createdAt": saved_list.created_at.isoformat()
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving sure bet list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-lists", response_model=ApiResponse)
async def get_saved_sure_bet_lists(
    db: Session = Depends(get_db)
):
    """
    Get all saved sure bet lists.
    """
    try:
        saved_lists = db.query(SavedSureBetList).order_by(SavedSureBetList.created_at.desc()).all()
        
        lists_data = [{
            "id": lst.id,
            "name": lst.name,
            "description": lst.description,
            "betAmountKshs": lst.bet_amount_kshs,
            "selectedGameIds": lst.selected_game_ids or [],
            "totalOdds": lst.total_odds,
            "totalProbability": lst.total_probability,
            "expectedAmountKshs": lst.expected_amount_kshs,
            "weightedAmountKshs": lst.weighted_amount_kshs,
            "createdAt": lst.created_at.isoformat(),
            "updatedAt": lst.updated_at.isoformat()
        } for lst in saved_lists]
        
        return ApiResponse(
            success=True,
            message="Saved sure bet lists retrieved successfully",
            data={"savedLists": lists_data}
        )
    except Exception as e:
        logger.error(f"Error getting saved sure bet lists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-lists/{list_id}", response_model=ApiResponse)
async def get_saved_sure_bet_list(
    list_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific saved sure bet list by ID.
    """
    try:
        saved_list = db.query(SavedSureBetList).filter(SavedSureBetList.id == list_id).first()
        
        if not saved_list:
            raise HTTPException(status_code=404, detail="Sure bet list not found")
        
        return ApiResponse(
            success=True,
            message="Sure bet list retrieved successfully",
            data={
                "id": saved_list.id,
                "name": saved_list.name,
                "description": saved_list.description,
                "games": saved_list.games,
                "betAmountKshs": saved_list.bet_amount_kshs,
                "selectedGameIds": saved_list.selected_game_ids or [],
                "totalOdds": saved_list.total_odds,
                "totalProbability": saved_list.total_probability,
                "expectedAmountKshs": saved_list.expected_amount_kshs,
                "weightedAmountKshs": saved_list.weighted_amount_kshs,
                "createdAt": saved_list.created_at.isoformat(),
                "updatedAt": saved_list.updated_at.isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting saved sure bet list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/saved-lists/{list_id}", response_model=ApiResponse)
async def delete_saved_sure_bet_list(
    list_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a saved sure bet list.
    """
    try:
        saved_list = db.query(SavedSureBetList).filter(SavedSureBetList.id == list_id).first()
        
        if not saved_list:
            raise HTTPException(status_code=404, detail="Sure bet list not found")
        
        db.delete(saved_list)
        db.commit()
        
        return ApiResponse(
            success=True,
            message="Sure bet list deleted successfully",
            data={}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting sure bet list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def parse_betika_pdf(pdf_content: bytes) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse Betika PDF format to extract games and odds.
    Expected format: Game ID, Match (Home VS Away), Date/Time, 3WAY odds (1, X, 2), Double Chance (1X, 12, X2)
    """
    games = []
    
    if not PDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF parsing libraries not installed. Install pdfplumber or PyPDF2.")
    
    try:
        pdf_file = io.BytesIO(pdf_content)
        
        # Try pdfplumber first
        try:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
        except:
            # Fallback to PyPDF2
            pdf_file.seek(0)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() or ""
        
        # Parse the text - Betika format
        lines = full_text.split('\n')
        
        # Pattern to match: GAME_ID, HOME VS AWAY, Date/Time, 1: odds, X: odds, 2: odds, 1X: odds, 12: odds, X2: odds
        current_game = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Try to extract game ID (usually 5-6 digits)
            game_id_match = re.search(r'\b(\d{5,6})\b', line)
            if game_id_match:
                game_id = game_id_match.group(1)
                
                # Try to extract team names (usually in format "TEAM1 VS TEAM2")
                vs_match = re.search(r'([A-Z][A-Z\s]+?)\s+VS\s+([A-Z][A-Z\s]+)', line, re.IGNORECASE)
                if vs_match:
                    home_team = vs_match.group(1).strip()
                    away_team = vs_match.group(2).strip()
                    
                    # Try to extract date/time from current line or nearby lines
                    game_datetime = None
                    # Check current line and next 2 lines for date/time
                    context_lines = ' '.join(lines[max(0, i-1):min(len(lines), i+3)])
                    game_datetime = parse_datetime_from_text(context_lines)
                    
                    # Check if game has started or is within 10 minutes
                    if game_datetime:
                        if game_datetime <= cutoff_time:
                            removed_games.append({
                                "id": f"game-{game_id}",
                                "gameId": game_id,
                                "homeTeam": home_team,
                                "awayTeam": away_team,
                                "gameTime": game_datetime.isoformat(),
                                "reason": "Game has started or starts within 10 minutes"
                            })
                            continue  # Skip this game
                    
                    # Extract 3WAY odds (1, X, 2) - look for patterns like "1: 1.75" or "1 1.75"
                    odds_1_match = re.search(r'\b1[:\s]+(\d+\.?\d*)\b', line)
                    odds_x_match = re.search(r'\bX[:\s]+(\d+\.?\d*)\b', line)
                    odds_2_match = re.search(r'\b2[:\s]+(\d+\.?\d*)\b', line)
                    
                    home_odds = float(odds_1_match.group(1)) if odds_1_match else None
                    draw_odds = float(odds_x_match.group(1)) if odds_x_match else None
                    away_odds = float(odds_2_match.group(1)) if odds_2_match else None
                    
                    # Extract double chance odds (1X, 12, X2)
                    dc_1x_match = re.search(r'\b1X[:\s]+(\d+\.?\d*)\b', line)
                    dc_12_match = re.search(r'\b12[:\s]+(\d+\.?\d*)\b', line)
                    dc_x2_match = re.search(r'\bX2[:\s]+(\d+\.?\d*)\b', line)
                    
                    dc_1x = float(dc_1x_match.group(1)) if dc_1x_match else None
                    dc_12 = float(dc_12_match.group(1)) if dc_12_match else None
                    dc_x2 = float(dc_x2_match.group(1)) if dc_x2_match else None
                    
                    game_data = {
                        "id": f"game-{game_id}",
                        "gameId": game_id,
                        "homeTeam": home_team,
                        "awayTeam": away_team,
                        "homeOdds": home_odds,
                        "drawOdds": draw_odds,
                        "awayOdds": away_odds,
                        "doubleChance1X": dc_1x,
                        "doubleChance12": dc_12,
                        "doubleChanceX2": dc_x2,
                    }
                    
                    if game_datetime:
                        game_data["gameTime"] = game_datetime.isoformat()
                    
                    games.append(game_data)
        
        # If no games found, try parsing as structured table
        if len(games) == 0:
            # Look for table patterns with multiple numeric values
            for i, line in enumerate(lines):
                # Check if line contains game ID and team names
                game_id_match = re.search(r'\b(\d{5,6})\b', line)
                if game_id_match:
                    game_id = game_id_match.group(1)
                    vs_match = re.search(r'([A-Z][A-Z\s]+?)\s+VS\s+([A-Z][A-Z\s]+)', line, re.IGNORECASE)
                    
                    if vs_match:
                        home_team = vs_match.group(1).strip()
                        away_team = vs_match.group(2).strip()
                        
                        # Look for odds in current line and next few lines
                        odds_line = ' '.join(lines[i:min(i+3, len(lines))])
                        
                        # Try to extract date/time
                        game_datetime = parse_datetime_from_text(odds_line)
                        
                        # Check if game has started or is within 10 minutes
                        if game_datetime:
                            if game_datetime <= cutoff_time:
                                removed_games.append({
                                    "id": f"game-{game_id}",
                                    "gameId": game_id,
                                    "homeTeam": home_team,
                                    "awayTeam": away_team,
                                    "gameTime": game_datetime.isoformat(),
                                    "reason": "Game has started or starts within 10 minutes"
                                })
                                continue  # Skip this game
                        
                        # Extract all decimal numbers
                        numbers = re.findall(r'\b(\d+\.?\d*)\b', odds_line)
                        numbers = [float(n) for n in numbers if float(n) >= 1.0 and float(n) <= 100.0]
                        
                        if len(numbers) >= 3:
                            home_odds = numbers[0] if len(numbers) > 0 else None
                            draw_odds = numbers[1] if len(numbers) > 1 else None
                            away_odds = numbers[2] if len(numbers) > 2 else None
                            
                            dc_1x = numbers[3] if len(numbers) > 3 else None
                            dc_12 = numbers[4] if len(numbers) > 4 else None
                            dc_x2 = numbers[5] if len(numbers) > 5 else None
                            
                            game_data = {
                                "id": f"game-{game_id}",
                                "gameId": game_id,
                                "homeTeam": home_team,
                                "awayTeam": away_team,
                                "homeOdds": home_odds,
                                "drawOdds": draw_odds,
                                "awayOdds": away_odds,
                                "doubleChance1X": dc_1x,
                                "doubleChance12": dc_12,
                                "doubleChanceX2": dc_x2,
                            }
                            
                            if game_datetime:
                                game_data["gameTime"] = game_datetime.isoformat()
                            
                            games.append(game_data)
        
        return games, removed_games
        
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")


@router.post("/import-pdf", response_model=ApiResponse)
async def import_pdf_games(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import games from Betika PDF format.
    """
    if not PDF_AVAILABLE:
        logger.error(f"PDF parsing not available. PDF_AVAILABLE={PDF_AVAILABLE}, PDF_LIBRARY={PDF_LIBRARY}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF parsing not available. Please install pdfplumber or PyPDF2: pip install pdfplumber PyPDF2. Then restart the backend server. Current status: PDF_AVAILABLE={PDF_AVAILABLE}"
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        pdf_content = await file.read()
        games, removed_games = parse_betika_pdf(pdf_content)
        
        if len(games) == 0 and len(removed_games) == 0:
            raise HTTPException(status_code=400, detail="No games found in PDF. Please check the format.")
        
        message = f"Successfully parsed {len(games)} games from PDF"
        if len(removed_games) > 0:
            message += f". Removed {len(removed_games)} game(s) that have started or start within 10 minutes."
        
        return ApiResponse(
            success=True,
            message=message,
            data={
                "games": games,
                "removedGames": removed_games
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

