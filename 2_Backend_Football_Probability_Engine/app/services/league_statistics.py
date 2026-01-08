"""
League Statistics Service
Calculates and updates league-specific statistics (avg_draw_rate, home_advantage)
from match data.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models import League, Match, MatchResult
import logging

logger = logging.getLogger(__name__)


class LeagueStatisticsService:
    """Service for calculating and updating league statistics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def update_all_leagues(self):
        """Update statistics for all leagues"""
        leagues = self.db.query(League).all()
        
        updated_count = 0
        for league in leagues:
            if self.update_league(league.id):
                updated_count += 1
        
        self.db.commit()
        logger.info(f"Updated statistics for {updated_count} out of {len(leagues)} leagues")
        return updated_count
    
    def update_league(self, league_id: int) -> bool:
        """
        Update statistics for a single league
        
        Returns:
            True if updated, False if no matches found
        """
        league = self.db.query(League).filter(League.id == league_id).first()
        if not league:
            logger.warning(f"League {league_id} not found")
            return False
        
        # Calculate from last 5 years of matches
        cutoff_date = datetime.now() - timedelta(days=5*365)
        
        matches = self.db.query(Match).filter(
            Match.league_id == league_id,
            Match.match_date >= cutoff_date
        ).all()
        
        if not matches:
            logger.debug(f"No matches found for league {league.code}, keeping defaults")
            return False
        
        # Calculate avg_draw_rate
        draws = sum(1 for m in matches if m.result == MatchResult.D)
        league.avg_draw_rate = draws / len(matches) if matches else 0.26
        
        # Calculate home_advantage
        valid_matches = [
            m for m in matches 
            if m.home_goals is not None and m.away_goals is not None
        ]
        
        if valid_matches:
            goal_diffs = [m.home_goals - m.away_goals for m in valid_matches]
            home_advantage = sum(goal_diffs) / len(goal_diffs)
            # Clamp to reasonable range [0.1, 0.6]
            league.home_advantage = max(0.1, min(0.6, home_advantage))
        else:
            league.home_advantage = 0.35  # Default
        
        logger.debug(
            f"League {league.code}: "
            f"draw_rate={league.avg_draw_rate:.3f}, "
            f"home_advantage={league.home_advantage:.3f} "
            f"(from {len(matches)} matches)"
        )
        
        return True
    
    def update_league_by_code(self, league_code: str) -> bool:
        """Update statistics for a league by code"""
        league = self.db.query(League).filter(League.code == league_code).first()
        if not league:
            logger.warning(f"League with code {league_code} not found")
            return False
        
        return self.update_league(league.id)

