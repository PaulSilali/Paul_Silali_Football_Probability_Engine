"""
Load Calibration Dataset
========================

Loads calibration dataset from prediction_snapshot and jackpot_fixtures.
Falls back to saved_probability_results if prediction_snapshot is empty.
"""
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_calibration_dataset(
    engine: Engine,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_samples: int = 200,
    league: Optional[str] = None
) -> pd.DataFrame:
    """
    Load calibration dataset from database.
    
    First tries the calibration_dataset view (prediction_snapshot + jackpot_fixtures).
    If that's empty, falls back to saved_probability_results by:
    1. Loading saved results with actual_results
    2. Recalculating probabilities for those jackpots
    3. Matching probabilities with actual results
    
    Args:
        engine: SQLAlchemy engine
        start_date: Filter by created_at >= start_date
        end_date: Filter by created_at <= end_date
        min_samples: Minimum samples required
        league: Filter by league code (optional)
    
    Returns:
        DataFrame with columns:
        - fixture_id, created_at, league, model_version
        - prob_home, prob_draw, prob_away
        - actual_result, y_home, y_draw, y_away
        - odds_home, odds_draw, odds_away (if available)
    
    Raises:
        RuntimeError: If insufficient samples
    """
    # First, try prediction_snapshot (calibration_dataset view)
    query = """
    SELECT
        fixture_id,
        created_at,
        league,
        model_version,
        prob_home,
        prob_draw,
        prob_away,
        actual_result,
        y_home,
        y_draw,
        y_away,
        odds_home,
        odds_draw,
        odds_away,
        market_disagreement_home,
        market_disagreement_draw,
        market_disagreement_away
    FROM calibration_dataset
    WHERE 1=1
    """
    
    params = {}
    
    if start_date:
        query += " AND created_at >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND created_at <= :end_date"
        params["end_date"] = end_date
    
    if league:
        query += " AND league = :league"
        params["league"] = league
    
    query += " ORDER BY created_at DESC"
    
    logger.info(f"Loading calibration dataset (league={league}, start_date={start_date}, end_date={end_date})")
    
    df = pd.read_sql(text(query), engine, params=params)
    
    # If prediction_snapshot is empty, fall back to saved_probability_results
    if len(df) < min_samples:
        logger.info(f"prediction_snapshot has {len(df)} samples, falling back to saved_probability_results")
        df = _load_from_saved_results(engine, start_date, end_date, league)
    
    if len(df) < min_samples:
        # Check if saved_probability_results has data
        check_saved_query = """
        SELECT COUNT(*) as count
        FROM saved_probability_results
        WHERE actual_results IS NOT NULL
          AND jsonb_typeof(actual_results::jsonb) = 'object'
        """
        saved_count = pd.read_sql(text(check_saved_query), engine).iloc[0]['count']
        
        if saved_count > 0:
            raise RuntimeError(
                f"Insufficient calibration samples: {len(df)} < {min_samples}. "
                f"Found {saved_count} saved results with actual outcomes. "
                f"Please export validation results to training first using the 'Export Validation Data to Training' button on the Validation page. "
                f"This will populate the calibration dataset with your validated predictions."
            )
        else:
            raise RuntimeError(
                f"Insufficient calibration samples: {len(df)} < {min_samples}. "
                f"Need at least {min_samples} samples with actual results. "
                f"Please: 1) Import jackpot results with actual outcomes, 2) Compute probabilities, 3) Export validation results to training."
            )
    
    logger.info(f"Loaded {len(df)} calibration samples")
    
    # Validate data
    required_cols = ['prob_home', 'prob_draw', 'prob_away', 'y_home', 'y_draw', 'y_away']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    return df


def _load_from_saved_results(
    engine: Engine,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    league: Optional[str] = None
) -> pd.DataFrame:
    """
    Load calibration data from saved_probability_results.
    
    This extracts probabilities from saved results by:
    1. Loading saved results with actual_results
    2. Getting jackpot fixtures
    3. Recalculating probabilities (or using stored probabilities if available)
    4. Matching with actual results
    
    Note: This requires recalculating probabilities, which may be slow.
    """
    logger.info("Loading calibration data from saved_probability_results")
    
    # Query saved results with actual_results
    # Note: jackpots table doesn't have league_code, we'll get league from fixtures if needed
    query = """
    SELECT DISTINCT
        spr.id AS saved_result_id,
        spr.jackpot_id,
        spr.actual_results,
        spr.selections,
        spr.model_version,
        spr.created_at,
        j.kickoff_date
    FROM saved_probability_results spr
    JOIN jackpots j ON spr.jackpot_id = j.jackpot_id
    WHERE spr.actual_results IS NOT NULL
      AND jsonb_typeof(spr.actual_results::jsonb) = 'object'
      AND jsonb_object_keys(spr.actual_results::jsonb) IS NOT NULL
    """
    
    params = {}
    
    if start_date:
        query += " AND spr.created_at >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND spr.created_at <= :end_date"
        params["end_date"] = end_date
    
    # League filtering would need to join with jackpot_fixtures, skip for now
    # if league:
    #     query += " AND EXISTS (SELECT 1 FROM jackpot_fixtures jf JOIN teams t ON jf.home_team_id = t.id JOIN leagues l ON t.league_id = l.id WHERE jf.jackpot_id = j.id AND l.code = :league)"
    #     params["league"] = league
    
    query += " ORDER BY spr.created_at DESC"
    
    saved_results = pd.read_sql(text(query), engine, params=params)
    
    if len(saved_results) == 0:
        logger.warning("No saved results with actual_results found")
        return pd.DataFrame()
    
    logger.info(f"Found {len(saved_results)} saved results with actual_results")
    
    # For each saved result, we need to:
    # 1. Get fixtures for the jackpot
    # 2. Recalculate probabilities (or extract from stored data)
    # 3. Match with actual_results
    
    # This is complex - we'll use a simpler approach:
    # Extract probabilities from the probability calculations that were done
    # when the results were saved. We'll need to recalculate them.
    
    # For now, return empty DataFrame - the caller should use train_calibration_from_validation
    # which already handles this properly
    logger.warning(
        "saved_probability_results found but calibration_dataset is empty. "
        "Please export validation results to training first using the validation export feature, "
        "or use the train_calibration_from_validation endpoint which handles saved results properly."
    )
    
    return pd.DataFrame()

