# Environment Configuration Guide

## Overview

The backend uses environment variables for configuration. Create a `.env` file in the `2_Backend_Football_Probability_Engine` directory with the following variables.

## Required Configuration

Create a `.env` file with these settings:

```bash
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Individual database connection parameters (preferred method)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_probability_engine
DB_USER=postgres
DB_PASSWORD=11403775411

# Database connection pool settings
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False

# Alternative: Full DATABASE_URL (optional - will be auto-constructed if not provided)
# DATABASE_URL=postgresql+psycopg://postgres:11403775411@localhost:5432/football_probability_engine

# ============================================================================
# API CONFIGURATION
# ============================================================================
API_PREFIX=/api
API_TITLE=Football Jackpot Probability Engine API
API_VERSION=v2.4.1

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
# IMPORTANT: Change this to a secure random string in production!
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=change-this-in-production-use-secrets-token-urlsafe-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================================================
# REDIS & CELERY CONFIGURATION
# ============================================================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ============================================================================
# EXTERNAL API KEYS
# ============================================================================
API_FOOTBALL_KEY=
FOOTBALL_DATA_BASE_URL=https://www.football-data.co.uk

# ============================================================================
# ENVIRONMENT SETTINGS
# ============================================================================
ENV=development
DEBUG=True
LOG_LEVEL=INFO

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
MODEL_VERSION=v2.4.1
DEFAULT_DECAY_RATE=0.0065
DEFAULT_HOME_ADVANTAGE=0.35
DEFAULT_RHO=-0.13

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================
MIN_VALID_ODDS=1.01
MAX_VALID_ODDS=100.0
PROBABILITY_SUM_TOLERANCE=0.001
MAX_GOALS_IN_CALCULATION=8
```

## Quick Setup

1. Copy the configuration above into a new `.env` file:
   ```bash
   # In the 2_Backend_Football_Probability_Engine directory
   # Create .env file and paste the configuration above
   ```

2. Update the following critical values:
   - **DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD**: Update with your PostgreSQL credentials
   - **SECRET_KEY**: Generate a secure key for production:
     ```python
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - **CORS_ORIGINS**: Add your frontend URL(s)

3. Ensure required services are running:
   - PostgreSQL 15+ (for database)
   - Redis (for caching and Celery)

## Production Checklist

- [ ] Change `SECRET_KEY` to a secure random string
- [ ] Set `DEBUG=False`
- [ ] Set `ENV=production`
- [ ] Update `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` with production database credentials
- [ ] Update `CORS_ORIGINS` with production frontend domain(s)
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR` for production
- [ ] Configure `API_FOOTBALL_KEY` if using live data API
- [ ] Ensure `.env` is in `.gitignore` (already configured)

## Notes

- The `.env` file is already in `.gitignore` - never commit it to version control
- Default values are defined in `app/config.py` if environment variables are not set
- All environment variables are optional but recommended for production

