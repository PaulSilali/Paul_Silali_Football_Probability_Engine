"""
Ingest match data from OpenFootball project (GitHub repositories)

OpenFootball provides free, open public domain football data in Football.TXT format.
This service handles leagues that are not available on football-data.co.uk or Football-Data.org API.

Repositories:
- world: https://github.com/openfootball/world (North America, Asia, Africa, Australia)
- europe: https://github.com/openfootball/europe (European leagues)
- south-america: https://github.com/openfootball/south-america (South American leagues)
"""
import requests
import re
import os
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import logging
import csv
import io
import urllib3

from app.db.models import League, Team, Match, DataSource, IngestionLog
from app.services.team_resolver import resolve_team_safe
from app.config import settings

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
# Use getattr with default True to handle cases where attribute might not exist yet
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Mapping of league codes to OpenFootball repository and path structure
# Format: (repository, country_folder, file_pattern, season_format, file_extension)
# Based on actual world-master structure analysis
LEAGUE_CODE_TO_OPENFOOTBALL = {
    # Europe - from europe repository
    'SWE1': ('europe', 'sweden', '1-allsvenskan', 'YYYY-YY', '.txt'),  # May not exist
    'FIN1': ('europe', 'finland', '1-veikkausliiga', 'YYYY-YY', '.txt'),  # May not exist
    'RO1': ('europe', 'romania', '1-liga', 'YYYY-YY', '.txt'),
    'RUS1': ('europe', 'russia', '1-premier', 'YYYY-YY', '.txt'),
    'IRL1': ('europe', 'ireland', '1-premier', 'YYYY-YY', '.txt'),
    'CZE1': ('europe', 'czech-republic', '1-liga', 'YYYY-YY', '.txt'),
    'CRO1': ('europe', 'croatia', '1-hnl', 'YYYY-YY', '.txt'),
    'SRB1': ('europe', 'serbia', '1-superliga', 'YYYY-YY', '.txt'),
    'UKR1': ('europe', 'ukraine', '1-premier', 'YYYY-YY', '.txt'),
    
    # Americas - from world repository (ACTUAL STRUCTURE)
    'ARG1': ('south-america', 'argentina', '1-primera', 'YYYY-YY', '.txt'),
    'BRA1': ('south-america', 'brazil', '1-serie-a', 'YYYY-YY', '.txt'),
    'MEX1': ('world', 'north-america/mexico', 'mx1', 'YYYY-YY', '.txt'),  # Format: 2023-24_mx1.txt
    'USA1': ('world', 'north-america/major-league-soccer', 'mls', 'YYYY', '.txt'),  # Format: 2023_mls.txt
    
    # Asia & Oceania - from world repository (ACTUAL STRUCTURE)
    'CHN1': ('world', 'asia/china', 'cn1', 'YYYY', '.txt'),  # Format: 2023_cn1.txt
    'JPN1': ('world', 'asia/japan', 'jp1', 'YYYY', '.txt'),  # Format: 2023_jp1.txt
    'KOR1': ('world', 'south-korea', '1-k-league', 'YYYY-YY', '.txt'),  # Need to verify
    'AUS1': ('world', 'pacific/australia', 'au1', 'YYYY-YY', '.txt'),  # Format: 2023-24_au1.txt
}

# Base URL for OpenFootball raw content
OPENFOOTBALL_BASE_URL = "https://raw.githubusercontent.com/openfootball"


def get_openfootball_path(league_code: str) -> Optional[Tuple[str, str, str, str, str]]:
    """Get OpenFootball repository and path for a league code"""
    return LEAGUE_CODE_TO_OPENFOOTBALL.get(league_code)


def convert_season_code_to_openfootball(season_code: str, season_format: str = 'YYYY-YY') -> Tuple[str, str]:
    """
    Convert season code (e.g., '2324') to OpenFootball format
    
    Args:
        season_code: Season code like '2324' for 2023-24 season
        season_format: Format type - 'YYYY-YY' for season format, 'YYYY' for single year
    
    Returns:
        Tuple of (season_string, file_pattern) for OpenFootball
        - For 'YYYY-YY': ('2023-24', '2023-24_mx1.txt')
        - For 'YYYY': ('2023', '2023_mls.txt')
    """
    if len(season_code) == 4:
        year1 = 2000 + int(season_code[:2])
        year2 = int(season_code[2:])
        
        if season_format == 'YYYY':
            # Single year format (e.g., MLS, J-League, China)
            return (str(year1), f"{year1}_{{league_code}}.txt")
        else:
            # Season format (e.g., Liga MX, A-League)
            return (f"{year1}-{year2:02d}", f"{year1}-{year2:02d}_{{league_code}}.txt")
    
    return (season_code, f"{season_code}_{{league_code}}.txt")


def build_openfootball_url(repository: str, country: str, league_file: str, season: str) -> str:
    """
    Build OpenFootball raw GitHub URL
    
    Args:
        repository: Repository name (e.g., 'world', 'europe', 'south-america')
        country: Country folder name
        league_file: League file name pattern
        season: Season in OpenFootball format (e.g., '2023-24')
    
    Returns:
        Full URL to raw file
    """
    # Try common file extensions
    file_patterns = [
        f"{league_file}.txt",
        f"{league_file}.yml",
        f"{season}/{league_file}.txt",
        f"{season}/{league_file}.yml",
    ]
    
    # Return base URL - will try patterns in order
    base_path = f"{repository}/master/{country}"
    return f"{OPENFOOTBALL_BASE_URL}/{base_path}"


class OpenFootballService:
    """Service for ingesting data from OpenFootball repositories"""
    
    def __init__(self, db: Session):
        """
        Initialize OpenFootball service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def download_football_txt(
        self,
        repository: str,
        country: str,
        league_code: str,
        season_str: str,
        file_pattern: str
    ) -> Optional[str]:
        """
        Download Football.TXT file from OpenFootball repository
        Tries local files first (if OPENFOOTBALL_LOCAL_PATH is configured), then falls back to GitHub.
        
        Args:
            repository: Repository name ('world', 'europe', 'south-america')
            country: Country folder name (can include subfolders like 'north-america/mexico')
            league_code: League code for file naming (e.g., 'mx1', 'mls', 'jp1')
            season_str: Season string (e.g., '2023-24' or '2023')
            file_pattern: File pattern template with {league_code} placeholder
        
        Returns:
            File content as string, or None if not found
        """
        # Replace {league_code} placeholder in file pattern
        filename = file_pattern.format(league_code=league_code)
        
        # Try local file first if OPENFOOTBALL_LOCAL_PATH is configured
        if settings.OPENFOOTBALL_LOCAL_PATH:
            # Resolve path - handle both absolute and relative paths
            local_path_str = settings.OPENFOOTBALL_LOCAL_PATH
            if not os.path.isabs(local_path_str):
                # Relative path - resolve from project root (where the script is run from)
                # Or use the workspace root if available
                project_root = Path.cwd()  # Current working directory
                local_path = project_root / local_path_str
            else:
                local_path = Path(local_path_str)
            
            if local_path.exists() and local_path.is_dir():
                # Construct local file path: {local_path}/{country}/{filename}
                # Note: For world repo, country already includes subfolders (e.g., "north-america/mexico")
                local_file = local_path / country / filename
                
                if local_file.exists() and local_file.is_file():
                    try:
                        logger.info(f"Reading OpenFootball data from local file: {local_file}")
                        with open(local_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        if content:
                            logger.info(f"Successfully loaded {len(content)} characters from local file")
                            return content
                    except Exception as e:
                        logger.warning(f"Failed to read local file {local_file}: {e}")
                else:
                    logger.debug(f"Local file not found: {local_file}, trying GitHub...")
            else:
                logger.debug(f"Local path does not exist or is not a directory: {local_path}, trying GitHub...")
        
        # Fall back to GitHub download
        base_path = f"{repository}/master/{country}"
        url = f"{OPENFOOTBALL_BASE_URL}/{base_path}/{filename}"
        
        try:
            logger.debug(f"Trying OpenFootball URL: {url}")
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, timeout=30, verify=verify_ssl)
            if response.status_code == 200:
                content = response.text.strip()
                # Validate it's not HTML error page
                if content and not (content.startswith('<!DOCTYPE') or content.startswith('<html') or content.startswith('<HTML')):
                    logger.info(f"Found OpenFootball data at: {url}")
                    return content
        except requests.RequestException as e:
            logger.debug(f"Failed to download from {url}: {e}")
        
        logger.warning(f"Could not find OpenFootball data locally or at: {url}")
        return None
    
    def parse_football_txt(self, content: str) -> List[Dict]:
        """
        Parse Football.TXT format into match records
        
        Actual Football.TXT format (from world-master):
        » Matchday 1
          Sat Feb/25 2023
            16.55  Nashville SC            v New York City FC         2-0 (1-0)
            19.30  Atlanta United FC       v San Jose Earthquakes     2-1 (0-1)
                  Charlotte FC            v New England Revolution   0-1 (0-0)
        
        Date formats:
        - "Sat Feb/25 2023" (most common)
        - "Fri Oct/20 2023"
        
        Match formats:
        - "19.45  Team A v Team B 3-0 (1-0)" (with time and half-time)
        - "Team A v Team B 3-0" (without time)
        - "Team A v Team B 3-0 (1-0)" (without time, with half-time)
        
        Args:
            content: Football.TXT file content
        
        Returns:
            List of match dictionaries with keys: date, home_team, away_team, home_goals, away_goals
        """
        matches = []
        lines = content.split('\n')
        
        current_date = None
        current_round = None
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Skip empty lines, comments, and header lines
            if not line or line.startswith('#') or line.startswith('=') or line.startswith('»'):
                continue
            
            # Parse date lines - format: "Sat Feb/25 2023" or "Fri Oct/20 2023"
            # Pattern: Day Mon/Day Year
            date_patterns = [
                r'(\w+)\s+(\w+)/(\d+)\s+(\d{4})',  # "Sat Feb/25 2023"
                r'(\w+)\s+(\w+)\s+(\d+),\s+(\d{4})',  # "Sat Aug 23, 2024" (alternative)
            ]
            
            for pattern in date_patterns:
                date_match = re.match(pattern, line)
                if date_match:
                    try:
                        day_name = date_match.group(1)
                        month_name = date_match.group(2)
                        day_num = date_match.group(3)
                        year = int(date_match.group(4))
                        
                        # Convert month name to number
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month = month_map.get(month_name.lower()[:3])
                        if month:
                            current_date = date(year, month, int(day_num))
                            continue
                    except (ValueError, IndexError):
                        pass
            
            # Try ISO date format
            iso_date_match = re.match(r'(\d{4}-\d{2}-\d{2})', line)
            if iso_date_match:
                try:
                    current_date = datetime.strptime(iso_date_match.group(1), '%Y-%m-%d').date()
                    continue
                except ValueError:
                    pass
            
            # Parse matchday/round headers - format: "» Matchday 1" or "[Round 1]"
            round_patterns = [
                r'»\s*(?:Matchday|Round|Game)\s+(\d+)',  # "» Matchday 1"
                r'\[(?:Round|Matchday|Game)\s+(\d+)\]',  # "[Round 1]"
            ]
            for pattern in round_patterns:
                round_match = re.match(pattern, line, re.IGNORECASE)
                if round_match:
                    current_round = round_match.group(1)
                    continue
            
            # Parse match line
            # Format: "[time]  Team A v Team B score (half-time)" or "Team A v Team B score"
            # Examples:
            # "19.45  Team A v Team B 3-0 (1-0)"
            # "Team A v Team B 3-0"
            # "Team A v Team B 3-0 (1-0)"
            
            # Pattern 1: With time: "HH.MM  Team A v Team B FT (HT)"
            match_with_time = re.match(r'(\d{1,2}\.\d{2})\s+(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?', line)
            if match_with_time:
                home_team = match_with_time.group(2).strip()
                away_team = match_with_time.group(3).strip()
                home_goals = int(match_with_time.group(4))
                away_goals = int(match_with_time.group(5))
                
                if not current_date:
                    logger.warning(f"Skipping match {home_team} vs {away_team} - no date available")
                    continue
                
                matches.append({
                    'date': current_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'round': current_round
                })
                continue
            
            # Pattern 2: Without time: "Team A v Team B FT (HT)"
            match_no_time = re.match(r'(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?', line)
            if match_no_time:
                home_team = match_no_time.group(1).strip()
                away_team = match_no_time.group(2).strip()
                home_goals = int(match_no_time.group(3))
                away_goals = int(match_no_time.group(4))
                
                if not current_date:
                    logger.warning(f"Skipping match {home_team} vs {away_team} - no date available")
                    continue
                
                matches.append({
                    'date': current_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'round': current_round
                })
                continue
        
        return matches
    
    def convert_matches_to_csv(self, matches: List[Dict], league_code: str) -> str:
        """
        Convert match records to CSV format matching football-data.co.uk structure
        
        Args:
            matches: List of match dictionaries
            league_code: League code
        
        Returns:
            CSV content as string
        """
        if not matches:
            return ""
        
        # Create CSV with minimal required columns (matching football-data.co.uk format)
        output = io.StringIO()
        fieldnames = [
            'Div', 'Date', 'Time', 'HomeTeam', 'AwayTeam', 
            'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 'HTR',
            'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
            'AvgH', 'AvgD', 'AvgA'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for match in matches:
            # Determine result
            if match['home_goals'] > match['away_goals']:
                ftr = 'H'
            elif match['home_goals'] < match['away_goals']:
                ftr = 'A'
            else:
                ftr = 'D'
            
            # Format date
            date_str = match['date'].strftime('%d/%m/%Y')
            
            row = {
                'Div': league_code,
                'Date': date_str,
                'Time': '',  # OpenFootball doesn't always have time
                'HomeTeam': match['home_team'],
                'AwayTeam': match['away_team'],
                'FTHG': match['home_goals'],
                'FTAG': match['away_goals'],
                'FTR': ftr,
                'HTHG': '',  # Half-time data not always available
                'HTAG': '',
                'HTR': '',
                'HS': '',  # Stats not available in OpenFootball
                'AS': '',
                'HST': '',
                'AST': '',
                'HF': '',
                'AF': '',
                'HC': '',
                'AC': '',
                'HY': '',
                'AY': '',
                'HR': '',
                'AR': '',
                'AvgH': '',  # Betting odds not available in OpenFootball
                'AvgD': '',
                'AvgA': '',
            }
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def ingest_league_matches(
        self,
        league_code: str,
        season: Optional[str] = None,
        batch_number: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Ingest matches for a league from OpenFootball
        
        Args:
            league_code: League code (e.g., 'USA1')
            season: Season code (e.g., '2324' for 2023-24) or None for current season
            batch_number: Optional batch number for logging
        
        Returns:
            Dict with ingestion statistics
        """
        # Get OpenFootball path
        path_info = get_openfootball_path(league_code)
        if not path_info:
            raise ValueError(f"No OpenFootball path found for league code: {league_code}")
        
        repository, country, league_code_file, season_format, file_ext = path_info
        
        # Convert season code to OpenFootball format
        if season:
            season_str, file_pattern = convert_season_code_to_openfootball(season, season_format)
        else:
            # Use current season
            current_year = datetime.now().year
            if season_format == 'YYYY':
                season_str = str(current_year)
                file_pattern = f"{current_year}_{{league_code}}.txt"
            else:
                season_str = f"{current_year}-{str(current_year + 1)[-2:]}"
                file_pattern = f"{season_str}_{{league_code}}.txt"
        
        # Download Football.TXT file
        logger.info(f"Downloading {league_code} season {season_str} from OpenFootball ({repository})...")
        content = self.download_football_txt(repository, country, league_code_file, season_str, file_pattern)
        
        if not content:
            raise ValueError(f"Could not download OpenFootball data for {league_code} season {season_str}")
        
        # Parse Football.TXT
        logger.info(f"Parsing Football.TXT format for {league_code}...")
        matches = self.parse_football_txt(content)
        
        if not matches:
            logger.warning(f"No matches found in OpenFootball data for {league_code} season {season_str}")
            return {
                "processed": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0
            }
        
        logger.info(f"Parsed {len(matches)} matches from OpenFootball data")
        
        # Convert to CSV format
        csv_content = self.convert_matches_to_csv(matches, league_code)
        
        # Use existing CSV ingestion (but mark source as OpenFootball)
        from app.services.data_ingestion import DataIngestionService
        
        ingestion_service = DataIngestionService(self.db, enable_cleaning=settings.ENABLE_DATA_CLEANING)
        
        # Ingest the CSV content
        # Use original season code for ingestion (e.g., '2324') or season_str if no season provided
        ingestion_season = season if season else season_str
        stats = ingestion_service.ingest_csv(
            csv_content,
            league_code,
            ingestion_season,
            source_name="OpenFootball",
            batch_number=batch_number,
            save_csv=False  # Don't save converted CSV, just ingest
        )
        
        return stats

