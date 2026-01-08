# Database Rebuild Instructions

## Problem: `psql` not in PATH

If you're getting `'psql' is not recognized`, you have two options:

---

## Option 1: Use pgAdmin (Recommended)

1. **Open pgAdmin**
2. **Connect to PostgreSQL server**
3. **Right-click on "Databases" → "Query Tool"**
4. **Run the SQL commands below**

---

## Option 2: Find psql.exe

1. **Find PostgreSQL installation:**
   - Usually in: `C:\Program Files\PostgreSQL\<version>\bin\`
   - Or: `C:\Program Files (x86)\PostgreSQL\<version>\bin\`

2. **Use full path:**
   ```batch
   "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d postgres
   ```

---

## SQL Commands to Run

### **Step 1: Drop Existing Database**

Run this in pgAdmin Query Tool (connected to `postgres` database):

```sql
-- Disconnect all users
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'football_probability_engine'
  AND pid <> pg_backend_pid();

-- Drop database
DROP DATABASE IF EXISTS football_probability_engine;
```

---

### **Step 2: Create New Database**

```sql
CREATE DATABASE football_probability_engine
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;
```

---

### **Step 3: Connect to New Database**

In pgAdmin:
1. **Right-click on `football_probability_engine` database**
2. **Select "Query Tool"**
3. **Run the main schema file**

---

### **Step 4: Run Main Schema**

**Option A: Using pgAdmin File Menu**
1. **File → Open**
2. **Select:** `3_Database_Football_Probability_Engine.sql`
3. **Click "Execute" (F5)**

**Option B: Copy-Paste**
- Open `3_Database_Football_Probability_Engine.sql` in a text editor
- Copy all contents
- Paste into pgAdmin Query Tool
- Execute (F5)

---

### **Step 5: Run All Migrations**

Run each migration file in order:

1. **File → Open → `migrations/4_ALL_LEAGUES_FOOTBALL_DATA.sql`** → Execute
2. **File → Open → `migrations/2025_01_draw_structural_extensions.sql`** → Execute
3. **File → Open → `migrations/2025_01_add_historical_tables.sql`** → Execute
4. **File → Open → `migrations/2025_01_add_league_structure.sql`** → Execute
5. **File → Open → `migrations/2025_01_add_odds_movement_historical.sql`** → Execute
6. **File → Open → `migrations/2025_01_add_xg_data.sql`** → Execute
7. **File → Open → `migrations/add_h2h_stats.sql`** → Execute
8. **File → Open → `migrations/add_saved_jackpot_templates.sql`** → Execute
9. **File → Open → `migrations/add_saved_probability_results.sql`** → Execute
10. **File → Open → `migrations/add_entropy_metrics.sql`** → Execute
11. **File → Open → `migrations/add_unique_partial_index_models.sql`** → Execute
12. **File → Open → `migrations/add_draw_model_support.sql`** → Execute
13. **File → Open → `migrations/fix_matchresult_enum.sql`** → Execute

---

### **Step 6: Verify**

Run this query to verify all tables were created:

```sql
-- Count tables
SELECT COUNT(*) as total_tables
FROM pg_tables
WHERE schemaname = 'public';

-- List all tables
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify critical tables
SELECT tablename 
FROM pg_tables 
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
```

**Expected:** Should return 21 rows (all critical tables)

---

## Quick Reference: All SQL Commands

Here's a single SQL script you can copy-paste (after creating the database):

```sql
-- ============================================================================
-- COMPLETE REBUILD SCRIPT
-- ============================================================================
-- Run this AFTER creating the database and connecting to it

-- Step 1: Run main schema (copy contents of 3_Database_Football_Probability_Engine.sql here)
-- OR use File → Open in pgAdmin

-- Step 2: Verify main schema created tables
SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';
-- Should return ~20+ tables

-- Step 3: Run migrations (use File → Open for each migration file)
-- OR copy-paste each migration file's contents here

-- Step 4: Final verification
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
-- Should show all 32 tables
```

---

## Troubleshooting

### **Error: "database does not exist"**
- Make sure you created the database first
- Check you're connected to the correct database

### **Error: "relation already exists"**
- Table already exists from previous run
- Drop the table or continue (migrations use `IF NOT EXISTS`)

### **Error: "permission denied"**
- Make sure you're connected as `postgres` user
- Or a user with superuser privileges

---

## Next Steps After Rebuild

1. **Re-ingest data:**
   ```bash
   cd "15_Football_Data_/01_extruction_Script"
   python extract_football_data.py
   
   cd "../02_Db populating_Script"
   python populate_database.py <csv_path>
   ```

2. **Update statistics:**
   ```bash
   python update_league_statistics.py
   python update_teams_ratings.py
   ```

