"""
Team Form Service

Calculates and stores team form metrics for fixtures.
"""
from sqlalchemy.orm import Session
from app.db.models import TeamForm, JackpotFixture, Team
from app.services.team_form_calculator import calculate_team_form, TeamFormMetrics
from typing import Dict, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


def calculate_and_store_team_form(
    db: Session,
    team_id: int,
    fixture_id: int,
    fixture_date: Optional[date] = None,
    matches_count: int = 5
) -> Dict:
    """
    Calculate team form and store it in the database.
    
    Args:
        db: Database session
        team_id: Team ID
        fixture_id: Fixture ID
        fixture_date: Fixture date (default: today)
        matches_count: Number of recent matches to consider
    
    Returns:
        Dict with success status and form metrics
    """
    try:
        # Calculate form
        form_metrics = calculate_team_form(db, team_id, fixture_date, matches_count)
        
        if form_metrics is None:
            logger.debug(f"Insufficient matches to calculate form for team {team_id}")
            return {
                "success": False,
                "error": "Insufficient matches to calculate form"
            }
        
        # Check if form record already exists
        existing = db.query(TeamForm).filter(
            TeamForm.team_id == team_id,
            TeamForm.fixture_id == fixture_id
        ).first()
        
        if existing:
            # Update existing record
            existing.matches_played = form_metrics.matches_played
            existing.wins = form_metrics.wins
            existing.draws = form_metrics.draws
            existing.losses = form_metrics.losses
            existing.goals_scored = form_metrics.goals_scored
            existing.goals_conceded = form_metrics.goals_conceded
            existing.points = form_metrics.points
            existing.form_rating = form_metrics.form_rating
            existing.attack_form = form_metrics.attack_form
            existing.defense_form = form_metrics.defense_form
            existing.last_match_date = form_metrics.last_match_date
            
            db.commit()
            logger.info(f"Updated form record for team {team_id} in fixture {fixture_id}")
            
            return {
                "success": True,
                "form_id": existing.id,
                "action": "updated",
                "form_metrics": {
                    "matches_played": form_metrics.matches_played,
                    "wins": form_metrics.wins,
                    "draws": form_metrics.draws,
                    "losses": form_metrics.losses,
                    "points": form_metrics.points,
                    "form_rating": form_metrics.form_rating,
                    "attack_form": form_metrics.attack_form,
                    "defense_form": form_metrics.defense_form
                }
            }
        else:
            # Create new record
            form_record = TeamForm(
                team_id=team_id,
                fixture_id=fixture_id,
                matches_played=form_metrics.matches_played,
                wins=form_metrics.wins,
                draws=form_metrics.draws,
                losses=form_metrics.losses,
                goals_scored=form_metrics.goals_scored,
                goals_conceded=form_metrics.goals_conceded,
                points=form_metrics.points,
                form_rating=form_metrics.form_rating,
                attack_form=form_metrics.attack_form,
                defense_form=form_metrics.defense_form,
                last_match_date=form_metrics.last_match_date
            )
            
            db.add(form_record)
            db.commit()
            logger.info(f"Created form record for team {team_id} in fixture {fixture_id}")
            
            return {
                "success": True,
                "form_id": form_record.id,
                "action": "created",
                "form_metrics": {
                    "matches_played": form_metrics.matches_played,
                    "wins": form_metrics.wins,
                    "draws": form_metrics.draws,
                    "losses": form_metrics.losses,
                    "points": form_metrics.points,
                    "form_rating": form_metrics.form_rating,
                    "attack_form": form_metrics.attack_form,
                    "defense_form": form_metrics.defense_form
                }
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating/storing form for team {team_id} in fixture {fixture_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_team_form_for_fixture(
    db: Session,
    team_id: int,
    fixture_id: int
) -> Optional[TeamForm]:
    """
    Get stored team form for a fixture.
    
    Args:
        db: Database session
        team_id: Team ID
        fixture_id: Fixture ID
    
    Returns:
        TeamForm object or None
    """
    return db.query(TeamForm).filter(
        TeamForm.team_id == team_id,
        TeamForm.fixture_id == fixture_id
    ).first()

