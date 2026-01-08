"""
Quick script to add teams that are showing as missing in the UI.

Based on common missing teams from jackpot inputs.
Run this script to add them to the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import Team, League
from app.services.team_resolver import create_team_if_not_exists, normalize_team_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Teams that commonly appear as missing in the UI
# Format: (team_name, league_code, league_name, country)
MISSING_TEAMS = [
    # A-League (Australia)
    ("Auckland FC", "AUS1", "A-League", "Australia"),
    ("Brisbane Roar", "AUS1", "A-League", "Australia"),
    
    # Turkish Super Lig
    ("Vanspor BB", "T1", "Super Lig", "Turkey"),
    ("Boluspor", "T1", "Super Lig", "Turkey"),
    
    # Ethiopian Premier League (may need to create league first)
    ("Hawassa Kenema SC", None, "Ethiopian Premier League", "Ethiopia"),
    ("Saint George FC", None, "Ethiopian Premier League", "Ethiopia"),
    
    # German Bundesliga
    ("Eintracht Frankfurt", "D1", "Bundesliga", "Germany"),
    ("Borussia Dortmund", "D1", "Bundesliga", "Germany"),
]


def get_or_create_league(db, league_code: str, league_name: str, country: str):
    """Get or create a league"""
    # Try by code first
    if league_code:
        league = db.query(League).filter(League.code == league_code).first()
        if league:
            return league
    
    # Try by name
    league = db.query(League).filter(
        League.name.ilike(f"%{league_name}%"),
        League.country.ilike(f"%{country}%")
    ).first()
    
    if league:
        logger.info(f"Found league: {league.name} ({league.code})")
        return league
    
    # Create new league if not found
    if not league_code:
        # Generate code from league name
        league_code = league_name.upper().replace(" ", "")[:10]
        # Check if code already exists
        existing = db.query(League).filter(League.code == league_code).first()
        if existing:
            logger.warning(f"League code {league_code} already exists, using existing league")
            return existing
    
    league = League(
        code=league_code,
        name=league_name,
        country=country,
        tier=1,
        avg_draw_rate=0.26,
        home_advantage=0.35,
        is_active=True
    )
    db.add(league)
    db.flush()
    logger.info(f"Created new league: {league_name} ({league_code})")
    return league


def main(dry_run: bool = False):
    """Add missing teams to database"""
    db = SessionLocal()
    
    try:
        added_count = 0
        skipped_count = 0
        error_count = 0
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Adding missing teams...")
        logger.info("=" * 60)
        
        for team_name, league_code, league_name, country in MISSING_TEAMS:
            try:
                # Get or create league
                league = get_or_create_league(db, league_code, league_name, country)
                
                # Check if team already exists
                canonical_name = normalize_team_name(team_name)
                existing = db.query(Team).filter(
                    Team.canonical_name == canonical_name,
                    Team.league_id == league.id
                ).first()
                
                if existing:
                    logger.info(f"✓ Already exists: {team_name} (ID: {existing.id})")
                    skipped_count += 1
                    continue
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would add: {team_name} → {canonical_name} ({league.name})")
                    added_count += 1
                else:
                    # Create team
                    team = create_team_if_not_exists(db, team_name, league.id)
                    logger.info(f"✓ Added: {team_name} (ID: {team.id}, canonical: {team.canonical_name})")
                    added_count += 1
                    
            except Exception as e:
                logger.error(f"✗ Error adding {team_name}: {e}")
                error_count += 1
                continue
        
        if not dry_run:
            db.commit()
            logger.info("✓ Changes committed to database")
        
        logger.info("=" * 60)
        logger.info("SUMMARY:")
        logger.info(f"  Added: {added_count}")
        logger.info(f"  Skipped (already exist): {skipped_count}")
        logger.info(f"  Errors: {error_count}")
        
        if dry_run:
            logger.info("\nThis was a dry run. Run without --dry-run to actually add teams.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Critical error: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add missing teams from UI")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without making changes")
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)

