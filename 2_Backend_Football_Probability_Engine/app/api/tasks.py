"""
Task Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])

# In-memory task store (replace with Redis/Celery in production)
task_store: Dict[str, dict] = {}


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get task status by ID"""
    # Check in-memory store
    if task_id in task_store:
        return task_store[task_id]
    
    # Check database for training runs, ingestion logs, etc.
    # For now, return not found
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running task"""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_store[task_id]["status"] = "cancelled"
    return {"success": True, "message": "Task cancelled"}

