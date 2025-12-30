"""
Script to add missing teams to the database.

This script adds teams that are frequently appearing in jackpots but not found
in the database, causing them to use default strengths (1.0, 1.0).
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import Team, League
from app.services.team_resolver import normalize_team_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Teams to add - organized by likely league/country
# Format: (team_name, league_name, country)
MISSING_TEAMS = [
    # Swedish Allsvenskan
    ("Norrkoping FK", "Allsvenskan", "Sweden"),
    ("IK Sirius", "Allsvenskan", "Sweden"),
    
    # Dutch Eredivisie / Eerste Divisie
    ("Excelsior Rotterdam", "Eredivisie", "Netherlands"),
    ("Heracles Almelo", "Eredivisie", "Netherlands"),
    ("NAC Breda", "Eerste Divisie", "Netherlands"),
    ("Go Ahead Eagles", "Eredivisie", "Netherlands"),
    ("SC Telstar", "Eerste Divisie", "Netherlands"),
    ("FC Groningen", "Eredivisie", "Netherlands"),
    ("FC Twente", "Eredivisie", "Netherlands"),
    ("PEC Zwolle", "Eredivisie", "Netherlands"),
    
    # Spanish La Liga / Segunda
    ("Celta Vigo", "La Liga", "Spain"),
    ("Levante", "La Liga", "Spain"),
    ("Alaves", "La Liga", "Spain"),
    ("Espanyol", "La Liga", "Spain"),
    ("Real Sociedad", "La Liga", "Spain"),
    ("Athletic Bilbao", "La Liga", "Spain"),
    
    # Austrian Bundesliga
    ("SK Rapid", "Austrian Bundesliga", "Austria"),
    ("SK Sturm Graz", "Austrian Bundesliga", "Austria"),
    
    # Russian Premier League
    ("FK Krasnodar", "Russian Premier League", "Russia"),
    ("FK Spartak Moscow", "Russian Premier League", "Russia"),
    
    # German Bundesliga (common teams that might be missing)
    ("Union Berlin", "Bundesliga", "Germany"),
    ("Freiburg", "Bundesliga", "Germany"),
    ("Leipzig", "Bundesliga", "Germany"),
    ("Stuttgart", "Bundesliga", "Germany"),
    ("Wolfsburg", "Bundesliga", "Germany"),
    ("Hoffenheim", "Bundesliga", "Germany"),
    
    # English Premier League
    ("Nottingham", "Premier League", "England"),
    ("Man Utd", "Premier League", "England"),
    ("Tottenham", "Premier League", "England"),
    ("Chelsea", "Premier League", "England"),
]


def get_or_create_league(db, league_name: str, country: str):
    """Get or create a league"""
    # Try to find existing league
    league = db.query(League).filter(
        League.name.ilike(f"%{league_name}%"),
        League.country.ilike(f"%{country}%")
    ).first()
    
    if league:
        logger.info(f"Found existing league: {league.name} ({league.country})")
        return league
    
    # Create new league if not found
    # Generate a code from league name
    code = league_name.upper().replace(" ", "")[:10]
    
    league = League(
        code=code,
        name=league_name,
        country=country,
        tier=1,
        avg_draw_rate=0.26,
        home_advantage=0.35,
        is_active=True
    )
    db.add(league)
    db.flush()
    logger.info(f"Created new league: {league_name} ({country})")
    return league


def add_team(db, team_name: str, league: League, dry_run: bool = False):
    """Add a team to the database if it doesn't exist"""
    canonical_name = normalize_team_name(team_name)
    
    # Check if team already exists
    existing = db.query(Team).filter(
        Team.canonical_name == canonical_name,
        Team.league_id == league.id
    ).first()
    
    if existing:
        logger.info(f"Team already exists: {team_name} -> {existing.canonical_name} (ID: {existing.id})")
        return False
    
    if dry_run:
        logger.info(f"[DRY RUN] Would add team: {team_name} -> {canonical_name} to league {league.name}")
        return True
    
    # Create new team
    team = Team(
        league_id=league.id,
        name=team_name,
        canonical_name=canonical_name,
        attack_rating=1.0,  # Default - will be updated when model is trained
        defense_rating=1.0,  # Default - will be updated when model is trained
        home_bias=0.0
    )
    db.add(team)
    logger.info(f"Added team: {team_name} -> {canonical_name} to league {league.name}")
    return True


def main(dry_run: bool = False):
    """Main function to add missing teams"""
    db = SessionLocal()
    
    try:
        added_count = 0
        skipped_count = 0
        created_leagues = []
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Adding missing teams to database...")
        
        for team_name, league_name, country in MISSING_TEAMS:
            try:
                # Get or create league
                league = get_or_create_league(db, league_name, country)
                if league.id not in [l.id for l in created_leagues]:
                    created_leagues.append(league)
                
                # Add team
                if add_team(db, team_name, league, dry_run=dry_run):
                    added_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error adding team {team_name}: {e}")
                continue
        
        if not dry_run:
            db.commit()
            logger.info(f"✓ Committed changes to database")
        
        logger.info(f"\n=== SUMMARY ===")
        logger.info(f"Teams added: {added_count}")
        logger.info(f"Teams skipped (already exist): {skipped_count}")
        logger.info(f"Leagues created: {len(created_leagues)}")
        
        if dry_run:
            logger.info("\nThis was a dry run. Run without --dry-run to actually add teams.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add missing teams to the database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without making changes")
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)

