"""
Jackpot schemas
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.prediction import FixtureInput


class Jackpot(BaseModel):
    """Jackpot model"""
    id: str
    name: Optional[str] = None
    fixtures: List[FixtureInput]
    createdAt: datetime
    modelVersion: str
    status: str


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    data: dict
    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response"""
    data: List[dict]
    total: int
    page: int
    pageSize: int

