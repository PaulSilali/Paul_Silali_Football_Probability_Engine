"""
Team Form Calculator

Calculates recent team form (last N matches) and uses it to adjust team strengths.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.db.models import Match, Team
from typing import Dict, Optional, List, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class TeamFormMetrics:
    """Team form metrics from recent matches"""
    team_id: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_scored: float
    goals_conceded: float
    points: int  # 3*wins + draws
    form_rating: float  # Normalized form rating (0.0-1.0)
    attack_form: float  # Goals scored per match (normalized)
    defense_form: float  # Goals conceded per match (normalized, inverted)
    last_match_date: Optional[date] = None


def calculate_team_form(
    db: Session,
    team_id: int,
    reference_date: Optional[date] = None,
    matches_count: int = 5,
    min_matches: int = 3
) -> Optional[TeamFormMetrics]:
    """
    Calculate team form from recent matches.
    
    Args:
        db: Database session
        team_id: Team ID
        reference_date: Reference date (default: today)
        matches_count: Number of recent matches to consider (default: 5)
        min_matches: Minimum matches required to calculate form (default: 3)
    
    Returns:
        TeamFormMetrics or None if insufficient matches
    """
    if reference_date is None:
        reference_date = date.today()
    
    try:
        # Get recent matches for this team
        matches = db.execute(
            text("""
                SELECT 
                    match_date,
                    home_team_id,
                    away_team_id,
                    home_goals,
                    away_goals,
                    result
                FROM matches
                WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                  AND match_date < :reference_date
                  AND home_goals IS NOT NULL
                  AND away_goals IS NOT NULL
                ORDER BY match_date DESC
                LIMIT :matches_count
            """),
            {
                "team_id": team_id,
                "reference_date": reference_date,
                "matches_count": matches_count
            }
        ).fetchall()
        
        if len(matches) < min_matches:
            logger.debug(f"Insufficient matches for team {team_id}: {len(matches)} < {min_matches}")
            return None
        
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        last_match_date = None
        
        for match in matches:
            match_date, home_id, away_id, home_goals, away_goals, result = match
            
            if last_match_date is None:
                last_match_date = match_date
            
            # Determine team's goals and result
            if home_id == team_id:
                team_goals = home_goals or 0
                opponent_goals = away_goals or 0
                is_home = True
            else:
                team_goals = away_goals or 0
                opponent_goals = home_goals or 0
                is_home = False
            
            goals_scored += team_goals
            goals_conceded += opponent_goals
            
            # Determine result
            if result == 'H':
                if is_home:
                    wins += 1
                else:
                    losses += 1
            elif result == 'A':
                if is_home:
                    losses += 1
                else:
                    wins += 1
            elif result == 'D':
                draws += 1
            else:
                # Fallback: use goals
                if team_goals > opponent_goals:
                    wins += 1
                elif team_goals < opponent_goals:
                    losses += 1
                else:
                    draws += 1
        
        matches_played = len(matches)
        points = 3 * wins + draws
        
        # Calculate form metrics
        # Form rating: points per match (normalized to 0-1, where 1.0 = 3 points/match = perfect)
        form_rating = min(1.0, points / (matches_played * 3.0))
        
        # Attack form: goals scored per match (normalized, assuming 2.5 goals/match = 1.0)
        avg_goals_scored = goals_scored / matches_played if matches_played > 0 else 0
        attack_form = min(1.0, avg_goals_scored / 2.5)  # Normalize to 0-1
        
        # Defense form: goals conceded per match (inverted and normalized, lower is better)
        avg_goals_conceded = goals_conceded / matches_played if matches_played > 0 else 0
        # Invert: 0 goals conceded = 1.0, 2.5+ goals conceded = 0.0
        defense_form = max(0.0, 1.0 - (avg_goals_conceded / 2.5))
        
        return TeamFormMetrics(
            team_id=team_id,
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            points=points,
            form_rating=form_rating,
            attack_form=attack_form,
            defense_form=defense_form,
            last_match_date=last_match_date
        )
    
    except Exception as e:
        logger.error(f"Error calculating team form for team {team_id}: {e}", exc_info=True)
        return None


def get_team_form_for_fixture(
    db: Session,
    team_id: int,
    fixture_date: Optional[date] = None,
    matches_count: int = 5
) -> Optional[TeamFormMetrics]:
    """
    Get team form for a specific fixture date.
    
    Args:
        db: Database session
        team_id: Team ID
        fixture_date: Fixture date (default: today)
        matches_count: Number of recent matches to consider
    
    Returns:
        TeamFormMetrics or None
    """
    return calculate_team_form(db, team_id, fixture_date, matches_count)


def adjust_team_strength_with_form(
    base_attack: float,
    base_defense: float,
    form_metrics: Optional[TeamFormMetrics],
    form_weight: float = 0.15  # How much form affects strength (0.0-1.0)
) -> tuple[float, float]:
    """
    Adjust team strength based on recent form.
    
    Args:
        base_attack: Base attack strength from model
        base_defense: Base defense strength from model
        form_metrics: Team form metrics (None = no adjustment)
        form_weight: Weight of form adjustment (0.0 = no effect, 1.0 = full effect)
    
    Returns:
        Tuple of (adjusted_attack, adjusted_defense)
    """
    if form_metrics is None:
        return base_attack, base_defense
    
    # Adjust attack based on attack form
    # form_rating affects overall strength, attack_form affects attack specifically
    attack_adjustment = 1.0 + form_weight * (form_metrics.attack_form - 0.5)  # -0.5 to +0.5 range
    attack_adjustment *= 1.0 + form_weight * (form_metrics.form_rating - 0.5)  # Overall form
    
    # Adjust defense based on defense form
    defense_adjustment = 1.0 + form_weight * (form_metrics.defense_form - 0.5)
    defense_adjustment *= 1.0 + form_weight * (form_metrics.form_rating - 0.5)
    
    # Clamp adjustments to reasonable range (0.7x to 1.3x)
    attack_adjustment = max(0.7, min(1.3, attack_adjustment))
    defense_adjustment = max(0.7, min(1.3, defense_adjustment))
    
    adjusted_attack = base_attack * attack_adjustment
    adjusted_defense = base_defense * defense_adjustment
    
    return adjusted_attack, adjusted_defense

