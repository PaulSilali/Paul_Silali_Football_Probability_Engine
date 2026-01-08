# Database Population Scripts

This directory contains scripts for populating the Football Probability Engine database from extracted Football.TXT data.

## Files

- `populate_database.py` - Main database population script
- `schema_enhancements.sql` - SQL migration for additional columns
- `league_mapping.json` - League code mapping configuration
- `README.md` - This file

## Prerequisites

1. **PostgreSQL Database** - Version 15+ with the schema from `3_Database_Football_Probability_Engine.sql`
2. **Python 3.8+** with packages:
   ```bash
   pip install psycopg2-binary pandas
   ```
3. **Extracted CSV** - Run the extraction script first to generate `matches_extracted.csv`

## Quick Start

### Step 1: Extract Data

```bash
cd 15_Football_Data_/01_extruction_Script
python extract_football_data.py --data-dir .. --output-dir output
```

This generates `output/matches_extracted.csv`

### Step 2: Apply Schema Enhancements

```bash
psql -U postgres -d football_probability_engine -f schema_enhancements.sql
```

### Step 3: Populate Database

```bash
cd 15_Football_Data_/02_Db populating_Script
python populate_database.py \
    --csv ../01_extruction_Script/output/matches_extracted.csv \
    --db-url postgresql://user:password@localhost/football_probability_engine
```

## Deduplication Strategy

The scripts implement **multi-level deduplication**:

### 1. Extraction Level
- Tracks seen matches by `(date, home_team, away_team, league_code)`
- Prevents duplicate extraction from multiple files

### 2. Database Level
- Uses `ON CONFLICT` clauses on unique constraints:
  - **matches**: `(home_team_id, away_team_id, match_date)`
  - **teams**: `(canonical_name, league_id)`
  - **leagues**: `(code)`
  - **league_draw_priors**: `(league_id, season)`
  - **h2h_draw_stats**: `(team_home_id, team_away_id)`

### 3. Team Name Normalization
- Normalizes team names for matching:
  - Removes common suffixes (FC, AFC, United → Utd)
  - Handles variations (Man Utd, Manchester United)
  - Case-insensitive matching

## Load Order (FK-Safe)

The population follows this order to respect foreign key constraints:

1. **Phase 0**: Create staging schema and load CSV
2. **Phase 1**: Populate reference tables
   - `leagues` (no dependencies)
   - `teams` (depends on `leagues`)
3. **Phase 2**: Populate fact tables
   - `matches` (depends on `leagues`, `teams`)
4. **Phase 3**: Populate derived statistics
   - `league_draw_priors` (depends on `matches`, `leagues`)
   - `h2h_draw_stats` (depends on `matches`, `teams`)
   - `team_h2h_stats` (depends on `matches`, `teams`)
   - `league_stats` (depends on `matches`, `leagues`)
5. **Phase 4**: Register data source
   - `data_sources` (tracks ingestion)

## Schema Enhancements

The `schema_enhancements.sql` adds:

- **Half-time scores**: `ht_home_goals`, `ht_away_goals`
- **Match metadata**: `match_time`, `venue`, `matchday`, `round_name`
- **Source tracking**: `source_file`, `ingestion_batch_id`
- **Computed columns**: `total_goals`, `goal_difference`, `is_draw`
- **Views**: `v_season_statistics`, `v_team_season_stats`

## Team Name Matching

Team names are normalized using:

1. **Canonical name creation**:
   - Remove common suffixes (FC, AFC, etc.)
   - Normalize whitespace
   - Convert to lowercase
   - Remove special characters

2. **Variation handling**:
   - "Manchester United" → "manchester utd"
   - "Man Utd" → "manchester utd"
   - "Tottenham Hotspur" → "tottenham hotspur"
   - "Spurs" → "tottenham hotspur"

3. **SQL function**: `normalize_team_name()` for consistent matching

## Error Handling

- **Unmatched teams**: Logged as warnings, matches skipped
- **Invalid data**: Filtered out (NULL dates, goals, results)
- **Transaction safety**: All operations in transactions with rollback on error

## Performance

- **Bulk loading**: Uses PostgreSQL `COPY` for fast CSV import
- **Staging table**: Loads all data to staging first, then processes
- **Batch operations**: Processes in batches for large datasets
- **Indexes**: Leverages existing indexes for fast lookups

## Output

After successful population:

1. **Database tables populated**:
   - `leagues`, `teams`, `matches`
   - `league_draw_priors`, `h2h_draw_stats`, `team_h2h_stats`, `league_stats`
   - `data_sources`

2. **Report file**: `population_report.json` with:
   - Total matches, leagues, seasons
   - Matches by league
   - Draw statistics

## Troubleshooting

### Team Matching Issues

If teams aren't matching:

1. Check `unmatched_teams.log` (if generated)
2. Manually add to `teams.alternative_names` array
3. Update `league_mapping.json` with variations

### Duplicate Matches

If seeing duplicates:

1. Check unique constraint: `(home_team_id, away_team_id, match_date)`
2. Verify team IDs are consistent
3. Check date format consistency

### Performance Issues

For large datasets:

1. Increase `work_mem` in PostgreSQL
2. Disable indexes during load, rebuild after
3. Use `COPY` instead of `INSERT` (already implemented)

## Next Steps

After population:

1. **Verify data quality**:
   ```sql
   SELECT league_code, season, COUNT(*) 
   FROM matches m
   JOIN leagues l ON l.id = m.league_id
   GROUP BY league_code, season
   ORDER BY league_code, season;
   ```

2. **Check draw rates**:
   ```sql
   SELECT * FROM v_season_statistics
   ORDER BY league_code, season DESC;
   ```

3. **Train models** using the populated data

## Support

For issues or questions, check:
- Database schema: `3_Database_Football_Probability_Engine.sql`
- Extraction script: `01_extruction_Script/extract_football_data.py`
- Deep scan report: `DEEP_SCAN_REPORT.md`

