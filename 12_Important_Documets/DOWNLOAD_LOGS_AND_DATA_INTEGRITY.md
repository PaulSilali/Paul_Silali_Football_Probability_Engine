# Download Logs and Data Integrity Guide

## Overview

This document describes the comprehensive logging system implemented for data ingestion and verification tools for ensuring data integrity across CSV files and database records.

## Logging System

### Log Locations

All download and ingestion logs are now saved in dedicated `01_logs` folders:

1. **Draw Structural Data Logs:**
   - `data/1_data_ingestion/Draw_structural/01_logs/`
   - `data/2_Cleaned_data/Draw_structural/01_logs/`

2. **Historical Match Odds Data Logs:**
   - `data/1_data_ingestion/Historical Match_Odds_Data/01_logs/`
   - `data/2_Cleaned_data/Historical Match_Odds_Data/01_logs/`

### Log File Naming Convention

- **Draw Structural:** `{Data_Type}_{Timestamp}_INGESTION_LOG.txt`
  - Example: `Team_Form_20250109_143022_INGESTION_LOG.txt`

- **Historical Odds:** `Historical_Odds_{Session_Folder}_{Timestamp}_LOG.txt`
  - Example: `Historical_Odds_2026-01-09_Seasons_10_Leagues_43_20250109_143022_LOG.txt`

### Log Contents

Each log file contains:

1. **Status Summary**
   - Success/Failure status
   - Total processed, successful, failed, skipped counts

2. **Details Section**
   - Individual record processing details (first 50 entries)

3. **Errors Section**
   - All errors encountered (first 20 entries)

4. **Warnings Section**
   - All warnings encountered (first 20 entries)

5. **CSV Files Saved**
   - List of CSV files created during ingestion

6. **Database Updates**
   - Records inserted count
   - Records updated count

7. **Performance Metrics**
   - Execution time
   - Average time per record

## CSV File Paths

### Draw Structural Data

All draw structural CSV files are saved to **both** locations:

1. **Ingestion:** `data/1_data_ingestion/Draw_structural/{Data_Type}/`
2. **Cleaned:** `data/2_Cleaned_data/Draw_structural/{Data_Type}/`

**Data Types:**
- `Team_Form/`
- `Rest_Days/`
- `Odds_Movement/`
- `h2h_stats/`
- `Elo_Rating/`
- `XG Data/` (Note: capital X, space - fixed from "xG_Data")
- `Weather/`
- `League_structure/`
- `Referee/`
- `League_Priors/`

### Historical Match Odds Data

CSV files are saved to:

1. **Ingestion:** `data/1_data_ingestion/Historical Match_Odds_Data/{Session_Folder}/{League_Code}/`
2. **Cleaned:** `data/2_Cleaned_data/Historical Match_Odds_Data/{League_Code}/`

**File Structure:**
```
Historical Match_Odds_Data/
├── 01_logs/                          # Log files
├── {Session_Folder}/                 # e.g., 2026-01-09_Seasons_10_Leagues_43
│   ├── {League_Code}/                # e.g., E0, SP1
│   │   └── {League_Code}_{Season}.csv
│   └── DOWNLOAD_LOG.txt              # Legacy log (also in 01_logs)
```

## Database Alignment

### Key Tables Verified

1. **Team Form:**
   - `team_form` (for fixtures)
   - `team_form_historical` (for historical matches)

2. **Rest Days:**
   - `team_rest_days` (for fixtures)
   - `team_rest_days_historical` (for historical matches)

3. **XG Data:**
   - `match_xg` (for fixtures)
   - `match_xg_historical` (for historical matches)

4. **Weather:**
   - `match_weather` (for fixtures)
   - `match_weather_historical` (for historical matches)

5. **Odds Movement:**
   - `odds_movement` (for fixtures)
   - `odds_movement_historical` (for historical matches)

### Database Schema Verification

Run the verification script to check database alignment:

```bash
python 2_Backend_Football_Probability_Engine/scripts/verify_data_integrity.py
```

This script verifies:
- CSV file paths are correct
- Database schema matches expected tables
- CSV records align with database records
- Log folders exist and contain logs

## Implementation Details

### Logging Utility

**File:** `app/services/ingestion/draw_structural_logging.py`

**Functions:**
- `write_draw_structural_log()` - Writes logs for draw structural data ingestion
- `write_historical_odds_log()` - Writes logs for historical odds downloads

### Updated Functions

1. **Team Form Ingestion:**
   - `batch_ingest_team_form_from_matches()` - Now includes comprehensive logging
   - Tracks CSV files saved, DB records inserted/updated, errors, warnings

2. **Historical Match Odds:**
   - `_write_download_log()` - Updated to save logs in `01_logs` folders
   - Tracks CSV files saved per league/season

3. **XG Data:**
   - Fixed folder name from `xG_Data` to `XG Data` (capital X, space)
   - Updated in `hybrid_import.py` and `ingest_xg_data.py`

## Usage

### Checking Logs

1. **Draw Structural Data:**
   ```bash
   # View latest Team Form log
   cat "data/1_data_ingestion/Draw_structural/01_logs/Team_Form_*.txt" | tail -1
   ```

2. **Historical Odds:**
   ```bash
   # View latest Historical Odds log
   cat "data/1_data_ingestion/Historical Match_Odds_Data/01_logs/Historical_Odds_*.txt" | tail -1
   ```

### Running Verification

```bash
cd "2_Backend_Football_Probability_Engine"
python scripts/verify_data_integrity.py
```

## Troubleshooting

### Issue: Logs Not Appearing

1. Check that `01_logs` folders exist:
   ```bash
   ls -la "data/1_data_ingestion/Draw_structural/01_logs"
   ls -la "data/2_Cleaned_data/Draw_structural/01_logs"
   ```

2. Check file permissions - logs are written with UTF-8 encoding

3. Check backend logs for errors during log writing

### Issue: CSV Files Not Saving

1. Verify folder paths are correct (check `draw_structural_utils.py`)
2. Check disk space
3. Verify write permissions on data folders

### Issue: Database Not Updating

1. Check database connection
2. Verify table exists (run verification script)
3. Check for constraint violations in logs
4. Review error messages in ingestion logs

## Best Practices

1. **Always Check Logs After Ingestion:**
   - Review `01_logs` folders after each batch ingestion
   - Look for errors and warnings sections

2. **Verify Data Integrity:**
   - Run verification script regularly
   - Compare CSV record counts with database counts

3. **Monitor Log File Sizes:**
   - Logs are truncated to first 20-50 entries for readability
   - Full details are in database records

4. **Keep Logs Organized:**
   - Logs are timestamped for easy sorting
   - Old logs can be archived but should be kept for audit trail

## Future Enhancements

1. **Log Rotation:** Implement automatic log rotation for large files
2. **Log Aggregation:** Create summary dashboard of all ingestion logs
3. **Alerting:** Set up alerts for failed ingestions
4. **Performance Tracking:** Track ingestion performance over time

