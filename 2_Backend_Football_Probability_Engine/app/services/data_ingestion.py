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
import logging
from app.db.models import (
    League, Team, Match, DataSource, IngestionLog, MatchResult
)
from app.services.team_resolver import resolve_team_safe, normalize_team_name

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Service for ingesting match data from various sources"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def ingest_csv(
        self,
        csv_content: str,
        league_code: str,
        season: str,
        source_name: str = "football-data.co.uk"
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
        
        # Create ingestion log
        ingestion_log = IngestionLog(
            source_id=data_source.id,
            status="running"
        )
        self.db.add(ingestion_log)
        self.db.flush()
        
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
                    continue
            
            # Final commit
            self.db.commit()
            
            # Update ingestion log
            ingestion_log.status = "completed"
            ingestion_log.completed_at = datetime.now()
            ingestion_log.records_processed = stats["processed"]
            ingestion_log.records_inserted = stats["inserted"]
            ingestion_log.records_updated = stats["updated"]
            ingestion_log.records_skipped = stats["skipped"]
            ingestion_log.error_message = "\n".join(errors[:10]) if errors else None
            ingestion_log.logs = {"errors": errors[:50]}  # Store first 50 errors
            
            # Update data source
            data_source.status = "fresh"
            data_source.last_sync_at = datetime.now()
            data_source.record_count = stats["inserted"] + stats["updated"]
            
            self.db.commit()
            
            return stats
        
        except Exception as e:
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
        season: str
    ) -> Dict[str, int]:
        """
        Download and ingest data from football-data.co.uk
        
        Returns:
            Dict with ingestion statistics
        """
        csv_content = self.download_from_football_data(league_code, season)
        return self.ingest_csv(csv_content, league_code, season)
    
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

