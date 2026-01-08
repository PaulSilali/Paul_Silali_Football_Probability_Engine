# Ingestion & Migration Guide

## Question 1: Does ingestion check if files are already ingested?

### **Answer: PARTIALLY**

#### ✅ **What It Checks:**
- **Database:** Checks for existing matches by `(home_team_id, away_team_id, match_date)`
- **Updates existing matches** (doesn't skip them)
- Uses `ON CONFLICT DO UPDATE` in SQL

#### ❌ **What It Doesn't Check:**
- **File system:** Does NOT check if CSV files already exist
- **Source tracking:** Does NOT check `source_file` or `ingestion_batch_id` to skip files
- **Re-downloads:** Downloads CSV files even if they exist in folders
- **Overwrites:** Overwrites existing CSV files

### **Current Behavior:**

**When you download data:**
1. ✅ **Downloads CSV** from football-data.co.uk (even if file exists locally)
2. ✅ **Saves CSV** to `data/1_data_ingestion/batch_XXX/` folder (overwrites if exists)
3. ✅ **Checks database** for existing matches
4. ✅ **Updates existing matches** (odds, probabilities)
5. ✅ **Inserts new matches**

**Example from DOWNLOAD_LOG.txt:**
```
✓ E0 - Season: last10 (Batch #399)
  Records: 3,620 processed, 1,144 inserted, 2,470 updated, 6 skipped
```

This means:
- **1,144** new matches inserted
- **2,470** existing matches updated
- **6** invalid rows skipped

---

## Question 2: How to migrate from SQL export files?

### **Answer: You have SQL files, not a live database**

The original `MIGRATE_FROM_OLD_DB.sql` assumes a **live database connection**, but you only have **SQL export files** in `C:\Users\Admin\Desktop\Exported_Football _DB`.

### **Solution: Two Options**

#### **Option A: Manual SQL Import (Simple, for small data)**

1. **Open each SQL file** in pgAdmin
2. **Modify INSERT statements:**
   - Remove `id` column (let database auto-generate)
   - Add `ON CONFLICT DO UPDATE` clause
   - Map foreign keys using subqueries

**Example:**
```sql
-- Original (from export):
INSERT INTO public.leagues (id, code, name, country, ...) 
VALUES (1, 'E0', 'Premier League', 'England', ...);

-- Modified (for import):
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
VALUES ('E0', 'Premier League', 'England', 1, 0.26, 0.35, true)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    updated_at = now();
```

#### **Option B: Python Script (Automated, for large data)**

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

## Recommended Workflow

### **Step 1: Run New Schema**
```sql
-- In pgAdmin
-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)
```

### **Step 2: Import Valuable Data from SQL Files**

**For Small Data (Manual):**
1. Open `leagues_202601081444.sql` in pgAdmin
2. Copy INSERT statements
3. Modify to remove `id` and add `ON CONFLICT`
4. Execute

**For Large Data (Automated):**
```bash
python import_from_sql_exports.py --export-dir "C:\Users\Admin\Desktop\Exported_Football _DB"
```

**What to Import:**
- ✅ `models` - Trained models
- ✅ `calibration_data` - Calibration curves
- ✅ `league_draw_priors` - Historical draw rates
- ✅ `h2h_draw_stats` - H2H statistics
- ✅ `team_elo` - Elo ratings
- ✅ `referee_stats` - Referee statistics
- ✅ `league_structure` - League metadata
- ✅ `jackpots` & `jackpot_fixtures` - User data
- ✅ `saved_jackpot_templates` - User templates
- ✅ `saved_probability_results` - User results
- ✅ `training_runs` - Training history

**What NOT to Import:**
- ❌ `matches` - Re-ingest to get new columns
- ❌ `teams` - Re-ingest for better normalization
- ❌ `leagues` - Re-ingest for consistency

### **Step 3: Re-Ingest Matches/Teams/Leagues**
```bash
cd "15_Football_Data_/01_extruction_Script"
python extract_football_data.py --data-dir .. --output-dir output

cd "../02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

### **Step 4: Update Foreign Keys**
After re-ingesting, update foreign keys in imported tables:
```sql
-- Example: Update calibration_data model_id
UPDATE calibration_data cd
SET model_id = m.id
FROM models m
WHERE cd.model_id IS NULL  -- Or use old mapping
AND m.version = 'v1.0.0';
```

### **Step 5: Recalculate Statistics**
```bash
python update_league_statistics.py
```

---

## Duplicate Prevention Summary

### **Database Level:**
- ✅ Unique constraints prevent duplicates
- ✅ `ON CONFLICT DO UPDATE` updates existing records
- ✅ `DISTINCT ON` removes duplicates at staging

### **File Level:**
- ❌ Does NOT check if files exist
- ❌ Re-downloads and overwrites CSV files
- ⚠️ Consider adding file checking if needed

### **Ingestion Level:**
- ✅ Checks database for existing matches
- ✅ Updates existing matches (odds, probabilities)
- ✅ Inserts new matches
- ❌ Does NOT check `source_file` to skip files

---

## Files Created

1. ✅ `import_from_sql_exports.py` - Automated import script
2. ✅ `IMPORT_FROM_SQL_EXPORTS.sql` - Manual SQL template
3. ✅ `IMPORT_SQL_EXPORTS_SIMPLE.sql` - Simplified template
4. ✅ `INGESTION_DUPLICATE_PREVENTION.md` - Detailed explanation
5. ✅ `INGESTION_AND_MIGRATION_GUIDE.md` - This file

---

## Quick Answer

**Q1: Does ingestion check if files are already ingested?**
- ✅ **Database:** Yes, checks and updates existing matches
- ❌ **Files:** No, re-downloads and overwrites CSV files

**Q2: How to migrate from SQL export files?**
- ✅ **Option A:** Manually modify SQL files and import
- ✅ **Option B:** Use `import_from_sql_exports.py` for automated import

