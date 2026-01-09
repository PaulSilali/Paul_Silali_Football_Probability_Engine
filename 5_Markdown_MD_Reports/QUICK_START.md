# Quick Start - Run Schema on Existing Database

## ✅ Your Database is Created!

Since you've already created `football_probability_engine`, follow these steps:

---

## Step 1: Open pgAdmin

1. **Open pgAdmin**
2. **Connect to your PostgreSQL server**
3. **Expand "Databases"**
4. **Right-click `football_probability_engine` → Query Tool**

---

## Step 2: Run the Schema

### **Option A: Using File Menu (Easiest)**

1. **In Query Tool: File → Open**
2. **Navigate to:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
3. **Click "Open"**
4. **Press F5 (or click Execute button)**

### **Option B: Copy-Paste**

1. **Open** `3_Database_Football_Probability_Engine.sql` in a text editor
2. **Copy all contents** (Ctrl+A, Ctrl+C)
3. **Paste into pgAdmin Query Tool** (Ctrl+V)
4. **Press F5** to execute

---

## Step 3: Wait for Completion

The script will:
- ✅ Create all tables
- ✅ Add all columns
- ✅ Create all indexes
- ✅ Insert all leagues
- ✅ Verify everything

**Time:** Usually takes 10-30 seconds

---

## Step 4: Verify Success

Run this query to verify:

```sql
SELECT 
    COUNT(*) as total_tables,
    COUNT(*) FILTER (WHERE tablename IN (
        'leagues', 'teams', 'matches', 'jackpots', 'jackpot_fixtures',
        'predictions', 'models', 'training_runs', 'league_draw_priors',
        'h2h_draw_stats', 'team_elo', 'match_weather', 'match_weather_historical',
        'referee_stats', 'team_rest_days', 'team_rest_days_historical',
        'odds_movement', 'odds_movement_historical', 'league_structure',
        'match_xg', 'match_xg_historical'
    )) as critical_tables
FROM pg_tables
WHERE schemaname = 'public';
```

**Expected Result:**
- `total_tables` >= 32
- `critical_tables` = 21

---

## ✅ Done!

Your database is now ready. Next steps:

1. **Re-ingest data** using `populate_database.py`
2. **Train model** using `update_teams_ratings.py`
3. **Update statistics** using `update_league_statistics.py`

---

## Troubleshooting

### **Error: "relation already exists"**
- ✅ **This is OK!** The script uses `IF NOT EXISTS`, so it's safe
- Just continue - the script will skip existing objects

### **Error: "constraint already exists"**
- ✅ **This is OK!** The script handles this
- The constraint will be recreated if needed

### **Error: "column already exists"**
- ✅ **This is OK!** The script uses `ADD COLUMN IF NOT EXISTS`
- Existing columns won't be modified

---

## What's Included

The schema file now includes:
- ✅ All 32 tables
- ✅ All columns (including ht_home_goals, alternative_names, etc.)
- ✅ All indexes (including GIN indexes)
- ✅ All constraints
- ✅ All migrations integrated
- ✅ All leagues from football-data.co.uk

**You don't need to run migrations separately!**

