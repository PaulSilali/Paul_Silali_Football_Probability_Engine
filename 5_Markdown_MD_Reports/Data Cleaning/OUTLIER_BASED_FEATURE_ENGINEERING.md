# Outlier-Based Feature Engineering Implementation

## 📊 Overview

Based on the outlier investigation analysis, we've implemented feature engineering that creates new features from outlier patterns identified in the data. These features help models better understand and predict edge cases.

## 🎯 Features Created

### 1. Mismatch Indicators
**Purpose:** Identify matches with extreme skill gaps (strong favorites)

- **`is_extreme_favorite_home`** (binary)
  - `1` when `AvgH > 15` (home team is extreme underdog)
  - `0` otherwise
  - **Threshold:** Based on outlier analysis showing AvgH outliers >15

- **`is_extreme_favorite_away`** (binary)
  - `1` when `AvgA > 30` (away team is extreme underdog)
  - `0` otherwise
  - **Threshold:** Based on outlier analysis showing AvgA outliers >30

- **`is_mismatch`** (binary)
  - `1` when either team is extreme favorite (`is_extreme_favorite_home` OR `is_extreme_favorite_away`)
  - `0` otherwise
  - **Use case:** Flag matches where one team is heavily favored

### 2. High-Scoring Match Indicators
**Purpose:** Identify matches with unusually high goal counts

- **`is_high_scoring_match`** (binary)
  - `1` when `FTHG > 6` OR `TotalGoals > 7`
  - `0` otherwise
  - **Threshold:** Based on outlier analysis showing FTHG outliers >6

- **`is_very_high_scoring`** (binary)
  - `1` when `FTHG > 8` OR `TotalGoals > 9`
  - `0` otherwise
  - **Use case:** Flag extremely rare high-scoring matches (e.g., 9-0, 8-0)

### 3. Draw Probability Categories
**Purpose:** Categorize matches by draw likelihood

- **`draw_prob_category`** (categorical: 'low', 'medium', 'high', 'unknown')
  - `'low'`: `prob_draw_market < 0.15` (very unlikely draw)
  - `'medium'`: `0.15 ≤ prob_draw_market ≤ 0.35` (normal draw probability)
  - `'high'`: `prob_draw_market > 0.35` (high draw probability)
  - `'unknown'`: Missing probability data
  - **Thresholds:** Based on outlier analysis showing draw prob outliers <0.15 and >0.35

### 4. Extreme Odds Flags
**Purpose:** Flag matches with extreme odds values (potential outliers)

- **`has_extreme_draw_odds`** (binary)
  - `1` when `AvgD > 12`
  - `0` otherwise
  - **Threshold:** Based on outlier analysis showing AvgD outliers >12

- **`has_extreme_home_odds`** (binary)
  - `1` when `AvgH > 15`
  - `0` otherwise

- **`has_extreme_away_odds`** (binary)
  - `1` when `AvgA > 30`
  - `0` otherwise

### 5. Team Strength Categories
**Purpose:** Categorize team strength based on odds

- **`home_team_strength_category`** (categorical: 'strong', 'medium', 'weak', 'unknown')
  - `'strong'`: `AvgH < 2.0` (strong favorite)
  - `'medium'`: `2.0 ≤ AvgH ≤ 10.0` (moderate favorite/underdog)
  - `'weak'`: `AvgH > 10.0` (weak underdog)
  - `'unknown'`: Missing odds data

- **`away_team_strength_category`** (categorical: 'strong', 'medium', 'weak', 'unknown')
  - `'strong'`: `AvgA < 3.0` (strong favorite)
  - `'medium'`: `3.0 ≤ AvgA ≤ 20.0` (moderate favorite/underdog)
  - `'weak'`: `AvgA > 20.0` (weak underdog)
  - `'unknown'`: Missing odds data

## 🔧 Implementation Details

### Location
- **File:** `2_Backend_Football_Probability_Engine/app/services/data_cleaning.py`
- **Method:** `_create_outlier_based_features()`
- **Called from:** `_phase2_enhancement()`

### Configuration
- **Default Phase:** `DATA_CLEANING_PHASE = "phase2"` (includes Phase 1 + outlier features)
- **Can be overridden:** Set `DATA_CLEANING_PHASE` in `.env` file:
  - `"phase1"` - Only critical cleaning (no outlier features)
  - `"phase2"` - Phase 1 + enhancement + outlier features ✅ (recommended)
  - `"both"` - Same as phase2

### Feature Creation Flow
```
Phase 2 Enhancement:
  1. Impute medium missing values
  2. Create derived features (TotalGoals, GoalDifference)
  3. Calculate odds features (Overround, probabilities)
  4. Extract date features (Year, Month, DayOfWeek)
  5. Create outlier-based features ← NEW
```

## 📈 Expected Impact

### Model Training Benefits
1. **Better Edge Case Handling:** Models can learn patterns for extreme matches
2. **Improved Predictions:** Mismatch indicators help predict blowouts
3. **Feature Importance:** Outlier flags can be used as model features
4. **Categorical Features:** Team strength categories provide interpretable features

### Data Quality
- **No data loss:** All features are additive (no rows removed)
- **Backward compatible:** Existing features remain unchanged
- **Optional:** Can be disabled by setting `DATA_CLEANING_PHASE="phase1"`

## 🔄 Do You Need to Re-run Cleaning?

### **YES** - You need to re-run cleaning if:
- ✅ You want the new outlier-based features in your training data
- ✅ You're preparing data for model training
- ✅ You want to use these features in predictions

### **NO** - You don't need to re-run if:
- ❌ You only need Phase 1 cleaning (critical cleaning)
- ❌ You're not using these features in your models
- ❌ You're satisfied with existing features

### How to Re-run Cleaning

#### Option 1: Re-download Data (Recommended)
1. Go to **Data Ingestion** page
2. Select leagues/seasons
3. Click **"Download Selected"**
4. New data will automatically include outlier-based features (Phase 2)

#### Option 2: Re-run Data Preparation Pipeline
1. Go to **Data Cleaning & ETL** page
2. Click **"Run Pipeline"** button
3. This will re-process existing data with Phase 2 cleaning

#### Option 3: Backend API
```python
# Via API
POST /api/data/prepare-training-data
{
  "league_codes": ["E0", "SP1"],
  "format": "both"
}
```

## 📊 Feature Statistics

After implementation, you can check feature creation stats:
- **Cleaning stats** include `features_created` list
- **All outlier-based features** are logged during cleaning
- **Feature counts** are tracked in `cleaning_stats`

## 🎯 Usage in Models

### Example: Using Mismatch Indicator
```python
# In model training
if 'is_mismatch' in features:
    # Model can learn different patterns for mismatches
    mismatch_features = ['is_mismatch', 'is_extreme_favorite_home', 'is_extreme_favorite_away']
```

### Example: Using Team Strength Categories
```python
# One-hot encode categorical features
strength_features = ['home_team_strength_category', 'away_team_strength_category']
# Model can learn: strong vs weak, strong vs medium, etc.
```

### Example: Using High-Scoring Indicators
```python
# Flag rare high-scoring matches
if 'is_very_high_scoring' in features:
    # Model can adjust predictions for extreme matches
```

## ✅ Summary

- **✅ Implemented:** All outlier-based features are now in production
- **✅ Default:** Phase 2 cleaning is enabled by default
- **✅ Backward Compatible:** Existing features unchanged
- **✅ Optional:** Can be disabled via config
- **✅ Ready for Training:** Features available for model training

## 🔍 Next Steps

1. **Re-run data preparation** to generate features for existing data
2. **Train models** using new features
3. **Evaluate impact** of outlier-based features on model performance
4. **Monitor** feature distributions in new data

---

**Status:** ✅ **IMPLEMENTED AND READY FOR USE**

