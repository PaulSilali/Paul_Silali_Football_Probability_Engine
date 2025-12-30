# Data Ingestion Flow Analysis

## Current Implementation Status

### ⚠️ **IMPORTANT: Frontend is Currently Mock/Simulated**

The frontend `DataIngestion.tsx` currently **does NOT** call the backend API. It simulates downloads with mock progress bars and creates batch records only in browser memory (React state).

---

## 1. What Happens When You Click "Download Selected"?

### Current Behavior (Frontend Only - Mock)

1. **Frontend State Management** (`DataIngestion.tsx` lines 150-222):
   - Sets `isDownloading = true`
   - Iterates through selected data sources
   - Simulates progress with random increments (150ms intervals)
   - Creates a `DownloadBatch` object with:
     - `batchNumber`: Auto-incremented counter (starts at 1000)
     - `timestamp`: Current ISO timestamp
     - `sources`: Array of downloaded source names
     - `totalRecords`: Sum of mock record counts (2000-5000 per source)
   - Stores batch in React state (`downloadBatches` array)
   - **NO backend API call is made**

### What SHOULD Happen (Backend Integration Needed)

The frontend should call:
```
POST /api/data/refresh
Body: {
  source: "football-data.co.uk",
  league_code: "E0",  // e.g., Premier League
  season: "2324"      // e.g., 2023-24 season
}
```

---

## 2. Where is Data Saved? Database Tables

### ✅ **Data is Saved to PostgreSQL Database**

**Primary Table: `matches`**
- Stores all historical match data
- Columns include:
  - `league_id` (references `leagues` table)
  - `season` (e.g., '2023-24')
  - `match_date`
  - `home_team_id`, `away_team_id` (references `teams` table)
  - `home_goals`, `away_goals`
  - `result` (H/D/A)
  - `odds_home`, `odds_draw`, `odds_away`
  - `prob_home_market`, `prob_draw_market`, `prob_away_market`
  - `source` (e.g., 'football-data.co.uk')

**Supporting Tables:**
- `data_sources`: Tracks external data sources
- `ingestion_logs`: Logs each ingestion job with statistics
- `teams`: Team registry (auto-created during ingestion)
- `leagues`: League reference data

### ❌ **CSV Files are NOT Saved to Disk**

**Current Implementation:**
- CSV content is downloaded from football-data.co.uk
- Parsed in-memory (`io.StringIO`)
- Data is inserted directly into database
- **CSV files are saved to `data/1_data_ingestion/` folder**

**Backend Code Location:**
- `app/services/data_ingestion.py` → `ingest_from_football_data()`
- Downloads CSV via HTTP request
- Parses and inserts into `matches` table
- No file system write operations

---

## 3. Batch Files and Batch Numbers

### Current State

**Frontend:**
- Tracks batches in memory (`DownloadBatch[]` array)
- Batch numbers start at 1000 and increment
- Each batch contains:
  - `batchNumber`: Sequential ID
  - `sources`: Which leagues were downloaded
  - `totalRecords`: Total records in batch
  - `timestamp`: When batch completed

**Backend:**
- `ingestion_logs` table tracks each ingestion job
- Each log has:
  - `id`: Auto-increment primary key
  - `source_id`: Reference to data source
  - `records_processed`, `records_inserted`, `records_updated`
  - `status`: 'running', 'completed', 'failed'
  - `started_at`, `completed_at`

### ❌ **No CSV Files Saved by Batch Number**

There is **NO** implementation that:
- Saves CSV files to `data/1_data_ingestion/`
- Names files with batch numbers (e.g., `batch_1000_E0_2324.csv`)
- Organizes files by batch

**If you want CSV files saved**, you would need to add code like:
```python
# In data_ingestion.py
import os
from pathlib import Path

def ingest_from_football_data(self, league_code: str, season: str):
    csv_content = self.download_from_football_data(league_code, season)
    
    # Save CSV file (NEW CODE NEEDED)
    batch_dir = Path("data/1_data_ingestion")
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_number = self.get_next_batch_number()  # Would need to implement
    filename = f"batch_{batch_number}_{league_code}_{season}.csv"
    filepath = batch_dir / filename
    filepath.write_text(csv_content, encoding='utf-8')
    
    # Then ingest to database
    return self.ingest_csv(csv_content, league_code, season)
```

---

## 4. How Far Back Can Data Go? Model Training Recommendations

### Available Data Range

**Football-Data.co.uk Coverage:**
- **Premier League (E0)**: ~1993-94 onwards (30+ years)
- **Championship (E1)**: ~2000-01 onwards (24+ years)
- **La Liga (SP1)**: ~2000-01 onwards (24+ years)
- **Bundesliga (D1)**: ~1993-94 onwards (30+ years)
- **Serie A (I1)**: ~1993-94 onwards (30+ years)
- **Ligue 1 (F1)**: ~1995-96 onwards (29+ years)

**Frontend UI Shows:**
- Individual seasons: 2020-21, 2021-22, 2022-23, 2023-24, 2024-25
- "All Seasons" option (but not implemented)
- Data sources show `seasons: '2018-2024'` (6-7 years)

### Model Training Recommendations

**From Architecture Document** (`jackpot_system_architecture.md`):

**Minimum Viable Dataset:**
- **5+ seasons per league** (ideally 8-10 seasons)
- **Coverage**: Top 6-8 European leagues minimum
- **Total matches**: ~40,000+ matches for robust training

**Recommended Training Window:**
- **5-7 years** is optimal for most leagues
- **Why not more?**
  - Team compositions change significantly over 10+ years
  - League dynamics evolve (tactics, rules, competitiveness)
  - Older data has less predictive value (time decay parameter ξ = 0.0065)
  - Diminishing returns beyond 7-8 seasons

**Why not less?**
- < 3 seasons: Insufficient for team strength estimation
- < 5 seasons: Higher variance in model parameters
- 5-7 seasons: Sweet spot for stability vs. relevance

**Current System Training Data:**
- Mock data shows: `seasons: '2018-2024'` (6-7 years)
- This aligns with recommendations ✅

---

## 5. "All Seasons" Selection - How Far Back?

### Current Implementation

**Frontend (`DataIngestion.tsx` line 332):**
```tsx
<SelectItem value="all">All Seasons</SelectItem>
```

**Problem:** The `selectedSeason` state is set to `'all'`, but:
- ❌ No backend API call is made
- ❌ No logic to iterate through multiple seasons
- ❌ No season range is defined

### What "All Seasons" SHOULD Do

When "all" is selected, the system should:

1. **Define Season Range:**
   - Start: 2018-19 (or earliest available)
   - End: Current season (2024-25)
   - Total: ~7 seasons

2. **Download Each Season:**
   ```python
   # Pseudo-code for backend
   seasons = ['1819', '1920', '2021', '2122', '2223', '2324', '2425']
   for season in seasons:
       for league_code in selected_leagues:
           ingest_from_football_data(league_code, season)
   ```

3. **Batch Tracking:**
   - Could create one batch per season
   - Or one batch for all seasons combined
   - Each batch logged in `ingestion_logs` table

### Estimated Data Volume for "All Seasons"

**Per League (Premier League example):**
- ~380 matches per season
- 7 seasons = ~2,660 matches per league
- 10 leagues = ~26,600 matches total

**Download Time:**
- ~1-2 seconds per CSV download
- 10 leagues × 7 seasons = 70 downloads
- Total: ~2-3 minutes (sequential) or ~30 seconds (parallel)

---

## Summary & Recommendations

### Current State
- ✅ Database schema ready (`matches`, `ingestion_logs` tables)
- ✅ Backend service ready (`DataIngestionService`)
- ✅ API endpoint exists (`POST /api/data/refresh`)
- ❌ Frontend not connected to backend (mock only)
- ❌ CSV files not saved to disk
- ❌ "All Seasons" not implemented
- ❌ Batch file organization not implemented

### Recommended Next Steps

1. **Connect Frontend to Backend:**
   - Replace mock `startDownload()` with actual API call
   - Call `POST /api/data/refresh` for each selected source
   - Handle season selection (single vs. "all")

2. **Implement "All Seasons" Logic:**
   - Backend: Add endpoint that accepts `season: "all"`
   - Backend: Define season range (2018-19 to current)
   - Backend: Loop through all seasons for selected leagues

3. **Optional: Save CSV Files:**
   - Add file writing logic to `data_ingestion.py`
   - Organize by batch number: `data/1_data_ingestion/batch_{N}/{league}_{season}.csv`
   - Useful for backup/audit purposes

4. **Batch Number Management:**
   - Use `ingestion_logs.id` as batch number (or separate sequence)
   - Link frontend batch display to backend `ingestion_logs` table
   - Show real statistics instead of mock data

### Recommended Training Data Range

**For Model Training:**
- **5-7 years** (2018-2024) ✅ **RECOMMENDED**
- This provides:
  - ~40,000+ matches across top leagues
  - Recent enough to be relevant
  - Old enough for statistical stability
  - Optimal balance for Dixon-Coles model

**Maximum Practical Range:**
- **10 years** (2015-2024) - Still useful but diminishing returns
- **15+ years** - Not recommended (too much change over time)

---

## Database Tables Reference

### `matches` Table (Primary Storage)
```sql
CREATE TABLE matches (
    id BIGSERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(id),
    season VARCHAR NOT NULL,              -- '2023-24'
    match_date DATE NOT NULL,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    result match_result NOT NULL,         -- 'H', 'D', 'A'
    odds_home DOUBLE PRECISION,
    odds_draw DOUBLE PRECISION,
    odds_away DOUBLE PRECISION,
    prob_home_market DOUBLE PRECISION,
    prob_draw_market DOUBLE PRECISION,
    prob_away_market DOUBLE PRECISION,
    source VARCHAR DEFAULT 'football-data.co.uk',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (home_team_id, away_team_id, match_date)
);
```

### `ingestion_logs` Table (Batch Tracking)
```sql
CREATE TABLE ingestion_logs (
    id SERIAL PRIMARY KEY,                -- This could be batch number
    source_id INTEGER REFERENCES data_sources(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status VARCHAR DEFAULT 'running',     -- 'running', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    logs JSONB
);
```

---

## File Locations

- **Frontend:** `1_Frontend_Football_Probability_Engine/src/pages/DataIngestion.tsx`
- **Backend Service:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py`
- **Backend API:** `2_Backend_Football_Probability_Engine/app/api/data.py`
- **Database Schema:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
- **Data Folder:** `2_Backend_Football_Probability_Engine/data/1_data_ingestion/`

