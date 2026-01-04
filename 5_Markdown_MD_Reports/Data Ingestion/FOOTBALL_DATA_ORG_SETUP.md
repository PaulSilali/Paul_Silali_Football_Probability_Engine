# Football-Data.org API Integration Setup

## Overview

Football-Data.org API has been integrated as an alternative data source for 17 leagues that are not available on football-data.co.uk.

## Setup Instructions

### 1. Get API Key

1. Visit: https://www.football-data.org/client/register
2. Register for a free account
3. Copy your API key (free tier allows 10 requests per minute)

### 2. Configure API Key

Add to your `.env` file:

```env
FOOTBALL_DATA_ORG_KEY=your_api_key_here
FOOTBALL_DATA_ORG_BASE_URL=https://api.football-data.org/v4
```

### 3. Verify Competition IDs

The competition IDs in `ingest_football_data_org.py` are placeholders and need to be verified.

**To find correct competition IDs:**

1. Make a request to: `https://api.football-data.org/v4/competitions`
2. Search for your league by name
3. Update `LEAGUE_CODE_TO_COMPETITION_ID` mapping in:
   - `2_Backend_Football_Probability_Engine/app/services/ingestion/ingest_football_data_org.py`

**Example:**
```python
LEAGUE_CODE_TO_COMPETITION_ID = {
    'SWE1': 2003,  # Verify this ID from API
    'FIN1': 2010,  # Verify this ID from API
    # ... etc
}
```

### 4. Test Integration

```bash
# Test a single league
curl -X POST http://localhost:8000/api/data/refresh \
  -H "Content-Type: application/json" \
  -d '{"source": "football-data.org", "league_code": "SWE1", "season": "2324"}'
```

## Leagues Using Football-Data.org

The following 17 leagues automatically use Football-Data.org API:

### Europe (9 leagues)
- SWE1 - Allsvenskan (Sweden)
- FIN1 - Veikkausliiga (Finland)
- RO1 - Liga 1 (Romania)
- RUS1 - Premier League (Russia)
- CZE1 - First League (Czech Republic)
- CRO1 - Prva HNL (Croatia)
- SRB1 - SuperLiga (Serbia)
- UKR1 - Premier League (Ukraine)
- IRL1 - Premier Division (Ireland)

### Americas (4 leagues)
- ARG1 - Primera Division (Argentina)
- BRA1 - Serie A (Brazil)
- MEX1 - Liga MX (Mexico)
- USA1 - Major League Soccer (USA)

### Asia & Oceania (4 leagues)
- CHN1 - Super League (China)
- JPN1 - J-League (Japan)
- KOR1 - K League 1 (South Korea)
- AUS1 - A-League (Australia)

## Rate Limits

**Free Tier:**
- 10 requests per minute
- Code automatically enforces 6-second intervals between requests

**Paid Tier:**
- Higher rate limits available
- Update `min_request_interval` in `FootballDataOrgService` if needed

## API Endpoints Used

- `GET /competitions/{id}/matches` - Get matches for a competition
- `GET /competitions` - List all competitions (for finding IDs)

## Data Format

Football-Data.org returns JSON with:
- Match date/time (UTC)
- Home/away team names
- Scores (if finished)
- Match status

The service automatically:
- Resolves team names to database teams
- Creates/updates match records
- Handles missing data gracefully

## Troubleshooting

### "API key not configured"
- Check `.env` file has `FOOTBALL_DATA_ORG_KEY` set
- Restart backend server after adding key

### "Rate limit exceeded"
- Free tier allows 10 requests/minute
- Code automatically waits and retries
- Consider upgrading to paid tier for higher limits

### "Competition ID not found"
- Verify competition ID exists in Football-Data.org API
- Check `LEAGUE_CODE_TO_COMPETITION_ID` mapping

### "No matches returned"
- League may not have data for requested season
- Check season year is correct (e.g., 2023 for 2023/24 season)

## Next Steps

1. ✅ Get API key and add to `.env`
2. ✅ Verify competition IDs are correct
3. ✅ Test with one league first
4. ✅ Run batch download for all 17 leagues
5. ✅ Monitor rate limits and adjust if needed

