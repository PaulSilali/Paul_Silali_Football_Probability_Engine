"""
Activate Calibration
====================

Safely activates a calibration curve (deactivates previous, activates new).
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


def activate_calibration(engine: Engine, calibration_id: str):
    """
    Activate a calibration curve.
    
    This:
    1. Deactivates existing active calibration for same (outcome, league, model_version)
    2. Activates the specified calibration
    
    This is safe and reversible - just activate a different calibration_id to rollback.
    
    Args:
        engine: SQLAlchemy engine
        calibration_id: UUID of calibration to activate
    """
    # First, get the calibration to find its scope
    get_query = """
    SELECT outcome, league, model_version
    FROM probability_calibration
    WHERE calibration_id = :calibration_id
    """
    
    with engine.begin() as conn:
        result = conn.execute(text(get_query), {"calibration_id": calibration_id})
        row = result.fetchone()
        
        if not row:
            raise ValueError(f"Calibration {calibration_id} not found")
        
        outcome = row.outcome
        league = row.league
        model_version = row.model_version
        
        # Deactivate existing calibration for same scope
        deactivate_query = """
        UPDATE probability_calibration
        SET is_active = FALSE
        WHERE outcome = :outcome
          AND model_version = :model_version
          AND (league = :league OR (league IS NULL AND :league IS NULL))
          AND is_active = TRUE
        """
        
        conn.execute(text(deactivate_query), {
            "outcome": outcome,
            "league": league,
            "model_version": model_version
        })
        
        # Activate new calibration
        activate_query = """
        UPDATE probability_calibration
        SET is_active = TRUE
        WHERE calibration_id = :calibration_id
        """
        
        conn.execute(text(activate_query), {"calibration_id": calibration_id})
    
    logger.info(f"Activated calibration: {calibration_id} (outcome={outcome}, league={league}, model_version={model_version})")


def load_active_calibration(
    engine: Engine,
    outcome: str,
    model_version: str,
    league: Optional[str] = None
) -> Optional[Dict]:
    """
    Load active calibration for a given scope.
    
    Args:
        engine: SQLAlchemy engine
        outcome: 'H', 'D', or 'A'
        model_version: Model version string
        league: League code or None for global
    
    Returns:
        Dictionary with calibration data, or None if not found
    """
    query = """
    SELECT
        calibration_id,
        outcome,
        league,
        model_version,
        created_at,
        valid_from,
        calibration_blob,
        samples_used,
        is_active
    FROM probability_calibration
    WHERE outcome = :outcome
      AND model_version = :model_version
      AND (league = :league OR (league IS NULL AND :league IS NULL))
      AND is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 1
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), {
            "outcome": outcome,
            "model_version": model_version,
            "league": league
        })
        row = result.fetchone()
        
        if row:
            return {
                "calibration_id": str(row.calibration_id),
                "outcome": row.outcome,
                "league": row.league,
                "model_version": row.model_version,
                "created_at": row.created_at,
                "valid_from": row.valid_from,
                "calibration_blob": row.calibration_blob,
                "samples_used": row.samples_used,
                "is_active": row.is_active
            }
    
    return None

