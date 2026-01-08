"""
API endpoints for draw structural data ingestion
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.jackpot import ApiResponse
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/draw-ingestion", tags=["draw-ingestion"])


class IngestLeaguePriorsRequest(BaseModel):
    league_code: str
    season: Optional[str] = "ALL"
    csv_path: Optional[str] = None


class BatchIngestLeaguePriorsRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None  # Only used if use_all_seasons=True


class IngestH2HRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    use_api: bool = False


class BatchIngestH2HRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestEloRequest(BaseModel):
    team_id: Optional[int] = None
    csv_path: Optional[str] = None
    calculate_from_matches: bool = False


class BatchIngestEloRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestWeatherRequest(BaseModel):
    fixture_id: int
    latitude: float
    longitude: float
    match_datetime: str  # ISO format


class IngestRefereeRequest(BaseModel):
    referee_id: int
    referee_name: Optional[str] = None


class BatchIngestRefereeRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestRestDaysRequest(BaseModel):
    fixture_id: int
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None


class BatchIngestRestDaysRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestOddsMovementRequest(BaseModel):
    fixture_id: int
    draw_odds: Optional[float] = None


class IngestInjuriesRequest(BaseModel):
    team_id: int
    fixture_id: int
    key_players_missing: Optional[int] = None
    injury_severity: Optional[float] = None  # 0.0-1.0
    attackers_missing: Optional[int] = None
    midfielders_missing: Optional[int] = None
    defenders_missing: Optional[int] = None
    goalkeepers_missing: Optional[int] = None
    notes: Optional[str] = None


class BatchIngestInjuriesRequest(BaseModel):
    injuries: List[IngestInjuriesRequest]


class BatchIngestRequest(BaseModel):
    """Request model for batch import all draw structural data"""
    use_all_leagues: bool = True
    use_all_seasons: bool = True
    max_years: Optional[int] = 10
    league_codes: Optional[List[str]] = None
    use_hybrid_import: bool = True


class BatchIngestOddsMovementRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class BatchIngestWeatherRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestLeagueStructureRequest(BaseModel):
    league_code: str
    season: str
    total_teams: Optional[int] = None
    relegation_zones: Optional[int] = None
    promotion_zones: Optional[int] = None
    playoff_zones: Optional[int] = None
    save_csv: bool = True


class BatchIngestLeagueStructureRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


class IngestXGDataRequest(BaseModel):
    fixture_id: Optional[int] = None
    match_id: Optional[int] = None
    xg_home: float
    xg_away: float


class BatchIngestXGDataRequest(BaseModel):
    league_codes: Optional[List[str]] = None
    season: Optional[str] = "ALL"
    use_all_leagues: bool = False
    use_all_seasons: bool = False
    max_years: Optional[int] = None
    save_csv: bool = True


@router.post("/league-priors", response_model=ApiResponse)
async def ingest_league_priors(
    request: IngestLeaguePriorsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest league draw priors"""
    try:
        from app.services.ingestion.ingest_league_draw_priors import (
            ingest_league_draw_priors_from_csv,
            ingest_from_matches_table
        )
        
        if request.csv_path:
            result = ingest_league_draw_priors_from_csv(
                db, request.csv_path, request.league_code, request.season
            )
        else:
            result = ingest_from_matches_table(db, request.league_code, request.season, save_csv=True)
        
        if not result.get("success"):
            error_msg = result.get("error", "Ingestion failed")
            # Handle "No matches found" gracefully - not an error, just no data
            if "No matches found" in error_msg:
                return ApiResponse(
                    data={"league_code": request.league_code, "season": request.season, "matches_found": 0},
                    success=True,
                    message=f"No matches found for league {request.league_code} season {request.season}. Skipping league priors calculation."
                )
            # For other errors, return 400
            raise HTTPException(status_code=400, detail=error_msg)
        
        return ApiResponse(
            data=result,
            success=True,
            message="League draw priors ingested successfully"
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like 400 Bad Request) as-is
        raise
    except Exception as e:
        logger.error(f"Error ingesting league priors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/league-priors/batch", response_model=ApiResponse)
async def batch_ingest_league_priors(
    request: BatchIngestLeaguePriorsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest league draw priors for multiple leagues"""
    try:
        from app.services.ingestion.ingest_league_draw_priors import batch_ingest_league_priors
        
        result = batch_ingest_league_priors(
            db=db,
            league_codes=request.league_codes,
            season=request.season,
            use_all_leagues=request.use_all_leagues,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years,
            save_csv=True
        )
        
        if not result.get("success") and result.get("successful", 0) == 0:
            # Only return error if nothing succeeded
            error_msg = result.get("error", "Batch ingestion failed")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Return success even if some failed, as long as some succeeded
        message = (
            f"Processed {result.get('processed', 0)} league/season combinations: "
            f"{result.get('successful', 0)} successful, "
            f"{result.get('failed', 0)} failed, "
            f"{result.get('skipped', 0)} skipped"
        )
        
        return ApiResponse(
            data=result,
            success=True,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch league priors ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/h2h", response_model=ApiResponse)
async def ingest_h2h(
    request: IngestH2HRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest head-to-head statistics"""
    try:
        from app.services.ingestion.ingest_h2h_stats import (
            ingest_h2h_from_api_football,
            ingest_h2h_from_matches_table
        )
        
        if request.use_api:
            result = ingest_h2h_from_api_football(
                db, request.home_team_id, request.away_team_id
            )
        else:
            result = ingest_h2h_from_matches_table(
                db, request.home_team_id, request.away_team_id, save_csv=True
            )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="H2H statistics ingested successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting H2H: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/h2h/batch", response_model=ApiResponse)
async def batch_ingest_h2h(
    request: BatchIngestH2HRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest H2H statistics for all team pairs in specified leagues"""
    try:
        from app.services.ingestion.ingest_h2h_stats import batch_ingest_h2h_stats
        
        result = batch_ingest_h2h_stats(
            db=db,
            league_codes=request.league_codes,
            season=request.season or "ALL",
            use_all_leagues=request.use_all_leagues,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"H2H batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch H2H ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elo", response_model=ApiResponse)
async def ingest_elo(
    request: IngestEloRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest Elo ratings"""
    try:
        from app.services.ingestion.ingest_elo_ratings import (
            ingest_elo_from_clubelo_csv,
            calculate_elo_from_matches
        )
        
        if request.csv_path:
            result = ingest_elo_from_clubelo_csv(db, request.csv_path)
        elif request.calculate_from_matches and request.team_id:
            result = calculate_elo_from_matches(db, request.team_id, save_csv=True)
        else:
            raise HTTPException(status_code=400, detail="Either csv_path or (team_id + calculate_from_matches) required")
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="Elo ratings ingested successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting Elo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/elo/batch", response_model=ApiResponse)
async def batch_ingest_elo(
    request: BatchIngestEloRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch calculate Elo ratings for all teams in specified leagues and seasons"""
    try:
        from app.services.ingestion.ingest_elo_ratings import batch_calculate_elo_from_matches
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_calculate_elo_from_matches(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Elo batch calculation complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch Elo ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weather", response_model=ApiResponse)
async def ingest_weather(
    request: IngestWeatherRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest weather data"""
    try:
        from app.services.ingestion.ingest_weather import ingest_weather_from_open_meteo
        from datetime import datetime
        
        match_datetime = datetime.fromisoformat(request.match_datetime)
        
        result = ingest_weather_from_open_meteo(
            db, request.fixture_id, request.latitude, request.longitude, match_datetime
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="Weather data ingested successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting weather: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/referee", response_model=ApiResponse)
async def ingest_referee(
    request: IngestRefereeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest referee statistics"""
    try:
        from app.services.ingestion.ingest_referee_stats import ingest_referee_stats_from_matches
        
        result = ingest_referee_stats_from_matches(
            db, request.referee_id, request.referee_name, save_csv=True
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="Referee statistics ingested successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting referee: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/referee/batch", response_model=ApiResponse)
async def batch_ingest_referee(
    request: BatchIngestRefereeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest referee statistics for all referees in specified leagues and seasons"""
    try:
        from app.services.ingestion.ingest_referee_stats import batch_ingest_referee_stats
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_ingest_referee_stats(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Referee batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch referee ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rest-days", response_model=ApiResponse)
async def ingest_rest_days(
    request: IngestRestDaysRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest rest days"""
    try:
        from app.services.ingestion.ingest_rest_days import ingest_rest_days_for_fixture
        
        result = ingest_rest_days_for_fixture(
            db, request.fixture_id, request.home_team_id, request.away_team_id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="Rest days ingested successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting rest days: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/odds-movement", response_model=ApiResponse)
async def ingest_odds_movement(
    request: IngestOddsMovementRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest or track odds movement"""
    try:
        from app.services.ingestion.ingest_odds_movement import (
            ingest_odds_movement_from_football_data_org,
            track_odds_movement
        )
        
        if request.draw_odds:
            result = track_odds_movement(db, request.fixture_id, request.draw_odds)
        else:
            result = ingest_odds_movement_from_football_data_org(db, request.fixture_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="Odds movement tracked successfully"
        )
    except Exception as e:
        logger.error(f"Error ingesting odds movement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/rest-days", response_model=ApiResponse)
async def batch_ingest_rest_days(
    fixture_ids: List[int] = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest rest days for multiple fixtures"""
    try:
        from app.services.ingestion.ingest_rest_days import ingest_rest_days_batch
        
        result = ingest_rest_days_batch(db, fixture_ids)
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Rest days calculated for {result.get('success_count', 0)}/{result.get('total', 0)} fixtures"
        )
    except Exception as e:
        logger.error(f"Error in batch rest days ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rest-days/batch", response_model=ApiResponse)
async def batch_ingest_rest_days_from_matches(
    request: BatchIngestRestDaysRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest rest days for matches in specified leagues and seasons"""
    try:
        from app.services.ingestion.ingest_rest_days import batch_ingest_rest_days_from_matches
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_ingest_rest_days_from_matches(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Rest days batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch rest days ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/odds-movement/batch", response_model=ApiResponse)
async def batch_ingest_odds_movement(
    request: BatchIngestOddsMovementRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest odds movement for matches in specified leagues and seasons"""
    try:
        from app.services.ingestion.ingest_odds_movement import batch_ingest_odds_movement_from_matches
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_ingest_odds_movement_from_matches(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Odds movement batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch odds movement ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/weather/batch", response_model=ApiResponse)
async def batch_ingest_weather(
    request: BatchIngestWeatherRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest weather for matches in specified leagues and seasons"""
    try:
        from app.services.ingestion.ingest_weather import batch_ingest_weather_from_matches
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_ingest_weather_from_matches(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Weather batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch weather ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/league-priors/summary", response_model=ApiResponse)
async def get_league_priors_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for league draw priors"""
    try:
        from sqlalchemy import text
        from app.db.models import League
        
        # Get total count
        total_count = db.execute(text('SELECT COUNT(*) FROM league_draw_priors')).scalar()
        
        # Get count by league
        league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(*) as count
            FROM league_draw_priors ldp 
            JOIN leagues l ON ldp.league_id = l.id 
            GROUP BY l.code, l.name
            ORDER BY count DESC
        """)).fetchall()
        
        # Get most recent update
        most_recent = db.execute(text("""
            SELECT MAX(updated_at) as last_updated
            FROM league_draw_priors
        """)).fetchone()
        
        # Get total leagues with priors
        leagues_with_priors = db.execute(text('SELECT COUNT(DISTINCT league_id) FROM league_draw_priors')).scalar()
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        # Get unique seasons count
        unique_seasons = db.execute(text('SELECT COUNT(DISTINCT season) FROM league_draw_priors')).scalar()
        
        return ApiResponse(
            data={
                "total_priors": total_count,
                "leagues_with_priors": leagues_with_priors,
                "total_leagues": total_leagues,
                "unique_seasons": unique_seasons,
                "last_updated": most_recent.last_updated.isoformat() if most_recent and most_recent.last_updated else None,
                "by_league": [
                    {
                        "code": row.code,
                        "name": row.name,
                        "count": row.count
                    }
                    for row in league_counts
                ]
            },
            success=True,
            message="League priors summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting league priors summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/h2h-stats/summary", response_model=ApiResponse)
async def get_h2h_stats_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for H2H stats"""
    try:
        from sqlalchemy import text
        
        # Get total count - using h2h_draw_stats table (where data is actually stored)
        total_count = db.execute(text('SELECT COUNT(*) FROM h2h_draw_stats')).scalar()
        
        # Get count by league (through teams)
        league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(DISTINCT h2h.id) as count
            FROM h2h_draw_stats h2h
            JOIN teams t ON h2h.team_home_id = t.id
            JOIN leagues l ON t.league_id = l.id
            GROUP BY l.code, l.name
            ORDER BY count DESC
        """)).fetchall()
        
        # Get most recent update
        most_recent = db.execute(text("""
            SELECT MAX(last_updated) as last_updated
            FROM h2h_draw_stats
        """)).fetchone()
        
        # Get total leagues with H2H stats
        leagues_with_stats = db.execute(text("""
            SELECT COUNT(DISTINCT l.id)
            FROM h2h_draw_stats h2h
            JOIN teams t ON h2h.team_home_id = t.id
            JOIN leagues l ON t.league_id = l.id
        """)).scalar()
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_stats": leagues_with_stats,
                "total_leagues": total_leagues,
                "last_updated": most_recent.last_updated.isoformat() if most_recent and most_recent.last_updated else None,
                "by_league": [
                    {
                        "code": row.code,
                        "name": row.name,
                        "count": row.count
                    }
                    for row in league_counts
                ]
            },
            success=True,
            message="H2H stats summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting H2H stats summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elo-ratings/summary", response_model=ApiResponse)
async def get_elo_ratings_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for Elo ratings"""
    try:
        from sqlalchemy import text
        
        # Get total count
        total_count = db.execute(text('SELECT COUNT(*) FROM team_elo')).scalar()
        
        # Get count by league (through teams)
        league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(DISTINCT e.id) as count
            FROM team_elo e
            JOIN teams t ON e.team_id = t.id
            JOIN leagues l ON t.league_id = l.id
            GROUP BY l.code, l.name
            ORDER BY count DESC
        """)).fetchall()
        
        # Get most recent update
        most_recent = db.execute(text("""
            SELECT MAX(created_at) as last_updated
            FROM team_elo
        """)).fetchone()
        
        # Get total leagues with Elo ratings
        leagues_with_elo = db.execute(text("""
            SELECT COUNT(DISTINCT l.id)
            FROM team_elo e
            JOIN teams t ON e.team_id = t.id
            JOIN leagues l ON t.league_id = l.id
        """)).scalar()
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        # Get unique dates count
        unique_dates = db.execute(text('SELECT COUNT(DISTINCT date) FROM team_elo')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_elo": leagues_with_elo,
                "total_leagues": total_leagues,
                "unique_dates": unique_dates,
                "last_updated": most_recent.last_updated.isoformat() if most_recent and most_recent.last_updated else None,
                "by_league": [
                    {
                        "code": row.code,
                        "name": row.name,
                        "count": row.count
                    }
                    for row in league_counts
                ]
            },
            success=True,
            message="Elo ratings summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting Elo ratings summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather/summary", response_model=ApiResponse)
async def get_weather_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for weather data"""
    try:
        from sqlalchemy import text
        
        # Check if match_weather_historical table exists
        try:
            historical_exists = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'match_weather_historical'
                )
            """)).scalar()
        except:
            historical_exists = False
        
        # Get total count from both tables
        if historical_exists:
            total_count = db.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM match_weather) +
                    (SELECT COUNT(*) FROM match_weather_historical)
            """)).scalar()
        else:
            total_count = db.execute(text('SELECT COUNT(*) FROM match_weather')).scalar()
        
        # Get count by league (from fixtures)
        league_counts_fixtures = db.execute(text("""
            SELECT l.code, l.name, COUNT(DISTINCT mw.id) as count
            FROM match_weather mw
            JOIN jackpot_fixtures jf ON mw.fixture_id = jf.id
            JOIN leagues l ON jf.league_id = l.id
            WHERE jf.league_id IS NOT NULL
            GROUP BY l.code, l.name
        """)).fetchall()
        
        # Get count by league (from historical matches) if table exists
        league_counts_historical = []
        if historical_exists:
            try:
                league_counts_historical = db.execute(text("""
                    SELECT l.code, l.name, COUNT(DISTINCT mwh.id) as count
                    FROM match_weather_historical mwh
                    JOIN matches m ON mwh.match_id = m.id
                    JOIN leagues l ON m.league_id = l.id
                    GROUP BY l.code, l.name
                """)).fetchall()
            except:
                pass
        
        # Combine counts by league
        league_dict = {}
        for row in league_counts_fixtures:
            league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        for row in league_counts_historical:
            if row.code in league_dict:
                league_dict[row.code]["count"] += row.count
            else:
                league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        # Convert to list format expected by frontend
        league_counts_list = [
            {
                "code": data["code"],
                "name": data["name"],
                "count": data["count"]
            }
            for data in sorted(league_dict.values(), key=lambda x: x["count"], reverse=True)
        ]
        
        # Get most recent update from both tables
        last_updated = None
        if historical_exists:
            most_recent = db.execute(text("""
                SELECT GREATEST(
                    COALESCE((SELECT MAX(recorded_at) FROM match_weather), '1970-01-01'::timestamptz),
                    COALESCE((SELECT MAX(recorded_at) FROM match_weather_historical), '1970-01-01'::timestamptz)
                ) as last_updated
            """)).fetchone()
            if most_recent and most_recent.last_updated:
                last_updated = most_recent.last_updated
        else:
            most_recent = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM match_weather
            """)).fetchone()
            if most_recent and most_recent.last_updated:
                last_updated = most_recent.last_updated
        
        # Get total leagues with weather data
        if historical_exists:
            leagues_with_weather = db.execute(text("""
                SELECT COUNT(DISTINCT league_id) FROM (
                    SELECT jf.league_id FROM match_weather mw
                    JOIN jackpot_fixtures jf ON mw.fixture_id = jf.id
                    WHERE jf.league_id IS NOT NULL
                    UNION
                    SELECT m.league_id FROM match_weather_historical mwh
                    JOIN matches m ON mwh.match_id = m.id
                ) combined
            """)).scalar() or 0
        else:
            leagues_with_weather = db.execute(text("""
                SELECT COUNT(DISTINCT jf.league_id)
                FROM match_weather mw
                JOIN jackpot_fixtures jf ON mw.fixture_id = jf.id
                WHERE jf.league_id IS NOT NULL
            """)).scalar() or 0
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar() or 0
        
        return ApiResponse(
            data={
                "total_records": total_count or 0,
                "leagues_with_weather": leagues_with_weather,
                "total_leagues": total_leagues,
                "last_updated": last_updated.isoformat() if last_updated and hasattr(last_updated, 'isoformat') and last_updated.year > 1970 else None,
                "by_league": league_counts_list
            },
            success=True,
            message="Weather summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting weather summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/referee/summary", response_model=ApiResponse)
async def get_referee_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for referee stats"""
    try:
        from sqlalchemy import text
        
        # Get total count
        total_count = db.execute(text('SELECT COUNT(*) FROM referee_stats')).scalar()
        
        # Get most recent update
        most_recent = db.execute(text("""
            SELECT MAX(updated_at) as last_updated
            FROM referee_stats
        """)).fetchone()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "last_updated": most_recent.last_updated.isoformat() if most_recent and most_recent.last_updated else None,
                "by_league": []  # Referee stats don't have direct league association
            },
            success=True,
            message="Referee stats summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting referee summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rest-days/summary", response_model=ApiResponse)
async def get_rest_days_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for rest days"""
    try:
        from sqlalchemy import text
        
        # Get total count from both tables (fixtures and historical matches)
        total_fixtures = db.execute(text('SELECT COUNT(*) FROM team_rest_days')).scalar() or 0
        
        # Check if historical table exists
        historical_count = 0
        try:
            historical_count = db.execute(text('SELECT COUNT(*) FROM team_rest_days_historical')).scalar() or 0
        except:
            pass  # Table doesn't exist yet
        
        total_count = total_fixtures + historical_count
        
        # Get count by league from fixtures
        fixture_league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(DISTINCT trd.id) as count
            FROM team_rest_days trd
            JOIN jackpot_fixtures jf ON trd.fixture_id = jf.id
            JOIN leagues l ON jf.league_id = l.id
            WHERE jf.league_id IS NOT NULL
            GROUP BY l.code, l.name
        """)).fetchall()
        
        # Get count by league from historical matches
        historical_league_counts = []
        try:
            historical_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT trdh.id) as count
                FROM team_rest_days_historical trdh
                JOIN matches m ON trdh.match_id = m.id
                JOIN leagues l ON m.league_id = l.id
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass  # Table doesn't exist yet
        
        # Combine league counts
        league_dict = {}
        for row in fixture_league_counts:
            league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        for row in historical_league_counts:
            if row.code in league_dict:
                league_dict[row.code]["count"] += row.count
            else:
                league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        # Get most recent update from both tables
        most_recent_fixtures = db.execute(text("""
            SELECT MAX(created_at) as last_updated
            FROM team_rest_days
        """)).fetchone()
        
        most_recent_historical = None
        try:
            most_recent_historical = db.execute(text("""
                SELECT MAX(created_at) as last_updated
                FROM team_rest_days_historical
            """)).fetchone()
        except:
            pass
        
        # Get the most recent of both
        last_updated = None
        if most_recent_fixtures and most_recent_fixtures.last_updated:
            last_updated = most_recent_fixtures.last_updated
        if most_recent_historical and most_recent_historical.last_updated:
            if not last_updated or most_recent_historical.last_updated > last_updated:
                last_updated = most_recent_historical.last_updated
        
        # Get total leagues with rest days data
        leagues_with_rest_days = len(league_dict)
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_rest_days": leagues_with_rest_days,
                "total_leagues": total_leagues,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "by_league": [
                    {
                        "code": data["code"],
                        "name": data["name"],
                        "count": data["count"]
                    }
                    for data in league_dict.values()
                ]
            },
            success=True,
            message="Rest days summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting rest days summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/odds-movement/summary", response_model=ApiResponse)
async def get_odds_movement_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for odds movement"""
    try:
        from sqlalchemy import text
        
        # Get total count from both tables (fixtures and historical matches)
        total_fixtures = db.execute(text('SELECT COUNT(*) FROM odds_movement')).scalar() or 0
        
        # Check if historical table exists
        historical_count = 0
        try:
            historical_count = db.execute(text('SELECT COUNT(*) FROM odds_movement_historical')).scalar() or 0
        except:
            pass  # Table doesn't exist yet
        
        total_count = total_fixtures + historical_count
        
        # Get count by league from fixtures
        fixture_league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(DISTINCT om.id) as count
            FROM odds_movement om
            JOIN jackpot_fixtures jf ON om.fixture_id = jf.id
            JOIN leagues l ON jf.league_id = l.id
            WHERE jf.league_id IS NOT NULL
            GROUP BY l.code, l.name
        """)).fetchall()
        
        # Get count by league from historical matches
        historical_league_counts = []
        try:
            historical_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT omh.id) as count
                FROM odds_movement_historical omh
                JOIN matches m ON omh.match_id = m.id
                JOIN leagues l ON m.league_id = l.id
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass  # Table doesn't exist yet
        
        # Combine league counts
        league_dict = {}
        for row in fixture_league_counts:
            league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        for row in historical_league_counts:
            if row.code in league_dict:
                league_dict[row.code]["count"] += row.count
            else:
                league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        # Get most recent update from both tables
        most_recent_fixtures = db.execute(text("""
            SELECT MAX(recorded_at) as last_updated
            FROM odds_movement
        """)).fetchone()
        
        most_recent_historical = None
        try:
            most_recent_historical = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM odds_movement_historical
            """)).fetchone()
        except:
            pass
        
        # Get the most recent of both
        last_updated = None
        if most_recent_fixtures and most_recent_fixtures.last_updated:
            last_updated = most_recent_fixtures.last_updated
        if most_recent_historical and most_recent_historical.last_updated:
            if not last_updated or most_recent_historical.last_updated > last_updated:
                last_updated = most_recent_historical.last_updated
        
        # Get total leagues with odds movement data
        leagues_with_odds = len(league_dict)
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_odds": leagues_with_odds,
                "total_leagues": total_leagues,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "by_league": [
                    {
                        "code": data["code"],
                        "name": data["name"],
                        "count": data["count"]
                    }
                    for data in league_dict.values()
                ]
            },
            success=True,
            message="Odds movement summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting odds movement summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/league-structure", response_model=ApiResponse)
async def ingest_league_structure(
    request: IngestLeagueStructureRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest league structure metadata"""
    try:
        from app.services.ingestion.ingest_league_structure import ingest_league_structure
        
        result = ingest_league_structure(
            db=db,
            league_code=request.league_code,
            season=request.season,
            total_teams=request.total_teams,
            relegation_zones=request.relegation_zones,
            promotion_zones=request.promotion_zones,
            playoff_zones=request.playoff_zones,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="League structure ingested successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting league structure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/league-structure/batch", response_model=ApiResponse)
async def batch_ingest_league_structure(
    request: BatchIngestLeagueStructureRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest league structure for multiple leagues and seasons"""
    try:
        from app.services.ingestion.ingest_league_structure import batch_ingest_league_structure
        
        # Convert season "ALL" to None
        season = None if request.season == "ALL" else request.season
        
        result = batch_ingest_league_structure(
            db=db,
            league_codes=request.league_codes,
            use_all_leagues=request.use_all_leagues,
            season=season,
            use_all_seasons=request.use_all_seasons,
            max_years=request.max_years or 10,
            save_csv=request.save_csv
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Batch ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"League structure batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch league structure ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/league-structure/summary", response_model=ApiResponse)
async def get_league_structure_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for league structure"""
    try:
        from sqlalchemy import text
        
        # Get total count
        total_count = db.execute(text('SELECT COUNT(*) FROM league_structure')).scalar()
        
        # Get count by league
        league_counts = db.execute(text("""
            SELECT l.code, l.name, COUNT(ls.id) as count
            FROM league_structure ls
            JOIN leagues l ON ls.league_id = l.id
            GROUP BY l.code, l.name
            ORDER BY count DESC
        """)).fetchall()
        
        # Get most recent update
        most_recent = db.execute(text("""
            SELECT MAX(updated_at) as last_updated
            FROM league_structure
        """)).fetchone()
        
        # Get total leagues with structure data
        leagues_with_structure = db.execute(text("""
            SELECT COUNT(DISTINCT league_id)
            FROM league_structure
        """)).scalar()
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_structure": leagues_with_structure,
                "total_leagues": total_leagues,
                "last_updated": most_recent.last_updated.isoformat() if most_recent and most_recent.last_updated else None,
                "by_league": [
                    {
                        "code": row.code,
                        "name": row.name,
                        "count": row.count
                    }
                    for row in league_counts
                ]
            },
            success=True,
            message="League structure summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting league structure summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xg-data", response_model=ApiResponse)
async def ingest_xg_data(
    request: IngestXGDataRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Ingest xG data for a fixture or match"""
    try:
        from app.services.ingestion.ingest_xg_data import ingest_xg_for_fixture, ingest_xg_for_match
        
        if request.fixture_id:
            result = ingest_xg_for_fixture(
                db=db,
                fixture_id=request.fixture_id,
                xg_home=request.xg_home,
                xg_away=request.xg_away
            )
        elif request.match_id:
            result = ingest_xg_for_match(
                db=db,
                match_id=request.match_id,
                xg_home=request.xg_home,
                xg_away=request.xg_away
            )
        else:
            raise HTTPException(status_code=400, detail="Either fixture_id or match_id must be provided")
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
        
        return ApiResponse(
            data=result,
            success=True,
            message="xG data ingested successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting xG data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xg-data/batch", response_model=ApiResponse)
async def batch_ingest_xg_data(
    request: BatchIngestXGDataRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch ingest xG data for multiple leagues and seasons"""
    try:
        from app.services.ingestion.ingest_xg_data import batch_ingest_xg_from_matches
        from app.services.data_ingestion import get_seasons_list
        
        # Convert league codes to league IDs if needed
        league_ids = None
        if request.league_codes:
            from sqlalchemy import text
            league_ids = [
                row.id for row in db.execute(
                    text("SELECT id FROM leagues WHERE code = ANY(:codes)"),
                    {"codes": request.league_codes}
                ).fetchall()
            ]
        
        # Convert season "ALL" to None
        seasons = None if request.season == "ALL" else [request.season] if request.season else None
        
        if request.use_all_seasons and request.max_years:
            seasons = get_seasons_list(request.max_years)
        
        result = batch_ingest_xg_from_matches(
            db=db,
            league_ids=league_ids,
            seasons=seasons,
            max_years=request.max_years if not seasons else None
        )
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"xG data batch ingestion complete: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch xG data ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/injuries", response_model=ApiResponse)
async def record_injuries(
    request: IngestInjuriesRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Record injury data for a team in a fixture"""
    try:
        from app.services.injury_tracking import record_team_injuries
        
        result = record_team_injuries(
            db=db,
            team_id=request.team_id,
            fixture_id=request.fixture_id,
            key_players_missing=request.key_players_missing,
            injury_severity=request.injury_severity,
            attackers_missing=request.attackers_missing,
            midfielders_missing=request.midfielders_missing,
            defenders_missing=request.defenders_missing,
            goalkeepers_missing=request.goalkeepers_missing,
            notes=request.notes
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to record injuries"))
        
        return ApiResponse(
            data=result,
            success=True,
            message=f"Injuries recorded successfully ({result.get('action', 'created')})"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording injuries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/injuries/{fixture_id}/{team_id}", response_model=ApiResponse)
async def get_injuries(
    fixture_id: int,
    team_id: int,
    db: Session = Depends(get_db)
):
    """Get injury data for a team in a fixture"""
    try:
        from app.services.injury_tracking import get_team_injuries_for_fixture
        
        injuries = get_team_injuries_for_fixture(db, team_id, fixture_id)
        
        if not injuries:
            return ApiResponse(
                data=None,
                success=True,
                message="No injury data found for this team/fixture"
            )
        
        return ApiResponse(
            data={
                "id": injuries.id,
                "team_id": injuries.team_id,
                "fixture_id": injuries.fixture_id,
                "key_players_missing": injuries.key_players_missing,
                "injury_severity": injuries.injury_severity,
                "attackers_missing": injuries.attackers_missing,
                "midfielders_missing": injuries.midfielders_missing,
                "defenders_missing": injuries.defenders_missing,
                "goalkeepers_missing": injuries.goalkeepers_missing,
                "notes": injuries.notes,
                "recorded_at": injuries.recorded_at.isoformat() if injuries.recorded_at else None
            },
            success=True,
            message="Injury data retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting injuries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/injuries/batch", response_model=ApiResponse)
async def batch_record_injuries(
    request: BatchIngestInjuriesRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Batch record injuries for multiple teams/fixtures"""
    try:
        from app.services.injury_tracking import record_team_injuries
        
        results = []
        successful = 0
        failed = 0
        
        for injury_request in request.injuries:
            try:
                result = record_team_injuries(
                    db=db,
                    team_id=injury_request.team_id,
                    fixture_id=injury_request.fixture_id,
                    key_players_missing=injury_request.key_players_missing,
                    injury_severity=injury_request.injury_severity,
                    attackers_missing=injury_request.attackers_missing,
                    midfielders_missing=injury_request.midfielders_missing,
                    defenders_missing=injury_request.defenders_missing,
                    goalkeepers_missing=injury_request.goalkeepers_missing,
                    notes=injury_request.notes
                )
                
                if result.get("success"):
                    successful += 1
                else:
                    failed += 1
                
                results.append({
                    "team_id": injury_request.team_id,
                    "fixture_id": injury_request.fixture_id,
                    "success": result.get("success"),
                    "error": result.get("error")
                })
            except Exception as e:
                failed += 1
                results.append({
                    "team_id": injury_request.team_id,
                    "fixture_id": injury_request.fixture_id,
                    "success": False,
                    "error": str(e)
                })
        
        return ApiResponse(
            data={
                "successful": successful,
                "failed": failed,
                "total": len(request.injuries),
                "results": results
            },
            success=True,
            message=f"Injuries recorded: {successful} successful, {failed} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch injury recording: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xg-data/summary", response_model=ApiResponse)
async def get_xg_data_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for xG data"""
    try:
        from sqlalchemy import text
        
        # Get total count from both tables (fixtures and historical matches)
        total_fixtures = 0
        try:
            total_fixtures = db.execute(text('SELECT COUNT(*) FROM match_xg')).scalar() or 0
        except:
            pass  # Table doesn't exist yet
        
        # Check if historical table exists
        historical_count = 0
        try:
            historical_count = db.execute(text('SELECT COUNT(*) FROM match_xg_historical')).scalar() or 0
        except:
            pass  # Table doesn't exist yet
        
        total_count = total_fixtures + historical_count
        
        # Get count by league from fixtures
        fixture_league_counts = []
        try:
            fixture_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT mx.id) as count
                FROM match_xg mx
                JOIN jackpot_fixtures jf ON mx.fixture_id = jf.id
                JOIN leagues l ON jf.league_id = l.id
                WHERE jf.league_id IS NOT NULL
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass  # Table doesn't exist yet
        
        # Get count by league from historical matches
        historical_league_counts = []
        try:
            historical_league_counts = db.execute(text("""
                SELECT l.code, l.name, COUNT(DISTINCT mxh.id) as count
                FROM match_xg_historical mxh
                JOIN matches m ON mxh.match_id = m.id
                JOIN leagues l ON m.league_id = l.id
                GROUP BY l.code, l.name
            """)).fetchall()
        except:
            pass  # Table doesn't exist yet
        
        # Combine league counts
        league_dict = {}
        for row in fixture_league_counts:
            league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        for row in historical_league_counts:
            if row.code in league_dict:
                league_dict[row.code]["count"] += row.count
            else:
                league_dict[row.code] = {"code": row.code, "name": row.name, "count": row.count}
        
        # Get most recent update from both tables
        most_recent_fixtures = None
        try:
            most_recent_fixtures = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM match_xg
            """)).fetchone()
        except:
            pass
        
        most_recent_historical = None
        try:
            most_recent_historical = db.execute(text("""
                SELECT MAX(recorded_at) as last_updated
                FROM match_xg_historical
            """)).fetchone()
        except:
            pass
        
        # Get the most recent of both
        last_updated = None
        if most_recent_fixtures and most_recent_fixtures.last_updated:
            last_updated = most_recent_fixtures.last_updated
        if most_recent_historical and most_recent_historical.last_updated:
            if not last_updated or most_recent_historical.last_updated > last_updated:
                last_updated = most_recent_historical.last_updated
        
        # Get total leagues with xG data
        leagues_with_xg = len(league_dict)
        
        # Get total leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        
        return ApiResponse(
            data={
                "total_records": total_count,
                "leagues_with_xg": leagues_with_xg,
                "total_leagues": total_leagues,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "by_league": [
                    {
                        "code": data["code"],
                        "name": data["name"],
                        "count": data["count"]
                    }
                    for data in league_dict.values()
                ]
            },
            success=True,
            message="xG data summary retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting xG data summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-all", response_model=ApiResponse)
async def import_all_draw_structural_data(
    request: BatchIngestRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Import all draw structural data in one click.
    
    Order of import:
    1. League Draw Priors
    2. League Structure
    3. Elo Ratings
    4. H2H Stats
    5. Odds Movement
    6. Referee Stats
    7. Rest Days
    8. XG Data
    9. Weather (LAST)
    
    Args:
        use_all_leagues: Import for all leagues
        use_all_seasons: Import for all seasons
        max_years: Maximum years to look back (if use_all_seasons=True)
        league_codes: Optional list of league codes to import (if use_all_leagues=False)
    
    Returns:
        Dict with import statistics for each data type
    """
    try:
        results = {
            "league_priors": {"success": False, "message": "Not started"},
            "league_structure": {"success": False, "message": "Not started"},
            "elo_ratings": {"success": False, "message": "Not started"},
            "h2h_stats": {"success": False, "message": "Not started"},
            "odds_movement": {"success": False, "message": "Not started"},
            "referee_stats": {"success": False, "message": "Not started"},
            "rest_days": {"success": False, "message": "Not started"},
            "xg_data": {"success": False, "message": "Not started"},
            "weather": {"success": False, "message": "Not started"}
        }
        
        # Extract parameters from request
        use_all_leagues = request.use_all_leagues
        use_all_seasons = request.use_all_seasons
        max_years = request.max_years
        league_codes = request.league_codes
        use_hybrid_import = request.use_hybrid_import
        
        # 1. League Draw Priors
        try:
            if use_hybrid_import:
                # Use hybrid CSV-first approach
                from app.services.ingestion.hybrid_import import hybrid_import_league_priors
                result = hybrid_import_league_priors(
                    db,
                    league_codes=league_codes,
                    seasons=None,  # Will be determined from CSV files
                    use_all_leagues=use_all_leagues,
                    use_all_seasons=use_all_seasons,
                    max_years=max_years,
                    save_csv=True
                )
                logger.info(f"✓ League Draw Priors (Hybrid): {result.get('csv_imported', 0)} from CSV, {result.get('calculated', 0)} calculated")
            else:
                # Use traditional calculate-from-matches approach
                from app.services.ingestion.ingest_league_draw_priors import batch_ingest_league_priors
                result = batch_ingest_league_priors(
                    db,
                    league_codes=league_codes,
                    use_all_leagues=use_all_leagues,
                    use_all_seasons=use_all_seasons,
                    max_years=max_years,
                    save_csv=True
                )
                logger.info(f"✓ League Draw Priors: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
            results["league_priors"] = result
        except Exception as e:
            logger.error(f"Error importing league priors: {e}", exc_info=True)
            results["league_priors"] = {"success": False, "error": str(e)}
        
        # 2. League Structure
        try:
            from app.services.ingestion.ingest_league_structure import batch_ingest_league_structure
            result = batch_ingest_league_structure(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["league_structure"] = result
            logger.info(f"✓ League Structure: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing league structure: {e}", exc_info=True)
            results["league_structure"] = {"success": False, "error": str(e)}
        
        # 3. Elo Ratings
        try:
            from app.services.ingestion.ingest_elo_ratings import batch_calculate_elo_from_matches
            result = batch_calculate_elo_from_matches(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                season=None,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["elo_ratings"] = result
            logger.info(f"✓ Elo Ratings: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing Elo ratings: {e}", exc_info=True)
            results["elo_ratings"] = {"success": False, "error": str(e)}
        
        # 4. H2H Stats
        try:
            from app.services.ingestion.ingest_h2h_stats import batch_ingest_h2h_stats
            result = batch_ingest_h2h_stats(
                db,
                league_codes=league_codes,
                season="ALL",
                use_all_leagues=use_all_leagues,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["h2h_stats"] = result
            logger.info(f"✓ H2H Stats: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing H2H stats: {e}", exc_info=True)
            results["h2h_stats"] = {"success": False, "error": str(e)}
        
        # 5. Odds Movement
        try:
            from app.services.ingestion.ingest_odds_movement import batch_ingest_odds_movement_from_matches
            result = batch_ingest_odds_movement_from_matches(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                season=None,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["odds_movement"] = result
            logger.info(f"✓ Odds Movement: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing odds movement: {e}", exc_info=True)
            results["odds_movement"] = {"success": False, "error": str(e)}
        
        # 6. Referee Stats
        try:
            from app.services.ingestion.ingest_referee_stats import batch_ingest_referee_stats
            result = batch_ingest_referee_stats(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                season=None,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["referee_stats"] = result
            logger.info(f"✓ Referee Stats: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing referee stats: {e}", exc_info=True)
            results["referee_stats"] = {"success": False, "error": str(e)}
        
        # 7. Rest Days
        try:
            from app.services.ingestion.ingest_rest_days import batch_ingest_rest_days_from_matches
            result = batch_ingest_rest_days_from_matches(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                season=None,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["rest_days"] = result
            logger.info(f"✓ Rest Days: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing rest days: {e}", exc_info=True)
            results["rest_days"] = {"success": False, "error": str(e)}
        
        # 8. XG Data
        try:
            from app.services.ingestion.ingest_xg_data import batch_ingest_xg_from_matches
            from app.db.models import League
            # Convert league_codes to league_ids if needed
            league_ids = None
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
            elif use_all_leagues:
                leagues = db.query(League).all()
                league_ids = [l.id for l in leagues]
            
            # Get seasons list
            seasons = None
            if use_all_seasons:
                from app.services.data_ingestion import get_seasons_list
                seasons = get_seasons_list(max_years)
            
            result = batch_ingest_xg_from_matches(
                db,
                league_ids=league_ids,
                seasons=seasons,
                max_years=max_years
            )
            results["xg_data"] = result
            logger.info(f"✓ XG Data: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing xG data: {e}", exc_info=True)
            results["xg_data"] = {"success": False, "error": str(e)}
        
        # 9. Weather (LAST)
        try:
            from app.services.ingestion.ingest_weather import batch_ingest_weather_from_matches
            result = batch_ingest_weather_from_matches(
                db,
                league_codes=league_codes,
                use_all_leagues=use_all_leagues,
                season=None,
                use_all_seasons=use_all_seasons,
                max_years=max_years,
                save_csv=True
            )
            results["weather"] = result
            logger.info(f"✓ Weather: {result.get('successful', 0)} successful, {result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Error importing weather: {e}", exc_info=True)
            results["weather"] = {"success": False, "error": str(e)}
        
        # Calculate summary
        total_successful = sum(
            r.get("successful", 0) if isinstance(r, dict) and "successful" in r else 0
            for r in results.values()
        )
        total_failed = sum(
            r.get("failed", 0) if isinstance(r, dict) and "failed" in r else 0
            for r in results.values()
        )
        
        all_success = all(
            r.get("success", False) if isinstance(r, dict) else False
            for r in results.values()
        )
        
        return ApiResponse(
            data={
                "results": results,
                "summary": {
                    "total_successful": total_successful,
                    "total_failed": total_failed,
                    "all_completed": all_success
                }
            },
            success=all_success,
            message=f"Import completed: {total_successful} successful, {total_failed} failed"
        )
    except Exception as e:
        logger.error(f"Error in batch import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

