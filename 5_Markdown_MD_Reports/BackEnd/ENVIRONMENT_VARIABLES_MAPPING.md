# Environment Variables Mapping & Usage Guide

This document maps all environment variables used in both frontend and backend, showing where they are defined, accessed, and their purpose.

## Frontend Environment Variables

### Location
- **Config File**: `1_Frontend_Football_Probability_Engine/vite.config.ts`
- **Usage**: Accessed via `import.meta.env.VITE_*` in React/Vite
- **File**: `.env` or `.env.local` in frontend root (not currently tracked)

### Variables Used

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000/api` | `src/services/api.ts:19` | Backend API base URL for all API calls |

**Current Usage:**
```typescript
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
```

### Frontend .env File Template
```bash
# Frontend Environment Variables
# Create this file: 1_Frontend_Football_Probability_Engine/.env

# Backend API URL
VITE_API_URL=http://localhost:8000/api

# For production, use:
# VITE_API_URL=https://your-api-domain.com/api
```

---

## Backend Environment Variables

### Location
- **Config File**: `2_Backend_Football_Probability_Engine/app/config.py`
- **Usage**: Accessed via `settings.*` throughout the backend
- **File**: `.env` in backend root (already in .gitignore)

### Database Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `DB_HOST` | `localhost` | `app/config.py:14` | PostgreSQL host |
| `DB_PORT` | `5432` | `app/config.py:15` | PostgreSQL port |
| `DB_NAME` | `football_probability_engine` | `app/config.py:16` | Database name |
| `DB_USER` | `postgres` | `app/config.py:17` | Database user |
| `DB_PASSWORD` | `""` | `app/config.py:18` | Database password |
| `DATABASE_URL` | `None` (auto-constructed) | `app/config.py:21` | Full connection URL (optional) |
| `DATABASE_POOL_SIZE` | `5` | `app/db/session.py:12` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | `app/db/session.py:13` | Max pool overflow |
| `DATABASE_ECHO` | `False` | `app/db/session.py:14` | SQL query logging |

**Usage:**
```python
# app/db/session.py
engine = create_engine(
    settings.get_database_url(),  # Constructs from DB_* vars
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
)
```

### API Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `API_PREFIX` | `/api` | `app/main.py:48-59` | API route prefix |
| `API_TITLE` | `Football Jackpot Probability Engine API` | `app/main.py:21` | API title |
| `API_VERSION` | `v2.4.1` | `app/main.py:22` | API version |

**Usage:**
```python
# app/main.py
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
)
app.include_router(auth.router, prefix=settings.API_PREFIX)
```

### CORS Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `CORS_ORIGINS` | `["http://localhost:8080", "http://localhost:3000"]` | `app/main.py:41` | Allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `True` | `app/main.py:42` | Allow credentials |
| `CORS_ALLOW_METHODS` | `["*"]` | `app/main.py:43` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `["*"]` | `app/main.py:44` | Allowed headers |

**Usage:**
```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
```

### Security Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `SECRET_KEY` | `change-this-in-production` | `app/api/auth.py` (JWT) | JWT secret key |
| `ALGORITHM` | `HS256` | `app/api/auth.py` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | `app/api/auth.py` | Token expiration |

**Usage:**
```python
# app/api/auth.py (implied usage)
# Used for JWT token generation and validation
```

### Redis & Celery Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379/0` | Background tasks | Redis connection |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery | Broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery | Result backend |

**Note**: Currently configured but Celery tasks not yet fully implemented.

### External API Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `API_FOOTBALL_KEY` | `""` | `app/services/data_ingestion.py` | API-Football API key |
| `FOOTBALL_DATA_BASE_URL` | `https://www.football-data.co.uk` | `app/services/data_ingestion.py` | Football data base URL |

**Usage:**
```python
# app/services/data_ingestion.py
# Used for fetching external football data
```

### Environment Settings

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `ENV` | `development` | General | Environment name |
| `DEBUG` | `True` | General | Debug mode |
| `LOG_LEVEL` | `INFO` | `app/main.py:15` | Logging level |

**Usage:**
```python
# app/main.py
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Model Configuration

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `MODEL_VERSION` | `v2.4.1` | Model registry | Current model version |
| `DEFAULT_DECAY_RATE` | `0.0065` | `app/models/dixon_coles.py` | Time decay parameter |
| `DEFAULT_HOME_ADVANTAGE` | `0.35` | `app/models/dixon_coles.py` | Home advantage factor |
| `DEFAULT_RHO` | `-0.13` | `app/models/dixon_coles.py` | Low-score dependency |

**Note**: These are defaults; actual model parameters are stored in database.

### Validation Constants

| Variable | Default Value | Used In | Purpose |
|----------|--------------|---------|---------|
| `MIN_VALID_ODDS` | `1.01` | Validation | Minimum valid odds |
| `MAX_VALID_ODDS` | `100.0` | Validation | Maximum valid odds |
| `PROBABILITY_SUM_TOLERANCE` | `0.001` | Validation | Probability sum tolerance |
| `MAX_GOALS_IN_CALCULATION` | `8` | `app/models/dixon_coles.py` | Max goals in Poisson calc |

---

## Complete .env File Templates

### Backend .env File
```bash
# ============================================================================
# Database Configuration
# ============================================================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_probability_engine
DB_USER=postgres
DB_PASSWORD=11403775411
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False

# ============================================================================
# API Configuration
# ============================================================================
API_PREFIX=/api
API_TITLE=Football Jackpot Probability Engine API
API_VERSION=v2.4.1

# ============================================================================
# CORS Configuration
# ============================================================================
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*

# ============================================================================
# Security Configuration
# ============================================================================
SECRET_KEY=change-this-in-production-use-secrets-token-urlsafe-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================================================
# Redis & Celery Configuration
# ============================================================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ============================================================================
# External API Keys
# ============================================================================
API_FOOTBALL_KEY=
FOOTBALL_DATA_BASE_URL=https://www.football-data.co.uk

# ============================================================================
# Environment Settings
# ============================================================================
ENV=development
DEBUG=True
LOG_LEVEL=INFO

# ============================================================================
# Model Configuration
# ============================================================================
MODEL_VERSION=v2.4.1
DEFAULT_DECAY_RATE=0.0065
DEFAULT_HOME_ADVANTAGE=0.35
DEFAULT_RHO=-0.13

# ============================================================================
# Validation Constants
# ============================================================================
MIN_VALID_ODDS=1.01
MAX_VALID_ODDS=100.0
PROBABILITY_SUM_TOLERANCE=0.001
MAX_GOALS_IN_CALCULATION=8
```

### Frontend .env File
```bash
# Frontend Environment Variables
# Create: 1_Frontend_Football_Probability_Engine/.env

# Backend API URL
VITE_API_URL=http://localhost:8000/api
```

---

## Usage Summary

### Frontend
- **1 variable**: `VITE_API_URL`
- **Location**: `src/services/api.ts`
- **Access**: `import.meta.env.VITE_API_URL`

### Backend
- **29 variables** total
- **Location**: `app/config.py` (Settings class)
- **Access**: `settings.VARIABLE_NAME`
- **Primary usage areas**:
  - Database: `app/db/session.py`
  - API: `app/main.py`
  - Auth: `app/api/auth.py`
  - Data ingestion: `app/services/data_ingestion.py`
  - Models: `app/models/dixon_coles.py`

---

## Important Notes

1. **Frontend**: Only `VITE_API_URL` is currently used. Vite requires `VITE_` prefix for env vars to be exposed to client code.

2. **Backend**: All variables are loaded from `.env` file via Pydantic Settings. Defaults are provided in `app/config.py`.

3. **Database URL**: Can be provided as full `DATABASE_URL` OR constructed from individual `DB_*` variables (preferred method).

4. **Security**: Never commit `.env` files to version control. They are already in `.gitignore`.

5. **Production**: Update `SECRET_KEY`, `CORS_ORIGINS`, `DEBUG=False`, and database credentials for production.

---

## Quick Setup Commands

### Backend
```bash
cd 2_Backend_Football_Probability_Engine
python generate_env.py  # Generates .env with defaults
# Edit .env with your values
```

### Frontend
```bash
cd 1_Frontend_Football_Probability_Engine
# Create .env file manually with VITE_API_URL
```

