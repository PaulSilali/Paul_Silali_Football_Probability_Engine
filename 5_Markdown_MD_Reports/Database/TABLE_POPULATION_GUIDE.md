# Database Table Population Guide

## Overview
This document explains **who** fills each table, **when** it's filled, and **what features/validation** are stored.

---

## 1. `leagues` Table

### **Who Fills It:**
- **Database Administrator** or **System Initialization**
- **NOT automatically filled** during data ingestion

### **When It's Filled:**
1. **During Database Initialization** (SQL Schema)
   - **File:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
   - **When:** When database is first created
   - **Current Status:** Only 5 leagues defined (E0, SP1, D1, I1, F1)

2. **Via API Endpoint** (Manual)
   - **Endpoint:** `POST /api/data/init-leagues`
   - **File:** `2_Backend_Football_Probability_Engine/app/api/data.py` (line 607)
   - **Function:** `create_default_leagues()` in `data_ingestion.py`
   - **When:** Called manually by admin/user
   - **⚠️ Issue:** Uses wrong league codes (`EPL`, `LaLiga` instead of `E0`, `SP1`)

3. **Manual SQL Insert**
   - Most reliable method
   - Insert leagues before downloading match data

### **What's Stored:**
```sql
- code (VARCHAR, UNIQUE) - League code like 'E0', 'SP1', 'D1'
- name (VARCHAR) - Full name like 'Premier League'
- country (VARCHAR) - Country name
- tier (INTEGER) - League tier (1 = top tier)
- avg_draw_rate (FLOAT) - Historical average draw rate (default 0.26)
- home_advantage (FLOAT) - League-specific home advantage (default 0.35)
- is_active (BOOLEAN) - Whether league is currently active
- created_at, updated_at (TIMESTAMPTZ)
```

### **Important Notes:**
- ❌ **Leagues are NOT created automatically** during CSV download
- ❌ If a league doesn't exist, data ingestion **FAILS** with error
- ✅ Leagues must exist **BEFORE** downloading match data
- ✅ League codes must match football-data.co.uk format (`E0`, `SP1`, etc.)

---

## 2. `team_features` Table

### **Who Fills It:**
- **Feature Calculation Service** (when implemented)
- **Currently: NOT AUTOMATICALLY POPULATED** ⚠️

### **When It's Filled:**
- **Status:** Table exists but **no automatic population** implemented yet
- **Intended Use:** Store rolling statistics for teams (last 5/10/20 matches)
- **Future Implementation:** Would be calculated during:
  - Model training preparation
  - Feature engineering pipeline
  - Pre-prediction feature calculation

### **What's Stored:**
```sql
- team_id (INTEGER) - Reference to teams table
- calculated_at (TIMESTAMPTZ) - When features were calculated
- goals_scored_5, goals_scored_10, goals_scored_20 (DOUBLE PRECISION)
- goals_conceded_5, goals_conceded_10, goals_conceded_20 (DOUBLE PRECISION)
- win_rate_5, win_rate_10 (DOUBLE PRECISION)
- draw_rate_5, draw_rate_10 (DOUBLE PRECISION)
- home_win_rate, away_win_rate (DOUBLE PRECISION)
- avg_rest_days (DOUBLE PRECISION)
- league_position (INTEGER)
- created_at (TIMESTAMPTZ)
```

### **Current Status:**
- ✅ Table schema exists
- ❌ No automatic calculation service
- ❌ No API endpoint to populate
- 📝 **TODO:** Implement feature calculation service

---

## 3. `validation_results` Table

### **Who Fills It:**
- **Export to Training Endpoint** (when user clicks "Export Selected" or "Export All")
- **Status:** ⚠️ **ENDPOINT MISSING** - Frontend calls it but backend doesn't have it

### **When It's Filled:**
1. **User Action:** When user clicks "Export Selected" or "Export All to Training" in Jackpot Validation page
2. **Frontend Call:** `apiClient.exportValidationToTraining(validationIds)`
3. **Expected Endpoint:** `POST /api/probabilities/validation/export`
4. **Current Status:** ❌ **Endpoint doesn't exist in `probabilities.py`**

### **What Should Be Stored:**
```sql
- jackpot_id (INTEGER) - Reference to jackpots table
- set_type (prediction_set ENUM) - Which set (A-G) was validated
- model_id (INTEGER) - Reference to models table
- total_matches (INTEGER) - Number of matches validated
- correct_predictions (INTEGER) - How many were correct
- accuracy (DOUBLE PRECISION) - Percentage accuracy
- brier_score (DOUBLE PRECISION) - Brier score metric
- log_loss (DOUBLE PRECISION) - Log loss metric
- home_correct, home_total (INTEGER) - Home win breakdown
- draw_correct, draw_total (INTEGER) - Draw breakdown
- away_correct, away_total (INTEGER) - Away win breakdown
- exported_to_training (BOOLEAN) - Flag if exported
- exported_at (TIMESTAMPTZ) - When exported
- created_at (TIMESTAMPTZ)
```

### **Current Flow:**
1. ✅ User saves probability results with actual outcomes
2. ✅ User views validation in "Jackpot Validation" page
3. ✅ User clicks "Export Selected" or "Export All"
4. ❌ **Backend endpoint missing** - Returns 404 error
5. ❌ **No data stored** in `validation_results` table

### **What Needs to Be Done:**
- ✅ Add `POST /api/probabilities/validation/export` endpoint
- ✅ Endpoint should:
  1. Accept list of validation IDs (format: `"savedResultId-setId"`)
  2. Load saved probability results
  3. Calculate metrics (accuracy, Brier score, etc.)
  4. Insert into `validation_results` table
  5. Mark as `exported_to_training = TRUE`

---

## Summary Table

| Table | Who Fills | When | Status | Auto-Populated? |
|-------|-----------|------|--------|----------------|
| **leagues** | Admin/DB Init | DB creation or manual API call | ✅ Working | ❌ No |
| **team_features** | Feature Service | Not implemented | ❌ Missing | ❌ No |
| **validation_results** | Export Endpoint | User clicks "Export" | ❌ Missing | ❌ No |

---

## Recommendations

### 1. **Fix League Population**
- Update `create_default_leagues()` to use correct codes (`E0`, `SP1`, etc.)
- Or add auto-creation during CSV ingestion (with warning)

### 2. **Implement Feature Calculation**
- Create `FeatureCalculationService`
- Calculate features before model training
- Store in `team_features` table

### 3. **Implement Validation Export**
- Add `POST /api/probabilities/validation/export` endpoint
- Store validation metrics in `validation_results` table
- Enable backtesting and calibration training

---

## Related Files

- **League Creation:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py` (line 645)
- **League API:** `2_Backend_Football_Probability_Engine/app/api/data.py` (line 607)
- **Validation Export (Missing):** Should be in `2_Backend_Football_Probability_Engine/app/api/probabilities.py`
- **Frontend Export Call:** `1_Frontend_Football_Probability_Engine/src/pages/JackpotValidation.tsx` (lines 454, 481)
- **Database Schema:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`

