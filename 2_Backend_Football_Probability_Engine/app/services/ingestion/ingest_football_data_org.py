"""
Ingest match data from Football-Data.org API

Football-Data.org provides free API access (with rate limits) for match data.
This service handles leagues that are not available on football-data.co.uk.
"""
import requests
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, date, time as dt_time
import logging
import time
import urllib3

from app.db.models import League, Team, Match, DataSource, IngestionLog, MatchResult
from app.services.team_resolver import resolve_team_safe
from app.config import settings

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
# Use getattr with default True to handle cases where attribute might not exist yet
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Mapping of our league codes to Football-Data.org competition IDs
# Football-Data.org uses numeric competition IDs
# 
# IMPORTANT: Many competitions require a PAID subscription tier.
# Free tier typically only includes:
# - Major European leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1)
# - Some major competitions (Champions League, Europa League)
#
# To verify competition IDs, visit: https://www.football-data.org/documentation/api
# To check your subscription tier limits, visit: https://www.football-data.org/pricing
#
# If you get 403 errors, the competition likely requires a paid subscription.
LEAGUE_CODE_TO_COMPETITION_ID = {
    # Europe - Extra Leagues
    # NOTE: These may require paid subscription (Tier 2 or higher)
    'SWE1': 2003,  # Allsvenskan (Sweden) - May require paid subscription
    'FIN1': 2010,  # Veikkausliiga (Finland) - May require paid subscription
    'RO1': 2013,   # Liga 1 (Romania) - May require paid subscription
    'RUS1': 2018,  # Premier League (Russia) - May require paid subscription
    'IRL1': 2019,  # Premier Division (Ireland) - May require paid subscription
    'CZE1': 2015,  # First League (Czech Republic) - May require paid subscription
    'CRO1': 2014,  # Prva HNL (Croatia) - May require paid subscription
    'SRB1': 2016,  # SuperLiga (Serbia) - May require paid subscription
    'UKR1': 2002,  # Premier League (Ukraine) - May require paid subscription
    
    # Americas
    # NOTE: These likely require paid subscription
    'ARG1': 2014,  # Primera Division (Argentina) - Requires paid subscription
    'BRA1': 2013,  # Serie A (Brazil) - Requires paid subscription
    'MEX1': 2012,  # Liga MX (Mexico) - Requires paid subscription
    'USA1': 2017,  # Major League Soccer (USA) - May require paid subscription
    
    # Asia & Oceania
    # NOTE: These likely require paid subscription
    'CHN1': 2011,  # Super League (China) - Requires paid subscription
    'JPN1': 2019,  # J-League (Japan) - Requires paid subscription
    'KOR1': 2018,  # K League 1 (South Korea) - Requires paid subscription
    'AUS1': 2018,  # A-League (Australia) - Requires paid subscription
}

# Reverse mapping for lookup
COMPETITION_ID_TO_LEAGUE_CODE = {v: k for k, v in LEAGUE_CODE_TO_COMPETITION_ID.items()}


def get_competition_id(league_code: str) -> Optional[int]:
    """Get Football-Data.org competition ID for a league code"""
    return LEAGUE_CODE_TO_COMPETITION_ID.get(league_code)


def get_league_code(competition_id: int) -> Optional[str]:
    """Get league code from Football-Data.org competition ID"""
    return COMPETITION_ID_TO_LEAGUE_CODE.get(competition_id)


class FootballDataOrgService:
    """Service for ingesting data from Football-Data.org API"""
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Initialize Football-Data.org service
        
        Args:
            db: Database session
            api_key: API key (optional, will use config if not provided)
        """
        self.db = db
        self.api_key = api_key or settings.FOOTBALL_DATA_ORG_KEY
        self.base_url = settings.FOOTBALL_DATA_ORG_BASE_URL
        self.headers = {
            "X-Auth-Token": self.api_key
        } if self.api_key else {}
        
        # Rate limiting: Free tier allows 10 requests per minute
        self.last_request_time = 0
        self.min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make API request with rate limiting and error handling
        
        Args:
            endpoint: API endpoint (e.g., '/competitions/{id}/matches')
            params: Query parameters
        
        Returns:
            JSON response as dict
        """
        if not self.api_key:
            raise ValueError("Football-Data.org API key not configured. Set FOOTBALL_DATA_ORG_KEY in environment variables.")
        
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=self.headers, params=params, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                # Retry once
                verify_ssl = getattr(settings, 'VERIFY_SSL', True)
                response = requests.get(url, headers=self.headers, params=params, timeout=30, verify=verify_ssl)
                response.raise_for_status()
                return response.json()
            elif response.status_code == 403:
                # 403 Forbidden - usually means subscription tier doesn't include this competition
                error_msg = response.text if hasattr(response, 'text') else str(e)
                logger.error(
                    f"403 Forbidden from Football-Data.org for {endpoint}. "
                    f"This competition may require a paid subscription tier. "
                    f"Free tier typically only includes major European leagues. "
                    f"Error: {error_msg}"
                )
                # Raise a more informative error
                raise ValueError(
                    f"403 Forbidden: This competition requires a paid Football-Data.org subscription. "
                    f"Free tier access is limited. Endpoint: {endpoint}"
                )
            elif response.status_code == 404:
                logger.error(f"404 Not Found from Football-Data.org: {endpoint}. Competition ID may be incorrect.")
                raise ValueError(f"Competition not found (404): {endpoint}. Verify competition ID.")
            else:
                error_msg = response.text if hasattr(response, 'text') else str(e)
                logger.error(f"HTTP error {response.status_code} from Football-Data.org: {error_msg}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error from Football-Data.org: {e}")
            raise
    
    def get_matches_for_competition(
        self,
        competition_id: int,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict]:
        """
        Get matches for a competition
        
        Args:
            competition_id: Football-Data.org competition ID
            season: Season year (e.g., 2023 for 2023/24 season)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
        
        Returns:
            List of match dictionaries
        """
        endpoint = f"/competitions/{competition_id}/matches"
        params = {}
        
        if season:
            params['season'] = season
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        
        data = self._make_request(endpoint, params)
        return data.get('matches', [])
    
    def ingest_league_matches(
        self,
        league_code: str,
        season: Optional[str] = None,
        batch_number: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Ingest matches for a league from Football-Data.org
        
        Args:
            league_code: League code (e.g., 'SWE1')
            season: Season code (e.g., '2324' for 2023-24) or None for current season
            batch_number: Optional batch number for logging
        
        Returns:
            Dict with ingestion statistics
        """
        competition_id = get_competition_id(league_code)
        if not competition_id:
            raise ValueError(f"No Football-Data.org competition ID found for league code: {league_code}")
        
        # Get league from database - create if it doesn't exist
        league = self.db.query(League).filter(League.code == league_code).first()
        
        if not league:
            # Auto-create league if it doesn't exist (same logic as ingest_csv)
            logger.warning(f"League {league_code} not found in database. Attempting to create...")
            try:
                # League name mapping for Football-Data.org leagues
                league_names = {
                    'SWE1': ('Allsvenskan', 'Sweden', 1),
                    'FIN1': ('Veikkausliiga', 'Finland', 1),
                    'RO1': ('Liga 1', 'Romania', 1),
                    'RUS1': ('Premier League', 'Russia', 1),
                    'IRL1': ('Premier Division', 'Ireland', 1),
                    'CZE1': ('First League', 'Czech Republic', 1),
                    'CRO1': ('Prva HNL', 'Croatia', 1),
                    'SRB1': ('SuperLiga', 'Serbia', 1),
                    'UKR1': ('Premier League', 'Ukraine', 1),
                    'ARG1': ('Primera Division', 'Argentina', 1),
                    'BRA1': ('Serie A', 'Brazil', 1),
                    'MEX1': ('Liga MX', 'Mexico', 1),
                    'USA1': ('Major League Soccer', 'USA', 1),
                    'CHN1': ('Super League', 'China', 1),
                    'JPN1': ('J-League', 'Japan', 1),
                    'KOR1': ('K League 1', 'South Korea', 1),
                    'AUS1': ('A-League', 'Australia', 1),
                }
                
                league_info = league_names.get(league_code)
                if league_info:
                    name, country, tier = league_info
                else:
                    # Fallback for unknown codes
                    name = f"League {league_code}"
                    country = "Unknown"
                    tier = 1
                
                # Create league entry
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
        
        # Convert season code to year
        season_year = None
        if season and len(season) == 4:
            # Format: '2324' -> 2023
            season_year = 2000 + int(season[:2])
        elif season:
            # Try to parse other formats
            try:
                season_year = int(season)
            except ValueError:
                pass
        
        # Get matches
        try:
            matches_data = self.get_matches_for_competition(competition_id, season=season_year)
        except Exception as e:
            logger.error(f"Failed to fetch matches from Football-Data.org for {league_code}: {e}")
            raise
        
        stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Process each match
        for match_data in matches_data:
            try:
                stats["processed"] += 1
                
                # Extract match data
                match_date = datetime.fromisoformat(match_data['utcDate'].replace('Z', '+00:00')).date()
                home_team_name = match_data['homeTeam']['name']
                away_team_name = match_data['awayTeam']['name']
                
                # Get result if match is finished
                status = match_data.get('status', 'SCHEDULED')
                if status == 'FINISHED':
                    score = match_data.get('score', {})
                    full_time = score.get('fullTime', {})
                    home_goals = full_time.get('home')
                    away_goals = full_time.get('away')
                else:
                    home_goals = None
                    away_goals = None
                
                # Resolve teams
                home_team = resolve_team_safe(self.db, home_team_name, league.id)
                away_team = resolve_team_safe(self.db, away_team_name, league.id)
                
                if not home_team or not away_team:
                    stats["skipped"] += 1
                    logger.warning(f"Skipping match {home_team_name} vs {away_team_name} - teams not resolved")
                    continue
                
                # Check if match already exists
                existing_match = self.db.query(Match).filter(
                    Match.league_id == league.id,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == match_date
                ).first()
                
                # Extract additional data if available
                half_time = score.get('halfTime', {})
                ht_home_goals = half_time.get('home')
                ht_away_goals = half_time.get('away')
                # Ensure both are NULL together (constraint requirement)
                if ht_home_goals is None or ht_away_goals is None:
                    ht_home_goals = None
                    ht_away_goals = None
                
                # Extract match metadata
                match_time = None
                if 'utcDate' in match_data:
                    try:
                        dt = datetime.fromisoformat(match_data['utcDate'].replace('Z', '+00:00'))
                        match_time = dt.time()  # Extract time object (datetime.time)
                    except:
                        pass
                
                venue = match_data.get('venue', {}).get('name') if isinstance(match_data.get('venue'), dict) else None
                matchday = match_data.get('matchday')
                round_name = match_data.get('stage', {}).get('name') if isinstance(match_data.get('stage'), dict) else None
                
                # Extract cards/penalties if available (Football-Data.org API may have this)
                hy = None
                ay = None
                hr = None
                ar = None
                home_penalties = None
                away_penalties = None
                referee_id = None
                
                # Determine result
                result = None
                if home_goals is not None and away_goals is not None:
                    if home_goals > away_goals:
                        result = MatchResult.H
                    elif home_goals < away_goals:
                        result = MatchResult.A
                    else:
                        result = MatchResult.D
                
                # Determine season from match_date
                season_str = None
                if season:
                    # Convert '2324' to '2023-24'
                    if len(season) == 4:
                        year_start = 2000 + int(season[:2])
                        season_str = f"{year_start}-{season[2:]}"
                elif match_date:
                    # Fallback: extract from match_date
                    year = match_date.year
                    month = match_date.month
                    if month >= 8:  # Season starts in August
                        season_str = f"{year}-{str(year + 1)[2:]}"
                    else:
                        season_str = f"{year - 1}-{str(year)[2:]}"
                
                if existing_match:
                    # Update existing match
                    if home_goals is not None and away_goals is not None:
                        existing_match.home_goals = home_goals
                        existing_match.away_goals = away_goals
                    if result:
                        existing_match.result = result
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
                    if season_str:
                        existing_match.season = season_str
                    stats["updated"] += 1
                else:
                    # Create new match
                    new_match = Match(
                        league_id=league.id,
                        season=season_str or f"{match_date.year}-{str(match_date.year + 1)[2:]}",
                        match_date=match_date,
                        home_team_id=home_team.id,
                        away_team_id=away_team.id,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        result=result or MatchResult.D,  # Default to draw if no result
                        ht_home_goals=ht_home_goals,
                        ht_away_goals=ht_away_goals,
                        match_time=match_time,
                        venue=venue,
                        matchday=matchday,
                        round_name=round_name,
                        hy=hy,
                        ay=ay,
                        hr=hr,
                        ar=ar,
                        home_penalties=home_penalties,
                        away_penalties=away_penalties,
                        referee_id=referee_id,
                        source='football-data.org'
                    )
                    self.db.add(new_match)
                    stats["inserted"] += 1
                
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error processing match: {e}", exc_info=True)
                continue
        
        # Commit all changes
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing matches: {e}", exc_info=True)
            raise
        
        logger.info(f"Ingested {stats['inserted']} new matches, updated {stats['updated']} matches for {league_code}")
        
        return stats

