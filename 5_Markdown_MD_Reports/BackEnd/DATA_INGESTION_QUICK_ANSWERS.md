# Data Ingestion - Quick Answers

## Your Questions Answered

### 1. What happens when I click "Download Selected"?

**Current State:** ❌ **NOTHING REAL HAPPENS**
- Frontend only simulates download (mock progress bars)
- No backend API call is made
- No data is actually downloaded or saved
- Batch records exist only in browser memory

**What Should Happen:**
- Frontend calls `POST /api/data/refresh` with league code and season
- Backend downloads CSV from football-data.co.uk
- Backend parses CSV and saves to database `matches` table
- Batch logged in `ingestion_logs` table

---

### 2. Where is data saved? What database tables?

**✅ Data is saved to PostgreSQL database:**

**Primary Table:** `matches`
- All historical match data stored here
- Includes: date, teams, scores, odds, probabilities

**Supporting Tables:**
- `ingestion_logs` - Tracks each download batch
- `data_sources` - Registry of data sources
- `teams` - Team registry (auto-created)
- `leagues` - League reference data

**❌ CSV files are NOT saved to disk**
- CSV files saved to `data/1_data_ingestion/` folder
- CSV content is downloaded, parsed in-memory, then discarded
- Only database records are persisted

---

### 3. Are CSV files saved by batch number?

**❌ NO - CSV files are NOT saved**

**Current Implementation:**
- CSV downloaded → Parsed → Database inserted → CSV discarded
- No file system writes
- No batch-organized folders

**If you want CSV files saved:**
- Would need to add code to write files like:
  - `data/1_data_ingestion/batch_1000/E0_2324.csv`
  - `data/1_data_ingestion/batch_1000/SP1_2324.csv`
- Currently not implemented

**Batch Tracking:**
- Frontend: Batch numbers in memory (starts at 1000)
- Backend: `ingestion_logs.id` could serve as batch number
- Not currently linked together

---

### 4. For model training, how far back can data go? Recommended years?

**Available Data:**
- Football-Data.co.uk has data going back **20-30 years** for major leagues
- Premier League: ~1993 onwards (30+ years)
- La Liga, Bundesliga: ~2000 onwards (24+ years)

**Recommended for Model Training:**
- ✅ **5-7 years** (2018-2024) - **OPTIMAL**
- ✅ **8-10 years** - Still good, but diminishing returns
- ❌ **15+ years** - Not recommended (too much change over time)

**Why 5-7 years?**
- Recent enough to be relevant (team compositions, tactics)
- Old enough for statistical stability
- Optimal balance for Dixon-Coles model
- ~40,000+ matches across top leagues

**Current System:**
- Frontend shows: `seasons: '2018-2024'` (6-7 years) ✅
- This aligns with recommendations

---

### 5. When selecting "All Seasons", how far back does it download?

**Current State:** ❌ **NOT IMPLEMENTED**

**Frontend:**
- Has "All Seasons" dropdown option
- But no backend logic to handle it
- No season range defined

**What "All Seasons" SHOULD Do:**
- Download seasons: **2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25**
- Total: **~7 seasons** per league
- For 10 leagues: **~26,600 matches** total
- Download time: **~2-3 minutes** (sequential) or **~30 seconds** (parallel)

**Season Format:**
- Football-Data.co.uk uses: `1819`, `1920`, `2021`, `2122`, `2223`, `2324`, `2425`
- URL format: `https://www.football-data.co.uk/mmz4281/{season}/{league}.csv`
- Example: `https://www.football-data.co.uk/mmz4281/2324/E0.csv` (Premier League 2023-24)

---

## Summary Table

| Question | Answer | Status |
|----------|--------|--------|
| **Where is data saved?** | PostgreSQL `matches` table | ✅ Implemented |
| **CSV files saved?** | No, only database | ✅ Current behavior |
| **Batch files organized?** | No, not implemented | ❌ Missing |
| **How far back?** | 5-7 years recommended (2018-2024) | ✅ Recommended |
| **"All Seasons" works?** | No, not implemented | ❌ Missing |
| **Frontend connected?** | No, mock only | ❌ Missing |

---

## Next Steps to Fix

1. **Connect Frontend to Backend** (Priority 1)
   - Replace mock `startDownload()` with API call
   - Call `POST /api/data/refresh` for each selected source

2. **Implement "All Seasons"** (Priority 2)
   - Backend: Handle `season: "all"` parameter
   - Loop through seasons 2018-19 to 2024-25

3. **Optional: Save CSV Files** (Priority 3)
   - CSV files saved to `data/1_data_ingestion/batch_{N}/`
   - Organize by batch number

4. **Link Batch Numbers** (Priority 4)
   - Use `ingestion_logs.id` as batch number
   - Connect frontend batch display to backend logs

---

## Database Query Examples

**Check downloaded matches:**
```sql
SELECT COUNT(*), season, league_id 
FROM matches 
GROUP BY season, league_id 
ORDER BY season DESC;
```

**Check ingestion logs (batches):**
```sql
SELECT id, started_at, records_inserted, records_updated, status
FROM ingestion_logs
ORDER BY started_at DESC
LIMIT 10;
```

**Check data source status:**
```sql
SELECT name, status, last_sync_at, record_count
FROM data_sources;
```

