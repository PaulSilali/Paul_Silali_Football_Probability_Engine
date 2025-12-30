# Environment Variables Usage Summary

## Overview

This document provides a complete mapping of all environment variables used in both frontend and backend, showing exactly where they are accessed in the codebase.

---

## Frontend Environment Variables

### Location: `1_Frontend_Football_Probability_Engine`

#### Variable: `VITE_API_URL`

**Default**: `http://localhost:8000/api`

**Used In**:
- `src/services/api.ts:19`
  ```typescript
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  ```

**Purpose**: Backend API base URL for all HTTP requests

**Setup**:
1. Create `.env` file in `1_Frontend_Football_Probability_Engine/`
2. Add: `VITE_API_URL=http://localhost:8000/api`
3. See `1_Frontend_Football_Probability_Engine/ENV_SETUP.md` for details

---

## Backend Environment Variables

### Location: `2_Backend_Football_Probability_Engine`

All backend environment variables are defined in `app/config.py` and accessed via `settings.*`

### Database Configuration

#### Variables:
- `DB_HOST` (default: `localhost`)
- `DB_PORT` (default: `5432`)
- `DB_NAME` (default: `football_probability_engine`)
- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (default: `""`)
- `DATABASE_URL` (optional, auto-constructed)
- `DATABASE_POOL_SIZE` (default: `5`)
- `DATABASE_MAX_OVERFLOW` (default: `10`)
- `DATABASE_ECHO` (default: `False`)

**Used In**:
- `app/config.py:14-26` - Variable definitions
- `app/config.py:28-38` - `get_database_url()` method
- `app/db/session.py:10-15` - Database engine creation
  ```python
  engine = create_engine(
      settings.get_database_url(),
      pool_size=settings.DATABASE_POOL_SIZE,
      max_overflow=settings.DATABASE_MAX_OVERFLOW,
      echo=settings.DATABASE_ECHO,
  )
  ```

### API Configuration

#### Variables:
- `API_PREFIX` (default: `/api`)
- `API_TITLE` (default: `Football Jackpot Probability Engine API`)
- `API_VERSION` (default: `v2.4.1`)

**Used In**:
- `app/main.py:21-22` - FastAPI app initialization
  ```python
  app = FastAPI(
      title=settings.API_TITLE,
      version=settings.API_VERSION,
  )
  ```
- `app/main.py:48-59` - Router prefix
  ```python
  app.include_router(auth.router, prefix=settings.API_PREFIX)
  ```
- `app/api/auth.py:22` - OAuth2 token URL
  ```python
  oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")
  ```

### CORS Configuration

#### Variables:
- `CORS_ORIGINS` (default: `["http://localhost:8080", "http://localhost:3000"]`)
- `CORS_ALLOW_CREDENTIALS` (default: `True`)
- `CORS_ALLOW_METHODS` (default: `["*"]`)
- `CORS_ALLOW_HEADERS` (default: `["*"]`)

**Used In**:
- `app/main.py:39-45` - CORS middleware configuration
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS,
      allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
      allow_methods=settings.CORS_ALLOW_METHODS,
      allow_headers=settings.CORS_ALLOW_HEADERS,
  )
  ```

### Security Configuration

#### Variables:
- `SECRET_KEY` (default: `change-this-in-production`)
- `ALGORITHM` (default: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: `30`)

**Used In**:
- `app/api/auth.py:41` - Token expiration
  ```python
  expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  ```
- `app/api/auth.py:44` - JWT encoding
  ```python
  encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
  ```

### Redis & Celery Configuration

#### Variables:
- `REDIS_URL` (default: `redis://localhost:6379/0`)
- `CELERY_BROKER_URL` (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND` (default: `redis://localhost:6379/0`)

**Used In**: 
- Currently configured but Celery tasks not yet fully implemented
- Will be used for background job processing

### External API Configuration

#### Variables:
- `API_FOOTBALL_KEY` (default: `""`)
- `FOOTBALL_DATA_BASE_URL` (default: `https://www.football-data.co.uk`)

**Used In**:
- `app/services/data_ingestion.py` - For fetching external football data
- Currently configured but implementation pending

### Environment Settings

#### Variables:
- `ENV` (default: `development`)
- `DEBUG` (default: `True`)
- `LOG_LEVEL` (default: `INFO`)

**Used In**:
- `app/main.py:14-17` - Logging configuration
  ```python
  logging.basicConfig(
      level=getattr(logging, settings.LOG_LEVEL),
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )
  ```
- `run.py:12` - Server reload
  ```python
  reload=settings.DEBUG,
  ```

### Model Configuration

#### Variables:
- `MODEL_VERSION` (default: `v2.4.1`)
- `DEFAULT_DECAY_RATE` (default: `0.0065`)
- `DEFAULT_HOME_ADVANTAGE` (default: `0.35`)
- `DEFAULT_RHO` (default: `-0.13`)

**Used In**:
- Model registry and Dixon-Coles model parameters
- Defaults for model training

### Validation Constants

#### Variables:
- `MIN_VALID_ODDS` (default: `1.01`)
- `MAX_VALID_ODDS` (default: `100.0`)
- `PROBABILITY_SUM_TOLERANCE` (default: `0.001`)
- `MAX_GOALS_IN_CALCULATION` (default: `8`)

**Used In**:
- Input validation and probability calculations
- Currently defined but specific usage pending implementation

---

## Complete File Reference

### Frontend Files Using Environment Variables

| File | Line | Variable | Usage |
|------|------|----------|-------|
| `src/services/api.ts` | 19 | `VITE_API_URL` | API base URL |

### Backend Files Using Environment Variables

| File | Line(s) | Variables | Usage |
|------|---------|-----------|-------|
| `app/config.py` | 14-85 | All variables | Variable definitions |
| `app/db/session.py` | 10-15 | `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_ECHO` | Database connection |
| `app/main.py` | 15 | `LOG_LEVEL` | Logging level |
| `app/main.py` | 21-22 | `API_TITLE`, `API_VERSION` | FastAPI app config |
| `app/main.py` | 41-44 | `CORS_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS` | CORS middleware |
| `app/main.py` | 48-59 | `API_PREFIX` | Router prefixes |
| `app/api/auth.py` | 22 | `API_PREFIX` | OAuth2 token URL |
| `app/api/auth.py` | 41 | `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration |
| `app/api/auth.py` | 44 | `SECRET_KEY`, `ALGORITHM` | JWT encoding |
| `run.py` | 12-13 | `DEBUG`, `LOG_LEVEL` | Server configuration |

---

## Setup Checklist

### Frontend
- [ ] Create `.env` file in `1_Frontend_Football_Probability_Engine/`
- [ ] Add `VITE_API_URL=http://localhost:8000/api`
- [ ] Restart dev server

### Backend
- [ ] Create `.env` file in `2_Backend_Football_Probability_Engine/`
- [ ] Run `python generate_env.py` OR manually create with values from `ENV_SETUP.md`
- [ ] Update database credentials (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- [ ] Update `SECRET_KEY` for production
- [ ] Update `CORS_ORIGINS` with frontend URL(s)
- [ ] Restart backend server

---

## Your Current Configuration

Based on your provided values:

```bash
# Backend .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_probability_engine
DB_USER=postgres
DB_PASSWORD=11403775411
```

All other variables will use their defaults from `app/config.py`.

---

## Notes

1. **Frontend**: Only 1 variable (`VITE_API_URL`) is currently used
2. **Backend**: 29 variables total, all defined in `app/config.py`
3. **Database URL**: Auto-constructed from `DB_*` variables if `DATABASE_URL` not provided
4. **Security**: Never commit `.env` files (already in `.gitignore`)
5. **Defaults**: All variables have defaults, so `.env` is optional but recommended

