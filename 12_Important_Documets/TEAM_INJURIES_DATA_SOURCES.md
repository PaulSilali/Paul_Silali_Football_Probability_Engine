# Team Injuries Data Sources Implementation Guide

## Overview

This document explains how to populate the `team_injuries` table using external data sources. The system supports multiple methods for adding injury data.

## Available Methods

### 1. **Manual Entry** (Current - Fully Working)
- Use the injury icon (🏥) next to team names in the Probability Output page
- Enter injury data directly through the UI
- Best for: Real-time updates, specific fixtures

### 2. **CSV Import** (Current - Fully Working)
- Upload CSV files with injury data
- Format: `league_code, season, match_date, home_team, away_team, home_key_players_missing, home_injury_severity, ...`
- Best for: Bulk historical data, external data exports

### 3. **API-Football Download** (✅ Fully Implemented)
- Automated download from API-Football with automatic fixture ID mapping
- Requires: API key from RapidAPI
- Best for: Near-real-time injury updates, production pipelines
- Features:
  - Automatic fixture matching by date, league, and team names
  - Fuzzy team name matching (70%+ similarity)
  - Rate limiting (6 seconds between requests for free tier)
  - Automatic injury parsing and database storage

### 4. **Transfermarkt Scraping** (Planned - Free Alternative)
- Web scraping from Transfermarkt
- Requires: Web scraping setup
- Best for: Free alternative, no API costs

## API-Football Setup

### Step 1: Get API Key

1. Visit: https://rapidapi.com/api-sports/api/api-football
2. Sign up for a free account
3. Subscribe to the "API-Football" API (free tier available)
4. Copy your API key from the dashboard

### Step 2: Configure API Key

Add to your `.env` file:

```env
API_FOOTBALL_KEY=your_api_key_here
```

### Step 3: Use the Download Feature

1. Go to **Draw Structural Ingestion** → **Team Injuries** tab
2. Select leagues or fixtures
3. Click **"Download Injuries from API-Football"**
4. The system will fetch injury data for selected fixtures

### API-Football Implementation Details

**✅ Fully Functional:** The system now automatically:

1. **Fixture ID Mapping:**
   - Queries API-Football fixtures endpoint to find matching fixtures
   - Matches by date (±1 day), league ID, and team names
   - Uses fuzzy matching (70%+ similarity) for team name variations
   - Handles timezone differences and date variations

2. **Injury Data Parsing:**
   - Fetches injuries using API-Football fixture ID
   - Parses player positions (attackers, midfielders, defenders, goalkeepers)
   - Calculates injury severity automatically
   - Extracts injury notes and reasons

3. **Rate Limiting:**
   - Automatically handles API rate limits (6 seconds between requests)
   - Respects free tier limits (~10 requests/minute)
   - Waits 60 seconds if rate limit exceeded

**Recommended Approach:**
- Use **CSV Import** for bulk historical data
- Use **Manual Entry** for specific fixtures or when API is unavailable
- Use **API-Football Download** for automated, near-real-time updates

## CSV Import Format

### Required Columns

```csv
league_code,season,match_date,home_team,away_team,
home_key_players_missing,home_injury_severity,home_attackers_missing,
home_midfielders_missing,home_defenders_missing,home_goalkeepers_missing,home_notes,
away_key_players_missing,away_injury_severity,away_attackers_missing,
away_midfielders_missing,away_defenders_missing,away_goalkeepers_missing,away_notes
```

### Example CSV

```csv
league_code,season,match_date,home_team,away_team,home_key_players_missing,home_injury_severity,home_attackers_missing,home_midfielders_missing,home_defenders_missing,home_goalkeepers_missing,home_notes,away_key_players_missing,away_injury_severity,away_attackers_missing,away_midfielders_missing,away_defenders_missing,away_goalkeepers_missing,away_notes
E0,2023-24,2024-01-15,Arsenal,Manchester City,2,0.4,1,1,0,0,"Saka, Partey injured",1,0.2,0,1,0,0,"De Bruyne out"
```

### Field Descriptions

- **league_code**: League code (e.g., E0, SP1, D1)
- **season**: Season identifier (e.g., 2023-24)
- **match_date**: Match date (YYYY-MM-DD format)
- **home_team / away_team**: Team names (must match database)
- **key_players_missing**: Number of key players missing
- **injury_severity**: Overall severity (0.0-1.0), auto-calculated if not provided
- **attackers_missing**: Number of attackers missing
- **midfielders_missing**: Number of midfielders missing
- **defenders_missing**: Number of defenders missing
- **goalkeepers_missing**: Number of goalkeepers missing
- **notes**: Free text notes about injuries

## Data Sources Comparison

| Source | Cost | Setup Complexity | Data Quality | Update Frequency |
|--------|------|------------------|--------------|------------------|
| **Manual Entry** | Free | None | High (user-controlled) | On-demand |
| **CSV Import** | Free | Low | Depends on source | Batch |
| **API-Football** | Freemium | Medium | High | Near-real-time |
| **Transfermarkt** | Free | High (scraping) | High | Daily (manual) |

## Recommended Workflow

### For Historical Data
1. Export injury data from external sources (Transfermarkt, PhysioRoom) to CSV
2. Format according to CSV import format
3. Import via **CSV Import** feature

### For Current Fixtures
1. Use **Manual Entry** for important fixtures
2. Or set up **API-Football** integration (requires fixture ID mapping)

### For Production Pipeline
1. Implement fixture ID mapping for API-Football
2. Set up automated downloads before each prediction
3. Fall back to manual entry for missing data

## Implementation Status

- ✅ **Manual Entry**: Fully implemented
- ✅ **CSV Import**: Fully implemented
- ⚠️ **API-Football Download**: Partially implemented (requires fixture ID mapping)
- ❌ **Transfermarkt Scraping**: Not yet implemented

## Next Steps

1. **Implement Fixture ID Mapping** for API-Football
   - Map our fixtures to API-Football fixture IDs
   - Use API-Football's fixtures endpoint to find matches
   - Then fetch injuries for those fixtures

2. **Add Transfermarkt Scraping** (Optional)
   - Web scraping implementation
   - Respect rate limits and terms of service
   - Parse HTML to extract injury data

3. **Add PhysioRoom Integration** (Optional)
   - Similar to Transfermarkt scraping
   - Medical context for injuries

## API Endpoints

### Download Injuries
```
POST /api/draw-ingestion/team-injuries/download
Body: {
  "fixture_ids": [1, 2, 3],  // Optional
  "league_codes": ["E0", "SP1"],  // Optional
  "use_all_leagues": false,
  "source": "api-football"  // or "transfermarkt"
}
```

### Import from CSV
```
POST /api/draw-ingestion/team-injuries/import-csv
Body: FormData with CSV file
```

### Export Existing Data
```
POST /api/draw-ingestion/team-injuries/batch
Body: {
  "league_codes": ["E0"],
  "use_all_leagues": false,
  "save_csv": true
}
```

## Notes

- Injury severity is auto-calculated if not provided (based on position counts)
- Duplicate entries (same team + fixture) are updated, not inserted
- CSV import validates team names and league codes
- Missing fixtures are skipped (logged as errors)

