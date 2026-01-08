# Data Ingestion - Duplicate Prevention & File Checking

## Question 1: Does the system check if files are already ingested?

### **Answer: PARTIALLY - It checks database, NOT files**

### Current Behavior:

#### ✅ **Database-Level Checking:**
- **Checks database** for existing matches by `(home_team_id, away_team_id, match_date)`
- **UPDATES existing matches** (doesn't skip them)
- Uses `ON CONFLICT DO UPDATE` in SQL

#### ❌ **File-Level Checking:**
- **Does NOT check** if CSV files already exist in folders
- **Does NOT check** `source_file` or `ingestion_batch_id` to skip files
- **Re-downloads** CSV files even if they exist
- **Overwrites** existing CSV files in batch folders

### Code Location: `app/services/data_ingestion.py`

```python
# Line 372-388: Match duplicate checking
existing_match = self.db.query(Match).filter(
    Match.home_team_id == home_team.id,
    Match.away_team_id == away_team.id,
    Match.match_date == match_date
).first()

if existing_match:
    # UPDATE existing match (odds, probabilities)
    existing_match.odds_home = odds_home
    existing_match.odds_draw = odds_draw
    # ... updates other fields
    stats["updated"] += 1
else:
    # INSERT new match
    match = Match(...)
    stats["inserted"] += 1
```

### What This Means:

**If you download the same league/season again:**
- ✅ **Database:** Existing matches are **UPDATED** (not skipped)
- ⚠️ **Files:** CSV files are **RE-DOWNLOADED** and **OVERWRITTEN**

**If you download new data:**
- ✅ **Database:** New matches are **INSERTED**
- ✅ **Files:** New CSV files are **CREATED**

---

## Question 2: How does migration work with SQL export files?

### **Answer: You need a different approach**

The `MIGRATE_FROM_OLD_DB.sql` script assumes a **live database connection**, but you only have **SQL export files**.

### **Solution: Use Python Script**

I've created `import_from_sql_exports.py` which:
- ✅ Reads SQL INSERT statements from export files
- ✅ Parses and extracts data
- ✅ Maps old IDs to new IDs
- ✅ Uses `ON CONFLICT DO UPDATE` to prevent duplicates
- ✅ Preserves foreign key relationships

---

## How to Import from SQL Export Files

### **Option A: Manual SQL Import (Recommended for Small Data)**

1. **Open each SQL file** in pgAdmin
2. **Modify INSERT statements** to use `ON CONFLICT DO UPDATE`
3. **Remove ID columns** (let database auto-generate)
4. **Map foreign keys** manually

**Example:**
```sql
-- Original (from export):
INSERT INTO public.leagues (id, code, name, ...) VALUES (1, 'E0', 'Premier League', ...);

-- Modified (for import):
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
VALUES ('E0', 'Premier League', 'England', 1, 0.26, 0.35, true)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    updated_at = now();
```

### **Option B: Python Script (Recommended for Large Data)**

```bash
cd "3_Database_Football_Probability_Engine/migrations"
python import_from_sql_exports.py \
    --export-dir "C:\Users\Admin\Desktop\Exported_Football _DB" \
    --db-url "postgresql://postgres:password@localhost/football_probability_engine"
```

**What it does:**
- ✅ Reads SQL files automatically
- ✅ Parses INSERT statements
- ✅ Maps IDs automatically
- ✅ Handles duplicates with `ON CONFLICT`

---

## What to Import vs Re-Ingest

### ✅ **IMPORT from SQL Files:**
- `models` - Trained models (valuable)
- `calibration_data` - Calibration curves (valuable)
- `league_draw_priors` - Historical draw rates
- `h2h_draw_stats` - H2H statistics
- `team_elo` - Elo ratings
- `referee_stats` - Referee statistics
- `league_structure` - League metadata
- `jackpots` - User-created jackpots
- `saved_jackpot_templates` - User templates
- `saved_probability_results` - User results
- `training_runs` - Training history

### ❌ **RE-INGEST (Don't Import):**
- `matches` - Missing 11 new columns
- `teams` - Missing `alternative_names`, better normalization
- `leagues` - Better to re-ingest for consistency

---

## Recommended Workflow

### **Step 1: Run New Schema**
```sql
-- In pgAdmin
-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)
```

### **Step 2: Import Valuable Data**
```bash
# Option A: Use Python script
python import_from_sql_exports.py --export-dir "C:\Users\Admin\Desktop\Exported_Football _DB"

# Option B: Manual SQL import (for specific tables)
# Open each SQL file, modify INSERT statements, run in pgAdmin
```

### **Step 3: Re-Ingest Matches/Teams/Leagues**
```bash
cd "15_Football_Data_/01_extruction_Script"
python extract_football_data.py --data-dir .. --output-dir output

cd "../02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

### **Step 4: Update Foreign Keys**
```sql
-- Update foreign keys in imported tables
-- (team_id, league_id, model_id mappings)
```

### **Step 5: Recalculate Statistics**
```bash
python update_league_statistics.py
```

---

## Summary

### **Ingestion System:**
- ✅ Checks **database** for duplicates (updates existing)
- ❌ Does **NOT** check **files** (re-downloads everything)
- ✅ Uses `ON CONFLICT DO UPDATE` to prevent duplicates

### **Migration from SQL Files:**
- ✅ Use `import_from_sql_exports.py` for automated import
- ✅ Or manually modify SQL files and import
- ✅ Map IDs to preserve relationships
- ✅ Use `ON CONFLICT` to prevent duplicates

---

## Files Created

1. ✅ `import_from_sql_exports.py` - Automated import script
2. ✅ `IMPORT_FROM_SQL_EXPORTS.sql` - Manual SQL template
3. ✅ `INGESTION_DUPLICATE_PREVENTION.md` - This document

