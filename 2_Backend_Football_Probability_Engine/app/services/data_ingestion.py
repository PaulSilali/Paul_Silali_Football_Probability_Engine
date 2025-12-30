"""
Data Ingestion Service

Handles importing match data from various sources
"""
import csv
import io
import requests
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path
import logging
from app.db.models import (
    League, Team, Match, DataSource, IngestionLog, MatchResult
)
from app.services.team_resolver import resolve_team_safe, normalize_team_name
from app.services.data_cleaning import DataCleaningService

logger = logging.getLogger(__name__)

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
        save_csv: bool = True
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
        
        # Apply data cleaning (before saving and parsing)
        cleaning_stats = None
        if self.enable_cleaning and self.cleaning_service:
            try:
                # Use Phase 2 (includes Phase 1) for enhanced features
                from app.config import settings
                cleaning_phase = getattr(settings, 'DATA_CLEANING_PHASE', 'phase1')  # Default to phase1
                
                logger.info(f"Applying data cleaning (phase: {cleaning_phase})...")
                csv_content, cleaning_stats = self.cleaning_service.clean_csv_content(
                    csv_content,
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
        
        # Save CSV file if requested (save cleaned version)
        if save_csv:
            try:
                csv_path = self._save_csv_file(
                    csv_content, 
                    league_code, 
                    season, 
                    batch_number
                )
                logger.info(f"CSV saved to: {csv_path}")
            except Exception as e:
                logger.warning(f"Failed to save CSV file: {e}")
        
        # Get league
        league = self.db.query(League).filter(
            League.code == league_code
        ).first()
        
        if not league:
            raise ValueError(f"League not found: {league_code}")
        
        stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        errors = []
        
        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                stats["processed"] += 1
                
                try:
                    # Parse date
                    match_date = self._parse_date(row.get('Date', ''))
                    if not match_date:
                        stats["skipped"] += 1
                        continue
                    
                    # Get teams
                    home_team_name = row.get('HomeTeam', '').strip()
                    away_team_name = row.get('AwayTeam', '').strip()
                    
                    if not home_team_name or not away_team_name:
                        stats["skipped"] += 1
                        continue
                    
                    home_team = resolve_team_safe(self.db, home_team_name, league.id)
                    away_team = resolve_team_safe(self.db, away_team_name, league.id)
                    
                    if not home_team or not away_team:
                        stats["skipped"] += 1
                        errors.append(f"Teams not found: {home_team_name} vs {away_team_name}")
                        continue
                    
                    # Parse scores
                    home_goals = self._parse_int(row.get('FTHG', ''))
                    away_goals = self._parse_int(row.get('FTAG', ''))
                    
                    if home_goals is None or away_goals is None:
                        stats["skipped"] += 1
                        continue
                    
                    # Determine result
                    if home_goals > away_goals:
                        result = MatchResult.H
                    elif home_goals < away_goals:
                        result = MatchResult.A
                    else:
                        result = MatchResult.D
                    
                    # Parse odds
                    odds_home = self._parse_float(row.get('AvgH', ''))
                    odds_draw = self._parse_float(row.get('AvgD', ''))
                    odds_away = self._parse_float(row.get('AvgA', ''))
                    
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
                            source=source_name
                        )
                        self.db.add(match)
                        stats["inserted"] += 1
                    
                    # Commit periodically
                    if stats["processed"] % 100 == 0:
                        self.db.commit()
                
                except Exception as e:
                    stats["errors"] += 1
                    errors.append(f"Row {stats['processed']}: {str(e)}")
                    logger.error(f"Error processing row: {e}")
                    # Rollback the failed transaction
                    self.db.rollback()
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
                    "files": batch_files
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
            CSV content as string
        """
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to download from {url}: {e}")
            raise
    
    def ingest_from_football_data(
        self,
        league_code: str,
        season: str,
        batch_number: Optional[int] = None,
        save_csv: bool = True
    ) -> Dict[str, int]:
        """
        Download and ingest data from football-data.co.uk
        
        Args:
            league_code: League code (e.g., 'E0' for Premier League)
            season: Season code (e.g., '2324' for 2023-24), 'all'/'last7' for 7 seasons, or 'last10' for 10 seasons
            batch_number: Optional batch number (uses ingestion_log.id if not provided)
            save_csv: Whether to save CSV files to disk
        
        Returns:
            Dict with ingestion statistics including batch_number
        """
        # Handle multi-season options
        if season == "all" or season == "last7":
            return self.ingest_all_seasons(league_code, batch_number, save_csv, max_years=7)
        elif season == "last10":
            return self.ingest_all_seasons(league_code, batch_number, save_csv, max_years=10)
        
        csv_content = self.download_from_football_data(league_code, season)
        return self.ingest_csv(csv_content, league_code, season, batch_number=batch_number, save_csv=save_csv)
    
    def ingest_all_seasons(
        self,
        league_code: str,
        batch_number: Optional[int] = None,
        save_csv: bool = True,
        max_years: int = MAX_YEARS_BACK
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
                    save_csv=save_csv
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
                    "is_404": is_404  # Flag for 404 errors (data not available)
                })
                
                # Don't log 404s as critical errors - they're expected for some leagues/seasons
                if not is_404:
                    logger.warning(f"Non-404 error for {league_code} season {season_code}: {error_msg}")
                continue
        
        if batch_number:
            total_stats["batch_number"] = batch_number
        
        return total_stats
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try common formats
        formats = [
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d.%m.%Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
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
        batch_number: int
    ) -> Path:
        """
        Save CSV file to disk organized by batch number and league name
        
        Structure: data/1_data_ingestion/batch_{N}_{League_Name}/{league_code}_{season}.csv
        Example: data/1_data_ingestion/batch_100_Premier_League/E0_2425.csv
        """
        # Get league name from database
        league = self.db.query(League).filter(
            League.code == league_code
        ).first()
        
        # Create safe folder name from league name
        if league:
            # Replace spaces and special chars with underscores, remove invalid chars
            league_name_safe = league.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            league_name_safe = ''.join(c for c in league_name_safe if c.isalnum() or c in ('_', '-'))
            batch_folder_name = f"batch_{batch_number}_{league_name_safe}"
        else:
            # Fallback if league not found
            batch_folder_name = f"batch_{batch_number}_{league_code}"
        
        # Create batch directory
        base_dir = Path("data/1_data_ingestion")
        batch_dir = base_dir / batch_folder_name
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{league_code}_{season}.csv"
        filepath = batch_dir / filename
        
        # Write CSV content
        filepath.write_text(csv_content, encoding='utf-8')
        
        return filepath


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

