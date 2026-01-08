# How to Populate Database - Step by Step Guide

## Prerequisites

1. ✅ PostgreSQL database created: `football_probability_engine`
2. ✅ Schema applied (from `3_Database_Football_Probability_Engine.sql`)
3. ✅ Schema enhancements applied (from `schema_enhancements.sql`)
4. ✅ Extracted CSV file: `matches_extracted.csv`
5. ✅ Python with `psycopg2-binary` installed

## Step-by-Step Instructions

### Step 1: Install Required Python Package

```bash
pip install psycopg2-binary pandas
```

### Step 2: Apply Schema Enhancements (If Not Done)

```bash
cd "15_Football_Data_\02_Db populating_Script"
psql -U postgres -d football_probability_engine -f schema_enhancements.sql
```

**Or if you need to specify password:**
```bash
set PGPASSWORD=11403775411
psql -U postgres -d football_probability_engine -f schema_enhancements.sql
```

### Step 3: Run Database Population

#### Option A: Using Batch Script (Windows - Easiest)

```batch
cd "15_Football_Data_\02_Db populating_Script"
run_population.bat postgresql://postgres:11403775411@localhost/football_probability_engine
```

#### Option B: Using Python Directly

```bash
cd "15_Football_Data_\02_Db populating_Script"
python populate_database.py --csv ..\01_extruction_Script\output\matches_extracted.csv --db-url postgresql://postgres:11403775411@localhost/football_probability_engine
```

#### Option C: If PostgreSQL is on Different Host

```bash
python populate_database.py --csv ..\01_extruction_Script\output\matches_extracted.csv --db-url postgresql://postgres:11403775411@your-host:5432/football_probability_engine
```

## Database Connection URL Format

```
postgresql://[username]:[password]@[host]:[port]/[database]
```

**Your specific URL:**
```
postgresql://postgres:11403775411@localhost/football_probability_engine
```

**Components:**
- `postgres` = username (default PostgreSQL user)
- `11403775411` = password
- `localhost` = host (change if PostgreSQL is on different machine)
- `5432` = port (default, can be omitted)
- `football_probability_engine` = database name

## What Happens During Population

1. **Staging**: Loads CSV to `staging.matches_raw` table
2. **Leagues**: Populates/updates `leagues` table
3. **Teams**: Populates/updates `teams` table (with normalization)
4. **Matches**: Populates/updates `matches` table
5. **Statistics**: Calculates and populates:
   - `league_draw_priors`
   - `h2h_draw_stats`
   - `team_h2h_stats`
   - `league_stats`
6. **Data Source**: Registers data source in `data_sources` table

## Expected Output

```
Populating leagues table...
Populated 60 leagues
Populating teams table...
Populated teams: 5000 inserted, 200 updated
Populating matches table...
Populated 103983 matches
Populating derived statistics...
Derived statistics populated
Registering data source...
Data source registered

============================================================
POPULATION COMPLETE
============================================================
Total matches: 103983
Total leagues: 60
Total seasons: 21
Total draws: 25000
Draw rate: 24.05%
```

## Troubleshooting

### Error: "psycopg2.OperationalError: could not connect"

**Solution:** Check PostgreSQL is running and connection details:
```bash
# Test connection
psql -U postgres -d football_probability_engine -c "SELECT 1;"
```

### Error: "relation 'staging.matches_raw' does not exist"

**Solution:** The script creates this automatically, but if it fails:
```sql
CREATE SCHEMA IF NOT EXISTS staging;
```

### Error: "permission denied for schema staging"

**Solution:** Grant permissions:
```sql
GRANT ALL ON SCHEMA staging TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO postgres;
```

### Error: "column 'ht_home_goals' does not exist"

**Solution:** Apply schema enhancements:
```bash
psql -U postgres -d football_probability_engine -f schema_enhancements.sql
```

### Error: "duplicate key value violates unique constraint"

**This is normal!** The script uses `ON CONFLICT DO UPDATE`, so duplicates are handled automatically.

## Verification After Population

### Check Total Matches
```sql
SELECT COUNT(*) FROM matches WHERE source = 'football-txt-extraction';
```

### Check Leagues
```sql
SELECT code, name, country, COUNT(*) as match_count
FROM matches m
JOIN leagues l ON l.id = m.league_id
GROUP BY code, name, country
ORDER BY match_count DESC;
```

### Check Seasons
```sql
SELECT season, COUNT(*) as matches
FROM matches
GROUP BY season
ORDER BY season DESC;
```

### Check Draw Statistics
```sql
SELECT 
    l.code,
    l.name,
    COUNT(*) as total_matches,
    SUM(CASE WHEN m.result = 'D' THEN 1 ELSE 0 END) as draws,
    ROUND(100.0 * SUM(CASE WHEN m.result = 'D' THEN 1 ELSE 0 END) / COUNT(*), 2) as draw_rate
FROM matches m
JOIN leagues l ON l.id = m.league_id
GROUP BY l.code, l.name
ORDER BY draw_rate DESC;
```

## Quick Start (All Steps)

```batch
REM 1. Navigate to population script directory
cd "15_Football_Data_\02_Db populating_Script"

REM 2. Apply schema enhancements (if not done)
set PGPASSWORD=11403775411
psql -U postgres -d football_probability_engine -f schema_enhancements.sql

REM 3. Run population
python populate_database.py --csv ..\01_extruction_Script\output\matches_extracted.csv --db-url postgresql://postgres:11403775411@localhost/football_probability_engine
```

## Notes

- **Idempotent**: Safe to run multiple times
- **Updates existing**: Uses `ON CONFLICT DO UPDATE`
- **No data loss**: Existing records are preserved
- **Progress tracking**: Check `population_report.json` after completion

