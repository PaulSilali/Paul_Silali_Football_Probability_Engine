"""
Team Name Resolution Service

Resolves team names to canonical database entries using fuzzy matching
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from difflib import SequenceMatcher
import re
from app.db.models import Team


# Common team name aliases and variations
TEAM_ALIASES = {
    # Premier League
    "manchester united": ["man united", "man u", "manchester utd", "man utd"],
    "manchester city": ["man city", "mancity", "manchester c"],
    "tottenham hotspur": ["tottenham", "spurs", "tottenham h"],
    "brighton & hove albion": ["brighton", "brighton hove", "brighton albion"],
    "wolverhampton wanderers": ["wolves", "wolverhampton", "wolves fc"],
    "west ham united": ["west ham", "west ham u", "west ham utd"],
    "newcastle united": ["newcastle", "newcastle utd", "newcastle u"],
    "leicester city": ["leicester", "leicester c"],
    "norwich city": ["norwich", "norwich c"],
    "southampton": ["southampton fc"],
    "crystal palace": ["palace", "crystal p"],
    "aston villa": ["villa", "aston v"],
    "everton": ["everton fc"],
    "burnley": ["burnley fc"],
    "watford": ["watford fc"],
    "bournemouth": ["bournemouth fc", "afc bournemouth"],
    
    # La Liga (Spain) - SP1
    # Canonical names should match database canonical_name (normalized)
    # Aliases include all variations from Football-Data.org and other sources
    "club atletico de madrid": ["atletico madrid", "atletico", "atletico m", "atletico mad", "atletico de madrid", "atletico madrid cf"],
    "real madrid cf": ["real madrid", "real m", "real mad", "real madrid cf", "real madrid club"],
    "fc barcelona": ["barcelona", "barcelona fc", "barca", "fc barcelona", "barcelona cf"],
    "sevilla fc": ["sevilla", "sevilla fc", "sevilla club"],
    "valencia cf": ["valencia", "valencia cf", "valencia club"],
    "villarreal cf": ["villarreal", "villarreal cf", "villarreal club"],
    "real sociedad de futbol": ["real sociedad", "real s", "real sociedad de futbol", "real sociedad cf", "real sociedad club"],
    "athletic club": ["athletic bilbao", "athletic", "athletic club", "athletic b", "athletic bilbao fc"],
    "rcd mallorca": ["mallorca", "rcd mallorca", "mallorca cf", "real mallorca"],
    "ca osasuna": ["osasuna", "ca osasuna", "osasuna cf", "club atletico osasuna"],
    "rayo vallecano de madrid": ["rayo vallecano", "rayo", "rayo vallecano de madrid", "rayo vallecano cf"],
    "deportivo alaves": ["alaves", "deportivo alaves", "alaves cf", "deportivo alaves cf"],
    "cadiz cf": ["cadiz", "cadiz cf", "cadiz club"],
    "getafe cf": ["getafe", "getafe cf", "getafe club"],
    "ud almeria": ["almeria", "ud almeria", "almeria cf", "union deportiva almeria"],
    "ud las palmas": ["las palmas", "ud las palmas", "las palmas cf", "union deportiva las palmas"],
    "rc celta de vigo": ["celta vigo", "celta", "rc celta de vigo", "celta de vigo", "celta vigo cf"],
    "real betis balompie": ["real betis", "betis", "real betis balompie", "betis cf", "real betis cf"],
    "girona fc": ["girona", "girona fc", "girona cf", "girona club"],
    "granada cf": ["granada", "granada cf", "granada club"],
    
    # Additional mappings for common variations
    "atletico madrid": ["club atletico de madrid", "atletico madrid", "atletico"],
    "real madrid": ["real madrid cf", "real madrid"],
    "barcelona": ["fc barcelona", "barcelona"],
    "sevilla": ["sevilla fc", "sevilla"],
    "valencia": ["valencia cf", "valencia"],
    "villarreal": ["villarreal cf", "villarreal"],
    "real sociedad": ["real sociedad de futbol", "real sociedad"],
    "athletic bilbao": ["athletic club", "athletic bilbao", "athletic"],
    "mallorca": ["rcd mallorca", "mallorca"],
    "osasuna": ["ca osasuna", "osasuna"],
    "rayo vallecano": ["rayo vallecano de madrid", "rayo vallecano", "rayo"],
    "alaves": ["deportivo alaves", "alaves"],
    "cadiz": ["cadiz cf", "cadiz"],
    "getafe": ["getafe cf", "getafe"],
    "almeria": ["ud almeria", "almeria"],
    "las palmas": ["ud las palmas", "las palmas"],
    "celta vigo": ["rc celta de vigo", "celta vigo", "celta"],
    "real betis": ["real betis balompie", "real betis", "betis"],
    "girona": ["girona fc", "girona"],
    "granada": ["granada cf", "granada"],
    
    # Bundesliga (Germany) - D1
    # Canonical names should match database canonical_name (normalized)
    # Aliases include all variations from Football-Data.org and other sources
    # Note: Umlauts (ö, ü, ä) are preserved in normalization, but aliases include both forms
    "fc bayern munchen": ["fc bayern munich", "bayern munich", "bayern munchen", "bayern", "bayern m", "fc bayern", "fc bayern m", "fc bayern münchen"],
    "borussia dortmund": ["dortmund", "bvb", "borussia d", "bvb dortmund", "borussia dortmund"],
    "rb leipzig": ["leipzig", "rb l", "rasenballsport leipzig", "rb leipzig", "red bull leipzig"],
    "bayer 04 leverkusen": ["bayer leverkusen", "leverkusen", "bayer l", "bayer 04", "bayer leverkusen", "bayer", "bayer 04 leverkusen"],
    "borussia monchengladbach": ["borussia mönchengladbach", "gladbach", "borussia m", "m'gladbach", "borussia mg", "mönchengladbach", "monchengladbach", "borussia mönchengladbach", "mgladbach"],
    "eintracht frankfurt": ["frankfurt", "eintracht f", "eintracht", "eintracht frankfurt", "frankfurt eintracht", "eintracht frankfurt"],
    "fc st pauli 1910": ["st pauli", "fc st pauli", "fc st pauli 1910", "st pauli 1910", "st. pauli", "fc st. pauli", "fc st. pauli 1910"],
    "vfb stuttgart": ["stuttgart", "vfb s", "vfb stuttgart", "vfb", "stuttgart vfb", "vfb stuttgart"],
    "fc augsburg": ["augsburg", "fc a", "fc augsburg", "augsburg fc"],
    "1 fsv mainz 05": ["mainz", "mainz 05", "1. fsv mainz 05", "1 fsv mainz", "fsv mainz", "mainz 05", "1. fsv mainz", "1 fsv mainz 05"],
    "tsg 1899 hoffenheim": ["hoffenheim", "tsg hoffenheim", "tsg 1899", "1899 hoffenheim", "tsg", "hoffenheim 1899", "tsg 1899 hoffenheim"],
    "sc freiburg": ["freiburg", "sc f", "sc freiburg", "freiburg sc"],
    "1 fc heidenheim 1846": ["heidenheim", "1. fc heidenheim 1846", "fc heidenheim", "heidenheim 1846", "1 fc heidenheim", "1. fc heidenheim", "1 fc heidenheim 1846"],
    "sv werder bremen": ["werder bremen", "werder", "sv werder", "sv werder bremen", "bremen", "werder b"],
    "vfl wolfsburg": ["wolfsburg", "vfl w", "vfl wolfsburg", "vfl", "wolfsburg vfl"],
    "1 fc union berlin": ["union berlin", "1. fc union berlin", "fc union berlin", "union", "1 fc union berlin", "1. fc union", "1 fc union berlin"],
    "vfl bochum 1848": ["bochum", "vfl bochum", "vfl bochum 1848", "bochum 1848", "1. fc bochum", "vfl bochum"],
    "holstein kiel": ["kiel", "holstein k", "holstein kiel", "holstein"],
    "1 fc koln": ["1 fc köln", "fc köln", "koln", "köln", "1. fc köln", "1 fc koln", "1. fc koln", "fc koln", "1. fc köln"],
    "sv darmstadt 98": ["darmstadt", "sv darmstadt", "sv darmstadt 98", "darmstadt 98", "sv darmstadt 98"],
    
    # Serie A
    "ac milan": ["milan", "ac m", "a.c. milan"],
    "inter milan": ["inter", "inter m", "inter milano"],
    "juventus": ["juventus fc", "juve"],
    "as roma": ["roma", "as r", "a.s. roma"],
    "napoli": ["napoli fc", "ssc napoli"],
    "atalanta": ["atalanta bc", "atalanta bergamo"],
    
    # Ligue 1
    "paris saint-germain": ["psg", "paris sg", "paris s-g"],
    "olympique lyonnais": ["lyon", "ol lyonnais", "ol"],
    "olympique marseille": ["marseille", "om", "olympique m"],
    "monaco": ["as monaco", "monaco fc"],
    
    # League Two (English Football League)
    "milton keynes dons": ["mk dons", "mk", "milton keynes", "mk dons fc"],
    "afc wimbledon": ["wimbledon", "afc w", "wimbledon fc"],
    "newport county": ["newport", "newport c", "newport county afc"],
    "notts county": ["notts", "notts c", "notts county fc"],
    "tranmere rovers": ["tranmere", "tranmere r", "tranmere rovers fc"],
    "port vale": ["port v", "vale", "port vale fc"],
    "grimsby town": ["grimsby", "grimsby t", "grimsby town fc"],
    "crewe alexandra": ["crewe", "crewe a", "crewe alexandra fc"],
    "swindon town": ["swindon", "swindon t", "swindon town fc"],
    "walsall": ["walsall fc"],
    "morecambe": ["morecambe fc"],
    "carlisle united": ["carlisle", "carlisle u", "carlisle united fc"],
    "colchester united": ["colchester", "colchester u", "colchester united fc"],
    "doncaster rovers": ["doncaster", "doncaster r", "doncaster rovers fc"],
    "accrington stanley": ["accrington", "accrington s", "accrington stanley fc"],
    "barrow": ["barrow afc", "barrow fc"],
    "bradford city": ["bradford", "bradford c", "bradford city afc"],
    "cheltenham town": ["cheltenham", "cheltenham t", "cheltenham town fc"],
    "fleetwood town": ["fleetwood", "fleetwood t", "fleetwood town fc"],
    "gillingham": ["gillingham fc"],
    "harrogate town": ["harrogate", "harrogate t", "harrogate town afc"],
    "salford city": ["salford", "salford c", "salford city fc"],
    
    # Eredivisie (Netherlands) - N1
    # Canonical names should match database canonical_name (normalized)
    # Aliases include all variations from Football-Data.org and other sources
    # Note: Both full names and abbreviations are included to handle all cases
    "afc ajax": ["ajax", "ajax amsterdam", "ajax a", "afc ajax amsterdam"],
    "psv eindhoven": ["psv", "psv e", "psv eindhoven", "psv eindhoven fc"],
    "feyenoord rotterdam": ["feyenoord", "feyenoord r", "feyenoord rotterdam", "feyenoord fc"],
    "az alkmaar": ["az", "az alkmaar", "alkmaar", "az alkmaar fc"],
    "fc utrecht": ["utrecht", "fc u", "fc utrecht", "utrecht fc"],
    "sbv vitesse": ["vitesse", "vitesse arnhem", "sbv v", "vitesse arnhem", "sbv vitesse arnhem"],
    "sc heerenveen": ["heerenveen", "sc h", "sc heerenveen", "heerenveen fc"],
    "nec nijmegen": ["nec", "nec nijmegen", "nijmegen", "nec nijmegen fc"],
    "sparta rotterdam": ["sparta", "sparta rotterdam", "sparta r", "sparta rotterdam fc"],
    "fc twente 65": ["fc twente '65", "twente", "fc twente", "twente '65", "fc twente 65", "twente 65"],
    "pec zwolle": ["zwolle", "pec z", "pec zwolle", "zwolle fc"],
    "fortuna sittard": ["fortuna", "fortuna s", "fortuna sittard", "fortuna sittard fc"],
    "go ahead eagles": ["go ahead", "go ahead eagles", "gae", "go ahead eagles deventer"],
    "rkc waalwijk": ["waalwijk", "rkc", "rkc waalwijk", "rkc waalwijk fc"],
    "sbv excelsior": ["excelsior", "sbv e", "sbv excelsior", "excelsior rotterdam", "excelsior fc"],
    "heracles almelo": ["heracles", "heracles a", "heracles almelo", "heracles almelo fc"],
    "fc volendam": ["volendam", "fc v", "fc volendam", "volendam fc"],
    "almere city fc": ["almere city", "almere", "almere city fc", "almere fc"],
    
    # Additional mappings for common Football-Data.org variations
    # These handle cases where database might have different canonical names
    "nec": ["nec nijmegen", "nec", "nijmegen"],  # If DB has "nec" as canonical
    "ajax": ["afc ajax", "ajax", "ajax amsterdam"],  # If DB has "ajax" as canonical
    "psv": ["psv eindhoven", "psv"],  # If DB has "psv" as canonical
    "feyenoord": ["feyenoord rotterdam", "feyenoord"],  # If DB has "feyenoord" as canonical
    "az": ["az alkmaar", "az"],  # If DB has "az" as canonical
    "utrecht": ["fc utrecht", "utrecht"],  # If DB has "utrecht" as canonical
    "vitesse": ["sbv vitesse", "vitesse"],  # If DB has "vitesse" as canonical
    "heerenveen": ["sc heerenveen", "heerenveen"],  # If DB has "heerenveen" as canonical
    "sparta": ["sparta rotterdam", "sparta"],  # If DB has "sparta" as canonical
    "twente": ["fc twente 65", "fc twente '65", "twente"],  # If DB has "twente" as canonical
    "zwolle": ["pec zwolle", "zwolle"],  # If DB has "zwolle" as canonical
    "fortuna": ["fortuna sittard", "fortuna"],  # If DB has "fortuna" as canonical
    "go ahead": ["go ahead eagles", "go ahead"],  # If DB has "go ahead" as canonical
    "rkc": ["rkc waalwijk", "rkc"],  # If DB has "rkc" as canonical
    "excelsior": ["sbv excelsior", "excelsior"],  # If DB has "excelsior" as canonical
    "heracles": ["heracles almelo", "heracles"],  # If DB has "heracles" as canonical
    "volendam": ["fc volendam", "volendam"],  # If DB has "volendam" as canonical
    "almere city": ["almere city fc", "almere city"],  # If DB has "almere city" as canonical
    
    # Allsvenskan (Sweden) - SWE1
    "malmo ff": ["malmo", "malmo ff", "malmö ff"],
    "aik": ["aik stockholm", "aik", "aik s"],
    "ifk goteborg": ["goteborg", "ifk g", "ifk göteborg", "ifk gothenburg"],
    "hammarby": ["hammarby if", "hammarby", "hammarby if"],
    "djurgarden": ["djurgarden", "djurgårdens if", "djurgårdens", "djurgarden if"],
    "ifk norrkoping": ["norrkoping", "ifk n", "ifk norrköping"],
    "kalmar ff": ["kalmar", "kalmar ff", "kalmar f"],
    "orebro": ["orebro sk", "orebro", "örebro"],
    "hacken": ["bk hacken", "hacken", "bk h"],
    "elfsborg": ["if elfsborg", "elfsborg", "if e"],
    "sundsvall": ["gif sundsvall", "sundsvall", "gif s"],
    "ostersunds": ["ostersunds fk", "ostersunds", "östersunds"],
    "trelleborg": ["trelleborgs ff", "trelleborg", "trelleborgs"],
    "halmstad": ["halmstads bk", "halmstad", "halmstads"],
    "ifk varnamo": ["varnamo", "ifk v", "ifk varnamo"],
    "dalkurd": ["dalkurd ff", "dalkurd", "dalkurd f"],
    "sirius": ["ik sirius", "sirius", "ik s"],
    "varberg": ["varbergs bois", "varberg", "varbergs"],
    "degefors": ["degefors if", "degefors", "degefors if"],
    "hammarby talang": ["hammarby t", "hammarby talang"],
}


def normalize_team_name(name: str) -> str:
    """
    Normalize team name for matching
    
    - Convert to lowercase
    - Remove extra whitespace
    - Remove common suffixes (FC, CF, etc.)
    - Remove special characters
    """
    # Convert to lowercase and strip
    normalized = name.lower().strip()
    
    # Remove common suffixes
    suffixes = [" fc", " cf", " bc", " ac", " united", " utd", " city", " town"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    
    # Remove special characters except spaces and hyphens
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def similarity_score(name1: str, name2: str) -> float:
    """
    Calculate similarity score between two team names
    
    Returns:
        Float between 0.0 and 1.0 (1.0 = identical)
    """
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return 1.0
    
    # Check aliases
    for canonical, aliases in TEAM_ALIASES.items():
        if norm1 == canonical or norm1 in aliases:
            if norm2 == canonical or norm2 in aliases:
                return 0.95  # High confidence alias match
    
    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def resolve_team(
    db: Session,
    team_name: str,
    league_id: Optional[int] = None,
    min_similarity: float = 0.7
) -> Optional[Tuple[Team, float]]:
    """
    Resolve team name to Team model using fuzzy matching
    
    Args:
        db: Database session
        team_name: Input team name
        league_id: Optional league ID to narrow search
        min_similarity: Minimum similarity score (0.0-1.0)
    
    Returns:
        Tuple of (Team, similarity_score) or None if not found
    """
    if not team_name or len(team_name.strip()) < 2:
        return None
    
    # Build query
    query = db.query(Team)
    if league_id:
        query = query.filter(Team.league_id == league_id)
    
    # Get all teams
    teams = query.all()
    
    if not teams:
        return None
    
    # Calculate similarity scores
    matches = []
    for team in teams:
        # Try canonical name
        score1 = similarity_score(team_name, team.canonical_name)
        # Try display name
        score2 = similarity_score(team_name, team.name)
        
        best_score = max(score1, score2)
        if best_score >= min_similarity:
            matches.append((team, best_score))
    
    if not matches:
        return None
    
    # Return best match
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[0]


def resolve_team_safe(
    db: Session,
    team_name: str,
    league_id: Optional[int] = None
) -> Optional[Team]:
    """
    Resolve team name, returning Team or None
    
    Wrapper around resolve_team that only returns the Team object
    """
    result = resolve_team(db, team_name, league_id)
    return result[0] if result else None


def create_team_if_not_exists(
    db: Session,
    team_name: str,
    league_id: int
) -> Team:
    """
    Create a team if it doesn't exist, or return existing team
    
    Args:
        db: Database session
        team_name: Team name to create
        league_id: League ID
    
    Returns:
        Team object (newly created or existing)
    """
    if not team_name or len(team_name.strip()) < 2:
        raise ValueError(f"Invalid team name: {team_name}")
    
    # First try to resolve existing team
    existing = resolve_team_safe(db, team_name, league_id)
    if existing:
        return existing
    
    # Create new team
    canonical_name = normalize_team_name(team_name)
    
    # Check if team with same canonical name exists in this league
    existing_canonical = db.query(Team).filter(
        Team.league_id == league_id,
        Team.canonical_name == canonical_name
    ).first()
    
    if existing_canonical:
        return existing_canonical
    
    # Create new team
    new_team = Team(
        league_id=league_id,
        name=team_name.strip(),
        canonical_name=canonical_name,
        attack_rating=1.0,
        defense_rating=1.0,
        home_bias=0.0
    )
    db.add(new_team)
    db.flush()  # Flush to get the ID without committing
    
    logger.info(f"Created new team: {team_name} (canonical: {canonical_name}) in league_id {league_id}")
    
    return new_team


def search_teams(
    db: Session,
    query: str,
    league_id: Optional[int] = None,
    limit: int = 10
) -> List[Tuple[Team, float]]:
    """
    Search for teams matching a query string
    
    Returns:
        List of (Team, similarity_score) tuples, sorted by score
    """
    if not query or len(query.strip()) < 2:
        return []
    
    # Build database query
    db_query = db.query(Team)
    if league_id:
        db_query = db_query.filter(Team.league_id == league_id)
    
    teams = db_query.all()
    
    if not teams:
        return []
    
    # Calculate similarity scores
    matches = []
    for team in teams:
        score1 = similarity_score(query, team.canonical_name)
        score2 = similarity_score(query, team.name)
        best_score = max(score1, score2)
        
        if best_score > 0.3:  # Lower threshold for search
            matches.append((team, best_score))
    
    # Sort by score and return top results
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:limit]


def suggest_team_names(
    db: Session,
    team_name: str,
    league_id: Optional[int] = None,
    limit: int = 5
) -> List[str]:
    """
    Suggest team names similar to input
    
    Useful for autocomplete or "did you mean?" suggestions
    """
    matches = search_teams(db, team_name, league_id, limit)
    return [team.canonical_name for team, score in matches]


def validate_team_name(
    db: Session,
    team_name: str,
    league_id: Optional[int] = None
) -> dict:
    """
    Validate team name and return suggestions if not found
    
    Returns:
        Dict with:
        - isValid: bool
        - suggestions: List[str] (if not valid)
        - normalizedName: str (if valid)
        - team: Team (if valid)
    """
    result = resolve_team(db, team_name, league_id)
    
    if result:
        team, score = result
        return {
            "isValid": True,
            "normalizedName": team.canonical_name,
            "team": team,
            "confidence": score
        }
    else:
        suggestions = suggest_team_names(db, team_name, league_id)
        return {
            "isValid": False,
            "suggestions": suggestions
        }

