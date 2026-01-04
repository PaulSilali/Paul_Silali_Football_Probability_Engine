"""
Feature Store API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Model, Team
from app.mlops.feature_store import SimpleFeatureStore
import os
from typing import Dict, List, Optional
import logging

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feature-store", tags=["feature-store"])


def get_feature_store() -> Optional[SimpleFeatureStore]:
    """Get feature store instance"""
    if not REDIS_AVAILABLE:
        logger.warning("Redis is not installed. Feature store unavailable.")
        return None
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        return SimpleFeatureStore(redis_client)
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")
        return None


@router.get("/stats")
async def get_feature_store_stats():
    """Get feature store statistics"""
    feature_store = get_feature_store()
    if not feature_store:
        return {
            "success": False,
            "message": "Feature store not available (Redis not connected)",
            "stats": {
                "status": "disabled",
                "total_features": 0,
                "team_features": 0,
                "match_features": 0,
                "memory_usage_mb": 0
            }
        }
    
    stats = feature_store.get_feature_stats()
    return {
        "success": True,
        "stats": stats
    }


@router.get("/teams/{team_id}")
async def get_team_features(team_id: int):
    """Get features for a specific team"""
    feature_store = get_feature_store()
    if not feature_store:
        raise HTTPException(status_code=503, detail="Feature store not available")
    
    features = feature_store.get_team_features(team_id)
    if not features:
        raise HTTPException(status_code=404, detail="Team features not found")
    
    return {
        "success": True,
        "team_id": team_id,
        "features": features
    }


@router.get("/teams")
async def get_all_team_features(
    league: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get features for all teams (optionally filtered by league)"""
    feature_store = get_feature_store()
    
    # Get teams from database
    query = db.query(Team)
    if league:
        query = query.filter(Team.league == league)
    teams = query.all()
    
    # Get features from feature store
    team_features_list = []
    for team in teams:
        if feature_store:
            features = feature_store.get_team_features(team.id)
            if features:
                team_features_list.append({
                    "team_id": team.id,
                    "team_name": team.name,
                    "league": team.league,
                    "features": features.get("features", {}),
                    "updated_at": features.get("updated_at"),
                    "data_quality": "complete" if features else "missing"
                })
        else:
            # Fallback: get from model weights if available
            active_model = db.query(Model).filter(
                Model.status == "active",
                Model.model_type == "poisson"
            ).order_by(Model.training_completed_at.desc()).first()
            
            if active_model and active_model.model_weights:
                team_strengths = active_model.model_weights.get("team_strengths", {})
                if str(team.id) in team_strengths:
                    strength = team_strengths[str(team.id)]
                    team_features_list.append({
                        "team_id": team.id,
                        "team_name": team.name,
                        "league": team.league,
                        "features": {
                            "attack": strength.get("attack", 1.0),
                            "defense": strength.get("defense", 1.0)
                        },
                        "updated_at": active_model.training_completed_at.isoformat() if active_model.training_completed_at else None,
                        "data_quality": "complete"
                    })
    
    return {
        "success": True,
        "teams": team_features_list,
        "total": len(team_features_list)
    }

