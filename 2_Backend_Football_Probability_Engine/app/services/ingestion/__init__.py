"""
Data ingestion services for draw structural modeling

Each service populates one or more tables with data from external sources.
All services are idempotent and can be run on a schedule (cron/Celery).
"""

__all__ = [
    "ingest_league_draw_priors",
    "ingest_h2h_stats",
    "ingest_elo_ratings",
    "ingest_weather",
    "ingest_referee_stats",
    "ingest_rest_days",
    "ingest_odds_movement",
]

