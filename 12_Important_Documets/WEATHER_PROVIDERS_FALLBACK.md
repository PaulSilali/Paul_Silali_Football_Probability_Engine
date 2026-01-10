# Weather Providers Fallback System

## Overview

The system now supports multiple weather data providers with automatic fallback. If one provider fails, the system automatically tries the next provider in the list.

## Supported Providers

### 1. Open-Meteo (Primary)
- **Status**: Current default provider
- **Best for**: General use, free tier available
- **Limits**: ~10,000 requests/day (free tier)
- **Features**: Historical + forecast data
- **No API key required**

### 2. Meteostat (Secondary - Historical)
- **Status**: Fallback for historical data
- **Best for**: Historical backtesting, reproducible data
- **Limits**: Free, open-source
- **Features**: Station-based historical data back to 2000+
- **Installation**: `pip install meteostat`
- **No API key required**

### 3. OpenWeather One Call API 3.0 (Tertiary - Live)
- **Status**: Fallback for live forecasts
- **Best for**: Current weather, hourly and daily forecasts
- **Limits**: Free tier: 60 calls/minute, 1,000,000 calls/month
- **Features**: 
  - Current weather
  - Hourly forecast (48 hours)
  - Daily forecast (8 days)
  - Weather alerts
- **API Key Required**: Set `OPENWEATHER_API_KEY` in `.env`
- **Note**: One Call API 3.0 requires "One Call by Call" subscription (free tier available)

## Fallback Order

The system tries providers in this order:

1. **Open-Meteo** (primary)
2. **Meteostat** (historical fallback)
3. **OpenWeather** (live fallback)

If all providers fail, the system returns an error.

## Configuration

### Environment Variables

Add to `.env` file:

```env
# OpenWeather API Key (optional, for fallback)
OPENWEATHER_API_KEY=your_api_key_here
```

### Installing Meteostat

```bash
pip install meteostat
```

## How It Works

### Automatic Fallback

When fetching weather data:

1. System tries Open-Meteo first
2. If Open-Meteo fails → tries Meteostat
3. If Meteostat fails → tries OpenWeather
4. If all fail → returns error

### Provider Selection Logic

- **Historical dates** (< today): Prefers Meteostat if available, falls back to Open-Meteo archive
- **Future dates** (>= today): Prefers Open-Meteo forecast, falls back to OpenWeather forecast
- **Current date**: Tries all providers in order

## Usage

### In Code

The fallback is automatic. Just call the existing function:

```python
from app.services.ingestion.ingest_weather import ingest_weather_from_open_meteo

result = ingest_weather_from_open_meteo(
    db=db,
    fixture_id=fixture_id,
    latitude=51.5074,
    longitude=-0.1278,
    match_datetime=datetime(2024, 1, 15, 15, 0)
)

# Result includes which provider was used
print(f"Weather fetched from: {result.get('provider', 'unknown')}")
```

### Manual Provider Selection

You can also use providers directly:

```python
from app.services.ingestion.weather_providers import (
    OpenMeteoProvider,
    MeteostatProvider,
    OpenWeatherProvider,
    fetch_weather_with_fallback
)

# Use specific providers only
weather_data = fetch_weather_with_fallback(
    latitude=51.5074,
    longitude=-0.1278,
    match_datetime=datetime(2024, 1, 15, 15, 0),
    providers=[
        MeteostatProvider(),  # Try Meteostat first
        OpenWeatherProvider()  # Then OpenWeather
    ]
)
```

## Provider Comparison

| Provider | Historical | Forecast | Free Tier | API Key | Best For |
|----------|-----------|----------|-----------|---------|----------|
| Open-Meteo | ✅ | ✅ | ✅ | ❌ | General use |
| Meteostat | ✅ | ❌ | ✅ | ❌ | Historical data |
| OpenWeather | ⚠️* | ✅ | ✅ | ✅ | Live forecasts |

*OpenWeather historical data requires paid plan or One Call API 3.0

## Benefits

1. **Reliability**: If one provider is down, others can still provide data
2. **Cost Efficiency**: Uses free providers first
3. **Data Quality**: Meteostat provides high-quality historical data
4. **Flexibility**: Easy to add more providers
5. **Transparency**: Logs which provider was used

## Logging

The system logs which provider was used:

```
INFO: Ingested weather for fixture 123 from meteostat: temp=15.5°C, rain=2.3mm, wind=12.5km/h
DEBUG: Weather fetched successfully from meteostat provider
```

## Adding New Providers

To add a new provider:

1. Create a class inheriting from `WeatherProvider`
2. Implement `fetch_weather()` method
3. Add to provider list in `fetch_weather_with_fallback()`

Example:

```python
class NewProvider(WeatherProvider):
    def fetch_weather(self, latitude, longitude, match_datetime):
        # Your implementation
        return {
            "temperature": temp,
            "rainfall": rain,
            "wind_speed": wind,
            "provider": "new-provider"
        }
```

## Troubleshooting

### Meteostat Not Working
- **Error**: "Meteostat library not installed"
- **Solution**: `pip install meteostat`

### OpenWeather Not Working
- **Error**: "OpenWeather API key not configured"
- **Solution**: Add `OPENWEATHER_API_KEY` to `.env`

### All Providers Failing
- Check internet connection
- Verify coordinates are valid
- Check provider status/limits
- Review logs for specific errors

## Recommended Setup

For best results:

1. **Install Meteostat**: `pip install meteostat`
2. **Get OpenWeather API Key**: https://openweathermap.org/api (free tier)
3. **Add to .env**: `OPENWEATHER_API_KEY=your_key`
4. **Keep Open-Meteo**: Already working, no setup needed

This gives you:
- ✅ Primary: Open-Meteo (general use)
- ✅ Fallback 1: Meteostat (historical accuracy)
- ✅ Fallback 2: OpenWeather (live forecasts)

## API Keys

### OpenWeather API Key

1. Sign up at: https://openweathermap.org/api
2. Subscribe to "One Call API 3.0" (free tier available)
3. Get API key from dashboard
4. Add to `.env`: `OPENWEATHER_API_KEY=your_key_here`
5. Free tier: 60 calls/minute, 1M calls/month
6. **Important**: One Call API 3.0 requires subscription activation (free tier available)

### Meteostat

- No API key needed
- Open-source Python library
- Free historical weather data

