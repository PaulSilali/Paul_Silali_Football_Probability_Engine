#!/usr/bin/env python3
"""
Check and fix .env file parsing issues
"""
import os
import re
from pathlib import Path

def check_env_file():
    """Check .env file for parsing issues"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print(f"   Expected location: {env_path}")
        return False
    
    print(f"Checking .env file: {env_path}")
    print("=" * 60)
    
    issues = []
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            continue
        
        # Check for common issues
        if line_stripped.startswith('#'):
            # Comment line - check for issues
            if line.startswith(' ') and not line.startswith('#') and '#' in line:
                issues.append((i, "Comment has leading spaces", line))
        elif '=' in line_stripped:
            # Key-value line
            parts = line_stripped.split('=', 1)
            if len(parts) != 2:
                issues.append((i, "Invalid key=value format", line))
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Check for spaces around =
            if ' = ' in line_stripped or line_stripped.startswith(' ') or line_stripped.endswith(' '):
                issues.append((i, "Spaces around = or trailing spaces", line))
        else:
            # Line without = and not a comment - might be issue
            if not line_stripped.startswith('#'):
                issues.append((i, "Line without = or #", line))
    
    if issues:
        print(f"⚠ Found {len(issues)} potential issues:\n")
        for line_num, issue, content in issues:
            print(f"Line {line_num}: {issue}")
            print(f"  Content: {repr(content)}")
            print()
        
        print("=" * 60)
        print("Common fixes:")
        print("1. Remove spaces around = (use KEY=value not KEY = value)")
        print("2. Ensure comments start with # at the beginning of the line")
        print("3. Remove trailing spaces")
        print("4. Remove any blank lines with only spaces")
        return False
    else:
        print("✓ No parsing issues found!")
        return True

def create_clean_env_template():
    """Create a clean .env template"""
    template = """# ============================================================================
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
"""
    
    return template

if __name__ == '__main__':
    print("=" * 60)
    print("Football Probability Engine - .env File Checker")
    print("=" * 60)
    print()
    
    if check_env_file():
        print("\n✓ Your .env file looks good!")
    else:
        print("\n⚠ Issues found. Would you like to:")
        print("1. See a clean template")
        print("2. Exit and fix manually")
        
        response = input("\nEnter choice (1/2): ").strip()
        if response == '1':
            print("\n" + "=" * 60)
            print("Clean .env template:")
            print("=" * 60)
            print(create_clean_env_template())
            print("=" * 60)
            print("\nCopy this template to your .env file and update values as needed.")

