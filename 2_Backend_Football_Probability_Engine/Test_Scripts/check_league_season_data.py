"""Check which leagues have matches for season 2324 and other seasons"""
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from sqlalchemy import text
from datetime import datetime

db = SessionLocal()

try:
    print('\n=== League Data Availability Check ===')
    
    # Check season 2324 specifically
    print('\n[1] Checking season 2324 (2023-24):')
    print('-' * 80)
    season_2324 = db.execute(text("""
        SELECT l.code, COUNT(*) as match_count
        FROM matches m
        JOIN leagues l ON m.league_id = l.id
        WHERE m.season = '2324' OR m.season = '2023-24' OR m.season = '23/24'
        GROUP BY l.code
        ORDER BY match_count DESC
    """)).fetchall()
    
    if season_2324:
        print(f'Found {len(season_2324)} leagues with data for season 2324:')
        for row in season_2324:
            print(f'  {row[0]:6} : {row[1]:4} matches')
    else:
        print('  No matches found for season 2324')
    
    # Check all seasons
    print('\n[2] Checking all seasons (top 20 leagues by total matches):')
    print('-' * 80)
    all_seasons = db.execute(text("""
        SELECT l.code, COUNT(DISTINCT m.season) as season_count, COUNT(*) as total_matches,
               STRING_AGG(DISTINCT m.season, ', ' ORDER BY m.season) as seasons
        FROM matches m
        JOIN leagues l ON m.league_id = l.id
        GROUP BY l.code
        ORDER BY total_matches DESC
        LIMIT 20
    """)).fetchall()
    
    if all_seasons:
        print(f'Found {len(all_seasons)} leagues with match data:')
        for row in all_seasons:
            print(f'  {row[0]:6} : {row[2]:5} matches across {row[1]} seasons | Seasons: {row[3][:50]}')
    
    # Check what seasons are available
    print('\n[3] Available seasons in database:')
    print('-' * 80)
    seasons = db.execute(text("""
        SELECT DISTINCT m.season, COUNT(*) as match_count
        FROM matches m
        GROUP BY m.season
        ORDER BY m.season DESC
        LIMIT 15
    """)).fetchall()
    
    if seasons:
        print(f'Found {len(seasons)} distinct seasons:')
        for row in seasons:
            print(f'  {row[0]:10} : {row[1]:5} matches')
    
    # Check leagues that were called but have no data
    print('\n[4] Checking if leagues exist but have no matches:')
    print('-' * 80)
    leagues_no_matches = db.execute(text("""
        SELECT l.code, l.name
        FROM leagues l
        LEFT JOIN matches m ON m.league_id = l.id
        WHERE m.id IS NULL
        ORDER BY l.code
        LIMIT 20
    """)).fetchall()
    
    if leagues_no_matches:
        print(f'Found {len(leagues_no_matches)} leagues with no matches:')
        for row in leagues_no_matches:
            print(f'  {row[0]:6} : {row[1]}')
    
finally:
    db.close()

