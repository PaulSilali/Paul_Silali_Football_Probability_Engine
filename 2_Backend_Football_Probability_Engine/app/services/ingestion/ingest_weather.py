"""
Ingest weather data from Open-Meteo API or similar sources
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import JackpotFixture, MatchWeather, League, Match, Team
from typing import Optional, Dict, List
from datetime import datetime, time, date
from pathlib import Path
import pandas as pd
import logging
import time as time_module

logger = logging.getLogger(__name__)


def ingest_weather_from_open_meteo(
    db: Session,
    fixture_id: int,
    latitude: float,
    longitude: float,
    match_datetime: datetime
) -> Dict:
    """
    Ingest weather data from Open-Meteo API.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        latitude: Stadium latitude
        longitude: Stadium longitude
        match_datetime: Match date and time
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Determine if we need historical API (for dates in the past) or forecast API (for future dates)
        today = date.today()
        match_date_only = match_datetime.date()
        
        # Use historical API for dates more than 2 days in the past
        # Forecast API works for dates up to ~16 days in the future
        if match_date_only < today:
            # Historical weather API for past dates
            url = "https://archive-api.open-meteo.com/v1/archive"
        else:
            # Forecast API for future dates
            url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,rain,wind_speed_10m",
            "start_date": match_datetime.strftime("%Y-%m-%d"),
            "end_date": match_datetime.strftime("%Y-%m-%d"),
            "timezone": "auto"
        }
        
        # Add retry logic with exponential backoff for connection errors
        # Open-Meteo free tier: ~10,000 requests/day, but connection issues can occur
        max_retries = 3
        retry_delay = 2  # Start with 2 second delay
        response = None
        
        for attempt in range(max_retries):
            try:
                # Add a small delay before each request to avoid overwhelming the API
                if attempt > 0:
                    time_module.sleep(retry_delay * (2 ** (attempt - 1)))
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                break  # Success, exit retry loop
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    logger.warning(f"Connection error for fixture {fixture_id} (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time_module.sleep(wait_time)
                else:
                    logger.error(f"Failed to get weather data for fixture {fixture_id} after {max_retries} attempts: {e}")
                    raise  # Re-raise on final attempt
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors (429 rate limit, 500 server error, etc.)
                if e.response.status_code == 429:
                    # Rate limit exceeded - wait longer
                    wait_time = 60  # Wait 60 seconds for rate limit
                    logger.warning(f"Rate limit exceeded for fixture {fixture_id}, waiting {wait_time}s...")
                    time_module.sleep(wait_time)
                    if attempt < max_retries - 1:
                        continue  # Retry after waiting
                    else:
                        raise
                else:
                    # Other HTTP errors - don't retry
                    logger.error(f"HTTP error {e.response.status_code} for fixture {fixture_id}: {e}")
                    raise
        
        if response is None:
            raise requests.exceptions.RequestException("Failed to get response after retries")
        
        data = response.json()
        hourly = data.get("hourly", {})
        
        if not hourly or not hourly.get("time"):
            return {"success": False, "error": "No weather data available"}
        
        # Find closest hour to match time
        match_hour = match_datetime.hour
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        rains = hourly.get("rain", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        
        # Get weather at match hour (or closest)
        idx = min(match_hour, len(times) - 1) if times else 0
        
        temperature = temperatures[idx] if idx < len(temperatures) else None
        rainfall = rains[idx] if idx < len(rains) else None
        wind_speed = wind_speeds[idx] if idx < len(wind_speeds) else None
        
        # Handle None values - convert to 0.0 for calculations
        rainfall_value = float(rainfall) if rainfall is not None else 0.0
        wind_speed_value = float(wind_speed) if wind_speed is not None else 0.0
        
        # Calculate weather draw index
        # Rain and wind increase draw probability, cold temperatures slightly
        weather_draw_index = (
            0.3 * min(rainfall_value / 10.0, 1.0) +  # Rain factor (max 10mm = 0.3)
            0.2 * min(wind_speed_value / 20.0, 1.0) +  # Wind factor (max 20 km/h = 0.2)
            0.1 * (1.0 if temperature is not None and temperature < 5 else 0.0)  # Cold factor
        )
        
        # Normalize to 0.95-1.10 range
        weather_draw_index = max(0.0, min(0.15, weather_draw_index))
        weather_factor = 1.0 + weather_draw_index
        
        # Insert or update
        existing = db.query(MatchWeather).filter(
            MatchWeather.fixture_id == fixture_id
        ).first()
        
        if existing:
            existing.temperature = float(temperature) if temperature is not None else None
            existing.rainfall = float(rainfall_value)
            existing.wind_speed = float(wind_speed_value)
            existing.weather_draw_index = weather_factor
        else:
            weather = MatchWeather(
                fixture_id=fixture_id,
                temperature=float(temperature) if temperature is not None else None,
                rainfall=float(rainfall_value),
                wind_speed=float(wind_speed_value),
                weather_draw_index=weather_factor
            )
            db.add(weather)
        
        db.commit()
        
        logger.info(f"Ingested weather for fixture {fixture_id}: temp={temperature}°C, rain={rainfall_value}mm, wind={wind_speed_value}km/h")
        
        return {
            "success": True,
            "temperature": float(temperature) if temperature is not None else None,
            "rainfall": float(rainfall_value),
            "wind_speed": float(wind_speed_value),
            "weather_draw_index": weather_factor
        }
    
    except requests.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting weather: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_weather_batch(
    db: Session,
    fixture_ids: list[int],
    stadium_coordinates: Dict[int, Dict[str, float]]
) -> Dict:
    """
    Ingest weather for multiple fixtures.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs
        stadium_coordinates: Dict mapping fixture_id to {lat, lon, datetime}
    
    Returns:
        Dict with batch statistics
    """
    success_count = 0
    error_count = 0
    
    for fixture_id in fixture_ids:
        if fixture_id not in stadium_coordinates:
            error_count += 1
            continue
        
        coords = stadium_coordinates[fixture_id]
        result = ingest_weather_from_open_meteo(
            db,
            fixture_id,
            coords["latitude"],
            coords["longitude"],
            coords["datetime"]
        )
        
        if result.get("success"):
            success_count += 1
        else:
            error_count += 1
    
    return {
        "success": True,
        "total": len(fixture_ids),
        "success_count": success_count,
        "error_count": error_count
    }


def _save_weather_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    weather_records: List[Dict]
) -> Path:
    """
    Save CSV file with weather data for all matches in a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        weather_records: List of dictionaries with weather data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not weather_records:
            raise ValueError("No weather records to save")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/Weather")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame from all records
        df = pd.DataFrame(weather_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "home_team", "away_team",
                "temperature", "rainfall", "wind_speed", "weather_draw_index"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_weather.csv
        filename = f"{league_code}_{season}_weather.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved batch weather CSV for {league_code} ({season}): {len(weather_records)} records -> {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving batch weather CSV: {e}", exc_info=True)
        raise


def batch_ingest_weather_from_matches(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest weather data for matches in specified leagues and seasons.
    Note: This requires stadium coordinates which may not be available for all matches.
    
    Args:
        db: Database session
        league_codes: List of league codes to process
        use_all_leagues: If True, process all leagues
        season: Specific season to process
        use_all_seasons: If True, process all available seasons
        max_years: Maximum years back if use_all_seasons is True
        save_csv: Whether to save CSV files
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        from app.services.data_ingestion import get_seasons_list
        
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get leagues to process
        if use_all_leagues:
            leagues = db.query(League).all()
        elif league_codes:
            leagues = db.query(League).filter(League.code.in_(league_codes)).all()
        else:
            return {"success": False, "error": "No leagues specified"}
        
        # Determine seasons to process
        if use_all_seasons:
            seasons = get_seasons_list(max_years)
        elif season:
            seasons = [season]
        else:
            seasons = [None]  # Process all seasons
        
        logger.info(f"Batch processing weather for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Ensure clean transaction state before querying matches
                    try:
                        db.rollback()
                    except:
                        pass
                    
                    # Get matches for this league/season
                    if season_filter:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id AND season = :season
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id, "season": season_filter}
                    else:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id}
                    
                    matches = db.execute(matches_query, matches_params).fetchall()
                    
                    if not matches:
                        continue
                    
                    # Collect weather records for this league/season
                    weather_records = []
                    
                    # Get approximate coordinates for league country (fallback for stadium coordinates)
                    # Using capital city coordinates as approximation
                    country_coords = {
                        'England': {'lat': 51.5074, 'lon': -0.1278},
                        'Spain': {'lat': 40.4168, 'lon': -3.7038},
                        'Germany': {'lat': 52.5200, 'lon': 13.4050},
                        'Italy': {'lat': 41.9028, 'lon': 12.4964},
                        'France': {'lat': 48.8566, 'lon': 2.3522},
                        'Netherlands': {'lat': 52.3676, 'lon': 4.9041},
                        'Portugal': {'lat': 38.7223, 'lon': -9.1393},
                        'Scotland': {'lat': 55.9533, 'lon': -3.1883},
                        'Belgium': {'lat': 50.8503, 'lon': 4.3517},
                        'Turkey': {'lat': 41.0082, 'lon': 28.9784},
                        'Greece': {'lat': 37.9838, 'lon': 23.7275},
                        'Mexico': {'lat': 19.4326, 'lon': -99.1332},
                        'USA': {'lat': 38.9072, 'lon': -77.0369},
                        'China': {'lat': 39.9042, 'lon': 116.4074},
                        'Japan': {'lat': 35.6762, 'lon': 139.6503},
                        'Australia': {'lat': -33.8688, 'lon': 151.2093},
                    }
                    
                    # Get default coordinates for this league's country
                    default_coords = country_coords.get(league.country, {'lat': 51.5074, 'lon': -0.1278})  # Default to London
                    
                    for match in matches:
                        match_id = match.id
                        match_date = match.match_date
                        home_team_id = match.home_team_id
                        away_team_id = match.away_team_id
                        results["total"] += 1
                        
                        # Add delay between requests to avoid rate limiting
                        # Open-Meteo free tier allows ~10,000 requests/day
                        # Use 1 second delay to stay well under limits and avoid connection errors
                        if results["total"] > 1:
                            time_module.sleep(1.0)  # 1 second delay between requests
                        
                        try:
                            # Get team names
                            home_team = db.query(Team).filter(Team.id == home_team_id).first()
                            away_team = db.query(Team).filter(Team.id == away_team_id).first()
                            
                            # Use default coordinates (approximate)
                            latitude = default_coords['lat']
                            longitude = default_coords['lon']
                            
                            # Create datetime for match (assume 3 PM local time)
                            match_datetime = datetime.combine(match_date, time(hour=15, minute=0))
                            
                            # Fetch weather data directly from API (without DB write)
                            try:
                                # Determine if we need historical API (for dates in the past) or forecast API (for future dates)
                                today = date.today()
                                match_date_only = match_datetime.date()
                                
                                # Use historical API for dates in the past
                                # Forecast API works for dates up to ~16 days in the future
                                if match_date_only < today:
                                    # Historical weather API for past dates
                                    url = "https://archive-api.open-meteo.com/v1/archive"
                                else:
                                    # Forecast API for future dates
                                    url = "https://api.open-meteo.com/v1/forecast"
                                
                                params = {
                                    "latitude": latitude,
                                    "longitude": longitude,
                                    "hourly": "temperature_2m,rain,wind_speed_10m",
                                    "start_date": match_datetime.strftime("%Y-%m-%d"),
                                    "end_date": match_datetime.strftime("%Y-%m-%d"),
                                    "timezone": "auto"
                                }
                                
                                # Add retry logic with exponential backoff for connection errors
                                # Open-Meteo free tier: ~10,000 requests/day, but connection issues can occur
                                max_retries = 3
                                retry_delay = 2  # Start with 2 second delay
                                response = None
                                
                                for attempt in range(max_retries):
                                    try:
                                        # Add a small delay before each request attempt
                                        if attempt > 0:
                                            time_module.sleep(retry_delay * (2 ** (attempt - 1)))
                                        
                                        response = requests.get(url, params=params, timeout=30)
                                        response.raise_for_status()
                                        break  # Success, exit retry loop
                                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError) as e:
                                        if attempt < max_retries - 1:
                                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                                            logger.warning(f"Connection error for match {match_id} (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                            time_module.sleep(wait_time)
                                        else:
                                            logger.error(f"Failed to get weather data for match {match_id} after {max_retries} attempts: {e}")
                                            raise  # Re-raise on final attempt
                                    except requests.exceptions.HTTPError as e:
                                        # Handle HTTP errors (429 rate limit, 500 server error, etc.)
                                        if e.response.status_code == 429:
                                            # Rate limit exceeded - wait longer
                                            wait_time = 60  # Wait 60 seconds for rate limit
                                            logger.warning(f"Rate limit exceeded for match {match_id}, waiting {wait_time}s...")
                                            time_module.sleep(wait_time)
                                            if attempt < max_retries - 1:
                                                continue  # Retry after waiting
                                            else:
                                                raise
                                        else:
                                            # Other HTTP errors - don't retry
                                            logger.error(f"HTTP error {e.response.status_code} for match {match_id}: {e}")
                                            raise
                                
                                if response is None:
                                    raise requests.exceptions.RequestException("Failed to get response after retries")
                                
                                data = response.json()
                                hourly = data.get("hourly", {})
                                
                                if hourly and hourly.get("time"):
                                    # Find closest hour to match time
                                    match_hour = match_datetime.hour
                                    times = hourly.get("time", [])
                                    temperatures = hourly.get("temperature_2m", [])
                                    rains = hourly.get("rain", [])
                                    wind_speeds = hourly.get("wind_speed_10m", [])
                                    
                                    # Get weather at match hour (or closest)
                                    idx = min(match_hour, len(times) - 1) if times else 0
                                    
                                    temperature = temperatures[idx] if idx < len(temperatures) else None
                                    rainfall = rains[idx] if idx < len(rains) else None
                                    wind_speed = wind_speeds[idx] if idx < len(wind_speeds) else None
                                    
                                    # Handle None values - convert to 0.0 for calculations
                                    rainfall_value = float(rainfall) if rainfall is not None else 0.0
                                    wind_speed_value = float(wind_speed) if wind_speed is not None else 0.0
                                    
                                    # Calculate weather draw index
                                    weather_draw_index = (
                                        0.3 * min(rainfall_value / 10.0, 1.0) +
                                        0.2 * min(wind_speed_value / 20.0, 1.0) +
                                        0.1 * (1.0 if temperature is not None and temperature < 5 else 0.0)
                                    )
                                    weather_draw_index = max(0.0, min(0.15, weather_draw_index))
                                    weather_factor = 1.0 + weather_draw_index
                                    
                                    # Save to database using raw SQL (since match_weather requires fixture_id)
                                    # We'll create a match_weather_historical table or use a workaround
                                    # For now, save to a separate table that links to matches
                                    db_saved = False
                                    try:
                                        # Ensure we're in a clean transaction state
                                        try:
                                            db.rollback()
                                        except:
                                            pass
                                        
                                        # Try to insert into match_weather_historical if it exists
                                        # Otherwise, we'll need to create it first
                                        insert_query = text("""
                                            INSERT INTO match_weather_historical 
                                            (match_id, temperature, rainfall, wind_speed, weather_draw_index, recorded_at)
                                            VALUES (:match_id, :temperature, :rainfall, :wind_speed, :weather_draw_index, NOW())
                                            ON CONFLICT (match_id) DO UPDATE SET
                                                temperature = EXCLUDED.temperature,
                                                rainfall = EXCLUDED.rainfall,
                                                wind_speed = EXCLUDED.wind_speed,
                                                weather_draw_index = EXCLUDED.weather_draw_index,
                                                recorded_at = NOW()
                                        """)
                                        
                                        db.execute(insert_query, {
                                            "match_id": match_id,
                                            "temperature": float(temperature) if temperature is not None else None,
                                            "rainfall": float(rainfall_value),
                                            "wind_speed": float(wind_speed_value),
                                            "weather_draw_index": weather_factor
                                        })
                                        db.commit()
                                        db_saved = True
                                        
                                    except Exception as db_error:
                                        # Always rollback on error to clear transaction state
                                        try:
                                            db.rollback()
                                        except:
                                            pass
                                        
                                        # If table doesn't exist, create it
                                        if "does not exist" in str(db_error) or "relation" in str(db_error).lower() or "InFailedSqlTransaction" in str(db_error):
                                            try:
                                                # Rollback first to clear any aborted transaction
                                                try:
                                                    db.rollback()
                                                except:
                                                    pass
                                                
                                                create_table_query = text("""
                                                    CREATE TABLE IF NOT EXISTS match_weather_historical (
                                                        id SERIAL PRIMARY KEY,
                                                        match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                                                        temperature DOUBLE PRECISION,
                                                        rainfall DOUBLE PRECISION CHECK (rainfall >= 0),
                                                        wind_speed DOUBLE PRECISION CHECK (wind_speed >= 0),
                                                        weather_draw_index DOUBLE PRECISION,
                                                        recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                                                        CONSTRAINT uix_match_weather_historical_match UNIQUE (match_id)
                                                    );
                                                    CREATE INDEX IF NOT EXISTS idx_match_weather_historical_match ON match_weather_historical(match_id);
                                                """)
                                                db.execute(create_table_query)
                                                db.commit()
                                                
                                                # Now try insert again
                                                insert_query = text("""
                                                    INSERT INTO match_weather_historical 
                                                    (match_id, temperature, rainfall, wind_speed, weather_draw_index, recorded_at)
                                                    VALUES (:match_id, :temperature, :rainfall, :wind_speed, :weather_draw_index, NOW())
                                                    ON CONFLICT (match_id) DO UPDATE SET
                                                        temperature = EXCLUDED.temperature,
                                                        rainfall = EXCLUDED.rainfall,
                                                        wind_speed = EXCLUDED.wind_speed,
                                                        weather_draw_index = EXCLUDED.weather_draw_index,
                                                        recorded_at = NOW()
                                                """)
                                                
                                                db.execute(insert_query, {
                                                    "match_id": match_id,
                                                    "temperature": float(temperature) if temperature is not None else None,
                                                    "rainfall": float(rainfall_value),
                                                    "wind_speed": float(wind_speed_value),
                                                    "weather_draw_index": weather_factor
                                                })
                                                db.commit()
                                                db_saved = True
                                                
                                            except Exception as create_error:
                                                try:
                                                    db.rollback()
                                                except:
                                                    pass
                                                logger.warning(f"Failed to create/save weather to database for match {match_id}: {create_error}")
                                                # Continue anyway - at least CSV will be saved
                                        else:
                                            logger.warning(f"Failed to save weather to database for match {match_id}: {db_error}")
                                    
                                    # Always add to CSV records (regardless of DB save status)
                                    weather_records.append({
                                        "league_code": league.code,
                                        "season": season_filter or "all",
                                        "match_date": match_date.isoformat() if hasattr(match_date, "isoformat") else str(match_date),
                                        "home_team": home_team.name if home_team else f"Team {home_team_id}",
                                        "away_team": away_team.name if away_team else f"Team {away_team_id}",
                                        "temperature": float(temperature) if temperature is not None else None,
                                        "rainfall": float(rainfall_value),
                                        "wind_speed": float(wind_speed_value),
                                        "weather_draw_index": weather_factor
                                    })
                                    
                                    # Only count as successful if database save succeeded
                                    if db_saved:
                                        results["successful"] += 1
                                        logger.debug(f"Successfully saved weather for match {match_id} to database")
                                    else:
                                        results["failed"] += 1
                                        logger.warning(f"Weather not saved to database for match {match_id}, but CSV will be saved")
                                else:
                                    results["skipped"] += 1
                                    logger.warning(f"No weather data available for match {match_id} on {match_date}")
                            
                            except requests.RequestException as e:
                                results["failed"] += 1
                                logger.warning(f"Weather API request failed for match {match_id}: {e}")
                            except Exception as e:
                                results["failed"] += 1
                                logger.warning(f"Failed to fetch weather for match {match_id}: {e}")
                        
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to process weather for match {match_id}: {e}")
                    
                    # Save CSV for this league/season combination
                    if save_csv and weather_records:
                        try:
                            csv_path = _save_weather_csv_batch(db, league.code, season_filter or "all", weather_records)
                            logger.info(f"Saved Weather CSV for {league.code} ({season_filter or 'all'}): {len(weather_records)} records")
                        except Exception as e:
                            logger.warning(f"Failed to save Weather CSV for {league.code} ({season_filter or 'all'}): {e}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        logger.info(f"Batch weather ingestion complete: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch weather ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

