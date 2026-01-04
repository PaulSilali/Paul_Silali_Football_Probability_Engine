# What Updates the Matches Table

The `matches` table is updated by several ingestion services. Here's a comprehensive overview:

## Primary Update Sources

### 1. **DataIngestionService.ingest_csv()** 
**Location:** `app/services/data_ingestion.py` (lines 96-450)

**What it does:**
- Main service for ingesting match data from CSV files
- Reads CSV content (from football-data.co.uk format)
- Parses match data including scores, odds, and probabilities
- **Inserts new matches** or **updates existing matches** based on unique constraint (home_team_id, away_team_id, match_date)

**Key Methods:**
- `ingest_csv()` - Main ingestion method
- Checks for existing matches using: `home_team_id`, `away_team_id`, `match_date`
- Updates: `home_goals`, `away_goals`, `result`, odds, probabilities
- Inserts: New match records with all fields

**Called by:**
- `ingest_from_football_data()` - Downloads CSV from football-data.co.uk
- `OpenFootballService.ingest_league_matches()` - Converts OpenFootball TXT to CSV, then calls `ingest_csv()`

---

### 2. **FootballDataOrgService.ingest_league_matches()**
**Location:** `app/services/ingestion/ingest_football_data_org.py` (lines 195-367)

**What it does:**
- Ingests match data from Football-Data.org API (v4)
- Fetches matches via API calls
- Resolves team names to database teams
- **Inserts new matches** or **updates existing matches**

**Key Features:**
- Uses API competition IDs mapped to league codes
- Handles rate limiting (429 errors)
- Updates existing matches if `home_goals` and `away_goals` are available
- Inserts new matches with all available data

**Called by:**
- `DataIngestionService.ingest_from_football_data_org()` - Main entry point

---

### 3. **OpenFootballService.ingest_league_matches()**
**Location:** `app/services/ingestion/ingest_openfootball.py` (lines 410-490)

**What it does:**
- Downloads Football.TXT files from OpenFootball repositories (GitHub or local)
- Parses Football.TXT format into match records
- Converts to CSV format
- **Calls `DataIngestionService.ingest_csv()`** to insert/update matches

**Key Features:**
- Supports local file reading (if `OPENFOOTBALL_LOCAL_PATH` is configured)
- Falls back to GitHub downloads if local files not found
- Parses various date formats and match line formats
- Handles optional time and half-time scores

**Called by:**
- `DataIngestionService.ingest_from_football_data_org()` - As fallback when Football-Data.org returns 403

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Pipeline                   │
└─────────────────────────────────────────────────────────────┘

1. DataIngestionService.ingest_all_seasons()
   │
   ├─→ For each league:
   │   │
   │   ├─→ Try: ingest_from_football_data() [CSV download]
   │   │   └─→ DataIngestionService.ingest_csv()
   │   │       └─→ INSERT/UPDATE matches table
   │   │
   │   └─→ Try: ingest_from_football_data_org() [API]
   │       │
   │       ├─→ Success: FootballDataOrgService.ingest_league_matches()
   │       │   └─→ INSERT/UPDATE matches table
   │       │
   │       └─→ 403 Error: OpenFootballService.ingest_league_matches()
   │           └─→ Parse TXT → CSV → DataIngestionService.ingest_csv()
   │               └─→ INSERT/UPDATE matches table
```

---

## Match Update Logic

### Unique Constraint
Matches are identified by: `(home_team_id, away_team_id, match_date)`

### Update vs Insert
```python
# Check for existing match
existing_match = db.query(Match).filter(
    Match.home_team_id == home_team.id,
    Match.away_team_id == away_team.id,
    Match.match_date == match_date
).first()

if existing_match:
    # UPDATE existing match
    existing_match.home_goals = home_goals
    existing_match.away_goals = away_goals
    existing_match.result = result
    # ... update other fields
    stats["updated"] += 1
else:
    # INSERT new match
    new_match = Match(...)
    db.add(new_match)
    stats["inserted"] += 1
```

---

## Why "No Matches Found" Error Occurs

The error you're seeing (`400: No matches found`) comes from:

**Location:** `app/services/ingestion/ingest_league_draw_priors.py` (line 166)

**Function:** `ingest_from_matches_table()`

**Cause:** 
- The draw priors ingestion service queries the `matches` table
- If no matches exist for the specified `league_code` and `season`, it returns "No matches found"
- This means **matches haven't been ingested yet** for that league/season

**Solution:**
1. Run the main data ingestion first to populate matches:
   ```python
   # Via API or script
   POST /api/data/ingest-all-seasons
   ```

2. Or ingest specific league/season:
   ```python
   POST /api/data/ingest-league
   ```

---

## Summary

**The matches table is updated by:**
1. ✅ `DataIngestionService.ingest_csv()` - From CSV files (football-data.co.uk)
2. ✅ `FootballDataOrgService.ingest_league_matches()` - From Football-Data.org API
3. ✅ `OpenFootballService.ingest_league_matches()` - From OpenFootball TXT files (via CSV conversion)

**All three services:**
- Check for existing matches using unique constraint
- Update existing matches if found
- Insert new matches if not found
- Commit changes to database

**To fix "No matches found" error:**
- Run data ingestion first to populate the matches table
- Then run draw priors ingestion

