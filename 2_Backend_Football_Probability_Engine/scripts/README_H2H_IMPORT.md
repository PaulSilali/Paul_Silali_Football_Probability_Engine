# H2H Stats CSV Import Script

## Overview

This script imports H2H (Head-to-Head) statistics from CSV files into the `h2h_draw_stats` database table.

## Prerequisites

1. Database must be running and accessible
2. CSV files must exist in one of these locations:
   - `data/2_Cleaned_data/Draw_structural/h2h_stats/` (preferred)
   - `data/1_data_ingestion/Draw_structural/h2h_stats/` (fallback)
3. Teams must already exist in the database (team IDs in CSV must match database)

## CSV File Format

Expected CSV columns:
- `home_team_id` - Home team ID (must exist in `teams` table)
- `home_team_name` - Home team name (for reference, not used)
- `away_team_id` - Away team ID (must exist in `teams` table)
- `away_team_name` - Away team name (for reference, not used)
- `season` - Season identifier (for reference, not used)
- `matches_played` - Number of matches between these teams
- `draw_count` - Number of draws
- `draw_rate` - Draw rate (draw_count / matches_played)
- `avg_goals` - Average goals per match (optional)

Example:
```csv
home_team_id,home_team_name,away_team_id,away_team_name,season,matches_played,draw_count,draw_rate,avg_goals
9059,Guimaraes,9060,Benfica,1617,2,0,0.0,3.5
```

## Usage

### Option 1: Run Python Script Directly

```bash
cd "F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine"
python scripts/import_h2h_stats_from_csv.py
```

### Option 2: Run from Backend Root

```bash
cd "2_Backend_Football_Probability_Engine"
python scripts/import_h2h_stats_from_csv.py
```

## What the Script Does

1. **Scans for CSV files** in the cleaned data directory
2. **Validates each record**:
   - Checks team IDs exist in database
   - Validates matches_played >= draw_count
   - Validates draw_rate consistency
3. **Inserts or updates** records in `h2h_draw_stats` table:
   - If team pair doesn't exist: INSERT
   - If team pair exists: UPDATE with new values
4. **Provides detailed logging**:
   - Progress per file
   - Insert/update counts
   - Errors and skipped records
   - Final summary

## Output Example

```
2026-01-08 21:00:00 - INFO - Found 263 H2H stats CSV files
2026-01-08 21:00:00 - INFO - Starting import of 263 CSV files...
2026-01-08 21:00:01 - INFO - Processing CSV file: PL1_1617_h2h_stats.csv
2026-01-08 21:00:01 - INFO - ✓ PL1_1617_h2h_stats.csv: 150 inserted, 5 updated, 0 skipped, 0 errors
...
============================================================
IMPORT SUMMARY
============================================================
Total files processed: 263
Successful: 263
Failed: 0
Total records inserted: 35000
Total records updated: 500
Total records skipped: 0
Total errors: 0
============================================================
Total H2H records in database: 35500
```

## Verification

After running the script, verify the import:

```sql
-- Check total records
SELECT COUNT(*) FROM h2h_draw_stats;

-- View sample records
SELECT 
    h.team_home_id,
    ht.name as home_team_name,
    h.team_away_id,
    at.name as away_team_name,
    h.matches_played,
    h.draw_count,
    h.avg_goals
FROM h2h_draw_stats h
JOIN teams ht ON ht.id = h.team_home_id
JOIN teams at ON at.id = h.team_away_id
LIMIT 10;

-- Check records per league
SELECT 
    l.code as league_code,
    COUNT(*) as h2h_records
FROM h2h_draw_stats h
JOIN teams ht ON ht.id = h.team_home_id
JOIN leagues l ON l.id = ht.league_id
GROUP BY l.code
ORDER BY h2h_records DESC;
```

## Troubleshooting

### Error: "Team IDs not found"
- **Cause**: Team IDs in CSV don't match database
- **Solution**: Ensure teams are imported first using `populate_database.py` or team import scripts

### Error: "Invalid H2H stats"
- **Cause**: Data validation failed (e.g., draw_count > matches_played)
- **Solution**: Check CSV file for data quality issues

### Error: "No CSV files found"
- **Cause**: CSV files not in expected directory
- **Solution**: Check file paths or move CSV files to correct directory

### Error: Database connection failed
- **Cause**: Database not running or connection settings incorrect
- **Solution**: Check `.env` file and database connection settings

## Notes

- The script is **idempotent** - safe to run multiple times
- Existing records are **updated** (not duplicated)
- Records with invalid team IDs are **skipped** (not inserted)
- All changes are **committed** per file (transaction per file)

