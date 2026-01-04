"""
Download 7 Years of Data from football-data.co.uk
Downloads historical match data for all leagues for the last 7 years
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use app's database connection
from app.db.session import SessionLocal
from app.services.data_ingestion import DataIngestionService, create_default_leagues

# All leagues available from football-data.co.uk
ALL_LEAGUES = [
    # England
    "E0",  # Premier League
    "E1",  # Championship
    "E2",  # League 1
    "E3",  # League 2
    # Spain
    "SP1",  # La Liga
    "SP2",  # La Liga 2
    # Italy
    "I1",  # Serie A
    "I2",  # Serie B
    # France
    "F1",  # Ligue 1
    "F2",  # Ligue 2
    # Germany
    "D1",  # Bundesliga
    "D2",  # 2. Bundesliga
    # Netherlands
    "N1",  # Eredivisie
    # Belgium
    "B1",  # Pro League
    # Portugal
    "P1",  # Primeira Liga
    # Turkey
    "T1",  # Super Lig
    # Greece
    "G1",  # Super League
    # Scotland
    "SC0",  # Premiership
    "SC1",  # Championship
    "SC2",  # League 1
    "SC3",  # League 2
]

def download_7_years_data():
    """Download 7 years of data for all leagues from football-data.co.uk"""
    print("="*80)
    print("DOWNLOADING 7 YEARS OF DATA FROM FOOTBALL-DATA.CO.UK")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total leagues: {len(ALL_LEAGUES)}")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Ensure leagues exist in database
        print("\n[INFO] Ensuring leagues exist in database...")
        create_default_leagues(db)
        db.commit()
        print("[OK] Leagues initialized")
        
        # Initialize ingestion service with cleaning enabled
        service = DataIngestionService(db, enable_cleaning=True)
        
        # Create download session folder
        download_date = datetime.now().strftime("%Y-%m-%d")
        download_session_folder = f"{download_date}_Seasons_7_Leagues_{len(ALL_LEAGUES)}"
        
        print(f"\n[INFO] Download session folder: {download_session_folder}")
        print(f"[INFO] Season range: Last 7 years (7 seasons per league)")
        print(f"[INFO] Data will be saved to: data/1_data_ingestion/Historical Match_Odds_Data/{download_session_folder}/")
        print("\n" + "="*80)
        
        total_stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "leagues_processed": 0,
            "leagues_failed": []
        }
        
        # Process each league
        for idx, league_code in enumerate(ALL_LEAGUES, 1):
            print(f"\n[{idx}/{len(ALL_LEAGUES)}] Processing league: {league_code}")
            print("-" * 80)
            
            try:
                # Ingest last 7 years of data
                stats = service.ingest_from_football_data(
                    league_code=league_code,
                    season="last7",  # Last 7 years
                    save_csv=True,
                    download_session_folder=download_session_folder
                )
                
                # Accumulate stats
                total_stats["processed"] += stats.get("processed", 0)
                total_stats["inserted"] += stats.get("inserted", 0)
                total_stats["updated"] += stats.get("updated", 0)
                total_stats["skipped"] += stats.get("skipped", 0)
                total_stats["errors"] += stats.get("errors", 0)
                total_stats["leagues_processed"] += 1
                
                print(f"[OK] {league_code}: {stats.get('inserted', 0)} matches inserted, "
                      f"{stats.get('updated', 0)} updated, {stats.get('skipped', 0)} skipped")
                
            except Exception as e:
                total_stats["leagues_failed"].append(league_code)
                total_stats["errors"] += 1
                print(f"[ERROR] {league_code}: Failed - {str(e)[:200]}")
            
            # Brief pause between leagues to avoid rate limiting
            if idx < len(ALL_LEAGUES):
                time.sleep(2)
        
        # Print summary
        print("\n" + "="*80)
        print("DOWNLOAD SUMMARY")
        print("="*80)
        print(f"Leagues processed: {total_stats['leagues_processed']}/{len(ALL_LEAGUES)}")
        print(f"Total matches processed: {total_stats['processed']:,}")
        print(f"Total matches inserted: {total_stats['inserted']:,}")
        print(f"Total matches updated: {total_stats['updated']:,}")
        print(f"Total matches skipped: {total_stats['skipped']:,}")
        print(f"Total errors: {total_stats['errors']}")
        
        if total_stats["leagues_failed"]:
            print(f"\n[WARN] Failed leagues: {', '.join(total_stats['leagues_failed'])}")
        else:
            print("\n[OK] All leagues processed successfully!")
        
        # Check database
        matches_count = db.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        teams_count = db.execute(text("SELECT COUNT(*) FROM teams")).scalar()
        leagues_count = db.execute(text("SELECT COUNT(*) FROM leagues")).scalar()
        
        print("\n" + "="*80)
        print("DATABASE STATUS")
        print("="*80)
        print(f"Matches in database: {matches_count:,}")
        print(f"Teams in database: {teams_count:,}")
        print(f"Leagues in database: {leagues_count:,}")
        print("="*80)
        
        print(f"\n[OK] Download completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return total_stats
        
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    download_7_years_data()

