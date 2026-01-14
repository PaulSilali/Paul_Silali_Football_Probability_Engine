"""
Test script to verify injuries download functionality
Tests if API key is configured and if injuries are being downloaded to database
Date: 2026-01-12
"""
import sys
import os
from pathlib import Path

# Get the absolute path to the backend directory
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent  # This is 2_Backend_Football_Probability_Engine

# Add backend directory to Python path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Change to backend directory for relative imports
os.chdir(str(backend_dir))

# Verify we can import
try:
    from app.db.session import get_db
    from app.config import settings
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")
    raise

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.config import settings
from app.db.models import TeamInjuries, JackpotFixture, Team
from datetime import datetime, date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key_configuration():
    """Test if API key is configured"""
    logger.info("=== API KEY CONFIGURATION TEST ===")
    api_key = settings.API_FOOTBALL_KEY
    has_key = api_key and api_key.strip() != ""
    
    logger.info(f"API_FOOTBALL_KEY configured: {has_key}")
    if has_key:
        logger.info(f"API key length: {len(api_key)} characters")
        logger.info(f"API key starts with: {api_key[:8]}...")
        if api_key == "b41227796150918ad901f64b9bdf3b76":
            logger.warning("⚠ Using hardcoded fallback API key (from config.py)")
        else:
            logger.info("✓ Using API key from environment variable or .env file")
    else:
        logger.error("✗ No API key configured - injuries will not be downloaded")
    
    return has_key

def test_injuries_in_database():
    """Test if injuries exist in database"""
    logger.info("\n=== INJURIES IN DATABASE TEST ===")
    
    db: Session = next(get_db())
    try:
        # Count total injuries
        total_injuries = db.query(TeamInjuries).count()
        logger.info(f"Total injuries in database: {total_injuries}")
        
        # Count injuries by fixture
        injuries_by_fixture = db.query(
            TeamInjuries.fixture_id,
            func.count(TeamInjuries.id).label('count')
        ).group_by(TeamInjuries.fixture_id).all()
        
        logger.info(f"Injuries across {len(injuries_by_fixture)} fixtures")
        
        # Get recent injuries (last 7 days)
        recent_injuries = db.query(TeamInjuries).filter(
            TeamInjuries.recorded_at >= datetime.now().date()
        ).count()
        
        logger.info(f"Recent injuries (today): {recent_injuries}")
        
        # Check injuries for recent fixtures
        recent_fixtures = db.query(JackpotFixture).order_by(
            JackpotFixture.created_at.desc()
        ).limit(10).all()
        
        logger.info(f"\nChecking injuries for {len(recent_fixtures)} most recent fixtures:")
        for fixture in recent_fixtures:
            fixture_injuries = db.query(TeamInjuries).filter(
                TeamInjuries.fixture_id == fixture.id
            ).count()
            
            if fixture_injuries > 0:
                logger.info(f"  ✓ Fixture {fixture.id} ({fixture.home_team} vs {fixture.away_team}): {fixture_injuries} injury records")
            else:
                logger.info(f"  ✗ Fixture {fixture.id} ({fixture.home_team} vs {fixture.away_team}): No injuries")
        
        return total_injuries > 0
    except Exception as e:
        logger.error(f"Error checking injuries: {e}", exc_info=True)
        return False
    finally:
        db.close()

def test_injury_download_functionality():
    """Test if injury download function works"""
    logger.info("\n=== INJURY DOWNLOAD FUNCTIONALITY TEST ===")
    
    try:
        from app.services.ingestion.download_injuries_from_api import download_injuries_from_api_football
        from app.db.models import Jackpot
        
        db: Session = next(get_db())
        try:
            # Get a fixture that has a date (prefer fixtures with jackpot kickoff_date)
            fixture = db.query(JackpotFixture).join(
                Jackpot, JackpotFixture.jackpot_id == Jackpot.id
            ).filter(
                Jackpot.kickoff_date.isnot(None)
            ).order_by(
                JackpotFixture.created_at.desc()
            ).first()
            
            # Fallback: any fixture
            if not fixture:
                fixture = db.query(JackpotFixture).order_by(
                    JackpotFixture.created_at.desc()
                ).first()
            
            if not fixture:
                logger.warning("No fixtures found in database")
                return False
            
            # Check if fixture has a date
            has_date = False
            if fixture.jackpot and fixture.jackpot.kickoff_date:
                has_date = True
                logger.info(f"Fixture {fixture.id} has jackpot kickoff_date: {fixture.jackpot.kickoff_date}")
            else:
                logger.warning(f"Fixture {fixture.id} does not have kickoff_date - will use today's date as fallback")
            
            logger.info(f"Testing injury download for fixture {fixture.id} ({fixture.home_team} vs {fixture.away_team})")
            
            api_key = settings.API_FOOTBALL_KEY
            if not api_key or api_key.strip() == "":
                logger.warning("⚠ No API key - skipping download test")
                return False
            
            # Try to download injuries
            result = download_injuries_from_api_football(
                db=db,
                fixture_id=fixture.id,
                api_key=api_key
            )
            
            if result.get("success"):
                logger.info(f"✓ Injury download successful: {result}")
                return True
            elif result.get("skipped"):
                logger.info(f"ℹ Injury download skipped (expected): {result.get('error', 'Unknown reason')}")
                return True  # Skipped is OK (e.g., international matches)
            else:
                logger.warning(f"⚠ Injury download failed: {result.get('error', 'Unknown error')}")
                return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error testing injury download: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("INJURIES DOWNLOAD VERIFICATION TEST")
    logger.info("=" * 60)
    
    # Test 1: API Key Configuration
    has_api_key = test_api_key_configuration()
    
    # Test 2: Injuries in Database
    has_injuries = test_injuries_in_database()
    
    # Test 3: Injury Download Functionality (only if API key exists)
    if has_api_key:
        download_works = test_injury_download_functionality()
    else:
        download_works = False
        logger.warning("Skipping download test - no API key")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"API Key Configured: {'✓' if has_api_key else '✗'}")
    logger.info(f"Injuries in Database: {'✓' if has_injuries else '✗'}")
    logger.info(f"Download Functionality: {'✓' if download_works else '✗'}")
    
    if has_api_key and not has_injuries:
        logger.warning("\n⚠ API key is configured but no injuries found in database")
        logger.warning("  This could mean:")
        logger.warning("  1. Injuries haven't been downloaded yet")
        logger.warning("  2. API doesn't have injury data for your fixtures")
        logger.warning("  3. Download is failing silently")
    
    if not has_api_key:
        logger.warning("\n⚠ No API key configured - injuries will not be auto-downloaded")
        logger.warning("  Set API_FOOTBALL_KEY in .env file or environment variables")

if __name__ == "__main__":
    main()

