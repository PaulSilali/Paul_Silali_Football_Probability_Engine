# Automatic Data Download Guide

## Overview

The system automatically downloads and calculates various data features during probability generation. This document explains what data is automatically fetched and when.

---

## ✅ **Automatically Downloaded/Calculated During Probability Generation**

### 1. **Weather Data** 🌤️
- **When**: Automatically fetched if missing during probability calculation
- **Source**: Open-Meteo API (free, no API key needed)
- **What's Downloaded**:
  - Temperature (°C)
  - Rainfall (mm)
  - Wind Speed (km/h)
  - Weather draw index (calculated from conditions)
- **Location**: `app/api/probabilities.py` lines 618-669
- **Fallback**: Uses country capital coordinates if stadium coordinates unavailable
- **Storage**: `match_weather` table

**Example:**
```python
# Auto-ingested if missing
weather_result = ingest_weather_from_open_meteo(
    db=db,
    fixture_id=fixture_id,
    latitude=51.5074,  # London coordinates
    longitude=-0.1278,
    match_datetime=match_datetime
)
```

---

### 2. **Rest Days** ⏰
- **When**: Automatically calculated if missing during probability calculation
- **Source**: Calculated from `matches` table (previous match dates)
- **What's Calculated**:
  - Days between current fixture and team's last match
  - Home team rest days
  - Away team rest days
  - Rest day advantage (difference between teams)
- **Location**: `app/api/probabilities.py` lines 671-711
- **Storage**: `team_rest_days` table
- **Impact**: Adjusts team strengths (optimal: 3-4 days = +2% boost)

**Example:**
```python
# Auto-calculated if missing
rest_days_result = ingest_rest_days_for_fixture(
    db=db,
    fixture_id=fixture_id,
    home_team_id=home_team_id,
    away_team_id=away_team_id
)
```

---

### 3. **Team Form** 📊
- **When**: Automatically calculated on-the-fly during probability calculation
- **Source**: Calculated from `matches` table (last 5 matches)
- **What's Calculated**:
  - Wins, draws, losses (last 5 matches)
  - Goals scored/conceded
  - Points (3*wins + draws)
  - Form rating (normalized 0.0-1.0)
  - Attack form (goals scored per match)
  - Defense form (goals conceded per match, inverted)
- **Location**: `app/api/probabilities.py` lines 566-588
- **Storage**: `team_form` table (cached for performance)
- **Impact**: Adjusts team strengths by ~15% based on recent form

**Example:**
```python
# Calculated on-the-fly
home_form = get_team_form_for_fixture(db, home_team_id, fixture_date)
home_attack_adj, home_defense_adj = adjust_team_strength_with_form(
    base_attack, base_defense, home_form, form_weight=0.15
)
```

---

### 4. **Injuries** 🏥
- **When**: Automatically downloaded if missing AND API key is configured
- **Source**: API-Football (requires API key from RapidAPI)
- **What's Downloaded**:
  - Key players missing
  - Injury severity (0.0-1.0)
  - Squad availability
- **Location**: `app/api/probabilities.py` lines 713-756
- **Storage**: `team_injuries` table
- **Requirement**: `API_FOOTBALL_KEY` must be set in `.env`
- **Impact**: Adjusts team strengths based on missing players

**Example:**
```python
# Auto-downloaded if API key configured
if has_api_key and not injury_exists:
    injury_result = download_injuries_from_api_football(
        db=db,
        fixture_id=fixture_id,
        api_key=api_football_key
    )
```

---

### 5. **Odds Movement** 📈
- **When**: Automatically tracked if missing during probability calculation
- **Source**: Current odds from fixture input
- **What's Tracked**:
  - Current draw odds
  - Opening odds (if available)
  - Odds delta (change from opening)
- **Location**: `app/api/probabilities.py` lines 758-789
- **Storage**: `odds_movement` table
- **Impact**: Used for draw probability adjustments

**Example:**
```python
# Auto-tracked if missing
odds_result = track_odds_movement(
    db=db,
    fixture_id=fixture_id,
    draw_odds=float(fixture_data['odds_draw'])
)
```

---

## ❌ **NOT Automatically Downloaded**

### 1. **xG Data**
- **Status**: Must be ingested separately (OPTIONAL - used for draw structural adjustments only)
- **Required for Probability Calculation**: ❌ No (probabilities work without it)
- **Impact if Missing**: Draw structural adjustments will use fallback values
- **How to Populate**: Use batch ingestion endpoint
- **Endpoint**: `POST /draw-ingestion/xg-data/batch`

### 2. **League Priors**
- **Status**: Must be ingested separately (OPTIONAL - has fallback if missing)
- **Required for Probability Calculation**: ❌ No (system uses default draw rate if missing)
- **Impact if Missing**: Draw prior injection uses default league draw rate (~25%)
- **How to Populate**: Use batch ingestion endpoint
- **Endpoint**: `POST /draw-ingestion/league-priors/batch`
- **Note**: System will still calculate probabilities without league priors, but accuracy may be slightly lower

### 3. **Historical Match Data**
- **Status**: Downloaded during pipeline, not during probability calculation
- **When**: During automated pipeline run (Step 3)
- **Source**: football-data.co.uk API
- **Required for Probability Calculation**: ✅ Yes (needed for model training)

---

## 📋 **Summary Table**

| Feature | Auto-Download? | Source | When | Storage |
|---------|----------------|--------|------|---------|
| **Weather** | ✅ Yes (if missing) | Open-Meteo API | During probability calc | `match_weather` |
| **Rest Days** | ✅ Yes (if missing) | Calculated from matches | During probability calc | `team_rest_days` |
| **Team Form** | ✅ Yes (calculated) | Calculated from matches | During probability calc | `team_form` |
| **Injuries** | ✅ Yes (if API key set) | API-Football | During probability calc | `team_injuries` |
| **Odds Movement** | ✅ Yes (if missing) | Current odds | During probability calc | `odds_movement` |
| **xG Data** | ❌ No | Manual/Batch | Separate ingestion | `match_xg` |
| **League Priors** | ❌ No | Manual/Batch | Separate ingestion | `league_draw_priors` |
| **Historical Matches** | ✅ Yes | football-data.co.uk | Pipeline Step 3 | `matches` |

---

## 🔍 **Why Teams Still Show "Need Training" After Training**

### **The Check Process:**

1. **Gets Active Poisson Model** (lines 54-57):
   ```python
   poisson_model = db.query(Model).filter(
       Model.model_type == "poisson",
       Model.status == ModelStatus.active
   ).order_by(Model.training_completed_at.desc()).first()
   ```

2. **Checks Team Strengths** (lines 71-74):
   ```python
   is_trained = (
       team_id in team_strengths or 
       str(team_id) in team_strengths
   )
   ```

### **Possible Issues:**

1. **Model Not Activated**: New model might not be set as `active` after training ✅ Fixed with `expire_all()`
2. **Session Cache**: Database session might be using cached/old query results ✅ Fixed with `expire_all()`
3. **Team IDs Mismatch**: Team IDs in model might not match database IDs (check logs for team_id resolution)
4. **Model Not Committed**: Training might have failed before model was saved (check training logs)
5. **Teams Not in Training Data**: Teams might exist in DB but weren't included in training matches (need more historical data)

### **Fix Applied:**

- Added `self.db.expire_all()` to refresh session cache
- Added logging to show which model is being checked
- Added logging to show how many teams are in the active model

---

## 🛠️ **Troubleshooting**

### **Check Active Model:**
```sql
SELECT id, version, status, training_completed_at, 
       jsonb_object_keys(model_weights->'team_strengths') as team_ids
FROM models 
WHERE model_type = 'poisson' 
  AND status = 'active'
ORDER BY training_completed_at DESC 
LIMIT 1;
```

### **Check Team Training Status:**
```sql
-- Check if team is in active model
SELECT t.id, t.name, 
       CASE 
         WHEN m.model_weights->'team_strengths'->t.id::text IS NOT NULL 
         THEN 'Trained' 
         ELSE 'Not Trained' 
       END as training_status
FROM teams t
CROSS JOIN (
    SELECT model_weights 
    FROM models 
    WHERE model_type = 'poisson' AND status = 'active'
    ORDER BY training_completed_at DESC 
    LIMIT 1
) m
WHERE t.name IN ('Fortuna Dusseldorf', 'Arminia Bielefeld', ...);
```

---

## 📝 **Notes**

- All automatic downloads happen **during probability calculation**, not during training
- Training uses **historical match data** only (goals, dates, teams)
- Weather, form, rest days are **adjustments** applied to base probabilities
- If API keys are not configured, some features will be skipped (non-blocking)

