# Draw Structural CSV Files Analysis

## Overview
This document analyzes the CSV files in `data/1_data_ingestion/Draw_structural/` folders and identifies improvements needed in the ingestion code.

## CSV File Structure Analysis

### 1. Elo_Rating (`{league_code}_{season}_elo_ratings.csv`)
**Format:**
```csv
league_code,season,team_id,team_name,date,elo_rating
G1,2223,539,Ionikos,2022-08-21,1528.7631157119636
```

**Current Status:**
- ✅ Has `ingest_elo_from_clubelo_csv()` but expects ClubElo format (ClubID, From, To, Elo)
- ❌ **MISSING**: Function to import from our CSV format (league_code, season, team_id, team_name, date, elo_rating)

**Improvement Needed:**
- Add `ingest_elo_from_csv()` function that reads our CSV format

---

### 2. h2h_stats (`{league_code}_{season}_h2h_stats.csv`)
**Format:**
```csv
home_team_id,home_team_name,away_team_id,away_team_name,season,matches_played,draw_count,draw_rate,avg_goals
533,Atromitos,535,OFI Crete,2223,3,0,0.0,3.3333333333333335
```

**Current Status:**
- ✅ Has `ingest_h2h_from_matches_table()` to calculate from matches
- ✅ Has `batch_ingest_h2h_stats()` to calculate in batch
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_h2h_from_csv()` function to read CSV and populate `h2h_draw_stats` table

---

### 3. League_Priors (`{league_code}_{season}_draw_priors.csv`)
**Format:**
```csv
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,is_draw
2022-08-19,Volos NFC,Asteras Tripolis,3,3,D,1
```

**Current Status:**
- ✅ Has `ingest_league_draw_priors_from_csv()` but expects football-data.co.uk format
- ❌ **MISSING**: Function to import from our CSV format (Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, is_draw)

**Note:** This format is actually compatible with football-data.co.uk format, so existing function should work, but needs verification.

**Improvement Needed:**
- Verify `ingest_league_draw_priors_from_csv()` works with this format
- If not, add wrapper function

---

### 4. League_structure (`{league_code}_{season}_league_structure.csv`)
**Format:**
```csv
league_code,season,total_teams,relegation_zones,promotion_zones,playoff_zones
G1,2223,14,2,2,0
```

**Current Status:**
- ✅ Has `_save_league_structure_csv_batch()` to save CSV
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_league_structure_from_csv()` function

---

### 5. Odds_Movement (`{league_code}_{season}_odds_movement.csv`)
**Format:**
```csv
league_code,season,match_date,home_team,away_team,draw_open,draw_close,draw_delta
G1,2223,2022-08-19,Volos NFC,Asteras Tripolis,3.15,3.15,0.0
```

**Current Status:**
- ✅ Has `ingest_odds_movement_from_football_data_org()` for API
- ✅ Has `track_odds_movement()` for tracking
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_odds_movement_from_csv()` function to read CSV and populate `odds_movement_historical` table

---

### 6. Referee (`{league_code}_{season}_referee_stats.csv`)
**Format:**
```csv
league_code,season,referee_id,referee_name,matches,avg_cards,avg_penalties,draw_rate
G1,2223,116023,League Average (G1 2223),240,0.0,0.0,0.3
```

**Current Status:**
- ✅ Has `_save_referee_csv_batch()` to save CSV
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_referee_stats_from_csv()` function

---

### 7. Rest_Days (`{league_code}_{season}_rest_days.csv`)
**Format:**
```csv
league_code,season,match_date,home_team,away_team,home_rest_days,away_rest_days,is_midweek
G1,2223,2022-08-19,Volos NFC,Asteras Tripolis,97,96,False
```

**Current Status:**
- ✅ Has `calculate_rest_days_for_fixture()` to calculate from matches
- ✅ Has `batch_calculate_rest_days()` to calculate in batch
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_rest_days_from_csv()` function to read CSV and populate `team_rest_days_historical` table

---

### 8. Weather (`{league_code}_{season}_weather.csv`)
**Format:**
```csv
league_code,season,match_date,home_team,away_team,temperature,rainfall,wind_speed,weather_draw_index
E0,2526,2025-08-15,Liverpool,Bournemouth,29.5,0.0,7.7,1.077
```

**Current Status:**
- ✅ Has `ingest_weather_from_open_meteo()` for API
- ✅ Has `batch_ingest_weather()` for batch API calls
- ❌ **MISSING**: Function to import from existing CSV files

**Improvement Needed:**
- Add `ingest_weather_from_csv()` function to read CSV and populate `match_weather_historical` table

---

### 9. XG Data (`{league_code}_{season}_xg_data.csv`)
**Format:**
```csv
match_id,xg_home,xg_away,xg_total,xg_draw_index
40994,2.9492207956044325,0.0,2.9492207956044325,0.9640623363516454
```

**Current Status:**
- ✅ Has `ingest_xg_for_fixture()` and `batch_ingest_xg_data()` functions
- ✅ **ADDED**: `ingest_xg_from_csv()` function to import from CSV files

**Note:** CSV files found in `app/data/1_data_ingestion/Draw_structural/xG_Data/` (167 files)

---

## Summary of Improvements Needed

### ✅ COMPLETED (CSV Import Functions Added)
1. ✅ **Elo_Rating**: Added `ingest_elo_from_csv()` for our CSV format
2. ✅ **h2h_stats**: Added `ingest_h2h_from_csv()` function
3. ✅ **League_structure**: Added `ingest_league_structure_from_csv()` function
4. ✅ **Odds_Movement**: Added `ingest_odds_movement_from_csv()` function
5. ✅ **Referee**: Added `ingest_referee_stats_from_csv()` function
6. ✅ **Rest_Days**: Added `ingest_rest_days_from_csv()` function
7. ✅ **Weather**: Added `ingest_weather_from_csv()` function

### Medium Priority (Verification)
1. ⚠️ **League_Priors**: Verify existing function works with CSV format (format appears compatible)

### ✅ COMPLETED (XG Data)
1. ✅ **XG Data**: Added `ingest_xg_from_csv()` function (167 CSV files found)

---

## Recommended Implementation

### Option 1: Add CSV Import Functions to Each Service
- Add `ingest_*_from_csv()` function to each ingestion service
- Functions should:
  - Read CSV files from `Draw_structural/` folders
  - Match teams/leagues by name or ID
  - Use `ON CONFLICT DO UPDATE` for idempotency
  - Handle missing teams/leagues gracefully

### Option 2: Create Unified CSV Import Script
- Create a single script that can import all CSV types
- Use a configuration file to map CSV columns to database columns
- More maintainable but less flexible

**Recommendation:** Option 1 (Add functions to each service) for better modularity and maintainability.

---

## File Counts
- Elo_Rating: 148 CSV files
- h2h_stats: 167 CSV files
- League_Priors: 167 CSV files
- League_structure: 430 CSV files
- Odds_Movement: 147 CSV files
- Referee: 167 CSV files
- Rest_Days: 167 CSV files
- Weather: 2 CSV files
- XG Data: 167 CSV files

**Total:** ~1,562 CSV files to potentially import

---

## Next Steps
1. ✅ **COMPLETED**: Create CSV import functions for each service
2. ⏳ **TODO**: Add batch import endpoints to API (optional - can use existing endpoints with loop)
3. ⏳ **TODO**: Test with sample CSV files
4. ⏳ **TODO**: Document usage in API documentation

## Implementation Details

### CSV Import Functions Added

All CSV import functions follow this pattern:
- Read CSV file using pandas
- Validate required columns
- Match teams/leagues by name or ID
- Find matches by date, teams, and league
- Insert into appropriate historical tables
- Use `ON CONFLICT DO UPDATE` for idempotency
- Handle missing teams/leagues/matches gracefully

### Function Locations

1. **Elo_Rating**: `ingest_elo_ratings.py::ingest_elo_from_csv()`
2. **h2h_stats**: `ingest_h2h_stats.py::ingest_h2h_from_csv()`
3. **League_structure**: `ingest_league_structure.py::ingest_league_structure_from_csv()`
4. **Odds_Movement**: `ingest_odds_movement.py::ingest_odds_movement_from_csv()`
5. **Referee**: `ingest_referee_stats.py::ingest_referee_stats_from_csv()`
6. **Rest_Days**: `ingest_rest_days.py::ingest_rest_days_from_csv()`
7. **Weather**: `ingest_weather.py::ingest_weather_from_csv()`
8. **XG Data**: `ingest_xg_data.py::ingest_xg_from_csv()`

### Usage Example

```python
from app.services.ingestion.ingest_elo_ratings import ingest_elo_from_csv
from app.db.session import SessionLocal

db = SessionLocal()
result = ingest_elo_from_csv(
    db, 
    "data/1_data_ingestion/Draw_structural/Elo_Rating/G1_2223_elo_ratings.csv"
)
print(f"Inserted: {result['inserted']}, Updated: {result['updated']}, Errors: {result['errors']}")
```

### Notes

- All functions use team name resolution via `resolve_team_safe()` for robust matching
- Functions handle missing data gracefully (skip with warning, don't fail entire import)
- All functions are idempotent (safe to run multiple times)
- Functions commit after processing all rows (transactional)

