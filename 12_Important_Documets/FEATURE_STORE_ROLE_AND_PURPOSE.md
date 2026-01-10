# Feature Store: Role and Purpose

## Overview

The **Feature Store** is a high-performance caching layer that stores pre-computed features (team strengths, league statistics, and match-level data) for fast access during probability calculations. It acts as a bridge between raw data storage (PostgreSQL) and real-time prediction serving.

---

## 🎯 Primary Roles

### 1. **Performance Optimization**
- **Fast Feature Retrieval**: Stores frequently-used features in Redis for sub-millisecond access
- **Reduces Database Load**: Avoids expensive JOIN queries during prediction time
- **Scalability**: Handles high-volume prediction requests efficiently

### 2. **Team Strength Features Management**
- **Cached Team Strengths**: Stores attack/defense ratings from trained models
- **Rolling Statistics**: Pre-computed metrics (goals scored/conceded, win rates, form)
- **Version Control**: Tracks feature versions for reproducibility

### 3. **League Statistics Aggregation**
- **Baseline Metrics**: League-wide statistics (draw rates, home advantage, avg goals)
- **Seasonal Trends**: Per-season aggregations for context-aware predictions
- **Historical Context**: Enables comparison across leagues and seasons

### 4. **Data Quality Monitoring**
- **Feature Completeness**: Tracks which teams have complete feature sets
- **Data Freshness**: Monitors when features were last updated
- **Quality Indicators**: Flags missing or stale data

---

## 🏗️ Architecture

### **Storage Layers:**

```
┌─────────────────────────────────────────────────────────┐
│              Feature Store (Redis Cache)                │
│  - Fast access (<1ms)                                   │
│  - TTL-based expiration                                 │
│  - In-memory storage                                    │
└─────────────────────────────────────────────────────────┘
                    ▲
                    │ (fallback if cache miss)
                    │
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL Database (Source of Truth)           │
│  - models.model_weights (team strengths)                 │
│  - team_features table (rolling stats)                   │
│  - league_stats table (league aggregations)              │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Components

### **1. Team Strength Features**

**What They Are:**
- **Attack Strength**: Team's offensive capability (normalized, mean = 1.0)
- **Defense Strength**: Team's defensive capability (normalized, mean = 1.0)
- **Home Advantage**: Additional strength when playing at home
- **Model Version**: Which model version calculated these strengths

**Where They Come From:**
- Calculated during **Poisson model training**
- Stored in `models.model_weights['team_strengths']` (JSONB)
- Cached in Redis Feature Store for fast access

**Example:**
```json
{
  "team_id": 123,
  "features": {
    "attack": 1.35,
    "defense": 0.85,
    "home_advantage": 0.35
  },
  "updated_at": "2026-01-09T12:00:00",
  "version": "poisson-20260108-203536"
}
```

**Usage:**
- Used during probability calculation to estimate expected goals
- Enables fast lookups without querying database
- Automatically invalidated when model retrains

---

### **2. League Statistics**

**What They Are:**
- **Draw Rate**: Historical draw probability for the league
- **Home Win Rate**: Baseline home win probability
- **Away Win Rate**: Baseline away win probability
- **Average Goals**: Expected goals per match
- **Home Advantage Factor**: League-specific home advantage

**Where They Come From:**
- Calculated from historical match data
- Stored in `league_stats` table (PostgreSQL)
- Aggregated per league and season

**Example:**
```json
{
  "league_id": 5,
  "season": "2425",
  "draw_rate": 0.28,
  "home_win_rate": 0.45,
  "away_win_rate": 0.27,
  "avg_goals_per_match": 2.65,
  "home_advantage_factor": 0.35
}
```

**Usage:**
- Provides baseline probabilities for draw adjustment
- Used in draw structural signal calculation
- Enables league-specific calibration

---

### **3. Data Quality Monitoring**

**What It Tracks:**

1. **Feature Completeness**
   - Which teams have features available
   - Which teams are missing features
   - Data quality status per team

2. **Data Freshness**
   - When features were last updated
   - TTL expiration status
   - Stale data detection

3. **Feature Store Health**
   - Total features stored
   - Memory usage
   - Redis connection status
   - Cache hit/miss rates

**API Endpoints:**
- `GET /api/feature-store/stats` - Overall statistics
- `GET /api/feature-store/teams/{team_id}` - Team-specific features
- `GET /api/feature-store/teams` - All teams with quality indicators

**Example Response:**
```json
{
  "success": true,
  "teams": [
    {
      "team_id": 123,
      "team_name": "Manchester United",
      "features": {...},
      "updated_at": "2026-01-09T12:00:00",
      "data_quality": "complete"  // or "missing"
    }
  ],
  "total": 24
}
```

---

## 🔄 How It Works

### **Feature Storage Flow:**

```
1. Model Training
   ↓
2. Calculate Team Strengths
   ↓
3. Store in models.model_weights (PostgreSQL)
   ↓
4. Cache in Feature Store (Redis)
   ↓
5. Serve from cache during predictions
```

### **Feature Retrieval Flow:**

```
Prediction Request
   ↓
Check Feature Store (Redis)
   ↓
   ├─ Cache Hit → Use cached features ✅
   │
   └─ Cache Miss → Query Database
                     ↓
                  Store in cache
                     ↓
                  Use features ✅
```

### **Cache Invalidation:**

- **Automatic**: Features expire after TTL (7 days default)
- **Manual**: When model retrains, features are invalidated
- **On-Demand**: API endpoint to invalidate specific team features

---

## 💡 Benefits

### **1. Performance**
- **Sub-millisecond access** vs. database queries (10-50ms)
- **Reduced database load** during high-volume predictions
- **Horizontal scalability** via Redis clustering

### **2. Reliability**
- **Fallback mechanism**: If Redis unavailable, queries database
- **Data consistency**: PostgreSQL remains source of truth
- **Version tracking**: Know which model version generated features

### **3. Monitoring**
- **Data quality visibility**: See which teams have complete features
- **Health checks**: Monitor Feature Store status
- **Usage metrics**: Track feature access patterns

### **4. Development**
- **Fast iteration**: Features pre-computed, ready to use
- **Reproducibility**: Feature versions tracked
- **Testing**: Can mock feature store for unit tests

---

## 🔧 Implementation Details

### **Technology Stack:**
- **Redis**: In-memory cache (optional, gracefully degrades if unavailable)
- **PostgreSQL**: Source of truth for features
- **FastAPI**: REST API endpoints

### **Key Classes:**
- `SimpleFeatureStore`: Main feature store implementation
- `TeamFeature`: Database model for team features
- `LeagueStats`: Database model for league statistics

### **File Locations:**
- **Implementation**: `app/mlops/feature_store.py`
- **API Endpoints**: `app/api/feature_store.py`
- **Database Models**: `app/db/models.py` (TeamFeature, LeagueStats)

---

## 📈 Current Status

### **What's Implemented:**
✅ Redis-based caching layer
✅ Team strength feature storage
✅ League statistics aggregation
✅ Data quality monitoring endpoints
✅ Fallback to database if Redis unavailable
✅ Feature invalidation on model retrain

### **What's Planned (Potential Enhancements):**
- ⏳ Real-time feature computation pipeline
- ⏳ Feature versioning and rollback
- ⏳ Feature lineage tracking
- ⏳ Automated data quality alerts
- ⏳ Feature store metrics dashboard

---

## 🎯 Use Cases

### **1. Probability Calculation**
- Fast lookup of team strengths during prediction
- Access league statistics for draw adjustment
- Check data quality before making predictions

### **2. Model Training**
- Pre-compute features for training dataset
- Cache frequently-used features
- Monitor feature availability

### **3. Data Quality Assurance**
- Identify teams with missing features
- Track feature freshness
- Alert on stale data

### **4. System Monitoring**
- Monitor Feature Store health
- Track cache hit rates
- Monitor memory usage

---

## 🔍 Example Usage

### **During Probability Calculation:**

```python
# 1. Try to get team features from cache
feature_store = SimpleFeatureStore(redis_client)
team_features = feature_store.get_team_features(team_id)

# 2. If cache miss, get from database
if not team_features:
    active_model = db.query(Model).filter(...).first()
    team_strengths = active_model.model_weights.get('team_strengths', {})
    
    # Store in cache for next time
    feature_store.store_team_features(team_id, team_strengths)

# 3. Use features for prediction
attack_strength = team_features['features']['attack']
defense_strength = team_features['features']['defense']
```

### **Data Quality Check:**

```python
# Check which teams have complete features
response = requests.get("/api/feature-store/teams")
teams = response.json()['teams']

complete_teams = [t for t in teams if t['data_quality'] == 'complete']
missing_teams = [t for t in teams if t['data_quality'] == 'missing']

print(f"Complete: {len(complete_teams)}, Missing: {len(missing_teams)}")
```

---

## 📝 Summary

The **Feature Store** serves as a **high-performance caching layer** that:

1. **Stores Team Strength Features** - Pre-computed attack/defense ratings from trained models
2. **Aggregates League Statistics** - League-wide baselines for context-aware predictions
3. **Monitors Data Quality** - Tracks feature completeness and freshness
4. **Optimizes Performance** - Reduces database load and enables fast predictions

It's an **optional but recommended** component that significantly improves system performance and provides valuable data quality insights. If Redis is unavailable, the system gracefully falls back to database queries.

---

**Key Takeaway:** The Feature Store is the **performance optimization layer** that makes real-time probability calculations fast and scalable, while also providing **data quality monitoring** capabilities.

