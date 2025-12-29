"""
Pydantic Schemas for API Requests/Responses
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings


class MarketOdds(BaseModel):
    """Market odds for a fixture (1X2 format)."""
    home: float = Field(..., ge=settings.MIN_VALID_ODDS, le=settings.MAX_VALID_ODDS)
    draw: float = Field(..., ge=settings.MIN_VALID_ODDS, le=settings.MAX_VALID_ODDS)
    away: float = Field(..., ge=settings.MIN_VALID_ODDS, le=settings.MAX_VALID_ODDS)


class FixtureInput(BaseModel):
    """Single fixture input."""
    id: str
    homeTeam: str = Field(..., min_length=2, max_length=100)
    awayTeam: str = Field(..., min_length=2, max_length=100)
    odds: Optional[MarketOdds] = None
    matchDate: Optional[str] = None
    league: Optional[str] = None


class JackpotInput(BaseModel):
    """Complete jackpot input request."""
    fixtures: List[FixtureInput] = Field(..., min_length=1, max_length=20)
    createdAt: datetime


class MatchProbabilitiesOutput(BaseModel):
    """Match outcome probabilities."""
    homeWinProbability: float = Field(..., ge=0.0, le=1.0)
    drawProbability: float = Field(..., ge=0.0, le=1.0)
    awayWinProbability: float = Field(..., ge=0.0, le=1.0)
    entropy: Optional[float] = Field(None, ge=0.0)
    confidenceLow: Optional[float] = None
    confidenceHigh: Optional[float] = None
    
    @field_validator('homeWinProbability', 'drawProbability', 'awayWinProbability')
    @classmethod
    def validate_probability_sum(cls, v, info):
        """Validate that probabilities sum to 1.0."""
        if hasattr(info, 'data'):
            total = (
                info.data.get('homeWinProbability', 0) +
                info.data.get('drawProbability', 0) +
                info.data.get('awayWinProbability', 0)
            )
            if abs(total - 1.0) > settings.PROBABILITY_SUM_TOLERANCE:
                raise ValueError(f"Probabilities must sum to 1.0, got {total}")
        return v


class FixtureProbability(BaseModel):
    """Probability output for a single fixture."""
    fixtureId: str
    homeTeam: str
    awayTeam: str
    homeWinProbability: float
    drawProbability: float
    awayWinProbability: float
    confidenceLow: Optional[float] = None
    confidenceHigh: Optional[float] = None


class ProbabilitySet(BaseModel):
    """Probabilities for all fixtures in a set."""
    id: str
    name: str
    description: str
    probabilities: List[FixtureProbability]


class PredictionWarning(BaseModel):
    """Warning about a prediction."""
    fixtureId: str
    type: str
    message: str
    severity: str


class PredictionResponse(BaseModel):
    """Complete prediction response."""
    predictionId: str
    modelVersion: str
    createdAt: datetime
    fixtures: List[FixtureInput]
    probabilitySets: Dict[str, List[MatchProbabilitiesOutput]]
    confidenceFlags: Dict[int, str]
    warnings: Optional[List[PredictionWarning]] = None


class ModelVersionResponse(BaseModel):
    """Model version information."""
    version: str
    trainedAt: datetime
    dataVersion: str
    validationMetrics: Dict[str, float]
    status: str


class ModelHealthResponse(BaseModel):
    """Model health status."""
    status: str
    lastChecked: datetime
    metrics: Dict[str, float]
    alerts: List[Dict]
    driftIndicators: List[Dict]

