#!/usr/bin/env python3
"""
Helper script to generate .env file from template
"""
import secrets
import os

def generate_secret_key():
    """Generate a secure random secret key"""
    return secrets.token_urlsafe(32)

def create_env_file():
    """Create .env file with default values"""
    env_content = f"""# ============================================================================
# Football Jackpot Probability Engine - Environment Configuration
# ============================================================================
# Generated automatically - Update with your actual values
# Never commit .env to version control!

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
# Generated secure secret key - Keep this secret!
SECRET_KEY={generate_secret_key()}
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
"""
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        response = input(f".env file already exists at {env_path}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled. .env file not overwritten.")
            return
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✓ Created .env file at {env_path}")
    print("⚠ Remember to update DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD and other values as needed!")

if __name__ == '__main__':
    create_env_file()

