"""
Dashboard API Endpoints
Aggregates data from multiple sources for dashboard display
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.db.session import get_db
from app.db.models import (
    Model, ModelStatus, TrainingRun, Match, League, 
    DataSource, ValidationResult, JackpotFixture, Prediction,
    MatchResult, Jackpot, Ticket, TicketOutcome, DecisionThreshold
)
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard summary
    Combines model status, validation metrics, data freshness, and trends
    """
    try:
        # 1. Get active model status
        poisson_model = db.query(Model).filter(
            Model.model_type == "poisson",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        blending_model = db.query(Model).filter(
            Model.model_type == "blending",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        calibration_model = db.query(Model).filter(
            Model.model_type == "calibration",
            Model.status == ModelStatus.active
        ).order_by(Model.training_completed_at.desc()).first()
        
        # Use calibration model if available, otherwise blending, otherwise poisson
        active_model = calibration_model or blending_model or poisson_model
        
        # 2. Get validation metrics
        validation_metrics = {
            "brierScore": None,
            "logLoss": None,
            "accuracy": None,
            "drawAccuracy": None,
            "totalMatches": 0
        }
        
        if active_model:
            validation_results = db.query(ValidationResult).filter(
                ValidationResult.model_id == active_model.id
            ).all()
            
            if validation_results:
                total_matches = sum(v.total_matches for v in validation_results if v.total_matches)
                total_correct = sum(v.correct_predictions for v in validation_results if v.correct_predictions)
                
                if total_matches > 0:
                    validation_metrics["brierScore"] = sum(
                        v.brier_score * v.total_matches for v in validation_results 
                        if v.brier_score and v.total_matches
                    ) / total_matches
                    validation_metrics["logLoss"] = sum(
                        v.log_loss * v.total_matches for v in validation_results 
                        if v.log_loss and v.total_matches
                    ) / total_matches
                    validation_metrics["accuracy"] = (total_correct / total_matches * 100) if total_correct else 0
                    validation_metrics["totalMatches"] = total_matches
                    
                    # Draw accuracy
                    draw_total = sum(v.draw_total for v in validation_results if v.draw_total)
                    draw_correct = sum(v.draw_correct for v in validation_results if v.draw_correct)
                    if draw_total > 0:
                        validation_metrics["drawAccuracy"] = (draw_correct / draw_total * 100)
            
            # If no validation results, use model metrics
            if not validation_results and active_model:
                validation_metrics["brierScore"] = active_model.brier_score
                validation_metrics["logLoss"] = active_model.log_loss
                validation_metrics["accuracy"] = active_model.overall_accuracy
                validation_metrics["drawAccuracy"] = active_model.draw_accuracy
                validation_metrics["totalMatches"] = active_model.training_matches or 0
        
        # 3. Get data freshness
        data_sources = db.query(DataSource).all()
        data_freshness = []
        for source in data_sources:
            # Determine status based on last_sync_at
            status = "fresh"
            if source.last_sync_at:
                # Ensure both datetimes are timezone-aware
                now = datetime.now(timezone.utc)
                last_sync = source.last_sync_at
                if last_sync.tzinfo is None:
                    # If last_sync_at is naive, assume UTC
                    last_sync = last_sync.replace(tzinfo=timezone.utc)
                hours_since_sync = (now - last_sync).total_seconds() / 3600
                if hours_since_sync > 48:
                    status = "stale"
                elif hours_since_sync > 24:
                    status = "warning"
            elif source.status:
                status = source.status
            
            data_freshness.append({
                "source": source.name,
                "lastUpdated": source.last_sync_at.isoformat() if source.last_sync_at else None,
                "status": status,
                "recordCount": source.record_count or 0
            })
        
        # 4. Get calibration trend (last 5 weeks of training runs)
        calibration_trend = []
        if active_model:
            # Get training runs for this model in last 5 weeks
            now = datetime.now(timezone.utc)
            five_weeks_ago = now - timedelta(weeks=5)
            recent_runs = db.query(TrainingRun).filter(
                TrainingRun.model_id == active_model.id,
                TrainingRun.completed_at >= five_weeks_ago,
                TrainingRun.brier_score.isnot(None)
            ).order_by(TrainingRun.completed_at.asc()).all()
            
            # Group by week
            for i, run in enumerate(recent_runs[-5:]):  # Last 5 runs
                if run.completed_at:
                    completed = run.completed_at
                    if completed.tzinfo is None:
                        completed = completed.replace(tzinfo=timezone.utc)
                    week_num = (now - completed).days // 7
                    week_label = f"W{52 - week_num}" if week_num < 52 else f"W{week_num % 52}"
                    calibration_trend.append({
                        "week": week_label,
                        "brier": float(run.brier_score) if run.brier_score else 0.15
                    })
        
        # 5. Get outcome distribution (from recent predictions with actual results)
        outcome_distribution = []
        if active_model:
            # Get fixtures with actual results
            fixtures_with_results = db.query(JackpotFixture).filter(
                JackpotFixture.actual_result.isnot(None)
            ).limit(1000).all()
            
            if fixtures_with_results:
                # Get predictions for these fixtures (Set B)
                fixture_ids = [f.id for f in fixtures_with_results]
                predictions = db.query(Prediction).filter(
                    Prediction.fixture_id.in_(fixture_ids),
                    Prediction.model_id == active_model.id,
                    Prediction.set_type == "B"
                ).all()
                
                # Calculate predicted vs actual distribution
                predicted_home = 0
                predicted_draw = 0
                predicted_away = 0
                actual_home = 0
                actual_draw = 0
                actual_away = 0
                total = 0
                
                for fixture in fixtures_with_results:
                    prediction = next((p for p in predictions if p.fixture_id == fixture.id), None)
                    if prediction and fixture.actual_result:
                        total += 1
                        # Predicted (highest probability)
                        if prediction.prob_home >= prediction.prob_draw and prediction.prob_home >= prediction.prob_away:
                            predicted_home += 1
                        elif prediction.prob_draw >= prediction.prob_away:
                            predicted_draw += 1
                        else:
                            predicted_away += 1
                        
                        # Actual
                        if fixture.actual_result == MatchResult.H:
                            actual_home += 1
                        elif fixture.actual_result == MatchResult.D:
                            actual_draw += 1
                        else:
                            actual_away += 1
                
                if total > 0:
                    outcome_distribution = [
                        {
                            "name": "Home",
                            "predicted": round((predicted_home / total) * 100, 1),
                            "actual": round((actual_home / total) * 100, 1)
                        },
                        {
                            "name": "Draw",
                            "predicted": round((predicted_draw / total) * 100, 1),
                            "actual": round((actual_draw / total) * 100, 1)
                        },
                        {
                            "name": "Away",
                            "predicted": round((predicted_away / total) * 100, 1),
                            "actual": round((actual_away / total) * 100, 1)
                        }
                    ]
        
        # 6. Get league performance (accuracy by league)
        league_performance = []
        if active_model:
            # Get validation results grouped by league
            # Join through jackpots -> jackpot_fixtures -> leagues
            validation_with_leagues = db.query(
                League.name,
                League.code,
                func.sum(ValidationResult.total_matches).label('total_matches'),
                func.sum(ValidationResult.correct_predictions).label('correct_predictions')
            ).join(
                Jackpot, ValidationResult.jackpot_id == Jackpot.id
            ).join(
                JackpotFixture, JackpotFixture.jackpot_id == Jackpot.id
            ).join(
                League, League.id == JackpotFixture.league_id
            ).filter(
                ValidationResult.model_id == active_model.id,
                ValidationResult.total_matches.isnot(None),
                ValidationResult.correct_predictions.isnot(None)
            ).group_by(
                League.name, League.code
            ).having(
                func.sum(ValidationResult.total_matches) > 0
            ).order_by(
                (func.sum(ValidationResult.correct_predictions) / func.sum(ValidationResult.total_matches)).desc()
            ).limit(10).all()
            
            for league_name, league_code, total, correct in validation_with_leagues:
                accuracy = (correct / total * 100) if total > 0 else 0
                status = "excellent" if accuracy >= 70 else "good" if accuracy >= 65 else "fair"
                league_performance.append({
                    "league": league_name,
                    "accuracy": round(accuracy, 1),
                    "matches": int(total),
                    "status": status
                })
        
        # 7. Get total matches count
        total_matches_count = db.query(func.count(Match.id)).scalar() or 0
        
        # 8. Get league count
        league_count = db.query(func.count(League.id)).filter(League.is_active == True).scalar() or 0
        
        # 9. Get season count (distinct seasons)
        season_count = db.query(func.count(func.distinct(Match.season))).scalar() or 0
        
        # 10. Get Decision Intelligence metrics
        decision_intelligence = {
            "totalTickets": 0,
            "acceptedTickets": 0,
            "rejectedTickets": 0,
            "avgEvScore": None,
            "avgHitRate": None,
            "currentEvThreshold": 0.12,
            "maxContradictions": 1
        }
        
        try:
            # Get ticket counts
            total_tickets = db.query(func.count(Ticket.ticket_id)).scalar() or 0
            accepted_tickets = db.query(func.count(Ticket.ticket_id)).filter(
                Ticket.accepted == True
            ).scalar() or 0
            
            decision_intelligence["totalTickets"] = total_tickets
            decision_intelligence["acceptedTickets"] = accepted_tickets
            decision_intelligence["rejectedTickets"] = total_tickets - accepted_tickets
            
            # Get average EV score for accepted tickets
            avg_ev_result = db.query(func.avg(Ticket.ev_score)).filter(
                Ticket.accepted == True,
                Ticket.ev_score.isnot(None)
            ).scalar()
            if avg_ev_result:
                decision_intelligence["avgEvScore"] = float(avg_ev_result)
            
            # Get average hit rate from outcomes
            avg_hit_rate_result = db.query(func.avg(TicketOutcome.hit_rate)).filter(
                TicketOutcome.hit_rate.isnot(None)
            ).scalar()
            if avg_hit_rate_result:
                decision_intelligence["avgHitRate"] = float(avg_hit_rate_result) * 100  # Convert to percentage
            
            # Get current thresholds
            ev_threshold = db.query(DecisionThreshold).filter(
                DecisionThreshold.threshold_type == "ev_threshold",
                DecisionThreshold.is_active == True
            ).first()
            if ev_threshold:
                decision_intelligence["currentEvThreshold"] = float(ev_threshold.value)
            
            max_contradictions = db.query(DecisionThreshold).filter(
                DecisionThreshold.threshold_type == "max_contradictions",
                DecisionThreshold.is_active == True
            ).first()
            if max_contradictions:
                decision_intelligence["maxContradictions"] = int(max_contradictions.value)
        except Exception as e:
            logger.warning(f"Error fetching decision intelligence metrics: {e}")
        
        return {
            "success": True,
            "data": {
                "systemHealth": {
                    "modelVersion": active_model.version if active_model else "No model",
                    "modelStatus": active_model.status.value if active_model else "no_model",
                    "lastRetrain": active_model.training_completed_at.isoformat() if active_model and active_model.training_completed_at else None,
                    "calibrationScore": validation_metrics["brierScore"],
                    "logLoss": validation_metrics["logLoss"],
                    "totalMatches": validation_metrics["totalMatches"] or total_matches_count,
                    "avgWeeklyAccuracy": validation_metrics["accuracy"],
                    "drawAccuracy": validation_metrics["drawAccuracy"],
                    "leagueCount": league_count,
                    "seasonCount": season_count
                },
                "dataFreshness": data_freshness,
                "calibrationTrend": calibration_trend if calibration_trend else [],
                "outcomeDistribution": outcome_distribution if outcome_distribution else [],
                "leaguePerformance": league_performance if league_performance else [],
                "decisionIntelligence": decision_intelligence
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

