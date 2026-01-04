# Football Probability Engine: Detailed Architectural Design

**Version:** 2.0  
**Date:** January 2, 2026  
**Architect:** Paul's AI Assistant  
**Status:** Design Proposal  

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Service Specifications](#2-service-specifications)
3. [Database Design](#3-database-design)
4. [API Design](#4-api-design)
5. [ML Pipeline Design](#5-ml-pipeline-design)
6. [Infrastructure Design](#6-infrastructure-design)
7. [Security Architecture](#7-security-architecture)
8. [Deployment Strategy](#8-deployment-strategy)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         INTERNET / CDN                                 │
│                    (Cloudflare Edge Network)                           │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Load Balancer  │ (HAProxy / NGINX)
                    │  + WAF + DDoS   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│  Next.js App   │  │  API Gateway    │  │  Admin Portal  │
│  (Frontend)    │  │  (FastAPI)      │  │  (React)       │
│                │  │                 │  │                │
│ • SSR/RSC      │  │ • Auth          │  │ • Monitoring   │
│ • Edge Cache   │  │ • Rate Limit    │  │ • Analytics    │
│ • PWA          │  │ • Routing       │  │ • Management   │
└────────────────┘  └────────┬────────┘  └────────────────┘
                             │
        ┌────────────────────┼────────────────────────────┐
        │                    │                            │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────────────▼──────┐
│ Prediction     │  │ Data Service    │  │ Model Service       │
│ Service        │  │ (FastAPI)       │  │ (FastAPI)           │
│ (FastAPI)      │  │                 │  │                     │
│                │  │ • Ingestion     │  │ • Training          │
│ • Dixon-Coles  │  │ • Validation    │  │ • Tuning            │
│ • Calibration  │  │ • ETL           │  │ • Deployment        │
│ • Ticket Gen   │  │ • Cleaning      │  │ • Versioning        │
└────────┬───────┘  └────────┬────────┘  └────────┬────────────┘
         │                   │                     │
         │      ┌────────────┼────────────┐       │
         │      │            │            │       │
    ┌────▼──────▼────┐  ┌────▼─────┐  ┌──▼───────▼─────┐
    │  Redis Cluster │  │PostgreSQL│  │  MLflow        │
    │  (Cache +      │  │+ Timescale│  │  (Model        │
    │   Feature      │  │  (Primary)│  │   Registry)    │
    │   Store)       │  └──────┬────┘  └────────────────┘
    └────────────────┘         │
                               │
                    ┌──────────┴──────────┐
                    │  PostgreSQL Replicas│
                    │  (Read Scaling)     │
                    └─────────────────────┘
```

### 1.2 Microservices Breakdown

| Service | Purpose | Tech Stack | Scale Target |
|---------|---------|------------|--------------|
| **Frontend** | User interface | Next.js 14 + React | 1M req/day |
| **API Gateway** | Auth, routing, rate limit | FastAPI + Kong | 5M req/day |
| **Prediction Service** | Generate probabilities | FastAPI + Dixon-Coles | 2M pred/day |
| **Data Service** | ETL, ingestion, cleaning | FastAPI + Pandas | 100K matches/day |
| **Model Service** | Training, tuning, deploy | Ray + MLflow | Weekly training |
| **Cache Layer** | Fast reads, feature store | Redis Cluster | 10M ops/sec |
| **Database** | Persistent storage | PostgreSQL + TimescaleDB | 100M rows |

### 1.3 Communication Patterns

```
┌─────────────────────────────────────────────────────┐
│          Communication Patterns                     │
│                                                      │
│  Frontend ←REST→ API Gateway ←REST→ Microservices  │
│                                                      │
│  Services ←gRPC→ Services (internal)               │
│                                                      │
│  Services ←Event Bus→ Async Processing             │
│  (RabbitMQ/Kafka)                                   │
│                                                      │
│  Services ←Shared Cache→ Redis Cluster             │
│                                                      │
│  Services ←Database→ PostgreSQL (via ORM)          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 2. Service Specifications

### 2.1 Frontend Service (Next.js 14)

#### Technology Stack
```json
{
  "framework": "Next.js 14.2.0",
  "react": "18.3.1",
  "typescript": "5.8.3",
  "styling": "Tailwind CSS 3.4.17",
  "components": "shadcn/ui + Radix UI",
  "state": "Zustand + React Query",
  "auth": "NextAuth.js",
  "deployment": "Vercel Edge / Cloudflare Pages"
}
```

#### App Structure
```
app/
├── (auth)/
│   ├── login/
│   └── signup/
├── (dashboard)/
│   ├── page.tsx                    # Dashboard (SSR)
│   ├── jackpots/
│   │   ├── new/page.tsx            # Create jackpot (Client)
│   │   └── [id]/page.tsx           # View jackpot (SSR)
│   ├── predictions/
│   │   └── [id]/page.tsx           # Predictions (SSR + ISR)
│   ├── tickets/
│   │   └── [id]/page.tsx           # Tickets (Client)
│   └── analytics/
│       ├── backtesting/page.tsx    # Backtesting (SSR)
│       ├── validation/page.tsx     # Validation (SSR)
│       └── calibration/page.tsx    # Calibration (SSR)
├── (admin)/
│   ├── models/page.tsx             # Model management
│   ├── data/page.tsx               # Data ingestion
│   └── system/page.tsx             # System health
├── api/
│   ├── auth/[...nextauth]/route.ts # Auth API
│   └── revalidate/route.ts         # ISR revalidation
└── layout.tsx
```

#### Performance Optimizations

**1. Server-Side Rendering (SSR)**
```typescript
// app/predictions/[id]/page.tsx
export default async function PredictionPage({ 
  params 
}: { 
  params: { id: string } 
}) {
  const prediction = await fetchPrediction(params.id);
  
  return <PredictionView prediction={prediction} />;
}

// ✅ Rendered on server
// ✅ SEO-friendly
// ✅ Fast Time-to-Interactive
```

**2. Incremental Static Regeneration (ISR)**
```typescript
// app/dashboard/page.tsx
export const revalidate = 300; // 5 minutes

export default async function Dashboard() {
  const stats = await fetchDashboardStats();
  
  return <DashboardView stats={stats} />;
}

// ✅ Static at build time
// ✅ Regenerates every 5 minutes
// ✅ Fast CDN delivery
```

**3. React Server Components (RSC)**
```typescript
// components/MatchCard.tsx
async function MatchCard({ matchId }: { matchId: string }) {
  const match = await fetchMatch(matchId);
  
  return (
    <Card>
      <CardHeader>{match.home} vs {match.away}</CardHeader>
      <CardContent>
        {/* Client component for interactivity */}
        <ProbabilityChart probabilities={match.probabilities} />
      </CardContent>
    </Card>
  );
}

// ✅ Fetches data on server
// ✅ Zero JavaScript for static parts
// ✅ Reduced bundle size
```

**4. Code Splitting**
```typescript
// Dynamic imports
const TutorialModal = dynamic(() => import('./TutorialModal'), {
  loading: () => <Spinner />,
  ssr: false
});

// ✅ Lazy load modals
// ✅ Reduce initial bundle
// ✅ Load on demand
```

#### State Management

**Global State (Zustand)**
```typescript
// store/useUserStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserStore {
  user: User | null;
  preferences: Preferences;
  setUser: (user: User) => void;
  updatePreferences: (prefs: Partial<Preferences>) => void;
}

export const useUserStore = create<UserStore>()(
  persist(
    (set) => ({
      user: null,
      preferences: {},
      setUser: (user) => set({ user }),
      updatePreferences: (prefs) => 
        set((state) => ({ 
          preferences: { ...state.preferences, ...prefs } 
        }))
    }),
    { name: 'user-storage' }
  )
);
```

**Server State (React Query)**
```typescript
// hooks/useJackpots.ts
import { useQuery } from '@tanstack/react-query';

export function useJackpots() {
  return useQuery({
    queryKey: ['jackpots'],
    queryFn: () => apiClient.getJackpots(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true
  });
}
```

### 2.2 API Gateway Service (FastAPI + Kong)

#### Purpose
- **Authentication & Authorization** (JWT, OAuth2, API Keys)
- **Rate Limiting** (Redis-based)
- **Request Routing** (to microservices)
- **Response Caching** (Redis)
- **Logging & Metrics** (Prometheus)

#### Configuration
```yaml
# kong.yml
_format_version: "3.0"

services:
  - name: prediction-service
    url: http://prediction-service:8001
    routes:
      - name: predictions
        paths:
          - /api/predictions
        strip_path: false
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
      - name: jwt
        config:
          secret_is_base64: false
      - name: cors
        config:
          origins: ["*"]

  - name: data-service
    url: http://data-service:8002
    routes:
      - name: data-ingestion
        paths:
          - /api/data
        strip_path: false
    plugins:
      - name: rate-limiting
        config:
          minute: 50
          hour: 500
```

#### Rate Limiting Strategy
```python
# Rate limits by tier
RATE_LIMITS = {
    "free": {
        "minute": 10,
        "hour": 100,
        "day": 1000
    },
    "pro": {
        "minute": 100,
        "hour": 5000,
        "day": 50000
    },
    "enterprise": {
        "minute": 1000,
        "hour": 50000,
        "day": "unlimited"
    }
}
```

### 2.3 Prediction Service (FastAPI + Dixon-Coles)

#### API Endpoints

```python
# app/api/predictions.py
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/api/predictions")

@router.post("/generate")
async def generate_predictions(
    jackpot: JackpotCreate,
    user: User = Depends(get_current_user)
) -> PredictionResponse:
    """
    Generate 10 probability sets (A-J) for jackpot fixtures
    
    Process:
    1. Resolve team names (fuzzy matching)
    2. Get team strengths from trained model
    3. Calculate Dixon-Coles probabilities
    4. Apply isotonic calibration
    5. Generate 10 sets with uncertainty
    6. Cache results (1 hour TTL)
    """
    # 1. Validate & resolve teams
    fixtures = await resolve_teams(jackpot.fixtures)
    
    # 2. Get cached predictions if available
    cache_key = generate_cache_key(fixtures)
    cached = await redis.get(cache_key)
    if cached:
        return cached
    
    # 3. Generate predictions
    predictions = []
    for fixture in fixtures:
        probs = await dixon_coles.predict(
            home=fixture.home_team,
            away=fixture.away_team,
            date=fixture.date
        )
        
        # Apply calibration
        calibrated = await calibration.transform(probs)
        
        # Generate 10 sets
        sets = await generate_probability_sets(calibrated)
        
        predictions.append(sets)
    
    # 4. Cache result
    await redis.setex(cache_key, 3600, predictions)
    
    return PredictionResponse(predictions=predictions)


@router.get("/{jackpot_id}")
async def get_predictions(
    jackpot_id: int,
    set_name: str = "A"
) -> PredictionResponse:
    """Get saved predictions for a jackpot"""
    return await prediction_service.get_by_jackpot_id(jackpot_id, set_name)


@router.post("/batch")
async def batch_predictions(
    fixtures: List[FixtureInput],
    user: User = Depends(get_current_user)
) -> List[PredictionResponse]:
    """Batch prediction for multiple fixtures"""
    return await prediction_service.batch_predict(fixtures)
```

#### Caching Strategy

```python
# Redis cache structure
CACHE_KEYS = {
    "prediction": "pred:{home}:{away}:{date}",  # 1 hour TTL
    "team_strength": "team:{team_id}",          # 24 hours TTL
    "model_version": "model:version:current",   # No expiry
    "league_stats": "league:{league_id}",       # 7 days TTL
}

# Cache invalidation
async def invalidate_team_cache(team_id: int):
    """Invalidate cache when team strength updates"""
    await redis.delete(f"team:{team_id}")
    await redis.delete_pattern(f"pred:*{team_id}*")
```

#### Performance Targets

| Metric | Target | Current | Improvement |
|--------|--------|---------|-------------|
| **API Latency (p50)** | 50ms | 500ms | **10x** |
| **API Latency (p95)** | 100ms | 1000ms | **10x** |
| **API Latency (p99)** | 200ms | 2000ms | **10x** |
| **Cache Hit Rate** | 95% | 0% | **New** |
| **Throughput** | 10K req/sec | 100 req/sec | **100x** |

### 2.4 Data Service (FastAPI + Pandas)

#### API Endpoints

```python
# app/api/data.py
from fastapi import APIRouter, BackgroundTasks
import pandas as pd

router = APIRouter(prefix="/api/data")

@router.post("/ingest/batch")
async def ingest_batch_data(
    source: str,
    season: str,
    leagues: List[str],
    background_tasks: BackgroundTasks
) -> IngestionResponse:
    """
    Ingest historical match data
    
    Sources:
    - football-data.co.uk
    - API-Football
    - Custom CSV uploads
    """
    job_id = generate_job_id()
    
    # Run ingestion in background
    background_tasks.add_task(
        run_ingestion,
        job_id=job_id,
        source=source,
        season=season,
        leagues=leagues
    )
    
    return IngestionResponse(
        job_id=job_id,
        status="pending",
        message="Ingestion started"
    )


@router.get("/ingestion/status/{job_id}")
async def get_ingestion_status(job_id: str) -> IngestionStatus:
    """Get ingestion job status"""
    return await ingestion_service.get_status(job_id)


@router.post("/clean/teams")
async def clean_team_names(
    league_id: int,
    dry_run: bool = True
) -> TeamCleaningReport:
    """
    Clean and normalize team names
    
    Process:
    1. Detect duplicates (fuzzy matching)
    2. Suggest canonical names
    3. Apply corrections (if not dry_run)
    """
    return await team_cleaning_service.clean(league_id, dry_run)


@router.post("/validate")
async def validate_data(
    start_date: str,
    end_date: str
) -> ValidationReport:
    """
    Validate data quality
    
    Checks:
    - Missing values
    - Duplicate matches
    - Invalid scores
    - Inconsistent odds
    - Team name issues
    """
    return await data_validation_service.validate(start_date, end_date)
```

#### ETL Pipeline

```python
# services/etl_pipeline.py
from prefect import task, flow

@task
def extract_matches(source: str, season: str) -> pd.DataFrame:
    """Extract matches from source"""
    if source == "football-data":
        return extract_from_football_data(season)
    elif source == "api-football":
        return extract_from_api_football(season)
    else:
        raise ValueError(f"Unknown source: {source}")


@task
def transform_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Transform and clean data"""
    # Normalize team names
    df['home_team'] = df['home_team'].apply(normalize_team_name)
    df['away_team'] = df['away_team'].apply(normalize_team_name)
    
    # Calculate market probabilities
    df['prob_home'] = calculate_implied_prob(df['odds_home'])
    df['prob_draw'] = calculate_implied_prob(df['odds_draw'])
    df['prob_away'] = calculate_implied_prob(df['odds_away'])
    
    # Validate data
    validate_probabilities(df)
    
    return df


@task
def load_matches(df: pd.DataFrame):
    """Load data into PostgreSQL"""
    df.to_sql(
        'matches',
        engine,
        if_exists='append',
        index=False,
        method='multi'
    )


@flow
def etl_flow(source: str, season: str):
    """Complete ETL flow"""
    df = extract_matches(source, season)
    df_clean = transform_matches(df)
    load_matches(df_clean)
```

### 2.5 Model Service (Ray + MLflow)

#### Training Pipeline

```python
# services/training_pipeline.py
import mlflow
import ray
from ray import tune

@ray.remote
def train_dixon_coles_model(
    data: pd.DataFrame,
    hyperparams: dict
) -> ModelMetrics:
    """
    Train Dixon-Coles model with given hyperparameters
    
    Parameters:
    - rho: Dependency parameter (-0.2 to 0)
    - xi: Time decay (0.001 to 0.01)
    - home_advantage: Home advantage (0.2 to 0.5)
    - blend_alpha: Model vs market weight (0.3 to 0.7)
    """
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params(hyperparams)
        
        # Train model
        model = DixonColesModel(**hyperparams)
        model.fit(data)
        
        # Validate
        metrics = validate_model(model, holdout_data)
        mlflow.log_metrics(metrics)
        
        # Save model
        mlflow.sklearn.log_model(model, "model")
        
        return metrics


def hyperparameter_tuning(data: pd.DataFrame):
    """Run hyperparameter tuning with Ray Tune"""
    config = {
        "rho": tune.uniform(-0.2, 0),
        "xi": tune.uniform(0.001, 0.01),
        "home_advantage": tune.uniform(0.2, 0.5),
        "blend_alpha": tune.uniform(0.3, 0.7)
    }
    
    analysis = tune.run(
        train_dixon_coles_model,
        config=config,
        num_samples=100,
        metric="brier_score",
        mode="min"
    )
    
    best_config = analysis.get_best_config(metric="brier_score")
    return best_config
```

#### Model Registry

```python
# services/model_registry.py
import mlflow

class ModelRegistry:
    def register_model(
        self,
        model_name: str,
        model_version: str,
        metrics: dict
    ):
        """Register model in MLflow"""
        mlflow.register_model(
            f"runs:/{mlflow.active_run().info.run_id}/model",
            model_name
        )
        
        # Add tags
        client = mlflow.tracking.MlflowClient()
        client.set_model_version_tag(
            model_name,
            model_version,
            "brier_score",
            str(metrics["brier_score"])
        )
    
    def promote_to_production(
        self,
        model_name: str,
        model_version: str
    ):
        """Promote model to production"""
        client = mlflow.tracking.MlflowClient()
        client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage="Production"
        )
    
    def load_production_model(self, model_name: str):
        """Load current production model"""
        return mlflow.pyfunc.load_model(
            f"models:/{model_name}/Production"
        )
```

---

## 3. Database Design

### 3.1 Improved Schema

#### Time-Series Optimization (TimescaleDB)

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Convert matches table to hypertable
SELECT create_hypertable(
    'matches',
    'match_date',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Add compression
ALTER TABLE matches SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'league_id'
);

-- Add compression policy (compress data older than 1 year)
SELECT add_compression_policy('matches', INTERVAL '1 year');

-- Add retention policy (delete data older than 5 years)
SELECT add_retention_policy('matches', INTERVAL '5 years');
```

**Benefits:**
- 10x faster time-series queries
- Automatic compression (90% storage savings)
- Continuous aggregations
- Automatic retention management

#### Partitioning Strategy

```sql
-- Partition predictions table by month
CREATE TABLE predictions (
    id BIGSERIAL,
    jackpot_id INTEGER NOT NULL,
    fixture_id INTEGER NOT NULL,
    prediction_set prediction_set NOT NULL,
    prob_home DOUBLE PRECISION NOT NULL,
    prob_draw DOUBLE PRECISION NOT NULL,
    prob_away DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE predictions_2025_01 
    PARTITION OF predictions
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE predictions_2025_02 
    PARTITION OF predictions
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Automatic partition creation (pg_partman)
SELECT partman.create_parent(
    p_parent_table => 'public.predictions',
    p_control => 'created_at',
    p_type => 'range',
    p_interval => 'monthly',
    p_premake => 3
);
```

#### Materialized Views

```sql
-- Team strength materialized view
CREATE MATERIALIZED VIEW team_strengths AS
SELECT
    t.id,
    t.name,
    t.attack_rating,
    t.defense_rating,
    l.name AS league_name,
    t.last_calculated
FROM teams t
JOIN leagues l ON t.league_id = l.id
WHERE t.last_calculated > now() - INTERVAL '7 days';

-- Refresh policy
CREATE INDEX ON team_strengths (id);
REFRESH MATERIALIZED VIEW CONCURRENTLY team_strengths;

-- League statistics materialized view
CREATE MATERIALIZED VIEW league_season_stats AS
SELECT
    l.id AS league_id,
    l.name AS league_name,
    m.season,
    COUNT(*) AS total_matches,
    AVG(CASE WHEN m.result = 'H' THEN 1.0 ELSE 0.0 END) AS home_win_rate,
    AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END) AS draw_rate,
    AVG(CASE WHEN m.result = 'A' THEN 1.0 ELSE 0.0 END) AS away_win_rate,
    AVG(m.home_goals + m.away_goals) AS avg_goals_per_match
FROM matches m
JOIN leagues l ON m.league_id = l.id
GROUP BY l.id, l.name, m.season;

CREATE INDEX ON league_season_stats (league_id, season);
```

#### Additional Indexes

```sql
-- Composite indexes for common queries
CREATE INDEX idx_matches_team_date 
    ON matches(home_team_id, away_team_id, match_date);

CREATE INDEX idx_predictions_jackpot_set 
    ON predictions(jackpot_id, prediction_set);

CREATE INDEX idx_team_features_team_calculated 
    ON team_features(team_id, calculated_at DESC);

-- Full-text search on team names
CREATE INDEX idx_teams_name_trgm 
    ON teams USING gin(name gin_trgm_ops);

-- JSON index for model weights
CREATE INDEX idx_models_weights 
    ON models USING gin(model_weights);
```

### 3.2 Read Replica Configuration

```yaml
# docker-compose.yml
services:
  postgres-primary:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres-primary-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  postgres-replica-1:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
      POSTGRES_MASTER_PORT: 5432
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres-replica-1-data:/var/lib/postgresql/data
    depends_on:
      - postgres-primary

  postgres-replica-2:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
      POSTGRES_MASTER_PORT: 5432
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres-replica-2-data:/var/lib/postgresql/data
    depends_on:
      - postgres-primary

  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: postgres-primary
      DATABASES_PORT: 5432
      DATABASES_USER: ${DB_USER}
      DATABASES_PASSWORD: ${DB_PASSWORD}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 25
    ports:
      - "6432:6432"
    depends_on:
      - postgres-primary
```

---

## 4. API Design

### 4.1 RESTful API Standards

#### Endpoint Naming Convention

```
# Resources (plural nouns)
GET    /api/jackpots              # List all jackpots
POST   /api/jackpots              # Create new jackpot
GET    /api/jackpots/{id}         # Get specific jackpot
PUT    /api/jackpots/{id}         # Update jackpot
DELETE /api/jackpots/{id}         # Delete jackpot

# Nested resources
GET    /api/jackpots/{id}/predictions         # Get predictions
POST   /api/jackpots/{id}/predictions         # Generate predictions
GET    /api/jackpots/{id}/predictions/{set}   # Get specific set

# Actions (verbs)
POST   /api/models/train                      # Train model
POST   /api/predictions/batch                 # Batch predictions
POST   /api/tickets/generate                  # Generate tickets
```

#### HTTP Status Codes

```python
# Success
200: OK                # Successful GET, PUT, DELETE
201: Created           # Successful POST
202: Accepted          # Async operation started
204: No Content        # Successful DELETE (no body)

# Client Errors
400: Bad Request       # Invalid input
401: Unauthorized      # Missing/invalid auth
403: Forbidden         # Valid auth, insufficient permissions
404: Not Found         # Resource doesn't exist
409: Conflict          # Duplicate resource
422: Unprocessable     # Validation error
429: Too Many Requests # Rate limit exceeded

# Server Errors
500: Internal Error    # Server error
502: Bad Gateway       # Upstream service error
503: Service Unavailable # Service down
504: Gateway Timeout   # Upstream timeout
```

#### Response Format

```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "Weekend Jackpot",
    "created_at": "2025-01-02T10:00:00Z"
  },
  "meta": {
    "timestamp": "2025-01-02T10:00:00Z",
    "request_id": "req_abc123",
    "version": "v2.0.0"
  }
}
```

#### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid fixture data",
    "details": [
      {
        "field": "fixtures[0].home_team",
        "issue": "Team not found in database",
        "suggestion": "Use /api/teams/search to find correct team name"
      }
    ]
  },
  "meta": {
    "timestamp": "2025-01-02T10:00:00Z",
    "request_id": "req_abc123",
    "version": "v2.0.0"
  }
}
```

### 4.2 GraphQL API (Optional)

```graphql
type Query {
  jackpots(first: Int, after: String): JackpotConnection
  jackpot(id: ID!): Jackpot
  predictions(jackpotId: ID!, set: PredictionSet): [Prediction]
  teams(league: String, search: String): [Team]
}

type Mutation {
  createJackpot(input: CreateJackpotInput!): Jackpot
  generatePredictions(jackpotId: ID!): PredictionResponse
  generateTickets(input: GenerateTicketsInput!): TicketResponse
}

type Jackpot {
  id: ID!
  name: String!
  fixtures: [Fixture!]!
  predictions(set: PredictionSet): [Prediction!]
  createdAt: DateTime!
}

type Fixture {
  id: ID!
  homeTeam: Team!
  awayTeam: Team!
  date: DateTime!
}

type Prediction {
  id: ID!
  fixture: Fixture!
  probabilities: Probabilities!
  entropy: Float!
}

type Probabilities {
  home: Float!
  draw: Float!
  away: Float!
}

enum PredictionSet {
  A, B, C, D, E, F, G, H, I, J
}
```

---

## 5. ML Pipeline Design

### 5.1 Training Pipeline (Airflow DAG)

```python
# dags/model_training_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email': ['ml-team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'model_training_weekly',
    default_args=default_args,
    description='Weekly model training pipeline',
    schedule_interval='0 2 * * 0',  # Every Sunday at 2 AM
    catchup=False
)

# Task 1: Extract data
extract_data_task = PythonOperator(
    task_id='extract_training_data',
    python_callable=extract_training_data,
    op_kwargs={
        'start_date': '{{ ds }}',
        'lookback_days': 730  # 2 years
    },
    dag=dag
)

# Task 2: Feature engineering
feature_engineering_task = PythonOperator(
    task_id='engineer_features',
    python_callable=engineer_features,
    dag=dag
)

# Task 3: Hyperparameter tuning
tuning_task = PythonOperator(
    task_id='hyperparameter_tuning',
    python_callable=hyperparameter_tuning,
    op_kwargs={
        'n_trials': 100,
        'metric': 'brier_score'
    },
    dag=dag
)

# Task 4: Train model
train_task = PythonOperator(
    task_id='train_model',
    python_callable=train_dixon_coles,
    dag=dag
)

# Task 5: Validate model
validate_task = PythonOperator(
    task_id='validate_model',
    python_callable=validate_model,
    op_kwargs={
        'threshold_brier': 0.15,
        'threshold_logloss': 0.45
    },
    dag=dag
)

# Task 6: A/B test
ab_test_task = PythonOperator(
    task_id='ab_test',
    python_callable=deploy_ab_test,
    op_kwargs={
        'traffic_split': 0.5  # 50/50 split
    },
    dag=dag
)

# Task 7: Promote to production
promote_task = PythonOperator(
    task_id='promote_to_production',
    python_callable=promote_model,
    dag=dag
)

# Define dependencies
extract_data_task >> feature_engineering_task >> tuning_task >> train_task >> validate_task >> ab_test_task >> promote_task
```

### 5.2 Feature Store (Feast)

```python
# features/team_features.py
from feast import Entity, Feature, FeatureView, ValueType
from feast.data_source import FileSource

# Define entity
team = Entity(
    name="team_id",
    value_type=ValueType.INT64,
    description="Team identifier"
)

# Define data source
team_features_source = FileSource(
    path="s3://feature-store/team_features.parquet",
    event_timestamp_column="calculated_at"
)

# Define feature view
team_features_view = FeatureView(
    name="team_features",
    entities=["team_id"],
    ttl=timedelta(days=7),
    features=[
        Feature(name="attack_rating", dtype=ValueType.DOUBLE),
        Feature(name="defense_rating", dtype=ValueType.DOUBLE),
        Feature(name="goals_scored_5", dtype=ValueType.DOUBLE),
        Feature(name="goals_conceded_5", dtype=ValueType.DOUBLE),
        Feature(name="win_rate_5", dtype=ValueType.DOUBLE),
        Feature(name="draw_rate_5", dtype=ValueType.DOUBLE),
        Feature(name="home_win_rate", dtype=ValueType.DOUBLE),
    ],
    online=True,
    source=team_features_source,
    tags={"team": "ml-team"}
)
```

```python
# Usage in prediction service
from feast import FeatureStore

store = FeatureStore(repo_path=".")

# Get features for teams
features = store.get_online_features(
    features=[
        "team_features:attack_rating",
        "team_features:defense_rating",
        "team_features:goals_scored_5",
        "team_features:goals_conceded_5",
    ],
    entity_rows=[
        {"team_id": 1},  # Arsenal
        {"team_id": 2},  # Chelsea
    ]
).to_dict()
```

---

## 6. Infrastructure Design

### 6.1 Kubernetes Architecture

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: football-probability
---
# k8s/deployments/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: football-probability
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: football-probability/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# k8s/services/api-gateway.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: football-probability
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
# k8s/hpa/api-gateway.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: football-probability
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 6.2 Infrastructure as Code (Terraform)

```hcl
# terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# EKS Cluster
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "19.0"
  cluster_name    = "football-probability-prod"
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 3
      max_size     = 10
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
    
    ml = {
      desired_size = 1
      min_size     = 0
      max_size     = 5
      
      instance_types = ["c5.2xlarge"]
      capacity_type  = "SPOT"
      
      labels = {
        workload = "ml-training"
      }
      
      taints = [{
        key    = "workload"
        value  = "ml-training"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier           = "football-probability-db"
  engine              = "postgres"
  engine_version      = "15.4"
  instance_class      = "db.r6g.xlarge"
  allocated_storage   = 100
  storage_encrypted   = true
  
  username = var.db_username
  password = var.db_password
  
  multi_az               = true
  backup_retention_period = 7
  
  tags = {
    Name = "football-probability-postgres"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "football-probability-redis"
  engine              = "redis"
  engine_version      = "7.0"
  node_type           = "cache.r6g.large"
  num_cache_nodes     = 3
  parameter_group_name = "default.redis7.cluster.on"
  
  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
  
  tags = {
    Name = "football-probability-redis"
  }
}

# S3 Bucket for ML artifacts
resource "aws_s3_bucket" "ml_artifacts" {
  bucket = "football-probability-ml-artifacts"
  
  tags = {
    Name = "ML Artifacts"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/eks/football-probability/app"
  retention_in_days = 30
}
```

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

```python
# OAuth2 + JWT Implementation
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User roles
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    API_CLIENT = "api_client"

# Token creation
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Authentication dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_from_db(user_id)
    if user is None:
        raise credentials_exception
    return user

# Authorization decorator
def require_role(role: UserRole):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role != role and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker
```

### 7.2 API Rate Limiting

```python
# Redis-based rate limiting
from redis import Redis
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if request is within rate limit
        
        Uses sliding window algorithm
        """
        now = datetime.now().timestamp()
        window_start = now - window_seconds
        
        # Remove old requests
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        request_count = self.redis.zcard(key)
        
        if request_count >= max_requests:
            return False
        
        # Add current request
        self.redis.zadd(key, {str(now): now})
        
        # Set expiry
        self.redis.expire(key, window_seconds)
        
        return True

# Usage in FastAPI
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    rate_limiter = RateLimiter(redis_client)
    
    # Get user tier
    user_tier = get_user_tier(request)
    limits = RATE_LIMITS[user_tier]
    
    # Check rate limit
    key = f"rate_limit:{user_tier}:{request.client.host}"
    if not await rate_limiter.check_rate_limit(
        key,
        limits["minute"],
        60
    ):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )
    
    response = await call_next(request)
    return response
```

---

## 8. Deployment Strategy

### 8.1 Blue-Green Deployment

```yaml
# k8s/deployments/blue-green.yaml

# Blue deployment (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway-blue
  namespace: football-probability
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
      version: blue
  template:
    metadata:
      labels:
        app: api-gateway
        version: blue
    spec:
      containers:
      - name: api-gateway
        image: football-probability/api-gateway:v2.4.1
---
# Green deployment (new version)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway-green
  namespace: football-probability
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
      version: green
  template:
    metadata:
      labels:
        app: api-gateway
        version: green
    spec:
      containers:
      - name: api-gateway
        image: football-probability/api-gateway:v2.5.0
---
# Service (switch between blue/green)
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: football-probability
spec:
  selector:
    app: api-gateway
    version: blue  # Change to "green" to switch
  ports:
  - port: 80
    targetPort: 8000
```

### 8.2 Canary Deployment

```yaml
# k8s/deployments/canary.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api.football-probability.com
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: api-gateway
        subset: canary
  - route:
    - destination:
        host: api-gateway
        subset: stable
      weight: 90
    - destination:
        host: api-gateway
        subset: canary
      weight: 10
```

### 8.3 Rollback Strategy

```bash
#!/bin/bash
# scripts/rollback.sh

# Get current deployment
CURRENT_DEPLOYMENT=$(kubectl get deployment -n football-probability \
  -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')

echo "Current deployment: $CURRENT_DEPLOYMENT"

# Get previous revision
PREVIOUS_REVISION=$(kubectl rollout history deployment/$CURRENT_DEPLOYMENT \
  -n football-probability | tail -n 2 | head -n 1 | awk '{print $1}')

echo "Rolling back to revision: $PREVIOUS_REVISION"

# Rollback
kubectl rollout undo deployment/$CURRENT_DEPLOYMENT \
  -n football-probability \
  --to-revision=$PREVIOUS_REVISION

# Monitor rollback
kubectl rollout status deployment/$CURRENT_DEPLOYMENT \
  -n football-probability
```

---

## Conclusion

This architectural design provides a **production-ready, scalable, and maintainable** system for the Football Probability Engine. Key improvements include:

1. ✅ **Microservices Architecture** - Independent scaling and deployment
2. ✅ **Modern ML Pipeline** - MLflow, Feast, Airflow
3. ✅ **High Performance** - Redis caching, read replicas, TimescaleDB
4. ✅ **Observability** - Prometheus, Grafana, Jaeger
5. ✅ **Security** - OAuth2, rate limiting, encryption
6. ✅ **Scalability** - Kubernetes, horizontal auto-scaling
7. ✅ **Reliability** - Blue-green deployments, automated rollbacks

**Next Steps:**
1. Review this design with stakeholders
2. Prioritize implementation phases
3. Begin with Phase 1 (Foundation)
4. Iterate based on feedback

---

**Document Version:** 2.0  
**Last Updated:** January 2, 2026  
**Architect:** Claude (Sonnet 4.5)  

