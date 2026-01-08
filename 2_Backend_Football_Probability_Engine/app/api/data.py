"""
Data Ingestion API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.services.data_ingestion import DataIngestionService, create_default_leagues, get_seasons_list
from app.config import settings
from app.db.models import DataSource, IngestionLog, League, Match
from app.schemas.jackpot import ApiResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["data"])




@router.post("/updates")
async def trigger_data_update(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Trigger data update from external source
    
    Matches frontend API contract: POST /api/data/updates
    Body: { "source": "football-data.co.uk" }
    """
    try:
        source = request.get("source", "")
        
        if not source:
            raise HTTPException(status_code=400, detail="source is required")
        
        # For now, return task ID (would queue Celery task in production)
        task_id = f"task-{int(datetime.now().timestamp())}"
        
        return {
            "data": {
                "id": task_id,
                "source": source,
                "status": "pending",
                "progress": 0,
                "startedAt": datetime.now().isoformat()
            },
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering data update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def trigger_data_refresh(
    source: str,
    league_code: Optional[str] = None,
    season: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger data refresh from external source (with league/season)
    
    Args:
        source: Data source name ('football-data.co.uk', 'api-football', etc.)
        league_code: League code (e.g., 'E0' for Premier League)
        season: Season code (e.g., '2324' for 2023-24) or 'all' for all seasons (max 7 years)
    
    Returns:
        Response with batch number and ingestion statistics
    """
    try:
        service = DataIngestionService(
            db,
            enable_cleaning=settings.ENABLE_DATA_CLEANING
        )
        
        if source == "football-data.co.uk":
            if not league_code:
                raise HTTPException(
                    status_code=400,
                    detail="league_code is required for football-data.co.uk"
                )
            
            if not season:
                raise HTTPException(
                    status_code=400,
                    detail="season is required (e.g., '2324' or 'all')"
                )
            
            # Convert season format if needed (e.g., "2023-24" -> "2324")
            from app.services.data_ingestion import get_season_code, get_seasons_list
            season_code = get_season_code(season)
            
            # Determine season display text and number of seasons
            if season_code == "last7":
                num_seasons = 7
                season_display = f"Last 7 Seasons ({len(get_seasons_list(7))} seasons)"
            elif season_code == "last10":
                num_seasons = 10
                season_display = f"Last 10 Seasons ({len(get_seasons_list(10))} seasons)"
            elif season_code == "all":
                num_seasons = 7
                season_display = f"All Seasons ({len(get_seasons_list())} seasons)"
            else:
                num_seasons = 1
                season_display = season_code
            
            # Create download session folder name: {DownloadDate}_Seasons_{No of Seasons}_Leagues_{no of leagues}
            download_date = datetime.now().strftime("%Y-%m-%d")
            download_session_folder = f"{download_date}_Seasons_{num_seasons}_Leagues_1"  # 1 league for single download
            
            # Start ingestion (batch number will be assigned from ingestion_log.id)
            stats = service.ingest_from_football_data(
                league_code, 
                season_code,
                save_csv=True,
                download_session_folder=download_session_folder
            )
            
            # Get batch number from stats
            batch_number = stats.get("batch_number", stats.get("ingestion_log_id"))
            
            return {
                "data": {
                    "id": f"task-{int(datetime.now().timestamp())}",
                    "batchNumber": batch_number,
                    "source": source,
                    "leagueCode": league_code,
                    "season": season_display,
                    "status": "completed",
                    "progress": 100,
                    "startedAt": datetime.now().isoformat(),
                    "completedAt": datetime.now().isoformat(),
                    "stats": stats
                },
                "success": True
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown source: {source}"
            )
    
    except Exception as e:
        logger.error(f"Error refreshing data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    league_code: str = None,
    season: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload and ingest CSV file
    
    Expected format: Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,AvgH,AvgD,AvgA
    """
    if not league_code or not season:
        raise HTTPException(
            status_code=400,
            detail="league_code and season are required"
        )
    
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        service = DataIngestionService(
            db,
            enable_cleaning=settings.ENABLE_DATA_CLEANING
        )
        stats = service.ingest_csv(csv_content, league_code, season)
        
        return {
            "data": {
                "status": "completed",
                "stats": stats
            },
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/freshness")
async def get_data_freshness(
    db: Session = Depends(get_db)
):
    """Get data freshness status for all sources"""
    sources = db.query(DataSource).all()
    
    return {
        "data": [
            {
                "source": source.name,
                "lastUpdated": source.last_sync_at.isoformat() if source.last_sync_at else None,
                "recordCount": source.record_count,
                "status": source.status
            }
            for source in sources
        ],
        "success": True
    }


@router.get("/updates")
async def get_data_updates(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """Get data ingestion logs"""
    offset = (page - 1) * page_size
    
    logs = db.query(IngestionLog).order_by(
        IngestionLog.started_at.desc()
    ).offset(offset).limit(page_size).all()
    
    total = db.query(IngestionLog).count()
    
    return {
        "data": [
            {
                "id": str(log.id),
                "source": log.source.name if log.source else "unknown",
                "status": log.status,
                "progress": int((log.records_processed / max(log.records_processed, 1)) * 100),
                "startedAt": log.started_at.isoformat(),
                "completedAt": log.completed_at.isoformat() if log.completed_at else None,
                "recordsProcessed": log.records_processed,
                "recordsInserted": log.records_inserted,
                "recordsUpdated": log.records_updated,
                "recordsSkipped": log.records_skipped
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "pageSize": page_size
    }


@router.post("/prepare-training-data")
async def prepare_training_data_endpoint(
    request: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Prepare cleaned training data files per league
    
    Combines all seasons per league into single CSV/Parquet files
    Optimized for model training workflows
    
    Request body:
        - league_codes: Optional[List[str]] - List of league codes (None = all leagues)
        - format: str - Output format ("csv", "parquet", or "both", default: "both")
    
    Returns:
        Preparation statistics and file paths
    """
    try:
        from app.services.data_preparation import DataPreparationService
        
        league_codes = request.get("league_codes")
        format_type = request.get("format", "both")
        
        service = DataPreparationService(db)
        
        if league_codes:
            results = []
            for code in league_codes:
                stats = service.prepare_league_data(code, format=format_type)
                results.append(stats)
            return {
                "success": True,
                "data": {
                    "leagues": results,
                    "total_matches": sum(r["matches_count"] for r in results),
                    "output_directory": str(service.output_dir)
                }
            }
        else:
            summary = service.prepare_all_leagues(format=format_type)
            return {
                "success": True,
                "data": summary
            }
    
    except Exception as e:
        logger.error(f"Error preparing training data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/league-stats")
async def get_league_stats(
    db: Session = Depends(get_db)
):
    """
    Get statistics for each league (record counts and last updated dates)
    
    Returns:
        Dict mapping league codes to their statistics
    """
    try:
        import json
        
        # Query match counts and last match dates per league
        league_stats_query = db.query(
            League.code,
            League.name,
            func.count(Match.id).label('record_count'),
            func.max(Match.match_date).label('last_match_date')
        ).outerjoin(
            Match, League.id == Match.league_id
        ).group_by(
            League.id, League.code, League.name
        ).all()
        
        # Get last ingestion dates per league from IngestionLog
        # Query all completed logs and extract league codes from logs JSON
        ingestion_dates = {}
        logs = db.query(IngestionLog).filter(
            IngestionLog.status == "completed",
            IngestionLog.completed_at.isnot(None)
        ).all()
        
        for log in logs:
            logs_data = log.logs or {}
            if isinstance(logs_data, str):
                try:
                    logs_data = json.loads(logs_data)
                except:
                    logs_data = {}
            
            # Try both possible JSON keys
            league_code = logs_data.get('league_code') or logs_data.get('leagueCode')
            if league_code and log.completed_at:
                # Keep the most recent date for each league
                if league_code not in ingestion_dates or ingestion_dates[league_code] < log.completed_at:
                    ingestion_dates[league_code] = log.completed_at
        
        # Build result dictionary
        stats = {}
        for row in league_stats_query:
            # Get the most recent date (either last match or last ingestion)
            last_updated = None
            if row.code in ingestion_dates:
                last_updated = ingestion_dates[row.code].strftime('%Y-%m-%d')
            elif row.last_match_date:
                last_updated = row.last_match_date.strftime('%Y-%m-%d')
            
            stats[row.code] = {
                'name': row.name,
                'recordCount': row.record_count or 0,
                'lastUpdated': last_updated
            }
        
        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting league stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", response_model=ApiResponse)
async def get_batch_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get batch history with database and file system information"""
    from pathlib import Path
    
    # Get completed ingestion logs from database
    logs = db.query(IngestionLog).filter(
        IngestionLog.status == "completed"
    ).order_by(
        IngestionLog.started_at.desc()
    ).limit(limit).all()
    
    # Also get DataSource names in a separate query for efficiency
    source_ids = {log.source_id for log in logs if log.source_id}
    sources_map = {}
    if source_ids:
        sources = db.query(DataSource).filter(DataSource.id.in_(source_ids)).all()
        sources_map = {s.id: s.name for s in sources}
    
    # Get file system batches
    # Use absolute path relative to backend root directory
    backend_root = Path(__file__).parent.parent.parent  # Go up from app/api/data.py to backend root
    data_dir = backend_root / "data" / "1_data_ingestion"
    historical_data_dir = data_dir / "Historical Match_Odds_Data"
    file_batches = {}
    
    # Get league names mapping for display
    leagues_map = {}
    all_leagues = db.query(League).all()
    for league in all_leagues:
        leagues_map[league.code] = league.name
    
    # Check new structure: Historical Match_Odds_Data/{session_folder}/{league_code}/*.csv
    if historical_data_dir.exists():
        for session_folder in historical_data_dir.iterdir():
            if session_folder.is_dir():
                # Look for league code folders inside session folder
                league_details = {}  # Track league details with names
                for league_folder in session_folder.iterdir():
                    if league_folder.is_dir():
                        csv_files = list(league_folder.glob("*.csv"))
                        if csv_files:
                            folder_name = league_folder.name
                            # Parse folder name: could be "Premier League (E0)" or just "E0"
                            league_code = None
                            league_name = folder_name
                            
                            # Check if folder name contains league code in parentheses
                            match = re.match(r'^(.+?)\s*\(([A-Z0-9]+)\)$', folder_name)
                            if match:
                                league_name = match.group(1).strip()
                                league_code = match.group(2)
                            else:
                                # Try to match by code directly
                                if folder_name in leagues_map:
                                    league_code = folder_name
                                    league_name = leagues_map[league_code]
                                else:
                                    # Use folder name as both
                                    league_code = folder_name
                                    league_name = leagues_map.get(league_code, league_code)
                            
                            # Extract league code from CSV filenames if not found
                            if not league_code:
                                for csv_file in csv_files:
                                    parts = csv_file.stem.split('_')
                                    if len(parts) >= 1:
                                        potential_code = parts[0]
                                        if potential_code in leagues_map:
                                            league_code = potential_code
                                            league_name = leagues_map[league_code]
                                            break
                            
                            # Extract league codes and seasons from filenames
                            seasons = set()
                            for csv_file in csv_files:
                                parts = csv_file.stem.split('_')
                                if len(parts) >= 2:
                                    # Use the extracted league_code or first part of filename
                                    if not league_code:
                                        league_code = parts[0]
                                        league_name = leagues_map.get(league_code, league_code)
                                    seasons.add(parts[1])
                            
                            # Store league details with name
                            if league_code:
                                league_details[league_code] = {
                                    "code": league_code,
                                    "name": league_name,
                                    "csvCount": len(csv_files),
                                    "seasons": sorted(list(seasons)),
                                    "files": [f.name for f in csv_files]
                                }
                
                # Group by session folder and aggregate all leagues
                if league_details:
                    session_key = session_folder.name
                    all_leagues_in_session = list(league_details.keys())
                    all_seasons = set()
                    total_csv_count = 0
                    all_files = []
                    
                    for league_info in league_details.values():
                        all_seasons.update(league_info["seasons"])
                        total_csv_count += league_info["csvCount"]
                        all_files.extend(league_info["files"])
                    
                    file_batches[session_key] = {
                        "folderName": session_folder.name,
                        "csvCount": total_csv_count,
                        "leagues": sorted(all_leagues_in_session),
                        "leagueDetails": league_details,  # Include full details with names
                        "seasons": sorted(list(all_seasons)),
                        "files": all_files
                    }
    
    # Also check old structure: data/1_data_ingestion/batch_* (for backward compatibility)
    if data_dir.exists():
        for batch_folder in data_dir.glob("batch_*"):
            if batch_folder.is_dir():
                # Extract batch number from folder name (e.g., "batch_176_Premier_League" -> 176)
                folder_name = batch_folder.name
                try:
                    # Try to extract batch number (handles both "batch_176" and "batch_176_League_Name")
                    batch_num_str = folder_name.split('_')[1]
                    batch_num = int(batch_num_str)
                    
                    csv_files = list(batch_folder.glob("*.csv"))
                    if csv_files:
                        # Extract league codes and seasons from filenames
                        leagues = set()
                        seasons = set()
                        for csv_file in csv_files:
                            parts = csv_file.stem.split('_')
                            if len(parts) >= 2:
                                leagues.add(parts[0])
                                seasons.add(parts[1])
                        
                        # Use batch number as key for old structure
                        if batch_num not in file_batches:
                            file_batches[batch_num] = {
                                "batchNumber": batch_num,
                                "folderName": folder_name,
                                "csvCount": len(csv_files),
                                "leagues": set(),
                                "seasons": set(),
                                "files": []
                            }
                        
                        file_batches[batch_num]["csvCount"] += len(csv_files)
                        file_batches[batch_num]["leagues"].update(leagues)
                        file_batches[batch_num]["seasons"].update(seasons)
                        file_batches[batch_num]["files"].extend([f.name for f in csv_files])
                except (ValueError, IndexError):
                    continue
    
    # Convert sets to sorted lists for JSON serialization
    for key in file_batches:
        if isinstance(file_batches[key]["leagues"], set):
            file_batches[key]["leagues"] = sorted(list(file_batches[key]["leagues"]))
        if isinstance(file_batches[key]["seasons"], set):
            file_batches[key]["seasons"] = sorted(list(file_batches[key]["seasons"]))
    
    # Combine database logs with file system data
    batch_list = []
    for log in logs:
        source_name = sources_map.get(log.source_id, "unknown") if log.source_id else "unknown"
        
        # Try to find matching files for this batch
        file_info = None
        has_files = False
        
        # Check if log has download_session_folder to match new structure
        if log.logs and isinstance(log.logs, dict):
            download_session = log.logs.get("download_session_folder")
            if download_session and download_session in file_batches:
                # Match by download session folder (new structure)
                file_info = file_batches[download_session]
                has_files = True
            elif log.id in file_batches:
                # Match by batch number (old structure)
                file_info = file_batches[log.id]
                has_files = True
        
        batch_info = {
            "id": str(log.id),
            "batchNumber": log.id,
            "source": source_name,
            "status": log.status,
            "startedAt": log.started_at.isoformat(),
            "completedAt": log.completed_at.isoformat() if log.completed_at else None,
            "recordsProcessed": log.records_processed or 0,
            "recordsInserted": log.records_inserted or 0,
            "recordsUpdated": log.records_updated or 0,
            "recordsSkipped": log.records_skipped or 0,
            "hasFiles": has_files,
            "fileInfo": file_info
        }
        
        # Extract league info from logs JSON if available
        if log.logs and isinstance(log.logs, dict):
            if "league_code" in log.logs:
                batch_info["leagueCode"] = log.logs.get("league_code")
            if "season" in log.logs:
                batch_info["season"] = log.logs.get("season")
        
        batch_list.append(batch_info)
    
    # Add file-only batches (batches that exist in file system but not in DB)
    db_batch_numbers = {log.id for log in logs}
    db_session_folders = set()
    if logs:
        for log in logs:
            if log.logs and isinstance(log.logs, dict):
                session_folder = log.logs.get("download_session_folder")
                if session_folder:
                    db_session_folders.add(session_folder)
    
    for batch_key, file_info in file_batches.items():
        # For new structure (session folders), add if not matched to a DB log
        if isinstance(batch_key, str) and batch_key not in db_session_folders:
            # Create a synthetic batch entry for file-only data
            batch_list.append({
                "id": f"file_{batch_key}",
                "batchNumber": 0,  # Use 0 for file-only batches to sort them last
                "source": "file_system",
                "status": "completed",
                "startedAt": None,
                "completedAt": None,
                "recordsProcessed": 0,
                "recordsInserted": 0,
                "recordsUpdated": 0,
                "recordsSkipped": 0,
                "hasFiles": True,
                "fileInfo": file_info
            })
        # For old structure (batch numbers), add if not in DB
        elif isinstance(batch_key, int) and batch_key not in db_batch_numbers:
            batch_list.append({
                "id": f"file_{batch_key}",
                "batchNumber": batch_key,
                "source": "file_system",
                "status": "completed",
                "startedAt": None,
                "completedAt": None,
                "recordsProcessed": 0,
                "recordsInserted": 0,
                "recordsUpdated": 0,
                "recordsSkipped": 0,
                "hasFiles": True,
                "fileInfo": file_info
            })
    
    # Sort by batch number descending
    batch_list.sort(key=lambda x: x["batchNumber"], reverse=True)
    
    # Calculate summary statistics
    total_batches = len(batch_list)
    total_records = sum(b["recordsInserted"] for b in batch_list)
    total_files = sum(b["fileInfo"]["csvCount"] if b.get("fileInfo") else 0 for b in batch_list)
    unique_leagues = set()
    for b in batch_list:
        if b.get("fileInfo") and b["fileInfo"].get("leagues"):
            unique_leagues.update(b["fileInfo"]["leagues"])
        elif b.get("leagueCode"):
            unique_leagues.add(b["leagueCode"])
    
    return ApiResponse(
        success=True,
        data={
            "batches": batch_list[:limit],
            "summary": {
                "totalBatches": total_batches,
                "totalRecords": total_records,
                "totalFiles": total_files,
                "uniqueLeagues": len(unique_leagues),
                "leagues": sorted(list(unique_leagues))
            }
        }
    )


@router.get("/league-stats")
async def get_league_stats(
    db: Session = Depends(get_db)
):
    """
    Get statistics for each league (record counts and last updated dates)
    
    Returns:
        Dict mapping league codes to their statistics
    """
    try:
        # Query match counts and last updated dates per league
        league_stats_query = db.query(
            League.code,
            League.name,
            func.count(Match.id).label('record_count'),
            func.max(Match.match_date).label('last_match_date'),
            func.max(IngestionLog.completed_at).label('last_ingestion')
        ).outerjoin(
            Match, League.id == Match.league_id
        ).outerjoin(
            IngestionLog, 
            (IngestionLog.logs['league_code'].astext == League.code) | 
            (IngestionLog.logs['leagueCode'].astext == League.code)
        ).group_by(
            League.id, League.code, League.name
        ).all()
        
        # Build result dictionary
        stats = {}
        for row in league_stats_query:
            # Get the most recent date (either last match or last ingestion)
            last_updated = None
            if row.last_ingestion:
                last_updated = row.last_ingestion.strftime('%Y-%m-%d')
            elif row.last_match_date:
                last_updated = row.last_match_date.strftime('%Y-%m-%d')
            
            stats[row.code] = {
                'name': row.name,
                'recordCount': row.record_count or 0,
                'lastUpdated': last_updated
            }
        
        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting league stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-download")
async def batch_download(
    request: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Download multiple leagues/seasons in a single batch
    
    Body:
        {
            "source": "football-data.co.uk",
            "leagues": [{"code": "E0", "season": "2324"}, ...],
            "season": "all"  # Optional: if provided, applies to all leagues
        }
    """
    try:
        source = request.get("source", "football-data.co.uk")
        leagues = request.get("leagues", [])
        season_override = request.get("season")  # Optional: "all" or specific season
        
        if not leagues:
            raise HTTPException(status_code=400, detail="leagues array is required")
        
        service = DataIngestionService(
            db,
            enable_cleaning=settings.ENABLE_DATA_CLEANING
        )
        
        # Get or create data source (ensure it exists and is committed before using)
        from app.db.models import DataSource, IngestionLog
        data_source = db.query(DataSource).filter(
            DataSource.name == source
        ).first()
        
        if not data_source:
            data_source = DataSource(
                name=source,
                source_type="csv",
                status="running"
            )
            db.add(data_source)
            db.flush()  # Flush to get the ID
            # Commit the data_source to ensure it exists in the database before foreign key reference
            db.commit()
            # Refresh the object to ensure it's properly loaded
            db.refresh(data_source)
        
        # Verify data_source has a valid ID
        if not data_source or not data_source.id:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get or create data source: {source}"
            )
        
        results = []
        total_stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        batch_numbers = []  # Track all batch numbers created
        
        # Create download session folder name: {DownloadDate}_Seasons_{No of Seasons}_Leagues_{no of leagues}
        download_date = datetime.now().strftime("%Y-%m-%d")
        
        # Determine number of seasons
        if season_override:
            if season_override in ["last7", "all"]:
                num_seasons = 7
            elif season_override == "last10":
                num_seasons = 10
            else:
                num_seasons = 1
        else:
            # Check if any league has multi-season
            num_seasons = 1
            for league_item in leagues:
                league_season = league_item.get("season", "all")
                if league_season in ["last7", "all"]:
                    num_seasons = 7
                    break
                elif league_season == "last10":
                    num_seasons = 10
                    break
        
        num_leagues = len(leagues)
        download_session_folder = f"{download_date}_Seasons_{num_seasons}_Leagues_{num_leagues}"
        
        # Create ONE batch PER LEAGUE (not per download operation)
        for league_item in leagues:
            league_code = league_item.get("code")
            season = season_override or league_item.get("season", "all")
            
            if not league_code:
                continue
            
            try:
                # Create one batch per league
                # data_source is already committed, so its ID is valid
                league_batch_log = IngestionLog(
                    source_id=data_source.id,
                    status="running"
                )
                db.add(league_batch_log)
                db.flush()
                league_batch_number = league_batch_log.id
                batch_numbers.append(league_batch_number)
                
                from app.services.data_ingestion import get_season_code
                season_code = get_season_code(season)
                
                stats = service.ingest_from_football_data(
                    league_code,
                    season_code,
                    batch_number=league_batch_number,  # One batch per league
                    save_csv=True,
                    download_session_folder=download_session_folder
                )
                
                # Refresh the log from DB to get updates from ingest_csv
                # ingest_csv already updates: status, completed_at, records_*, error_message, logs
                # Re-query to ensure it's in the session (in case of rollbacks)
                try:
                    league_batch_log = db.query(IngestionLog).filter(
                        IngestionLog.id == league_batch_number
                    ).first()
                except Exception:
                    # If query fails, try to refresh existing object
                    try:
                        db.refresh(league_batch_log)
                    except Exception:
                        # If refresh also fails, re-query
                        league_batch_log = db.query(IngestionLog).filter(
                            IngestionLog.id == league_batch_number
                        ).first()
                
                # Only update if log exists (it might be None if there was an error)
                if league_batch_log:
                    # Ensure status is completed (ingest_csv should have set this, but double-check)
                    if league_batch_log.status != "completed":
                        league_batch_log.status = "completed"
                        league_batch_log.completed_at = league_batch_log.completed_at or datetime.now()
                    
                    # Merge logs JSON (preserve detailed logs from ingest_csv, add batch metadata if missing)
                    existing_logs = league_batch_log.logs or {}
                    if not existing_logs.get("batch_number"):
                        existing_logs["batch_number"] = league_batch_number
                    if not existing_logs.get("league_code"):
                        existing_logs["league_code"] = league_code
                    if not existing_logs.get("season"):
                        existing_logs["season"] = season_code
                    existing_logs["download_session_folder"] = download_session_folder
                    league_batch_log.logs = existing_logs
                    
                    db.commit()
                
                results.append({
                    "leagueCode": league_code,
                    "season": season_code,
                    "stats": stats,
                    "batchNumber": league_batch_number
                })
                
                total_stats["processed"] += stats.get("processed", 0)
                total_stats["inserted"] += stats.get("inserted", 0)
                total_stats["updated"] += stats.get("updated", 0)
                total_stats["skipped"] += stats.get("skipped", 0)
                total_stats["errors"] += stats.get("errors", 0)
                
            except Exception as e:
                logger.error(f"Error downloading {league_code}: {e}", exc_info=True)
                # Rollback any failed transaction
                db.rollback()
                
                # Try to update the batch log if it exists
                if 'league_batch_number' in locals():
                    try:
                        # Re-query the log to ensure it's in the session (after rollback)
                        league_batch_log = db.query(IngestionLog).filter(
                            IngestionLog.id == league_batch_number
                        ).first()
                        if league_batch_log:
                            league_batch_log.status = "failed"
                            league_batch_log.completed_at = datetime.now()
                            league_batch_log.error_message = str(e)
                            db.commit()
                    except Exception as log_error:
                        logger.error(f"Error updating batch log: {log_error}", exc_info=True)
                        try:
                            db.rollback()
                        except Exception:
                            pass
                
                results.append({
                    "leagueCode": league_code,
                    "season": season_code if 'season_code' in locals() else season,
                    "error": str(e),
                    "is_404": "404" in str(e) or "Not Found" in str(e)
                })
                total_stats["errors"] += 1
        
        # Create download summary for log file
        successful_downloads = []
        failed_downloads = []
        no_data_downloads = []  # Leagues that completed but have 0 records (all 404s)
        
        for result in results:
            if "error" in result:
                failed_downloads.append({
                    "league_code": result.get("leagueCode"),
                    "season": result.get("season", "Unknown"),
                    "error": result.get("error"),
                    "is_404": result.get("is_404", False)
                })
            else:
                stats = result.get("stats", {})
                processed = stats.get("processed", 0)
                
                # Only count as successful if it has actual data (records > 0)
                if processed > 0:
                    successful_downloads.append({
                        "league_code": result.get("leagueCode"),
                        "season": result.get("season", "Unknown"),
                        "stats": stats,
                        "batch_number": result.get("batchNumber")
                    })
                else:
                    # Completed but no data (all seasons returned 404)
                    no_data_downloads.append({
                        "league_code": result.get("leagueCode"),
                        "season": result.get("season", "Unknown"),
                        "stats": stats,
                        "batch_number": result.get("batchNumber"),
                        "reason": "No data available (all seasons returned 404)"
                    })
        
        download_summary = {
            "total_leagues": len(leagues),
            "successful": len(successful_downloads),  # Only leagues with actual data
            "failed": len(failed_downloads),
            "no_data": len(no_data_downloads),  # Leagues with 0 records
            "total_processed": total_stats["processed"],
            "total_inserted": total_stats["inserted"],
            "total_updated": total_stats["updated"],
            "total_skipped": total_stats["skipped"],
            "total_errors": total_stats["errors"],
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "no_data_downloads": no_data_downloads,  # Track leagues with no data
            "missing_data": []  # Can be populated if we track expected vs actual
        }
        
        # Write download log to session folder
        try:
            service._write_download_log(download_session_folder, download_summary)
        except Exception as log_error:
            logger.error(f"Failed to write download log: {log_error}", exc_info=True)
            # Don't fail the entire operation if log writing fails
        
        return {
            "data": {
                "batchId": f"batch-{batch_numbers[0] if batch_numbers else 'unknown'}",
                "batchNumbers": batch_numbers,  # All batch numbers created
                "source": source,
                "totalStats": total_stats,
                "results": results,
                "completedAt": datetime.now().isoformat(),
                "downloadSessionFolder": download_session_folder
            },
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Error in batch download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-leagues")
async def init_leagues(
    db: Session = Depends(get_db)
):
    """Initialize default leagues (development helper)"""
    try:
        create_default_leagues(db)
        return {
            "success": True,
            "message": "Default leagues created"
        }
    except Exception as e:
        logger.error(f"Error initializing leagues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

