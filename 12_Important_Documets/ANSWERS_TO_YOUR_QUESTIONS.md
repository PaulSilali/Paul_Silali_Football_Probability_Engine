# Answers to Your Questions

## Question 1: Does ingestion check if files are already ingested?

### **Answer: PARTIALLY**

#### ✅ **What It Checks:**
- **Database:** Checks for existing matches by `(home_team_id, away_team_id, match_date)`
- **Updates existing matches** (doesn't skip them)
- Uses `ON CONFLICT DO UPDATE` in SQL

#### ❌ **What It Doesn't Check:**
- **File system:** Does NOT check if CSV files already exist in folders
- **Source tracking:** Does NOT check `source_file` or `ingestion_batch_id` to skip files
- **Re-downloads:** Downloads CSV files even if they exist locally
- **Overwrites:** Overwrites existing CSV files in batch folders

### **Current Behavior:**

**When you download data:**
1. ✅ Downloads CSV from football-data.co.uk (even if file exists locally)
2. ✅ Saves CSV to `data/1_data_ingestion/batch_XXX/` folder (overwrites if exists)
3. ✅ Checks database for existing matches
4. ✅ Updates existing matches (odds, probabilities)
5. ✅ Inserts new matches

**Example from your DOWNLOAD_LOG.txt:**
```
✓ E0 - Season: last10 (Batch #399)
  Records: 3,620 processed, 1,144 inserted, 2,470 updated, 6 skipped
```

This means:
- **1,144** new matches inserted
- **2,470** existing matches updated (not skipped!)
- **6** invalid rows skipped

**So the system:**
- ✅ **Prevents duplicate matches** in database (updates instead)
- ❌ **Does NOT skip files** (re-downloads and overwrites CSV files)
- ❌ **Does NOT check** `source_file` to skip already-ingested files

---

## Question 2: How does migration work with SQL export files?

### **Answer: You need a different approach**

The original `MIGRATE_FROM_OLD_DB.sql` assumes a **live database connection**, but you only have **SQL export files** in `C:\Users\Admin\Desktop\Exported_Football _DB`.

### **Solution: Two Options**

#### **Option A: Manual Import (Simple, Recommended)**

1. **Open each SQL file** in pgAdmin
2. **Modify INSERT statements:**
   - Remove `id` column (first column)
   - Add `ON CONFLICT DO UPDATE` clause
   - Map foreign keys using subqueries

**Example for jackpots:**
```sql
-- Original (from export):
INSERT INTO public.jackpots (id, jackpot_id, user_id, name, ...) 
VALUES (14, 'JK-1767544221', 'anonymous', 'ODI Bets', ...);

-- Modified (for import):
INSERT INTO jackpots (jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at)
VALUES ('JK-1767544221', 'anonymous', 'ODI Bets', NULL, 'draft', 'v2.4.1', '2026-01-04 19:30:21.8007+03', '2026-01-04 19:30:21.8007+03')
ON CONFLICT (jackpot_id) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    updated_at = now();
```

#### **Option B: Python Script (Automated)**

```bash
cd "3_Database_Football_Probability_Engine/migrations"
python import_from_sql_exports.py \
    --export-dir "C:\Users\Admin\Desktop\Exported_Football _DB" \
    --db-url "postgresql://postgres:password@localhost/football_probability_engine"
```

**Note:** The Python script is a template - you may need to customize it for your specific export format.

---

## Recommended Workflow

### **Step 1: Run New Schema**
```sql
-- In pgAdmin
-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)
```

### **Step 2: Import Simple Tables (No Dependencies)**
Import these first (they have no foreign keys):
- ✅ `jackpots` - User-created jackpots
- ✅ `saved_jackpot_templates` - User templates
- ✅ `saved_probability_results` - User results
- ✅ `referee_stats` - Referee statistics

**How:**
1. Open SQL file in pgAdmin
2. Copy INSERT statements
3. Remove `id` column
4. Add `ON CONFLICT` clause
5. Execute

### **Step 3: Re-Ingest Core Data**
```bash
cd "15_Football_Data_/01_extruction_Script"
python extract_football_data.py --data-dir .. --output-dir output

cd "../02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

This will:
- ✅ Re-populate `matches` (with all new columns)
- ✅ Re-populate `teams` (with better normalization)
- ✅ Re-populate `leagues` (for consistency)

### **Step 4: Import Tables with Foreign Keys**
After re-ingesting, import:
- ✅ `models` - Trained models
- ✅ `calibration_data` - Calibration curves (map model_id)
- ✅ `league_draw_priors` - Historical draw rates (map league_id)
- ✅ `h2h_draw_stats` - H2H statistics (map team_id)
- ✅ `team_elo` - Elo ratings (map team_id)
- ✅ `league_structure` - League metadata (map league_id)
- ✅ `jackpot_fixtures` - Fixtures (map team_id, league_id)

**How:**
- Use subqueries to map foreign keys:
  ```sql
  (SELECT id FROM leagues WHERE code = 'E0') as league_id
  (SELECT id FROM teams WHERE canonical_name = 'brighton' AND league_id = ...) as team_id
  ```

### **Step 5: Update Statistics**
```bash
python update_league_statistics.py
```

---

## Summary

### **Q1: Does ingestion check if files are already ingested?**
- ✅ **Database:** Yes, checks and updates existing matches
- ❌ **Files:** No, re-downloads and overwrites CSV files
- ❌ **Source tracking:** No, doesn't check `source_file` to skip files

### **Q2: How to migrate from SQL export files?**
- ✅ **Option A:** Manually modify SQL files and import (simple)
- ✅ **Option B:** Use Python script for automated import (complex)
- ✅ **Recommended:** Import simple tables first, re-ingest core data, then import tables with foreign keys

---

## Files Created

1. ✅ `import_from_sql_exports.py` - Automated import script
2. ✅ `IMPORT_SQL_EXPORTS_SIMPLE.sql` - Simple template
3. ✅ `QUICK_IMPORT_FROM_SQL_EXPORTS.md` - Quick guide
4. ✅ `INGESTION_AND_MIGRATION_GUIDE.md` - Complete guide
5. ✅ `ANSWERS_TO_YOUR_QUESTIONS.md` - This file

