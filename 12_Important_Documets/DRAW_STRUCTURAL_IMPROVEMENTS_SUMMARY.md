# Draw Structural CSV Files - Improvements Summary

## ✅ All Improvements Completed

### Overview
Deep scan of all CSV files in `data/1_data_ingestion/Draw_structural/` folders revealed that ingestion services could **write** CSV files but **could not read** them back. All missing CSV import functions have now been added.

---

## 📊 CSV Files Inventory

| Folder | File Count | Status |
|--------|-----------|--------|
| Elo_Rating | 148 files | ✅ Import function added |
| h2h_stats | 167 files | ✅ Import function added |
| League_Priors | 167 files | ✅ Compatible with existing function |
| League_structure | 430 files | ✅ Import function added |
| Odds_Movement | 147 files | ✅ Import function added |
| Referee | 167 files | ✅ Import function added |
| Rest_Days | 167 files | ✅ Import function added |
| Weather | 2 files | ✅ Import function added |
| XG Data | 167 files | ✅ Import function added |

**Total:** ~1,562 CSV files

---

## 🔧 Functions Added

### 1. Elo Ratings
**File:** `ingest_elo_ratings.py`  
**Function:** `ingest_elo_from_csv(csv_path, league_code=None)`

**CSV Format:**
```csv
league_code,season,team_id,team_name,date,elo_rating
G1,2223,539,Ionikos,2022-08-21,1528.76
```

**Database Table:** `team_elo`

---

### 2. H2H Statistics
**File:** `ingest_h2h_stats.py`  
**Function:** `ingest_h2h_from_csv(csv_path)`

**CSV Format:**
```csv
home_team_id,home_team_name,away_team_id,away_team_name,season,matches_played,draw_count,draw_rate,avg_goals
533,Atromitos,535,OFI Crete,2223,3,0,0.0,3.33
```

**Database Table:** `h2h_draw_stats`

---

### 3. League Structure
**File:** `ingest_league_structure.py`  
**Function:** `ingest_league_structure_from_csv(csv_path)`

**CSV Format:**
```csv
league_code,season,total_teams,relegation_zones,promotion_zones,playoff_zones
G1,2223,14,2,2,0
```

**Database Table:** `league_structure`

---

### 4. Odds Movement
**File:** `ingest_odds_movement.py`  
**Function:** `ingest_odds_movement_from_csv(csv_path)`

**CSV Format:**
```csv
league_code,season,match_date,home_team,away_team,draw_open,draw_close,draw_delta
G1,2223,2022-08-19,Volos NFC,Asteras Tripolis,3.15,3.15,0.0
```

**Database Table:** `odds_movement_historical`

**Note:** Requires matching match by date, teams, and league.

---

### 5. Referee Statistics
**File:** `ingest_referee_stats.py`  
**Function:** `ingest_referee_stats_from_csv(csv_path)`

**CSV Format:**
```csv
league_code,season,referee_id,referee_name,matches,avg_cards,avg_penalties,draw_rate
G1,2223,116023,League Average (G1 2223),240,0.0,0.0,0.3
```

**Database Table:** `referee_stats`

---

### 6. Rest Days
**File:** `ingest_rest_days.py`  
**Function:** `ingest_rest_days_from_csv(csv_path)`

**CSV Format:**
```csv
league_code,season,match_date,home_team,away_team,home_rest_days,away_rest_days,is_midweek
G1,2223,2022-08-19,Volos NFC,Asteras Tripolis,97,96,False
```

**Database Table:** `team_rest_days_historical`

**Note:** Creates two records per match (one for home team, one for away team).

---

### 7. Weather
**File:** `ingest_weather.py`  
**Function:** `ingest_weather_from_csv(csv_path)`

**CSV Format:**
```csv
league_code,season,match_date,home_team,away_team,temperature,rainfall,wind_speed,weather_draw_index
E0,2526,2025-08-15,Liverpool,Bournemouth,29.5,0.0,7.7,1.077
```

**Database Table:** `match_weather_historical`

---

### 8. XG Data
**File:** `ingest_xg_data.py`  
**Function:** `ingest_xg_from_csv(csv_path)`

**CSV Format:**
```csv
match_id,xg_home,xg_away,xg_total,xg_draw_index
40994,2.9492207956044325,0.0,2.9492207956044325,0.9640623363516454
```

**Database Table:** `match_xg_historical`

**Note:** Uses `match_id` directly (no team name resolution needed).

---

### 9. League Draw Priors
**File:** `ingest_league_draw_priors.py`  
**Function:** `ingest_league_draw_priors_from_csv()` (already exists)

**CSV Format:**
```csv
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,is_draw
2022-08-19,Volos NFC,Asteras Tripolis,3,3,D,1
```

**Status:** ✅ Existing function is compatible with this format (football-data.co.uk format)

**Database Table:** `league_draw_priors`

---

## 🎯 Key Features

### All Import Functions:
- ✅ **Idempotent**: Safe to run multiple times (uses `ON CONFLICT DO UPDATE`)
- ✅ **Robust Team Matching**: Uses `resolve_team_safe()` for fuzzy team name matching
- ✅ **Error Handling**: Skips invalid rows with warnings, doesn't fail entire import
- ✅ **Transaction Safety**: Commits after processing all rows
- ✅ **Logging**: Comprehensive logging for debugging

### Common Patterns:
1. **Team Name Resolution**: Functions that need team names use `resolve_team_safe()` for robust matching
2. **Match Lookup**: Functions that need matches find them by `(league_id, season, match_date, home_team_id, away_team_id)`
3. **Historical Tables**: Most functions insert into `*_historical` tables for match data
4. **Validation**: All functions validate required columns before processing

---

## 📝 Usage Examples

### Import Single CSV File

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

### Batch Import All CSV Files in a Folder

```python
from pathlib import Path
from app.services.ingestion.ingest_elo_ratings import ingest_elo_from_csv
from app.db.session import SessionLocal

db = SessionLocal()
folder = Path("data/1_data_ingestion/Draw_structural/Elo_Rating")

total_inserted = 0
total_updated = 0
total_errors = 0

for csv_file in folder.glob("*.csv"):
    result = ingest_elo_from_csv(db, str(csv_file))
    if result.get("success"):
        total_inserted += result["inserted"]
        total_updated += result["updated"]
        total_errors += result["errors"]
    else:
        print(f"Failed to import {csv_file}: {result.get('error')}")

print(f"Total: {total_inserted} inserted, {total_updated} updated, {total_errors} errors")
```

---

## ⚠️ Important Notes

### 1. Prerequisites
- ✅ Database schema must be up-to-date (all tables exist)
- ✅ `matches` table must be populated (for functions that need to find matches)
- ✅ `teams` table must be populated (for team name resolution)
- ✅ `leagues` table must be populated (for league code lookup)

### 2. Team Name Matching
- Functions use `resolve_team_safe()` which performs fuzzy matching
- If team names don't match exactly, the function will try to find the closest match
- Teams that can't be matched are skipped with a warning

### 3. Match Lookup
- Functions that need matches look them up by `(league_id, season, match_date, home_team_id, away_team_id)`
- If a match is not found, the row is skipped with a warning
- This ensures data integrity (no orphaned records)

### 4. Error Handling
- Invalid rows are skipped with warnings (logged)
- Entire import doesn't fail if some rows are invalid
- Transaction is rolled back only on critical errors (file read failure, etc.)

---

## 🚀 Next Steps (Optional)

1. **API Endpoints**: Add batch import endpoints to `app/api/draw_ingestion.py`
2. **CLI Script**: Create a command-line script to import all CSV files
3. **Validation Script**: Create a script to validate CSV files before import
4. **Documentation**: Add usage examples to API documentation

---

## ✅ Status: All Improvements Complete

All CSV import functions have been added and are ready to use. The code is production-ready and follows best practices for error handling, logging, and data integrity.

