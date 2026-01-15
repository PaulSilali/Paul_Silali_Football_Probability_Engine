"""
Simple test to verify league lookup logic with debug logging
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import JackpotFixture, Team, League, Match
from datetime import date, timedelta
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_league_lookup_logic(fixture_id: int):
    """Test the league lookup logic exactly as it appears in the function"""
    db = SessionLocal()
    try:
        print(f"\n{'='*60}")
        print(f"Testing League Lookup Logic for Fixture {fixture_id}")
        print(f"{'='*60}\n")
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            print(f"❌ Fixture {fixture_id} not found")
            return None
        
        print(f"Fixture {fixture_id}:")
        print(f"  - Home Team ID: {fixture.home_team_id}")
        print(f"  - Away Team ID: {fixture.away_team_id}")
        print(f"  - League ID: {fixture.league_id}")
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            print(f"❌ Teams not found: home={home_team is not None}, away={away_team is not None}")
            return None
        
        print(f"\nTeams:")
        print(f"  - Home: {home_team.name} (ID: {home_team.id}, League ID: {home_team.league_id})")
        print(f"  - Away: {away_team.name} (ID: {away_team.id}, League ID: {away_team.league_id})")
        
        # Simulate the exact league lookup logic from the function
        print(f"\n{'='*60}")
        print("EXECUTING LEAGUE LOOKUP LOGIC:")
        print(f"{'='*60}\n")
        
        logger.debug(f"Fixture {fixture_id}: Starting league lookup - fixture.league_id={fixture.league_id}, home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}")
        league = None
        
        # Method 1: Try fixture.league_id
        if fixture.league_id:
            league = db.query(League).filter(League.id == fixture.league_id).first()
            if league:
                logger.debug(f"Fixture {fixture_id}: ✓ Method 1 (fixture.league_id): Found league {league.code} (ID: {league.id})")
                print(f"✓ Method 1 (fixture.league_id): Found league {league.code} (ID: {league.id})")
            else:
                logger.debug(f"Fixture {fixture_id}: ✗ Method 1 (fixture.league_id): League ID {fixture.league_id} not found in leagues table")
                print(f"✗ Method 1 (fixture.league_id): League ID {fixture.league_id} not found")
        else:
            logger.debug(f"Fixture {fixture_id}: ✗ Method 1 (fixture.league_id): fixture.league_id is None")
            print(f"✗ Method 1 (fixture.league_id): fixture.league_id is None")
        
        # Method 2: Try home team's league
        if not league:
            if home_team:
                logger.debug(f"Fixture {fixture_id}: Checking home team - ID: {home_team.id}, league_id: {home_team.league_id}")
                print(f"  Checking home team - ID: {home_team.id}, league_id: {home_team.league_id}")
                if home_team.league_id:
                    league = db.query(League).filter(League.id == home_team.league_id).first()
                    if league:
                        logger.debug(f"Fixture {fixture_id}: ✓ Method 2 (home_team.league_id): Found league {league.code} (ID: {league.id})")
                        print(f"✓ Method 2 (home_team.league_id): Found league {league.code} (ID: {league.id})")
                    else:
                        logger.debug(f"Fixture {fixture_id}: ✗ Method 2 (home_team.league_id): League ID {home_team.league_id} not found in leagues table")
                        print(f"✗ Method 2 (home_team.league_id): League ID {home_team.league_id} not found")
                else:
                    logger.debug(f"Fixture {fixture_id}: ✗ Method 2 (home_team.league_id): home_team.league_id is None")
                    print(f"✗ Method 2 (home_team.league_id): home_team.league_id is None")
            else:
                logger.debug(f"Fixture {fixture_id}: ✗ Method 2 (home_team.league_id): home_team is None")
                print(f"✗ Method 2 (home_team.league_id): home_team is None")
        
        # Method 3: Try away team's league
        if not league:
            if away_team:
                logger.debug(f"Fixture {fixture_id}: Checking away team - ID: {away_team.id}, league_id: {away_team.league_id}")
                print(f"  Checking away team - ID: {away_team.id}, league_id: {away_team.league_id}")
                if away_team.league_id:
                    league = db.query(League).filter(League.id == away_team.league_id).first()
                    if league:
                        logger.debug(f"Fixture {fixture_id}: ✓ Method 3 (away_team.league_id): Found league {league.code} (ID: {league.id})")
                        print(f"✓ Method 3 (away_team.league_id): Found league {league.code} (ID: {league.id})")
                    else:
                        logger.debug(f"Fixture {fixture_id}: ✗ Method 3 (away_team.league_id): League ID {away_team.league_id} not found in leagues table")
                        print(f"✗ Method 3 (away_team.league_id): League ID {away_team.league_id} not found")
                else:
                    logger.debug(f"Fixture {fixture_id}: ✗ Method 3 (away_team.league_id): away_team.league_id is None")
                    print(f"✗ Method 3 (away_team.league_id): away_team.league_id is None")
            else:
                logger.debug(f"Fixture {fixture_id}: ✗ Method 3 (away_team.league_id): away_team is None")
                print(f"✗ Method 3 (away_team.league_id): away_team is None")
        
        # Final result
        print(f"\n{'='*60}")
        if league:
            print(f"✅ RESULT: League FOUND - {league.code} ({league.name}, ID: {league.id})")
            logger.info(f"Fixture {fixture_id}: League found - {league.code}")
        else:
            print(f"❌ RESULT: League NOT FOUND")
            logger.warning(f"Fixture {fixture_id}: League not found")
        print(f"{'='*60}\n")
        
        return league
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Error testing fixture {fixture_id}: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("LEAGUE LOOKUP LOGIC TEST")
    print("="*60)
    print("\nThis test simulates the exact league lookup logic")
    print("from download_injuries_from_api_football()")
    print("="*60)
    
    test_fixtures = [115, 116]
    
    for fixture_id in test_fixtures:
        test_league_lookup_logic(fixture_id)
    
    print("="*60)
    print("Test Complete")
    print("="*60)

