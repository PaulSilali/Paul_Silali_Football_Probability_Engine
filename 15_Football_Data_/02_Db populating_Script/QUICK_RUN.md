# Quick Run Instructions

## To Populate Database

### Option 1: Double-Click Batch File (Easiest)
1. Navigate to: `15_Football_Data_\02_Db populating_Script`
2. Double-click: `RUN_POPULATION.bat`
3. Wait for completion (may take 5-10 minutes)

### Option 2: Command Line
```batch
cd "15_Football_Data_\02_Db populating_Script"
python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
```

## What Happens

1. **Staging** (30 seconds) - Loads CSV to staging table
2. **Leagues** (1 second) - Populates 59 leagues
3. **Teams** (2-3 seconds) - Populates ~4,300 teams
4. **Matches** (5-10 minutes) - Populates 103,983 matches
5. **Statistics** (1-2 minutes) - Calculates draw rates, H2H stats
6. **Complete** - Generates report

## Expected Output

```
Connected to database
Creating staging schema...
Staging schema and table created successfully
Loading CSV file...
Reading CSV with pandas...
Inserting 103983 rows into staging table...
Loaded 103983 rows into staging table
Populating leagues table...
Populated 59 leagues
Populating teams table...
Populated teams: 4296 inserted, 0 updated
Populating matches table...
Populated 85000 matches
Populating derived statistics...
Derived statistics populated
Registering data source...
Data source registered

============================================================
POPULATION COMPLETE
============================================================
Total matches: 103983
Total leagues: 59
Total seasons: 21
Total draws: 25000
Draw rate: 24.05%
```

## If It Takes Too Long

The script processes matches in batches. If it seems stuck:
- Check PostgreSQL is running
- Check database connection
- Look for error messages in the output

## After Completion

Check the results:
```sql
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM leagues;
```

