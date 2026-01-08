# Database Rebuild Guide

## Overview

This guide provides step-by-step instructions for rebuilding the database from scratch with all migrations applied.

---

## Prerequisites

1. **PostgreSQL installed and running**
2. **Backup of current database** (if you want to preserve data)
3. **All migration files** in `3_Database_Football_Probability_Engine/migrations/`
4. **Python environment** with required packages

---

## Step-by-Step Process

### **Step 1: Backup Current Database (Optional but Recommended)**

```bash
pg_dump -U postgres -d football_probability_engine > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### **Step 2: Rebuild Database**

#### **Option A: Using Batch Script (Windows)**

```bash
cd "3_Database_Football_Probability_Engine"
rebuild_database.bat
```

#### **Option B: Using SQL Script (Manual)**

```bash
cd "3_Database_Football_Probability_Engine"
psql -U postgres -f rebuild_database.sql
```

#### **Option C: Manual Steps**

1. **Drop database:**
   ```sql
   psql -U postgres -c "DROP DATABASE IF EXISTS football_probability_engine;"
   ```

2. **Create database:**
   ```sql
   psql -U postgres -c "CREATE DATABASE football_probability_engine;"
   ```

3. **Run main schema:**
   ```bash
   psql -U postgres -d football_probability_engine -f 3_Database_Football_Probability_Engine.sql
   ```

4. **Run all migrations:**
   ```bash
   psql -U postgres -d football_probability_engine -f migrations/4_ALL_LEAGUES_FOOTBALL_DATA.sql
   psql -U postgres -d football_probability_engine -f migrations/2025_01_draw_structural_extensions.sql
   psql -U postgres -d football_probability_engine -f migrations/2025_01_add_historical_tables.sql
   psql -U postgres -d football_probability_engine -f migrations/2025_01_add_league_structure.sql
   psql -U postgres -d football_probability_engine -f migrations/2025_01_add_odds_movement_historical.sql
   psql -U postgres -d football_probability_engine -f migrations/2025_01_add_xg_data.sql
   psql -U postgres -d football_probability_engine -f migrations/add_h2h_stats.sql
   psql -U postgres -d football_probability_engine -f migrations/add_saved_jackpot_templates.sql
   psql -U postgres -d football_probability_engine -f migrations/add_saved_probability_results.sql
   psql -U postgres -d football_probability_engine -f migrations/add_entropy_metrics.sql
   psql -U postgres -d football_probability_engine -f migrations/add_unique_partial_index_models.sql
   psql -U postgres -d football_probability_engine -f migrations/add_draw_model_support.sql
   psql -U postgres -d football_probability_engine -f migrations/fix_matchresult_enum.sql
   ```

---

### **Step 3: Verify Database Structure**

Run verification queries:

```sql
-- Count tables
SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';

-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Verify critical tables
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
    'predictions', 'models', 'training_runs', 'league_draw_priors',
    'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
    'referee_stats', 'team_rest_days', 'team_rest_days_historical',
    'odds_movement', 'odds_movement_historical', 'league_structure',
    'match_xg', 'match_xg_historical'
)
ORDER BY tablename;

-- Verify matches columns
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'matches' AND table_schema = 'public'
ORDER BY column_name;

-- Verify teams columns
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'teams' AND table_schema = 'public'
ORDER BY column_name;
```

---

### **Step 4: Re-Ingest Data**

1. **Extract data from Football.TXT files:**
   ```bash
   cd "15_Football_Data_/01_extruction_Script"
   python extract_football_data.py
   ```

2. **Populate database:**
   ```bash
   cd "15_Football_Data_/02_Db populating_Script"
   python populate_database.py <path_to_extracted_csv>
   ```

---

### **Step 5: Train Model and Update Statistics**

1. **Update league statistics:**
   ```bash
   cd "15_Football_Data_/02_Db populating_Script"
   python update_league_statistics.py
   ```

2. **Train model and update team ratings:**
   ```bash
   cd "15_Football_Data_/02_Db populating_Script"
   python update_teams_ratings.py
   ```

---

## Verification Checklist

After rebuild, verify:

- [ ] All 32 tables created
- [ ] All migrations applied
- [ ] All indexes created
- [ ] All constraints created
- [ ] Matches table has all 11 new columns
- [ ] Teams table has `alternative_names` column
- [ ] Data ingested successfully
- [ ] League statistics calculated
- [ ] Team ratings populated

---

## Troubleshooting

### **Error: "relation does not exist"**
- **Cause:** Migration not applied
- **Fix:** Run missing migration manually

### **Error: "column does not exist"**
- **Cause:** Column not added to model
- **Fix:** Check `models.py` has all columns

### **Error: "duplicate key value"**
- **Cause:** Data already exists
- **Fix:** Drop and recreate database

### **Error: "permission denied"**
- **Cause:** Insufficient database permissions
- **Fix:** Run as PostgreSQL superuser

---

## Post-Rebuild Tasks

1. **Verify backend can connect:**
   ```bash
   cd "2_Backend_Football_Probability_Engine"
   python -c "from app.db.session import SessionLocal; db = SessionLocal(); print('Connected!')"
   ```

2. **Test API endpoints:**
   - Start backend server
   - Test health endpoint
   - Test data endpoints

3. **Verify frontend can connect:**
   - Start frontend server
   - Test API calls
   - Verify data displays correctly

---

## Summary

After completing all steps:
- ✅ Database rebuilt with all tables
- ✅ All migrations applied
- ✅ Data re-ingested
- ✅ Model trained
- ✅ Statistics calculated
- ✅ Backend and frontend aligned

