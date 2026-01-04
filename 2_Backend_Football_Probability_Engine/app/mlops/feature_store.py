"""
Redis-based Feature Store for Fast Feature Serving
"""
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SimpleFeatureStore:
    """
    Redis-based feature store for fast feature serving
    
    Features stored as JSON in Redis with TTL
    """
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize feature store
        
        Args:
            redis_client: Redis client instance (creates new if None)
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis is not installed. Feature store will be disabled.")
            self.redis = None
            return
        
        if redis_client:
            self.redis = redis_client
        else:
            # Try to connect to Redis
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()  # Test connection
                logger.info("Connected to Redis feature store")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}. Feature store disabled.")
                self.redis = None
        
        self.prefix = "feature_store:"
    
    def _make_key(self, entity: str, entity_id: int, feature_group: str = "stats") -> str:
        """Generate Redis key for feature"""
        return f"{self.prefix}{entity}:{entity_id}:{feature_group}"
    
    def store_team_features(
        self,
        team_id: int,
        features: Dict[str, float],
        ttl_days: int = 7
    ) -> bool:
        """
        Store team features
        
        Args:
            team_id: Team ID
            features: Dictionary of features
            ttl_days: Time-to-live in days
            
        Returns:
            True if successful
        """
        if not self.redis:
            return False
        
        try:
            key = self._make_key("team", team_id, "stats")
            
            feature_data = {
                "team_id": team_id,
                "features": features,
                "updated_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            self.redis.setex(
                key,
                timedelta(days=ttl_days),
                json.dumps(feature_data)
            )
            logger.debug(f"Stored team features for team_id: {team_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing team features: {e}")
            return False
    
    def get_team_features(self, team_id: int) -> Optional[Dict]:
        """Get team features from cache"""
        if not self.redis:
            return None
        
        try:
            key = self._make_key("team", team_id, "stats")
            data = self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting team features: {e}")
            return None
    
    def store_match_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: str,
        features: Dict[str, float],
        ttl_hours: int = 24
    ) -> bool:
        """Store match-level features"""
        if not self.redis:
            return False
        
        try:
            key = f"{self.prefix}match:{home_team_id}:{away_team_id}:{match_date}"
            
            feature_data = {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date,
                "features": features,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.redis.setex(
                key,
                timedelta(hours=ttl_hours),
                json.dumps(feature_data)
            )
            logger.debug(f"Stored match features for {home_team_id} vs {away_team_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing match features: {e}")
            return False
    
    def get_match_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: str
    ) -> Optional[Dict]:
        """Get match features from cache"""
        if not self.redis:
            return None
        
        try:
            key = f"{self.prefix}match:{home_team_id}:{away_team_id}:{match_date}"
            data = self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting match features: {e}")
            return None
    
    def bulk_store_features(self, features_list: List[Dict]) -> int:
        """
        Bulk store multiple features
        
        Args:
            features_list: List of feature dicts with keys:
                - entity_type: "team" or "match"
                - entity_id: ID of entity
                - features: Dict of features
                - ttl_days: TTL in days
                
        Returns:
            Number of features stored
        """
        if not self.redis:
            return 0
        
        try:
            pipe = self.redis.pipeline()
            stored = 0
            
            for feature_data in features_list:
                entity_type = feature_data.get("entity_type")
                entity_id = feature_data.get("entity_id")
                features = feature_data.get("features", {})
                ttl = feature_data.get("ttl_days", 7)
                
                if entity_type == "team":
                    key = self._make_key("team", entity_id, "stats")
                    pipe.setex(
                        key,
                        timedelta(days=ttl),
                        json.dumps({
                            "team_id": entity_id,
                            "features": features,
                            "updated_at": datetime.utcnow().isoformat()
                        })
                    )
                    stored += 1
            
            pipe.execute()
            logger.info(f"Bulk stored {stored} features")
            return stored
        except Exception as e:
            logger.error(f"Error bulk storing features: {e}")
            return 0
    
    def invalidate_team_features(self, team_id: int) -> bool:
        """Invalidate team features (e.g., after model retraining)"""
        if not self.redis:
            return False
        
        try:
            key = self._make_key("team", team_id, "stats")
            self.redis.delete(key)
            logger.debug(f"Invalidated team features for team_id: {team_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating team features: {e}")
            return False
    
    def get_feature_stats(self) -> Dict:
        """Get statistics about feature store"""
        if not self.redis:
            return {
                "total_features": 0,
                "team_features": 0,
                "match_features": 0,
                "memory_usage_mb": 0,
                "status": "disabled"
            }
        
        try:
            pattern = f"{self.prefix}*"
            keys = self.redis.keys(pattern)
            
            team_keys = [k for k in keys if "team:" in k]
            match_keys = [k for k in keys if "match:" in k]
            
            memory_usage = 0
            for key in keys:
                try:
                    memory_usage += self.redis.memory_usage(key)
                except:
                    pass
            
            return {
                "total_features": len(keys),
                "team_features": len(team_keys),
                "match_features": len(match_keys),
                "memory_usage_mb": round(memory_usage / 1024 / 1024, 2),
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Error getting feature stats: {e}")
            return {
                "total_features": 0,
                "team_features": 0,
                "match_features": 0,
                "memory_usage_mb": 0,
                "status": "error"
            }

