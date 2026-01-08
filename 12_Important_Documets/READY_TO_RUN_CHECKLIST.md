# Ready to Run Checklist ✅

## Pre-Flight Check

### ✅ Schema File
- [x] `3_Database_Football_Probability_Engine.sql` - Complete with all migrations
- [x] Includes entropy metrics, draw model support, unique indexes
- [x] All 43 leagues included
- [x] Ready to run on existing database

### ✅ Data Ingestion Services
- [x] `populate_database.py` - Updated with all new columns
- [x] `extract_football_data.py` - Updated CSV output with new columns
- [x] Staging table includes all new columns
- [x] INSERT statements handle all new columns
- [x] ON CONFLICT clauses updated

### ✅ Duplicate Prevention
- [x] Database constraints (UNIQUE on key columns)
- [x] ON CONFLICT DO UPDATE (idempotent operations)
- [x] DISTINCT ON in SQL queries
- [x] Team name normalization

### ✅ Migration Scripts
- [x] `MIGRATE_FROM_OLD_DB.sql` - For borrowing data
- [x] ID mapping logic included
- [x] Verification queries included

### ✅ Documentation
- [x] `FINAL_DEEP_SCAN_ANALYSIS.md` - Complete analysis
- [x] `MIGRATION_DECISION_GUIDE.md` - Decision tree
- [x] `SUMMARY_OF_CHANGES.md` - Summary of changes
- [x] `READY_TO_RUN_CHECKLIST.md` - This file

---

## Decision: Which Approach?

### Option 1: Full Re-Ingestion
**Use if:** You don't have valuable trained models or want a fresh start

**Steps:**
1. Run schema: `3_Database_Football_Probability_Engine.sql`
2. Extract data: `extract_football_data.py`
3. Populate database: `populate_database.py`
4. Train models: `model_training.py`
5. Update statistics: `update_league_statistics.py`

### Option 2: Hybrid Approach
**Use if:** You have trained models you want to preserve

**Steps:**
1. Run schema: `3_Database_Football_Probability_Engine.sql`
2. Migrate data: `MIGRATE_FROM_OLD_DB.sql` (with ID mapping)
3. Re-ingest matches/teams/leagues: `populate_database.py`
4. Update foreign keys in migrated tables
5. Recalculate statistics: `update_league_statistics.py`

---

## Execution Steps

### Step 1: Run Schema
```sql
-- In pgAdmin, connect to football_probability_engine
-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)
```

### Step 2: Choose Your Path

#### Path A: Full Re-Ingestion
```bash
# Extract data
cd "15_Football_Data_/01_extruction_Script"
python extract_football_data.py --data-dir .. --output-dir output

# Populate database
cd "../02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

#### Path B: Hybrid Approach
```sql
-- First, migrate valuable data
-- Update MIGRATE_FROM_OLD_DB.sql with your old database connection
-- Run in pgAdmin
```

Then:
```bash
# Re-ingest matches/teams/leagues
cd "15_Football_Data_/02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

### Step 3: Update Statistics
```bash
cd "15_Football_Data_/02_Db populating_Script"
python update_league_statistics.py
```

### Step 4: Verify
```sql
-- Check table counts
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM leagues;

-- Check new columns
SELECT COUNT(*) FROM matches WHERE ht_home_goals IS NOT NULL;
SELECT COUNT(*) FROM teams WHERE alternative_names IS NOT NULL;
```

---

## What's Protected

### ✅ Duplicate Prevention:
- Unique constraints prevent duplicates
- ON CONFLICT DO UPDATE updates existing records
- DISTINCT ON removes duplicates at staging level
- Team name normalization ensures consistent matching

### ✅ Data Accuracy:
- Team name normalization improves matching
- Source file tracking enables data lineage
- Half-time scores preserved when available
- All new columns properly handled

---

## Files Updated

1. ✅ `3_Database_Football_Probability_Engine.sql` - Complete schema
2. ✅ `populate_database.py` - Updated with new columns
3. ✅ `extract_football_data.py` - Updated CSV output
4. ✅ `MIGRATE_FROM_OLD_DB.sql` - Migration script
5. ✅ All documentation files

---

## ✅ READY TO RUN!

All systems are go. Choose your approach and follow the steps above.

