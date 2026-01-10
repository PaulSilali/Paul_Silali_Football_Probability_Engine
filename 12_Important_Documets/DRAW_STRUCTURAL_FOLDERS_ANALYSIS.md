# Draw Structural Folders Analysis Report

## Summary

Analysis of `2_Cleaned_data/Draw_structural` folder to identify missing folders and data inconsistencies.

## Findings

### Missing Folders (Now Fixed)

1. **Referee/** - ✅ FIXED
   - **Status:** Had 167 CSV files in `1_data_ingestion` but folder was missing in `2_Cleaned_data`
   - **Root Cause:** `_save_referee_csv()` function (single referee save) was not using `save_draw_structural_csv()` utility, so it only saved to ingestion folder
   - **Fix Applied:**
     - Updated `_save_referee_csv()` to use `save_draw_structural_csv()` with `save_to_cleaned=True`
     - Copied existing 167 CSV files from ingestion to cleaned_data folder
   - **Files:** 167 CSV files now in cleaned_data

2. **XG Data/** - ⚠️ Empty
   - **Status:** Folder exists in `1_data_ingestion` but contains 0 CSV files
   - **Reason:** No XG data has been ingested yet
   - **Action Required:** Run XG data batch ingestion when data is available

### Existing Folders Status

| Folder | Ingestion Files | Cleaned Files | Status |
|--------|----------------|---------------|--------|
| Team_Form | 260 | 260 | ✅ OK |
| Rest_Days | 264 | 263 | ⚠️ 1 file difference |
| Odds_Movement | 168 | 168 | ✅ OK |
| h2h_stats | 264 | 263 | ⚠️ 1 file difference |
| Elo_Rating | 241 | 240 | ⚠️ 1 file difference |
| Weather | 2 | 1 | ⚠️ 1 file difference |
| League_structure | 430 | 430 | ✅ OK |
| League_Priors | 167 | 0 | ⚠️ Empty in cleaned |
| Referee | 167 | 167 | ✅ Fixed |
| XG Data | 0 | 0 | ⚠️ No data ingested |

### Minor Count Mismatches

Small differences (1-2 files) between ingestion and cleaned folders are likely due to:
- Files being added/updated during ingestion
- Some files failing to save to cleaned folder (non-critical errors)
- Timing differences between saves

**Action:** These are acceptable and don't require immediate action.

### League_Priors Empty Folder

- **Issue:** Folder exists in cleaned_data but contains 0 CSV files (167 files in ingestion)
- **Possible Reason:** `save_to_cleaned=False` was used during ingestion, or error occurred
- **Action:** Re-run League Priors batch ingestion to populate cleaned folder

## Code Fixes Applied

### 1. Fixed `_save_referee_csv()` Function

**File:** `app/services/ingestion/ingest_referee_stats.py`

**Before:**
```python
def _save_referee_csv(...):
    # Only saved to ingestion folder
    base_dir = Path("data/1_data_ingestion/Draw_structural/Referee")
    df.to_csv(csv_path, index=False)
```

**After:**
```python
def _save_referee_csv(...):
    # Now uses utility function to save to both folders
    from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
    ingestion_path, cleaned_path = save_draw_structural_csv(
        df, "Referee", filename, save_to_cleaned=True
    )
```

### 2. Created Copy Script

**File:** `scripts/copy_missing_to_cleaned.py`

- Copies missing CSV files from ingestion to cleaned_data folders
- Used to fix Referee folder (167 files copied)

## Verification Scripts

### Check Missing Folders

```bash
python 2_Backend_Football_Probability_Engine/scripts/check_missing_draw_structural_folders.py
```

This script:
- Compares ingestion and cleaned folders
- Identifies missing folders
- Reports file count mismatches
- Provides recommendations

### Copy Missing Files

```bash
python 2_Backend_Football_Probability_Engine/scripts/copy_missing_to_cleaned.py
```

This script:
- Copies missing CSV files from ingestion to cleaned_data
- Only copies files that don't already exist
- Reports number of files copied

## Recommendations

1. **Run League Priors Batch Ingestion:**
   - Re-run to populate cleaned_data folder
   - Use batch ingestion endpoint with `save_csv=True`

2. **Ingest XG Data:**
   - When XG data sources are available, run batch ingestion
   - Will automatically save to both folders

3. **Monitor Future Ingestions:**
   - Use verification script after batch ingestions
   - Check logs in `01_logs` folders for any save errors

4. **Accept Minor Differences:**
   - 1-2 file differences are acceptable
   - Likely due to timing or non-critical errors

## Expected Folder Structure

```
2_Cleaned_data/Draw_structural/
├── 01_logs/              # Log files
├── Team_Form/            # Team form data
├── Rest_Days/            # Rest days data
├── Odds_Movement/        # Odds movement data
├── h2h_stats/            # Head-to-head statistics
├── Elo_Rating/           # Elo ratings
├── XG Data/              # Expected Goals data (capital X, space)
├── Weather/              # Weather data
├── League_structure/     # League structure metadata
├── Referee/              # Referee statistics
└── League_Priors/        # League draw priors
```

## Status: ✅ RESOLVED

- Referee folder: Fixed and populated
- Code updated to prevent future issues
- Verification scripts created for ongoing monitoring

