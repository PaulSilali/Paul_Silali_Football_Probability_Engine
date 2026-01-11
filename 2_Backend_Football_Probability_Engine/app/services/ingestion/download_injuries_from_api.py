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

