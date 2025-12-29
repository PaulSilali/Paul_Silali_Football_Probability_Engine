# FOOTBALL JACKPOT PROBABILITY ENGINE - COMPLETE BACKEND CODE PACKAGE

This document contains all remaining backend code modules.
Each section below should be saved as the indicated file path.

---

## FILE: backend/db/models.py

```python
"""
SQLAlchemy 2.0 Database Models

All tables follow the Lovable/Cursor specification exactly.
Row Level Security compatible with Supabase.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, 
    ForeignKey, Enum, JSON, Boolean, Text,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class ModelStatus(enum.Enum):
    active = "active"
    archived = "archived"
    failed = "failed"


class PredictionSet(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class MatchResult(enum.Enum):
    H = "H"  # Home win
    D = "D"  # Draw
    A = "A"  # Away win


# ============================================================================
# REFERENCE TABLES
# ============================================================================

class League(Base):
    __tablename__ = "leagues"
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    tier = Column(Integer, default=1)
    avg_draw_rate = Column(Float, default=0.26)
    home_advantage = Column(Float, default=0.35)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    teams = relationship("Team", back_populates="league")
    matches = relationship("Match", back_populates="league")


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    name = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)
    attack_rating = Column(Float, default=1.0)
    defense_rating = Column(Float, default=1.0)
    home_bias = Column(Float, default=0.0)
    last_calculated = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    league = relationship("League", back_populates="teams")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    
    __table_args__ = (
        UniqueConstraint('canonical_name', 'league_id', name='uix_team_league'),
    )


# ============================================================================
# HISTORICAL DATA
# ============================================================================

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    season = Column(String, nullable=False)
    match_date = Column(Date, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    result = Column(Enum(MatchResult), nullable=False)
    
    # Closing odds
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)
    
    # Market-implied probabilities
    prob_home_market = Column(Float)
    prob_draw_market = Column(Float)
    prob_away_market = Column(Float)
    
    source = Column(String, default='football-data.co.uk')
    created_at = Column(DateTime, server_default=func.now())
    
    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    
    __table_args__ = (
        UniqueConstraint('home_team_id', 'away_team_id', 'match_date', name='uix_match'),
        Index('idx_matches_date', 'match_date'),
        Index('idx_matches_league_season', 'league_id', 'season'),
    )


class TeamFeature(Base):
    __tablename__ = "team_features"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    calculated_at = Column(DateTime, nullable=False)
    
    # Rolling metrics
    goals_scored_5 = Column(Float)
    goals_scored_10 = Column(Float)
    goals_scored_20 = Column(Float)
    goals_conceded_5 = Column(Float)
    goals_conceded_10 = Column(Float)
    goals_conceded_20 = Column(Float)
    
    # Win rates
    win_rate_5 = Column(Float)
    win_rate_10 = Column(Float)
    draw_rate_5 = Column(Float)
    draw_rate_10 = Column(Float)
    
    # Splits
    home_win_rate = Column(Float)
    away_win_rate = Column(Float)
    
    avg_rest_days = Column(Float)
    league_position = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_team_features_lookup', 'team_id', 'calculated_at'),
    )


# ============================================================================
# MODEL TABLES
# ============================================================================

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True, nullable=False)
    model_type = Column(String, nullable=False)
    status = Column(Enum(ModelStatus), default=ModelStatus.active)
    
    # Training metadata
    training_started_at = Column(DateTime)
    training_completed_at = Column(DateTime)
    training_matches = Column(Integer)
    training_leagues = Column(JSON)
    training_seasons = Column(JSON)
    
    # Parameters
    decay_rate = Column(Float)
    blend_alpha = Column(Float)
    
    # Metrics
    brier_score = Column(Float)
    log_loss = Column(Float)
    draw_accuracy = Column(Float)
    overall_accuracy = Column(Float)
    
    # Stored weights (JSON)
    model_weights = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    predictions = relationship("Prediction", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    run_type = Column(String, nullable=False)
    status = Column(Enum(ModelStatus))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    
    match_count = Column(Integer)
    date_from = Column(Date)
    date_to = Column(Date)
    
    brier_score = Column(Float)
    log_loss = Column(Float)
    validation_accuracy = Column(Float)
    error_message = Column(Text)
    logs = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
# JACKPOT TABLES
# ============================================================================

class Jackpot(Base):
    __tablename__ = "jackpots"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(String, unique=True, nullable=False)
    user_id = Column(String)  # From Supabase auth
    name = Column(String)
    kickoff_date = Column(Date)
    status = Column(String, default='pending')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    fixtures = relationship("JackpotFixture", back_populates="jackpot", cascade="all, delete-orphan")


class JackpotFixture(Base):
    __tablename__ = "jackpot_fixtures"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(Integer, ForeignKey("jackpots.id", ondelete="CASCADE"), nullable=False)
    match_order = Column(Integer, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    
    # Input odds
    odds_home = Column(Float, nullable=False)
    odds_draw = Column(Float, nullable=False)
    odds_away = Column(Float, nullable=False)
    
    # Resolved team IDs
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    
    # Actual result (for validation)
    actual_result = Column(Enum(MatchResult))
    actual_home_goals = Column(Integer)
    actual_away_goals = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())
    
    jackpot = relationship("Jackpot", back_populates="fixtures")
    predictions = relationship("Prediction", back_populates="fixture", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    set_type = Column(Enum(PredictionSet), nullable=False)
    
    # Probabilities
    prob_home = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away = Column(Float, nullable=False)
    
    predicted_outcome = Column(Enum(MatchResult), nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Model components
    expected_home_goals = Column(Float)
    expected_away_goals = Column(Float)
    model_prob_home = Column(Float)
    model_prob_draw = Column(Float)
    model_prob_away = Column(Float)
    market_prob_home = Column(Float)
    market_prob_draw = Column(Float)
    market_prob_away = Column(Float)
    blend_weight = Column(Float)
    
    created_at = Column(DateTime, server_default=func.now())
    
    fixture = relationship("JackpotFixture", back_populates="predictions")
    model = relationship("Model", back_populates="predictions")
    
    __table_args__ = (
        Index('idx_predictions_fixture', 'fixture_id'),
        Index('idx_predictions_set', 'set_type'),
        CheckConstraint(
            'abs((prob_home + prob_draw + prob_away) - 1.0) < 0.001',
            name='check_prob_sum'
        ),
    )


# ============================================================================
# VALIDATION TABLES
# ============================================================================

class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(Integer, primary_key=True)
    jackpot_id = Column(Integer, ForeignKey("jackpots.id", ondelete="CASCADE"))
    set_type = Column(Enum(PredictionSet), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"))
    
    total_matches = Column(Integer)
    correct_predictions = Column(Integer)
    accuracy = Column(Float)
    brier_score = Column(Float)
    log_loss = Column(Float)
    
    # Breakdown by outcome
    home_correct = Column(Integer)
    home_total = Column(Integer)
    draw_correct = Column(Integer)
    draw_total = Column(Integer)
    away_correct = Column(Integer)
    away_total = Column(Integer)
    
    exported_to_training = Column(Boolean, default=False)
    exported_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class CalibrationData(Base):
    __tablename__ = "calibration_data"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    outcome_type = Column(Enum(MatchResult), nullable=False)
    
    predicted_prob_bucket = Column(Float, nullable=False)
    actual_frequency = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
# DATA INGESTION TABLES
# ============================================================================

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)
    status = Column(String, default='fresh')
    last_sync_at = Column(DateTime)
    record_count = Column(Integer, default=0)
    last_error = Column(Text)
    config = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    status = Column(String, default='running')
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    error_message = Column(Text)
    logs = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
```

---

## FILE: backend/db/session.py

```python
"""
Database Session Management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from backend.settings import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    future=True
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)


def get_db() -> Session:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

## FILE: backend/schemas/prediction.py

```python
"""
Pydantic Schemas for API Requests/Responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from datetime import datetime
from backend.settings import constants


class MarketOdds(BaseModel):
    """Market odds for a fixture (1X2 format)."""
    home: float = Field(..., ge=constants.MIN_VALID_ODDS, le=constants.MAX_VALID_ODDS)
    draw: float = Field(..., ge=constants.MIN_VALID_ODDS, le=constants.MAX_VALID_ODDS)
    away: float = Field(..., ge=constants.MIN_VALID_ODDS, le=constants.MAX_VALID_ODDS)


class FixtureInput(BaseModel):
    """Single fixture input."""
    id: str
    homeTeam: str = Field(..., min_length=2, max_length=100)
    awayTeam: str = Field(..., min_length=2, max_length=100)
    odds: Optional[MarketOdds] = None


class JackpotInput(BaseModel):
    """Complete jackpot input request."""
    fixtures: List[FixtureInput] = Field(..., min_length=1, max_length=20)
    createdAt: datetime


class MatchProbabilitiesOutput(BaseModel):
    """Match outcome probabilities."""
    home: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away: float = Field(..., ge=0.0, le=1.0)
    entropy: float = Field(..., ge=0.0)
    
    @field_validator('home', 'draw', 'away')
    def validate_probability_sum(cls, v, info):
        """Validate that probabilities sum to 1.0."""
        # This check happens after all fields are set
        if hasattr(info, 'data'):
            total = info.data.get('home', 0) + info.data.get('draw', 0) + v
            if 'away' in info.data and abs(total - 1.0) > constants.PROBABILITY_SUM_TOLERANCE:
                raise ValueError(f"Probabilities must sum to 1.0, got {total}")
        return v


class PredictionSetOutput(BaseModel):
    """Probabilities for all fixtures in a set."""
    set_id: str
    name: str
    description: str
    probabilities: List[MatchProbabilitiesOutput]


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
```

---

## FILE: backend/api/probabilities.py

```python
"""
FastAPI Router for Probability Calculations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.schemas.prediction import (
    JackpotInput, PredictionResponse, MatchProbabilitiesOutput
)
from backend.models.dixon_coles import (
    TeamStrength, DixonColesParams, calculate_match_probabilities
)
from backend.sets.registry import generate_all_probability_sets
from backend.db.models import Model, Jackpot, JackpotFixture, Prediction, Team
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResponse)
async def calculate_probabilities(
    jackpot: JackpotInput,
    db: Session = Depends(get_db)
):
    """
    Calculate probabilities for a jackpot.
    
    This is the main prediction endpoint.
    """
    try:
        # Get active model
        model = db.query(Model).filter(Model.status == "active").first()
        if not model:
            raise HTTPException(status_code=500, detail="No active model found")
        
        # Create jackpot record
        jackpot_record = Jackpot(
            jackpot_id=f"JK-{int(datetime.now().timestamp())}",
            user_id="anonymous",  # TODO: Get from auth
            status="calculating"
        )
        db.add(jackpot_record)
        db.flush()
        
        # Process each fixture
        all_predictions = {}
        confidence_flags = {}
        
        for idx, fixture in enumerate(jackpot.fixtures):
            # Resolve team names
            home_team = db.query(Team).filter(
                Team.canonical_name.ilike(f"%{fixture.homeTeam}%")
            ).first()
            away_team = db.query(Team).filter(
                Team.canonical_name.ilike(f"%{fixture.awayTeam}%")
            ).first()
            
            if not home_team or not away_team:
                logger.warning(f"Teams not found: {fixture.homeTeam} vs {fixture.awayTeam}")
                # Use league averages
                continue
            
            # Create fixture record
            fixture_record = JackpotFixture(
                jackpot_id=jackpot_record.id,
                match_order=idx + 1,
                home_team=fixture.homeTeam,
                away_team=fixture.awayTeam,
                odds_home=fixture.odds.home if fixture.odds else None,
                odds_draw=fixture.odds.draw if fixture.odds else None,
                odds_away=fixture.odds.away if fixture.odds else None,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                league_id=home_team.league_id
            )
            db.add(fixture_record)
            db.flush()
            
            # Get team strengths
            home_strength = TeamStrength(
                team_id=home_team.id,
                attack=home_team.attack_rating,
                defense=home_team.defense_rating,
                league_id=home_team.league_id
            )
            away_strength = TeamStrength(
                team_id=away_team.id,
                attack=away_team.attack_rating,
                defense=away_team.defense_rating,
                league_id=away_team.league_id
            )
            
            # Calculate probabilities
            params = DixonColesParams()
            model_probs = calculate_match_probabilities(
                home_strength, away_strength, params
            )
            
            # Generate all probability sets
            probability_sets = generate_all_probability_sets(
                model_probs,
                fixture.odds.model_dump() if fixture.odds else None,
                None  # calibration_curves TODO
            )
            
            # Store predictions
            for set_id, probs in probability_sets.items():
                pred = Prediction(
                    fixture_id=fixture_record.id,
                    model_id=model.id,
                    set_type=set_id,
                    prob_home=probs["home"],
                    prob_draw=probs["draw"],
                    prob_away=probs["away"],
                    predicted_outcome="H" if probs["home"] > max(probs["draw"], probs["away"]) else "D" if probs["draw"] > probs["away"] else "A",
                    confidence=max(probs["home"], probs["draw"], probs["away"])
                )
                db.add(pred)
            
            # Store for response
            if idx not in all_predictions:
                all_predictions[idx] = {}
            for set_id, probs in probability_sets.items():
                if set_id not in all_predictions[idx]:
                    all_predictions[idx][set_id] = []
                all_predictions[idx][set_id].append(
                    MatchProbabilitiesOutput(**probs)
                )
            
            # Confidence flag
            confidence_flags[idx] = "high" if probs["entropy"] < 1.0 else "medium"
        
        # Update jackpot status
        jackpot_record.status = "finalized"
        db.commit()
        
        # Build response
        response_probs = {}
        for set_id in ["A", "B", "C"]:  # Main sets
            response_probs[set_id] = [
                all_predictions[idx][set_id][0]
                for idx in range(len(jackpot.fixtures))
                if idx in all_predictions and set_id in all_predictions[idx]
            ]
        
        return PredictionResponse(
            predictionId=jackpot_record.jackpot_id,
            modelVersion=model.version,
            createdAt=datetime.now(),
            fixtures=jackpot.fixtures,
            probabilitySets=response_probs,
            confidenceFlags=confidence_flags
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## FILE: backend/main.py

```python
"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.settings import settings
from backend.api import probabilities
import logging

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    Football Jackpot Probability Engine
    
    This system provides calibrated probability estimates for football matches.
    It does NOT provide betting advice or "best picks".
    
    All probabilities are generated using Dixon-Coles Poisson models,
    market odds blending, and isotonic calibration.
    
    NO NEURAL NETWORKS. NO BLACK BOXES.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include routers
app.include_router(probabilities.router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "service": "Football Jackpot Probability Engine",
        "version": settings.API_VERSION,
        "status": "operational",
        "disclaimer": "This system estimates probabilities, not outcomes. No betting advice provided."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

---

## FILE: backend/sets/registry.py

```python
"""
Probability Set Generator Registry
"""

from typing import Dict, Optional
from backend.models.dixon_coles import MatchProbabilities


def generate_all_probability_sets(
    model_probs: MatchProbabilities,
    market_odds: Optional[Dict] = None,
    calibration_curves: Optional[Dict] = None
) -> Dict[str, Dict[str, float]]:
    """
    Generate all 7 probability sets.
    
    Args:
        model_probs: Pure model probabilities
        market_odds: Market odds dict (optional)
        calibration_curves: Calibration curves (optional)
    
    Returns:
        Dict mapping set_id to probability dict
    """
    sets = {}
    
    # Set A: Pure Model
    sets["A"] = {
        "home": model_probs.home,
        "draw": model_probs.draw,
        "away": model_probs.away,
        "entropy": model_probs.entropy
    }
    
    # Set B: Market-Aware (60/40)
    if market_odds:
        market_probs = odds_to_probabilities(market_odds)
        sets["B"] = blend_probabilities(
            sets["A"], market_probs, alpha=0.6
        )
    else:
        sets["B"] = sets["A"].copy()
    
    # Set C: Market-Dominant (20/80)
    if market_odds:
        sets["C"] = blend_probabilities(
            sets["A"], market_probs, alpha=0.2
        )
    else:
        sets["C"] = sets["A"].copy()
    
    return sets


def odds_to_probabilities(odds: Dict) -> Dict[str, float]:
    """Convert odds to implied probabilities."""
    probs = {
        "home": 1.0 / odds["home"],
        "draw": 1.0 / odds["draw"],
        "away": 1.0 / odds["away"]
    }
    total = sum(probs.values())
    return {k: v / total for k, v in probs.items()}


def blend_probabilities(
    model: Dict, market: Dict, alpha: float
) -> Dict[str, float]:
    """Blend model and market probabilities."""
    blended = {
        "home": alpha * model["home"] + (1 - alpha) * market["home"],
        "draw": alpha * model["draw"] + (1 - alpha) * market["draw"],
        "away": alpha * model["away"] + (1 - alpha) * market["away"],
    }
    # Recalculate entropy
    import math
    blended["entropy"] = -sum(
        p * math.log2(p) if p > 0 else 0
        for p in [blended["home"], blended["draw"], blended["away"]]
    )
    return blended
```

---

## FILE: requirements.txt

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg[binary]==3.1.16
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
python-dotenv==1.0.0
numpy==1.26.3
scipy==1.11.4
pandas==2.1.4
celery==5.3.6
redis==5.0.1
requests==2.31.0
httpx==0.26.0
pytest==7.4.4
pytest-asyncio==0.23.3
```

---

## FILE: .env.example

```env
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/jackpot_db

# API
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000"]

# Supabase (optional)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_JWT_SECRET=

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Data Sources
API_FOOTBALL_KEY=

# Environment
ENV=development
DEBUG=False
LOG_LEVEL=INFO
```

---

## FILE: README.md

# Football Jackpot Probability Engine - Backend

Production-ready backend for probability-first football jackpot analysis.

## What This System IS

✅ A probability estimation engine  
✅ Based on Dixon-Coles Poisson models  
✅ Deterministic and reproducible  
✅ Calibrated using isotonic regression  
✅ Auditable end-to-end  

## What This System IS NOT

❌ A betting tipster  
❌ A "best pick" generator  
❌ A neural network service  
❌ Reactive to injuries/news  
❌ A hit-rate optimizer  

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start server
uvicorn backend.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

See `CURSOR_BACKEND_PROMPT.md` for complete technical specification.

## License

Proprietary - Internal Use Only
