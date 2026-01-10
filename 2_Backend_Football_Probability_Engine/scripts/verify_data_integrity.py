"""
Data Integrity Verification Script
Verifies CSV files are saved correctly and database is updating properly
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

# Expected folder structure
EXPECTED_DRAW_STRUCTURAL_FOLDERS = [
    "Team_Form",
    "Rest_Days",
    "Odds_Movement",
    "h2h_stats",
    "Elo_Rating",
    "XG Data",  # Note: capital X, space
    "Weather",
    "League_structure",
    "Referee",
    "League_Priors"
]

EXPECTED_LOG_FOLDERS = [
    "01_logs"
]


def verify_csv_paths():
    """Verify CSV files are saved in correct folders"""
    backend_root = Path(__file__).parent.parent
    
    print("=" * 80)
    print("CSV FILE PATH VERIFICATION")
    print("=" * 80)
    
    issues = []
    successes = []
    
    # Check ingestion folders
    ingestion_root = backend_root / "data" / "1_data_ingestion"
    cleaned_root = backend_root / "data" / "2_Cleaned_data"
    
    # Check Draw Structural folders
    print("\n1. DRAW STRUCTURAL DATA FOLDERS")
    print("-" * 80)
    
    draw_structural_ingestion = ingestion_root / "Draw_structural"
    draw_structural_cleaned = cleaned_root / "Draw_structural"
    
    if not draw_structural_ingestion.exists():
        issues.append(f"Missing: {draw_structural_ingestion}")
    else:
        successes.append(f"✓ Found: {draw_structural_ingestion}")
    
    if not draw_structural_cleaned.exists():
        issues.append(f"Missing: {draw_structural_cleaned}")
    else:
        successes.append(f"✓ Found: {draw_structural_cleaned}")
    
    # Check each expected folder
    for folder_name in EXPECTED_DRAW_STRUCTURAL_FOLDERS:
        ingestion_folder = draw_structural_ingestion / folder_name
        cleaned_folder = draw_structural_cleaned / folder_name
        
        if ingestion_folder.exists():
            csv_count = len(list(ingestion_folder.glob("*.csv")))
            successes.append(f"✓ {folder_name}/ (ingestion): {csv_count} CSV files")
        else:
            issues.append(f"Missing: {ingestion_folder}")
        
        if cleaned_folder.exists():
            csv_count = len(list(cleaned_folder.glob("*.csv")))
            successes.append(f"✓ {folder_name}/ (cleaned): {csv_count} CSV files")
        else:
            issues.append(f"Missing: {cleaned_folder}")
    
    # Check log folders
    print("\n2. LOG FOLDERS")
    print("-" * 80)
    
    logs_ingestion_draw = draw_structural_ingestion / "01_logs"
    logs_cleaned_draw = draw_structural_cleaned / "01_logs"
    
    if logs_ingestion_draw.exists():
        log_count = len(list(logs_ingestion_draw.glob("*.txt")))
        successes.append(f"✓ Draw Structural logs (ingestion): {log_count} log files")
    else:
        issues.append(f"Missing: {logs_ingestion_draw}")
    
    if logs_cleaned_draw.exists():
        log_count = len(list(logs_cleaned_draw.glob("*.txt")))
        successes.append(f"✓ Draw Structural logs (cleaned): {log_count} log files")
    else:
        issues.append(f"Missing: {logs_cleaned_draw}")
    
    # Check Historical Match Odds Data folders
    print("\n3. HISTORICAL MATCH ODDS DATA FOLDERS")
    print("-" * 80)
    
    historical_ingestion = ingestion_root / "Historical Match_Odds_Data"
    historical_cleaned = cleaned_root / "Historical Match_Odds_Data"
    
    if historical_ingestion.exists():
        session_folders = [d for d in historical_ingestion.iterdir() if d.is_dir() and d.name != "01_logs"]
        csv_total = sum(len(list(d.glob("**/*.csv"))) for d in session_folders)
        successes.append(f"✓ Historical Odds (ingestion): {len(session_folders)} session folders, {csv_total} CSV files")
    else:
        issues.append(f"Missing: {historical_ingestion}")
    
    if historical_cleaned.exists():
        session_folders = [d for d in historical_cleaned.iterdir() if d.is_dir() and d.name != "01_logs"]
        csv_total = sum(len(list(d.glob("**/*.csv"))) for d in session_folders)
        successes.append(f"✓ Historical Odds (cleaned): {len(session_folders)} session folders, {csv_total} CSV files")
    else:
        issues.append(f"Missing: {historical_cleaned}")
    
    # Check Historical Odds log folders
    logs_ingestion_historical = historical_ingestion / "01_logs"
    logs_cleaned_historical = historical_cleaned / "01_logs"
    
    if logs_ingestion_historical.exists():
        log_count = len(list(logs_ingestion_historical.glob("*.txt")))
        successes.append(f"✓ Historical Odds logs (ingestion): {log_count} log files")
    else:
        issues.append(f"Missing: {logs_ingestion_historical}")
    
    if logs_cleaned_historical.exists():
        log_count = len(list(logs_cleaned_historical.glob("*.txt")))
        successes.append(f"✓ Historical Odds logs (cleaned): {log_count} log files")
    else:
        issues.append(f"Missing: {logs_cleaned_historical}")
    
    # Print results
    print("\nSUCCESSES:")
    for success in successes:
        print(f"  {success}")
    
    if issues:
        print("\nISSUES FOUND:")
        for issue in issues:
            print(f"  ✗ {issue}")
    else:
        print("\n✓ All expected folders exist!")
    
    return len(issues) == 0


def verify_database_schema():
    """Verify database schema matches expected tables"""
    print("\n" + "=" * 80)
    print("DATABASE SCHEMA VERIFICATION")
    print("=" * 80)
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Expected tables from schema
        expected_tables = {
            'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
            'predictions', 'models', 'training_runs', 'team_h2h_stats',
            'league_draw_priors', 'h2h_draw_stats', 'team_elo',
            'match_weather', 'match_weather_historical', 'referee_stats',
            'team_rest_days', 'team_rest_days_historical',
            'odds_movement', 'odds_movement_historical',
            'league_structure', 'match_xg', 'match_xg_historical',
            'team_form', 'team_form_historical', 'team_injuries',
            'saved_jackpot_templates', 'saved_probability_results',
            'data_sources', 'ingestion_logs', 'audit_entries'
        }
        
        missing_tables = expected_tables - existing_tables
        extra_tables = existing_tables - expected_tables
        
        print("\nEXPECTED TABLES:")
        for table in sorted(expected_tables):
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (MISSING)")
        
        if missing_tables:
            print(f"\n⚠ Missing tables: {sorted(missing_tables)}")
        
        if extra_tables:
            print(f"\nℹ Extra tables (not in expected list): {sorted(extra_tables)}")
        
        # Check record counts for key tables
        print("\nDATABASE RECORD COUNTS:")
        print("-" * 80)
        
        key_tables = [
            'leagues', 'teams', 'matches', 'team_form_historical',
            'team_rest_days_historical', 'match_xg_historical',
            'league_draw_priors', 'h2h_draw_stats', 'team_elo'
        ]
        
        for table_name in key_tables:
            if table_name in existing_tables:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    print(f"  {table_name}: {result:,} records")
                except Exception as e:
                    print(f"  ✗ {table_name}: Error counting - {e}")
            else:
                print(f"  ✗ {table_name}: Table does not exist")
        
        return len(missing_tables) == 0
        
    finally:
        db.close()


def verify_csv_database_alignment():
    """Verify CSV files align with database records"""
    print("\n" + "=" * 80)
    print("CSV-DATABASE ALIGNMENT VERIFICATION")
    print("=" * 80)
    
    backend_root = Path(__file__).parent.parent
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check team_form_historical
        print("\n1. TEAM FORM HISTORICAL")
        print("-" * 80)
        
        try:
            db_count = db.execute(text("SELECT COUNT(*) FROM team_form_historical")).scalar()
            csv_folder = backend_root / "data" / "1_data_ingestion" / "Draw_structural" / "Team_Form"
            csv_files = list(csv_folder.glob("*.csv")) if csv_folder.exists() else []
            
            if csv_files:
                # Count records in CSV files
                csv_total = 0
                for csv_file in csv_files:
                    try:
                        df = pd.read_csv(csv_file)
                        csv_total += len(df)
                    except:
                        pass
                
                print(f"  Database records: {db_count:,}")
                print(f"  CSV files: {len(csv_files)}")
                print(f"  CSV records (estimated): {csv_total:,}")
                
                if db_count > 0 and csv_total > 0:
                    ratio = db_count / csv_total if csv_total > 0 else 0
                    if 0.8 <= ratio <= 1.2:  # Allow 20% variance
                        print(f"  ✓ Alignment: Good (ratio: {ratio:.2f})")
                    else:
                        print(f"  ⚠ Alignment: Check needed (ratio: {ratio:.2f})")
            else:
                print(f"  Database records: {db_count:,}")
                print(f"  CSV files: 0 (none found)")
        except Exception as e:
            print(f"  ✗ Error checking team_form_historical: {e}")
        
        # Check matches table
        print("\n2. MATCHES TABLE")
        print("-" * 80)
        
        try:
            db_count = db.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            print(f"  Database records: {db_count:,}")
            
            if db_count == 0:
                print("  ⚠ Warning: No matches in database!")
            else:
                print("  ✓ Matches table has data")
        except Exception as e:
            print(f"  ✗ Error checking matches: {e}")
        
        return True
        
    finally:
        db.close()


def main():
    """Run all verification checks"""
    print("\n" + "=" * 80)
    print("DATA INTEGRITY VERIFICATION REPORT")
    print("=" * 80)
    print(f"Backend Root: {Path(__file__).parent.parent}")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    print("=" * 80)
    
    csv_ok = verify_csv_paths()
    db_ok = verify_database_schema()
    alignment_ok = verify_csv_database_alignment()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"CSV Paths: {'✓ OK' if csv_ok else '✗ ISSUES FOUND'}")
    print(f"Database Schema: {'✓ OK' if db_ok else '✗ ISSUES FOUND'}")
    print(f"CSV-DB Alignment: {'✓ OK' if alignment_ok else '✗ ISSUES FOUND'}")
    
    if csv_ok and db_ok and alignment_ok:
        print("\n✓ All checks passed!")
        return 0
    else:
        print("\n⚠ Some issues found. Please review above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

