"""
Data Ingestion Service

Handles importing match data from various sources
"""
import csv
import io
import requests
from typing import List, Dict, Optional
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path
import logging
import urllib3
from app.db.models import (
    League, Team, Match, DataSource, IngestionLog, MatchResult
)
from app.services.team_resolver import resolve_team_safe, normalize_team_name
from app.services.data_cleaning import DataCleaningService
from app.config import settings

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
# Use getattr with default True to handle cases where attribute might not exist yet
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("SSL certificate verification is DISABLED. This is insecure and should only be used in development!")

# Maximum years back for data ingestion (7 years)
MAX_YEARS_BACK = 7

# Season mapping: frontend format (2023-24) to football-data.co.uk format (2324)
def get_season_code(season_str: str) -> str:
    """Convert season string to football-data.co.uk format"""
    if season_str == "all" or season_str == "last7" or season_str == "last10":
        return season_str  # Return as-is to handle in ingest_from_football_data
    # Format: "2023-24" -> "2324"
    parts = season_str.split("-")
    if len(parts) == 2:
        start_year = parts[0][-2:]  # Last 2 digits
        end_year = parts[1]
        return f"{start_year}{end_year}"
    return season_str

def get_seasons_list(max_years: int = MAX_YEARS_BACK) -> List[str]:
    """Get list of seasons for 'all' option (last N years)"""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Determine current season (assumes season starts in August)
    if current_month >= 8:
        current_season_start = current_year
    else:
        current_season_start = current_year - 1
    
    seasons = []
    for i in range(max_years):
        year_start = current_season_start - i
        year_end = year_start + 1
        # Format: 2023-24 -> 2324
        season_code = f"{str(year_start)[-2:]}{str(year_end)[-2:]}"
        seasons.append(season_code)
    
    return seasons


class DataIngestionService:
    """Service for ingesting match data from various sources"""
    
    # Leagues that should use Football-Data.org API (not available on football-data.co.uk)
    FOOTBALL_DATA_ORG_LEAGUES = {
        'SWE1', 'FIN1', 'RO1', 'RUS1', 'IRL1',  # Europe
        'CZE1', 'CRO1', 'SRB1', 'UKR1',  # Eastern Europe
        'ARG1', 'BRA1', 'MEX1', 'USA1',  # Americas
        'CHN1', 'JPN1', 'KOR1', 'AUS1'  # Asia & Oceania
    }
    
    # Leagues available from OpenFootball (free, no API required)
    # These will be tried as fallback if Football-Data.org fails
    OPENFOOTBALL_LEAGUES = {
        'SWE1', 'FIN1', 'RO1', 'RUS1', 'IRL1',  # Europe
        'CZE1', 'CRO1', 'SRB1', 'UKR1',  # Eastern Europe
        'ARG1', 'BRA1', 'MEX1', 'USA1',  # Americas
        'CHN1', 'JPN1', 'KOR1', 'AUS1'  # Asia & Oceania
    }
    
    def __init__(self, db: Session, enable_cleaning: bool = True):
        """
        Initialize data ingestion service
        
        Args:
            db: Database session
            enable_cleaning: Enable Phase 1 data cleaning (default: True)
        """
        self.db = db
        self.enable_cleaning = enable_cleaning
        self.cleaning_service = DataCleaningService(
            missing_threshold=0.5,
            enable_cleaning=enable_cleaning
        ) if enable_cleaning else None
    
    def ingest_csv(
        self,
        csv_content: str,
        league_code: str,
        season: str,
        source_name: str = "football-data.co.uk",
        batch_number: Optional[int] = None,
        save_csv: bool = True,
        download_session_folder: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Ingest match data from CSV content
        
        Expected CSV format (football-data.co.uk):
        Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,AvgH,AvgD,AvgA
        
        Returns:
            Dict with counts: processed, inserted, updated, skipped, errors
        """
        # Get or create data source
        data_source = self.db.query(DataSource).filter(
            DataSource.name == source_name
        ).first()
        
        if not data_source:
            data_source = DataSource(
                name=source_name,
                source_type="csv",
                status="running"
            )
            self.db.add(data_source)
            self.db.flush()
        
        # Create ingestion log ONLY if batch_number is not provided
        # This allows reusing the same batch for multiple CSV files
        ingestion_log = None
        if batch_number is None:
            # Create new batch
            ingestion_log = IngestionLog(
                source_id=data_source.id,
                status="running"
            )
            self.db.add(ingestion_log)
            self.db.flush()
            batch_number = ingestion_log.id
        else:
            # If batch_number provided, find existing log (should exist from batch operation)
            # Always query fresh from DB to ensure we have it even after rollbacks
            ingestion_log = self.db.query(IngestionLog).filter(
                IngestionLog.id == batch_number
            ).first()
            
            # If log doesn't exist, this is an error (batch should be created before calling ingest_csv)
            if not ingestion_log:
                logger.error(f"IngestionLog {batch_number} not found! This should not happen. Creating new one.")
                ingestion_log = IngestionLog(
                    source_id=data_source.id,
                    status="running"
                )
                self.db.add(ingestion_log)
                self.db.flush()
                # Use the new log's ID instead
                batch_number = ingestion_log.id
        
        # Save RAW CSV file FIRST (before cleaning) to 1_data_ingestion folder
        raw_csv_content = csv_content  # Store original raw content
        if save_csv:
            try:
                raw_csv_path = self._save_csv_file(
                    raw_csv_content,  # Save RAW data before cleaning
                    league_code, 
                    season, 
                    batch_number,
                    download_session_folder
                )
                logger.info(f"Raw CSV saved to: {raw_csv_path}")
            except Exception as e:
                logger.warning(f"Failed to save raw CSV file: {e}")
        
        # Apply data cleaning (after saving raw data, before parsing)
        cleaning_stats = None
        cleaned_csv_content = raw_csv_content  # Default to raw if cleaning disabled
        if self.enable_cleaning and self.cleaning_service:
            try:
                # Use Phase 2 (includes Phase 1) for enhanced features
                from app.config import settings
                cleaning_phase = getattr(settings, 'DATA_CLEANING_PHASE', 'phase1')  # Default to phase1
                
                logger.info(f"Applying data cleaning (phase: {cleaning_phase})...")
                cleaned_csv_content, cleaning_stats = self.cleaning_service.clean_csv_content(
                    raw_csv_content,  # Clean the raw content
                    return_stats=True,
                    phase=cleaning_phase  # "phase1", "phase2", or "both"
                )
                if cleaning_stats:
                    logger.info(
                        f"Cleaning stats: {cleaning_stats['rows_removed']} rows removed, "
                        f"{len(cleaning_stats['columns_dropped'])} columns dropped"
                    )
            except Exception as e:
                logger.error(f"Error during data cleaning: {e}", exc_info=True)
                logger.warning("Continuing with original CSV content")
                # Continue with original content if cleaning fails
                cleaned_csv_content = raw_csv_content
        
        # Save CLEANED CSV file to 2_Cleaned_data folder if cleaning was applied
        if save_csv and self.enable_cleaning and self.cleaning_service:
                    try:
                        cleaned_csv_path = self._save_cleaned_csv_file(
                    cleaned_csv_content,  # Save CLEANED data
                            league_code,
                            season,
                            download_session_folder
                        )
                        logger.info(f"Cleaned CSV saved to: {cleaned_csv_path}")
                    except Exception as e:
                        logger.error(f"Failed to save cleaned CSV file: {e}", exc_info=True)
        
        # Use cleaned content for parsing (if cleaning was applied)
        csv_content = cleaned_csv_content
        
        # Mapping of league codes to proper names (from football-data.co.uk)
        league_names = {
            'E0': ('Premier League', 'England', 1),
            'E1': ('Championship', 'England', 2),
            'E2': ('League One', 'England', 3),
            'E3': ('League Two', 'England', 4),
            'SP1': ('La Liga', 'Spain', 1),
            'SP2': ('La Liga 2', 'Spain', 2),
            'D1': ('Bundesliga', 'Germany', 1),
            'D2': ('2. Bundesliga', 'Germany', 2),
            'I1': ('Serie A', 'Italy', 1),
            'I2': ('Serie B', 'Italy', 2),
            'F1': ('Ligue 1', 'France', 1),
            'F2': ('Ligue 2', 'France', 2),
            'N1': ('Eredivisie', 'Netherlands', 1),
            'P1': ('Primeira Liga', 'Portugal', 1),
            'SC0': ('Scottish Premiership', 'Scotland', 1),
            'SC1': ('Scottish Championship', 'Scotland', 2),
            'SC2': ('Scottish League One', 'Scotland', 3),
            'SC3': ('Scottish League Two', 'Scotland', 4),
            'T1': ('Super Lig', 'Turkey', 1),
            'G1': ('Super League', 'Greece', 1),
            'NO1': ('Eliteserien', 'Norway', 1),
            'SW1': ('Allsvenskan', 'Sweden', 1),
            'DK1': ('Superliga', 'Denmark', 1),
            'B1': ('Pro League', 'Belgium', 1),
            'A1': ('Bundesliga', 'Austria', 1),
        }
        
        # Get league - create if it doesn't exist (for football-data.co.uk leagues)
        league = self.db.query(League).filter(
            League.code == league_code
        ).first()
        
        # Update existing league if it has a placeholder name
        if league and league.name.startswith("League ") and league_code in league_names:
            league_info = league_names[league_code]
            league.name = league_info[0]
            league.country = league_info[1]
            league.tier = league_info[2]
            self.db.commit()
            logger.info(f"Updated league {league_code} name from '{league.name}' to '{league_info[0]}'")
        
        if not league:
            # Try to create league automatically for known football-data.co.uk codes
            # This prevents failures when leagues exist in CSV but not in DB
            logger.warning(f"League {league_code} not found in database. Attempting to create...")
            try:
                # Get league info from mapping (defined above)
                league_info = league_names.get(league_code)
                if league_info:
                    name, country, tier = league_info
                else:
                    # Fallback for unknown codes
                    name = f"League {league_code}"
                    country = "Unknown"
                    tier = 1
                
                # Create league entry with proper name
                league = League(
                    code=league_code,
                    name=name,
                    country=country,
                    tier=tier,
                    is_active=True
                )
                self.db.add(league)
                self.db.flush()
                logger.info(f"Created league {league_code} ({name}) in database")
            except Exception as e:
                logger.error(f"Failed to create league {league_code}: {e}")
                raise ValueError(f"League not found: {league_code} and could not be created")
        
        stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        errors = []
        
        try:
            # Parse CSV with better error handling
            try:
                reader = csv.DictReader(io.StringIO(csv_content))
                # Get fieldnames to check if required columns exist
                fieldnames = reader.fieldnames
                if not fieldnames:
                    raise ValueError(f"CSV file for {league_code} {season} has no headers")
                
                # Check for required columns (case-insensitive)
                required_columns = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
                fieldnames_lower = [f.lower() for f in fieldnames]
                missing_columns = []
                for req_col in required_columns:
                    if req_col.lower() not in fieldnames_lower:
                        missing_columns.append(req_col)
                
                if missing_columns:
                    error_msg = f"CSV file for {league_code} {season} missing required columns: {missing_columns}. Available columns: {fieldnames[:10]}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    raise ValueError(error_msg)
                
            except csv.Error as e:
                error_msg = f"CSV parsing error for {league_code} {season}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                raise ValueError(error_msg)
            
            row_num = 0
            for row in reader:
                row_num += 1
                stats["processed"] += 1
                
                try:
                    # Parse date - try multiple column name variations
                    date_str = row.get('Date', '') or row.get('date', '') or row.get('DATE', '')
                    match_date = self._parse_date(date_str)
                    if not match_date:
                        stats["skipped"] += 1
                        if row_num <= 5:  # Log first few skipped rows for debugging
                            errors.append(f"Row {row_num}: Invalid date '{date_str}'")
                        continue
                    
                    # Get teams - try multiple column name variations
                    home_team_name = (row.get('HomeTeam', '') or row.get('homeTeam', '') or 
                                     row.get('HOMETEAM', '') or row.get('Home', '')).strip()
                    away_team_name = (row.get('AwayTeam', '') or row.get('awayTeam', '') or 
                                     row.get('AWAYTEAM', '') or row.get('Away', '')).strip()
                    
                    if not home_team_name or not away_team_name:
                        stats["skipped"] += 1
                        if row_num <= 5:  # Log first few skipped rows for debugging
                            errors.append(f"Row {row_num}: Missing team names (Home: '{home_team_name}', Away: '{away_team_name}')")
                        continue
                    
                    # Try to resolve teams, create if they don't exist
                    from app.services.team_resolver import resolve_team_safe, create_team_if_not_exists
                    
                    home_team = resolve_team_safe(self.db, home_team_name, league.id)
                    if not home_team:
                        try:
                            home_team = create_team_if_not_exists(self.db, home_team_name, league.id)
                        except Exception as e:
                            stats["skipped"] += 1
                            errors.append(f"Failed to create home team {home_team_name}: {e}")
                            continue
                    
                    away_team = resolve_team_safe(self.db, away_team_name, league.id)
                    if not away_team:
                        try:
                            away_team = create_team_if_not_exists(self.db, away_team_name, league.id)
                        except Exception as e:
                            stats["skipped"] += 1
                            errors.append(f"Failed to create away team {away_team_name}: {e}")
                        continue
                    
                    # Parse scores - try multiple column name variations
                    home_goals = (self._parse_int(row.get('FTHG', '')) or 
                                 self._parse_int(row.get('fthg', '')) or
                                 self._parse_int(row.get('HomeGoals', '')) or
                                 self._parse_int(row.get('HG', '')))
                    away_goals = (self._parse_int(row.get('FTAG', '')) or 
                                 self._parse_int(row.get('ftag', '')) or
                                 self._parse_int(row.get('AwayGoals', '')) or
                                 self._parse_int(row.get('AG', '')))
                    
                    if home_goals is None or away_goals is None:
                        stats["skipped"] += 1
                        if row_num <= 5:  # Log first few skipped rows for debugging
                            errors.append(f"Row {row_num}: Missing goals (Home: {row.get('FTHG', 'N/A')}, Away: {row.get('FTAG', 'N/A')})")
                        continue
                    
                    # Parse half-time scores (if available) - try multiple column name variations
                    ht_home_goals = (self._parse_int(row.get('HTHG', '')) or 
                                    self._parse_int(row.get('hthg', '')) or
                                    self._parse_int(row.get('HTHomeGoals', '')) or
                                    self._parse_int(row.get('HT_HG', '')))
                    ht_away_goals = (self._parse_int(row.get('HTAG', '')) or 
                                    self._parse_int(row.get('htag', '')) or
                                    self._parse_int(row.get('HTAwayGoals', '')) or
                                    self._parse_int(row.get('HT_AG', '')))
                    # Ensure both are NULL together (constraint requirement)
                    if ht_home_goals is None or ht_away_goals is None:
                        ht_home_goals = None
                        ht_away_goals = None
                    
                    # Parse match metadata (if available)
                    match_time_str = row.get('Time', '').strip() or None
                    match_time = None
                    if match_time_str:
                        # Convert string to time object (e.g., '15:00' -> time(15, 0))
                        try:
                            # Try HH:MM format
                            if ':' in match_time_str:
                                parts = match_time_str.split(':')
                                if len(parts) >= 2:
                                    hour = int(parts[0])
                                    minute = int(parts[1])
                                    match_time = time(hour, minute)
                            # Try HH.MM format (e.g., '15.00')
                            elif '.' in match_time_str:
                                parts = match_time_str.split('.')
                                if len(parts) >= 2:
                                    hour = int(parts[0])
                                    minute = int(parts[1])
                                    match_time = time(hour, minute)
                        except (ValueError, IndexError):
                            # If parsing fails, leave as None
                            match_time = None
                    
                    venue = row.get('Venue', '').strip() or None
                    matchday = self._parse_int(row.get('Matchday', ''))
                    round_name = row.get('Round', '').strip() or None
                    
                    # Parse cards and penalties (if available)
                    hy = self._parse_int(row.get('HY', ''))
                    ay = self._parse_int(row.get('AY', ''))
                    hr = self._parse_int(row.get('HR', ''))
                    ar = self._parse_int(row.get('AR', ''))
                    home_penalties = self._parse_int(row.get('HP', '')) or self._parse_int(row.get('HomePenalties', ''))
                    away_penalties = self._parse_int(row.get('AP', '')) or self._parse_int(row.get('AwayPenalties', ''))
                    referee_id = self._parse_int(row.get('RefereeID', '')) or self._parse_int(row.get('Referee', ''))
                    
                    # Determine result
                    if home_goals > away_goals:
                        result = MatchResult.H
                    elif home_goals < away_goals:
                        result = MatchResult.A
                    else:
                        result = MatchResult.D
                    
                    # Parse odds - try multiple column name variations
                    # Common variations: AvgH/AvgD/AvgA, B365H/B365D/B365A, MaxH/MaxD/MaxA
                    odds_home = (self._parse_float(row.get('AvgH', '')) or 
                                self._parse_float(row.get('B365H', '')) or
                                self._parse_float(row.get('MaxH', '')) or
                                self._parse_float(row.get('avgH', '')) or
                                self._parse_float(row.get('b365H', '')))
                    odds_draw = (self._parse_float(row.get('AvgD', '')) or 
                                self._parse_float(row.get('B365D', '')) or
                                self._parse_float(row.get('MaxD', '')) or
                                self._parse_float(row.get('avgD', '')) or
                                self._parse_float(row.get('b365D', '')))
                    odds_away = (self._parse_float(row.get('AvgA', '')) or 
                                self._parse_float(row.get('B365A', '')) or
                                self._parse_float(row.get('MaxA', '')) or
                                self._parse_float(row.get('avgA', '')) or
                                self._parse_float(row.get('b365A', '')))
                    
                    # Calculate market probabilities
                    prob_home_market = None
                    prob_draw_market = None
                    prob_away_market = None
                    
                    if odds_home and odds_draw and odds_away:
                        total = 1/odds_home + 1/odds_draw + 1/odds_away
                        prob_home_market = (1/odds_home) / total
                        prob_draw_market = (1/odds_draw) / total
                        prob_away_market = (1/odds_away) / total
                    
                    # Check if match already exists
                    existing_match = self.db.query(Match).filter(
                        Match.home_team_id == home_team.id,
                        Match.away_team_id == away_team.id,
                        Match.match_date == match_date
                    ).first()
                    
                    if existing_match:
                        # Update existing match
                        existing_match.home_goals = home_goals
                        existing_match.away_goals = away_goals
                        existing_match.result = result
                        existing_match.odds_home = odds_home
                        existing_match.odds_draw = odds_draw
                        existing_match.odds_away = odds_away
                        existing_match.prob_home_market = prob_home_market
                        existing_match.prob_draw_market = prob_draw_market
                        existing_match.prob_away_market = prob_away_market
                        
                        # Update new columns if provided
                        if ht_home_goals is not None and ht_away_goals is not None:
                            existing_match.ht_home_goals = ht_home_goals
                            existing_match.ht_away_goals = ht_away_goals
                        if match_time:
                            existing_match.match_time = match_time
                        if venue:
                            existing_match.venue = venue
                        if matchday:
                            existing_match.matchday = matchday
                        if round_name:
                            existing_match.round_name = round_name
                        if hy is not None:
                            existing_match.hy = hy
                        if ay is not None:
                            existing_match.ay = ay
                        if hr is not None:
                            existing_match.hr = hr
                        if ar is not None:
                            existing_match.ar = ar
                        if home_penalties is not None:
                            existing_match.home_penalties = home_penalties
                        if away_penalties is not None:
                            existing_match.away_penalties = away_penalties
                        if referee_id is not None:
                            existing_match.referee_id = referee_id
                        
                        stats["updated"] += 1
                    else:
                        # Create new match
                        match = Match(
                            league_id=league.id,
                            season=season,
                            match_date=match_date,
                            home_team_id=home_team.id,
                            away_team_id=away_team.id,
                            home_goals=home_goals,
                            away_goals=away_goals,
                            result=result,
                            odds_home=odds_home,
                            odds_draw=odds_draw,
                            odds_away=odds_away,
                            prob_home_market=prob_home_market,
                            prob_draw_market=prob_draw_market,
                            prob_away_market=prob_away_market,
                            source=source_name,
                            ingestion_batch_id=str(batch_number) if batch_number else None,
                            # New columns
                            ht_home_goals=ht_home_goals,
                            ht_away_goals=ht_away_goals,
                            match_time=match_time,
                            venue=venue,
                            matchday=matchday,
                            round_name=round_name,
                            # Cards and penalties
                            hy=hy,
                            ay=ay,
                            hr=hr,
                            ar=ar,
                            home_penalties=home_penalties,
                            away_penalties=away_penalties,
                            referee_id=referee_id
                        )
                        self.db.add(match)
                        stats["inserted"] += 1
                    
                    # Commit periodically
                    if stats["processed"] % 100 == 0:
                        self.db.commit()
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = f"Row {row_num} ({league_code} {season}): {str(e)}"
                    errors.append(error_msg)
                    # Only log first 10 errors to avoid spam
                    if len(errors) <= 10:
                        logger.error(f"Error processing row {row_num}: {e}", exc_info=False)
                    # Rollback the failed transaction
                    try:
                        self.db.rollback()
                    except Exception:
                        pass  # Ignore rollback errors
                    continue
            
            # Final commit
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"Error committing matches: {commit_error}", exc_info=True)
                self.db.rollback()
                raise
            
            # Update ingestion log (only if it exists)
            if ingestion_log:
                # Accumulate stats if this is part of a larger batch
                ingestion_log.status = "completed"
                ingestion_log.completed_at = datetime.now()
                ingestion_log.records_processed = (ingestion_log.records_processed or 0) + stats["processed"]
                ingestion_log.records_inserted = (ingestion_log.records_inserted or 0) + stats["inserted"]
                ingestion_log.records_updated = (ingestion_log.records_updated or 0) + stats["updated"]
                ingestion_log.records_skipped = (ingestion_log.records_skipped or 0) + stats["skipped"]
                
                # Append to existing logs or create new
                existing_logs = ingestion_log.logs or {}
                existing_errors = existing_logs.get("errors", [])
                existing_errors.extend(errors[:50])
                
                # Track all leagues/seasons in this batch
                batch_files = existing_logs.get("files", [])
                batch_files.append({
                    "league_code": league_code,
                    "season": season,
                    "processed": int(stats["processed"]),
                    "inserted": int(stats["inserted"]),
                    "updated": int(stats["updated"])
                })
                
                ingestion_log.error_message = "\n".join(existing_errors[:10]) if existing_errors else None
                ingestion_log.logs = {
                    "errors": existing_errors[:50],
                    "batch_number": batch_number,
                    "files": batch_files,
                    "download_session_folder": download_session_folder  # Store for file matching
                }
            
            # Update data source
            data_source.status = "fresh"
            data_source.last_sync_at = datetime.now()
            data_source.record_count = stats["inserted"] + stats["updated"]
            
            # Add cleaning stats to ingestion log if available
            if cleaning_stats and ingestion_log:
                existing_logs = ingestion_log.logs or {}
                # Convert numpy/pandas types to native Python types for JSON serialization
                existing_logs["cleaning_stats"] = {
                    "columns_dropped": list(cleaning_stats.get("columns_dropped", [])),
                    "rows_before": int(cleaning_stats.get("rows_before", 0)),
                    "rows_after": int(cleaning_stats.get("rows_after", 0)),
                    "rows_removed": int(cleaning_stats.get("rows_removed", 0)),
                    "invalid_dates_removed": int(cleaning_stats.get("invalid_dates_removed", 0)),
                    "missing_critical_removed": int(cleaning_stats.get("missing_critical_removed", 0)),
                    "values_imputed": int(cleaning_stats.get("values_imputed", 0)),
                    "features_created": list(cleaning_stats.get("features_created", []))
                }
                ingestion_log.logs = existing_logs
            
            self.db.commit()
            
            # Add batch number and cleaning stats to stats
            stats["batch_number"] = batch_number
            if ingestion_log:
                stats["ingestion_log_id"] = ingestion_log.id
            if cleaning_stats:
                stats["cleaning"] = {
                    "columns_dropped": int(len(cleaning_stats.get("columns_dropped", []))),
                    "rows_removed": int(cleaning_stats.get("rows_removed", 0))
                }
            
            return stats
        
        except Exception as e:
            if ingestion_log:
                ingestion_log.status = "failed"
                ingestion_log.completed_at = datetime.now()
                ingestion_log.error_message = str(e)
                self.db.commit()
            raise
    
    def download_from_football_data(
        self,
        league_code: str,
        season: str
    ) -> str:
        """
        Download CSV from football-data.co.uk
        
        Args:
            league_code: League code (e.g., 'E0' for Premier League)
            season: Season code (e.g., '2324' for 2023-24)
        
        Returns:
            CSV content as string (UTF-8 encoded)
        """
        # Extra Leagues (available from 2012/13 onwards) use same URL structure
        # But some leagues may not exist at all - try standard URL first
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
        
        try:
            # Use SSL verification setting from config (default to True if not set)
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            
            # Try to detect encoding from response headers or content
            # football-data.co.uk CSVs are often latin-1 encoded
            encoding = response.encoding or 'utf-8'
            
            # Try to decode with detected encoding first
            try:
                content = response.content.decode(encoding).strip()
            except (UnicodeDecodeError, LookupError):
                # Fallback to common encodings
                for fallback_encoding in ['latin-1', 'windows-1252', 'iso-8859-1', 'utf-8']:
                    try:
                        content = response.content.decode(fallback_encoding).strip()
                        logger.debug(f"Successfully decoded {league_code} {season} using {fallback_encoding} encoding")
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    # If all encodings fail, use errors='replace' to handle bad characters
                    content = response.content.decode('utf-8', errors='replace').strip()
                    logger.warning(f"Used UTF-8 with error replacement for {league_code} {season}")
            
            if not content:
                raise ValueError(f"Empty response from {url}")
            
            # Check if response is HTML (error page)
            if content.startswith('<!DOCTYPE') or content.startswith('<html') or content.startswith('<HTML'):
                raise ValueError(f"Received HTML error page instead of CSV from {url}. The file may not exist for this league/season.")
            
            # Check content-type if available
            content_type = response.headers.get('Content-Type', '').lower()
            if 'html' in content_type and 'csv' not in content_type:
                raise ValueError(f"Received HTML content instead of CSV from {url}")
            
            return content
        except requests.RequestException as e:
            # Try alternative URL pattern for Extra Leagues (if different structure exists)
            # Some Extra Leagues might use country-specific paths
            error_msg = str(e)
            if "404" in error_msg or "Not Found" in error_msg:
                # Try alternative URL patterns for Extra Leagues
                # Note: Most Extra Leagues use the same pattern, but some may not exist
                logger.debug(f"404 for {league_code} season {season}, trying alternative patterns...")
                
                # Alternative pattern 1: Direct country path (if exists)
                # This is a fallback - most Extra Leagues use the standard pattern
                alt_urls = [
                    f"https://www.football-data.co.uk/{league_code.lower()}{season}.csv",
                    f"https://www.football-data.co.uk/{season}/{league_code.lower()}.csv",
                ]
                
                for alt_url in alt_urls:
                    try:
                        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
                        alt_response = requests.get(alt_url, timeout=30, verify=verify_ssl)
                        if alt_response.status_code == 200:
                            content = alt_response.text.strip()
                            # Validate it's CSV, not HTML
                            if content and not (content.startswith('<!DOCTYPE') or content.startswith('<html') or content.startswith('<HTML')):
                                logger.info(f"Found data at alternative URL: {alt_url}")
                                return content
                    except requests.RequestException:
                        continue
            
            logger.error(f"Failed to download from {url}: {e}")
            raise
    
    def get_data_source_for_league(self, league_code: str) -> str:
        """
        Determine which data source to use for a league
        
        Returns:
            'football-data.co.uk' or 'football-data.org'
        """
        if league_code in self.FOOTBALL_DATA_ORG_LEAGUES:
            return 'football-data.org'
        return 'football-data.co.uk'
    
    def ingest_from_football_data(
        self,
        league_code: str,
        season: str,
        batch_number: Optional[int] = None,
        save_csv: bool = True,
        download_session_folder: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Download and ingest data from football-data.co.uk or football-data.org
        
        Automatically routes to the correct source based on league availability.
        
        Args:
            league_code: League code (e.g., 'E0' for Premier League)
            season: Season code (e.g., '2324' for 2023-24), 'all'/'last7' for 7 seasons, or 'last10' for 10 seasons
            batch_number: Optional batch number (uses ingestion_log.id if not provided)
            save_csv: Whether to save CSV files to disk
            download_session_folder: Optional download session folder name (format: {Date}_{Seasons}_{Leagues})
        
        Returns:
            Dict with ingestion statistics including batch_number
        """
        # Determine data source
        data_source = self.get_data_source_for_league(league_code)
        
        if data_source == 'football-data.org':
            # Use Football-Data.org API
            return self.ingest_from_football_data_org(
                league_code=league_code,
                season=season,
                batch_number=batch_number
            )
        else:
            # Use football-data.co.uk CSV
            # Handle multi-season options
            if season == "all" or season == "last7":
                return self.ingest_all_seasons(league_code, batch_number, save_csv, max_years=7, download_session_folder=download_session_folder)
            elif season == "last10":
                return self.ingest_all_seasons(league_code, batch_number, save_csv, max_years=10, download_session_folder=download_session_folder)
            
            csv_content = self.download_from_football_data(league_code, season)
            return self.ingest_csv(csv_content, league_code, season, batch_number=batch_number, save_csv=save_csv, download_session_folder=download_session_folder)
    
    def ingest_from_football_data_org(
        self,
        league_code: str,
        season: str,
        batch_number: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Ingest data from Football-Data.org API
        
        Args:
            league_code: League code (e.g., 'SWE1')
            season: Season code (e.g., '2324' for 2023-24) or 'all'/'last7'/'last10'
            batch_number: Optional batch number
        
        Returns:
            Dict with ingestion statistics
        """
        from app.services.ingestion.ingest_football_data_org import FootballDataOrgService
        from app.db.models import DataSource, IngestionLog
        
        # Create or get data source
        data_source = self.db.query(DataSource).filter(
            DataSource.name == "football-data.org"
        ).first()
        
        if not data_source:
            data_source = DataSource(
                name="football-data.org",
                source_type="api",
                status="running"
            )
            self.db.add(data_source)
            self.db.flush()
        
        # Create batch log if not provided
        if batch_number is None:
            batch_log = IngestionLog(
                source_id=data_source.id,
                status="running"
            )
            self.db.add(batch_log)
            self.db.flush()
            batch_number = batch_log.id
        
        # Initialize Football-Data.org service
        org_service = FootballDataOrgService(self.db)
        
        # Handle multi-season options
        if season == "all" or season == "last7":
            max_years = 7
        elif season == "last10":
            max_years = 10
        else:
            max_years = 1
        
        # Get seasons list (from 2012/13 onwards for these leagues)
        current_year = datetime.now().year
        current_month = datetime.now().month
        if current_month < 8:
            current_season_start = current_year - 1
        else:
            current_season_start = current_year
        
        # Generate seasons from 2012/13 onwards
        seasons = []
        for year in range(2012, current_season_start + 1):
            season_code = f"{str(year)[-2:]}{str(year + 1)[-2:]}"
            seasons.append(season_code)
        
        seasons.reverse()
        if len(seasons) > max_years:
            seasons = seasons[:max_years]
        
        # Aggregate stats
        total_stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "batch_number": batch_number
        }
        
        # Ingest each season
        for season_code in seasons:
            try:
                logger.info(f"Downloading {league_code} season {season_code} from Football-Data.org...")
                stats = org_service.ingest_league_matches(
                    league_code=league_code,
                    season=season_code,
                    batch_number=batch_number
                )
                
                total_stats["processed"] += stats["processed"]
                total_stats["inserted"] += stats["inserted"]
                total_stats["updated"] += stats["updated"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]
                
            except ValueError as e:
                # Handle subscription/access errors gracefully
                error_msg = str(e)
                if "403 Forbidden" in error_msg or "subscription" in error_msg.lower():
                    logger.warning(
                        f"Football-Data.org failed for {league_code} season {season_code}: {error_msg}. "
                        f"Trying OpenFootball as fallback..."
                    )
                    # Try OpenFootball as fallback
                    try:
                        from app.services.ingestion.ingest_openfootball import OpenFootballService
                        openfootball_service = OpenFootballService(self.db)
                        stats = openfootball_service.ingest_league_matches(
                            league_code=league_code,
                            season=season_code,
                            batch_number=batch_number
                        )
                        logger.info(f"Successfully ingested {league_code} season {season_code} from OpenFootball")
                        total_stats["processed"] += stats["processed"]
                        total_stats["inserted"] += stats["inserted"]
                        total_stats["updated"] += stats["updated"]
                        total_stats["skipped"] += stats["skipped"]
                        total_stats["errors"] += stats["errors"]
                    except Exception as of_error:
                        logger.warning(f"OpenFootball also failed for {league_code} season {season_code}: {of_error}")
                        total_stats["errors"] += 1
                else:
                    logger.error(f"Failed to ingest {league_code} season {season_code} from Football-Data.org: {e}")
                    total_stats["errors"] += 1
                continue
            except Exception as e:
                logger.error(f"Failed to ingest {league_code} season {season_code} from Football-Data.org: {e}", exc_info=True)
                # Try OpenFootball as fallback
                try:
                    from app.services.ingestion.ingest_openfootball import OpenFootballService
                    openfootball_service = OpenFootballService(self.db)
                    stats = openfootball_service.ingest_league_matches(
                        league_code=league_code,
                        season=season_code,
                        batch_number=batch_number
                    )
                    logger.info(f"Successfully ingested {league_code} season {season_code} from OpenFootball (fallback)")
                    total_stats["processed"] += stats["processed"]
                    total_stats["inserted"] += stats["inserted"]
                    total_stats["updated"] += stats["updated"]
                    total_stats["skipped"] += stats["skipped"]
                    total_stats["errors"] += stats["errors"]
                except Exception as of_error:
                    logger.error(f"Both Football-Data.org and OpenFootball failed for {league_code} season {season_code}: {of_error}")
                total_stats["errors"] += 1
                continue
        
        # Update batch log
        batch_log = self.db.query(IngestionLog).filter(IngestionLog.id == batch_number).first()
        if batch_log:
            batch_log.status = "completed"
            batch_log.completed_at = datetime.now()
            batch_log.records_processed = total_stats["processed"]
            batch_log.records_inserted = total_stats["inserted"]
            batch_log.records_updated = total_stats["updated"]
            batch_log.records_skipped = total_stats["skipped"]
            self.db.commit()
        
        return total_stats
    
    def ingest_all_seasons(
        self,
        league_code: str,
        batch_number: Optional[int] = None,
        save_csv: bool = True,
        max_years: int = MAX_YEARS_BACK,
        download_session_folder: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Ingest data for multiple seasons (default 7 years back, configurable)
        
        Args:
            league_code: League code
            batch_number: Optional batch number
            save_csv: Whether to save CSV files
            max_years: Number of years/seasons to download (default: 7)
        
        Returns:
            Aggregated stats across all seasons
        """
        # Create ONE batch for all seasons if not provided
        if batch_number is None:
            from app.db.models import DataSource, IngestionLog
            data_source = self.db.query(DataSource).filter(
                DataSource.name == "football-data.co.uk"
            ).first()
            
            if not data_source:
                data_source = DataSource(
                    name="football-data.co.uk",
                    source_type="csv",
                    status="running"
                )
                self.db.add(data_source)
                self.db.flush()
            
            batch_log = IngestionLog(
                source_id=data_source.id,
                status="running"
            )
            self.db.add(batch_log)
            self.db.flush()
            batch_number = batch_log.id
        
        # Extra Leagues are only available from 2012/13 season onwards
        # Define Extra Leagues that have limited historical data
        extra_leagues = {
            'ARG1', 'BRA1', 'MEX1', 'USA1', 'CHN1', 'JPN1',  # Americas & Asia
            'FIN1', 'RO1', 'RUS1', 'IRL1', 'SWE1'  # Some European leagues
        }
        
        # For Extra Leagues, only try seasons from 2012/13 onwards
        if league_code in extra_leagues:
            # Calculate seasons from 2012/13 to current
            current_year = datetime.now().year
            current_month = datetime.now().month
            # Season starts in August, so if we're before August, current season started last year
            if current_month < 8:
                current_season_start = current_year - 1
            else:
                current_season_start = current_year
            
            # Generate seasons from 2012/13 onwards
            extra_seasons = []
            for year in range(2012, current_season_start + 1):
                season_code = f"{str(year)[-2:]}{str(year + 1)[-2:]}"
                extra_seasons.append(season_code)
            
            # Reverse to get most recent first
            extra_seasons.reverse()
            
            # Limit to max_years if specified
            if max_years and len(extra_seasons) > max_years:
                extra_seasons = extra_seasons[:max_years]
            
            seasons = extra_seasons
            logger.info(f"Ingesting {len(seasons)} seasons for Extra League {league_code} (from 2012/13): {seasons} (batch #{batch_number})")
        else:
            seasons = get_seasons_list(max_years)
            logger.info(f"Ingesting {len(seasons)} seasons for league {league_code}: {seasons} (batch #{batch_number})")
        
        total_stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "seasons_processed": 0,
            "seasons_failed": 0,
            "season_details": []
        }
        
        for season_code in seasons:
            try:
                logger.info(f"Downloading {league_code} season {season_code}...")
                csv_content = self.download_from_football_data(league_code, season_code)
                stats = self.ingest_csv(
                    csv_content, 
                    league_code, 
                    season_code,
                    batch_number=batch_number,
                    save_csv=save_csv,
                    download_session_folder=download_session_folder
                )
                
                total_stats["processed"] += stats["processed"]
                total_stats["inserted"] += stats["inserted"]
                total_stats["updated"] += stats["updated"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]
                total_stats["seasons_processed"] += 1
                
                total_stats["season_details"].append({
                    "season": season_code,
                    "stats": stats
                })
                
                # Commit after each season to release database connection
                try:
                    self.db.commit()
                except Exception as commit_error:
                    logger.warning(f"Error committing after season {season_code}: {commit_error}")
                    self.db.rollback()
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to ingest season {season_code}: {error_msg}", exc_info=True)
                
                # Handle 404 errors gracefully (data not available for this league/season)
                is_404 = "404" in error_msg or "Not Found" in error_msg
                
                # Rollback any failed transaction
                try:
                    self.db.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                
                total_stats["seasons_failed"] += 1
                total_stats["season_details"].append({
                    "season": season_code,
                    "status": "failed",
                    "error": error_msg,
                    "is_404": is_404,  # Flag for 404 errors (data not available)
                    "league_code": league_code  # Include league code for logging
                })
                
                # Don't log 404s as critical errors - they're expected for some leagues/seasons
                if not is_404:
                    logger.warning(f"Non-404 error for {league_code} season {season_code}: {error_msg}")
                continue
        
        # Write download log for this league if download_session_folder is provided
        if download_session_folder and total_stats.get("seasons_processed", 0) > 0:
            try:
                # Collect CSV files saved
                csv_files_saved = []
                backend_root = Path(__file__).parent.parent.parent
                session_dir = backend_root / "data" / "1_data_ingestion" / "Historical Match_Odds_Data" / download_session_folder / league_code
                if session_dir.exists():
                    csv_files = list(session_dir.glob("*.csv"))
                    csv_files_saved = [f.name for f in csv_files]
                
                league_summary = {
                    "total_leagues": 1,
                    "successful": total_stats["seasons_processed"],
                    "failed": total_stats["seasons_failed"],
                    "total_processed": total_stats["processed"],
                    "total_inserted": total_stats["inserted"],
                    "total_updated": total_stats["updated"],
                    "total_skipped": total_stats["skipped"],
                    "total_errors": total_stats["errors"],
                    "csv_files_saved": csv_files_saved,
                    "successful_downloads": [
                        {
                            "league_code": league_code,
                            "season": detail.get("season"),
                            "stats": detail.get("stats", {})
                        }
                        for detail in total_stats["season_details"]
                        if detail.get("status") != "failed"
                    ],
                    "failed_downloads": [
                        {
                            "league_code": league_code,
                            "season": detail.get("season"),
                            "error": detail.get("error"),
                            "is_404": detail.get("is_404", False)
                        }
                        for detail in total_stats["season_details"]
                        if detail.get("status") == "failed"
                    ],
                    "missing_data": []
                }
                self._write_download_log(download_session_folder, league_summary)
            except Exception as log_error:
                logger.error(f"Failed to write league download log: {log_error}", exc_info=True)
        
        if batch_number:
            total_stats["batch_number"] = batch_number
        
        return total_stats
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Remove any extra whitespace or newlines
        date_str = date_str.replace('\n', '').replace('\r', '')
        
        # Try common formats (football-data.co.uk uses dd/mm/yyyy)
        formats = [
            "%d/%m/%Y",      # 19/11/2021 (most common)
            "%d/%m/%y",      # 19/11/21
            "%Y-%m-%d",      # 2021-11-19 (ISO format)
            "%d-%m-%Y",      # 19-11-2021
            "%d.%m.%Y",      # 19.11.2021
            "%m/%d/%Y",      # 11/19/2021 (US format - some leagues)
            "%Y/%m/%d",      # 2021/11/19
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                # Validate date is reasonable (not too far in past/future)
                current_year = datetime.now().year
                if 1900 <= parsed_date.year <= current_year + 1:
                    return parsed_date
            except (ValueError, TypeError):
                continue
        
        return None
    
    def _parse_int(self, value: str) -> Optional[int]:
        """Parse integer from string"""
        if not value:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float from string"""
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _save_csv_file(
        self,
        csv_content: str,
        league_code: str,
        season: str,
        batch_number: Optional[int],
        download_session_folder: Optional[str] = None
    ) -> Path:
        """
        Save CSV file to disk organized by download session and league code
        
        Structure: data/1_data_ingestion/Historical Match_Odds_Data/{DownloadDate}_Seasons_{No of Seasons}_Leagues_{no of leagues}/{league_code}/{league_code}_{season}.csv
        Example: data/1_data_ingestion/Historical Match_Odds_Data/2025-01-15_Seasons_10_Leagues_43/E0/E0_2425.csv
        
        All CSV files are saved to Historical Match_Odds_Data folder.
        If download_session_folder is None, creates a default session folder: {Date}_Seasons_1_Leagues_1
        """
        # Initialize league_dir to avoid UnboundLocalError
        league_dir = None
        
        # Get league from database first (needed for old structure)
        league = self.db.query(League).filter(
            League.code == league_code
        ).first()
        
        # Always use Historical Match_Odds_Data folder structure
        # If download_session_folder is not provided, create a default one
        backend_root = Path(__file__).parent.parent.parent  # Go up from app/services/data_ingestion.py to backend root
        
        if not download_session_folder:
            from datetime import datetime
            download_date = datetime.now().strftime("%Y-%m-%d")
            # Create a default session folder name
            download_session_folder = f"{download_date}_Seasons_1_Leagues_1"
        
        base_dir = backend_root / "data" / "1_data_ingestion" / "Historical Match_Odds_Data" / download_session_folder
        # Organize by league code (simple and clean)
        # Format: {league_code}
        league_dir = base_dir / league_code
        
        league_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{league_code}_{season}.csv"
        filepath = league_dir / filename
        
        # Write CSV content (overwrite if exists - same league/season combination)
        filepath.write_text(csv_content, encoding='utf-8')
        
        return filepath
    
    def _save_cleaned_csv_file(
        self,
        csv_content: str,
        league_code: str,
        season: str,
        download_session_folder: Optional[str] = None
    ) -> Path:
        """
        Save cleaned CSV file to 2_Cleaned_data/Historical Match_Odds_Data folder
        
        Structure: data/2_Cleaned_data/Historical Match_Odds_Data/{DownloadDate}_Seasons_{No of Seasons}_Leagues_{no of leagues}/{league_code}/{league_code}_{season}.csv
        Example: data/2_Cleaned_data/Historical Match_Odds_Data/2025-01-15_Seasons_10_Leagues_43/E0/E0_2425.csv
        
        If download_session_folder is None, saves to: data/2_Cleaned_data/Historical Match_Odds_Data/{league_code}/{league_code}_{season}.csv
        """
        # Resolve path relative to backend root (where this file is located)
        backend_root = Path(__file__).parent.parent.parent  # Go up from app/services/data_ingestion.py to backend root
        
        if download_session_folder:
            base_dir = backend_root / "data" / "2_Cleaned_data" / "Historical Match_Odds_Data" / download_session_folder
            league_dir = base_dir / league_code
        else:
            # Fallback structure
            base_dir = backend_root / "data" / "2_Cleaned_data" / "Historical Match_Odds_Data"
            league_dir = base_dir / league_code
        
        league_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{league_code}_{season}.csv"
        filepath = league_dir / filename
        
        # Write CSV content (overwrite if exists)
        filepath.write_text(csv_content, encoding='utf-8')
        
        logger.info(f"Saved cleaned CSV to: {filepath.absolute()}")
        
        return filepath
    
    def _write_download_log(
        self,
        download_session_folder: str,
        download_summary: Dict
    ) -> Path:
        """
        Write comprehensive download log to the download session folder AND 01_logs folder
        
        Args:
            download_session_folder: The session folder name
            download_summary: Dictionary containing download summary information
            
        Returns:
            Path to the log file in 01_logs folder
        """
        backend_root = Path(__file__).parent.parent.parent
        
        # Also write to 01_logs folder
        logs_dir = backend_root / "data" / "1_data_ingestion" / "Historical Match_Odds_Data" / "01_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        cleaned_logs_dir = backend_root / "data" / "2_Cleaned_data" / "Historical Match_Odds_Data" / "01_logs"
        cleaned_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Keep original log in session folder for backward compatibility
        base_dir = backend_root / "data" / "1_data_ingestion" / "Historical Match_Odds_Data" / download_session_folder
        base_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = base_dir / "DOWNLOAD_LOG.txt"
        
        # Also create log in 01_logs folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_file = logs_dir / f"Historical_Odds_{download_session_folder}_{timestamp}_LOG.txt"
        cleaned_logs_file = cleaned_logs_dir / f"Historical_Odds_{download_session_folder}_{timestamp}_LOG.txt"
        
        # Build comprehensive log content
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append("DOWNLOAD SESSION LOG")
        log_lines.append("=" * 80)
        log_lines.append(f"Session Folder: {download_session_folder}")
        log_lines.append(f"Download Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_lines.append("")
        
        # Summary section
        log_lines.append("SUMMARY")
        log_lines.append("-" * 80)
        log_lines.append(f"Total Leagues Attempted: {download_summary.get('total_leagues', 0)}")
        log_lines.append(f"Successful Downloads (with data): {download_summary.get('successful', 0)}")
        log_lines.append(f"Failed Downloads (errors): {download_summary.get('failed', 0)}")
        log_lines.append(f"No Data Available (all 404s): {download_summary.get('no_data', 0)}")
        log_lines.append(f"Total Records Processed: {download_summary.get('total_processed', 0):,}")
        log_lines.append(f"Total Records Inserted: {download_summary.get('total_inserted', 0):,}")
        log_lines.append(f"Total Records Updated: {download_summary.get('total_updated', 0):,}")
        log_lines.append(f"Total Records Skipped: {download_summary.get('total_skipped', 0):,}")
        log_lines.append(f"Total Errors: {download_summary.get('total_errors', 0)}")
        log_lines.append("")
        
        # Successful downloads
        successful = download_summary.get('successful_downloads', [])
        if successful:
            log_lines.append("SUCCESSFUL DOWNLOADS")
            log_lines.append("-" * 80)
            for item in successful:
                league_code = item.get('league_code', 'Unknown')
                season = item.get('season', 'Unknown')
                stats = item.get('stats', {})
                batch_num = item.get('batch_number', 'N/A')
                
                log_lines.append(f"✓ {league_code} - Season: {season} (Batch #{batch_num})")
                log_lines.append(f"  Records: {stats.get('processed', 0):,} processed, "
                               f"{stats.get('inserted', 0):,} inserted, "
                               f"{stats.get('updated', 0):,} updated, "
                               f"{stats.get('skipped', 0):,} skipped")
                if stats.get('errors', 0) > 0:
                    log_lines.append(f"  ⚠ Warnings: {stats.get('errors', 0)} errors encountered")
                log_lines.append("")
        
        # No data downloads (completed but 0 records - all 404s)
        no_data = download_summary.get('no_data_downloads', [])
        if no_data:
            log_lines.append("NO DATA AVAILABLE (All seasons returned 404)")
            log_lines.append("-" * 80)
            for item in no_data:
                league_code = item.get('league_code', 'Unknown')
                season = item.get('season', 'Unknown')
                reason = item.get('reason', 'No data available')
                batch_num = item.get('batch_number', 'N/A')
                
                log_lines.append(f"⊘ {league_code} - Season: {season} (Batch #{batch_num})")
                log_lines.append(f"  Reason: {reason}")
                log_lines.append("")
        
        # Failed downloads (exceptions/errors)
        failed = download_summary.get('failed_downloads', [])
        if failed:
            log_lines.append("FAILED DOWNLOADS (Errors)")
            log_lines.append("-" * 80)
            for item in failed:
                league_code = item.get('league_code', 'Unknown')
                season = item.get('season', 'Unknown')
                error = item.get('error', 'Unknown error')
                is_404 = item.get('is_404', False)
                
                status = "⚠ Data Not Available (404)" if is_404 else "✗ ERROR"
                log_lines.append(f"{status} {league_code} - Season: {season}")
                log_lines.append(f"  Error: {error}")
                log_lines.append("")
        
        # Missing data (expected but not found)
        missing = download_summary.get('missing_data', [])
        if missing:
            log_lines.append("MISSING DATA (Expected but not available)")
            log_lines.append("-" * 80)
            for item in missing:
                league_code = item.get('league_code', 'Unknown')
                season = item.get('season', 'Unknown')
                reason = item.get('reason', 'Not specified')
                log_lines.append(f"⊘ {league_code} - Season: {season}")
                log_lines.append(f"  Reason: {reason}")
                log_lines.append("")
        
        # File structure
        log_lines.append("FILE STRUCTURE")
        log_lines.append("-" * 80)
        log_lines.append(f"Base Directory: {base_dir}")
        log_lines.append("")
        log_lines.append("Files are organized by league code:")
        log_lines.append("  {session_folder}/{league_code}/{league_code}_{season}.csv")
        log_lines.append("")
        
        # CSV files saved section
        csv_files_saved = download_summary.get('csv_files_saved', [])
        if csv_files_saved:
            log_lines.append("CSV FILES SAVED")
            log_lines.append("-" * 80)
            for csv_file in csv_files_saved[:30]:  # Limit to first 30 files
                log_lines.append(f"  ✓ {csv_file}")
            if len(csv_files_saved) > 30:
                log_lines.append(f"  ... and {len(csv_files_saved) - 30} more files")
        log_lines.append("")
        
        # Check actual files on disk
        if base_dir.exists():
            league_folders = sorted([d for d in base_dir.iterdir() if d.is_dir() and d.name != "01_logs"])
            if league_folders:
                log_lines.append("Downloaded Files:")
                for league_folder in league_folders:
                    csv_files = sorted(league_folder.glob("*.csv"))
                    if csv_files:
                        log_lines.append(f"  {league_folder.name}/ ({len(csv_files)} files)")
                        for csv_file in csv_files[:10]:  # Show first 10 files
                            log_lines.append(f"    - {csv_file.name}")
                        if len(csv_files) > 10:
                            log_lines.append(f"    ... and {len(csv_files) - 10} more files")
                    else:
                        log_lines.append(f"  {league_folder.name}/ (empty)")
        
        log_lines.append("")
        log_lines.append("=" * 80)
        log_lines.append("END OF LOG")
        log_lines.append("=" * 80)
        
        # Write log file to multiple locations
        log_content = "\n".join(log_lines)
        
        # Write to session folder (original location)
        log_file.write_text(log_content, encoding='utf-8')
        logger.info(f"Download log written to: {log_file}")
        
        # Write to 01_logs folder (new location)
        logs_file.write_text(log_content, encoding='utf-8')
        logger.info(f"Download log written to: {logs_file}")
        
        # Write to cleaned data 01_logs folder
        cleaned_logs_file.write_text(log_content, encoding='utf-8')
        logger.info(f"Download log written to: {cleaned_logs_file}")
        
        return logs_file  # Return the 01_logs path as primary


def create_default_leagues(db: Session) -> None:
    """Create default leagues if they don't exist"""
    default_leagues = [
        {"code": "EPL", "name": "Premier League", "country": "England", "tier": 1},
        {"code": "LaLiga", "name": "La Liga", "country": "Spain", "tier": 1},
        {"code": "Bundesliga", "name": "Bundesliga", "country": "Germany", "tier": 1},
        {"code": "SerieA", "name": "Serie A", "country": "Italy", "tier": 1},
        {"code": "Ligue1", "name": "Ligue 1", "country": "France", "tier": 1},
        {"code": "Eredivisie", "name": "Eredivisie", "country": "Netherlands", "tier": 1},
    ]
    
    for league_data in default_leagues:
        existing = db.query(League).filter(
            League.code == league_data["code"]
        ).first()
        
        if not existing:
            league = League(**league_data)
            db.add(league)
    
    db.commit()

