# Strategy Implementation Status

## Overview of Model Training Strategies

This document tracks which strategies from "How to Increase Ticket Probabilities" are implemented and what can be added.

---

## Strategy A: More Historical Data

### ✅ **IMPLEMENTED**

**Status:** Fully implemented and working

**What's Implemented:**
- Downloads up to **7 seasons** by default (configurable via `max_seasons`)
- Pipeline automatically downloads missing historical data
- Data is **added** to existing dataset (doesn't replace)
- Configurable: Can download 5, 7, 10, or more seasons

**Code Location:**
- `app/services/automated_pipeline.py` → `download_missing_team_data()` (lines 110-204)
- `app/services/data_ingestion.py` → `ingest_from_football_data()` (lines 688-730)

**How It Works:**
```python
# Default: 7 seasons
max_seasons: int = 7

# Downloads last 7 seasons:
# ['2526', '2425', '2324', '2223', '2122', '2021', '1920']
```

**Impact:** ✅ +5-10% accuracy per match (as data accumulates)

---

## Strategy B: Recent Data Focus

### ⚠️ **PARTIALLY IMPLEMENTED**

**Status:** Feature exists but not easily configurable

**What's Implemented:**
- `base_model_window_years` parameter exists (default: 4 years)
- Can filter training data by date window
- Configurable in model training API

**What's Missing:**
- Not exposed in automated pipeline (always uses default 4 years)
- Not easily configurable from frontend
- No easy way to set to 2-3 years for recent data focus

**Code Location:**
- `app/services/model_training.py` → `train_poisson_model()` (lines 157, 218-221)

**Current Behavior:**
```python
# Default: 4 years
base_model_window_years = 4.0

# Can be changed manually, but not in automated pipeline
```

**What Can Be Implemented:**
- Add `recent_data_window_years` parameter to automated pipeline
- Allow configuration: 2, 3, or 4 years
- Expose in frontend/API for easy configuration

**Impact:** ⚠️ +3-5% accuracy per match (if configured to 2-3 years)

---

## Strategy C: League-Specific Training

### ✅ **IMPLEMENTED** (But NOT Separate Models Per League)

**Status:** Implemented as **filtered training**, not separate models

**What's Implemented:**
- Can filter training data by specific leagues
- Trains **ONE model** on filtered data
- Example: Train on `['SP1', 'E0']` only

**How It Works:**
```python
# Train model on specific leagues
train_poisson_model(leagues=['SP1', 'E0'])

# This:
# 1. Filters matches WHERE league_code IN ('SP1', 'E0')
# 2. Trains ONE model on filtered data
# 3. Model learns team strengths from these leagues only
```

**What It Does NOT Do:**
- ❌ Does NOT create separate models per league
- ❌ Does NOT train 42 models for 42 leagues
- ❌ Does NOT store league-specific model parameters

**What It Does:**
- ✅ Filters training data by league codes
- ✅ Trains one unified model on filtered data
- ✅ Better team strength estimates for those leagues

**Code Location:**
- `app/services/model_training.py` → `train_poisson_model()` (lines 152, 208-209)
- `app/services/automated_pipeline.py` → Uses league codes from teams (lines 414-422)

**Example:**
```python
# Automated pipeline automatically uses league codes from teams
league_codes = ['SP1']  # From teams in jackpot
train_poisson_model(leagues=league_codes)  # Trains on SP1 only
```

**Impact:** ✅ +5-8% accuracy per match (when training on relevant leagues)

**Answer to Your Question:**
> "For league-specific training, does it mean we'll have one model per league (e.g., 42 leagues = 42 models)?"

**NO** - It means:
- **ONE model** trained on **filtered data** from specific leagues
- You can train on `['SP1']` or `['SP1', 'E0']` or all leagues
- Model learns team strengths from those leagues
- **Not** 42 separate models

**Why This Approach:**
- ✅ Simpler: One model to manage
- ✅ Efficient: Shared learning across leagues
- ✅ Flexible: Can train on any combination of leagues
- ✅ Better: More data = better estimates (if leagues are similar)

---

## Strategy D: Team-Specific Features

### ⚠️ **PARTIALLY IMPLEMENTED**

**Status:** Rest days implemented, but form/injuries not implemented

### D1. Rest Days ✅ **IMPLEMENTED**

**What's Implemented:**
- `TeamRestDays` table stores rest days for fixtures
- `TeamRestDaysHistorical` table stores rest days for historical matches
- Rest days calculation and ingestion scripts
- Rest days are **stored** in database

**What's Missing:**
- Rest days are **NOT used** in probability calculations yet
- Rest days are **NOT used** in model training
- Only stored for future use

**Code Location:**
- `app/services/ingestion/ingest_rest_days.py` (full implementation)
- `app/db/models.py` → `TeamRestDays` model (lines 713-732)

**Impact:** ⚠️ +2-5% accuracy (if used in calculations - currently NOT used)

### D2. Team Form ❌ **NOT IMPLEMENTED**

**What's Missing:**
- No recent form calculation (last 5 matches, etc.)
- No form-based adjustments to probabilities
- No form tracking in database

**What Can Be Implemented:**
- Calculate recent form (last 5-10 matches)
- Store form metrics (wins, draws, losses, goals scored/conceded)
- Use form in probability adjustments
- Weight recent matches more heavily

**Impact:** +2-5% accuracy per match (if implemented)

### D3. Injuries ❌ **NOT IMPLEMENTED**

**What's Missing:**
- No injury tracking
- No squad availability data
- No injury-based adjustments

**What Can Be Implemented:**
- Track key player injuries
- Store squad availability
- Adjust team strengths based on missing players
- Use injury data in probability calculations

**Impact:** +1-3% accuracy per match (if implemented)

---

## Summary Table

| Strategy | Status | Implementation | Impact | Notes |
|----------|--------|---------------|--------|-------|
| **A. More Historical Data** | ✅ **IMPLEMENTED** | Downloads up to 7 seasons | +5-10% | Fully working |
| **B. Recent Data Focus** | ⚠️ **PARTIAL** | Window exists (4 years default) | +3-5% | Not configurable in pipeline |
| **C. League-Specific Training** | ✅ **IMPLEMENTED** | Filters by leagues (ONE model) | +5-8% | Not separate models per league |
| **D1. Rest Days** | ⚠️ **STORED ONLY** | Data stored, not used | +2-5% | Need to integrate into calculations |
| **D2. Team Form** | ❌ **NOT IMPLEMENTED** | No form tracking | +2-5% | Can be added |
| **D3. Injuries** | ❌ **NOT IMPLEMENTED** | No injury tracking | +1-3% | Can be added |

---

## What Can Be Implemented

### Quick Wins (Easy to Add)

#### 1. **Recent Data Focus Configuration**
- Add `recent_data_window_years` parameter to automated pipeline
- Allow 2, 3, or 4 years configuration
- Expose in frontend/API

**Effort:** Low (1-2 hours)
**Impact:** +3-5% accuracy

#### 2. **Use Rest Days in Calculations**
- Integrate rest days into probability calculations
- Adjust team strengths based on rest days
- Use in draw probability adjustments

**Effort:** Medium (4-6 hours)
**Impact:** +2-5% accuracy

### Medium-Term (Moderate Effort)

#### 3. **Team Form Calculation**
- Calculate recent form (last 5-10 matches)
- Store form metrics in database
- Use form to adjust probabilities

**Effort:** Medium (6-8 hours)
**Impact:** +2-5% accuracy

#### 4. **League-Specific Model Parameters**
- Store league-specific home advantage
- Store league-specific draw rates
- Use in probability calculations

**Effort:** Medium (4-6 hours)
**Impact:** +3-5% accuracy

### Long-Term (Significant Effort)

#### 5. **Injury Tracking**
- Build injury data ingestion
- Track key player availability
- Adjust team strengths based on injuries

**Effort:** High (10-15 hours)
**Impact:** +1-3% accuracy

#### 6. **Separate Models Per League**
- Train individual models for each league
- Store 42 separate models
- Route predictions to correct model

**Effort:** Very High (20-30 hours)
**Impact:** +5-10% accuracy (but complex to maintain)

---

## Recommendations

### Priority 1: Quick Wins
1. ✅ **Recent Data Focus** - Easy to add, good impact
2. ✅ **Use Rest Days** - Data already exists, just need to use it

### Priority 2: Medium-Term
3. ✅ **Team Form** - Significant impact, moderate effort
4. ✅ **League Parameters** - Good impact, moderate effort

### Priority 3: Long-Term
5. ⚠️ **Injury Tracking** - Lower impact, high effort
6. ⚠️ **Separate Models** - High impact but very complex

---

## League-Specific Training Explained

### Current Implementation (ONE Model, Filtered Data)

**How It Works:**
```
Training Request:
  leagues = ['SP1', 'E0']

Process:
  1. Query matches WHERE league_code IN ('SP1', 'E0')
  2. Train ONE model on filtered matches
  3. Model learns team strengths from SP1 and E0 teams
  4. Store ONE model with team strengths for all teams

Result:
  - ONE model trained on SP1 + E0 data
  - Better estimates for SP1 and E0 teams
  - Can predict matches in SP1 or E0
```

### Alternative: Separate Models Per League

**How It Would Work:**
```
Training Request:
  leagues = ['SP1', 'E0']

Process:
  1. Train Model #1 on SP1 matches only
  2. Train Model #2 on E0 matches only
  3. Store TWO separate models
  4. Route predictions to correct model

Result:
  - Model #1: SP1-specific (home advantage, draw rates, etc.)
  - Model #2: E0-specific (home advantage, draw rates, etc.)
  - More accurate but more complex
```

### Why Current Approach is Better (For Now)

**Advantages:**
- ✅ Simpler: One model to manage
- ✅ Efficient: Shared learning across leagues
- ✅ Flexible: Can train on any combination
- ✅ Better data: More matches = better estimates

**When Separate Models Make Sense:**
- ⚠️ Leagues have very different characteristics
- ⚠️ You have enough data per league (1000+ matches)
- ⚠️ You want league-specific parameters (home advantage, etc.)

**Current Recommendation:**
- ✅ Keep ONE model with league filtering
- ✅ Add league-specific parameters (home advantage, draw rates)
- ✅ Consider separate models only if needed

---

## Next Steps

### Immediate Actions:
1. ✅ Document current implementation status
2. ✅ Prioritize quick wins (Recent Data Focus, Rest Days)
3. ✅ Plan implementation of missing features

### Future Enhancements:
1. Add Recent Data Focus configuration
2. Integrate Rest Days into calculations
3. Implement Team Form tracking
4. Consider League-Specific Parameters

---

**Summary:** Most strategies are implemented or partially implemented. The main gaps are:
- Recent Data Focus not easily configurable
- Rest Days stored but not used
- Team Form and Injuries not implemented

