# How to Populate Database - Simple Instructions

## Your Database Details
- **Database Name**: `football_probability_engine`
- **Password**: `11403775411`
- **Username**: `postgres` (default)
- **Host**: `localhost` (default)

## Easiest Way (Recommended)

### Option 1: Use the Simple Batch File

1. Navigate to the population script folder:
   ```batch
   cd "15_Football_Data_\02_Db populating_Script"
   ```

2. Run the simple batch file:
   ```batch
   SIMPLE_POPULATE.bat
   ```

### Option 2: Use the Root Batch File

1. Navigate to the data folder:
   ```batch
   cd "15_Football_Data_"
   ```

2. Run:
   ```batch
   POPULATE_DB.bat
   ```

## Manual Method

### Step 1: Navigate to Correct Directory

```batch
cd "15_Football_Data_\02_Db populating_Script"
```

**Important:** You must be in the `02_Db populating_Script` folder, NOT `01_extruction_Script`!

### Step 2: Run the Population Script

```batch
python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
```

## Complete Command (Copy & Paste)

```batch
cd "15_Football_Data_\02_Db populating_Script" && python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
```

## If You Get Errors

### "No such file or directory"
- Make sure you're in the `02_Db populating_Script` folder
- Check that `populate_database.py` exists in that folder

### "Module not found: psycopg2"
- Install: `pip install psycopg2-binary pandas`

### "Could not connect to database"
- Make sure PostgreSQL is running
- Check password is correct: `11403775411`
- Verify database exists: `football_probability_engine`

### "relation does not exist"
- Apply schema first: Run `3_Database_Football_Probability_Engine.sql`
- Then apply enhancements: `schema_enhancements.sql`

## Quick Test

Test your connection first:
```batch
set PGPASSWORD=11403775411
psql -U postgres -d football_probability_engine -c "SELECT COUNT(*) FROM leagues;"
```

If this works, your connection is good!

