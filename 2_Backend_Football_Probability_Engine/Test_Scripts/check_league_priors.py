"""Check league priors in database"""
import sys
import os
from pathlib import Path

# Get the script's directory and add it to path
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

# Change to script directory to ensure .env file is found
os.chdir(script_dir)

# Load environment variables from .env file if it exists
# pydantic_settings should load it automatically, but we ensure it's found
env_file = script_dir / '.env'
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # dotenv not installed, but pydantic_settings should handle it
        pass

from app.db.session import SessionLocal
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

try:
    db = SessionLocal()
except Exception as e:
    print(f'\n❌ Error connecting to database: {e}')
    print('\nPlease ensure:')
    print('  1. PostgreSQL is running')
    print('  2. .env file exists with correct database credentials')
    print('  3. Database credentials are correct (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)')
    sys.exit(1)

try:
    # Count total records
    try:
        count = db.execute(text('SELECT COUNT(*) FROM league_draw_priors')).scalar()
    except Exception as e:
        print(f'\n❌ Error querying database: {e}')
        print('This might indicate:')
        print('  - The league_draw_priors table does not exist')
        print('  - Database permissions issue')
        print('  - SQL syntax error')
        raise
    
    print(f'\n=== League Draw Priors Database Check ===')
    print(f'Total league priors records: {count}')
    
    if count > 0:
        # Get all records with league codes
        priors = db.execute(text("""
            SELECT l.code, ldp.season, ldp.sample_size, ldp.draw_rate, ldp.updated_at 
            FROM league_draw_priors ldp 
            JOIN leagues l ON ldp.league_id = l.id 
            ORDER BY ldp.updated_at DESC
        """)).fetchall()
        
        print(f'\nAll league priors ({len(priors)} total):')
        print('-' * 100)
        print(f'{"League":<8} | {"Season":<12} | {"Matches":<8} | {"Draw Rate":<12} | {"Updated At"}')
        print('-' * 100)
        for p in priors:
            print(f'{p[0]:<8} | {p[1]:<12} | {p[2]:<8} | {p[3]:.6f}      | {p[4]}')
        
        # Count by league
        league_counts = db.execute(text("""
            SELECT l.code, COUNT(*) as count
            FROM league_draw_priors ldp 
            JOIN leagues l ON ldp.league_id = l.id 
            GROUP BY l.code
            ORDER BY count DESC
        """)).fetchall()
        
        print(f'\nLeague priors count by league:')
        print('-' * 40)
        for lc in league_counts:
            print(f'  {lc[0]:<8} : {lc[1]} record(s)')
        
        # Check which leagues have matches but no priors
        print(f'\n=== Leagues with matches but NO priors ===')
        leagues_with_matches = db.execute(text("""
            SELECT DISTINCT l.code, l.name, COUNT(DISTINCT m.season) as seasons_count, COUNT(*) as match_count
            FROM leagues l
            JOIN matches m ON l.id = m.league_id
            WHERE l.id NOT IN (
                SELECT DISTINCT league_id FROM league_draw_priors
            )
            GROUP BY l.code, l.name
            ORDER BY match_count DESC
            LIMIT 20
        """)).fetchall()
        
        if leagues_with_matches:
            print(f'Found {len(leagues_with_matches)} leagues with matches but no priors:')
            print('-' * 80)
            print(f'{"League":<8} | {"Name":<30} | {"Seasons":<8} | {"Matches":<8}')
            print('-' * 80)
            for l in leagues_with_matches:
                print(f'{l[0]:<8} | {l[1][:30]:<30} | {l[2]:<8} | {l[3]:<8}')
        else:
            print('All leagues with matches have priors.')
        
        # Check total leagues vs leagues with priors
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        leagues_with_priors = db.execute(text('SELECT COUNT(DISTINCT league_id) FROM league_draw_priors')).scalar()
        print(f'\n=== Summary ===')
        print(f'Total leagues in database: {total_leagues}')
        print(f'Leagues with priors: {leagues_with_priors}')
        print(f'Leagues without priors: {total_leagues - leagues_with_priors}')
        
    else:
        print('\nNo league priors found in database.')
        
        # Check if there are any leagues
        total_leagues = db.execute(text('SELECT COUNT(*) FROM leagues')).scalar()
        total_matches = db.execute(text('SELECT COUNT(*) FROM matches')).scalar()
        
        print(f'\nDatabase status:')
        print(f'  Total leagues: {total_leagues}')
        print(f'  Total matches: {total_matches}')
        
        if total_matches > 0:
            print(f'\n⚠️  Found {total_matches} matches but no priors!')
            print('This suggests league priors ingestion has not been run yet.')
            print('\nTo create priors, you can:')
            print('  1. Use the API endpoint: POST /api/draw-ingestion/league-priors')
            print('  2. Call ingest_from_matches_table() for each league')
        else:
            print('\nNo matches found in database. Ingest match data first.')
    
finally:
    db.close()

