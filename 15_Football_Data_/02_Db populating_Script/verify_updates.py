#!/usr/bin/env python3
"""
Verify that leagues and teams tables have been updated
"""
import sys
import os
import argparse

# Add parent directory to path to import from backend
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, '..', '..', '2_Backend_Football_Probability_Engine')
backend_dir = os.path.normpath(backend_dir)
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def verify_updates(db_url: str):
    """Verify that leagues and teams have been updated"""
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("VERIFYING LEAGUE UPDATES")
        print("="*60)
        
        # Check leagues
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_leagues,
                COUNT(CASE WHEN avg_draw_rate != 0.26 OR home_advantage != 0.35 THEN 1 END) as updated_leagues,
                COUNT(CASE WHEN avg_draw_rate = 0.26 AND home_advantage = 0.35 THEN 1 END) as default_leagues
            FROM leagues
        """))
        row = result.fetchone()
        print(f"Total Leagues: {row[0]}")
        print(f"Updated Leagues (non-default): {row[1]}")
        print(f"Default Leagues: {row[2]}")
        
        # Show sample updated leagues
        result = db.execute(text("""
            SELECT code, name, avg_draw_rate, home_advantage
            FROM leagues
            WHERE avg_draw_rate != 0.26 OR home_advantage != 0.35
            ORDER BY code
            LIMIT 10
        """))
        print("\nSample Updated Leagues:")
        print("-" * 60)
        for row in result:
            print(f"{row[0]:6} {row[1]:30} draw_rate={row[2]:.3f} home_adv={row[3]:.3f}")
        
        print("\n" + "="*60)
        print("VERIFYING TEAM UPDATES")
        print("="*60)
        
        # Check teams
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_teams,
                COUNT(CASE WHEN last_calculated IS NOT NULL THEN 1 END) as updated_teams,
                COUNT(CASE WHEN attack_rating != 1.0 OR defense_rating != 1.0 OR home_bias != 0.0 THEN 1 END) as teams_with_ratings
            FROM teams
        """))
        row = result.fetchone()
        print(f"Total Teams: {row[0]}")
        print(f"Teams with last_calculated: {row[1]}")
        print(f"Teams with calculated ratings: {row[2]}")
        
        # Show sample updated teams
        result = db.execute(text("""
            SELECT name, attack_rating, defense_rating, home_bias, last_calculated
            FROM teams
            WHERE last_calculated IS NOT NULL
            ORDER BY last_calculated DESC
            LIMIT 10
        """))
        print("\nSample Updated Teams:")
        print("-" * 80)
        for row in result:
            print(f"{row[0]:30} attack={row[1]:.3f} defense={row[2]:.3f} bias={row[3]:.3f} updated={row[4]}")
        
        print("\n" + "="*60)
        
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify league and team updates")
    parser.add_argument(
        "--db-url",
        type=str,
        default="postgresql://postgres:11403775411@localhost/football_probability_engine",
        help="Database connection URL"
    )
    
    args = parser.parse_args()
    verify_updates(args.db_url)

