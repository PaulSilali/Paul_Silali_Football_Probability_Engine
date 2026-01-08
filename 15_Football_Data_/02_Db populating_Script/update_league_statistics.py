#!/usr/bin/env python3
"""
Standalone script to update league statistics (avg_draw_rate, home_advantage)
without running the full database population.
"""
import sys
import os
import argparse
import logging

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '2_Backend_Football_Probability_Engine'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.league_statistics import LeagueStatisticsService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_league_statistics(db_url: str, league_code: str = None):
    """Update league statistics from match data"""
    try:
        # Create database connection
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            service = LeagueStatisticsService(db)
            
            if league_code:
                logger.info(f"Updating statistics for league: {league_code}")
                updated = service.update_league_by_code(league_code)
                if updated:
                    logger.info(f"✅ Successfully updated league {league_code}")
                else:
                    logger.warning(f"⚠️ League {league_code} not found or has no matches")
            else:
                logger.info("Updating statistics for all leagues...")
                count = service.update_all_leagues()
                logger.info(f"✅ Successfully updated {count} leagues")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error updating league statistics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update league statistics (avg_draw_rate, home_advantage) from match data"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default="postgresql://postgres:11403775411@localhost/football_probability_engine",
        help="Database connection URL"
    )
    parser.add_argument(
        "--league-code",
        type=str,
        default=None,
        help="Optional: Update specific league by code (e.g., E0)"
    )
    
    args = parser.parse_args()
    
    update_league_statistics(args.db_url, args.league_code)

