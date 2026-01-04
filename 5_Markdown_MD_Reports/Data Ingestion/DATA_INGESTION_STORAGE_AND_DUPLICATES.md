# Data Ingestion: Storage, Batches, and Duplicate Handling

## 📁 How Data is Stored When Downloading

### 1. **Database Storage (Primary)**

When you click "Download Selected" on the Data Ingestion page:

- **Data is stored in PostgreSQL database:**
  - **Primary Table:** `matches` - All historical match data
  - **Supporting Tables:**
    - `ingestion_logs` - Tracks each download batch
    - `data_sources` - Registry of data sources
    - `teams` - Team registry (auto-created during ingestion)
    - `leagues` - League reference data

- **What gets stored:**
  - Match date, teams, scores (FTHG, FTAG)
  - Match result (H/D/A)
  - Odds (B365H, B365D, B365A)
  - Market-implied probabilities
  - League and season information

### 2. **File System Storage (Backup/Archive)**

**Location:** `2_Backend_Football_Probability_Engine/data/1_data_ingestion/`

**Structure:**
```
data/1_data_ingestion/
  batch_100_Premier_League/
    E0_2425.csv
    E0_2324.csv
    E0_2223.csv
    ...
  batch_101_La_Liga/
    SP1_2425.csv
    SP1_2324.csv
    ...
```

**Naming Convention:**
- **Folder:** `batch_{N}_{League_Name}` (e.g., `batch_100_Premier_League`)
- **File:** `{league_code}_{season}.csv` (e.g., `E0_2425.csv`)

**Note:** CSV files are saved **in addition to** database storage, not instead of it. They serve as:
- Backup/archive
- Audit trail
- Offline access

---

## 🔄 Duplicate Detection: Does It Re-download Everything?

### **Current Behavior: UPDATE, Not SKIP**

**The system does NOT skip existing data. Instead, it UPDATES it.**

### How Duplicate Detection Works

**Code Location:** `app/services/data_ingestion.py` (lines 259-278)

```python
# Check if match already exists
existing_match = self.db.query(Match).filter(
    Match.home_team_id == home_team.id,
    Match.away_team_id == away_team.id,
    Match.match_date == match_date
).first()

if existing_match:
    # UPDATE existing match
    existing_match.home_goals = home_goals
    existing_match.away_goals = away_goals
    existing_match.result = result
    existing_match.odds_home = odds_home
    existing_match.odds_draw = odds_draw
    existing_match.odds_away = odds_away
    # ... update probabilities
    stats["updated"] += 1
else:
    # INSERT new match
    match = Match(...)
    self.db.add(match)
    stats["inserted"] += 1
```

### What This Means

**If you download today and again after a month:**

1. **Existing matches** (same teams, same date):
   - ✅ **UPDATED** with new odds/probabilities
   - ✅ **NOT skipped**
   - ✅ **NOT duplicated**

2. **New matches** (new dates or teams):
   - ✅ **INSERTED** as new records

3. **CSV Files:**
   - ⚠️ **Re-downloaded and overwritten** in batch folder
   - ⚠️ **No incremental backup** - old CSV is replaced

### Statistics Returned

The system tracks:
- `inserted` - New matches added
- `updated` - Existing matches updated
- `skipped` - Invalid rows skipped
- `processed` - Total rows processed

**Example Response:**
```json
{
  "stats": {
    "processed": 380,
    "inserted": 50,    // New matches
    "updated": 330,    // Existing matches updated
    "skipped": 0,
    "errors": 0
  }
}
```

---

## 📊 Batch Organization

### Current Implementation: **One Batch Per League**

**Code Location:** `app/api/data.py` (lines 487-514)

When you download multiple leagues:
- **Each league gets its own batch number**
- **All seasons for that league go into the same batch folder**

**Example:**
- Download: Premier League (E0) + La Liga (SP1) with "All Seasons"
- Result:
  - `batch_100_Premier_League/` - Contains E0_2425.csv, E0_2324.csv, ... (7 files)
  - `batch_101_La_Liga/` - Contains SP1_2425.csv, SP1_2324.csv, ... (7 files)

### Batch Number Assignment

- **Batch number = `IngestionLog.id`** (auto-increment from database)
- Each batch is tracked in `ingestion_logs` table
- Batch metadata stored in `logs` JSONB column

---

## 🎯 Best Practice Recommendations

### **Option 1: Incremental Updates (Recommended)**

**For regular updates (weekly/monthly):**

1. **Download only recent seasons:**
   - Select "2024-25" or "Last 7 Seasons"
   - System will update existing matches automatically

2. **Benefits:**
   - Faster downloads
   - Less bandwidth
   - Updates odds/probabilities for existing matches
   - Adds new matches automatically

### **Option 2: Full Refresh (When Needed)**

**For initial setup or major refresh:**

1. **Download "All Seasons" or "Last 10 Seasons"**
2. **System will:**
   - Update all existing matches
   - Add any missing historical data
   - Refresh odds/probabilities

3. **Use when:**
   - Initial database setup
   - After long gap (months/years)
   - When you suspect data corruption

### **Option 3: Selective League Updates**

**For targeted updates:**

1. **Select only leagues that need updating**
2. **Download specific seasons** (e.g., just "2024-25")
3. **System updates only those leagues**

---

## 🏆 Jackpot Results: Storage and Usage

### Where Jackpot Results Are Stored

**Database Table:** `saved_probability_results`

**Schema:**
```sql
CREATE TABLE saved_probability_results (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR,
    jackpot_id      VARCHAR NOT NULL,
    name            VARCHAR NOT NULL,
    description     TEXT,
    
    -- User selections per probability set
    selections      JSONB NOT NULL,  -- {"A": {"1": "1", "2": "X"}, "B": {...}}
    
    -- Actual results (entered after matches complete)
    actual_results  JSONB,           -- {"1": "X", "2": "1"}
    
    -- Score tracking per set
    scores          JSONB,           -- {"A": {"correct": 10, "total": 15}}
    
    model_version   VARCHAR,
    total_fixtures  INTEGER,
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
);
```

### How to Import Jackpot Results

**On Data Ingestion Page → "Jackpot Results" Tab:**

1. **Manual Import:**
   - Paste CSV format: `Match,HomeTeam,AwayTeam,Result`
   - Click "Import Results"
   - Creates entry in `saved_probability_results` table

2. **CSV Upload:**
   - Upload CSV file with jackpot results
   - System parses and stores in database

### What Jackpot Results Are Used For

#### 1. **Backtesting** (`/backtesting` page)
- Compare model predictions against actual results
- Test which probability set (A-G) performed best
- Calculate accuracy metrics per set

#### 2. **Calibration** (`/calibration` page)
- Validate model calibration
- Compute Brier Score, Log Loss
- Generate reliability curves
- Export to training data for model improvement

#### 3. **Model Health** (`/model-health` page)
- Track prediction accuracy over time
- Detect model drift
- Monitor league-specific performance

#### 4. **Jackpot Validation** (`/jackpot-validation` page)
- Detailed comparison of predictions vs actuals
- Per-fixture analysis
- Export validation data for retraining

### Data Flow

```
Import Jackpot Results
    ↓
saved_probability_results table
    ↓
┌─────────────────────────────────────┐
│  Backtesting                        │
│  - Compare sets A-G                 │
│  - Calculate accuracy               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Calibration                        │
│  - Brier Score                      │
│  - Reliability curves              │
│  - Export to training data          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Model Retraining                   │
│  - Use validation data              │
│  - Improve model accuracy           │
└─────────────────────────────────────┘
```

---

## 🔍 Summary

### Data Download Behavior

| Scenario | Behavior |
|----------|----------|
| **Download same league/season again** | ✅ Updates existing matches (odds, probabilities) |
| **Download new season** | ✅ Inserts new matches |
| **Download after 1 month** | ✅ Updates existing + inserts new |
| **CSV files** | ⚠️ Re-downloaded and overwritten |

### Key Points

1. **No duplicate matches** - System checks by `home_team_id`, `away_team_id`, `match_date`
2. **Updates, not skips** - Existing matches are updated with new data
3. **Batch organization** - One batch per league, all seasons in same folder
4. **Dual storage** - Database (primary) + CSV files (backup)
5. **Jackpot results** - Stored in `saved_probability_results` for backtesting/calibration

### Recommendations

- **Regular updates:** Download recent seasons only (faster, efficient)
- **Initial setup:** Download "All Seasons" for complete historical data
- **After long gap:** Full refresh to update all odds/probabilities
- **Jackpot results:** Import regularly for continuous model improvement

