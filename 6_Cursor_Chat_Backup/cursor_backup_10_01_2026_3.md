# Team injuries table id empty
_Exported on 1/11/2026 at 07:04:59 GMT+3 from Cursor (2.1.50)_

---

**User**

@python (326-349) team injuries table id empty

---

**Cursor**


Logs show 0 successful, 53 failed out of 106 processed. Investigating why all requests failed.



Reading the batch processing function to understand why requests are failing:



Checking error details. Reviewing the batch function and adding better error logging to identify why all requests are failing:



Fixing two issues:
1. Counting bug: `results["total"]` is incremented in the loop even though it's already set.
2. Missing return statement: the exception handler doesn't return an error.

Fixing these and improving error logging:



Fixing the counting bug and improving error logging to identify why fixtures are failing:


```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            logger.warning("API-Football key not configured, skipping injury download")
            return {"success": False, "error": "API key not configured"}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            return {"success": False, "error": "Fixture not found"}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            return {"success": False, "error": "Teams not found"}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            return {"success": False, "error": "League not found"}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            return {"success": False, "error": "Fixture date not found"}
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.info(f"Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                logger.warning(f"No API-Football league ID mapping for {league.code}")
                return {"success": False, "error": f"No API-Football mapping for league {league.code}"}
            
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                logger.info(f"International fixture not found in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} - skipping")
                return {
                    "success": False,
                    "error": f"International fixture not available in API-Football",
                    "skipped": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                }
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        # Log full response structure for debugging
        logger.debug(f"Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.info(f"Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            fixtures_list = fixture_data.get("response", [])
            if fixtures_list:
                teams = fixtures_list[0].get("teams", {})
                api_home_team_id = teams.get("home", {}).get("id")
                api_away_team_id = teams.get("away", {}).get("id")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error downloading injuries from API-Football: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```


Adding more detailed error logging in the main download function to identify failure causes:


```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        logger.debug(f"Starting injury download for fixture {fixture_id}")
        
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            error_msg = "API key not configured"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            error_msg = f"Fixture {fixture_id} not found in database"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            error_msg = f"Teams not found: home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            error_msg = f"League not found: league_id={fixture.league_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            error_msg = f"Fixture date not found for fixture {fixture_id} (jackpot_id={fixture.jackpot_id if fixture.jackpot_id else 'None'})"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.debug(f"Fixture {fixture_id}: {home_team.name} vs {away_team.name}, league={league.code}, date={fixture_date}")
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.info(f"Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                logger.warning(f"No API-Football league ID mapping for {league.code}")
                return {"success": False, "error": f"No API-Football mapping for league {league.code}"}
            
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                logger.info(f"International fixture not found in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} - skipping")
                return {
                    "success": False,
                    "error": f"International fixture not available in API-Football",
                    "skipped": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                }
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        # Log full response structure for debugging
        logger.debug(f"Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.info(f"Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            fixtures_list = fixture_data.get("response", [])
            if fixtures_list:
                teams = fixtures_list[0].get("teams", {})
                api_home_team_id = teams.get("home", {}).get("id")
                api_away_team_id = teams.get("away", {}).get("id")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error downloading injuries from API-Football: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```

```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        logger.debug(f"Starting injury download for fixture {fixture_id}")
        
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            error_msg = "API key not configured"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            error_msg = f"Fixture {fixture_id} not found in database"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            error_msg = f"Teams not found: home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            error_msg = f"League not found: league_id={fixture.league_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            error_msg = f"Fixture date not found for fixture {fixture_id} (jackpot_id={fixture.jackpot_id if fixture.jackpot_id else 'None'})"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.debug(f"Fixture {fixture_id}: {home_team.name} vs {away_team.name}, league={league.code}, date={fixture_date}")
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.debug(f"Fixture {fixture_id}: Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                error_msg = f"No API-Football league ID mapping for league code '{league.code}'"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.debug(f"Fixture {fixture_id}: Searching for fixture in API-Football league {api_league_id} ({league.code})")
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                error_msg = f"International fixture not available in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                logger.debug(f"Fixture {fixture_id}: {error_msg} - skipping")
                return {
                    "success": False,
                    "error": error_msg,
                    "skipped": True
                }
            else:
                error_msg = f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} (league: {league.code})"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        logger.debug(f"Fixture {fixture_id}: Found API-Football fixture ID {api_fixture_id}")
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        # Log full response structure for debugging
        logger.debug(f"Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.info(f"Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            fixtures_list = fixture_data.get("response", [])
            if fixtures_list:
                teams = fixtures_list[0].get("teams", {})
                api_home_team_id = teams.get("home", {}).get("id")
                api_away_team_id = teams.get("away", {}).get("id")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error downloading injuries from API-Football: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```

```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        logger.debug(f"Starting injury download for fixture {fixture_id}")
        
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            error_msg = "API key not configured"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            error_msg = f"Fixture {fixture_id} not found in database"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            error_msg = f"Teams not found: home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            error_msg = f"League not found: league_id={fixture.league_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            error_msg = f"Fixture date not found for fixture {fixture_id} (jackpot_id={fixture.jackpot_id if fixture.jackpot_id else 'None'})"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.debug(f"Fixture {fixture_id}: {home_team.name} vs {away_team.name}, league={league.code}, date={fixture_date}")
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.debug(f"Fixture {fixture_id}: Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                error_msg = f"No API-Football league ID mapping for league code '{league.code}'"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.debug(f"Fixture {fixture_id}: Searching for fixture in API-Football league {api_league_id} ({league.code})")
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                error_msg = f"International fixture not available in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                logger.debug(f"Fixture {fixture_id}: {error_msg} - skipping")
                return {
                    "success": False,
                    "error": error_msg,
                    "skipped": True
                }
            else:
                error_msg = f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} (league: {league.code})"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        logger.debug(f"Fixture {fixture_id}: Found API-Football fixture ID {api_fixture_id}")
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        # Log full response structure for debugging
        logger.debug(f"Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.info(f"Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            fixtures_list = fixture_data.get("response", [])
            if fixtures_list:
                teams = fixtures_list[0].get("teams", {})
                api_home_team_id = teams.get("home", {}).get("id")
                api_away_team_id = teams.get("away", {}).get("id")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}", exc_info=True)
        return {"success": False, "error": error_msg}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```


Adding error handling for API responses that return 200 but contain errors in the JSON body:


```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        logger.debug(f"Starting injury download for fixture {fixture_id}")
        
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            error_msg = "API key not configured"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            error_msg = f"Fixture {fixture_id} not found in database"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            error_msg = f"Teams not found: home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            error_msg = f"League not found: league_id={fixture.league_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            error_msg = f"Fixture date not found for fixture {fixture_id} (jackpot_id={fixture.jackpot_id if fixture.jackpot_id else 'None'})"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.debug(f"Fixture {fixture_id}: {home_team.name} vs {away_team.name}, league={league.code}, date={fixture_date}")
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.debug(f"Fixture {fixture_id}: Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                error_msg = f"No API-Football league ID mapping for league code '{league.code}'"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.debug(f"Fixture {fixture_id}: Searching for fixture in API-Football league {api_league_id} ({league.code})")
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                error_msg = f"International fixture not available in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                logger.debug(f"Fixture {fixture_id}: {error_msg} - skipping")
                return {
                    "success": False,
                    "error": error_msg,
                    "skipped": True
                }
            else:
                error_msg = f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} (league: {league.code})"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        logger.debug(f"Fixture {fixture_id}: Found API-Football fixture ID {api_fixture_id}")
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        # Check for API errors in response
        if response.status_code != 200:
            error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
            logger.error(f"Fixture {fixture_id}: {error_msg}")
            response.raise_for_status()
        
        data = response.json()
        
        # Check for API-Football error messages in response
        errors = data.get("errors", [])
        if errors:
            error_msg = f"API-Football errors: {errors}"
            logger.error(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Log full response structure for debugging
        logger.debug(f"Fixture {fixture_id}: Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.debug(f"Fixture {fixture_id}: Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            fixtures_list = fixture_data.get("response", [])
            if fixtures_list:
                teams = fixtures_list[0].get("teams", {})
                api_home_team_id = teams.get("home", {}).get("id")
                api_away_team_id = teams.get("away", {}).get("id")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}", exc_info=True)
        return {"success": False, "error": error_msg}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```


Adding error handling for the fixture query response:


```python
"""
Download team injuries from external APIs (API-Football, Transfermarkt, etc.)

This service provides functions to fetch injury data from various sources
and populate the team_injuries table.
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamInjuries, League, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.team_resolver import resolve_team_safe, normalize_team_name, similarity_score
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import logging
import urllib3
from app.config import settings
import time

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API-Football League ID Mapping
# API-Football uses numeric league IDs (different from our codes)
# To find league IDs: https://www.api-football.com/documentation-v3#tag/Leagues
API_FOOTBALL_LEAGUE_IDS = {
    # Major European Leagues
    'E0': 39,   # Premier League
    'E1': 40,   # Championship
    'E2': 41,   # League One
    'E3': 42,   # League Two
    'SP1': 140, # La Liga
    'SP2': 141, # La Liga 2
    'D1': 78,   # Bundesliga
    'D2': 79,   # 2. Bundesliga
    'I1': 135,  # Serie A
    'I2': 136,  # Serie B
    'F1': 61,   # Ligue 1
    'F2': 62,   # Ligue 2
    'N1': 88,   # Eredivisie
    'P1': 94,   # Primeira Liga
    'B1': 144,  # Pro League
    'T1': 203,  # Super Lig
    'G1': 197,  # Super League 1
    # Add more as needed
}


def get_api_football_league_id(league_code: str) -> Optional[int]:
    """Get API-Football league ID for a league code"""
    return API_FOOTBALL_LEAGUE_IDS.get(league_code)


def find_api_football_fixture_id(
    db: Session,
    fixture: JackpotFixture,
    api_league_id: int,
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID by querying fixtures endpoint.
    
    Args:
        db: Database session
        fixture: Our fixture object
        api_league_id: API-Football league ID
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        # Query API-Football fixtures endpoint
        # Search within date range (±1 day to account for timezone differences)
        date_from = (fixture_date - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (fixture_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "league": api_league_id,
            "date": fixture_date.strftime("%Y-%m-%d"),
            "season": fixture_date.year if fixture_date.month >= 8 else fixture_date.year - 1  # Approximate season
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)  # Wait 1 minute for rate limit
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get("response", [])
        if not fixtures:
            logger.debug(f"No fixtures found for league {api_league_id} on {fixture_date}")
            return None
        
        # Normalize team names for matching
        home_normalized = normalize_team_name(home_team_name)
        away_normalized = normalize_team_name(away_team_name)
        
        # Find best matching fixture
        best_match = None
        best_score = 0.0
        
        for api_fixture in fixtures:
            teams = api_fixture.get("teams", {})
            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            
            if not api_home or not api_away:
                continue
            
            # Calculate similarity scores
            home_score = similarity_score(home_team_name, api_home)
            away_score = similarity_score(away_team_name, api_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2.0
            
            if combined_score > best_score and combined_score >= 0.7:  # Minimum 70% similarity
                best_score = combined_score
                best_match = api_fixture
        
        if best_match:
            api_fixture_id = best_match.get("fixture", {}).get("id")
            logger.info(f"Found API-Football fixture ID {api_fixture_id} for fixture {fixture.id} (similarity: {best_score:.2f})")
            return api_fixture_id
        else:
            logger.warning(f"No matching fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football fixtures: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding API-Football fixture ID: {e}", exc_info=True)
        return None


def find_api_football_fixture_id_international(
    api_key: str,
    home_team_name: str,
    away_team_name: str,
    fixture_date: date
) -> Optional[int]:
    """
    Find API-Football fixture ID for international matches (no league ID needed).
    
    Args:
        api_key: API-Football API key
        home_team_name: Home team name
        away_team_name: Away team name
        fixture_date: Fixture date
    
    Returns:
        API-Football fixture ID or None if not found
    """
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": api_key
        }
        
        # For international matches, search by date only (no league parameter)
        # Try matching for +/- 1 day to account for timezone differences
        for day_offset in range(-1, 2):  # -1, 0, 1
            search_date = fixture_date + timedelta(days=day_offset)
            params = {
                "date": search_date.strftime("%Y-%m-%d")
            }
            
            verify_ssl = getattr(settings, 'VERIFY_SSL', True)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            # Check rate limit
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                try:
                    remaining = int(rate_limit_remaining)
                    if remaining <= 1:
                        logger.warning(f"API-Football rate limit low ({remaining}), waiting 60 seconds...")
                        time.sleep(60)
                        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
                except (ValueError, TypeError):
                    pass
            
            if response.status_code == 429:
                logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
            
            response.raise_for_status()
            data = response.json()
            
            fixtures = data.get("response", [])
            if not fixtures:
                continue
            
            # Find matching fixture by team names
            for api_fixture in fixtures:
                teams = api_fixture.get("teams", {})
                api_home = teams.get("home", {}).get("name", "")
                api_away = teams.get("away", {}).get("name", "")
                
                if not api_home or not api_away:
                    continue
                
                # Check if this is an international match (no league or league type is international)
                league_info = api_fixture.get("league", {})
                league_type = league_info.get("type", "").lower()
                
                # Match if it's an international match type or if team names match
                home_score = similarity_score(home_team_name, api_home)
                away_score = similarity_score(away_team_name, api_away)
                combined_score = (home_score + away_score) / 2.0
                
                # Match if similarity is good (70%+) and it's likely an international match
                if combined_score >= 0.7 and (league_type == "cup" or "international" in league_type or league_type == ""):
                    api_fixture_id = api_fixture.get("fixture", {}).get("id")
                    logger.info(f"Found international fixture ID {api_fixture_id} for {home_team_name} vs {away_team_name} on {search_date} (similarity: {combined_score:.2f})")
                    return api_fixture_id
        
        logger.warning(f"No matching international fixture found for {home_team_name} vs {away_team_name} on {fixture_date}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying API-Football for international fixture: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding international fixture ID: {e}", exc_info=True)
        return None


def parse_api_football_injuries(
    injuries_data: List[Dict],
    team_id: int,
    is_home: bool
) -> Dict:
    """
    Parse injury data from API-Football response.
    
    Args:
        injuries_data: List of injury objects from API-Football
        team_id: Our team ID
        is_home: Whether this is the home team
    
    Returns:
        Dict with parsed injury data
    """
    if not injuries_data:
        return {
            "key_players_missing": 0,
            "attackers_missing": 0,
            "midfielders_missing": 0,
            "defenders_missing": 0,
            "goalkeepers_missing": 0,
            "injury_severity": None,
            "notes": None
        }
    
    # Count injuries by position
    attackers = 0
    midfielders = 0
    defenders = 0
    goalkeepers = 0
    key_players = 0
    
    injury_notes = []
    
    for injury in injuries_data:
        player = injury.get("player", {})
        player_name = player.get("name", "")
        player_id = player.get("id", 0)
        
        # Get position (API-Football may have position info)
        position = injury.get("player", {}).get("position", "").lower()
        
        # Count by position
        if "forward" in position or "striker" in position or "winger" in position:
            attackers += 1
        elif "midfielder" in position or "midfield" in position:
            midfielders += 1
        elif "defender" in position or "defence" in position or "back" in position:
            defenders += 1
        elif "goalkeeper" in position or "keeper" in position or "gk" in position:
            goalkeepers += 1
        
        # Check if key player (you may want to enhance this logic)
        # For now, assume players with IDs are key players
        if player_id > 0:
            key_players += 1
        
        # Collect injury notes
        injury_type = injury.get("player", {}).get("reason", "")
        if injury_type:
            injury_notes.append(f"{player_name}: {injury_type}")
    
    # Calculate injury severity
    total_injuries = attackers + midfielders + goalkeepers + defenders
    injury_severity = calculate_injury_severity(
        key_players, attackers, midfielders, defenders, goalkeepers
    )
    
    notes = "; ".join(injury_notes) if injury_notes else None
    
    return {
        "key_players_missing": key_players,
        "attackers_missing": attackers,
        "midfielders_missing": midfielders,
        "defenders_missing": defenders,
        "goalkeepers_missing": goalkeepers,
        "injury_severity": injury_severity,
        "notes": notes
    }


def download_injuries_from_api_football(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Download injury data for a fixture from API-Football.
    
    Args:
        db: Database session
        fixture_id: Jackpot fixture ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with download statistics
    """
    try:
        logger.debug(f"Starting injury download for fixture {fixture_id}")
        
        if not api_key:
            api_key = settings.API_FOOTBALL_KEY
        
        # Check if API key is empty or None
        if not api_key or api_key.strip() == "":
            error_msg = "API key not configured"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture
        fixture = db.query(JackpotFixture).filter(JackpotFixture.id == fixture_id).first()
        if not fixture:
            error_msg = f"Fixture {fixture_id} not found in database"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get teams
        home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
        
        if not home_team or not away_team:
            error_msg = f"Teams not found: home_team_id={fixture.home_team_id}, away_team_id={fixture.away_team_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get league
        league = db.query(League).filter(League.id == fixture.league_id).first()
        if not league:
            error_msg = f"League not found: league_id={fixture.league_id}"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Get fixture date
        fixture_date = None
        if fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        else:
            error_msg = f"Fixture date not found for fixture {fixture_id} (jackpot_id={fixture.jackpot_id if fixture.jackpot_id else 'None'})"
            logger.warning(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        logger.debug(f"Fixture {fixture_id}: {home_team.name} vs {away_team.name}, league={league.code}, date={fixture_date}")
        
        # Handle INT (International) league differently - no league ID needed
        api_fixture_id = None
        if league.code == "INT":
            # For international matches, search by date and team names without league filter
            logger.debug(f"Fixture {fixture_id}: Searching for international fixture: {home_team.name} vs {away_team.name} on {fixture_date}")
            api_fixture_id = find_api_football_fixture_id_international(
                api_key, home_team.name, away_team.name, fixture_date
            )
        else:
            # For club matches, use league ID
            api_league_id = get_api_football_league_id(league.code)
            if not api_league_id:
                error_msg = f"No API-Football league ID mapping for league code '{league.code}'"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.debug(f"Fixture {fixture_id}: Searching for fixture in API-Football league {api_league_id} ({league.code})")
            # Step 1: Find API-Football fixture ID
            api_fixture_id = find_api_football_fixture_id(
                db, fixture, api_league_id, api_key,
                home_team.name, away_team.name, fixture_date
            )
        
        if not api_fixture_id:
            # For INT matches, this is expected - API-Football may not have all international fixtures
            if league.code == "INT":
                error_msg = f"International fixture not available in API-Football for {home_team.name} vs {away_team.name} on {fixture_date}"
                logger.debug(f"Fixture {fixture_id}: {error_msg} - skipping")
                return {
                    "success": False,
                    "error": error_msg,
                    "skipped": True
                }
            else:
                error_msg = f"Could not find matching fixture in API-Football for {home_team.name} vs {away_team.name} on {fixture_date} (league: {league.code})"
                logger.warning(f"Fixture {fixture_id}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        logger.debug(f"Fixture {fixture_id}: Found API-Football fixture ID {api_fixture_id}")
        
        # Step 2: Get injuries for the API-Football fixture
        url = "https://v3.football.api-sports.io/injuries"
        headers = {
            "x-apisports-key": api_key
        }
        params = {
            "fixture": api_fixture_id
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Check rate limit headers
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        daily_remaining = response.headers.get('x-ratelimit-requests-remaining')
        
        if rate_limit_remaining:
            try:
                remaining = int(rate_limit_remaining)
                if remaining <= 1:
                    logger.warning(f"API-Football per-minute rate limit low ({remaining} remaining), waiting 60 seconds...")
                    time.sleep(60)
            except (ValueError, TypeError):
                pass
        
        if response.status_code == 429:
            logger.warning("API-Football rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        
        # Log rate limit info for debugging
        if daily_remaining:
            try:
                logger.debug(f"API-Football daily requests remaining: {daily_remaining}")
            except:
                pass
        
        # Check for API errors in response
        if response.status_code != 200:
            error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
            logger.error(f"Fixture {fixture_id}: {error_msg}")
            response.raise_for_status()
        
        data = response.json()
        
        # Check for API-Football error messages in response
        errors = data.get("errors", [])
        if errors:
            error_msg = f"API-Football errors: {errors}"
            logger.error(f"Fixture {fixture_id}: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Log full response structure for debugging
        logger.debug(f"Fixture {fixture_id}: Injuries API response structure: {list(data.keys())}")
        
        injuries_response = data.get("response", [])
        logger.debug(f"Fixture {fixture_id}: Injuries API response for fixture {api_fixture_id}: {len(injuries_response)} injury groups found")
        
        if not injuries_response:
            logger.warning(f"No injury data returned from API-Football for fixture {api_fixture_id}")
            # Still create records with zeros to track that we checked
            injuries_response = []
        
        # Parse injuries for home and away teams
        home_injuries = []
        away_injuries = []
        
        # Get team names from API-Football fixture to match injuries
        # We need to query the fixture again to get team IDs
        fixture_url = "https://v3.football.api-sports.io/fixtures"
        fixture_response = requests.get(
            fixture_url,
            headers=headers,
            params={"id": api_fixture_id},
            timeout=30,
            verify=verify_ssl
        )
        
        # Check rate limit for fixture query
        if fixture_response.status_code == 429:
            logger.warning("API-Football rate limit exceeded on fixture query, waiting 60 seconds...")
            time.sleep(60)
            fixture_response = requests.get(
                fixture_url,
                headers=headers,
                params={"id": api_fixture_id},
                timeout=30,
                verify=verify_ssl
            )
        
        api_home_team_id = None
        api_away_team_id = None
        
        if fixture_response.status_code == 200:
            fixture_data = fixture_response.json()
            
            # Check for API errors
            errors = fixture_data.get("errors", [])
            if errors:
                logger.warning(f"Fixture {fixture_id}: API-Football fixture query errors: {errors}")
            else:
                fixtures_list = fixture_data.get("response", [])
                if fixtures_list:
                    teams = fixtures_list[0].get("teams", {})
                    api_home_team_id = teams.get("home", {}).get("id")
                    api_away_team_id = teams.get("away", {}).get("id")
                    logger.debug(f"Fixture {fixture_id}: Found API team IDs - home={api_home_team_id}, away={api_away_team_id}")
                else:
                    logger.warning(f"Fixture {fixture_id}: No fixture data returned from API-Football for fixture ID {api_fixture_id}")
        else:
            logger.warning(f"Fixture {fixture_id}: Failed to query fixture details from API-Football: status {fixture_response.status_code}")
        
        # Match injuries to teams
        logger.debug(f"Matching {len(injuries_response)} injury groups to teams")
        for injury_group in injuries_response:
            team_id_api = injury_group.get("team", {}).get("id")
            team_name_api = injury_group.get("team", {}).get("name", "")
            injuries = injury_group.get("players", [])
            
            logger.debug(f"Injury group: team_id={team_id_api}, team_name={team_name_api}, players={len(injuries)}")
            
            if not injuries:
                logger.debug(f"Skipping injury group with no players for team {team_name_api}")
                continue
            
            # Match team ID
            if api_home_team_id and team_id_api == api_home_team_id:
                home_injuries = injuries
            elif api_away_team_id and team_id_api == api_away_team_id:
                away_injuries = injuries
            else:
                # Fallback: match by team name similarity
                team_name_api = injury_group.get("team", {}).get("name", "")
                if team_name_api:
                    home_similarity = similarity_score(home_team.name, team_name_api)
                    away_similarity = similarity_score(away_team.name, team_name_api)
                    
                    if home_similarity > away_similarity and home_similarity >= 0.7:
                        home_injuries = injuries
                    elif away_similarity > home_similarity and away_similarity >= 0.7:
                        away_injuries = injuries
                    elif not home_injuries:
                        # Default to home if no match found
                        home_injuries = injuries
                    elif not away_injuries:
                        away_injuries = injuries
        
        # Parse injury data
        logger.info(f"Parsing injuries: home={len(home_injuries)} players, away={len(away_injuries)} players")
        home_injury_data = parse_api_football_injuries(home_injuries, fixture.home_team_id, True)
        away_injury_data = parse_api_football_injuries(away_injuries, fixture.away_team_id, False)
        
        logger.info(f"Parsed injury data - Home: key_players={home_injury_data.get('key_players_missing', 0)}, severity={home_injury_data.get('injury_severity')}")
        logger.info(f"Parsed injury data - Away: key_players={away_injury_data.get('key_players_missing', 0)}, severity={away_injury_data.get('injury_severity')}")
        
        # Check if we have any injury data at all
        has_home_injuries = home_injury_data.get('key_players_missing', 0) > 0 or home_injury_data.get('notes')
        has_away_injuries = away_injury_data.get('key_players_missing', 0) > 0 or away_injury_data.get('notes')
        
        if not has_home_injuries and not has_away_injuries:
            logger.info(f"No injuries found for fixture {fixture_id} - API may not have injury data for this fixture")
            # Still save zero records to indicate we checked
            has_home_injuries = True
            has_away_injuries = True
        
        # Save injuries to database
        results = {
            "home_inserted": 0,
            "away_inserted": 0,
            "home_updated": 0,
            "away_updated": 0,
            "errors": []
        }
        
        # Record home team injuries (always save, even if zeros, to track that we checked)
        logger.info(f"Recording injuries for home team {fixture.home_team_id} in fixture {fixture_id}")
        home_result = record_team_injuries(
            db,
            fixture.home_team_id,
            fixture_id,
            home_injury_data["key_players_missing"],
            home_injury_data["injury_severity"],
            home_injury_data["attackers_missing"],
            home_injury_data["midfielders_missing"],
            home_injury_data["defenders_missing"],
            home_injury_data["goalkeepers_missing"],
            home_injury_data["notes"]
        )
        
        if home_result.get("success"):
            if home_result.get("action") == "created":
                results["home_inserted"] = 1
                logger.info(f"✓ Created injury record for home team {fixture.home_team_id}")
            else:
                results["home_updated"] = 1
                logger.info(f"✓ Updated injury record for home team {fixture.home_team_id}")
        else:
            error_msg = home_result.get('error', 'Unknown error')
            results["errors"].append(f"Home team: {error_msg}")
            logger.warning(f"✗ Failed to record home team injuries: {error_msg}")
        
        # Record away team injuries
        logger.info(f"Recording injuries for away team {fixture.away_team_id} in fixture {fixture_id}")
        away_result = record_team_injuries(
            db,
            fixture.away_team_id,
            fixture_id,
            away_injury_data["key_players_missing"],
            away_injury_data["injury_severity"],
            away_injury_data["attackers_missing"],
            away_injury_data["midfielders_missing"],
            away_injury_data["defenders_missing"],
            away_injury_data["goalkeepers_missing"],
            away_injury_data["notes"]
        )
        
        if away_result.get("success"):
            if away_result.get("action") == "created":
                results["away_inserted"] = 1
                logger.info(f"✓ Created injury record for away team {fixture.away_team_id}")
            else:
                results["away_updated"] = 1
                logger.info(f"✓ Updated injury record for away team {fixture.away_team_id}")
        else:
            error_msg = away_result.get('error', 'Unknown error')
            results["errors"].append(f"Away team: {error_msg}")
            logger.warning(f"✗ Failed to record away team injuries: {error_msg}")
        
        db.commit()
        
        total_inserted = results['home_inserted'] + results['away_inserted']
        total_updated = results['home_updated'] + results['away_updated']
        logger.info(f"Downloaded injuries for fixture {fixture_id}: {total_inserted} inserted, {total_updated} updated")
        
        if total_inserted == 0 and total_updated == 0:
            logger.warning(f"⚠ No injuries were saved for fixture {fixture_id} - check if API returned injury data")
        
        return {
            "success": True,
            "api_fixture_id": api_fixture_id,
            **results
        }
        
    except requests.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Fixture {fixture_id}: {error_msg}", exc_info=True)
        return {"success": False, "error": error_msg}


def download_injuries_for_fixtures_batch(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    source: str = "api-football",
    api_key: Optional[str] = None
) -> Dict:
    """
    Batch download injuries for multiple fixtures from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        source: Data source ('api-football', 'transfermarkt', etc.)
        api_key: API key (optional, can be from config)
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        if source == "api-football":
            # Get API key from settings if not provided
            if not api_key or api_key.strip() == "":
                api_key = settings.API_FOOTBALL_KEY
            
            # Debug logging - check what we're getting from settings
            api_key_value = getattr(settings, 'API_FOOTBALL_KEY', None)
            logger.info(f"API-Football key check: has_attr={hasattr(settings, 'API_FOOTBALL_KEY')}, key_type={type(api_key_value)}, key_length={len(str(api_key_value)) if api_key_value else 0}, key_preview={str(api_key_value)[:15] + '...' if api_key_value and len(str(api_key_value)) > 15 else str(api_key_value) if api_key_value else 'None'}")
            
            # Check if API key is empty or None
            if not api_key or (isinstance(api_key, str) and api_key.strip() == ""):
                logger.warning(f"API-Football key not configured. Settings.API_FOOTBALL_KEY = '{api_key_value}' (type: {type(api_key_value)})")
                return {
                    "success": False,
                    "error": f"API-Football API key not configured. Current value: '{api_key_value}' (type: {type(api_key_value)}). Please set API_FOOTBALL_KEY in .env file and restart the backend server.",
                    "total": results["total"],
                    "successful": 0,
                    "failed": 0,
                    "skipped": results["total"]
                }
            
            # Download from API-Football
            # Add rate limiting: API-Football free tier allows ~10 requests/minute
            request_count = 0
            last_request_time = time.time()
            min_request_interval = 6.0  # 6 seconds between requests (10 per minute)
            
            for fixture in fixtures:
                # Rate limiting
                elapsed = time.time() - last_request_time
                if elapsed < min_request_interval:
                    time.sleep(min_request_interval - elapsed)
                last_request_time = time.time()
                
                request_count += 1
                
                try:
                    result = download_injuries_from_api_football(db, fixture.id, api_key)
                    if result.get("success"):
                        results["successful"] += 1
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "api_fixture_id": result.get("api_fixture_id"),
                            "home_inserted": result.get("home_inserted", 0),
                            "away_inserted": result.get("away_inserted", 0),
                            "home_updated": result.get("home_updated", 0),
                            "away_updated": result.get("away_updated", 0),
                            "success": True
                        })
                    elif result.get("skipped"):
                        # INT matches that aren't found in API-Football are skipped, not failed
                        results["skipped"] += 1
                        error_msg = result.get("error", "Skipped")
                        logger.debug(f"Fixture {fixture.id} skipped: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False,
                            "skipped": True
                        })
                    else:
                        results["failed"] += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.warning(f"Fixture {fixture.id} failed: {error_msg}")
                        results["details"].append({
                            "fixture_id": fixture.id,
                            "error": error_msg,
                            "success": False
                        })
                    
                    # Log progress every 10 fixtures
                    if request_count % 10 == 0:
                        logger.info(f"Processed {request_count}/{len(fixtures)} fixtures...")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = str(e)
                    logger.error(f"Exception downloading injuries for fixture {fixture.id}: {error_msg}", exc_info=True)
                    results["details"].append({
                        "fixture_id": fixture.id,
                        "error": error_msg,
                        "success": False
                    })
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        logger.info(f"Injury download complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch injury download: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


```


Fixed the counting bug and improved error logging. Summary:

## Issues Fixed:

1. **Counting bug**: Removed duplicate increment of `results["total"]` (line 746). It was already set to `len(fixtures)` earlier, causing incorrect totals (106 instead of 53).

2. **Error logging**: Added detailed logging throughout the function to identify why fixtures fail:
   - Logs fixture ID at each step
   - Logs specific error messages for each failure type
   - Logs API response errors
   - Logs when fixtures aren't found in API-Football

3. **API error handling**: Added checks for API-Football errors in JSON responses (they can return 200 with errors in the body).

## Next Steps:

Run the injury download again. The logs will show:
- Which fixtures are failing
- Why each fixture failed (e.g., "Could not find matching fixture", "No API-Football mapping for league", "API request failed", etc.)

Common failure reasons:
- **League code not mapped**: The league code isn't in `API_FOOTBALL_LEAGUE_IDS`
- **Fixture not found**: Team names or dates don't match API-Football data
- **API errors**: Rate limits, invalid API key, or API service issues

The improved logging will help pinpoint the exact cause. Check the terminal output after running the download to see the specific error messages for each fixture.

---

**User**

i want Data Cleaning & ETL whe i run pipel;ine its saves in the file {F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data\Historical Match_Odds_Data} and not directly in {F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data}

---

**Cursor**


Searching for where the ETL pipeline saves cleaned data to update the output path to the `Historical Match_Odds_Data` subdirectory.



Checking the data cleaning service to see where it saves cleaned files:



Checking for pipeline or ETL scripts that might save cleaned data directly:



Checking the automated pipeline scripts:



Checking `data_preparation.py` since it mentions saving to `2_Cleaned_data`:



Checking where `DataPreparationService` saves files:



Updating `DataPreparationService` to save files to `Historical Match_Odds_Data` instead of directly to `2_Cleaned_data`:


```python
"""
Data Preparation Service for Model Training
Combines cleaned data per league and exports to CSV/Parquet for training
"""
import pandas as pd
import numpy as np
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False
    logger.warning("pyarrow not installed. Parquet export disabled. Install with: pip install pyarrow")


class DataPreparationService:
    """
    Service for preparing cleaned data for model training
    - Combines all seasons per league
    - Exports to CSV and Parquet formats
    - Optimized for training workflows
    """
    
    def __init__(self, db: Session, output_dir: Optional[Path] = None):
        """
        Initialize data preparation service
        
        Args:
            db: Database session
            output_dir: Output directory for cleaned files (default: data/2_Cleaned_data/Historical Match_Odds_Data)
        """
        self.db = db
        
        if output_dir is None:
            backend_root = Path(__file__).parent.parent.parent
            output_dir = backend_root / "data" / "2_Cleaned_data" / "Historical Match_Odds_Data"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_league_data(
        self,
        league_code: str,
        format: str = "both",  # "csv", "parquet", or "both"
        apply_cleaning: bool = True
    ) -> Dict[str, any]:
        """
        Prepare cleaned data for a specific league
        
        Combines all seasons into one file per league
        
        Args:
            league_code: League code (e.g., 'E0')
            format: Output format ("csv", "parquet", or "both")
            apply_cleaning: Apply Phase 1 cleaning if loading from files
        
        Returns:
            Dictionary with file paths and statistics
        """
        from app.db.models import League, Match
        
        # Get league
        league = self.db.query(League).filter(League.code == league_code).first()
        if not league:
            raise ValueError(f"League not found: {league_code}")
        
        logger.info(f"Preparing data for league: {league.name} ({league_code})")
        
        # Load all matches for this league from database
        matches = self.db.query(Match).filter(
            Match.league_id == league.id
        ).order_by(Match.match_date.asc()).all()
        
        if not matches:
            logger.warning(f"No matches found in database for league {league_code}, trying to load from CSV files...")
            # Try loading from batch CSV files
            df = self._load_from_batch_csv_files(league_code, league.name)
            if df is None or len(df) == 0:
                logger.warning(f"No matches found for league {league_code}")
                return {
                    "league_code": league_code,
                    "league_name": league.name,
                    "matches_count": 0,
                    "files_created": []
                }
        else:
            # Convert to DataFrame
            df = self._matches_to_dataframe(matches, league_code)
        
        # Apply cleaning if requested
        if apply_cleaning:
            from app.services.data_cleaning import DataCleaningService
            from app.config import settings
            cleaner = DataCleaningService(missing_threshold=0.5, enable_cleaning=True)
            # Use Phase 2 cleaning (includes Phase 1 + outlier-based features)
            cleaning_phase = getattr(settings, 'DATA_CLEANING_PHASE', 'phase2')
            logger.info(f"Applying data cleaning with phase: {cleaning_phase}")
            df, _ = cleaner.clean_csv_content(
                df.to_csv(index=False),
                return_stats=False,
                phase=cleaning_phase  # Use phase2 to include all features
            )
            # Re-parse cleaned CSV
            df = pd.read_csv(io.StringIO(df))
        
        # Prepare filename
        league_name_safe = league.name.replace(' ', '_').replace('/', '_')
        league_name_safe = ''.join(c for c in league_name_safe if c.isalnum() or c in ('_', '-'))
        base_filename = f"{league_code}_{league_name_safe}_all_seasons"
        
        files_created = []
        
        # Determine date column name (could be 'Date' from CSV or 'match_date' from DB)
        date_col = 'Date' if 'Date' in df.columns else ('match_date' if 'match_date' in df.columns else None)
        
        # Ensure date column is datetime for isoformat()
        date_start = None
        date_end = None
        if date_col and date_col in df.columns and len(df) > 0:
            try:
                # Convert to datetime if it's not already
                if df[date_col].dtype == 'object' or (len(df) > 0 and isinstance(df[date_col].iloc[0], str)):
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # Get min/max after filtering out NaT values
                valid_dates = df[date_col].dropna()
                if len(valid_dates) > 0:
                    date_start = valid_dates.min()
                    date_end = valid_dates.max()
                    # Convert to ISO format if it's a datetime object
                    if hasattr(date_start, 'isoformat'):
                        date_start = date_start.isoformat()
                    if hasattr(date_end, 'isoformat'):
                        date_end = date_end.isoformat()
            except Exception as e:
                logger.warning(f"Error processing date range for {league_code}: {e}")
        
        stats = {
            "league_code": league_code,
            "league_name": league.name,
            "matches_count": len(df),
            "seasons": sorted(df['season'].unique().tolist()) if 'season' in df.columns else [],
            "date_range": {
                "start": date_start,
                "end": date_end
            },
            "files_created": files_created
        }
        
        # Export to CSV
        if format in ["csv", "both"]:
            csv_path = self.output_dir / f"{base_filename}.csv"
            df.to_csv(csv_path, index=False)
            files_created.append(str(csv_path))
            logger.info(f"Exported CSV: {csv_path} ({len(df)} rows)")
        
        # Export to Parquet
        if format in ["parquet", "both"] and HAS_PARQUET:
            parquet_path = self.output_dir / f"{base_filename}.parquet"
            df.to_parquet(parquet_path, index=False, compression='snappy')
            files_created.append(str(parquet_path))
            
            # Get file sizes
            csv_size = csv_path.stat().st_size if format in ["csv", "both"] else 0
            parquet_size = parquet_path.stat().st_size
            
            logger.info(
                f"Exported Parquet: {parquet_path} ({len(df)} rows, "
                f"CSV: {csv_size/1024/1024:.2f}MB, Parquet: {parquet_size/1024/1024:.2f}MB, "
                f"Compression: {(1 - parquet_size/csv_size)*100:.1f}%"
            )
        
        stats["files_created"] = files_created
        return stats
    
    def prepare_all_leagues(
        self,
        format: str = "both",
        apply_cleaning: bool = True
    ) -> Dict[str, any]:
        """
        Prepare cleaned data for all leagues
        
        Args:
            format: Output format ("csv", "parquet", or "both")
            apply_cleaning: Apply Phase 1 cleaning
        
        Returns:
            Summary statistics
        """
        from app.db.models import League
        
        leagues = self.db.query(League).all()
        
        results = []
        total_matches = 0
        
        for league in leagues:
            try:
                stats = self.prepare_league_data(
                    league.code,
                    format=format,
                    apply_cleaning=apply_cleaning
                )
                results.append(stats)
                total_matches += stats["matches_count"]
            except Exception as e:
                logger.error(f"Error preparing data for {league.code}: {e}", exc_info=True)
                results.append({
                    "league_code": league.code,
                    "league_name": league.name,
                    "error": str(e)
                })
        
        return {
            "total_leagues": len(leagues),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "total_matches": total_matches,
            "leagues": results,
            "output_directory": str(self.output_dir)
        }
    
    def _matches_to_dataframe(self, matches: List, league_code: str) -> pd.DataFrame:
        """
        Convert Match objects to DataFrame
        
        Args:
            matches: List of Match objects
            league_code: League code for reference
        
        Returns:
            DataFrame with match data
        """
        data = []
        for match in matches:
            data.append({
                'Date': match.match_date.isoformat() if match.match_date else None,
                'Div': league_code,
                'HomeTeam': match.home_team.name if match.home_team else None,
                'AwayTeam': match.away_team.name if match.away_team else None,
                'FTHG': match.home_goals,
                'FTAG': match.away_goals,
                'FTR': match.result.value if match.result else None,
                'AvgH': match.odds_home,
                'AvgD': match.odds_draw,
                'AvgA': match.odds_away,
                'season': match.season,
                'league_id': match.league_id,
                'home_team_id': match.home_team_id,
                'away_team_id': match.away_team_id,
                'prob_home_market': match.prob_home_market,
                'prob_draw_market': match.prob_draw_market,
                'prob_away_market': match.prob_away_market,
            })
        
        df = pd.DataFrame(data)
        
        # Convert Date to datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        return df
    
    def load_training_data(
        self,
        league_codes: Optional[List[str]] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        min_matches_per_team: int = 10,
        source: str = "database"  # "database" or "file"
    ) -> pd.DataFrame:
        """
        Load training data for model training
        
        Args:
            league_codes: List of league codes (None = all leagues)
            min_date: Minimum match date
            max_date: Maximum match date
            min_matches_per_team: Minimum matches required per team
            source: "database" (recommended) or "file" (from 2_Cleaned_data)
        
        Returns:
            DataFrame ready for model training
        """
        if source == "database":
            return self._load_from_database(
                league_codes, min_date, max_date, min_matches_per_team
            )
        else:
            return self._load_from_files(
                league_codes, min_date, max_date, min_matches_per_team
            )
    
    def _load_from_database(
        self,
        league_codes: Optional[List[str]],
        min_date: Optional[datetime],
        max_date: Optional[datetime],
        min_matches_per_team: int
    ) -> pd.DataFrame:
        """
        Load training data from database (RECOMMENDED - fastest)
        
        Database is optimized with indexes for fast queries
        """
        from app.db.models import League, Match
        
        query = self.db.query(Match)
        
        # Filter by leagues
        if league_codes:
            leagues = self.db.query(League).filter(League.code.in_(league_codes)).all()
            league_ids = [l.id for l in leagues]
            query = query.filter(Match.league_id.in_(league_ids))
        
        # Filter by date range
        if min_date:
            query = query.filter(Match.match_date >= min_date.date())
        if max_date:
            query = query.filter(Match.match_date <= max_date.date())
        
        # Load matches
        matches = query.order_by(Match.match_date.asc()).all()
        
        logger.info(f"Loaded {len(matches)} matches from database")
        
        # Convert to DataFrame
        df = self._matches_to_dataframe(matches, "ALL")
        
        # Filter teams with minimum matches
        if min_matches_per_team > 0:
            home_counts = df['home_team_id'].value_counts()
            away_counts = df['away_team_id'].value_counts()
            team_counts = (home_counts + away_counts).fillna(0)
            
            valid_teams = team_counts[team_counts >= min_matches_per_team].index.tolist()
            df = df[
                df['home_team_id'].isin(valid_teams) &
                df['away_team_id'].isin(valid_teams)
            ]
            
            logger.info(
                f"Filtered to {len(df)} matches with teams having >= {min_matches_per_team} matches"
            )
        
        return df
    
    def _load_from_files(
        self,
        league_codes: Optional[List[str]],
        min_date: Optional[datetime],
        max_date: Optional[datetime],
        min_matches_per_team: int
    ) -> pd.DataFrame:
        """
        Load training data from cleaned files
        
        Useful for offline training or when database is unavailable
        """
        dfs = []
        
        # Find all league files
        if league_codes:
            files = []
            for code in league_codes:
                csv_file = self.output_dir / f"{code}_*.csv"
                parquet_file = self.output_dir / f"{code}_*.parquet"
                files.extend(list(self.output_dir.glob(f"{code}_*.csv")))
                files.extend(list(self.output_dir.glob(f"{code}_*.parquet")))
        else:
            files = list(self.output_dir.glob("*_all_seasons.csv")) + \
                   list(self.output_dir.glob("*_all_seasons.parquet"))
        
        for file_path in files:
            try:
                if file_path.suffix == '.parquet' and HAS_PARQUET:
                    df = pd.read_parquet(file_path)
                else:
                    df = pd.read_csv(file_path)
                
                # Convert Date to datetime
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                
                # Filter by date range
                if min_date and 'Date' in df.columns:
                    df = df[df['Date'] >= min_date]
                if max_date and 'Date' in df.columns:
                    df = df[df['Date'] <= max_date]
                
                dfs.append(df)
                logger.info(f"Loaded {len(df)} matches from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        if not dfs:
            raise ValueError("No data files found")
        
        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter teams with minimum matches
        if min_matches_per_team > 0:
            home_counts = combined_df['home_team_id'].value_counts()
            away_counts = combined_df['away_team_id'].value_counts()
            team_counts = (home_counts + away_counts).fillna(0)
            
            valid_teams = team_counts[team_counts >= min_matches_per_team].index.tolist()
            combined_df = combined_df[
                combined_df['home_team_id'].isin(valid_teams) &
                combined_df['away_team_id'].isin(valid_teams)
            ]
        
        logger.info(f"Combined {len(combined_df)} total matches from {len(dfs)} files")
        return combined_df
    
    def _load_from_batch_csv_files(self, league_code: str, league_name: str) -> Optional[pd.DataFrame]:
        """
        Load data from CSV files in:
        1. New structure: data/1_data_ingestion/Historical Match_Odds_Data/{session_folder}/{league_code}/
        2. Moved batch folders: data/1_data_ingestion/Historical Match_Odds_Data/batch_*/
        3. Old structure: data/1_data_ingestion/batch_*/ (for backward compatibility)
        
        Args:
            league_code: League code (e.g., "E0")
            league_name: League name (e.g., "Premier League")
        
        Returns:
            DataFrame with all matches from CSV files, or None if no files found
        """
        import glob
        from pathlib import Path
        
        # Check both old batch folder structure and new Historical Match_Odds_Data structure
        base_dir = Path("data/1_data_ingestion")
        historical_data_dir = base_dir / "Historical Match_Odds_Data"
        
        csv_files = []
        
        # First, check new structure: Historical Match_Odds_Data/{session_folder}/{league_code}/
        if historical_data_dir.exists():
            for session_folder in historical_data_dir.iterdir():
                if session_folder.is_dir():
                    league_folder = session_folder / league_code
                    if league_folder.exists():
                        # Look for CSV files matching league code
                        pattern = f"{league_code}_*.csv"
                        found_files = list(league_folder.glob(pattern))
                        csv_files.extend(found_files)
            
            # Also check for batch folders that were moved to Historical Match_Odds_Data
            for folder in historical_data_dir.iterdir():
                if folder.is_dir() and folder.name.startswith("batch_"):
                    # Look for CSV files matching league code
                    pattern = f"{league_code}_*.csv"
                    found_files = list(folder.glob(pattern))
                    csv_files.extend(found_files)
        
        # Then, check old structure: data/1_data_ingestion/batch_*/
        if base_dir.exists():
            # Find all batch folders that contain this league's CSV files
            # Pattern: batch_*_{league_name}/
            league_name_safe = league_name.replace(' ', '_').replace('/', '_')
            league_name_safe = ''.join(c for c in league_name_safe if c.isalnum() or c in ('_', '-'))
            
            for folder in base_dir.iterdir():
                if folder.is_dir() and folder.name.startswith("batch_"):
                    # Look for CSV files matching league code
                    pattern = f"{league_code}_*.csv"
                    found_files = list(folder.glob(pattern))
                    csv_files.extend(found_files)
        
        if not csv_files:
            logger.warning(f"No CSV files found for league {league_code} in batch folders")
            return None
        
        # Load all CSV files
        dfs = []
        for csv_file in csv_files:
            try:
                # Try pandas read_csv with error handling for malformed files
                try:
                    # pandas >= 2.0
                    df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='utf-8')
                except TypeError:
                    # pandas < 2.0
                    try:
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='utf-8')
                    except Exception:
                        # Try with latin-1 encoding
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='latin-1')
            except Exception as e1:
                # Try with different encoding
                try:
                    try:
                        df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='latin-1')
                    except TypeError:
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='latin-1')
                except Exception as e2:
                    logger.error(f"Error loading {csv_file}: {e1} and {e2}")
                    continue  # Skip this file and continue with next
                
                # Extract season from filename (e.g., E0_1920.csv -> 1920)
                season = csv_file.stem.split('_')[-1] if '_' in csv_file.stem else None
                
                # Keep original column names (Date, HomeTeam, AwayTeam, etc.) to match _matches_to_dataframe format
                # Add season column
                if season:
                    df['season'] = season
                
                # Parse date - keep original 'Date' column name
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
                
                # Filter out invalid dates
                df = df[df['Date'].notna()]
                
                # Filter out rows with missing critical data (using original column names)
                df = df[df['HomeTeam'].notna() & df['AwayTeam'].notna()]
                df = df[df['FTHG'].notna() & df['FTAG'].notna()]
                
                if len(df) > 0:
                    dfs.append(df)
                    logger.info(f"Loaded {len(df)} matches from {csv_file.name}")
            except Exception as e:
                logger.error(f"Error loading {csv_file}: {e}", exc_info=True)
                continue
        
        if not dfs:
            logger.warning(f"No valid data loaded from CSV files for league {league_code}")
            return None
        
        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by date (using original 'Date' column name)
        if 'Date' in combined_df.columns:
            combined_df = combined_df.sort_values('Date')
        
        logger.info(f"Loaded {len(combined_df)} total matches from {len(dfs)} CSV files for league {league_code}")
        return combined_df


def prepare_training_data(
    db: Session,
    league_codes: Optional[List[str]] = None,
    output_format: str = "both"
) -> Dict:
    """
    Convenience function to prepare training data
    
    Args:
        db: Database session
        league_codes: List of league codes (None = all)
        output_format: "csv", "parquet", or "both"
    
    Returns:
        Preparation statistics
    """
    service = DataPreparationService(db)
    
    if league_codes:
        results = []
        for code in league_codes:
            results.append(service.prepare_league_data(code, format=output_format))
        return {"leagues": results}
    else:
        return service.prepare_all_leagues(format=output_format)


```


Checking for other places that instantiate `DataPreparationService` with an explicit output directory:



All instances use the default output directory, so the change applies. Verifying the update is complete:



Updated the data cleaning & ETL pipeline to save files in the `Historical Match_Odds_Data` subdirectory.

## Changes Made:

**File:** `2_Backend_Football_Probability_Engine/app/services/data_preparation.py`

- Updated the default output directory from `data/2_Cleaned_data` to `data/2_Cleaned_data/Historical Match_Odds_Data`
- Updated the docstring to reflect the new default path

## Result:

When you run the pipeline, cleaned data files will now be saved to:
```
F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data\Historical Match_Odds_Data\
```

Instead of directly to:
```
F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data\
```

This matches the structure used by the data ingestion service (`_save_cleaned_csv_file`), keeping all cleaned historical match odds data in the same subdirectory.

The change is backward compatible—if code explicitly passes an `output_dir` parameter, it will use that instead of the default.

```plaintext
F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data\Historical Match_Odds_Data\
```

```plaintext
F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine\data\2_Cleaned_data\
```

---

**User**

fix this error first {ipeline Execution Summary

Data downloaded: 0 matches(I1)

Warnings:

Error downloading I1 season 2526: HTTPSConnectionPool(host='www.football-data.co.uk', port=443): Max retries exceeded with url: /mmz4281/2526/I1.csv (Caused by NameResolutionError("HTTPSConnection(host='www.football-data.co.uk', port=443): Failed to resolve 'www.football-data.co.uk' ([Errno 11001] getaddrinfo failed)"))

Error downloading I1 season 2425: HTTPSConnectionPool(host='www.football-data.co.uk', port=443): Max retries exceeded with url: /mmz4281/2425/I1.csv (Caused by NameResolutionError("HTTPSConnection(host='www.football-data.co.uk', port=443): Failed to resolve 'www.football-data.co.uk' ([Errno 11001] getaddrinfo failed)"))

Error downloading I1 season 2324: HTTPSConnectionPool(host='www.football-data.co.uk', port=443): Max retries exceeded with url: /mmz4281/2324/I1.csv (Caused by NameResolutionError("HTTPSConnection(host='www.football-data.co.uk', port=443): Failed to resolve 'www.football-data.co.uk' ([Errno 11001] getaddrinfo failed)"))

Executed: 10/01/2026, 10:42:15}{Pipeline Execution Summary

Data downloaded: 186 matches(I1)

Warnings:

Error downloading I1 season 2425: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

Error downloading I1 season 2324: HTTPSConnectionPool(host='www.football-data.co.uk', port=443): Max retries exceeded with url: /mmz4281/2324/I1.csv (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1077)')))

Error downloading I1 season 2223: HTTPSConnectionPool(host='www.football-data.co.uk', port=443): Max retries exceeded with url: /mmz4281/2223/I1.csv (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1077)')))

Executed: 10/01/2026, 09:59:27}  , then analyse this  info based on your knowlegede of the application {Yes. API-Football provides several high-value datasets that can materially improve probability estimation, reduce uncertainty, and enhance your existing tables (team_form, team_injuries, and downstream probability outputs).



Below is a structured, model-oriented breakdown of what you can extract from API-Football, how it maps to your schema, and how it improves your probability engine.



1. Direct Probability Signals from API-Football

1.1 Fixture-Level Statistics (High Impact)



Endpoint: /fixtures/statistics



Key fields



Shots on target



Total shots



Possession %



Corners



Fouls



Expected pressure indicators



How it enhances probability



Improves attack_form beyond goals



Reduces variance in low-scoring teams



Strong early indicator for draw likelihood



Schema extension (recommended)



ALTER TABLE team_form ADD COLUMN x_pressure DOUBLE PRECISION;



2. Expected Goals (xG) – Critical for Calibration



Endpoint: /fixtures/statistics (league-dependent)



Key fields



Expected Goals (xG)



Shot quality proxies



Probability value



Corrects scoreline randomness



Stabilizes Poisson & Dixon–Coles inputs



Improves overround-adjusted probabilities



Enhancement



ALTER TABLE team_form ADD COLUMN xg_for DOUBLE PRECISION;

ALTER TABLE team_form ADD COLUMN xg_against DOUBLE PRECISION;



3. Team Form Endpoint (Pre-Aggregated)



Endpoint: /teams/statistics



What it gives



Last 5 / 10 match form



Home vs away splits



Goals per match



Clean sheets, failed-to-score %



Why this matters



Saves ETL complexity



Acts as cross-check against your computed form



Useful for model confidence scoring



4. Injuries & Squad Availability (Structured)



Endpoint: /injuries



Key enhancements



Player status per fixture



Position classification



Return dates



Schema alignment

Directly feeds:



attackers_missing



midfielders_missing



defenders_missing



goalkeepers_missing



injury_severity



Advantage



No scraping



Lower legal and operational risk



5. Lineups & Starting XI (Pre-Match Signal)



Endpoint: /fixtures/lineups



High-impact features



Confirmed starters



Formation changes



GK availability



Last-minute withdrawals



Probability impact



Adjusts probabilities 1–2 hours before kickoff



Especially important for draw suppression or late win bias



Suggested table



CREATE TABLE fixture_lineups (

  fixture_id INTEGER,

  team_id INTEGER,

  formation TEXT,

  starters_count INTEGER,

  is_confirmed BOOLEAN,

  captured_at TIMESTAMPTZ DEFAULT NOW()

);



6. Head-to-Head (H2H) – Controlled Use



Endpoint: /fixtures/headtohead



Use carefully



Small-sample bias



Psychological/contextual signal



Correct usage



Cap contribution ≤ 5%



Only recent (≤ 5 years)



Use as confidence modifier, not base probability



7. Discipline & Referee Effects (Underrated)



Endpoints



/fixtures/statistics



/fixtures/events



Extractable signals



Cards per match



Fouls committed



Penalties awarded



Probability benefit



Red cards increase goal variance



Penalty frequency impacts draw rates



8. Venue & Home Advantage Calibration



Endpoint: /fixtures



Data



Stadium



City



Attendance (league-dependent)



Usage



Venue-specific home advantage



Crowd pressure modifier



Travel fatigue proxy



9. Recommended API-Football Feature Priority (ROI-Based)

Priority	Feature	Impact

1	xG / shots on target	Very High

2	Lineups	Very High

3	Injuries	High

4	Home/away splits	High

5	Discipline stats	Medium

6	H2H	Low (controlled)

10. How This Enhances Your Existing Tables

team_form



Replace goal-only form with chance-quality-adjusted form



Add pressure & discipline features



team_injuries



Improve timeliness & accuracy



Enable pre-kickoff probability updates



Probability Engine



Better draw calibration



Reduced late-line drift



Stronger confidence bounds



11. Strong Recommendation



Use API-Football as a live enhancement layer, not your historical ground truth.



Historical → CSV / open data



Live adjustments → API-Football



Final probabilities → calibrated blend



This preserves auditability and model stability.}

---

**Cursor**


Fixing the download errors first, then analyzing the API-Football integration. Examining the data ingestion code to add better error handling and retries:



Examining the download function to add retry logic:



Adding retry logic with exponential backoff and improved error handling:


```python
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
import time as time_module
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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


```

```python
    def _create_session_with_retries(self) -> requests.Session:
        """
        Create a requests session with retry strategy and proper headers
        
        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=5,  # Total number of retries
            backoff_factor=2,  # Exponential backoff: 2s, 4s, 8s, 16s, 32s
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["GET"],  # Only retry GET requests
            respect_retry_after_header=True  # Respect Retry-After header
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set user-agent to avoid blocking
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return session
    
    def download_from_football_data(
        self,
        league_code: str,
        season: str
    ) -> str:
        """
        Download CSV from football-data.co.uk with retry logic and error handling
        
        Args:
            league_code: League code (e.g., 'E0' for Premier League)
            season: Season code (e.g., '2324' for 2023-24)
        
        Returns:
            CSV content as string (UTF-8 encoded)
        
        Raises:
            requests.RequestException: If download fails after all retries
        """
        # Extra Leagues (available from 2012/13 onwards) use same URL structure
        # But some leagues may not exist at all - try standard URL first
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
        
        # Use SSL verification setting from config (default to True if not set)
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        
        # Create session with retries
        session = self._create_session_with_retries()
        
        # Retry configuration for manual retries (for DNS/SSL errors)
        max_manual_retries = 3
        retry_delays = [5, 15, 30]  # Progressive delays: 5s, 15s, 30s
        
        last_exception = None
        
        for attempt in range(max_manual_retries):
            try:
                # Use longer timeout for initial connection
                timeout = (10, 30)  # (connect timeout, read timeout)
                
                logger.debug(f"Downloading {league_code} season {season} (attempt {attempt + 1}/{max_manual_retries})")
                response = session.get(url, timeout=timeout, verify=verify_ssl)
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
                content_type = response.headers.get('Content-Type', '').l
```

