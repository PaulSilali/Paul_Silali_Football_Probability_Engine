"""
Script to verify canonical names are set for all teams
Checks teams in database and identifies missing canonical names
Date: 2026-01-12
"""
import sys
import os
from pathlib import Path

# Get the absolute path to the backend directory
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent

# Add backend directory to Python path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Change to backend directory for relative imports
os.chdir(str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Team, Model, ModelStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_canonical_names():
    """Verify canonical names are set for all teams"""
    logger.info("=" * 80)
    logger.info("CANONICAL NAMES VERIFICATION")
    logger.info("=" * 80)
    
    db: Session = next(get_db())
    try:
        # Get all teams
        all_teams = db.query(Team).all()
        logger.info(f"\nTotal teams in database: {len(all_teams)}")
        
        # Check canonical names
        teams_with_canonical = []
        teams_without_canonical = []
        teams_with_empty_canonical = []
        
        for team in all_teams:
            if team.canonical_name and team.canonical_name.strip():
                teams_with_canonical.append(team)
            elif team.canonical_name is None:
                teams_without_canonical.append(team)
            else:
                teams_with_empty_canonical.append(team)
        
        logger.info(f"\nTeams WITH canonical name: {len(teams_with_canonical)}")
        logger.info(f"Teams WITHOUT canonical name: {len(teams_without_canonical)}")
        logger.info(f"Teams with EMPTY canonical name: {len(teams_with_empty_canonical)}")
        
        # Show teams without canonical names
        if teams_without_canonical or teams_with_empty_canonical:
            logger.warning("\n⚠ Teams missing canonical names:")
            for team in teams_without_canonical + teams_with_empty_canonical:
                logger.warning(f"  - Team ID {team.id}: {team.name} (league_id: {team.league_id})")
        
        # Check teams in active model
        poisson_model = db.query(Model).filter(
            Model.model_type == "poisson",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        if poisson_model:
            logger.info(f"\n\nActive Poisson Model: {poisson_model.version} (ID: {poisson_model.id})")
            
            if poisson_model.model_weights:
                team_strengths = poisson_model.model_weights.get('team_strengths', {})
                logger.info(f"Teams in model: {len(team_strengths)}")
                
                # Check canonical names for teams in model
                model_teams_with_canonical = 0
                model_teams_without_canonical = []
                
                for team_id_str, strength_data in team_strengths.items():
                    try:
                        team_id_int = int(team_id_str) if isinstance(team_id_str, str) else team_id_str
                        team = db.query(Team).filter(Team.id == team_id_int).first()
                        if team:
                            if team.canonical_name and team.canonical_name.strip():
                                model_teams_with_canonical += 1
                            else:
                                model_teams_without_canonical.append({
                                    'id': team_id_int,
                                    'name': team.name,
                                    'canonical': team.canonical_name
                                })
                    except (ValueError, TypeError):
                        continue
                
                logger.info(f"Model teams WITH canonical name: {model_teams_with_canonical}/{len(team_strengths)}")
                if model_teams_without_canonical:
                    logger.warning(f"\n⚠ Model teams WITHOUT canonical name: {len(model_teams_without_canonical)}")
                    for team_info in model_teams_without_canonical[:10]:  # Show first 10
                        logger.warning(f"  - Team ID {team_info['id']}: {team_info['name']} (canonical: {team_info['canonical']})")
                    if len(model_teams_without_canonical) > 10:
                        logger.warning(f"  ... and {len(model_teams_without_canonical) - 10} more")
        else:
            logger.warning("\n⚠ No active Poisson model found")
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        total_teams = len(all_teams)
        teams_with_canonical_count = len(teams_with_canonical)
        coverage = (teams_with_canonical_count / total_teams * 100) if total_teams > 0 else 0
        logger.info(f"Canonical name coverage: {teams_with_canonical_count}/{total_teams} ({coverage:.1f}%)")
        
        if teams_without_canonical or teams_with_empty_canonical:
            logger.warning(f"\n⚠ {len(teams_without_canonical) + len(teams_with_empty_canonical)} teams need canonical names set")
            logger.warning("  Recommendation: Set canonical_name for all teams to enable canonical name matching")
        else:
            logger.info("\n✓ All teams have canonical names set!")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    verify_canonical_names()

