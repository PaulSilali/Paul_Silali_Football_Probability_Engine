# Look-Back Window Analysis & Recommendations

## 📍 Where This Information Applies

### ❌ NOT in Data Ingestion or Draw Structure Tab

The look-back window recommendations are **NOT** about data ingestion. They are about **model training configuration**.

### ✅ Should Be in ML Training Configuration

This information should be implemented in:
1. **ML Training Page** (`MLTraining.tsx`) - Add look-back window configuration
2. **Model Training Service** (`model_training.py`) - Apply window filters during training
3. **Training Configuration** (`config.py`) - Default window settings

---

## ✅ Do I Agree with the Recommendations?

### **YES - The recommendations are sound:**

1. ✅ **Different windows for different components** - Makes sense
2. ✅ **Draw models need shorter windows** - Draw rates change faster
3. ✅ **Recency weighting** - Already implemented (decay_rate = 0.0065)
4. ✅ **Pre-COVID data issues** - Valid concern
5. ✅ **3-4 seasons for base models** - Reasonable balance

### **Minor Disagreements:**

1. ⚠️ **"1.5-2.5 seasons for draw models"** - Might be too short for some leagues
   - **Recommendation**: Make it configurable (2-3 seasons default)
2. ⚠️ **"Ignore old odds"** - Sometimes historical odds patterns are useful
   - **Recommendation**: Use with very low weight, don't ignore completely

---

## 🔄 How "Import All" Currently Works

### Current Implementation

When you click "Import All" in Draw Structure tab:

**It CALCULATES from the `matches` table, NOT from:**
- ❌ Online APIs
- ❌ CSV files
- ❌ External sources

**What it does:**
1. **League Draw Priors**: Queries `matches` table → Calculates draw rate → Saves to DB + CSV
2. **League Structure**: Uses defaults or calculates from league metadata
3. **Elo Ratings**: Calculates Elo from `matches` table → Saves to DB + CSV
4. **H2H Stats**: Queries `matches` table → Calculates H2H → Saves to DB + CSV
5. **Odds Movement**: Reads from `matches.odds_*` columns → Saves to DB + CSV
6. **Referee Stats**: Calculates from `matches` (if referee_id exists) → Saves to DB + CSV
7. **Rest Days**: Calculates from `matches.match_date` → Saves to DB + CSV
8. **XG Data**: Needs external source (not in matches table)
9. **Weather**: Needs API calls (Open-Meteo)

### Flow Diagram

```
User clicks "Import All"
    ↓
For each data type:
    ↓
1. Query matches table (with max_years filter)
    ↓
2. Calculate statistics/features
    ↓
3. Save to database tables
    ↓
4. Save to CSV files (both locations)
```

### CSV Import Functions (Separate)

We also have CSV import functions that can import from existing CSV files:
- `ingest_elo_from_csv()`
- `ingest_h2h_from_csv()`
- `ingest_league_structure_from_csv()`
- etc.

**But "Import All" does NOT use these** - it calculates from matches.

---

## 💡 Recommended Hybrid Approach

### Option 1: CSV-First, Then Calculate Missing (Recommended)

```python
def smart_import_all():
    # 1. Try to import from CSV files first (fast)
    for csv_file in find_csv_files():
        import_from_csv(csv_file)
    
    # 2. Check what's missing in database
    missing_data = check_missing_data()
    
    # 3. Calculate missing data from matches table
    for missing in missing_data:
        calculate_from_matches(missing)
```

### Option 2: Current Approach (Calculate from Matches)

**Pros:**
- ✅ Always up-to-date
- ✅ No CSV file management needed
- ✅ Works even if CSV files are missing

**Cons:**
- ❌ Slower (queries matches table)
- ❌ Doesn't use existing CSV files

---

## 🎯 Where to Implement Look-Back Windows

### 1. Model Training Service

**File:** `app/services/model_training.py`

**Current:** Uses `date_from` and `date_to` parameters

**Should Add:**
```python
def train_poisson_model(
    self,
    leagues: Optional[List[str]] = None,
    seasons: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    # NEW: Component-specific windows
    base_model_window_years: float = 4.0,  # 3-4 seasons
    draw_model_window_years: float = 2.0,  # 1.5-2.5 seasons
    odds_calibration_window_years: float = 1.5,  # 1-2 seasons
    recency_half_life_years: float = 1.0,  # ~1 season
    task_id: Optional[str] = None
) -> Dict:
```

### 2. Training Configuration

**File:** `app/config.py`

**Should Add:**
```python
# Model Training Windows (SP-FX Recommended)
BASE_MODEL_WINDOW_YEARS: float = 4.0  # Team strength, home advantage
DRAW_MODEL_WINDOW_YEARS: float = 2.0  # Draw-specific models
ODDS_CALIBRATION_WINDOW_YEARS: float = 1.5  # Market calibration
RECENCY_HALF_LIFE_YEARS: float = 1.0  # Exponential decay
LEAGUE_PRIORS_WINDOW_YEARS: float = 5.0  # League-level aggregates
H2H_WINDOW_YEARS: float = 2.0  # Head-to-head (capped at 24 months)
```

### 3. ML Training UI

**File:** `src/pages/MLTraining.tsx`

**Should Add:**
- Component-specific window configuration
- Visual indicators for recommended windows
- Pre-COVID data warning/toggle

---

## 📊 Current vs Recommended Windows

| Component | Current | Recommended | Status |
|-----------|---------|-------------|--------|
| Base Model | All data | 3-4 seasons | ⚠️ Needs implementation |
| Draw Model | All data | 1.5-2.5 seasons | ⚠️ Needs implementation |
| Odds Calibration | All data | 1-2 seasons | ⚠️ Needs implementation |
| League Priors | All data | 5-6 seasons | ⚠️ Needs implementation |
| H2H Stats | All data | ≤ 2 seasons | ⚠️ Needs implementation |
| Recency Weighting | 0.0065 decay | ~1 season half-life | ✅ Already implemented |

---

## 🔧 Implementation Priority

### High Priority
1. ✅ **Add window configuration to ML Training UI**
2. ✅ **Apply windows in model training service**
3. ✅ **Add pre-COVID data filter option**

### Medium Priority
4. ⏳ **Add component-specific training endpoints**
5. ⏳ **Document window recommendations in UI**

### Low Priority
6. ⏳ **Hybrid CSV-first import approach**
7. ⏳ **Automatic window optimization**

---

## 📝 Summary

### Where This Information Helps:
- ✅ **ML Training Configuration** (not data ingestion)
- ✅ **Model Training Service** (apply filters)
- ✅ **Training UI** (user configuration)

### How "Import All" Works:
- ✅ **Calculates from `matches` table** (not online, not CSV)
- ✅ **Uses `max_years` parameter** (default: 10 years)
- ✅ **Saves to both database and CSV files**

### Do We Have CSV Import?
- ✅ **Yes** - We have CSV import functions
- ⚠️ **But** - "Import All" doesn't use them (calculates instead)
- 💡 **Recommendation** - Add hybrid approach (CSV-first, then calculate missing)

### Agreement with Recommendations:
- ✅ **Mostly agree** - Recommendations are sound
- ⚠️ **Minor adjustments** - Make windows configurable, don't ignore old odds completely

