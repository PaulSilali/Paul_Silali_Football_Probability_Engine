"""Check season format in matches table"""
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    print('\n=== Season Format Check ===')
    
    # Check distinct seasons
    seasons = db.execute(text("""
        SELECT DISTINCT season 
        FROM matches 
        WHERE season IS NOT NULL 
        ORDER BY season DESC 
        LIMIT 10
    """)).fetchall()
    
    print('\n[1] Seasons stored in matches table:')
    for s in seasons:
        print(f'  "{s[0]}" (type: {type(s[0]).__name__}, length: {len(str(s[0]))})')
    
    # Check if season 2324 exists
    count_2324 = db.execute(text("""
        SELECT COUNT(*) 
        FROM matches 
        WHERE season = '2324'
    """)).scalar()
    
    print(f'\n[2] Matches with season = "2324": {count_2324}')
    
    # Check if season 2023-24 exists
    count_2023_24 = db.execute(text("""
        SELECT COUNT(*) 
        FROM matches 
        WHERE season = '2023-24'
    """)).scalar()
    
    print(f'[3] Matches with season = "2023-24": {count_2023_24}')
    
    # Check what format is used for 2023-24 season
    sample_2324 = db.execute(text("""
        SELECT l.code, m.season, COUNT(*) as match_count
        FROM matches m
        JOIN leagues l ON m.league_id = l.id
        WHERE m.season LIKE '%2324%' OR m.season LIKE '%2023%' OR m.season LIKE '%23-24%'
        GROUP BY l.code, m.season
        ORDER BY match_count DESC
        LIMIT 5
    """)).fetchall()
    
    print('\n[4] Sample leagues with 2023-24 season data:')
    for row in sample_2324:
        print(f'  {row[0]:6} : Season="{row[1]}", Matches={row[2]}')
    
finally:
    db.close()

