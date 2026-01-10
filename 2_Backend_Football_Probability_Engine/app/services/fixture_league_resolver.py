"""
League resolution for fixtures
Handles both international and club games
"""
from sqlalchemy.orm import Session
from app.db.models import League, Team
from app.services.team_resolver import resolve_team_safe, create_team_if_not_exists
import logging

logger = logging.getLogger(__name__)

# Country to league code mapping (top tier default)
# This is used as fallback when team lookup fails
COUNTRY_TO_LEAGUE_CODE = {
    "Spain": "SP1",
    "England": "E0",
    "Italy": "I1",
    "Turkey": "T1",
    "Greece": "G1",
    "Portugal": "P1",
    "France": "F1",
    "Germany": "D1",
    "Netherlands": "N1",
    "Scotland": "SC0",
    "Belgium": "B1",
    "Austria": "A1",
    "Sweden": "SW1",
    "Norway": "NO1",
    "Denmark": "DK1",
    "Cyprus": "CYP1",  # Cypriot First Division
    "Poland": "PL1",   # Ekstraklasa
    "Czech Republic": "CZE1",
    "Croatia": "CRO1",
    "Serbia": "SRB1",
    "Romania": "RO1",
    "Russia": "RUS1",
    "Ukraine": "UKR1",
    "Ireland": "IRL1",
    # Add more as needed
}


def get_or_create_int_league(db: Session) -> League:
    """
    Get or create INT league for international matches
    
    Returns:
        League object for INT league
    """
    int_league = db.query(League).filter(League.code == 'INT').first()
    if not int_league:
        logger.warning("INT league not found. Creating it now...")
        int_league = League(
            code='INT',
            name='International Matches',
            country='World',
            tier=0,  # Special tier for international
            is_active=True
        )
        db.add(int_league)
        db.commit()
        db.refresh(int_league)
        logger.info(f"Created INT league with ID: {int_league.id}")
    return int_league


def infer_league_from_fixture(
    db: Session,
    fixture_type: str = None,
    country: str = None,
    home_team: str = None,
    away_team: str = None
) -> League:
    """
    Infer league for a fixture
    
    Priority:
    1. If International → INT league
    2. Try team lookup → use team's league
    3. Country mapping → infer from country
    4. Default → raise error
    
    Args:
        db: Database session
        fixture_type: "International" or "Club" (or None)
        country: Country name (e.g., "Spain", "England")
        home_team: Home team name
        away_team: Away team name
    
    Returns:
        League object
    """
    # Step 1: International games
    if fixture_type and fixture_type.lower() == "international":
        return get_or_create_int_league(db)
    
    # Step 2: Try team lookup (most accurate)
    if home_team:
        home_team_obj = resolve_team_safe(db, home_team, None)
        if home_team_obj:
            league = db.query(League).filter(League.id == home_team_obj.league_id).first()
            if league:
                logger.info(f"Inferred league {league.code} from home team {home_team}")
                return league
    
    if away_team:
        away_team_obj = resolve_team_safe(db, away_team, None)
        if away_team_obj:
            league = db.query(League).filter(League.id == away_team_obj.league_id).first()
            if league:
                logger.info(f"Inferred league {league.code} from away team {away_team}")
                return league
    
    # Step 3: Country mapping (fallback)
    if country:
        league_code = COUNTRY_TO_LEAGUE_CODE.get(country)
        if league_code:
            league = db.query(League).filter(League.code == league_code).first()
            if league:
                logger.info(f"Inferred league {league_code} from country {country}")
                return league
    
    # Step 4: Try to infer country from team names (heuristic)
    # Some team names contain location hints (e.g., "Apollon Limassol" -> Cyprus)
    inferred_country = None
    if home_team:
        home_lower = home_team.lower()
        # Common location patterns in team names
        location_hints = {
            "limassol": "Cyprus",
            "nicosia": "Cyprus",
            "pafos": "Cyprus",
            "larnaca": "Cyprus",
            "athens": "Greece",
            "thessaloniki": "Greece",
            "istanbul": "Turkey",
            "ankara": "Turkey",
            "lisbon": "Portugal",
            "porto": "Portugal",
            "madrid": "Spain",
            "barcelona": "Spain",
            "london": "England",
            "manchester": "England",
            "milan": "Italy",
            "rome": "Italy",
            "paris": "France",
            "lyon": "France",
            "munich": "Germany",
            "berlin": "Germany",
        }
        for hint, country_name in location_hints.items():
            if hint in home_lower:
                inferred_country = country_name
                logger.info(f"Inferred country {country_name} from team name hint '{hint}' in {home_team}")
                break
    
    if inferred_country:
        league_code = COUNTRY_TO_LEAGUE_CODE.get(inferred_country)
        if league_code:
            league = db.query(League).filter(League.code == league_code).first()
            if league:
                logger.info(f"Inferred league {league_code} from team name hint")
                return league
    
    # Step 5: Auto-create league for unknown country (last resort)
    # Create a generic league with country name
    if country:
        # Try to create league with country code
        country_code = country[:3].upper() + "1"  # e.g., "Cyprus" -> "CYP1"
        existing_league = db.query(League).filter(League.code == country_code).first()
        if existing_league:
            logger.info(f"Found existing league {country_code} for country {country}")
            return existing_league
        
        # Create new league
        logger.warning(f"Auto-creating league {country_code} for unknown country: {country}")
        new_league = League(
            code=country_code,
            name=f"{country} League",
            country=country,
            tier=1,
            is_active=True
        )
        db.add(new_league)
        db.commit()
        db.refresh(new_league)
        logger.info(f"Created new league {country_code} ({new_league.name}) for country {country}")
        return new_league
    
    # Step 6: Final fallback - use INT league (treat as unknown/international)
    logger.warning(f"Could not infer league for fixture: type={fixture_type}, country={country}, teams=({home_team}, {away_team}). Using INT league as fallback.")
    return get_or_create_int_league(db)


def resolve_fixture_teams(
    db: Session,
    home_team: str,
    away_team: str,
    league: League
) -> tuple[Team, Team]:
    """
    Resolve or create teams for a fixture
    
    Args:
        db: Database session
        home_team: Home team name
        away_team: Away team name
        league: League object
    
    Returns:
        Tuple of (home_team_obj, away_team_obj)
    """
    home_team_obj = create_team_if_not_exists(db, home_team, league.id)
    away_team_obj = create_team_if_not_exists(db, away_team, league.id)
    
    return home_team_obj, away_team_obj

