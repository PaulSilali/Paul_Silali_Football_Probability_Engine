"""
Script to Verify Teams in Database

This script checks:
1. Which table teams are saved to
2. How many teams exist per league
3. Sample teams from each league

Usage:
    python scripts/verify_teams_in_db.py
    python scripts/verify_teams_in_db.py --league E0  # Only Premier League
"""

import sys
from pathlib import Path
from sqlalchemy import func

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import League, Team
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_teams_in_database(league_code_filter: str = None):
    """
    Verify teams are saved in the database
    
    Args:
        league_code_filter: Optional league code to filter (e.g., "E0")
    """
    db = SessionLocal()
    
    try:
        # Get table name from model
        table_name = Team.__tablename__
        logger.info("="*60)
        logger.info("TEAM DATABASE VERIFICATION")
        logger.info("="*60)
        logger.info(f"📊 Table Name: {table_name}")
        logger.info("")
        
        # Query teams
        query = db.query(Team).join(League)
        
        if league_code_filter:
            query = query.filter(League.code == league_code_filter)
        
        all_teams = query.all()
        total_teams = len(all_teams)
        
        logger.info(f"📈 Total Teams in Database: {total_teams}")
        logger.info("")
        
        # Group by league
        league_stats = db.query(
            League.code,
            League.name,
            func.count(Team.id).label('team_count')
        ).join(Team).group_by(League.id, League.code, League.name)
        
        if league_code_filter:
            league_stats = league_stats.filter(League.code == league_code_filter)
        
        league_stats = league_stats.order_by(League.code).all()
        
        logger.info("📋 Teams per League:")
        logger.info("-" * 60)
        
        for league_code, league_name, team_count in league_stats:
            logger.info(f"  {league_code:4} - {league_name:30} : {team_count:3} teams")
            
            # Show sample teams
            sample_teams = db.query(Team).join(League).filter(
                League.code == league_code
            ).limit(5).all()
            
            if sample_teams:
                logger.info(f"      Sample teams:")
                for team in sample_teams:
                    logger.info(f"        - {team.name:30} -> {team.canonical_name}")
        
        logger.info("")
        logger.info("="*60)
        
        # Show table structure info
        logger.info("📋 Table Structure:")
        logger.info(f"  Table: {table_name}")
        logger.info(f"  Columns:")
        logger.info(f"    - id (Primary Key)")
        logger.info(f"    - league_id (Foreign Key -> leagues.id)")
        logger.info(f"    - name (Team display name)")
        logger.info(f"    - canonical_name (Normalized name for matching)")
        logger.info(f"    - attack_rating, defense_rating, home_bias")
        logger.info(f"    - created_at, updated_at")
        logger.info("")
        
        # Check for potential duplicates (same canonical_name in same league)
        duplicates = db.query(
            Team.league_id,
            Team.canonical_name,
            func.count(Team.id).label('count')
        ).group_by(Team.league_id, Team.canonical_name).having(
            func.count(Team.id) > 1
        ).all()
        
        if duplicates:
            logger.warning(f"⚠️  Found {len(duplicates)} duplicate canonical names:")
            for league_id, canonical_name, count in duplicates:
                league = db.query(League).filter(League.id == league_id).first()
                logger.warning(f"  - League {league.code if league else league_id}: '{canonical_name}' appears {count} times")
        else:
            logger.info("✅ No duplicate canonical names found (good!)")
        
        logger.info("="*60)
        
        return {
            "table_name": table_name,
            "total_teams": total_teams,
            "leagues": len(league_stats),
            "duplicates": len(duplicates) if duplicates else 0
        }
    
    except Exception as e:
        logger.error(f"Error verifying teams: {e}", exc_info=True)
        return None
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify teams in database")
    parser.add_argument(
        "--league",
        type=str,
        help="Filter by league code (e.g., E0 for Premier League)"
    )
    
    args = parser.parse_args()
    
    result = verify_teams_in_database(args.league)
    
    if result:
        logger.info("\n✅ Verification complete!")
        logger.info(f"   Table: {result['table_name']}")
        logger.info(f"   Total Teams: {result['total_teams']}")
        logger.info(f"   Leagues: {result['leagues']}")
        logger.info(f"   Duplicates: {result['duplicates']}")

