# Implementation Summary: Football Data Extraction & Database Population

## Overview

This implementation provides a complete ETL pipeline for ingesting Football.TXT format data into the Football Probability Engine database with robust deduplication and schema enhancements.

## Files Created

### Extraction Script (`01_extruction_Script/`)
- **`extract_football_data.py`** - Parses Football.TXT files and extracts match data
  - Supports all `*-master` folder structures
  - Handles multiple date formats
  - Extracts half-time scores
  - Deduplication at extraction level

### Database Population (`02_Db populating_Script/`)
- **`populate_database.py`** - Populates PostgreSQL database
  - FK-safe load order
  - Idempotent operations
  - Team name normalization
  - Derived statistics calculation

- **`schema_enhancements.sql`** - Database schema additions
  - Half-time scores columns
  - Match metadata (time, venue, matchday)
  - Computed columns (total_goals, goal_difference, is_draw)
  - Statistics views

- **`league_mapping.json`** - League code configuration
- **`README.md`** - Complete documentation

## Deduplication Strategy

### Three-Level Protection

1. **Extraction Level** (Python)
   - Tracks seen matches: `(date, home_team, away_team, league_code)`
   - Prevents duplicate extraction from overlapping files
   - Location: `extract_football_data.py` → `seen_matches` set

2. **Database Level** (PostgreSQL)
   - Unique constraints with `ON CONFLICT` handling:
     - `matches`: `(home_team_id, away_team_id, match_date)`
     - `teams`: `(canonical_name, league_id)`
     - `leagues`: `(code)`
   - Idempotent `INSERT ... ON CONFLICT DO UPDATE`
   - Location: `populate_database.py` → all `populate_*` methods

3. **Team Name Normalization** (SQL + Python)
   - Consistent canonical name creation
   - Handles variations (Man Utd, Manchester United)
   - SQL function: `normalize_team_name()`
   - Location: `populate_database.py` → `TeamNameNormalizer` class

## Schema Enhancements

### New Columns Added to `matches` Table

| Column | Type | Purpose |
|--------|------|---------|
| `ht_home_goals` | INTEGER | Half-time goals for home team |
| `ht_away_goals` | INTEGER | Half-time goals for away team |
| `match_time` | TIME | Match kickoff time |
| `venue` | VARCHAR(200) | Stadium/venue name |
| `source_file` | TEXT | Original source file path |
| `ingestion_batch_id` | VARCHAR(50) | Batch identifier |
| `matchday` | INTEGER | Matchday/round number |
| `round_name` | VARCHAR(50) | Round name (e.g., "Matchday 1") |
| `total_goals` | INTEGER | Computed: home_goals + away_goals |
| `goal_difference` | INTEGER | Computed: home_goals - away_goals |
| `is_draw` | BOOLEAN | Computed: home_goals = away_goals |

### New Columns Added to `teams` Table

| Column | Type | Purpose |
|--------|------|---------|
| `alternative_names` | TEXT[] | Array of alternative team names for matching |

### New Views

- **`v_season_statistics`** - Season-level statistics for all leagues
- **`v_team_season_stats`** - Team statistics per season

## Data Flow

```
Football.TXT Files
    ↓
[Extraction Script]
    ↓
matches_extracted.csv
    ↓
[Staging Table]
    ↓
[Database Population]
    ↓
PostgreSQL Tables:
  - leagues
  - teams
  - matches
  - league_draw_priors
  - h2h_draw_stats
  - team_h2h_stats
  - league_stats
  - data_sources
```

## Load Order (FK-Safe)

1. **Staging**: Load CSV to `staging.matches_raw`
2. **Reference Tables**: `leagues` → `teams`
3. **Fact Tables**: `matches`
4. **Derived Statistics**: 
   - `league_draw_priors`
   - `h2h_draw_stats`
   - `team_h2h_stats`
   - `league_stats`
5. **Metadata**: `data_sources`

## Team Name Matching

### Normalization Process

1. **Remove suffixes**: FC, AFC, United → Utd, City, Town
2. **Normalize whitespace**: Multiple spaces → single space
3. **Remove special characters**: Keep only alphanumeric and spaces
4. **Lowercase**: For case-insensitive matching
5. **Variation mapping**: Handle known variations (Man Utd, Manchester United)

### Example

```
Input: "Manchester United FC"
  → Remove " FC" → "Manchester United"
  → Replace " United" → "Manchester Utd"
  → Lowercase → "manchester utd"
  → Canonical: "manchester utd"
```

## Probability Computation Enhancements

The schema enhancements support:

1. **Draw Probability Modeling**:
   - Half-time scores for draw prediction
   - Matchday for late-season draw rate adjustments
   - Goal difference for match quality metrics

2. **H2H Statistics**:
   - Enhanced `h2h_draw_stats` table
   - Team-specific draw rates
   - Historical meeting counts

3. **League Priors**:
   - `league_draw_priors` per season
   - Sample size tracking
   - Historical draw rates

4. **Match Quality Metrics**:
   - `total_goals` for offensive/defensive match classification
   - `goal_difference` for match competitiveness
   - `is_draw` for quick filtering

## Usage Example

```bash
# Step 1: Extract data
cd 15_Football_Data_/01_extruction_Script
python extract_football_data.py \
    --data-dir .. \
    --output-dir output

# Step 2: Apply schema enhancements
psql -U postgres -d football_probability_engine \
    -f ../02_Db\ populating_Script/schema_enhancements.sql

# Step 3: Populate database
cd ../02_Db\ populating_Script
python populate_database.py \
    --csv ../01_extruction_Script/output/matches_extracted.csv \
    --db-url postgresql://user:pass@localhost/football_probability_engine
```

## Verification Queries

```sql
-- Check total matches loaded
SELECT COUNT(*) FROM matches WHERE source = 'football-txt-extraction';

-- Check matches by league
SELECT l.code, l.name, COUNT(*) as match_count
FROM matches m
JOIN leagues l ON l.id = m.league_id
WHERE m.source = 'football-txt-extraction'
GROUP BY l.code, l.name
ORDER BY match_count DESC;

-- Check draw rates
SELECT * FROM v_season_statistics
ORDER BY league_code, season DESC
LIMIT 20;

-- Check team matching
SELECT t.name, t.canonical_name, COUNT(*) as match_count
FROM teams t
JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
WHERE m.source = 'football-txt-extraction'
GROUP BY t.id, t.name, t.canonical_name
ORDER BY match_count DESC
LIMIT 20;
```

## Key Features

✅ **Deduplication**: Multi-level protection against duplicates  
✅ **Idempotent**: Safe to re-run without creating duplicates  
✅ **FK-Safe**: Proper load order respects foreign key constraints  
✅ **Team Matching**: Robust normalization handles name variations  
✅ **Schema Enhancements**: Additional columns for probability modeling  
✅ **Performance**: Bulk loading with PostgreSQL COPY  
✅ **Error Handling**: Transaction safety with rollback  
✅ **Documentation**: Complete README and inline comments  

## Next Steps

1. **Run extraction** on all `*-master` folders
2. **Apply schema enhancements** to database
3. **Populate database** with extracted data
4. **Verify data quality** using verification queries
5. **Train models** using the populated historical data
6. **Monitor** data source freshness via `data_sources` table

## Support

- Extraction issues: Check `01_extruction_Script/extract_football_data.py`
- Population issues: Check `02_Db populating_Script/populate_database.py`
- Schema questions: Check `3_Database_Football_Probability_Engine.sql`
- Data format: Check `DEEP_SCAN_REPORT.md`

