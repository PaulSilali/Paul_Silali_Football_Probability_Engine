# Draw Structural Tables - Feature Engineering & Cleaning Analysis

## 📊 Overview

This document analyzes whether draw structure database tables need feature engineering and data cleaning.

---

## 🗂️ Draw Structure Tables

### Current Tables

1. **`league_draw_priors`**
   - `draw_rate` (0.0-1.0)
   - `sample_size` (integer > 0)

2. **`h2h_draw_stats`**
   - `matches_played` (integer)
   - `draw_count` (integer)
   - `draw_rate` (0.0-1.0)
   - `avg_goals` (float)

3. **`team_elo`**
   - `elo_rating` (float, typically 1000-2000)
   - `date` (date)

4. **`match_weather`**
   - `temperature` (float)
   - `precipitation` (float)
   - `wind_speed` (float)
   - `weather_draw_index` (0.95-1.10 typical)

5. **`referee_stats`**
   - `avg_cards_per_match` (float)
   - `avg_goals_per_match` (float)
   - `draw_rate` (0.0-1.0)

6. **`team_rest_days`**
   - `rest_days` (integer)
   - `fatigue_index` (float)

7. **`odds_movement`**
   - `odds_open` (float)
   - `odds_close` (float)
   - `odds_delta` (float)

8. **`league_structure`**
   - `total_teams` (integer)
   - `relegation_zones` (integer)
   - `promotion_zones` (integer)

9. **`match_xg`**
   - `xg_home` (float)
   - `xg_away` (float)

---

## ✅ Do They Need Feature Engineering?

### **Answer: PARTIALLY**

#### ✅ **Already Engineered (No Additional FE Needed)**

These tables contain **already-calculated features**:

1. **`league_draw_priors`**
   - ✅ `draw_rate` is already a calculated statistic
   - ✅ `sample_size` is metadata
   - ❌ **No additional feature engineering needed**

2. **`h2h_draw_stats`**
   - ✅ `draw_rate` is already calculated
   - ✅ `avg_goals` is already calculated
   - ❌ **No additional feature engineering needed**

3. **`team_elo`**
   - ✅ `elo_rating` is already calculated using Elo algorithm
   - ❌ **No additional feature engineering needed**

4. **`league_structure`**
   - ✅ Contains structural metadata
   - ❌ **No additional feature engineering needed**

#### ⚠️ **Could Benefit from Feature Engineering**

These tables could use **derived features**:

1. **`match_weather`**
   - ✅ Has `weather_draw_index` (already engineered)
   - 💡 **Could add**: Weather severity categories, extreme weather flags
   - **Priority**: Low (current index is sufficient)

2. **`referee_stats`**
   - ✅ Has basic stats
   - 💡 **Could add**: Referee strictness index, home/away bias
   - **Priority**: Medium (could improve predictions)

3. **`team_rest_days`**
   - ✅ Has `fatigue_index` (already engineered)
   - 💡 **Could add**: Fatigue categories, cumulative fatigue
   - **Priority**: Low (current index is sufficient)

4. **`odds_movement`**
   - ✅ Has `odds_delta` (already engineered)
   - 💡 **Could add**: Movement direction, volatility index
   - **Priority**: Low (delta is sufficient for most cases)

5. **`match_xg`**
   - ✅ Has raw xG values
   - 💡 **Could add**: xG difference, xG symmetry index
   - **Priority**: Medium (xG symmetry is important for draws)

---

## 🧹 Do They Need Data Cleaning?

### **Answer: YES - But Different from Match Data**

#### ✅ **What Needs Cleaning**

1. **Outlier Detection**
   - ❌ **`draw_rate`** values outside [0.0, 1.0] range
   - ❌ **`elo_rating`** values outside reasonable range (e.g., < 500 or > 3000)
   - ❌ **`weather_draw_index`** values outside [0.5, 2.0] range
   - ❌ **`sample_size`** = 0 or negative
   - ❌ **`rest_days`** negative values

2. **Missing Data Handling**
   - ❌ NULL values in critical columns
   - ❌ Missing historical data (gaps in time series)
   - ❌ Incomplete league/season coverage

3. **Data Consistency**
   - ❌ `draw_count` > `matches_played`
   - ❌ `draw_rate` doesn't match `draw_count / matches_played`
   - ❌ Duplicate records (same league/season/team combinations)

4. **Temporal Consistency**
   - ❌ Elo ratings that jump unrealistically (e.g., +500 in one day)
   - ❌ Weather data for future dates
   - ❌ Rest days calculated incorrectly

#### ⚠️ **What Doesn't Need Traditional Cleaning**

These are **already aggregated/calculated**:
- ✅ No raw text to normalize
- ✅ No date parsing issues (dates are already parsed)
- ✅ No encoding issues (all numeric/structured data)

---

## 🎯 Recommendations

### **Priority 1: Data Validation (High Priority)**

**Add validation checks during ingestion:**

```python
# Example validation for league_draw_priors
def validate_league_draw_prior(draw_rate: float, sample_size: int) -> bool:
    if not (0.0 <= draw_rate <= 1.0):
        logger.warning(f"Invalid draw_rate: {draw_rate}")
        return False
    if sample_size <= 0:
        logger.warning(f"Invalid sample_size: {sample_size}")
        return False
    return True
```

**Where to add:**
- ✅ In ingestion services (`ingest_league_draw_priors.py`, etc.)
- ✅ Before database insertion
- ✅ Log warnings but don't fail (use defaults if needed)

### **Priority 2: Outlier Detection (Medium Priority)**

**Add outlier detection for:**
- Elo ratings (unrealistic jumps)
- Draw rates (extremely high/low for league)
- Weather indices (outside expected range)

**Implementation:**
```python
def detect_elo_outlier(current_elo: float, previous_elo: float) -> bool:
    """Detect unrealistic Elo jumps"""
    change = abs(current_elo - previous_elo)
    if change > 100:  # Unrealistic jump
        logger.warning(f"Large Elo change: {change}")
        return True
    return False
```

### **Priority 3: Feature Engineering (Low Priority)**

**Only if you want to enhance predictions:**

1. **xG Symmetry Index** (for `match_xg`)
   ```python
   xg_symmetry = 1.0 - abs(xg_home - xg_away) / max(xg_home + xg_away, 0.1)
   # Higher symmetry = more likely draw
   ```

2. **Referee Strictness Index** (for `referee_stats`)
   ```python
   strictness = (avg_cards_per_match / 3.0) * (1.0 / avg_goals_per_match)
   # Higher strictness = fewer goals = more draws
   ```

3. **Odds Volatility** (for `odds_movement`)
   ```python
   volatility = abs(odds_delta) / odds_open
   # Higher volatility = market uncertainty = potential draw
   ```

---

## 📋 Current Status

### ✅ **What's Already Done**

1. **Database Constraints**
   - ✅ CHECK constraints on `draw_rate` (0.0-1.0)
   - ✅ CHECK constraints on `sample_size` (> 0)
   - ✅ UNIQUE constraints prevent duplicates

2. **Ingestion Validation**
   - ✅ Basic validation in ingestion services
   - ✅ Error handling for missing data

3. **Feature Engineering**
   - ✅ `weather_draw_index` is already calculated
   - ✅ `fatigue_index` is already calculated
   - ✅ `odds_delta` is already calculated

### ❌ **What's Missing**

1. **Comprehensive Validation**
   - ❌ No outlier detection during ingestion
   - ❌ No consistency checks (e.g., draw_count vs matches_played)
   - ❌ No temporal validation (e.g., Elo jumps)

2. **Data Quality Monitoring**
   - ❌ No automated data quality reports
   - ❌ No alerts for suspicious data

3. **Advanced Feature Engineering**
   - ❌ No xG symmetry index
   - ❌ No referee strictness index
   - ❌ No odds volatility index

---

## 🎯 Final Answer

### **Do Draw Structure Tables Need Feature Engineering?**

**Answer: Mostly NO, but some enhancements possible**

- ✅ **Most tables are already engineered** (draw rates, Elo, indices)
- ⚠️ **Some tables could benefit** from additional features (xG symmetry, referee strictness)
- 💡 **Priority**: Low (current features are sufficient for most use cases)

### **Do Draw Structure Tables Need Cleaning?**

**Answer: YES - But focused on validation, not traditional cleaning**

- ✅ **Need validation** (outlier detection, range checks, consistency)
- ✅ **Need missing data handling** (NULL values, gaps)
- ❌ **Don't need traditional cleaning** (text normalization, encoding, date parsing)
- 💡 **Priority**: Medium-High (data quality is important for predictions)

---

## 🔧 Recommended Actions

### **Immediate (High Priority)**

1. ✅ Add validation functions to ingestion services
2. ✅ Add outlier detection for Elo ratings
3. ✅ Add consistency checks (draw_count vs matches_played)

### **Short-term (Medium Priority)**

4. ⏳ Add data quality monitoring dashboard
5. ⏳ Add automated alerts for suspicious data
6. ⏳ Add xG symmetry index calculation

### **Long-term (Low Priority)**

7. ⏳ Add referee strictness index
8. ⏳ Add odds volatility index
9. ⏳ Add advanced feature engineering pipeline

---

## 📝 Summary

| Table | Feature Engineering | Data Cleaning | Priority |
|-------|-------------------|---------------|----------|
| `league_draw_priors` | ❌ Not needed | ✅ Validation needed | High |
| `h2h_draw_stats` | ❌ Not needed | ✅ Validation needed | High |
| `team_elo` | ❌ Not needed | ✅ Outlier detection | High |
| `match_weather` | ⚠️ Optional | ✅ Range validation | Medium |
| `referee_stats` | ⚠️ Could add index | ✅ Validation needed | Medium |
| `team_rest_days` | ❌ Not needed | ✅ Validation needed | Medium |
| `odds_movement` | ⚠️ Optional | ✅ Validation needed | Medium |
| `league_structure` | ❌ Not needed | ✅ Validation needed | Low |
| `match_xg` | ⚠️ Could add symmetry | ✅ Validation needed | Medium |

**Overall Recommendation:**
- ✅ **Focus on validation and outlier detection** (not traditional cleaning)
- ⚠️ **Feature engineering is optional** (current features are sufficient)
- 💡 **Priority**: Data quality > Feature engineering

