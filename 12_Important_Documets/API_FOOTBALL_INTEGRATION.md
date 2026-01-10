# API-Football Integration Guide

## Overview

The system integrates with API-Football (api-sports.io) to automatically download team injury data during live predictions. This ensures predictions always use the most up-to-date injury information.

## API Configuration

### Base URL
- **Football API**: `https://v3.football.api-sports.io`
- **Authentication**: Uses `x-apisports-key` header (not RapidAPI)

### Authentication Header
```python
headers = {
    "x-apisports-key": "your_api_key_here"
}
```

**Note**: The `x-rapidapi-host` header is NOT needed when using API-Sports directly (only needed for RapidAPI proxy).

## Rate Limits

### Free Tier Limits
- **Daily Requests**: Varies by plan (check dashboard)
- **Per-Minute Requests**: ~10 requests/minute (6 seconds between requests recommended)

### Rate Limit Headers
The API returns rate limit information in response headers:

- `x-ratelimit-requests-limit`: Daily request limit
- `x-ratelimit-requests-remaining`: Remaining daily requests
- `X-RateLimit-Limit`: Per-minute request limit
- `X-RateLimit-Remaining`: Remaining per-minute requests

### Rate Limit Handling

The system automatically handles rate limits:

1. **Pre-emptive Checking**: Checks `X-RateLimit-Remaining` header before making requests
2. **429 Error Handling**: If rate limit exceeded (429 status), waits 60 seconds and retries
3. **Batch Processing**: Uses 6-second intervals between requests for batch downloads
4. **Logging**: Logs rate limit status for monitoring

## Implementation Details

### Automatic Download During Prediction

When calculating probabilities for a jackpot:

1. **Check for Existing Injuries**: Queries database for injury data
2. **Auto-Download if Missing**: If injuries not found and `API_FOOTBALL_KEY` is configured:
   - Finds API-Football fixture ID using date, league, and team names
   - Downloads injury data from API-Football
   - Parses and saves to database
   - Uses fresh injury data in probability calculation

### Fixture ID Mapping

The system uses fuzzy matching to find API-Football fixture IDs:

1. **Query by Date & League**: Searches fixtures for the match date and league
2. **Fuzzy Team Matching**: Uses similarity scoring (70%+ threshold) to match team names
3. **Date Window**: Searches ±1 day to account for timezone differences
4. **Best Match Selection**: Selects fixture with highest combined similarity score

### Injury Data Parsing

Parses API-Football injury response to extract:

- **Key Players Missing**: Count of important injured players
- **Injury Severity**: Calculated severity score (0.0-1.0)
- **Position-Specific**: Attackers, midfielders, defenders, goalkeepers
- **Notes**: Additional injury information

## Environment Configuration

Add to `.env` file:

```env
API_FOOTBALL_KEY=your_api_key_here
```

Get your API key from: https://dashboard.api-football.com

## Usage

### Manual Download (UI)

1. Go to **Draw Structural Ingestion** → **Team Injuries** tab
2. Select leagues or fixtures
3. Click **"Download Injuries from API-Football"**
4. System downloads injuries for selected fixtures

### Automatic Download (During Prediction)

1. Create a jackpot with fixtures
2. Click **"Calculate Probabilities"**
3. System automatically downloads missing injury data
4. Probabilities reflect current injury status

## Error Handling

- **Missing API Key**: Skips auto-download, uses existing data
- **Rate Limit Exceeded**: Waits 60 seconds and retries
- **Fixture Not Found**: Logs warning, continues without injuries
- **API Errors**: Logs error, continues prediction without injuries

## Monitoring

Check logs for:
- `✓ Auto-downloaded injuries for fixture {id}`: Successful download
- `⚠ Injury auto-download failed`: Download failed (non-critical)
- `API-Football daily requests remaining: {count}`: Rate limit status
- `API-Football per-minute rate limit low`: Approaching per-minute limit

## Best Practices

1. **Monitor Rate Limits**: Check daily remaining requests regularly
2. **Cache Data**: Injuries don't change frequently, so avoid re-downloading unnecessarily
3. **Batch Downloads**: Use batch download during off-peak hours
4. **Error Handling**: System gracefully handles API failures

## API Endpoints Used

1. **GET /fixtures**: Find fixture ID by date, league, and teams
2. **GET /injuries**: Get injury data for a specific fixture

## Support

- **API Documentation**: https://www.api-football.com/documentation-v3
- **Dashboard**: https://dashboard.api-football.com
- **Support**: https://dashboard.api-football.com (contact through dashboard)

