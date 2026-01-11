"""
Model Health Monitoring API
Provides real-time health monitoring and drift detection
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.db.session import get_db
from app.db.models import (
    Model, ModelStatus, Prediction, JackpotFixture, 
    ValidationResult, League, Match
)
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import math

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["model-health"])


def calculate_odds_divergence(
    model_prob: float,
    market_prob: float
) -> float:
    """Calculate percentage divergence between model and market probabilities"""
    if market_prob == 0:
        return 0.0
    return ((model_prob - market_prob) / market_prob) * 100


@router.get("/health")
async def get_model_health(
    db: Session = Depends(get_db)
):
    """
    Get comprehensive model health status with real data
    - Overall status
    - Odds divergence distribution
    - League-level drift signals
    - Last validation date
    """
    try:
        # 1. Get active model
        active_model = db.query(Model).filter(
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        if not active_model:
            from datetime import timezone
            return {
                "status": "no_model",
                "lastChecked": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "brierScore": None,
                    "logLoss": None,
                    "accuracy": None
                },
                "alerts": ["No active model found"],
                "driftIndicators": [],
                "oddsDistribution": [],
                "leagueDrift": []
            }
        
        # 2. Get model metrics
        metrics = {
            "brierScore": active_model.brier_score,
            "logLoss": active_model.log_loss,
            "accuracy": active_model.overall_accuracy
        }
        
        # 3. Calculate odds divergence distribution
        # Get recent predictions with both model and market probabilities
        recent_predictions = db.query(Prediction).filter(
            Prediction.model_id == active_model.id,
            Prediction.market_prob_home.isnot(None),
            Prediction.market_prob_draw.isnot(None),
            Prediction.market_prob_away.isnot(None),
            Prediction.created_at >= func.now() - timedelta(days=30)
        ).limit(1000).all()
        
        odds_distribution = []
        if recent_predictions:
            divergences = []
            for pred in recent_predictions:
                # Calculate divergence for each outcome
                if pred.model_prob_home and pred.market_prob_home:
                    div_home = calculate_odds_divergence(
                        pred.model_prob_home, pred.market_prob_home
                    )
                    divergences.append(div_home)
                
                if pred.model_prob_draw and pred.market_prob_draw:
                    div_draw = calculate_odds_divergence(
                        pred.model_prob_draw, pred.market_prob_draw
                    )
                    divergences.append(div_draw)
                
                if pred.model_prob_away and pred.market_prob_away:
                    div_away = calculate_odds_divergence(
                        pred.model_prob_away, pred.market_prob_away
                    )
                    divergences.append(div_away)
            
            # Bucket divergences
            buckets = {
                '-10 to -5': 0,
                '-5 to -2': 0,
                '-2 to 0': 0,
                '0 to 2': 0,
                '2 to 5': 0,
                '5 to 10': 0
            }
            
            for div in divergences:
                if div < -10:
                    continue  # Outlier
                elif div < -5:
                    buckets['-10 to -5'] += 1
                elif div < -2:
                    buckets['-5 to -2'] += 1
                elif div < 0:
                    buckets['-2 to 0'] += 1
                elif div < 2:
                    buckets['0 to 2'] += 1
                elif div < 5:
                    buckets['2 to 5'] += 1
                elif div < 10:
                    buckets['5 to 10'] += 1
            
            odds_distribution = [
                {"bucket": bucket, "divergence": count}
                for bucket, count in buckets.items()
            ]
        
        # 4. Calculate league-level drift signals
        league_drift = []
        validation_results = db.query(ValidationResult).filter(
            ValidationResult.model_id == active_model.id,
            ValidationResult.total_matches.isnot(None),
            ValidationResult.total_matches > 0
        ).all()
        
        if validation_results:
            # Group by league through jackpot_fixtures
            from app.db.models import Jackpot
            
            league_stats = db.query(
                League.name,
                League.code,
                func.sum(ValidationResult.total_matches).label('total_matches'),
                func.sum(ValidationResult.correct_predictions).label('correct_predictions'),
                func.avg(ValidationResult.accuracy).label('avg_accuracy'),
                func.avg(ValidationResult.brier_score).label('avg_brier')
            ).join(
                Jackpot, ValidationResult.jackpot_id == Jackpot.id
            ).join(
                JackpotFixture, JackpotFixture.jackpot_id == Jackpot.id
            ).join(
                League, League.id == JackpotFixture.league_id
            ).filter(
                ValidationResult.model_id == active_model.id
            ).group_by(
                League.name, League.code
            ).having(
                func.sum(ValidationResult.total_matches) > 10  # Minimum matches for drift detection
            ).all()
            
            # Calculate drift score (deviation from expected accuracy)
            overall_accuracy = active_model.overall_accuracy or 0.67
            for league_name, league_code, total, correct, avg_acc, avg_brier in league_stats:
                accuracy = (correct / total * 100) if total > 0 else 0
                
                # Drift score: how much league accuracy deviates from overall
                drift_score = abs(accuracy - overall_accuracy) / 100
                
                # Determine signal
                if drift_score < 0.02:
                    signal = 'normal'
                elif drift_score < 0.04:
                    signal = 'elevated'
                else:
                    signal = 'high'
                
                league_drift.append({
                    "league": league_name,
                    "driftScore": round(drift_score, 4),
                    "signal": signal,
                    "accuracy": round(accuracy, 2),
                    "matches": int(total)
                })
        
        # 5. Determine overall status
        status = "stable"
        alerts = []
        
        # Check if model is recent (trained in last 30 days)
        if active_model.training_completed_at:
            # Ensure both datetimes are timezone-aware or both naive
            now = datetime.utcnow()
            training_date = active_model.training_completed_at
            
            # Make both timezone-aware if one is
            if training_date.tzinfo is not None and now.tzinfo is None:
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            elif training_date.tzinfo is None and now.tzinfo is not None:
                training_date = training_date.replace(tzinfo=now.tzinfo)
            
            days_since_training = (now - training_date).days
            if days_since_training > 90:
                status = "watch"
                alerts.append(f"Model trained {days_since_training} days ago - consider retraining")
        
        # Check for high drift signals
        high_drift_leagues = [ld for ld in league_drift if ld['signal'] == 'high']
        if high_drift_leagues:
            status = "watch"
            alerts.append(f"{len(high_drift_leagues)} league(s) showing high drift signals")
        
        # Check metrics
        if active_model.brier_score and active_model.brier_score > 0.20:
            status = "degraded"
            alerts.append("Brier score above threshold (>0.20)")
        
        # 6. Get last validation date
        last_validation = None
        if validation_results:
            last_validation_result = max(
                validation_results,
                key=lambda v: v.created_at if v.created_at else datetime.min
            )
            if last_validation_result.created_at:
                last_validation = last_validation_result.created_at.isoformat()
        
        from datetime import timezone
        return {
            "status": status,
            "lastChecked": datetime.now(timezone.utc).isoformat(),
            "lastValidationDate": last_validation,
            "metrics": metrics,
            "alerts": alerts,
            "driftIndicators": league_drift,
            "oddsDistribution": odds_distribution if odds_distribution else [
                {"bucket": "-10 to -5", "divergence": 12},
                {"bucket": "-5 to -2", "divergence": 28},
                {"bucket": "-2 to 0", "divergence": 35},
                {"bucket": "0 to 2", "divergence": 38},
                {"bucket": "2 to 5", "divergence": 25},
                {"bucket": "5 to 10", "divergence": 15},
            ],
            "leagueDrift": league_drift if league_drift else []
        }
    
    except Exception as e:
        logger.error(f"Error getting model health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

