"""
Celery tasks for draw structural data ingestion

These tasks can be scheduled with Celery Beat for automated ingestion.
"""
from celery import Task
from app.db.session import SessionLocal
from app.services.ingestion import (
    ingest_league_draw_priors,
    ingest_h2h_stats,
    ingest_elo_ratings,
    ingest_weather,
    ingest_referee_stats,
    ingest_rest_days,
    ingest_odds_movement
)
import logging

logger = logging.getLogger(__name__)

# Note: This requires Celery to be configured
# If Celery is not available, these can be called directly or via threading


def get_celery_app():
    """Get Celery app instance"""
    try:
        from app.tasks.celery_app import celery_app
        return celery_app
    except ImportError:
        logger.warning("Celery not configured, tasks will run synchronously")
        return None


def task_ingest_league_priors(league_code: str, season: str = "ALL"):
    """
    Background task to ingest league draw priors.
    
    Can be scheduled with Celery Beat:
    @celery_app.task
    def ingest_league_priors_task(league_code: str, season: str = "ALL"):
        db = SessionLocal()
        try:
            from app.services.ingestion.ingest_league_draw_priors import ingest_from_matches_table
            result = ingest_from_matches_table(db, league_code, season)
            return result
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_league_draw_priors import ingest_from_matches_table
        result = ingest_from_matches_table(db, league_code, season)
        return result
    except Exception as e:
        logger.error(f"Error in league priors ingestion task: {e}", exc_info=True)
        raise
    finally:
        db.close()


def task_ingest_h2h_for_fixtures(fixture_ids: list[int], use_api: bool = False):
    """
    Background task to ingest H2H stats for multiple fixtures.
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_h2h_stats import ingest_h2h_from_matches_table
        from app.db.models import JackpotFixture
        
        results = []
        for fixture_id in fixture_ids:
            fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
            if fixture and fixture.home_team_id and fixture.away_team_id:
                result = ingest_h2h_from_matches_table(
                    db, fixture.home_team_id, fixture.away_team_id
                )
                results.append(result)
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error in H2H ingestion task: {e}", exc_info=True)
        raise
    finally:
        db.close()


def task_calculate_elo_for_teams(team_ids: list[int]):
    """
    Background task to calculate Elo ratings for multiple teams.
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_elo_ratings import calculate_elo_from_matches
        
        results = []
        for team_id in team_ids:
            result = calculate_elo_from_matches(db, team_id)
            results.append(result)
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error in Elo calculation task: {e}", exc_info=True)
        raise
    finally:
        db.close()


def task_ingest_weather_for_fixtures(fixture_data: list[dict]):
    """
    Background task to ingest weather for multiple fixtures.
    
    fixture_data: List of {fixture_id, latitude, longitude, match_datetime}
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_weather import ingest_weather_from_open_meteo
        from datetime import datetime
        
        results = []
        for data in fixture_data:
            match_datetime = datetime.fromisoformat(data['match_datetime'])
            result = ingest_weather_from_open_meteo(
                db,
                data['fixture_id'],
                data['latitude'],
                data['longitude'],
                match_datetime
            )
            results.append(result)
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error in weather ingestion task: {e}", exc_info=True)
        raise
    finally:
        db.close()


def task_calculate_rest_days_for_fixtures(fixture_ids: list[int]):
    """
    Background task to calculate rest days for multiple fixtures.
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_rest_days import ingest_rest_days_batch
        
        result = ingest_rest_days_batch(db, fixture_ids)
        return result
    except Exception as e:
        logger.error(f"Error in rest days calculation task: {e}", exc_info=True)
        raise
    finally:
        db.close()


def task_track_odds_movement_for_fixtures(fixture_odds: list[dict]):
    """
    Background task to track odds movement for multiple fixtures.
    
    fixture_odds: List of {fixture_id, draw_odds}
    """
    db = SessionLocal()
    try:
        from app.services.ingestion.ingest_odds_movement import track_odds_movement
        
        results = []
        for data in fixture_odds:
            result = track_odds_movement(db, data['fixture_id'], data.get('draw_odds'))
            results.append(result)
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error in odds movement tracking task: {e}", exc_info=True)
        raise
    finally:
        db.close()


# Example Celery task definitions (uncomment if Celery is configured)
"""
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def ingest_league_priors_async(self, league_code: str, season: str = "ALL"):
    try:
        return task_ingest_league_priors(league_code, season)
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def ingest_h2h_async(self, fixture_ids: list[int], use_api: bool = False):
    try:
        return task_ingest_h2h_for_fixtures(fixture_ids, use_api)
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
"""

