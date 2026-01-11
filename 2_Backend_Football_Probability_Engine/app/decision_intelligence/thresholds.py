"""
Threshold Learning Module
==========================

Learns optimal thresholds from historical ticket outcomes.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Optional
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_thresholds(db: Session) -> Dict[str, float]:
    """
    Load active thresholds from database.
    
    Returns:
        Dictionary of threshold_type -> value
    """
    try:
        result = db.execute(text("""
            SELECT threshold_type, value
            FROM decision_thresholds
            WHERE is_active = TRUE
        """))
        
        thresholds = {}
        for row in result:
            thresholds[row.threshold_type] = float(row.value)
        
        # Set defaults if not found
        defaults = {
            'ev_threshold': 0.12,
            'max_contradictions': 1,
            'entropy_penalty': 0.05,
            'contradiction_penalty': 10.0
        }
        
        for key, default_value in defaults.items():
            if key not in thresholds:
                thresholds[key] = default_value
        
        return thresholds
    except Exception as e:
        logger.warning(f"Could not load thresholds from DB: {e}, using defaults")
        return {
            'ev_threshold': 0.12,
            'max_contradictions': 1,
            'entropy_penalty': 0.05,
            'contradiction_penalty': 10.0
        }


def learn_ev_threshold(db: Session, min_samples: int = 100) -> Optional[float]:
    """
    Learn optimal EV threshold from historical ticket outcomes.
    
    Groups tickets by EV score buckets and finds threshold that maximizes
    conditional accuracy.
    
    Args:
        db: Database session
        min_samples: Minimum samples per bucket to consider
    
    Returns:
        Optimal EV threshold, or None if insufficient data
    """
    try:
        # Get tickets with outcomes
        result = db.execute(text("""
            SELECT 
                FLOOR(t.ev_score * 10) / 10 AS ev_bucket,
                COUNT(*) as sample_count,
                AVG(to_outcome.hit_rate) as avg_hit_rate
            FROM ticket t
            JOIN ticket_outcome to_outcome ON t.ticket_id = to_outcome.ticket_id
            WHERE t.ev_score IS NOT NULL
                AND to_outcome.total_picks > 0
            GROUP BY ev_bucket
            HAVING COUNT(*) >= :min_samples
            ORDER BY ev_bucket DESC
        """), {'min_samples': min_samples})
        
        buckets = {}
        for row in result:
            buckets[float(row.ev_bucket)] = {
                'samples': int(row.sample_count),
                'hit_rate': float(row.avg_hit_rate)
            }
        
        if not buckets:
            logger.warning("Insufficient data for threshold learning")
            return None
        
        # Find threshold that maximizes hit rate while maintaining minimum samples
        best_threshold = None
        best_hit_rate = 0.0
        
        for threshold in sorted(buckets.keys(), reverse=True):
            # Calculate weighted hit rate for tickets above threshold
            total_samples = sum(
                buckets[t]['samples'] 
                for t in buckets.keys() 
                if t >= threshold
            )
            
            if total_samples >= min_samples:
                weighted_hit_rate = sum(
                    buckets[t]['hit_rate'] * buckets[t]['samples']
                    for t in buckets.keys()
                    if t >= threshold
                ) / total_samples
                
                if weighted_hit_rate > best_hit_rate:
                    best_hit_rate = weighted_hit_rate
                    best_threshold = threshold
        
        return best_threshold
        
    except Exception as e:
        logger.error(f"Error learning EV threshold: {e}", exc_info=True)
        return None


def update_thresholds(db: Session, thresholds: Dict[str, float], learned_from_samples: int = 0):
    """
    Update thresholds in database.
    
    Args:
        db: Database session
        thresholds: Dictionary of threshold_type -> value
        learned_from_samples: Number of samples used for learning
    """
    try:
        for threshold_type, value in thresholds.items():
            db.execute(text("""
                INSERT INTO decision_thresholds (threshold_type, value, learned_from_samples, is_active)
                VALUES (:type, :value, :samples, TRUE)
                ON CONFLICT (threshold_type) 
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    learned_from_samples = EXCLUDED.learned_from_samples,
                    learned_at = NOW(),
                    is_active = TRUE
            """), {
                'type': threshold_type,
                'value': value,
                'samples': learned_from_samples
            })
        
        db.commit()
        logger.info(f"Updated thresholds: {thresholds}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating thresholds: {e}", exc_info=True)
        raise


def bootstrap_thresholds_from_backup(db: Session, backup_data_path: Optional[str] = None):
    """
    Bootstrap thresholds from backup_1.zip data.
    
    This is a one-time operation to learn initial thresholds from historical data.
    
    Args:
        db: Database session
        backup_data_path: Path to backup data (optional, will use DB if not provided)
    """
    try:
        # Try to learn from existing ticket_outcome data
        learned_threshold = learn_ev_threshold(db, min_samples=50)
        
        if learned_threshold:
            thresholds = {
                'ev_threshold': learned_threshold,
                'max_contradictions': 1,  # Keep conservative
                'entropy_penalty': 0.05,
                'contradiction_penalty': 10.0
            }
            
            # Count samples used
            result = db.execute(text("""
                SELECT COUNT(*) 
                FROM ticket_outcome
            """))
            samples = result.scalar() or 0
            
            update_thresholds(db, thresholds, learned_from_samples=samples)
            logger.info(f"Bootstrapped thresholds from {samples} samples")
        else:
            logger.warning("Could not bootstrap thresholds - using defaults")
            
    except Exception as e:
        logger.error(f"Error bootstrapping thresholds: {e}", exc_info=True)

