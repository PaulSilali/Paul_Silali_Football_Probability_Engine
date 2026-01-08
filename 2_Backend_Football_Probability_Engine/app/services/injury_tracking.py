"""
Injury Tracking Service

Tracks and manages team injury data for fixtures.
"""
from sqlalchemy.orm import Session
from app.db.models import TeamInjuries, JackpotFixture, Team
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def record_team_injuries(
    db: Session,
    team_id: int,
    fixture_id: int,
    key_players_missing: Optional[int] = None,
    injury_severity: Optional[float] = None,
    attackers_missing: Optional[int] = None,
    midfielders_missing: Optional[int] = None,
    defenders_missing: Optional[int] = None,
    goalkeepers_missing: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict:
    """
    Record injury data for a team in a fixture.
    
    Args:
        db: Database session
        team_id: Team ID
        fixture_id: Fixture ID
        key_players_missing: Number of key players missing
        injury_severity: Overall injury severity (0.0-1.0)
        attackers_missing: Number of attacking players missing
        midfielders_missing: Number of midfielders missing
        defenders_missing: Number of defenders missing
        goalkeepers_missing: Number of goalkeepers missing
        notes: Free text notes about injuries
    
    Returns:
        Dict with success status and injury record ID
    """
    try:
        # Validate inputs
        if injury_severity is not None:
            injury_severity = max(0.0, min(1.0, injury_severity))  # Clamp to 0-1
        
        # Check if injury record already exists
        existing = db.query(TeamInjuries).filter(
            TeamInjuries.team_id == team_id,
            TeamInjuries.fixture_id == fixture_id
        ).first()
        
        if existing:
            # Update existing record
            if key_players_missing is not None:
                existing.key_players_missing = key_players_missing
            if injury_severity is not None:
                existing.injury_severity = injury_severity
            if attackers_missing is not None:
                existing.attackers_missing = attackers_missing
            if midfielders_missing is not None:
                existing.midfielders_missing = midfielders_missing
            if defenders_missing is not None:
                existing.defenders_missing = defenders_missing
            if goalkeepers_missing is not None:
                existing.goalkeepers_missing = goalkeepers_missing
            if notes is not None:
                existing.notes = notes
            
            db.commit()
            logger.info(f"Updated injury record for team {team_id} in fixture {fixture_id}")
            
            return {
                "success": True,
                "injury_id": existing.id,
                "action": "updated"
            }
        else:
            # Create new record
            # Calculate injury_severity if not provided but key_players_missing is
            if injury_severity is None and key_players_missing is not None:
                # Estimate severity: assume 5 key players = 1.0 severity
                injury_severity = min(1.0, key_players_missing / 5.0)
            
            injury_record = TeamInjuries(
                team_id=team_id,
                fixture_id=fixture_id,
                key_players_missing=key_players_missing or 0,
                injury_severity=injury_severity,
                attackers_missing=attackers_missing or 0,
                midfielders_missing=midfielders_missing or 0,
                defenders_missing=defenders_missing or 0,
                goalkeepers_missing=goalkeepers_missing or 0,
                notes=notes
            )
            
            db.add(injury_record)
            db.commit()
            logger.info(f"Created injury record for team {team_id} in fixture {fixture_id}")
            
            return {
                "success": True,
                "injury_id": injury_record.id,
                "action": "created"
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording injuries for team {team_id} in fixture {fixture_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_team_injuries_for_fixture(
    db: Session,
    team_id: int,
    fixture_id: int
) -> Optional[TeamInjuries]:
    """
    Get injury data for a team in a fixture.
    
    Args:
        db: Database session
        team_id: Team ID
        fixture_id: Fixture ID
    
    Returns:
        TeamInjuries object or None
    """
    return db.query(TeamInjuries).filter(
        TeamInjuries.team_id == team_id,
        TeamInjuries.fixture_id == fixture_id
    ).first()


def calculate_injury_severity(
    key_players_missing: int,
    attackers_missing: int = 0,
    midfielders_missing: int = 0,
    defenders_missing: int = 0,
    goalkeepers_missing: int = 0
) -> float:
    """
    Calculate overall injury severity from position-specific injuries.
    
    Args:
        key_players_missing: Number of key players missing
        attackers_missing: Number of attackers missing
        midfielders_missing: Number of midfielders missing
        defenders_missing: Number of defenders missing
        goalkeepers_missing: Number of goalkeepers missing
    
    Returns:
        Injury severity (0.0-1.0)
    """
    # Weight different positions differently
    # Goalkeepers are most critical (1.0 weight)
    # Key players are very important (0.8 weight)
    # Other positions weighted by importance
    
    total_impact = (
        goalkeepers_missing * 1.0 +
        key_players_missing * 0.8 +
        attackers_missing * 0.3 +
        midfielders_missing * 0.4 +
        defenders_missing * 0.3
    )
    
    # Normalize: assume 5 total key players/positions = max severity
    severity = min(1.0, total_impact / 5.0)
    
    return severity

