"""
Diagnostic script to check team training status mismatch
Compares teams in jackpot fixtures vs teams in trained model
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
from app.db.models import Model, ModelStatus, Team, Jackpot, JackpotFixture
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_team_training_status(jackpot_id: Optional[str] = None):
    """Diagnose why teams show as untrained after training"""
    logger.info("=" * 80)
    logger.info("TEAM TRAINING STATUS DIAGNOSTIC")
    logger.info("=" * 80)
    
    db: Session = next(get_db())
    try:
        # Get the jackpot (use most recent if not specified)
        if jackpot_id:
            jackpot = db.query(Jackpot).filter(Jackpot.jackpot_id == jackpot_id).first()
            if not jackpot:
                logger.error(f"Jackpot {jackpot_id} not found")
                return
        else:
            # Get most recent jackpot
            jackpot = db.query(Jackpot).order_by(Jackpot.created_at.desc()).first()
            if not jackpot:
                logger.error("No jackpots found in database")
                return
            jackpot_id = jackpot.jackpot_id
            logger.info(f"Using most recent jackpot: {jackpot_id}")
        
        logger.info(f"\nJackpot: {jackpot_id}")
        logger.info(f"Created: {jackpot.created_at}")
        
        # Get active Poisson model
        poisson_model = db.query(Model).filter(
            Model.model_type == "poisson",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        if not poisson_model:
            logger.error("No active Poisson model found")
            return
        
        logger.info(f"\nActive Poisson Model:")
        logger.info(f"  ID: {poisson_model.id}")
        logger.info(f"  Version: {poisson_model.version}")
        logger.info(f"  Trained: {poisson_model.training_completed_at}")
        
        # Get team_strengths from model
        team_strengths = {}
        if poisson_model.model_weights:
            team_strengths = poisson_model.model_weights.get('team_strengths', {})
        
        logger.info(f"\nTeams in Model (team_strengths): {len(team_strengths)}")
        logger.info("=" * 80)
        
        # Show teams in model with their IDs and names
        model_team_ids = set()
        model_team_names = {}
        for team_id_str, strength_data in team_strengths.items():
            try:
                team_id_int = int(team_id_str) if isinstance(team_id_str, str) else team_id_str
                model_team_ids.add(team_id_int)
                
                team = db.query(Team).filter(Team.id == team_id_int).first()
                if team:
                    model_team_names[team_id_int] = {
                        'name': team.name,
                        'canonical_name': team.canonical_name,
                        'league_id': team.league_id
                    }
                    logger.info(f"  Team ID {team_id_int}: {team.name} (canonical: {team.canonical_name})")
                else:
                    logger.warning(f"  Team ID {team_id_int}: NOT FOUND IN DATABASE")
            except (ValueError, TypeError) as e:
                logger.warning(f"  Invalid team_id: {team_id_str} - {e}")
        
        # Get fixtures from jackpot
        fixtures = db.query(JackpotFixture).filter(
            JackpotFixture.jackpot_id == jackpot.id
        ).all()
        
        logger.info(f"\n\nJackpot Fixtures: {len(fixtures)}")
        logger.info("=" * 80)
        
        # Check each fixture
        fixture_team_ids = set()
        fixture_team_info = {}
        
        for fixture in fixtures:
            if fixture.home_team_id:
                fixture_team_ids.add(fixture.home_team_id)
                if fixture.home_team_id not in fixture_team_info:
                    home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
                    if home_team:
                        fixture_team_info[fixture.home_team_id] = {
                            'name': home_team.name,
                            'canonical_name': home_team.canonical_name,
                            'league_id': home_team.league_id
                        }
            
            if fixture.away_team_id:
                fixture_team_ids.add(fixture.away_team_id)
                if fixture.away_team_id not in fixture_team_info:
                    away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
                    if away_team:
                        fixture_team_info[fixture.away_team_id] = {
                            'name': away_team.name,
                            'canonical_name': away_team.canonical_name,
                            'league_id': away_team.league_id
                        }
        
        logger.info(f"\nTeams in Jackpot Fixtures: {len(fixture_team_ids)}")
        for team_id in sorted(fixture_team_ids):
            info = fixture_team_info.get(team_id, {})
            in_model = team_id in model_team_ids
            status = "✓ IN MODEL" if in_model else "✗ NOT IN MODEL"
            logger.info(f"  Team ID {team_id}: {info.get('name', 'UNKNOWN')} (canonical: {info.get('canonical_name', 'N/A')}) - {status}")
        
        # Compare
        logger.info(f"\n\nCOMPARISON")
        logger.info("=" * 80)
        
        teams_in_both = model_team_ids.intersection(fixture_team_ids)
        teams_only_in_model = model_team_ids - fixture_team_ids
        teams_only_in_fixtures = fixture_team_ids - model_team_ids
        
        logger.info(f"\nTeams in BOTH model and fixtures: {len(teams_in_both)}")
        for team_id in sorted(teams_in_both):
            model_info = model_team_names.get(team_id, {})
            fixture_info = fixture_team_info.get(team_id, {})
            logger.info(f"  Team ID {team_id}: {model_info.get('name', 'N/A')} / {fixture_info.get('name', 'N/A')}")
        
        logger.info(f"\nTeams ONLY in model (not in fixtures): {len(teams_only_in_model)}")
        for team_id in sorted(teams_only_in_model):
            info = model_team_names.get(team_id, {})
            logger.info(f"  Team ID {team_id}: {info.get('name', 'N/A')}")
        
        logger.info(f"\nTeams ONLY in fixtures (not in model): {len(teams_only_in_fixtures)}")
        for team_id in sorted(teams_only_in_fixtures):
            info = fixture_team_info.get(team_id, {})
            logger.info(f"  Team ID {team_id}: {info.get('name', 'N/A')} (canonical: {info.get('canonical_name', 'N/A')})")
        
        # Check for canonical name matches
        logger.info(f"\n\nCANONICAL NAME MATCHING CHECK")
        logger.info("=" * 80)
        
        # Build canonical name mapping from model
        model_canonical_names = {}
        for team_id_int, info in model_team_names.items():
            if info.get('canonical_name'):
                canonical = info['canonical_name'].lower()
                if canonical not in model_canonical_names:
                    model_canonical_names[canonical] = []
                model_canonical_names[canonical].append(team_id_int)
        
        # Check fixture teams by canonical name
        canonical_matches = 0
        for team_id in teams_only_in_fixtures:
            info = fixture_team_info.get(team_id, {})
            canonical = info.get('canonical_name', '').lower() if info.get('canonical_name') else None
            
            if canonical and canonical in model_canonical_names:
                model_ids = model_canonical_names[canonical]
                canonical_matches += 1
                logger.info(f"  ✓ Canonical match: '{canonical}'")
                logger.info(f"    Fixture team ID: {team_id} ({info.get('name', 'N/A')})")
                logger.info(f"    Model team IDs: {model_ids}")
                for model_id in model_ids:
                    model_info = model_team_names.get(model_id, {})
                    logger.info(f"      - Model ID {model_id}: {model_info.get('name', 'N/A')}")
        
        logger.info(f"\n\nSUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total teams in model: {len(model_team_ids)}")
        logger.info(f"Total teams in fixtures: {len(fixture_team_ids)}")
        logger.info(f"Teams in both: {len(teams_in_both)}")
        logger.info(f"Teams only in model: {len(teams_only_in_model)}")
        logger.info(f"Teams only in fixtures: {len(teams_only_in_fixtures)}")
        logger.info(f"Canonical name matches: {canonical_matches}")
        logger.info(f"\nExpected trained teams: {len(teams_in_both) + canonical_matches}")
        logger.info(f"Actual trained teams (from logs): 1")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    jackpot_id = sys.argv[1] if len(sys.argv) > 1 else None
    diagnose_team_training_status(jackpot_id)

