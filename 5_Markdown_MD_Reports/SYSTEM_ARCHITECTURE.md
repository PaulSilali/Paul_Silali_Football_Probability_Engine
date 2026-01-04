# Football Probability Engine - System Architecture

## Version: 2.0.0
## Date: 2025-01-XX

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Database Schema](#database-schema)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow](#data-flow)
7. [API Endpoints](#api-endpoints)
8. [Model Training Pipeline](#model-training-pipeline)
9. [Backtesting Workflow](#backtesting-workflow)
10. [Testing Strategy](#testing-strategy)

---

## System Overview

The Football Probability Engine is a full-stack application that provides calibrated probability estimates for football match outcomes using Dixon-Coles Poisson models, market odds blending, and isotonic calibration.

### Technology Stack

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI + Python 3.11+ + SQLAlchemy 2.0
- **Database:** PostgreSQL 15+
- **Deployment:** Docker-ready

### Core Principles

- **Deterministic:** All predictions are reproducible
- **Immutable:** Jackpot predictions cannot be modified after creation
- **Audit-Safe:** Full audit trail of all operations
- **Probability Correctness:** Enforced at database level

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (React)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Pages   │  │Components│  │ Services │  │  Types   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Backend Layer (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   API    │  │ Services │  │  Models  │  │ Schemas  │   │
│  │ Routers  │  │          │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ SQLAlchemy ORM
                            │
┌─────────────────────────────────────────────────────────────┐
│              Database Layer (PostgreSQL)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Reference │  │Historical│  │  Models  │  │ Jackpots │   │
│  │  Tables  │  │   Data   │  │ Registry │  │ & Preds │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Core Tables

#### Reference Data
- **`leagues`** - League metadata (code, name, country, tier, draw rates)
- **`teams`** - Team registry with Dixon-Coles strength parameters
- **`team_h2h_stats`** - Head-to-head statistics for draw eligibility

#### Historical Data
- **`matches`** - Historical match results with closing odds
- **`team_features`** - Rolling team statistics (goals, form, etc.)
- **`league_stats`** - League-level baseline statistics per season

#### Model Registry
- **`models`** - Trained model registry (Poisson, Blending, Calibration)
- **`training_runs`** - Training execution history with metrics
- **`calibration_data`** - Isotonic calibration curves per outcome

#### Jackpot & Predictions
- **`jackpots`** - User jackpot submissions
- **`jackpot_fixtures`** - Individual fixtures within jackpots
- **`predictions`** - Probability predictions for all sets (A-J)
- **`saved_jackpot_templates`** - Saved fixture lists for reuse
- **`saved_probability_results`** - Saved selections and actual results

#### Validation & Audit
- **`validation_results`** - Validation metrics per set
- **`data_sources`** - External data source registry
- **`ingestion_logs`** - Data ingestion execution logs
- **`audit_entries`** - System audit trail
- **`users`** - User accounts

### Key Relationships

```
leagues (1) ──< (N) teams
teams (1) ──< (N) matches (home_team_id, away_team_id)
teams (1) ──< (N) team_h2h_stats (team_home_id, team_away_id)
models (1) ──< (N) predictions
models (1) ──< (N) training_runs
jackpots (1) ──< (N) jackpot_fixtures
jackpot_fixtures (1) ──< (N) predictions
```

---

## Backend Architecture

### Directory Structure

```
app/
├── api/              # FastAPI route handlers
│   ├── auth.py       # Authentication endpoints
│   ├── jackpots.py   # Jackpot CRUD operations
│   ├── probabilities.py  # Probability calculations
│   ├── model.py      # Model management
│   ├── data.py       # Data ingestion
│   ├── validation.py # Calibration & validation
│   ├── teams.py      # Team search & management
│   ├── tickets.py    # Ticket generation
│   └── ...
├── db/               # Database layer
│   ├── models.py     # SQLAlchemy models
│   ├── session.py    # Database session management
│   └── base.py       # Base class
├── models/           # Business logic models
│   ├── dixon_coles.py      # Dixon-Coles Poisson model
│   ├── probability_sets.py # Probability set generation
│   ├── calibration.py       # Isotonic calibration
│   ├── draw_model.py       # Draw probability model
│   └── ...
├── services/         # Service layer
│   ├── model_training.py   # Model training orchestration
│   ├── data_ingestion.py   # Data ingestion service
│   ├── team_resolver.py    # Team name resolution
│   ├── ticket_generation_service.py  # Ticket construction
│   └── ...
└── schemas/          # Pydantic schemas
    ├── prediction.py # Prediction request/response
    ├── jackpot.py    # Jackpot schemas
    └── auth.py       # Auth schemas
```

### Model Training Pipeline

```
1. Data Preparation
   └─> Historical matches (matches table)
   └─> Team strengths (teams table)
   └─> League parameters (leagues table)

2. Poisson Model Training
   └─> Learn team attack/defense ratings
   └─> Learn home advantage (rho)
   └─> Time decay parameter (xi)
   └─> Save to models table (model_type='poisson')

3. Blending Model Training
   └─> Learn optimal alpha (model vs market weight)
   └─> Reference poisson_model_id
   └─> Save to models table (model_type='blending')

4. Calibration Model Training
   └─> Isotonic regression per outcome (H, D, A)
   └─> Reference base_model_id (blending or poisson)
   └─> Save to models table (model_type='calibration')
   └─> Save calibration curves to calibration_data table

5. Validation
   └─> Calculate Brier score, log loss, accuracy
   └─> Save metrics to models table
   └─> Save training run to training_runs table
```

### Probability Calculation Flow

```
1. User submits jackpot (jackpots, jackpot_fixtures tables)
   └─> Team resolution (teams table)
   └─> League identification (leagues table)

2. Load active models
   └─> Calibration model (if exists)
   └─> Base model (blending or poisson)
   └─> Poisson model (for expected goals)

3. Calculate probabilities per fixture
   └─> Get team strengths from model_weights
   └─> Calculate expected goals (lambda_home, lambda_away)
   └─> Apply Dixon-Coles correction (rho)
   └─> Blend with market odds (if available)
   └─> Apply calibration curves
   └─> Generate all sets (A-J)

4. Save predictions
   └─> Save to predictions table (one row per set per fixture)
   └─> Update jackpot status to 'calculated'

5. Return to frontend
   └─> All probability sets (A-J)
   └─> Model version
   └─> Confidence flags
```

---

## Frontend Architecture

### Directory Structure

```
src/
├── pages/            # Page components
│   ├── Dashboard.tsx
│   ├── JackpotInput.tsx
│   ├── ProbabilityOutput.tsx
│   ├── MLTraining.tsx
│   └── ...
├── components/       # Reusable components
│   ├── ui/          # shadcn/ui components
│   ├── AccumulatorCalculator.tsx
│   ├── BacktestComparison.tsx
│   └── ...
├── services/        # API client
│   └── api.ts       # Centralized API service
├── types/           # TypeScript types
│   └── index.ts
├── contexts/        # React contexts
│   └── AuthContext.tsx
└── lib/             # Utilities
    └── utils.ts
```

### Page Components

1. **Dashboard** - System health, model metrics, data freshness
2. **JackpotInput** - Create jackpot with fixtures and odds
3. **ProbabilityOutput** - Display all probability sets (A-J)
4. **SetsComparison** - Compare probability sets side-by-side
5. **TicketConstruction** - Generate betting tickets
6. **Backtesting** - Historical performance analysis
7. **JackpotValidation** - Validate predictions vs actuals
8. **MLTraining** - Train new models
9. **DataIngestion** - Import match data
10. **DataCleaning** - Clean and prepare training data
11. **Calibration** - Calibration curves visualization
12. **ModelHealth** - Model drift monitoring
13. **Explainability** - Feature contributions
14. **FeatureStore** - Team feature management
15. **System** - System configuration
16. **TrainingDataContract** - Data format documentation
17. **ResponsibleGambling** - Responsible gambling information

---

## Data Flow

### Jackpot Creation Flow

```
Frontend (JackpotInput)
    │
    ├─> POST /api/jackpots
    │       └─> Backend (jackpots.py)
    │           ├─> Validate fixtures
    │           ├─> Resolve teams (team_resolver.py)
    │           ├─> Create jackpot (jackpots table)
    │           └─> Create fixtures (jackpot_fixtures table)
    │
    └─> GET /api/probabilities/{jackpot_id}/probabilities
            └─> Backend (probabilities.py)
                ├─> Load active models (models table)
                ├─> Calculate probabilities (dixon_coles.py)
                ├─> Generate sets (probability_sets.py)
                ├─> Apply calibration (calibration.py)
                ├─> Save predictions (predictions table)
                └─> Return all sets (A-J)
```

### Backtesting Workflow

```
1. User saves probability selections
   └─> POST /api/probabilities/{jackpot_id}/save-result
       └─> Save to saved_probability_results table

2. User enters actual results
   └─> PUT /api/probabilities/saved-results/{id}/actual-results
       └─> Update saved_probability_results.actual_results

3. System calculates scores
   └─> Compare selections vs actual_results
   └─> Update saved_probability_results.scores

4. Export to training data
   └─> POST /api/probabilities/validation/export
       └─> Create validation_results records
       └─> Optionally export to matches table
```

---

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Jackpots
- `GET /api/jackpots` - List all jackpots
- `POST /api/jackpots` - Create jackpot
- `GET /api/jackpots/{id}` - Get jackpot details
- `PUT /api/jackpots/{id}` - Update jackpot
- `DELETE /api/jackpots/{id}` - Delete jackpot
- `POST /api/jackpots/templates` - Save template
- `GET /api/jackpots/templates` - List templates
- `GET /api/jackpots/templates/{id}` - Get template
- `DELETE /api/jackpots/templates/{id}` - Delete template

### Probabilities
- `GET /api/probabilities/{jackpot_id}/probabilities` - Calculate all sets
- `POST /api/probabilities/{jackpot_id}/save-result` - Save selections
- `GET /api/probabilities/{jackpot_id}/saved-results` - Get saved results
- `GET /api/probabilities/saved-results/latest` - Get latest result
- `GET /api/probabilities/saved-results/all` - Get all results
- `PUT /api/probabilities/saved-results/{id}/actual-results` - Update actuals
- `POST /api/probabilities/validation/export` - Export to training

### Models
- `GET /api/model/status` - Get model status
- `GET /api/model/versions` - List all model versions
- `GET /api/model/training-history` - Get training history
- `POST /api/model/train` - Train new model
- `GET /api/model/leagues` - Get available leagues

### Data
- `GET /api/data/batches` - Get batch history
- `POST /api/data/batch-download` - Batch download
- `POST /api/data/refresh` - Refresh data source
- `GET /api/data/freshness` - Get data freshness
- `POST /api/data/prepare-training-data` - Prepare training data

### Validation & Calibration
- `GET /api/calibration` - Get calibration data
- `GET /api/calibration/validation-metrics` - Get validation metrics

### Teams
- `GET /api/teams/all` - Get all teams
- `GET /api/teams/search` - Search teams
- `POST /api/validation/team` - Validate team name

### Tickets
- `POST /api/tickets/generate` - Generate tickets
- `GET /api/tickets/draw-diagnostics` - Get draw diagnostics

### Audit
- `GET /api/audit` - Get audit log

---

## Backtesting Workflow

### Complete Flow

```
1. CREATE JACKPOT
   └─> User inputs fixtures with odds
   └─> POST /api/jackpots
   └─> Saved to: jackpots, jackpot_fixtures tables

2. CALCULATE PROBABILITIES
   └─> GET /api/probabilities/{jackpot_id}/probabilities
   └─> System calculates all sets (A-J)
   └─> Saved to: predictions table

3. USER SELECTS PICKS
   └─> User makes selections per set
   └─> POST /api/probabilities/{jackpot_id}/save-result
   └─> Saved to: saved_probability_results table
   └─> Fields: selections (JSONB), jackpot_id, name

4. MATCHES COMPLETE
   └─> User enters actual results
   └─> PUT /api/probabilities/saved-results/{id}/actual-results
   └─> Updated: saved_probability_results.actual_results (JSONB)

5. SCORE CALCULATION
   └─> System compares selections vs actual_results
   └─> Calculates correct/total per set
   └─> Updated: saved_probability_results.scores (JSONB)

6. VALIDATION EXPORT
   └─> POST /api/probabilities/validation/export
   └─> Creates: validation_results records
   └─> Aggregates: total_matches, correct_predictions, accuracy
   └─> Optionally: Exports to matches table for training

7. CALIBRATION UPDATE
   └─> Validation results feed into calibration model
   └─> Updates: calibration_data table
   └─> Improves: Future probability predictions
```

### Database Tables Involved

- `jackpots` - Jackpot metadata
- `jackpot_fixtures` - Individual fixtures
- `predictions` - Probability predictions (all sets)
- `saved_probability_results` - User selections and actual results
- `validation_results` - Aggregated validation metrics
- `calibration_data` - Calibration curves (updated from validation)

---

## Testing Strategy

### Frontend Tests

1. **Component Tests**
   - Test all page components render
   - Test API calls are made correctly
   - Test error handling
   - Test loading states

2. **Integration Tests**
   - Test complete workflows (jackpot creation → probabilities → saving)
   - Test backtesting workflow end-to-end
   - Test data flow: Frontend → Backend → Database

3. **E2E Tests**
   - Test user journeys
   - Test all 17 pages
   - Test all cards display real data

### Backend Tests

1. **Unit Tests**
   - Test model calculations
   - Test probability set generation
   - Test calibration logic

2. **API Tests**
   - Test all endpoints
   - Test database queries
   - Test error handling

3. **Integration Tests**
   - Test model training pipeline
   - Test backtesting workflow
   - Test data ingestion

### Database Tests

1. **Schema Tests**
   - Verify all tables exist
   - Verify all constraints
   - Verify all indexes

2. **Data Integrity Tests**
   - Test foreign key relationships
   - Test probability sum constraints
   - Test unique constraints

---

## Deployment Architecture

### Development
- Frontend: Vite dev server (port 5173)
- Backend: FastAPI uvicorn (port 8000)
- Database: PostgreSQL (port 5432)

### Production
- Frontend: Static build served by Nginx
- Backend: FastAPI with Gunicorn/Uvicorn workers
- Database: PostgreSQL with replication
- Caching: Redis (optional)
- Monitoring: Prometheus + Grafana (optional)

---

## Security Considerations

1. **Authentication**
   - JWT tokens for API access
   - Password hashing (bcrypt)
   - Session management

2. **Data Protection**
   - Input validation (Pydantic schemas)
   - SQL injection prevention (SQLAlchemy ORM)
   - XSS prevention (React sanitization)

3. **Audit Trail**
   - All actions logged to audit_entries table
   - Immutable prediction records
   - User action tracking

---

## Performance Optimization

1. **Database**
   - Indexes on frequently queried columns
   - Connection pooling
   - Query optimization

2. **Backend**
   - Async endpoints where possible
   - Caching of model weights
   - Batch operations for data ingestion

3. **Frontend**
   - Code splitting
   - Lazy loading
   - API response caching

---

## Future Enhancements

1. **Real-time Updates**
   - WebSocket support for live predictions
   - Real-time model training progress

2. **Advanced Analytics**
   - League-specific model variants
   - Time-series forecasting
   - Market sentiment analysis

3. **Scalability**
   - Horizontal scaling
   - Database sharding
   - CDN for static assets

---

**Last Updated:** 2025-01-XX
**Version:** 2.0.0

