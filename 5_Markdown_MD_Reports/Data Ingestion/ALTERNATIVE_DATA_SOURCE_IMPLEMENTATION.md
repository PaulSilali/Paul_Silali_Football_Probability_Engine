# Alternative Data Source Implementation - Football-Data.org API

## Summary

✅ **Option 3 Implemented:** Football-Data.org API has been integrated as an alternative data source for 17 leagues that are not available on football-data.co.uk.

## What Was Implemented

### 1. Backend Changes

#### Configuration (`app/config.py`)
- Added `FOOTBALL_DATA_ORG_KEY` setting for API key
- Added `FOOTBALL_DATA_ORG_BASE_URL` setting (defaults to v4 API)

#### New Service (`app/services/ingestion/ingest_football_data_org.py`)
- `FootballDataOrgService` class for API interactions
- Rate limiting (6 seconds between requests for free tier)
- Automatic team resolution
- Match creation/updating
- Error handling and retry logic

#### Updated Service (`app/services/data_ingestion.py`)
- Added `FOOTBALL_DATA_ORG_LEAGUES` set (17 leagues)
- `get_data_source_for_league()` method to route to correct source
- `ingest_from_football_data_org()` method for API ingestion
- Automatic source selection - no manual configuration needed

### 2. Frontend Changes

#### League Data (`src/data/allLeagues.ts`)
- Added `dataSource` field to `League` interface
- Marked 17 leagues with `dataSource: 'football-data.org'`
- Marked leagues as `available: true`

### 3. Automatic Routing

The system **automatically** routes to the correct data source:
- **26 leagues** → `football-data.co.uk` (CSV)
- **17 leagues** → `football-data.org` (API)

No manual selection needed - the system detects which source to use based on league code.

## Leagues Using Football-Data.org (17 total)

### Europe (9)
- SWE1 - Allsvenskan (Sweden)
- FIN1 - Veikkausliiga (Finland)
- RO1 - Liga 1 (Romania)
- RUS1 - Premier League (Russia)
- CZE1 - First League (Czech Republic)
- CRO1 - Prva HNL (Croatia)
- SRB1 - SuperLiga (Serbia)
- UKR1 - Premier League (Ukraine)
- IRL1 - Premier Division (Ireland)

### Americas (4)
- ARG1 - Primera Division (Argentina)
- BRA1 - Serie A (Brazil)
- MEX1 - Liga MX (Mexico)
- USA1 - Major League Soccer (USA)

### Asia & Oceania (4)
- CHN1 - Super League (China)
- JPN1 - J-League (Japan)
- KOR1 - K League 1 (South Korea)
- AUS1 - A-League (Australia)

## Setup Required

### 1. Get API Key
1. Visit: https://www.football-data.org/client/register
2. Register for free account
3. Copy API key

### 2. Add to `.env`
```env
FOOTBALL_DATA_ORG_KEY=your_api_key_here
```

### 3. Verify Competition IDs ⚠️ IMPORTANT

The competition IDs in `ingest_football_data_org.py` are **placeholders** and need to be verified:

1. Make request to: `https://api.football-data.org/v4/competitions`
2. Search for each league by name
3. Update `LEAGUE_CODE_TO_COMPETITION_ID` mapping

**Current placeholder IDs (need verification):**
```python
LEAGUE_CODE_TO_COMPETITION_ID = {
    'SWE1': 2003,  # ⚠️ Verify
    'FIN1': 2010,  # ⚠️ Verify
    'RO1': 2013,   # ⚠️ Verify
    # ... etc
}
```

## How It Works

### Automatic Source Selection

```python
# In DataIngestionService
def get_data_source_for_league(self, league_code: str) -> str:
    if league_code in self.FOOTBALL_DATA_ORG_LEAGUES:
        return 'football-data.org'
    return 'football-data.co.uk'
```

### Download Flow

1. User selects leagues and clicks "Download"
2. System checks league code
3. Routes to appropriate source:
   - `football-data.co.uk` → CSV download
   - `football-data.org` → API call
4. Data is ingested into same database structure
5. Results displayed in same UI

### Rate Limiting

Free tier: 10 requests/minute
- Code enforces 6-second intervals
- Automatic retry on 429 errors
- Waits 60 seconds if rate limited

## Benefits

✅ **Seamless Integration** - No UI changes needed, automatic routing  
✅ **Same Database** - All data goes to same tables  
✅ **Same UI** - Users see same interface  
✅ **Free Tier Available** - No cost for basic usage  
✅ **Automatic Fallback** - System handles source selection  

## Limitations

⚠️ **Competition IDs** - Need to be verified from API  
⚠️ **Rate Limits** - Free tier: 10 requests/minute  
⚠️ **Historical Data** - Limited compared to football-data.co.uk  
⚠️ **No CSV Files** - Data comes from API only  

## Testing

### Test Single League
```bash
curl -X POST http://localhost:8000/api/data/batch-download \
  -H "Content-Type: application/json" \
  -d '{
    "source": "football-data.co.uk",
    "leagues": [{"code": "SWE1"}],
    "season": "2324"
  }'
```

The system will automatically use Football-Data.org for SWE1.

### Test Multiple Leagues
Select both working and alternative leagues - system routes each to correct source.

## Next Steps

1. ✅ Get API key and add to `.env`
2. ⚠️ **Verify competition IDs** (critical!)
3. ✅ Test with one league
4. ✅ Run batch download
5. ✅ Monitor rate limits

## Files Modified

- `app/config.py` - Added API key settings
- `app/services/data_ingestion.py` - Added source routing
- `app/services/ingestion/ingest_football_data_org.py` - New service
- `src/data/allLeagues.ts` - Added dataSource metadata

## Documentation

- Setup Guide: `FOOTBALL_DATA_ORG_SETUP.md`
- League Availability: `LEAGUE_AVAILABILITY_ANALYSIS.md`

