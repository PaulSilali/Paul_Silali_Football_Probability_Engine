"""
Weather data providers with fallback support.

Supports multiple weather APIs:
1. Open-Meteo (current primary)
2. Meteostat (historical, free, reproducible)
3. OpenWeather (live forecasts)
"""
import requests
from typing import Dict, Optional
from datetime import datetime, date
import logging
import pandas as pd
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)


class WeatherProvider:
    """Base class for weather providers"""
    
    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        match_datetime: datetime
    ) -> Optional[Dict]:
        """
        Fetch weather data for given location and time.
        
        Returns:
            Dict with keys: temperature, rainfall, wind_speed
            None if fetch fails
        """
        raise NotImplementedError


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo API provider (current primary)"""
    
    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        match_datetime: datetime
    ) -> Optional[Dict]:
        """Fetch weather from Open-Meteo API"""
        try:
            today = date.today()
            match_date_only = match_datetime.date()
            
            # Use historical API for past dates, forecast for future
            if match_date_only < today:
                url = "https://archive-api.open-meteo.com/v1/archive"
            else:
                url = "https://api.open-meteo.com/v1/forecast"
            
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,rain,wind_speed_10m",
                "start_date": match_datetime.strftime("%Y-%m-%d"),
                "end_date": match_datetime.strftime("%Y-%m-%d"),
                "timezone": "auto"
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, params=params, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            hourly = data.get("hourly", {})
            
            if not hourly or not hourly.get("time"):
                return None
            
            # Find closest hour to match time
            match_hour = match_datetime.hour
            times = hourly.get("time", [])
            temperatures = hourly.get("temperature_2m", [])
            rains = hourly.get("rain", [])
            wind_speeds = hourly.get("wind_speed_10m", [])
            
            idx = min(match_hour, len(times) - 1) if times else 0
            
            temperature = temperatures[idx] if idx < len(temperatures) else None
            rainfall = rains[idx] if idx < len(rains) else None
            wind_speed = wind_speeds[idx] if idx < len(wind_speeds) else None
            
            return {
                "temperature": float(temperature) if temperature is not None else None,
                "rainfall": float(rainfall) if rainfall is not None else 0.0,
                "wind_speed": float(wind_speed) if wind_speed is not None else 0.0,
                "provider": "open-meteo"
            }
        except Exception as e:
            logger.debug(f"Open-Meteo provider failed: {e}")
            return None


class MeteostatProvider(WeatherProvider):
    """Meteostat API provider (best for historical data)"""
    
    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        match_datetime: datetime
    ) -> Optional[Dict]:
        """Fetch weather from Meteostat API"""
        try:
            # Meteostat uses station-based data, requires Point and Daily/Hourly
            try:
                from meteostat import Point, Hourly
            except ImportError:
                logger.warning("Meteostat library not installed. Install with: pip install meteostat")
                return None
            
            # Create point from lat/lon
            location = Point(latitude, longitude)
            
            # Get hourly data for the match date
            match_date = match_datetime.date()
            start = datetime.combine(match_date, datetime.min.time())
            end = datetime.combine(match_date, datetime.max.time())
            
            # Fetch hourly data
            data = Hourly(location, start, end)
            df = data.fetch()
            
            if df.empty:
                return None
            
            # Find closest hour to match time
            match_hour = match_datetime.hour
            # Meteostat returns hourly data, find the row closest to match hour
            df['hour'] = df.index.hour
            closest_row = df.iloc[(df['hour'] - match_hour).abs().argsort()[:1]]
            
            if closest_row.empty:
                return None
            
            # Extract weather data
            temperature = closest_row['temp'].iloc[0] if 'temp' in closest_row.columns else None
            rainfall = closest_row['prcp'].iloc[0] if 'prcp' in closest_row.columns else None
            wind_speed = closest_row['wspd'].iloc[0] if 'wspd' in closest_row.columns else None
            
            # Helper to safely convert to float, handling NaN
            def safe_float(value):
                if value is None:
                    return None
                try:
                    if pd.isna(value) or np.isnan(value):
                        return None
                    return float(value)
                except (TypeError, ValueError):
                    return None
            
            return {
                "temperature": safe_float(temperature),
                "rainfall": safe_float(rainfall) if safe_float(rainfall) is not None else 0.0,
                "wind_speed": safe_float(wind_speed) if safe_float(wind_speed) is not None else 0.0,
                "provider": "meteostat"
            }
        except Exception as e:
            logger.debug(f"Meteostat provider failed: {e}")
            return None


class OpenWeatherProvider(WeatherProvider):
    """OpenWeather One Call API 3.0 provider (best for live forecasts and current weather)"""
    
    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        match_datetime: datetime
    ) -> Optional[Dict]:
        """Fetch weather from OpenWeather One Call API 3.0"""
        try:
            api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
            if not api_key:
                logger.debug("OpenWeather API key not configured")
                return None
            
            today = date.today()
            match_date_only = match_datetime.date()
            match_timestamp = int(match_datetime.timestamp())
            
            # Use One Call API 3.0 (includes current, hourly, daily forecasts)
            url = "https://api.openweathermap.org/data/3.0/onecall"
            
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": api_key,
                "units": "metric"  # Celsius, meters/sec, mm
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, params=params, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            
            # One Call API 3.0 provides current, hourly, and daily data
            if match_date_only == today:
                # Use current weather for today's matches
                current = data.get("current", {})
                if current:
                    main_temp = current.get("temp")
                    rain = current.get("rain", {})
                    rainfall = rain.get("1h", 0.0) if isinstance(rain, dict) else 0.0
                    wind = current.get("wind_speed", 0.0) * 3.6  # Convert m/s to km/h
                    
                    return {
                        "temperature": float(main_temp) if main_temp is not None else None,
                        "rainfall": float(rainfall) if rainfall is not None else 0.0,
                        "wind_speed": float(wind) if wind is not None else 0.0,
                        "provider": "openweather-onecall"
                    }
            
            # For future dates, use hourly forecast
            hourly = data.get("hourly", [])
            if hourly:
                # Find closest hourly forecast to match time
                closest_hour = min(
                    hourly,
                    key=lambda h: abs(h.get("dt", 0) - match_timestamp)
                )
                
                temp = closest_hour.get("temp")
                rain = closest_hour.get("rain", {})
                rainfall = rain.get("1h", 0.0) if isinstance(rain, dict) else 0.0
                wind = closest_hour.get("wind_speed", 0.0) * 3.6  # Convert m/s to km/h
                
                return {
                    "temperature": float(temp) if temp is not None else None,
                    "rainfall": float(rainfall) if rainfall is not None else 0.0,
                    "wind_speed": float(wind) if wind is not None else 0.0,
                    "provider": "openweather-onecall"
                }
            
            # Fallback to current weather if no hourly data
            current = data.get("current", {})
            if current:
                main_temp = current.get("temp")
                rain = current.get("rain", {})
                rainfall = rain.get("1h", 0.0) if isinstance(rain, dict) else 0.0
                wind = current.get("wind_speed", 0.0) * 3.6
                
                return {
                    "temperature": float(main_temp) if main_temp is not None else None,
                    "rainfall": float(rainfall) if rainfall is not None else 0.0,
                    "wind_speed": float(wind) if wind is not None else 0.0,
                    "provider": "openweather-onecall"
                }
            
            return None
            
        except requests.exceptions.HTTPError as e:
            # Handle specific OpenWeather errors
            if e.response.status_code == 401:
                logger.debug("OpenWeather API key invalid or expired")
            elif e.response.status_code == 429:
                logger.debug("OpenWeather rate limit exceeded")
            else:
                logger.debug(f"OpenWeather HTTP error {e.response.status_code}: {e}")
            return None
        except Exception as e:
            logger.debug(f"OpenWeather provider failed: {e}")
            return None


def fetch_weather_with_fallback(
    latitude: float,
    longitude: float,
    match_datetime: datetime,
    providers: Optional[list] = None
) -> Optional[Dict]:
    """
    Fetch weather data with automatic fallback to alternative providers.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        match_datetime: Match date and time
        providers: List of provider instances to try (default: all available)
    
    Returns:
        Dict with weather data or None if all providers fail
    """
    if providers is None:
        # Default provider order: Open-Meteo (current), Meteostat (historical), OpenWeather (live)
        providers = [
            OpenMeteoProvider(),
            MeteostatProvider(),
            OpenWeatherProvider()
        ]
    
    last_error = None
    for provider in providers:
        try:
            result = provider.fetch_weather(latitude, longitude, match_datetime)
            if result:
                logger.debug(f"Weather fetched successfully from {result.get('provider', 'unknown')} provider")
                return result
        except Exception as e:
            last_error = e
            logger.debug(f"Provider {provider.__class__.__name__} failed: {e}")
            continue
    
    logger.warning(f"All weather providers failed. Last error: {last_error}")
    return None

