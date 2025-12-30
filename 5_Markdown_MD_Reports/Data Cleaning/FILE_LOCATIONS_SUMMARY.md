# File Locations Summary

## 📁 **Complete File Structure**

### **Backend Services (Production Code)**

#### **Data Cleaning Service**
**Location:** `2_Backend_Football_Probability_Engine/app/services/data_cleaning.py`

**What it does:**
- ✅ Phase 1: Critical cleaning (drop columns, convert dates, remove invalid rows)
- ✅ Phase 2: Enhancement (impute missing, create features, calculate overround)

**Status:** ✅ **PRODUCTION READY**

---

#### **Data Ingestion Service**
**Location:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py`

**What it does:**
- Downloads CSV from football-data.co.uk
- Applies cleaning (Phase 1/Phase 2)
- Inserts cleaned data into database `matches` table

**Status:** ✅ **INTEGRATED WITH CLEANING**

---

#### **Data Preparation Service**
**Location:** `2_Backend_Football_Probability_Engine/app/services/data_preparation.py`

**What it does:**
- Combines all seasons per league
- Exports to CSV/Parquet for training
- Loads training data from database or files

**Status:** ✅ **READY FOR MODEL TRAINING**

---

### **Configuration**

**Location:** `2_Backend_Football_Probability_Engine/app/config.py`

**Key Settings:**
```python
ENABLE_DATA_CLEANING: bool = True
DATA_CLEANING_MISSING_THRESHOLD: float = 0.5
DATA_CLEANING_PHASE: str = "phase1"  # "phase1", "phase2", or "both"
```

---

### **Jupyter Notebooks (Analysis)**

#### **1. Data Cleanup & EDA**
**Location:** `7_Jupyter_Notebooks/Data _Ingeston/data_cleanup.ipynb`

**Purpose:**
- Exploratory Data Analysis (EDA)
- Data quality assessment
- Cleaning method identification
- Generates: `data_quality_report_*.json`, `available_cleaning_methods.json`

**When to Run:** Before implementing cleaning

---

#### **2. Outlier Investigation** ⭐ **NEW**
**Location:** `7_Jupyter_Notebooks/Data _Ingeston/outlier_investigation.ipynb`

**Purpose:**
- Investigate outliers in cleaned data
- Verify legitimacy of extreme values
- Domain-specific validation
- Generate recommendations

**When to Run:** 
- **After Phase 2 Enhancement** (on cleaned data)
- Before model training
- Periodically for quality monitoring

**Outputs:**
- `outlier_summary.csv`
- `outlier_recommendations.csv`
- `outlier_distributions.png`
- `outlier_report_{timestamp}.json`

**Status:** ✅ **CREATED AND READY**

---

#### **3. Data Cleaning Pipeline (Python Script)**
**Location:** `7_Jupyter_Notebooks/Data _Ingeston/data_cleaning_pipeline.py`

**Purpose:**
- Standalone Python script for cleaning
- Can be run outside Jupyter
- Reference implementation

---

### **Documentation**

#### **1. Data Cleaning Implementation**
**Location:** `2_Backend_Football_Probability_Engine/DATA_CLEANING_IMPLEMENTATION.md`

**Contents:**
- Phase 1 implementation details
- How cleaning works
- Configuration options
- Testing guide

---

#### **2. Data Storage & Cleaning Complete Guide**
**Location:** `2_Backend_Football_Probability_Engine/DATA_STORAGE_AND_CLEANING_COMPLETE.md`

**Contents:**
- Database storage details
- Complete process flow
- Phase 2 implementation
- Outlier investigation guide
- Frontend alignment notes

---

#### **3. Model Training Data Strategy**
**Location:** `2_Backend_Football_Probability_Engine/MODEL_TRAINING_DATA_STRATEGY.md`

**Contents:**
- Database vs file-based training
- CSV vs Parquet comparison
- Data preparation workflow
- Usage examples

---

#### **4. Data Quality Deep Analysis**
**Location:** `7_Jupyter_Notebooks/Data _Ingeston/DATA_QUALITY_DEEP_ANALYSIS.md`

**Contents:**
- Detailed quality assessment
- Issue categorization
- Cleaning recommendations
- Two-phase approach

---

### **Data Directories**

#### **1. Raw Ingestion Data**
**Location:** `2_Backend_Football_Probability_Engine/data/1_data_ingestion/`

**Structure:**
```
batch_{N}_{League_Name}/
  ├── {league_code}_{season}.csv
  ├── {league_code}_{season}.csv
  └── ...
```

**Status:** ✅ **ACTIVE** - Data downloaded here

---

#### **2. Cleaned Training Data**
**Location:** `2_Backend_Football_Probability_Engine/data/2_Cleaned_data/`

**Structure:**
```
{league_code}_{league_name}_all_seasons.csv
{league_code}_{league_name}_all_seasons.parquet
```

**Status:** ⚠️ **CREATED BY PREPARATION SERVICE** - Run `prepare-training-data` endpoint

---

### **Database Tables**

#### **Matches Table** (Primary Storage)
**Table:** `matches`

**Columns:**
- `home_goals`, `away_goals` (INTEGER NOT NULL) ✅ Accurate
- `odds_home`, `odds_draw`, `odds_away` (FLOAT)
- `prob_home_market`, `prob_draw_market`, `prob_away_market` (FLOAT)
- `match_date` (DATE NOT NULL)
- `result` (ENUM: 'H', 'D', 'A')
- `league_id`, `season`, `home_team_id`, `away_team_id`

**Status:** ✅ **PRODUCTION** - All cleaned data stored here

---

## 🔄 **Process Flow**

```
1. DATA INGESTION
   ↓
   Download CSV → data/1_data_ingestion/batch_{N}_{League}/
   
2. PHASE 1 CLEANING (Automatic)
   ↓
   data_cleaning.py → Drop columns, convert dates, remove invalid rows
   
3. PHASE 2 ENHANCEMENT (Optional, Configurable)
   ↓
   data_cleaning.py → Impute, create features, calculate overround
   
4. DATABASE INSERTION
   ↓
   data_ingestion.py → Insert into matches table
   
5. OUTLIER INVESTIGATION (Manual - Notebook)
   ↓
   outlier_investigation.ipynb → Analyze cleaned data
   
6. DATA PREPARATION (Optional - For Training Files)
   ↓
   data_preparation.py → Combine per league, export CSV/Parquet
   
7. MODEL TRAINING
   ↓
   Load from database or files → Train Dixon-Coles model
```

---

## 📋 **Quick Reference**

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| **Data Cleaning Service** | `app/services/data_cleaning.py` | Phase 1 & 2 cleaning | ✅ Production |
| **Data Ingestion Service** | `app/services/data_ingestion.py` | Download & insert to DB | ✅ Integrated |
| **Data Preparation Service** | `app/services/data_preparation.py` | Prepare training files | ✅ Ready |
| **Outlier Investigation** | `7_Jupyter_Notebooks/.../outlier_investigation.ipynb` | Analyze outliers | ✅ Created |
| **Data Cleanup EDA** | `7_Jupyter_Notebooks/.../data_cleanup.ipynb` | Initial EDA | ✅ Existing |
| **Configuration** | `app/config.py` | Cleaning settings | ✅ Configured |
| **Database Table** | `matches` (PostgreSQL) | Store cleaned data | ✅ Active |

---

## ✅ **Summary**

**All files are in place:**

1. ✅ **Phase 1 & 2 Cleaning** - Implemented in `data_cleaning.py`
2. ✅ **Outlier Investigation Notebook** - Created at `outlier_investigation.ipynb`
3. ✅ **Database Storage** - Accurate data in `matches` table
4. ✅ **Data Preparation** - Service ready for training files
5. ✅ **Documentation** - Complete guides available

**Next Steps:**
1. Run `outlier_investigation.ipynb` after Phase 2
2. Enable Phase 2 in config if desired
3. Prepare training data files (optional)
4. Train model using cleaned database data

---

**Status:** ✅ **ALL FILES LOCATED AND READY**

