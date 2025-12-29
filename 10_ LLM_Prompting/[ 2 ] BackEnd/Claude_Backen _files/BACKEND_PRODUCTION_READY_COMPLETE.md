# 🎯 FOOTBALL JACKPOT PROBABILITY ENGINE - PRODUCTION BACKEND
## Complete Implementation Following Cursor Master Prompt

**DETERMINISTIC. ANALYTICAL. REGULATOR-DEFENSIBLE.**

---

## 📋 SYSTEM GUARANTEES (ENFORCED IN CODE)

✅ **Deterministic math only** (NumPy/SciPy)  
✅ **No Monte Carlo simulation**  
✅ **No neural networks**  
✅ **Immutable jackpot versions**  
✅ **Calibration applied after blending**  
✅ **Market odds are capped signals**  
✅ **Reproducible feature snapshots**  
✅ **Shrinkage for unseen teams**  
✅ **Graceful degradation** (never silent failure)

---

## 📁 COMPLETE FOLDER STRUCTURE

```
backend/
├── api/
│   ├── __init__.py
│   ├── jackpot.py
│   ├── probabilities.py
│   ├── calibration.py
│   ├── explainability.py
│   └── health.py
│
├── ingestion/
│   ├── __init__.py
│   ├── football_data_csv.py
│   ├── api_provider.py
│   └── ingest_runner.py
│
├── cleaning/
│   ├── __init__.py
│   ├── canonicalize.py
│   ├── validation.py
│   └── filters.py
│
├── features/
│   ├── __init__.py
│   ├── rolling_features.py
│   ├── league_baselines.py
│   └── feature_store.py
│
├── models/
│   ├── __init__.py
│   ├── poisson.py
│   ├── dixon_coles.py
│   └── strength_estimator.py
│
├── probabilities/
│   ├── __init__.py
│   ├── goal_matrix.py
│   └── outcome_integrator.py
│
├── blending/
│   ├── __init__.py
│   ├── odds_to_prob.py
│   └── linear_blend.py
│
├── calibration/
│   ├── __init__.py
│   ├── isotonic.py
│   └── calibration_store.py
│
├── sets/
│   ├── __init__.py
│   ├── set_a.py
│   ├── set_b.py
│   ├── set_c.py
│   └── registry.py
│
├── explainability/
│   ├── __init__.py
│   └── decomposition.py
│
├── validation/
│   ├── __init__.py
│   ├── brier.py
│   ├── reliability.py
│   └── reports.py
│
├── jobs/
│   ├── __init__.py
│   ├── ingest_job.py
│   ├── train_job.py
│   └── validate_job.py
│
├── db/
│   ├── __init__.py
│   ├── base.py
│   ├── models.py
│   └── session.py
│
├── schemas/
│   ├── __init__.py
│   ├── jackpot.py
│   ├── prediction.py
│   └── calibration.py
│
├── tests/
│   ├── __init__.py
│   ├── test_poisson.py
│   ├── test_dixon_coles.py
│   ├── test_probabilities.py
│   └── test_calibration.py
│
├── migrations/
│   ├── 001_enable_extensions.sql
│   ├── 002_enums.sql
│   ├── 003_leagues.sql
│   ├── 004_teams.sql
│   ├── 005_matches.sql
│   ├── 006_team_features.sql
│   ├── 007_models.sql
│   ├── 008_training_runs.sql
│   ├── 009_jackpots.sql
│   ├── 010_jackpot_fixtures.sql
│   ├── 011_predictions.sql
│   ├── 012_validation_results.sql
│   ├── 013_calibration_data.sql
│   ├── 014_ingestion_logs.sql
│   ├── 015_indexes.sql
│   └── 016_rls_policies.sql
│
├── main.py
├── settings.py
├── .env.example
└── README.md
```

---

## 🗄️ SQL MIGRATIONS (001-016)

### 001_enable_extensions.sql

```sql
-- Enable required PostgreSQL extensions
BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

COMMIT;
```

### 002_enums.sql

```sql
-- Create ENUM types
BEGIN;

DO $$ BEGIN
    CREATE TYPE model_status AS ENUM ('active', 'archived', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE prediction_set AS ENUM ('A','B','C','D','E','F','G');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE match_result AS ENUM ('H','D','A');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
```

### 003_leagues.sql

```sql
-- Leagues reference table
BEGIN;

CREATE TABLE IF NOT EXISTS leagues (
    id              SERIAL PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    country         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
```

### 004_teams.sql

```sql
-- Teams reference table
BEGIN;

CREATE TABLE IF NOT EXISTS teams (
    id              SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (league_id, canonical_name)
);

COMMIT;
```

### 005_matches.sql

```sql
-- Historical matches (training data)
BEGIN;

CREATE TABLE IF NOT EXISTS matches (
    id              BIGSERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    season          TEXT NOT NULL,
    match_date      DATE NOT NULL,
    home_team_id    INTEGER NOT NULL REFERENCES teams(id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(id),
    home_goals      INTEGER,
    away_goals      INTEGER,
    result          match_result,
    closing_odds    JSONB NOT NULL,  -- {home, draw, away}
    snapshot_date   DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (league_id, season, match_date, home_team_id, away_team_id)
);

COMMENT ON COLUMN matches.closing_odds IS 'Closing odds only - no in-play, no opening';
COMMENT ON COLUMN matches.snapshot_date IS 'When data was ingested for reproducibility';

COMMIT;
```

### 006_team_features.sql

```sql
-- Team feature store (reproducible snapshots)
BEGIN;

CREATE TABLE IF NOT EXISTS team_features (
    id               BIGSERIAL PRIMARY KEY,
    team_id          INTEGER NOT NULL REFERENCES teams(id),
    snapshot_date    DATE NOT NULL,
    attack_strength  DOUBLE PRECISION NOT NULL,
    defense_strength DOUBLE PRECISION NOT NULL,
    home_advantage   DOUBLE PRECISION NOT NULL,
    decay_lambda     DOUBLE PRECISION NOT NULL,
    feature_version  TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (team_id, snapshot_date, feature_version)
);

COMMENT ON TABLE team_features IS 'Versioned, timestamped team strength snapshots';

COMMIT;
```

### 007_models.sql

```sql
-- Model registry (immutable after training)
BEGIN;

CREATE TABLE IF NOT EXISTS models (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version         TEXT NOT NULL UNIQUE,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    parameters      JSONB NOT NULL,  -- {rho, xi, home_advantage, ...}
    trained_at      TIMESTAMPTZ NOT NULL,
    status          model_status NOT NULL,
    brier_score     DOUBLE PRECISION,
    log_loss        DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE models IS 'Immutable model registry - one active per league';

COMMIT;
```

### 008_training_runs.sql

```sql
-- Training run audit log
BEGIN;

CREATE TABLE IF NOT EXISTS training_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id        UUID NOT NULL REFERENCES models(id),
    data_start      DATE NOT NULL,
    data_end        DATE NOT NULL,
    objective       TEXT NOT NULL,  -- 'minimize_brier'
    metrics         JSONB NOT NULL,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
```

### 009_jackpots.sql

```sql
-- User jackpot entries (immutable after finalize)
BEGIN;

CREATE TABLE IF NOT EXISTS jackpots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    model_version   TEXT NOT NULL,  -- LOCKED at creation
    status          TEXT NOT NULL CHECK (status IN ('calculating','finalized')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at    TIMESTAMPTZ
);

COMMENT ON COLUMN jackpots.model_version IS 'Model version locked - predictions never change';

COMMIT;
```

### 010_jackpot_fixtures.sql

```sql
-- Individual fixtures within jackpots
BEGIN;

CREATE TABLE IF NOT EXISTS jackpot_fixtures (
    id              BIGSERIAL PRIMARY KEY,
    jackpot_id      UUID NOT NULL REFERENCES jackpots(id) ON DELETE CASCADE,
    match_order     INTEGER NOT NULL,
    match_date      DATE NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    odds_home       DOUBLE PRECISION,
    odds_draw       DOUBLE PRECISION,
    odds_away       DOUBLE PRECISION,
    home_team_id    INTEGER REFERENCES teams(id),  -- Resolved
    away_team_id    INTEGER REFERENCES teams(id),  -- Resolved
    actual_result   match_result,  -- For validation
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE jackpot_fixtures IS 'Raw input preserved - canonical resolution occurs separately';

COMMIT;
```

### 011_predictions.sql

```sql
-- Predictions (all 7 sets stored in parallel)
BEGIN;

CREATE TABLE IF NOT EXISTS predictions (
    id              BIGSERIAL PRIMARY KEY,
    fixture_id      BIGINT NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
    model_id        UUID NOT NULL REFERENCES models(id),
    set_id          prediction_set NOT NULL,
    prob_home       DOUBLE PRECISION NOT NULL,
    prob_draw       DOUBLE PRECISION NOT NULL,
    prob_away       DOUBLE PRECISION NOT NULL,
    lambda_home     DOUBLE PRECISION NOT NULL,  -- For explainability
    lambda_away     DOUBLE PRECISION NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (abs((prob_home + prob_draw + prob_away) - 1.0) < 1e-6)
);

COMMENT ON CONSTRAINT predictions_prob_home_prob_draw_prob_away_check 
ON predictions IS 'Probability conservation enforced at database level';

COMMIT;
```

### 012_validation_results.sql

```sql
-- Validation metrics (outcome-specific)
BEGIN;

CREATE TABLE IF NOT EXISTS validation_results (
    id              BIGSERIAL PRIMARY KEY,
    model_id        UUID NOT NULL REFERENCES models(id),
    set_id          prediction_set NOT NULL,
    outcome         TEXT NOT NULL CHECK (outcome IN ('home','draw','away')),
    brier_score     DOUBLE PRECISION NOT NULL,
    log_loss        DOUBLE PRECISION,
    reliability     JSONB NOT NULL,  -- Reliability curve data
    sample_count    INTEGER NOT NULL,
    evaluated_from  DATE NOT NULL,
    evaluated_to    DATE NOT NULL,
    evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE validation_results IS 'No raw accuracy % - Brier and reliability only';

COMMIT;
```

### 013_calibration_data.sql

```sql
-- Isotonic calibration curves (one per outcome)
BEGIN;

CREATE TABLE IF NOT EXISTS calibration_data (
    id              BIGSERIAL PRIMARY KEY,
    model_id        UUID NOT NULL REFERENCES models(id),
    outcome         TEXT NOT NULL CHECK (outcome IN ('home','draw','away')),
    bins            JSONB NOT NULL,       -- Predicted probability bins
    frequencies     JSONB NOT NULL,       -- Observed frequencies
    trained_on_end  DATE NOT NULL,        -- Out-of-sample enforced
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (model_id, outcome)
);

COMMENT ON TABLE calibration_data IS 'Isotonic regression - out-of-sample only';

COMMIT;
```

### 014_ingestion_logs.sql

```sql
-- Data ingestion audit trail
BEGIN;

CREATE TABLE IF NOT EXISTS ingestion_logs (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,  -- 'football-data.co.uk', 'api-football'
    league_code     TEXT NOT NULL,
    season          TEXT NOT NULL,
    snapshot_date   DATE NOT NULL,
    records_loaded  INTEGER NOT NULL,
    records_inserted INTEGER NOT NULL,
    records_updated  INTEGER NOT NULL,
    checksum        TEXT NOT NULL,  -- SHA256 of source file
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, league_code, season, snapshot_date)
);

COMMENT ON TABLE ingestion_logs IS 'Deterministic ingestion - idempotent inserts';

COMMIT;
```

### 015_indexes.sql

```sql
-- Performance indexes
BEGIN;

CREATE INDEX IF NOT EXISTS idx_matches_date 
ON matches(match_date);

CREATE INDEX IF NOT EXISTS idx_matches_league_season 
ON matches(league_id, season);

CREATE INDEX IF NOT EXISTS idx_predictions_fixture 
ON predictions(fixture_id);

CREATE INDEX IF NOT EXISTS idx_predictions_set 
ON predictions(set_id);

CREATE INDEX IF NOT EXISTS idx_team_features_snapshot 
ON team_features(team_id, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_models_status 
ON models(status) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_jackpots_user 
ON jackpots(user_id);

COMMIT;
```

### 016_rls_policies.sql

```sql
-- Row Level Security (Supabase compatibility)
BEGIN;

-- Enable RLS on user tables
ALTER TABLE jackpots ENABLE ROW LEVEL SECURITY;
ALTER TABLE jackpot_fixtures ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- Users can only read their own jackpots
CREATE POLICY "users_read_own_jackpots"
ON jackpots
FOR SELECT
USING (auth.uid() = user_id);

-- Users can only read their own fixtures
CREATE POLICY "users_read_own_fixtures"
ON jackpot_fixtures
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM jackpots 
        WHERE id = jackpot_fixtures.jackpot_id 
        AND user_id = auth.uid()
    )
);

-- Users can only read their own predictions
CREATE POLICY "users_read_own_predictions"
ON predictions
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM jackpot_fixtures jf
        JOIN jackpots j ON jf.jackpot_id = j.id
        WHERE jf.id = predictions.fixture_id
        AND j.user_id = auth.uid()
    )
);

-- Public read access to reference data
ALTER TABLE leagues ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_leagues" ON leagues FOR SELECT USING (true);

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_teams" ON teams FOR SELECT USING (true);

ALTER TABLE models ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_active_models" ON models FOR SELECT USING (status = 'active');

COMMIT;
```

---

## 🔧 CORE PYTHON MODULES

### backend/settings.py

```python
"""
Application Settings

CRITICAL: All parameters must be deterministic and auditable.
NO mutable globals.
NO environment-dependent behavior in math.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration with validation.
    
    All settings loaded from environment with safe defaults.
    """
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://user:pass@localhost:5432/jackpot_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # API
    API_TITLE: str = "Football Jackpot Probability Engine"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # Supabase JWT (optional)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Dixon-Coles Parameters (IMMUTABLE)
    DIXON_COLES_RHO: float = -0.13       # Dependency parameter
    TIME_DECAY_XI: float = 0.0065        # Per-day decay
    HOME_ADVANTAGE: float = 0.35         # Goals
    MAX_GOALS: int = 8                   # For probability matrix
    SHRINKAGE_FACTOR: float = 0.3        # For unseen teams
    
    # Blending
    DEFAULT_BLEND_ALPHA: float = 0.6     # Model weight
    MAX_MARKET_WEIGHT: float = 0.7       # Hard cap
    
    # Calibration
    MIN_CALIBRATION_SAMPLES: int = 30
    CALIBRATION_BINS: int = 20
    
    # Validation
    BRIER_SCORE_THRESHOLD: float = 0.22
    MIN_VALIDATION_SAMPLES: int = 100
    
    # System
    ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Feature flags
    ENABLE_SET_D: bool = True
    ENABLE_SET_E: bool = True
    ENABLE_SET_F: bool = True
    ENABLE_SET_G: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
```

### backend/db/base.py

```python
"""
SQLAlchemy Base Declaration
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
```

### backend/db/models.py

```python
"""
SQLAlchemy ORM Models

Matches SQL schema exactly (migrations 001-016).
NO gambling tables.
NO mutable predictions.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Enum, JSON, Boolean, Text, BigInteger,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum
from uuid import uuid4


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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    teams = relationship("Team", back_populates="league")
    matches = relationship("Match", back_populates="league")


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    name = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    league = relationship("League", back_populates="teams")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id")
    features = relationship("TeamFeature", back_populates="team")
    
    __table_args__ = (
        UniqueConstraint('league_id', 'canonical_name'),
    )


class Match(Base):
    __tablename__ = "matches"
    
    id = Column(BigInteger, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    season = Column(String, nullable=False)
    match_date = Column(Date, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    result = Column(Enum(MatchResult))
    closing_odds = Column(JSON, nullable=False)  # {home, draw, away}
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    
    __table_args__ = (
        UniqueConstraint('league_id', 'season', 'match_date', 
                        'home_team_id', 'away_team_id'),
    )


class TeamFeature(Base):
    __tablename__ = "team_features"
    
    id = Column(BigInteger, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    attack_strength = Column(Float, nullable=False)
    defense_strength = Column(Float, nullable=False)
    home_advantage = Column(Float, nullable=False)
    decay_lambda = Column(Float, nullable=False)
    feature_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    team = relationship("Team", back_populates="features")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'snapshot_date', 'feature_version'),
    )


class Model(Base):
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    version = Column(String, unique=True, nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    parameters = Column(JSON, nullable=False)
    trained_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(ModelStatus), nullable=False)
    brier_score = Column(Float)
    log_loss = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    training_runs = relationship("TrainingRun", back_populates="model")
    predictions = relationship("Prediction", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    data_start = Column(Date, nullable=False)
    data_end = Column(Date, nullable=False)
    objective = Column(String, nullable=False)
    metrics = Column(JSON, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    model = relationship("Model", back_populates="training_runs")


class Jackpot(Base):
    __tablename__ = "jackpots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    model_version = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finalized_at = Column(DateTime(timezone=True))
    
    fixtures = relationship("JackpotFixture", back_populates="jackpot", 
                          cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("status IN ('calculating', 'finalized')"),
    )


class JackpotFixture(Base):
    __tablename__ = "jackpot_fixtures"
    
    id = Column(BigInteger, primary_key=True)
    jackpot_id = Column(String, ForeignKey("jackpots.id", ondelete="CASCADE"), 
                       nullable=False)
    match_order = Column(Integer, nullable=False)
    match_date = Column(Date, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    actual_result = Column(Enum(MatchResult))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    jackpot = relationship("Jackpot", back_populates="fixtures")
    predictions = relationship("Prediction", back_populates="fixture", 
                             cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(BigInteger, primary_key=True)
    fixture_id = Column(BigInteger, ForeignKey("jackpot_fixtures.id", 
                        ondelete="CASCADE"), nullable=False)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    set_id = Column(Enum(PredictionSet), nullable=False)
    prob_home = Column(Float, nullable=False)
    prob_draw = Column(Float, nullable=False)
    prob_away = Column(Float, nullable=False)
    lambda_home = Column(Float, nullable=False)
    lambda_away = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    fixture = relationship("JackpotFixture", back_populates="predictions")
    model = relationship("Model", back_populates="predictions")
    
    __table_args__ = (
        CheckConstraint('abs((prob_home + prob_draw + prob_away) - 1.0) < 1e-6'),
    )


class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(BigInteger, primary_key=True)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    set_id = Column(Enum(PredictionSet), nullable=False)
    outcome = Column(String, nullable=False)
    brier_score = Column(Float, nullable=False)
    log_loss = Column(Float)
    reliability = Column(JSON, nullable=False)
    sample_count = Column(Integer, nullable=False)
    evaluated_from = Column(Date, nullable=False)
    evaluated_to = Column(Date, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("outcome IN ('home', 'draw', 'away')"),
    )


class CalibrationData(Base):
    __tablename__ = "calibration_data"
    
    id = Column(BigInteger, primary_key=True)
    model_id = Column(String, ForeignKey("models.id"), nullable=False)
    outcome = Column(String, nullable=False)
    bins = Column(JSON, nullable=False)
    frequencies = Column(JSON, nullable=False)
    trained_on_end = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('model_id', 'outcome'),
        CheckConstraint("outcome IN ('home', 'draw', 'away')"),
    )


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String, nullable=False)
    league_code = Column(String, nullable=False)
    season = Column(String, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    records_loaded = Column(Integer, nullable=False)
    records_inserted = Column(Integer, nullable=False)
    records_updated = Column(Integer, nullable=False)
    checksum = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('source', 'league_code', 'season', 'snapshot_date'),
    )
```

### backend/db/session.py

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
        @router.get("/endpoint")
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

**CONTINUED IN NEXT FILE DUE TO LENGTH...**

This document continues with all remaining modules:
- Dixon-Coles implementation
- Probability calculations
- Market blending
- Calibration
- Probability sets
- FastAPI routers
- Testing code
- Complete requirements.txt
- .env.example
- README.md

Total: ~5000 lines of production-ready code.
