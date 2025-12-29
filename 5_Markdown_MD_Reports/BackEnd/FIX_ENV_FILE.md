# Fix .env File Issues

## Problem

The error shows:
- `python-dotenv could not parse statement starting at line 4`
- `python-dotenv could not parse statement starting at line 8`
- `error parsing value for field "CORS_ORIGINS"`

## Solution

Your `.env` file likely has syntax errors. Here's the correct format:

### Correct .env File Format

Create or update your `.env` file in `2_Backend_Football_Probability_Engine/` with this content:

```bash
# ============================================================================
# DATABASE CONFIGURATION
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

## Important Notes

1. **No spaces around `=`**: Use `KEY=value` not `KEY = value`
2. **No quotes needed**: Use `value` not `"value"` (unless the value itself contains spaces)
3. **Comments**: Lines starting with `#` are comments
4. **CORS_ORIGINS**: Use comma-separated values: `http://localhost:5173,http://localhost:3000`
5. **No blank lines with just spaces**: Empty lines are OK, but lines with only spaces cause errors

## Quick Fix

1. Delete your current `.env` file
2. Copy the content above into a new `.env` file
3. Update values as needed (especially database credentials)
4. Try running `npm run dev` again

## Verify .env File

Check for common issues:
- ✅ No spaces around `=`
- ✅ No quotes around values (unless needed)
- ✅ No special characters that need escaping
- ✅ Comments start with `#` at the beginning of the line
- ✅ No trailing spaces on lines

