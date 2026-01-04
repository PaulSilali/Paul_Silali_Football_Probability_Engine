"""
Test script to verify matches and teams tables are being populated
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import Match, Team, League
from sqlalchemy import func
from app.services.data_ingestion import DataIngestionService, create_default_leagues
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_counts(db):
    """Check current counts in matches and teams tables"""
    matches_count = db.query(func.count(Match.id)).scalar()
    teams_count = db.query(func.count(Team.id)).scalar()
    leagues_count = db.query(func.count(League.id)).scalar()
    
    return {
        "matches": matches_count,
        "teams": teams_count,
        "leagues": leagues_count
    }


def test_populate_tables():
    """Test if tables can be populated"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("TESTING TABLE POPULATION")
        print("=" * 60)
        
        # Step 1: Check initial state
        print("\n[Step 1] Checking initial table counts...")
        initial_counts = check_table_counts(db)
        print(f"  Matches: {initial_counts['matches']}")
        print(f"  Teams: {initial_counts['teams']}")
        print(f"  Leagues: {initial_counts['leagues']}")
        
        # Step 2: Initialize leagues if needed
        if initial_counts['leagues'] == 0:
            print("\n[Step 2] Initializing leagues...")
            create_default_leagues(db)
            db.commit()
            print("  ✅ Leagues initialized")
        else:
            print("\n[Step 2] Leagues already exist, skipping initialization")
        
        # Step 3: Try to ingest a small amount of data
        print("\n[Step 3] Attempting to ingest test data...")
        print("  League: E0 (Premier League)")
        print("  Season: 2324 (2023-24)")
        
        service = DataIngestionService(
            db,
            enable_cleaning=settings.ENABLE_DATA_CLEANING
        )
        
        try:
            stats = service.ingest_from_football_data(
                league_code="E0",
                season="2324",  # Single season for testing
                save_csv=True
            )
            
            print(f"\n  ✅ Ingestion completed!")
            print(f"  Processed: {stats.get('processed', 0)}")
            print(f"  Inserted: {stats.get('inserted', 0)}")
            print(f"  Updated: {stats.get('updated', 0)}")
            print(f"  Skipped: {stats.get('skipped', 0)}")
            print(f"  Errors: {stats.get('errors', 0)}")
            
        except Exception as e:
            print(f"\n  ❌ Ingestion failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Check final state
        print("\n[Step 4] Checking final table counts...")
        final_counts = check_table_counts(db)
        print(f"  Matches: {final_counts['matches']} (was {initial_counts['matches']})")
        print(f"  Teams: {final_counts['teams']} (was {initial_counts['teams']})")
        print(f"  Leagues: {final_counts['leagues']} (was {initial_counts['leagues']})")
        
        # Step 5: Verify data was inserted
        print("\n[Step 5] Verifying data insertion...")
        matches_added = final_counts['matches'] - initial_counts['matches']
        teams_added = final_counts['teams'] - initial_counts['teams']
        
        if matches_added > 0:
            print(f"  ✅ SUCCESS: {matches_added} matches were inserted!")
        else:
            print(f"  ❌ FAILED: No matches were inserted")
            print(f"  ⚠️  REASON: All {stats.get('skipped', 0)} matches were skipped")
            print(f"  💡 SOLUTION: Teams need to be created first!")
            print(f"     The ingestion service requires teams to exist before inserting matches.")
            print(f"     Teams are NOT auto-created during ingestion.")
        
        if teams_added > 0:
            print(f"  ✅ SUCCESS: {teams_added} teams were created!")
        else:
            print(f"  ⚠️  WARNING: No new teams were created")
            print(f"  💡 This is the root cause - teams table is empty!")
            print(f"     Teams must be created before matches can be inserted.")
        
        # Step 6: Show sample data
        if final_counts['matches'] > 0:
            print("\n[Step 6] Sample match data:")
            sample_match = db.query(Match).first()
            if sample_match:
                print(f"  Match ID: {sample_match.id}")
                print(f"  Date: {sample_match.match_date}")
                print(f"  Home Team ID: {sample_match.home_team_id}")
                print(f"  Away Team ID: {sample_match.away_team_id}")
                print(f"  Score: {sample_match.home_goals}-{sample_match.away_goals}")
                print(f"  Result: {sample_match.result}")
                print(f"  Season: {sample_match.season}")
                print(f"  Source: {sample_match.source}")
        
        if final_counts['teams'] > 0:
            print("\n[Step 7] Sample team data:")
            sample_teams = db.query(Team).limit(5).all()
            for team in sample_teams:
                print(f"  {team.name} (ID: {team.id}, Canonical: {team.canonical_name})")
        
        # Final summary
        print("\n" + "=" * 60)
        if matches_added > 0:
            print("✅ TEST PASSED: Tables are being populated successfully!")
        else:
            print("❌ TEST FAILED: No data was inserted. Check errors above.")
        print("=" * 60)
        
        return matches_added > 0
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = test_populate_tables()
    sys.exit(0 if success else 1)

