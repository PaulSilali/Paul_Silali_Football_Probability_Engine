"""
Test script to diagnose league lookup issues in injury download
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import JackpotFixture, Team, League, Match, Jackpot
from datetime import date, timedelta

def test_fixture_league_lookup(fixture_id: int):
    """Test league lookup for a specific fixture"""
    db = SessionLocal()
    try:
        print(f"\n{'='*60}")
        print(f"Testing Fixture {fixture_id}")
        print(f"{'='*60}")
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            print(f"❌ Fixture {fixture_id} not found")
            return
        
        print(f"\n1. Fixture Data:")
        print(f"   - Fixture ID: {fixture.id}")
        print(f"   - Home Team ID: {fixture.home_team_id}")
        print(f"   - Away Team ID: {fixture.away_team_id}")
        print(f"   - League ID: {fixture.league_id}")
        print(f"   - Home Team Name: {fixture.home_team}")
        print(f"   - Away Team Name: {fixture.away_team}")
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first() if fixture.home_team_id else None
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first() if fixture.away_team_id else None
        
        print(f"\n2. Team Data:")
        if home_team:
            print(f"   - Home Team: {home_team.name} (ID: {home_team.id}, League ID: {home_team.league_id})")
        else:
            print(f"   - Home Team: NOT FOUND (ID: {fixture.home_team_id})")
        
        if away_team:
            print(f"   - Away Team: {away_team.name} (ID: {away_team.id}, League ID: {away_team.league_id})")
        else:
            print(f"   - Away Team: NOT FOUND (ID: {fixture.away_team_id})")
        
        # Get jackpot
        jackpot = None
        if fixture.jackpot_id:
            jackpot = db.query(Jackpot).filter(Jackpot.id == fixture.jackpot_id).first()
        
        print(f"\n3. Jackpot Data:")
        if jackpot:
            print(f"   - Jackpot ID: {jackpot.id}")
            print(f"   - Kickoff Date: {jackpot.kickoff_date}")
        else:
            print(f"   - Jackpot: NOT FOUND (ID: {fixture.jackpot_id})")
        
        # Test league lookup logic
        print(f"\n4. League Lookup Test:")
        
        # Method 1: fixture.league_id
        league = None
        if fixture.league_id:
            league = db.query(League).filter(League.id == fixture.league_id).first()
            if league:
                print(f"   ✓ Method 1 (fixture.league_id): FOUND - {league.code} ({league.name})")
            else:
                print(f"   ✗ Method 1 (fixture.league_id): League ID {fixture.league_id} not found in leagues table")
        else:
            print(f"   ✗ Method 1 (fixture.league_id): fixture.league_id is None")
        
        # Method 2: home_team.league_id
        if not league and home_team and home_team.league_id:
            league = db.query(League).filter(League.id == home_team.league_id).first()
            if league:
                print(f"   ✓ Method 2 (home_team.league_id): FOUND - {league.code} ({league.name})")
            else:
                print(f"   ✗ Method 2 (home_team.league_id): League ID {home_team.league_id} not found in leagues table")
        elif not league:
            if home_team:
                print(f"   ✗ Method 2 (home_team.league_id): home_team.league_id is None")
            else:
                print(f"   ✗ Method 2 (home_team.league_id): home_team is None")
        
        # Method 3: away_team.league_id
        if not league and away_team and away_team.league_id:
            league = db.query(League).filter(League.id == away_team.league_id).first()
            if league:
                print(f"   ✓ Method 3 (away_team.league_id): FOUND - {league.code} ({league.name})")
            else:
                print(f"   ✗ Method 3 (away_team.league_id): League ID {away_team.league_id} not found in leagues table")
        elif not league:
            if away_team:
                print(f"   ✗ Method 3 (away_team.league_id): away_team.league_id is None")
            else:
                print(f"   ✗ Method 3 (away_team.league_id): away_team is None")
        
        # Method 4: Find from matches table
        if not league and fixture.home_team_id and fixture.away_team_id:
            # Try to find any match between these teams (last 2 years)
            two_years_ago = date.today() - timedelta(days=730)
            match = db.query(Match).filter(
                ((Match.home_team_id == fixture.home_team_id) & (Match.away_team_id == fixture.away_team_id)) |
                ((Match.home_team_id == fixture.away_team_id) & (Match.away_team_id == fixture.home_team_id))
            ).filter(
                Match.match_date >= two_years_ago
            ).order_by(Match.match_date.desc()).first()
            
            if match:
                print(f"   ✓ Method 4 (matches table): Found match on {match.match_date}")
                if match.league_id:
                    league = db.query(League).filter(League.id == match.league_id).first()
                    if league:
                        print(f"      → League: {league.code} ({league.name})")
                    else:
                        print(f"      ✗ Match has league_id={match.league_id} but league not found")
                else:
                    print(f"      ✗ Match has no league_id")
            else:
                print(f"   ✗ Method 4 (matches table): No matches found between these teams (last 2 years)")
        elif not league:
            print(f"   ✗ Method 4 (matches table): Cannot search - missing team IDs")
        
        # Final result
        print(f"\n5. Result:")
        if league:
            print(f"   ✅ LEAGUE FOUND: {league.code} ({league.name})")
        else:
            print(f"   ❌ LEAGUE NOT FOUND - All methods failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Test problematic fixtures
    test_fixtures = [105, 106, 115, 116, 117]
    
    for fixture_id in test_fixtures:
        test_fixture_league_lookup(fixture_id)
    
    print(f"\n{'='*60}")
    print("Test Complete")
    print(f"{'='*60}")

