"""
Draw Structural Data Validation Module

Provides validation, outlier detection, and consistency checks for draw structural tables.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DrawStructuralValidator:
    """Validator for draw structural data"""
    
    # Validation ranges
    DRAW_RATE_MIN = 0.0
    DRAW_RATE_MAX = 1.0
    ELO_MIN = 500.0
    ELO_MAX = 3000.0
    ELO_MAX_JUMP = 100.0  # Maximum realistic Elo change per day
    WEATHER_INDEX_MIN = 0.5
    WEATHER_INDEX_MAX = 2.0
    SAMPLE_SIZE_MIN = 1
    REST_DAYS_MIN = 0
    REST_DAYS_MAX = 30  # Maximum realistic rest days
    
    @staticmethod
    def validate_draw_rate(draw_rate: float, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate draw rate is within [0.0, 1.0] range.
        
        Args:
            draw_rate: Draw rate value to validate
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        if draw_rate is None:
            return False, f"Draw rate is NULL{context}"
        
        if not isinstance(draw_rate, (int, float)):
            return False, f"Draw rate is not numeric: {type(draw_rate)}{context}"
        
        if draw_rate < DrawStructuralValidator.DRAW_RATE_MIN:
            return False, f"Draw rate below minimum ({DrawStructuralValidator.DRAW_RATE_MIN}): {draw_rate}{context}"
        
        if draw_rate > DrawStructuralValidator.DRAW_RATE_MAX:
            return False, f"Draw rate above maximum ({DrawStructuralValidator.DRAW_RATE_MAX}): {draw_rate}{context}"
        
        return True, None
    
    @staticmethod
    def validate_sample_size(sample_size: int, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate sample size is positive.
        
        Args:
            sample_size: Sample size value to validate
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        if sample_size is None:
            return False, f"Sample size is NULL{context}"
        
        if not isinstance(sample_size, int):
            return False, f"Sample size is not integer: {type(sample_size)}{context}"
        
        if sample_size < DrawStructuralValidator.SAMPLE_SIZE_MIN:
            return False, f"Sample size below minimum ({DrawStructuralValidator.SAMPLE_SIZE_MIN}): {sample_size}{context}"
        
        return True, None
    
    @staticmethod
    def validate_elo_rating(elo_rating: float, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate Elo rating is within reasonable range.
        
        Args:
            elo_rating: Elo rating value to validate
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        if elo_rating is None:
            return False, f"Elo rating is NULL{context}"
        
        if not isinstance(elo_rating, (int, float)):
            return False, f"Elo rating is not numeric: {type(elo_rating)}{context}"
        
        if elo_rating < DrawStructuralValidator.ELO_MIN:
            return False, f"Elo rating below minimum ({DrawStructuralValidator.ELO_MIN}): {elo_rating}{context}"
        
        if elo_rating > DrawStructuralValidator.ELO_MAX:
            return False, f"Elo rating above maximum ({DrawStructuralValidator.ELO_MAX}): {elo_rating}{context}"
        
        return True, None
    
    @staticmethod
    def detect_elo_outlier(
        db: Session,
        team_id: int,
        current_elo: float,
        current_date: date,
        previous_elo: Optional[float] = None
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Detect unrealistic Elo rating jumps.
        
        Args:
            db: Database session
            team_id: Team ID
            current_elo: Current Elo rating
            current_date: Current date
            previous_elo: Previous Elo rating (if known)
        
        Returns:
            (is_outlier, error_message, suggested_value)
        """
        # First validate the Elo rating itself
        is_valid, error = DrawStructuralValidator.validate_elo_rating(current_elo, f" (team_id={team_id})")
        if not is_valid:
            return True, error, None
        
        # If previous Elo is provided, check for jumps
        if previous_elo is not None:
            elo_change = abs(current_elo - previous_elo)
            if elo_change > DrawStructuralValidator.ELO_MAX_JUMP:
                suggested = previous_elo + (DrawStructuralValidator.ELO_MAX_JUMP if current_elo > previous_elo else -DrawStructuralValidator.ELO_MAX_JUMP)
                return True, f"Unrealistic Elo jump: {elo_change:.2f} (team_id={team_id}, date={current_date})", suggested
        
        # Otherwise, try to get previous Elo from database
        try:
            from app.db.models import TeamElo
            previous_record = db.query(TeamElo).filter(
                TeamElo.team_id == team_id,
                TeamElo.date < current_date
            ).order_by(TeamElo.date.desc()).first()
            
            if previous_record:
                elo_change = abs(current_elo - previous_record.elo_rating)
                if elo_change > DrawStructuralValidator.ELO_MAX_JUMP:
                    suggested = previous_record.elo_rating + (DrawStructuralValidator.ELO_MAX_JUMP if current_elo > previous_record.elo_rating else -DrawStructuralValidator.ELO_MAX_JUMP)
                    return True, f"Unrealistic Elo jump: {elo_change:.2f} (team_id={team_id}, date={current_date})", suggested
        except Exception as e:
            logger.warning(f"Could not check previous Elo for outlier detection: {e}")
        
        return False, None, None
    
    @staticmethod
    def validate_weather_index(weather_index: float, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate weather draw index is within reasonable range.
        
        Args:
            weather_index: Weather draw index value to validate
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        if weather_index is None:
            return True, None  # Weather index can be NULL
        
        if not isinstance(weather_index, (int, float)):
            return False, f"Weather index is not numeric: {type(weather_index)}{context}"
        
        if weather_index < DrawStructuralValidator.WEATHER_INDEX_MIN:
            return False, f"Weather index below minimum ({DrawStructuralValidator.WEATHER_INDEX_MIN}): {weather_index}{context}"
        
        if weather_index > DrawStructuralValidator.WEATHER_INDEX_MAX:
            return False, f"Weather index above maximum ({DrawStructuralValidator.WEATHER_INDEX_MAX}): {weather_index}{context}"
        
        return True, None
    
    @staticmethod
    def validate_rest_days(rest_days: int, context: str = "") -> Tuple[bool, Optional[str]]:
        """
        Validate rest days is within reasonable range.
        
        Args:
            rest_days: Rest days value to validate
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        if rest_days is None:
            return False, f"Rest days is NULL{context}"
        
        if not isinstance(rest_days, int):
            return False, f"Rest days is not integer: {type(rest_days)}{context}"
        
        if rest_days < DrawStructuralValidator.REST_DAYS_MIN:
            return False, f"Rest days below minimum ({DrawStructuralValidator.REST_DAYS_MIN}): {rest_days}{context}"
        
        if rest_days > DrawStructuralValidator.REST_DAYS_MAX:
            return False, f"Rest days above maximum ({DrawStructuralValidator.REST_DAYS_MAX}): {rest_days}{context}"
        
        return True, None
    
    @staticmethod
    def validate_h2h_consistency(
        matches_played: int,
        draw_count: int,
        draw_rate: Optional[float] = None,
        context: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate H2H statistics are consistent.
        
        Args:
            matches_played: Number of matches played
            draw_count: Number of draws
            draw_rate: Draw rate (optional, will be calculated if not provided)
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        # Validate matches_played
        if matches_played is None or matches_played < 0:
            return False, f"Invalid matches_played: {matches_played}{context}"
        
        # Validate draw_count
        if draw_count is None or draw_count < 0:
            return False, f"Invalid draw_count: {draw_count}{context}"
        
        # Check draw_count <= matches_played
        if draw_count > matches_played:
            return False, f"draw_count ({draw_count}) > matches_played ({matches_played}){context}"
        
        # Validate draw_rate if provided
        if draw_rate is not None:
            # Calculate expected draw_rate
            if matches_played > 0:
                expected_draw_rate = draw_count / matches_played
                # Allow small floating point differences
                if abs(draw_rate - expected_draw_rate) > 0.01:
                    return False, f"draw_rate ({draw_rate:.4f}) doesn't match draw_count/matches_played ({expected_draw_rate:.4f}){context}"
            else:
                if draw_rate != 0.0:
                    return False, f"draw_rate should be 0.0 when matches_played=0, got {draw_rate}{context}"
        
        return True, None
    
    @staticmethod
    def validate_league_prior_consistency(
        draw_rate: float,
        sample_size: int,
        context: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate league draw prior consistency.
        
        Args:
            draw_rate: Draw rate value
            sample_size: Sample size
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        # Validate draw_rate
        is_valid, error = DrawStructuralValidator.validate_draw_rate(draw_rate, context)
        if not is_valid:
            return False, error
        
        # Validate sample_size
        is_valid, error = DrawStructuralValidator.validate_sample_size(sample_size, context)
        if not is_valid:
            return False, error
        
        # Check if sample_size is too small for reliable draw_rate
        if sample_size < 10:
            logger.warning(f"Small sample size for draw rate: {sample_size}{context}")
        
        return True, None
    
    @staticmethod
    def validate_odds_movement(
        odds_open: Optional[float],
        odds_close: Optional[float],
        odds_delta: Optional[float] = None,
        context: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate odds movement data consistency.
        
        Args:
            odds_open: Opening odds
            odds_close: Closing odds
            odds_delta: Odds delta (optional, will be calculated if not provided)
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        # Validate odds_open
        if odds_open is not None:
            if odds_open <= 1.0:
                return False, f"Invalid odds_open (must be > 1.0): {odds_open}{context}"
        
        # Validate odds_close
        if odds_close is not None:
            if odds_close <= 1.0:
                return False, f"Invalid odds_close (must be > 1.0): {odds_close}{context}"
        
        # Validate odds_delta if provided
        if odds_delta is not None and odds_open is not None and odds_close is not None:
            expected_delta = odds_close - odds_open
            if abs(odds_delta - expected_delta) > 0.01:
                return False, f"odds_delta ({odds_delta:.4f}) doesn't match odds_close - odds_open ({expected_delta:.4f}){context}"
        
        return True, None
    
    @staticmethod
    def validate_xg_data(
        xg_home: Optional[float],
        xg_away: Optional[float],
        context: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate xG data values.
        
        Args:
            xg_home: Home team xG
            xg_away: Away team xG
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message)
        """
        # xG can be NULL (not all matches have xG data)
        if xg_home is None and xg_away is None:
            return True, None
        
        # If one is provided, both should be provided
        if (xg_home is None) != (xg_away is None):
            return False, f"xG data incomplete: xg_home={xg_home}, xg_away={xg_away}{context}"
        
        # Validate ranges (xG is typically 0-5 per team)
        if xg_home is not None:
            if xg_home < 0 or xg_home > 10:
                return False, f"Invalid xg_home (expected 0-10): {xg_home}{context}"
        
        if xg_away is not None:
            if xg_away < 0 or xg_away > 10:
                return False, f"Invalid xg_away (expected 0-10): {xg_away}{context}"
        
        return True, None


def validate_before_insert(
    data_type: str,
    data: Dict[str, Any],
    db: Session,
    context: str = ""
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate data before inserting into draw structural tables.
    
    Args:
        data_type: Type of data ('league_priors', 'h2h_stats', 'elo_rating', etc.)
        data: Dictionary with data to validate
        db: Database session
        context: Context string for error messages
    
    Returns:
        (is_valid, error_message, corrected_data)
    """
    validator = DrawStructuralValidator()
    corrected_data = data.copy()
    
    try:
        if data_type == 'league_priors':
            # Validate draw_rate
            is_valid, error = validator.validate_draw_rate(
                data.get('draw_rate'), context
            )
            if not is_valid:
                return False, error, None
            
            # Validate sample_size
            is_valid, error = validator.validate_sample_size(
                data.get('sample_size'), context
            )
            if not is_valid:
                return False, error, None
            
            # Validate consistency
            is_valid, error = validator.validate_league_prior_consistency(
                data.get('draw_rate'),
                data.get('sample_size'),
                context
            )
            if not is_valid:
                return False, error, None
        
        elif data_type == 'h2h_stats':
            # Validate consistency
            is_valid, error = validator.validate_h2h_consistency(
                data.get('matches_played', 0),
                data.get('draw_count', 0),
                data.get('draw_rate'),
                context
            )
            if not is_valid:
                return False, error, None
        
        elif data_type == 'elo_rating':
            # Validate Elo rating
            is_valid, error = validator.validate_elo_rating(
                data.get('elo_rating'), context
            )
            if not is_valid:
                return False, error, None
            
            # Detect outliers
            is_outlier, outlier_error, suggested_value = validator.detect_elo_outlier(
                db,
                data.get('team_id'),
                data.get('elo_rating'),
                data.get('date'),
                data.get('previous_elo')
            )
            if is_outlier:
                if suggested_value is not None:
                    logger.warning(f"Elo outlier detected, using suggested value: {outlier_error}")
                    corrected_data['elo_rating'] = suggested_value
                else:
                    return False, outlier_error, None
        
        elif data_type == 'weather':
            # Validate weather index
            is_valid, error = validator.validate_weather_index(
                data.get('weather_draw_index'), context
            )
            if not is_valid:
                return False, error, None
        
        elif data_type == 'rest_days':
            # Validate rest days
            is_valid, error = validator.validate_rest_days(
                data.get('rest_days'), context
            )
            if not is_valid:
                return False, error, None
        
        elif data_type == 'odds_movement':
            # Validate odds movement
            is_valid, error = validator.validate_odds_movement(
                data.get('odds_open'),
                data.get('odds_close'),
                data.get('odds_delta'),
                context
            )
            if not is_valid:
                return False, error, None
        
        elif data_type == 'xg_data':
            # Validate xG data
            is_valid, error = validator.validate_xg_data(
                data.get('xg_home'),
                data.get('xg_away'),
                context
            )
            if not is_valid:
                return False, error, None
        
        return True, None, corrected_data
    
    except Exception as e:
        logger.error(f"Validation error for {data_type}: {e}", exc_info=True)
        return False, f"Validation error: {str(e)}", None

