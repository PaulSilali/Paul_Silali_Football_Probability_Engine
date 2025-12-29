# FOOTBALL JACKPOT PROBABILITY ENGINE - COMPLETE BACKEND CODE
## Production-Ready Python Backend - Part 1: Core Models & Database

**Generated from Cursor Backend Master Prompt**
**NO NEURAL NETWORKS. NO BLACK BOXES. REGULATOR-DEFENSIBLE.**

---

## FILE: backend/settings.py

```python
"""
Application Settings - Deterministic Configuration

CRITICAL: All parameters must be reproducible and auditable.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration with validation."""
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://user:pass@localhost:5432/jackpot_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # API
    API_TITLE: str = "Football Jackpot Probability Engine"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Supabase JWT (optional)
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Dixon-Coles Parameters (IMMUTABLE)
    DIXON_COLES_RHO: float = -0.13  # Dependency parameter
    TIME_DECAY_XI: float = 0.0065   # Per-day decay (half-life ~106 days)
    HOME_ADVANTAGE: float = 0.35    # Goals
    MAX_GOALS: int = 8              # For probability matrix
    
    # Blending
    DEFAULT_BLEND_ALPHA: float = 0.6  # Model weight
    MAX_MARKET_WEIGHT: float = 0.7    # Hard cap on market dominance
    
    # Calibration
    MIN_CALIBRATION_SAMPLES: int = 30
    CALIBRATION_BINS: int = 20
    
    # Validation
    BRIER_SCORE_THRESHOLD: float = 0.22
    
    # System
    ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
```

---

## FILE: backend/db/base.py

```python
"""
SQLAlchemy Base Declaration
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass
```

---

## FILE: backend/db/models.py

```python
"""
Database Models - Exact Schema from Cursor/Lovable Specification

NO gambling tables.
NO mutable predictions.
IMMUTABLE jackpot versions.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Enum, JSON, Boolean, Text,
    UniqueConstraint, CheckConstraint, Index, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum
from datetime import datetime
from uuid import uuid4


# ============================================================================
# ENUMS
# ============================================================================

class ModelStatus(enum.Enum):
    active = "active"
    archived = "archived"
    failed = "failed"


class PredictionSet(enum.Enum):
    A = "A"  # Pure model
    B = "B"  # Market-aware
    C = "C"  # Conservative
    D = "D"  # Draw-boosted
    E = "E"  # Entropy-penalized
    F = "F"  # Kelly-weighted
    G = "G"  # Ensemble


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
    code = Column(String, unique=True, nullable=False)  # 'E0', 'SP1', etc.
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    tier = Column(Integer, default=1)
    avg_draw_rate = Column(Float, default=0.26)
    home_advantage = Column(Float, default=0.35)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    teams = relationship("Team", back_populates="league")
    matches = relationship("Match", back_populates="league")


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    name = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)  # Normalized for matching
    attack_rating = Column(Float, default=1.0)
    defense_rating = Column(Float, default=1.0)
    home_bias = Column(Float, default=0.0)
    last_calculated = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    league = relationship("League", back_populates="teams")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    features = relationship("TeamFeature", back_populates="team")
    
    __table_args__ = (
        UniqueConstraint('canonical_name', 'league_id', name='uix_team_league'),
        Index('idx_teams_canonical', 'canonical_name'),
    )


# ============================================================================
# HISTORICAL DATA
# ============================================================================

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(BigInteger, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    season = Column(String, nullable=False)  # '2023-24'
    match_date = Column(Date, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer, nullable=False)
    away_goals = Column(Integer, nullable=False)
    result = Column(Enum(MatchResult), nullable=False)
    
    # Closing odds ONLY (no in-play, no opening)
    closing_odds = Column(JSON, nullable=False)  # {home, draw, away}
    
    # Market-implied probabilities (after margin removal)
    prob_home_market = Column(Float)
    prob_draw_market = Column(Float)
    prob_away_market = Column(Float)
    
    source = Column(String, default='football-data.co.uk')
    snapshot_date = Column(Date, nullable=False)  # When data was ingested
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season', 'match_date', 'home_team_id', 'away_team_id', 
                        name='uix_match'),
        Index('idx_matches_date', 'match_date'),
        Index('idx_matches_league_season', 'league_id', 'season'),
        Index('idx_matches_snapshot', 'snapshot_date'),
    )


class TeamFeature(Base):
    __tablename__ = "team_features"
    
    id = Column(BigInteger, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    feature_version = Column(String, nullable=False)  # For reproducibility
    
    # Team strength (from Dixon-Coles)
    attack_strength = Column(Float, nullable=False)
    defense_strength = Column(Float, nullable=False)
    home_advantage = Column(Float, nullable=False)
    
    # Exponential decay parameter used
    decay_lambda = Column(Float, nullable=False)
    
    # Rolling statistics (5, 10, 20 matches)
    goals_scored_5 = Column(Float)
    goals_scored_10 = Column(Float)
    goals_scored_20 = Column(Float)
    goals_conceded_5 = Column(Float)
    goals_conceded_10 = Column(Float)
    goals_conceded_20 = Column(Float)
    
    win_rate_5 = Column(Float)
    win_rate_10 = Column(Float)
    draw_rate_5 = Column(Float)
    draw_rate_10 = Column(Float)
    
    home_win_rate = Column(Float)
    away_win_rate = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    team = relationship("Team", back_populates="features")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'snapshot_date', 'feature_version', name='uix_team_feature'),
        Index('idx_team_features_lookup', 'team_id', 'snapshot_date'),
    )


# ============================================================================
# MODEL REGISTRY
# ============================================================================

class Model(Base):
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))  # UUID as string
    version = Column(String, unique=True, nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    model_type = Column(String, nullable=False)  # 'dixon-coles'
    status = Column(Enum(ModelStatus), default=ModelStatus.active)
    
    # Training metadata
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_matches = Column(Integer)
    training_seasons = Column(JSON)  # ['2020-21', '2021-22', ...]
    
    # Parameters (IMMUTABLE after training)
    parameters = Column(JSON, nullable=False)  # {rho, xi, home_advantage, ...}
    
    # Validation metrics
    brier_score = Column(Float)
    log_loss = Column(Float)
    calibration_error = Column(Float)
    
    # Stored weights
    team_strengths = Column(JSON)  # {team_id: {attack, defense}}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    training_runs = relationship("TrainingRun", back_populates="model")
    predictions = relationship("Prediction", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    run_type = Column(String, nullable=False)  # 'full', 'incremental'
    status = Column(Enum(ModelStatus), default=ModelStatus.active)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Data range
    data_start = Column(Date, nullable=False)
    data_end = Column(Date, nullable=False)
    match_count = Column(Integer)
    
    # Optimization objective
    objective = Column(String, nullable=False)  # 'minimize_brier'
    
    # Results
    metrics = Column(JSON)  # {brier, log_loss, reliability, ...}
    error_message = Column(Text)
    logs = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    model = relationship("Model", back_populates="training_runs")


# ============================================================================
# JACKPOT TABLES
# ============================================================================

class Jackpot(Base):
    __tablename__ = "jackpots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=False)  # From Supabase auth
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    model_version = Column(String, nullable=False)  # LOCKED at creation
    status = Column(String, nullable=False, default='calculating')  # 'calculating', 'finalized'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finalized_at = Column(DateTime(timezone=True))
    
    fixtures = relationship("JackpotFixture", back_populates="jackpot", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("status IN ('calculating', 'finalized')", name='check_jackpot_status'),
    )


class JackpotFixture(Base):
    __tablename__ = "jackpot_fixtures"
    
    id = Column(BigInteger, primary_key=True)
    jackpot_id = Column(String, ForeignKey("jackpots.id", ondelete="CASCADE"), nullable=False)
    match_order = Column(Integer, nullable=False)  # Order in jackpot (1-13)
    
    # Raw input (preserved)
    match_date = Column(Date, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    
    # Input odds (nullable if user doesn't provide)
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)
    
    # Resolved team IDs (after canonicalization)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    
    # Actual result (for validation after matches complete)
    actual_result = Column(Enum(MatchResult))
    actual_home_goals = Column(Integer)
    actual_away_goals = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    jackpot = relationship("Jackpot", back_populates="fixtures")
    predictions = relationship("Prediction", back_populates="fixture", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_jackpot_fixtures_jackpot', 'jackpot_id'),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(BigInteger, primary_key=True)
    fixture_id = Column(BigInteger, ForeignKey("jackpot_fixtures.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    set_id = Column(Enum(PredictionSet), nullable=False)
    
    # Final probabilities (after calibration)
    prob_home = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away = Column(Float, nullable=False)
    
    # Expected goals (for explainability)
    lambda_home = Column(Float, nullable=False)
    lambda_away = Column(Float, nullable=False)
    
    # Intermediate probabilities (for decomposition)
    model_prob_home = Column(Float)  # Before blending
    model_prob_draw = Column(Float)
    model_prob_away = Column(Float)
    
    market_prob_home = Column(Float)  # Market-implied
    market_prob_draw = Column(Float)
    market_prob_away = Column(Float)
    
    blend_alpha = Column(Float)  # Weight used for this set
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    fixture = relationship("JackpotFixture", back_populates="predictions")
    model = relationship("Model", back_populates="predictions")
    
    __table_args__ = (
        CheckConstraint(
            'abs((prob_home + prob_draw + prob_away) - 1.0) < 1e-6',
            name='check_prob_sum'
        ),
        Index('idx_predictions_fixture', 'fixture_id'),
        Index('idx_predictions_set', 'set_id'),
    )


# ============================================================================
# VALIDATION TABLES
# ============================================================================

class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(BigInteger, primary_key=True)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    set_id = Column(Enum(PredictionSet), nullable=False)
    outcome = Column(String, nullable=False)  # 'home', 'draw', 'away'
    
    # Metrics
    brier_score = Column(Float, nullable=False)
    log_loss = Column(Float)
    sample_count = Column(Integer, nullable=False)
    
    # Reliability curve data
    reliability = Column(JSON, nullable=False)  # {predicted: [...], observed: [...]}
    
    # Time window
    evaluated_from = Column(Date, nullable=False)
    evaluated_to = Column(Date, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("outcome IN ('home', 'draw', 'away')", name='check_outcome_type'),
    )


class CalibrationData(Base):
    __tablename__ = "calibration_data"
    
    id = Column(BigInteger, primary_key=True)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    outcome = Column(String, nullable=False)  # 'home', 'draw', 'away'
    
    # Isotonic regression data
    bins = Column(JSON, nullable=False)  # Predicted probability bins
    frequencies = Column(JSON, nullable=False)  # Observed frequencies
    
    # Training data range (out-of-sample enforced)
    trained_on_end = Column(Date, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('model_id', 'outcome', name='uix_calibration_model_outcome'),
        CheckConstraint("outcome IN ('home', 'draw', 'away')", name='check_calibration_outcome'),
    )


# ============================================================================
# DATA INGESTION TRACKING
# ============================================================================

class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String, nullable=False)  # 'football-data.co.uk', 'api-football'
    league_code = Column(String, nullable=False)
    season = Column(String, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    
    records_loaded = Column(Integer, nullable=False)
    records_inserted = Column(Integer, nullable=False)
    records_updated = Column(Integer, nullable=False)
    records_skipped = Column(Integer, nullable=False)
    
    # Data integrity
    checksum = Column(String, nullable=False)  # SHA256 of source file
    
    status = Column(String, default='completed')
    error_message = Column(Text)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('source', 'league_code', 'season', 'snapshot_date', 
                        name='uix_ingestion_unique'),
    )
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

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True
)

# Session factory
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
            db.query(Model).all()
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

**END OF PART 1**

Part 2 will contain: Core Dixon-Coles implementation, probability calculations, blending, and calibration modules.
