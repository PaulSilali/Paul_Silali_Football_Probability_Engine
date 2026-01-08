#!/usr/bin/env python3
"""Quick script to check database status"""

import psycopg2
import sys

db_url = "postgresql://postgres:11403775411@localhost/football_probability_engine"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Check current counts
    cur.execute("SELECT COUNT(*) FROM matches")
    matches = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM teams")
    teams = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leagues")
    leagues = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM staging.matches_raw")
    staging = cur.fetchone()[0]
    
    print(f"Current Database Status:")
    print(f"  Matches: {matches:,}")
    print(f"  Teams: {teams:,}")
    print(f"  Leagues: {leagues:,}")
    print(f"  Staging rows: {staging:,}")
    
    if matches > 0:
        cur.execute("SELECT MIN(match_date), MAX(match_date) FROM matches")
        min_date, max_date = cur.fetchone()
        print(f"  Date range: {min_date} to {max_date}")
    
    conn.close()
    print("\nDatabase connection successful!")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

