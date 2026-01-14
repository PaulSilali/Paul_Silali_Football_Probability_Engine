"""
Test script to check data downloads for 12_01_2026
Checks if necessary data has been downloaded for probability calculations
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import (
    MatchWeather, TeamRestDays, TeamInjuries, OddsMovement,
    TeamForm, Team, Match, League
)

def test_data_downloads():
    """Test if data has been downloaded for 12_01_2026"""
    db = SessionLocal()
    
    try:
        today = date(2026, 1, 12)
        yesterday = today - timedelta(days=1)
        
        print("=" * 80)
        print(f"DATA DOWNLOAD TEST FOR {today}")
        print("=" * 80)
        print()
        
        # 1. Check Team Injuries Table
        print("1. TEAM INJURIES TABLE")
        print("-" * 80)
        total_injuries = db.query(TeamInjuries).count()
        print(f"Total records: {total_injuries}")
        
        if total_injuries == 0:
            print("⚠️  WARNING: Team injuries table is EMPTY")
        else:
            # Check recent injuries
            recent_injuries = db.query(TeamInjuries).filter(
                TeamInjuries.created_at >= datetime.combine(yesterday, datetime.min.time())
            ).count()
            print(f"Records from {yesterday} or later: {recent_injuries}")
            
            # Check oldest and newest
            oldest = db.query(func.min(TeamInjuries.created_at)).scalar()
            newest = db.query(func.max(TeamInjuries.created_at)).scalar()
            print(f"Oldest record: {oldest}")
            print(f"Newest record: {newest}")
        
        print()
        
        # 2. Check Match Weather
        print("2. MATCH WEATHER TABLE")
        print("-" * 80)
        total_weather = db.query(MatchWeather).count()
        print(f"Total records: {total_weather}")
        
        if total_weather > 0:
            # Check recent weather
            recent_weather = db.query(MatchWeather).filter(
                MatchWeather.created_at >= datetime.combine(yesterday, datetime.min.time())
            ).count()
            print(f"Records from {yesterday} or later: {recent_weather}")
            
            # Check oldest and newest
            oldest = db.query(func.min(MatchWeather.created_at)).scalar()
            newest = db.query(func.max(MatchWeather.created_at)).scalar()
            print(f"Oldest record: {oldest}")
            print(f"Newest record: {newest}")
            
            # Check fixtures from today/yesterday
            fixtures_today = db.query(MatchWeather).join(Match, MatchWeather.fixture_id == Match.id).filter(
                or_(
                    Match.match_date == today,
                    Match.match_date == yesterday
                )
            ).count()
            print(f"Weather data for fixtures on {yesterday} or {today}: {fixtures_today}")
        else:
            print("⚠️  WARNING: Match weather table is EMPTY")
        
        print()
        
        # 3. Check Team Rest Days
        print("3. TEAM REST DAYS TABLE")
        print("-" * 80)
        total_rest_days = db.query(TeamRestDays).count()
        print(f"Total records: {total_rest_days}")
        
        if total_rest_days > 0:
            # Check recent rest days
            recent_rest_days = db.query(TeamRestDays).filter(
                TeamRestDays.created_at >= datetime.combine(yesterday, datetime.min.time())
            ).count()
            print(f"Records from {yesterday} or later: {recent_rest_days}")
            
            # Check oldest and newest
            oldest = db.query(func.min(TeamRestDays.created_at)).scalar()
            newest = db.query(func.max(TeamRestDays.created_at)).scalar()
            print(f"Oldest record: {oldest}")
            print(f"Newest record: {newest}")
            
            # Check fixtures from today/yesterday
            fixtures_today = db.query(TeamRestDays).join(Match, TeamRestDays.fixture_id == Match.id).filter(
                or_(
                    Match.match_date == today,
                    Match.match_date == yesterday
                )
            ).count()
            print(f"Rest days for fixtures on {yesterday} or {today}: {fixtures_today}")
        else:
            print("⚠️  WARNING: Team rest days table is EMPTY")
        
        print()
        
        # 4. Check Odds Movement
        print("4. ODDS MOVEMENT TABLE")
        print("-" * 80)
        total_odds = db.query(OddsMovement).count()
        print(f"Total records: {total_odds}")
        
        if total_odds > 0:
            # Check recent odds
            recent_odds = db.query(OddsMovement).filter(
                OddsMovement.created_at >= datetime.combine(yesterday, datetime.min.time())
            ).count()
            print(f"Records from {yesterday} or later: {recent_odds}")
            
            # Check oldest and newest
            oldest = db.query(func.min(OddsMovement.created_at)).scalar()
            newest = db.query(func.max(OddsMovement.created_at)).scalar()
            print(f"Oldest record: {oldest}")
            print(f"Newest record: {newest}")
        else:
            print("⚠️  WARNING: Odds movement table is EMPTY")
        
        print()
        
        # 5. Check Team Form
        print("5. TEAM FORM TABLE")
        print("-" * 80)
        total_form = db.query(TeamForm).count()
        print(f"Total records: {total_form}")
        
        if total_form > 0:
            # Check recent form
            recent_form = db.query(TeamForm).filter(
                TeamForm.calculated_at >= datetime.combine(yesterday, datetime.min.time())
            ).count()
            print(f"Records calculated from {yesterday} or later: {recent_form}")
            
            # Check oldest and newest
            oldest = db.query(func.min(TeamForm.calculated_at)).scalar()
            newest = db.query(func.max(TeamForm.calculated_at)).scalar()
            print(f"Oldest record: {oldest}")
            print(f"Newest record: {newest}")
        else:
            print("⚠️  WARNING: Team form table is EMPTY")
        
        print()
        
        # 6. Check Matches (for fixtures on 12_01_2026)
        print("6. MATCHES TABLE (Fixtures on 12_01_2026)")
        print("-" * 80)
        matches_today = db.query(Match).filter(
            or_(
                Match.match_date == today,
                Match.match_date == yesterday
            )
        ).count()
        print(f"Matches scheduled for {yesterday} or {today}: {matches_today}")
        
        if matches_today > 0:
            # Check which matches have weather data
            matches_with_weather = db.query(Match).join(
                MatchWeather, Match.id == MatchWeather.fixture_id
            ).filter(
                or_(
                    Match.match_date == today,
                    Match.match_date == yesterday
                )
            ).count()
            print(f"Matches with weather data: {matches_with_weather} / {matches_today}")
            
            # Check which matches have rest days
            matches_with_rest = db.query(Match).join(
                TeamRestDays, Match.id == TeamRestDays.fixture_id
            ).filter(
                or_(
                    Match.match_date == today,
                    Match.match_date == yesterday
                )
            ).distinct().count()
            print(f"Matches with rest days: {matches_with_rest} / {matches_today}")
            
            # Check which matches have injuries
            matches_with_injuries = db.query(Match).join(
                TeamInjuries, Match.id == TeamInjuries.fixture_id
            ).filter(
                or_(
                    Match.match_date == today,
                    Match.match_date == yesterday
                )
            ).distinct().count()
            print(f"Matches with injuries: {matches_with_injuries} / {matches_today}")
        
        print()
        
        # 7. Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Team Injuries: {'✓ Has data' if total_injuries > 0 else '✗ EMPTY'}")
        print(f"Match Weather: {'✓ Has data' if total_weather > 0 else '✗ EMPTY'}")
        print(f"Team Rest Days: {'✓ Has data' if total_rest_days > 0 else '✗ EMPTY'}")
        print(f"Odds Movement: {'✓ Has data' if total_odds > 0 else '✗ EMPTY'}")
        print(f"Team Form: {'✓ Has data' if total_form > 0 else '✗ EMPTY'}")
        print()
        
        # Check if data is recent (downloaded today/yesterday)
        print("RECENT DATA CHECK (downloaded on 12_01/11_2026):")
        print(f"Recent Injuries: {recent_injuries if total_injuries > 0 else 0}")
        print(f"Recent Weather: {recent_weather if total_weather > 0 else 0}")
        print(f"Recent Rest Days: {recent_rest_days if total_rest_days > 0 else 0}")
        print(f"Recent Odds: {recent_odds if total_odds > 0 else 0}")
        print(f"Recent Form: {recent_form if total_form > 0 else 0}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_data_downloads()

