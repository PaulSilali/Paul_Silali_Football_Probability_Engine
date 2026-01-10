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
import urllib3
from app.services.ingestion.draw_structural_validation import (
    DrawStructuralValidator,
    validate_before_insert
)
from app.config import settings

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
# Use getattr with default True to handle cases where attribute might not exist yet
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def ingest_weather_from_open_meteo(
    db: Session,
    fixture_id: int,
    latitude: float,
    longitude: float,
    match_datetime: datetime
) -> Dict:
    """
    Ingest weather data with automatic fallback to multiple providers.
    
    Tries providers in order:
    1. Open-Meteo (current primary)
    2. Meteostat (historical, free, reproducible)
    3. OpenWeather (live forecasts)
    
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
        # Use fallback system to try multiple providers
        from app.services.ingestion.weather_providers import fetch_weather_with_fallback
        
        weather_data = fetch_weather_with_fallback(
            latitude=latitude,
            longitude=longitude,
            match_datetime=match_datetime
        )
        
        if not weather_data:
            return {"success": False, "error": "All weather providers failed"}
        
        # Extract weather values
        temperature = weather_data.get("temperature")
        rainfall_value = weather_data.get("rainfall", 0.0)
        wind_speed_value = weather_data.get("wind_speed", 0.0)
        provider_used = weather_data.get("provider", "unknown")
        
        logger.debug(f"Using weather data from {provider_used} provider for fixture {fixture_id}")
        
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
        
        # Validate weather index
        context = f" (fixture_id={fixture_id})"
        is_valid, error = DrawStructuralValidator.validate_weather_index(weather_factor, context)
        if not is_valid:
            logger.warning(f"Invalid weather index: {error}, using neutral value")
            weather_factor = 1.0  # Neutral
        
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
        
        logger.info(f"Ingested weather for fixture {fixture_id} from {provider_used}: temp={temperature}°C, rain={rainfall_value}mm, wind={wind_speed_value}km/h")
        
        return {
            "success": True,
            "temperature": float(temperature) if temperature is not None else None,
            "rainfall": float(rainfall_value),
            "wind_speed": float(wind_speed_value),
            "weather_draw_index": weather_factor,
            "provider": provider_used
        }
    
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
        
        # Create DataFrame from all records
        df = pd.DataFrame(weather_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "home_team", "away_team",
                "temperature", "rainfall", "wind_speed", "weather_draw_index"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_weather.csv
        filename = f"{league_code}_{season}_weather.csv"
        
        # Save to both locations
        from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "Weather", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved batch weather CSV for {league_code} ({season}): {len(weather_records)} records")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving batch weather CSV: {e}", exc_info=True)
        raise


def ingest_weather_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest weather data from CSV file in our format.
    
    CSV Format: league_code,season,match_date,home_team,away_team,temperature,rainfall,wind_speed,weather_draw_index
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['league_code', 'season', 'match_date', 'home_team', 'away_team', 'temperature', 'rainfall', 'wind_speed', 'weather_draw_index']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {"success": False, "error": f"Missing required columns: {missing_cols}"}
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                league_code = str(row['league_code']).strip()
                season = str(row['season']).strip()
                match_date = pd.to_datetime(row['match_date']).date()
                home_team_name = str(row['home_team']).strip()
                away_team_name = str(row['away_team']).strip()
                temperature = float(row['temperature']) if pd.notna(row['temperature']) else None
                rainfall = float(row['rainfall']) if pd.notna(row['rainfall']) else None
                wind_speed = float(row['wind_speed']) if pd.notna(row['wind_speed']) else None
                weather_draw_index = float(row['weather_draw_index']) if pd.notna(row['weather_draw_index']) else None
                
                # Find league
                league = db.query(League).filter(League.code == league_code).first()
                if not league:
                    logger.warning(f"League {league_code} not found, skipping")
                    errors += 1
                    continue
                
                # Find teams
                from app.services.team_resolver import resolve_team_safe
                home_team = resolve_team_safe(db, home_team_name, league.id)
                away_team = resolve_team_safe(db, away_team_name, league.id)
                if not home_team or not away_team:
                    logger.warning(f"Teams {home_team_name} or {away_team_name} not found, skipping")
                    errors += 1
                    continue
                
                # Find match
                match = db.query(Match).filter(
                    Match.league_id == league.id,
                    Match.season == season,
                    Match.match_date == match_date,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id
                ).first()
                
                if not match:
                    logger.warning(f"Match not found: {league_code} {season} {match_date} {home_team_name} vs {away_team_name}, skipping")
                    errors += 1
                    continue
                
                # Insert or update in match_weather_historical
                from sqlalchemy import text
                existing = db.execute(
                    text("""
                        SELECT id FROM match_weather_historical 
                        WHERE match_id = :match_id
                    """),
                    {"match_id": match.id}
                ).fetchone()
                
                if existing:
                    db.execute(
                        text("""
                            UPDATE match_weather_historical 
                            SET temperature = :temperature,
                                rainfall = :rainfall,
                                wind_speed = :wind_speed,
                                weather_draw_index = :weather_draw_index
                            WHERE match_id = :match_id
                        """),
                        {
                            "match_id": match.id,
                            "temperature": temperature,
                            "rainfall": rainfall,
                            "wind_speed": wind_speed,
                            "weather_draw_index": weather_draw_index
                        }
                    )
                    updated += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO match_weather_historical 
                            (match_id, temperature, rainfall, wind_speed, weather_draw_index)
                            VALUES (:match_id, :temperature, :rainfall, :wind_speed, :weather_draw_index)
                        """),
                        {
                            "match_id": match.id,
                            "temperature": temperature,
                            "rainfall": rainfall,
                            "wind_speed": wind_speed,
                            "weather_draw_index": weather_draw_index
                        }
                    )
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing weather row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested weather from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting weather from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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
                            
                            # Fetch weather data using fallback system
                            try:
                                from app.services.ingestion.weather_providers import fetch_weather_with_fallback
                                
                                weather_data = fetch_weather_with_fallback(
                                    latitude=latitude,
                                    longitude=longitude,
                                    match_datetime=match_datetime
                                )
                                
                                if weather_data:
                                    temperature = weather_data.get("temperature")
                                    rainfall_value = weather_data.get("rainfall", 0.0)
                                    wind_speed_value = weather_data.get("wind_speed", 0.0)
                                    provider_used = weather_data.get("provider", "unknown")
                                else:
                                    # All providers failed
                                    results["skipped"] += 1
                                    logger.warning(f"No weather data available for match {match_id} on {match_date} (all providers failed)")
                                    continue
                                
                                # Process weather data (same as before)
                                if temperature is not None or rainfall_value > 0 or wind_speed_value > 0:
                                    
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

