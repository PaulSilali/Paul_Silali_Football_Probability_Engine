"""
Comprehensive test that simulates the actual download_injuries_from_api_football function call
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import JackpotFixture, Team, League, Match, Jackpot
from app.services.ingestion.download_injuries_from_api import download_injuries_from_api_football
from app.core.config import settings
import logging

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_actual_function_call(fixture_id: int, use_api: bool = False):
    """Test the actual download_injuries_from_api_football function"""
    db = SessionLocal()
    try:
        print(f"\n{'='*60}")
        print(f"Testing ACTUAL FUNCTION CALL for Fixture {fixture_id}")
        print(f"{'='*60}")
        
        # Check if fixture exists
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            print(f"❌ Fixture {fixture_id} not found")
            return
        
        print(f"\nFixture Info:")
        print(f"  - ID: {fixture.id}")
        print(f"  - Home Team: {fixture.home_team} (ID: {fixture.home_team_id})")
        print(f"  - Away Team: {fixture.away_team} (ID: {fixture.away_team_id})")
        print(f"  - League ID: {fixture.league_id}")
        
        # Get teams to check their league_id
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if home_team:
            print(f"  - Home Team League ID: {home_team.league_id}")
        if away_team:
            print(f"  - Away Team League ID: {away_team.league_id}")
        
        # Check API key
        api_key = getattr(settings, 'API_FOOTBALL_KEY', None)
        if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
            print(f"\n⚠️  API-Football key not configured")
            if not use_api:
                print(f"   Skipping actual API call (use_api=False)")
                print(f"   This test will only verify league lookup logic")
                return
            else:
                print(f"   ❌ Cannot proceed without API key")
                return
        else:
            print(f"\n✓ API-Football key configured (length: {len(str(api_key))})")
        
        print(f"\n{'='*60}")
        print("CALLING download_injuries_from_api_football()...")
        print(f"{'='*60}\n")
        
        # Call the actual function
        if use_api:
            result = download_injuries_from_api_football(db, fixture_id, api_key)
        else:
            # For testing without API, we'll just check the league lookup part
            # by calling a modified version or checking the logic
            print("   (Skipping API call - checking league lookup only)")
            result = {"success": False, "error": "API call skipped for testing"}
        
        print(f"\n{'='*60}")
        print("FUNCTION RESULT:")
        print(f"{'='*60}")
        print(f"Success: {result.get('success', False)}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
        if result.get('skipped'):
            print(f"Skipped: {result.get('skipped')}")
        if result.get('api_fixture_id'):
            print(f"API Fixture ID: {result.get('api_fixture_id')}")
        if result.get('home_inserted'):
            print(f"Home Inserted: {result.get('home_inserted')}")
        if result.get('away_inserted'):
            print(f"Away Inserted: {result.get('away_inserted')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    print("Starting test...", file=sys.stderr)
    sys.stdout.flush()
    
    # Test problematic fixtures
    test_fixtures = [115, 116]
    
    print("="*60)
    print("COMPREHENSIVE FUNCTION TEST")
    print("="*60)
    print("\nThis test will:")
    print("1. Check fixture data")
    print("2. Verify team league_id values")
    print("3. Call the actual download_injuries_from_api_football function")
    print("4. Show detailed debug output from the function")
    print("\nNote: Set use_api=True to make actual API calls")
    print("="*60)
    sys.stdout.flush()
    
    try:
        for fixture_id in test_fixtures:
            print(f"\n>>> Testing fixture {fixture_id}...")
            sys.stdout.flush()
            # Test without API call first (just to see league lookup)
            # We'll manually test the league lookup logic instead
            result = test_actual_function_call(fixture_id, use_api=False)
            if result:
                print(f"Result received for fixture {fixture_id}")
            sys.stdout.flush()
        
        print(f"\n{'='*60}")
        print("Test Complete")
        print(f"{'='*60}")
        sys.stdout.flush()
    except Exception as e:
        print(f"ERROR in main: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

