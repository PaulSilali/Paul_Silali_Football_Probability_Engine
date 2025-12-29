"""
Audit Log API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import AuditEntry
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    jackpot_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get audit log entries
    
    Returns paginated audit log with optional filtering
    """
    offset = (page - 1) * page_size
    
    query = db.query(AuditEntry)
    
    if jackpot_id:
        query = query.filter(AuditEntry.jackpot_id == jackpot_id)
    
    total = query.count()
    entries = query.order_by(
        AuditEntry.timestamp.desc()
    ).offset(offset).limit(page_size).all()
    
    return {
        "data": [
            {
                "id": str(entry.id),
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "modelVersion": entry.model_version,
                "probabilitySet": entry.probability_set,
                "jackpotId": entry.jackpot_id,
                "details": entry.details
            }
            for entry in entries
        ],
        "total": total,
        "page": page,
        "pageSize": page_size
    }


def create_audit_entry(
    db: Session,
    action: str,
    model_version: Optional[str] = None,
    probability_set: Optional[str] = None,
    jackpot_id: Optional[str] = None,
    details: Optional[str] = None,
    user_id: Optional[int] = None
) -> AuditEntry:
    """Helper function to create audit entries"""
    entry = AuditEntry(
        action=action,
        model_version=model_version,
        probability_set=probability_set,
        jackpot_id=jackpot_id,
        details=details,
        user_id=user_id
    )
    db.add(entry)
    db.commit()
    return entry

