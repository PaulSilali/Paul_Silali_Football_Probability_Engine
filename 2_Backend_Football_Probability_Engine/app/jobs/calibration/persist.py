"""
Persist Calibration
===================

Persists calibration curves to database (versioned, append-only).
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def persist_calibration(engine: Engine, payload: Dict):
    """
    Persist calibration curve to database.
    
    This is append-only - never overwrites existing calibrations.
    
    Args:
        engine: SQLAlchemy engine
        payload: Dictionary with:
            - calibration_id: UUID
            - outcome: 'H', 'D', or 'A'
            - league: League code or None
            - model_version: Model version string
            - created_at: Timestamp
            - valid_from: Timestamp
            - calibration_blob: Pickled IsotonicRegression model
            - samples_used: Integer
            - is_active: Boolean (should be False for new calibrations)
            - notes: Optional string
    """
    query = """
    INSERT INTO probability_calibration (
        calibration_id,
        outcome,
        league,
        model_version,
        created_at,
        valid_from,
        calibration_blob,
        samples_used,
        is_active,
        notes
    )
    VALUES (
        :calibration_id,
        :outcome,
        :league,
        :model_version,
        :created_at,
        :valid_from,
        :calibration_blob,
        :samples_used,
        :is_active,
        :notes
    )
    """
    
    with engine.begin() as conn:
        conn.execute(text(query), payload)
    
    logger.info(f"Persisted calibration: {payload['calibration_id']} (outcome={payload['outcome']}, league={payload['league']})")

