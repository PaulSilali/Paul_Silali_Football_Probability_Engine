# Data Storage & Cleaning - Complete Guide

## 📊 **Database Storage**

### **✅ Data is Accurate and Stored in `matches` Table**

**Table:** `matches` (PostgreSQL)

**Key Columns:**
- `home_goals` (INTEGER NOT NULL) - Accurate, stored as integers
- `away_goals` (INTEGER NOT NULL) - Accurate, stored as integers
- `odds_home`, `odds_draw`, `odds_away` (FLOAT) - Closing odds
- `prob_home_market`, `prob_draw_market`, `prob_away_market` (FLOAT) - Market-implied probabilities (already calculated)
- `match_date` (DATE NOT NULL) - Match date
- `result` (ENUM: 'H', 'D', 'A') - Match result
- `league_id`, `season`, `home_team_id`, `away_team_id` - Foreign keys

**Data Flow:**
```
Download CSV → Phase 1 Cleaning → Phase 2 Enhancement → Insert to DB
```

**Accuracy:**
- ✅ Goals are stored as integers (no decimal precision loss)
- ✅ Dates are stored as DATE type (no string parsing needed)
- ✅ Odds stored as FLOAT (sufficient precision)
- ✅ Probabilities calculated and stored (no recalculation needed)

---

## 🔄 **Data Cleaning Process Flow**

### **Complete Pipeline:**

```
1. DATA INGESTION
   ↓
   Download CSV from football-data.co.uk
   
2. PHASE 1: CRITICAL CLEANING (Always Applied)
   ↓
   - Drop columns with >50% missing
   - Convert Date to datetime
   - Remove rows with missing critical columns (HomeTeam, AwayTeam, FTHG, FTAG)
   ↓
   Quality Score: 83.85 → ~92/100
   
3. PHASE 2: ENHANCEMENT (Optional, Configurable)
   ↓
   - Impute medium missing values (10-50%)
     * Median for numeric columns
     * Mode for categorical columns
   - Create derived features:
     * TotalGoals = FTHG + FTAG
     * GoalDifference = FTHG - FTAG
   - Calculate odds features:
     * Overround = sum(1/odds) - 1
     * Implied probabilities (if not present)
   - Extract date features:
     * Year, Month, DayOfWeek
   ↓
   Quality Score: ~92 → ~95/100
   
4. OUTLIER INVESTIGATION (Notebook Analysis)
   ↓
   - Statistical methods (IQR, Z-score, Modified Z-score)
   - Domain-specific validation
   - Visualizations
   - Recommendations
   ↓
   Verify legitimacy of outliers
   
5. MODEL TRAINING
   ↓
   Use cleaned data for Dixon-Coles model training
```

---

## ✅ **Phase 2 Implementation**

### **Implemented Features:**

#### **1. Impute Medium Missing Values (10-50%)**
- **Numeric columns**: Uses median
- **Categorical columns**: Uses mode
- **Tracks**: Number of values imputed

#### **2. Derived Features Created:**
- `TotalGoals` = FTHG + FTAG
- `GoalDifference` = FTHG - FTAG

#### **3. Odds Features:**
- `Overround` = (1/odds_home + 1/odds_draw + 1/odds_away) - 1
- Implied probabilities calculated if not present

#### **4. Date Features:**
- `Year` - Match year
- `Month` - Match month (1-12)
- `DayOfWeek` - Day of week (0=Monday, 6=Sunday)

### **Configuration:**

**In `app/config.py`:**
```python
DATA_CLEANING_PHASE: str = "phase1"  # Options: "phase1", "phase2", or "both"
```

**To Enable Phase 2:**
```python
# In .env file
DATA_CLEANING_PHASE=phase2  # or "both"
```

**Note:** Phase 2 automatically includes Phase 1, so `phase2` = Phase 1 + Phase 2

---

## 📓 **Outlier Investigation Notebook**

### **Location:** `7_Jupyter_Notebooks/Data _Ingeston/outlier_investigation.ipynb`

### **Purpose:**
- Investigate outliers in cleaned data
- Verify legitimacy of extreme values
- Identify potential data quality issues

### **When to Run:**
- **After Phase 2 Enhancement** (on cleaned data)
- Before model training
- Periodically to monitor data quality

### **Process:**
1. Load cleaned data from `data/2_Cleaned_data/`
2. Detect outliers using:
   - IQR method (Q1 - 1.5×IQR to Q3 + 1.5×IQR)
   - Z-score (|z| > 3)
   - Modified Z-score (more robust)
3. Domain-specific validation:
   - Goals: 0-15 range
   - Odds: 1.01-100.0 range
   - Overround: -0.1 to 0.5 range
4. Generate visualizations
5. Provide recommendations

### **Outputs:**
- `outlier_summary.csv` - Summary statistics
- `outlier_recommendations.csv` - Action items
- `outlier_distributions.png` - Visualizations
- `outlier_report_{timestamp}.json` - Comprehensive report

---

## 🎯 **Frontend Alignment**

### **Current Frontend:** `DataCleaning.tsx`

**Current Steps:**
1. Column Selection
2. Type Normalization
3. Team Name Standardization
4. Data Validation
5. Feature Derivation
6. Load to Training Store

**These steps are for MANUAL uploads, not automated ingestion.**

### **Automated Ingestion Flow (Backend):**

**Phase 1 (Critical):**
1. ✅ Drop columns with >50% missing
2. ✅ Convert Date to datetime
3. ✅ Remove invalid rows

**Phase 2 (Enhancement):**
4. ✅ Impute missing values
5. ✅ Create derived features
6. ✅ Calculate odds features
7. ✅ Extract date features

### **Frontend Updates Needed:**

The frontend `DataCleaning.tsx` page should be updated to show:

1. **Automated Cleaning Status** (separate from manual upload)
   - Show Phase 1 status
   - Show Phase 2 status (if enabled)
   - Display cleaning statistics
   - Link to outlier investigation notebook

2. **Cleaning Pipeline Visualization:**
   ```
   [Download] → [Phase 1] → [Phase 2] → [Outlier Check] → [Training Ready]
   ```

3. **Statistics Display:**
   - Columns dropped
   - Rows removed
   - Values imputed
   - Features created
   - Quality score

---

## 📋 **Summary**

### **Answers to Your Questions:**

1. **Is data stored in DB accurate?** ✅ **YES**
   - Stored in `matches` table
   - Goals as integers (accurate)
   - Dates as DATE type
   - Probabilities pre-calculated

2. **Phase 2 Implementation?** ✅ **COMPLETE**
   - Impute missing values (median/mode)
   - Create derived features (TotalGoals, GoalDifference)
   - Calculate overround
   - Extract date features

3. **Need another notebook?** ✅ **CREATED**
   - `outlier_investigation.ipynb`
   - Runs after Phase 2
   - Verifies outlier legitimacy

4. **What comes after cleaned data?** ✅ **OUTLIER INVESTIGATION**
   - Process: Ingestion → Phase 1 → Phase 2 → Outlier Check → Training
   - Notebook analyzes cleaned data
   - Provides recommendations

5. **Frontend alignment?** ⚠️ **NEEDS UPDATE**
   - Current frontend is for manual uploads
   - Should add automated cleaning status
   - Should show Phase 1/Phase 2 progress
   - Should display cleaning statistics

---

## 🚀 **Next Steps**

1. **Enable Phase 2** (if desired):
   ```bash
   # In .env
   DATA_CLEANING_PHASE=phase2
   ```

2. **Run Outlier Investigation:**
   - Open `outlier_investigation.ipynb`
   - Run all cells
   - Review recommendations

3. **Update Frontend** (optional):
   - Add automated cleaning status to `DataCleaning.tsx`
   - Show Phase 1/Phase 2 progress
   - Display cleaning statistics

4. **Monitor Data Quality:**
   - Review outlier reports periodically
   - Adjust cleaning thresholds if needed
   - Verify data quality scores

---

**Status:** ✅ **Phase 2 Implementation Complete**

All Phase 2 enhancements are implemented and ready to use. The outlier investigation notebook is created and ready for analysis.

