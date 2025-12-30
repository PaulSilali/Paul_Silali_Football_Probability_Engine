# Model Training Data Strategy

## 📊 **Recommended Approach**

### **Primary: Database-First Training** ✅ (RECOMMENDED)

**Why Database?**
- ✅ **Fastest**: Database queries are optimized with indexes
- ✅ **Flexible**: Easy filtering by league, date range, team
- ✅ **Real-time**: Always uses latest cleaned data
- ✅ **Memory efficient**: Can stream data in batches
- ✅ **Already implemented**: Your Dixon-Coles model loads from database

**How It Works:**
```python
# In model training code
from app.services.data_preparation import DataPreparationService

service = DataPreparationService(db)

# Load training data directly from database
df = service.load_training_data(
    league_codes=['E0', 'SP1', 'D1'],  # Premier League, La Liga, Bundesliga
    min_date=datetime(2020, 1, 1),
    max_date=datetime.now(),
    min_matches_per_team=10,
    source="database"  # ← Database is fastest
)
```

---

### **Secondary: File-Based Training** (Backup/Portability)

**When to Use Files:**
- ✅ **Offline training**: When database unavailable
- ✅ **Data sharing**: Export for external analysis
- ✅ **Backup**: Archive cleaned data
- ✅ **Jupyter notebooks**: Easy to load and explore

**File Format Recommendation:**

#### **1. CSV Files** (Human-Readable)
- ✅ Easy to inspect and debug
- ✅ Universal compatibility
- ✅ Works in Excel, Python, R, etc.
- ❌ Larger file size (~10-50MB per league)
- ❌ Slower I/O for large datasets

#### **2. Parquet Files** (ML-Optimized) ⭐ **RECOMMENDED**
- ✅ **50-80% smaller** than CSV
- ✅ **5-10x faster** I/O
- ✅ Columnar format (perfect for ML)
- ✅ Built-in compression
- ✅ Preserves data types
- ❌ Requires `pyarrow` library
- ❌ Not human-readable

**Recommendation: Export BOTH formats**
- CSV for human inspection
- Parquet for ML training

---

## 🗂️ **File Structure**

### **Current Structure:**
```
data/
├── 1_data_ingestion/          # Raw downloaded data (by batch)
│   ├── batch_176_Premier_League/
│   │   ├── E0_1920.csv
│   │   ├── E0_2021.csv
│   │   └── ...
│   └── batch_177_Championship/
│       └── ...
│
└── 2_Cleaned_data/            # Combined cleaned data (for training)
    ├── E0_Premier_League_all_seasons.csv
    ├── E0_Premier_League_all_seasons.parquet
    ├── SP1_La_Liga_all_seasons.csv
    ├── SP1_La_Liga_all_seasons.parquet
    └── ...
```

### **Benefits:**
- ✅ **One file per league** = Easy to load entire league history
- ✅ **All seasons combined** = No need to merge multiple files
- ✅ **Already cleaned** = Phase 1 cleaning applied
- ✅ **Ready for training** = Optimized format

---

## 🚀 **Implementation**

### **1. Prepare Training Data Files**

**API Endpoint:**
```bash
POST /api/data/prepare-training-data
{
  "league_codes": ["E0", "SP1"],  # Optional: None = all leagues
  "format": "both"  # "csv", "parquet", or "both"
}
```

**Python Code:**
```python
from app.services.data_preparation import DataPreparationService

service = DataPreparationService(db)

# Prepare single league
stats = service.prepare_league_data("E0", format="both")
# Creates: E0_Premier_League_all_seasons.csv + .parquet

# Prepare all leagues
summary = service.prepare_all_leagues(format="both")
```

---

### **2. Load Data for Training**

#### **Option A: Database (Recommended)**
```python
from app.services.data_preparation import DataPreparationService

service = DataPreparationService(db)

# Load from database (fastest)
df = service.load_training_data(
    league_codes=['E0', 'SP1', 'D1'],
    min_date=datetime(2020, 1, 1),
    source="database"  # ← Fastest
)

# Train Dixon-Coles model
from app.models.dixon_coles import train_team_strengths
team_strengths = train_team_strengths(df, params)
```

#### **Option B: Files (Backup)**
```python
# Load from Parquet files (faster than CSV)
df = service.load_training_data(
    league_codes=['E0', 'SP1'],
    source="file"  # ← Loads from 2_Cleaned_data/
)
```

---

## 📈 **Performance Comparison**

| Method | Speed | File Size | Use Case |
|--------|-------|-----------|----------|
| **Database** | ⚡⚡⚡⚡⚡ Fastest | N/A | Production training |
| **Parquet** | ⚡⚡⚡⚡ Fast | 50-80% smaller | Offline training |
| **CSV** | ⚡⚡ Medium | Larger | Human inspection |

---

## 🎯 **Training Workflow**

### **Recommended Workflow:**

```
1. Data Ingestion
   ↓
   Download → Clean → Save CSV → Insert to DB
   
2. Prepare Training Files (Optional - for backup/portability)
   ↓
   POST /api/data/prepare-training-data
   Combines all seasons per league
   Exports CSV + Parquet to 2_Cleaned_data/
   
3. Model Training (Primary Method)
   ↓
   Load from Database (fastest)
   Filter by league/date/team
   Train Dixon-Coles model
   
4. Alternative: Load from Files
   ↓
   Load Parquet files (if DB unavailable)
   Train model
```

---

## 💡 **Best Practices**

### **1. Database-First Approach**
- ✅ Always load training data from database
- ✅ Use file exports only for backup/portability
- ✅ Database queries are optimized with indexes

### **2. File Format Choice**
- ✅ **Parquet** for ML training (faster, smaller)
- ✅ **CSV** for human inspection (readable)
- ✅ Export both formats for flexibility

### **3. Data Preparation**
- ✅ Run `prepare-training-data` after major data ingestion
- ✅ Keep files in sync with database
- ✅ Use Parquet for large datasets (>100K rows)

### **4. Training Data Loading**
- ✅ Filter by date range (e.g., last 7 years)
- ✅ Filter by league (train per league or combined)
- ✅ Filter teams with minimum matches (e.g., >= 10 matches)

---

## 🔧 **Configuration**

### **In `app/config.py`:**
```python
# Data Preparation Configuration
COMBINE_SEASONS_PER_LEAGUE: bool = True  # Combine all seasons
USE_PARQUET_FORMAT: bool = True  # Export Parquet files
TRAINING_MIN_MATCHES_PER_TEAM: int = 10  # Filter threshold
```

---

## 📝 **Example Usage**

### **1. Prepare Training Files**
```python
from app.services.data_preparation import prepare_training_data
from app.db.session import get_db

db = next(get_db())
stats = prepare_training_data(
    db=db,
    league_codes=['E0', 'SP1'],  # Premier League, La Liga
    output_format="both"  # CSV + Parquet
)

print(f"Prepared {stats['total_matches']} matches")
print(f"Files: {stats['files_created']}")
```

### **2. Load for Training**
```python
from app.services.data_preparation import DataPreparationService
from datetime import datetime

service = DataPreparationService(db)

# Load from database (recommended)
df = service.load_training_data(
    league_codes=['E0'],
    min_date=datetime(2020, 1, 1),
    min_matches_per_team=10,
    source="database"
)

print(f"Loaded {len(df)} matches for training")
```

---

## ✅ **Summary**

**Answer to Your Questions:**

1. **Will files be combined per league?** ✅ **YES**
   - One file per league: `{league_code}_{league_name}_all_seasons.csv/.parquet`
   - All seasons combined in single file

2. **CSV or Parquet?** ✅ **BOTH**
   - CSV for human inspection
   - Parquet for ML training (recommended)

3. **How will model training be done?** ✅ **DATABASE-FIRST**
   - Primary: Load from database (fastest)
   - Backup: Load from Parquet files (if needed)

4. **Whole data or bits?** ✅ **FLEXIBLE**
   - Can filter by league, date range, team
   - Can load all leagues or specific ones
   - Can stream in batches for large datasets

---

**Status:** ✅ **READY TO USE**

The data preparation service is implemented and ready. Use database-first approach for training, with file exports as backup/portability option.

