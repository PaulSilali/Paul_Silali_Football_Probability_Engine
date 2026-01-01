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
    
    # La Liga
    "atletico madrid": ["atletico", "atletico m", "atletico mad"],
    "real madrid": ["real madrid cf", "real m", "real mad"],
    "barcelona": ["barcelona fc", "barca", "fc barcelona"],
    "sevilla": ["sevilla fc"],
    "valencia": ["valencia cf"],
    "villarreal": ["villarreal cf"],
    "real sociedad": ["real s", "real sociedad"],
    "athletic bilbao": ["athletic", "athletic club", "athletic b"],
    
    # Bundesliga
    "bayern munich": ["bayern", "bayern m", "fc bayern"],
    "borussia dortmund": ["dortmund", "bvb", "borussia d"],
    "rb leipzig": ["leipzig", "rb l", "rasenballsport leipzig"],
    "bayer leverkusen": ["leverkusen", "bayer l"],
    "borussia monchengladbach": ["gladbach", "borussia m", "m'gladbach"],
    
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

