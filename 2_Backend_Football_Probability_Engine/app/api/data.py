"""
Data Ingestion API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.data_ingestion import DataIngestionService, create_default_leagues
from app.db.models import DataSource, IngestionLog
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

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
        league_code: Optional league code
        season: Optional season code
    """
    try:
        service = DataIngestionService(db)
        
        if source == "football-data.co.uk":
            if not league_code or not season:
                raise HTTPException(
                    status_code=400,
                    detail="league_code and season required for football-data.co.uk"
                )
            
            stats = service.ingest_from_football_data(league_code, season)
            
            return {
                "data": {
                    "id": f"task-{int(datetime.now().timestamp())}",
                    "source": source,
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
        
        service = DataIngestionService(db)
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

