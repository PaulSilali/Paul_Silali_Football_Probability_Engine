"""
Celery application configuration

For scheduled background tasks (ingestion, training, etc.)
"""
from celery import Celery
from app.config import settings
import os

# Create Celery app
celery_app = Celery(
    "football_probability_engine",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Import tasks (this will register them)
try:
    from app.tasks import draw_ingestion_tasks
except ImportError:
    pass

# Celery Beat schedule (for periodic tasks)
celery_app.conf.beat_schedule = {
    # Example: Ingest league priors daily at 2 AM
    "ingest-league-priors-daily": {
        "task": "app.tasks.draw_ingestion_tasks.task_ingest_league_priors",
        "schedule": 86400.0,  # 24 hours in seconds
        "args": ("E0", "ALL")  # Example: Premier League
    },
    # Add more scheduled tasks as needed
}

