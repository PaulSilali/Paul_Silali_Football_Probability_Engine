# International Games Data Ingestion Guide

## Overview

This guide explains how to ingest historical match data for international games (country vs country matches) into the system.

---

## Prerequisites

✅ **INT League Created**
- Run `create_international_league.sql` or `create_international_league.py`
- Verify INT league exists in database

---

## Data Sources for International Matches

### 1. Football-Data.org API
- **URL:** https://www.football-data.org/
- **Coverage:** Major international tournaments (World Cup, Euros, etc.)
- **Format:** JSON API
- **Note:** May require paid subscription for full access

### 2. OpenFootball (GitHub)
- **Repository:** https://github.com/openfootball
- **Path:** `world/` folder
- **Format:** Text files (`.txt`)
- **Coverage:** Various international competitions

### 3. Manual CSV Import
- Create CSV files in football-data.co.uk format
- Use `league_code = "INT"` for all international matches

---

## CSV Format for International Matches

### Required Columns

```csv
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR
2024-01-10,Algeria,Nigeria,2,1,H,1,0,H
2024-01-15,Brazil,Argentina,1,1,D,0,0,D
```

### Column Descriptions

| Column | Description | Example |
|--------|-------------|---------|
| `Date` | Match date | 2024-01-10 |
| `HomeTeam` | Home team name | Algeria |
| `AwayTeam` | Away team name | Nigeria |
| `FTHG` | Full Time Home Goals | 2 |
| `FTAG` | Full Time Away Goals | 1 |
| `FTR` | Full Time Result (H/D/A) | H |
| `HTHG` | Half Time Home Goals | 1 |
| `HTAG` | Half Time Away Goals | 0 |
| `HTR` | Half Time Result (H/D/A) | D |

---

## Ingestion Methods

### Method 1: Using Data Ingestion Service

```python
from app.services.data_ingestion import DataIngestionService
from app.db.session import SessionLocal

db = SessionLocal()
ingestion_service = DataIngestionService(db, enable_cleaning=True)

# Ingest CSV file
stats = ingestion_service.ingest_csv(
    csv_content=csv_content,  # CSV file content as string
    league_code="INT",  # Use INT for international matches
    season="ALL",  # Or specific season like "2425"
    source_name="manual",
    save_csv=True
)

print(f"Processed: {stats['processed']} matches")
print(f"Inserted: {stats['inserted']} matches")
```

### Method 2: Using Batch Ingestion API

**Endpoint:** `POST /api/draw-ingestion/league-priors/batch`

**Request Body:**
```json
{
  "league_codes": ["INT"],
  "use_all_leagues": false,
  "season": "ALL",
  "use_all_seasons": true,
  "max_years": 10,
  "save_csv": true
}
```

### Method 3: Direct Database Insert

```python
from app.db.models import Match, League, Team
from app.services.team_resolver import create_team_if_not_exists
from datetime import datetime

db = SessionLocal()

# Get INT league
int_league = db.query(League).filter(League.code == 'INT').first()

# Create teams if they don't exist
home_team = create_team_if_not_exists(db, "Algeria", int_league.id)
away_team = create_team_if_not_exists(db, "Nigeria", int_league.id)

# Create match
match = Match(
    league_id=int_league.id,
    season="2425",  # Or appropriate season
    match_date=datetime(2024, 1, 10),
    home_team_id=home_team.id,
    away_team_id=away_team.id,
    home_goals=2,
    away_goals=1,
    result="H"
)
db.add(match)
db.commit()
```

---

## Draw Structural Data for International Matches

### 1. League Priors

**Special Handling:**
- INT league doesn't have traditional "league priors"
- System uses default draw rate (0.25) or calculates from all INT matches
- Can manually set if needed:

```python
from app.db.models import LeagueDrawPrior, League

int_league = db.query(League).filter(League.code == 'INT').first()
prior = LeagueDrawPrior(
    league_id=int_league.id,
    season="ALL",
    draw_rate=0.25,  # Typical international draw rate
    sample_size=1000  # Or actual count
)
db.add(prior)
db.commit()
```

### 2. Team Form

**Works Normally:**
- Calculates from matches in `matches` table
- Filters by `league_id = INT`
- No special handling needed

**Ingestion:**
```python
from app.services.ingestion.ingest_team_form import batch_ingest_team_form_from_matches

results = batch_ingest_team_form_from_matches(
    db=db,
    league_codes=["INT"],
    use_all_seasons=True,
    max_years=10,
    save_csv=True
)
```

### 3. H2H Stats

**Works Normally:**
- Calculates from matches between two teams
- No special handling needed

**Ingestion:**
```python
from app.services.ingestion.ingest_h2h_stats import ingest_h2h_from_matches_table

results = ingest_h2h_from_matches_table(
    db=db,
    home_team_id=home_team.id,
    away_team_id=away_team.id,
    season="ALL",
    save_csv=True
)
```

### 4. Elo Ratings

**Works Normally:**
- Calculates Elo ratings for teams
- No special handling needed

**Ingestion:**
```python
from app.services.ingestion.ingest_elo_ratings import batch_calculate_elo_from_matches

results = batch_calculate_elo_from_matches(
    db=db,
    league_codes=["INT"],
    use_all_seasons=True,
    max_years=10,
    save_csv=True
)
```

### 5. Weather Data

**Works Normally:**
- Uses country coordinates for weather lookup
- No special handling needed

**Ingestion:**
```python
from app.services.ingestion.ingest_weather import batch_ingest_weather_from_matches

results = batch_ingest_weather_from_matches(
    db=db,
    league_codes=["INT"],
    use_all_seasons=True,
    max_years=10,
    save_csv=True
)
```

### 6. Rest Days

**Works Normally:**
- Calculates rest days between matches
- No special handling needed

**Ingestion:**
- Automatically calculated during probability calculation
- Or manually:

```python
from app.services.ingestion.ingest_rest_days import ingest_rest_days_for_fixture

results = ingest_rest_days_for_fixture(
    db=db,
    fixture_id=fixture.id
)
```

---

## Example: Complete International Match Ingestion

```python
from app.services.data_ingestion import DataIngestionService
from app.services.ingestion.ingest_team_form import batch_ingest_team_form_from_matches
from app.services.ingestion.ingest_elo_ratings import batch_calculate_elo_from_matches
from app.services.ingestion.ingest_h2h_stats import ingest_h2h_from_matches_table
from app.db.session import SessionLocal

db = SessionLocal()

# Step 1: Ingest match data
ingestion_service = DataIngestionService(db, enable_cleaning=True)
csv_content = """
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR
2024-01-10,Algeria,Nigeria,2,1,H
2024-01-15,Brazil,Argentina,1,1,D
"""

stats = ingestion_service.ingest_csv(
    csv_content=csv_content,
    league_code="INT",
    season="2425",
    save_csv=True
)

# Step 2: Calculate team form
form_results = batch_ingest_team_form_from_matches(
    db=db,
    league_codes=["INT"],
    season="2425",
    save_csv=True
)

# Step 3: Calculate Elo ratings
elo_results = batch_calculate_elo_from_matches(
    db=db,
    league_codes=["INT"],
    season="2425",
    save_csv=True
)

# Step 4: Calculate H2H stats (for specific pairs)
# This is done automatically during probability calculation
# Or manually for specific pairs:

from app.services.team_resolver import resolve_team_safe
from app.db.models import League

int_league = db.query(League).filter(League.code == 'INT').first()
algeria = resolve_team_safe(db, "Algeria", int_league.id)
nigeria = resolve_team_safe(db, "Nigeria", int_league.id)

if algeria and nigeria:
    h2h_results = ingest_h2h_from_matches_table(
        db=db,
        home_team_id=algeria.id,
        away_team_id=nigeria.id,
        season="ALL",
        save_csv=True
    )

db.close()
```

---

## Data File Locations

After ingestion, data is saved to:

### Raw Data (Ingestion)
- `data/1_data_ingestion/Draw_structural/Team_Form/INT_*_team_form.csv`
- `data/1_data_ingestion/Draw_structural/Elo_Rating/INT_*_elo_ratings.csv`
- `data/1_data_ingestion/Draw_structural/h2h_stats/INT_*_h2h_stats.csv`

### Cleaned Data
- `data/2_Cleaned_data/Draw_structural/Team_Form/INT_*_team_form.csv`
- `data/2_Cleaned_data/Draw_structural/Elo_Rating/INT_*_elo_ratings.csv`
- `data/2_Cleaned_data/Draw_structural/h2h_stats/INT_*_h2h_stats.csv`

### Historical Match Data
- `data/1_data_ingestion/Historical Match_Odds_Data/INT_*_*.csv`
- `data/2_Cleaned_data/Historical Match_Odds_Data/INT_*_*.csv`

---

## Verification

### Check INT League Exists
```sql
SELECT * FROM leagues WHERE code = 'INT';
```

### Check International Teams
```sql
SELECT t.name, l.code, l.name as league_name
FROM teams t
JOIN leagues l ON t.league_id = l.id
WHERE l.code = 'INT'
ORDER BY t.name;
```

### Check International Matches
```sql
SELECT m.match_date, ht.name as home_team, at.name as away_team, 
       m.home_goals, m.away_goals, m.result
FROM matches m
JOIN leagues l ON m.league_id = l.id
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
WHERE l.code = 'INT'
ORDER BY m.match_date DESC
LIMIT 10;
```

### Check Draw Structural Data
```sql
-- Team Form
SELECT COUNT(*) FROM team_form_historical tfh
JOIN matches m ON tfh.match_id = m.id
JOIN leagues l ON m.league_id = l.id
WHERE l.code = 'INT';

-- Elo Ratings
SELECT COUNT(*) FROM team_elo te
JOIN teams t ON te.team_id = t.id
JOIN leagues l ON t.league_id = l.id
WHERE l.code = 'INT';

-- H2H Stats
SELECT COUNT(*) FROM h2h_draw_stats h2h
JOIN teams ht ON h2h.team_home_id = ht.id
JOIN teams at ON h2h.team_away_id = at.id
JOIN leagues l1 ON ht.league_id = l1.id
JOIN leagues l2 ON at.league_id = l2.id
WHERE l1.code = 'INT' OR l2.code = 'INT';
```

---

## Troubleshooting

### Issue: Teams Not Created
**Solution:** Ensure INT league exists before creating teams

### Issue: League Priors Not Found
**Solution:** System uses default (0.25) for INT league. This is expected behavior.

### Issue: Draw Structural Data Empty
**Solution:** Run batch ingestion functions after match data is ingested

### Issue: CSV Files Not Saving
**Solution:** Check folder permissions and ensure `save_csv=True` is set

---

## Summary

✅ **Match Data:** Use `DataIngestionService.ingest_csv()` with `league_code="INT"`  
✅ **Team Form:** Use `batch_ingest_team_form_from_matches()` with `league_codes=["INT"]`  
✅ **Elo Ratings:** Use `batch_calculate_elo_from_matches()` with `league_codes=["INT"]`  
✅ **H2H Stats:** Calculated automatically or use `ingest_h2h_from_matches_table()`  
✅ **Weather:** Use `batch_ingest_weather_from_matches()` with `league_codes=["INT"]`  
✅ **Rest Days:** Calculated automatically during probability calculation  

All draw structural data ingestion works normally for INT league, except league priors which use a default value.

