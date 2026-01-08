"""
Ingest head-to-head statistics from API-Football or similar sources

Database Storage:
- H2H statistics are saved to the 'h2h_draw_stats' table
- Table structure: team_home_id, team_away_id, matches_played, draw_count, avg_goals
- Each team pair has one record (unique constraint on team_home_id + team_away_id)
- CSV files are saved to: data/1_data_ingestion/Draw_structural/h2h_stats/
- Format: {league_code}_{season}_h2h_stats.csv (one file per league/season)
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, H2HDrawStats, League, Match
from typing import Optional, Dict, List
from pathlib import Path
import pandas as pd
import logging
import urllib3
from app.services.ingestion.draw_structural_validation import (
    DrawStructuralValidator,
    validate_before_insert
)
from app.config import settings

logger = logging.getLogger(__name__)

# Disable SSL warnings if verification is disabled
# Use getattr with default True to handle cases where attribute might not exist yet
if not getattr(settings, 'VERIFY_SSL', True):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def ingest_h2h_from_api_football(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Ingest H2H statistics from API-Football.
    
    Args:
        db: Database session
        home_team_id: Home team ID
        away_team_id: Away team ID
        api_key: API-Football API key (optional, can be from config)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        if not api_key:
            from app.config import settings
            api_key = getattr(settings, 'API_FOOTBALL_KEY', None)
        
        if not api_key:
            logger.warning("API-Football key not configured, skipping H2H ingestion")
            return {"success": False, "error": "API key not configured"}
        
        # Get team IDs from database
        home_team = db.query(Team).filter(Team.id == home_team_id).first()
        away_team = db.query(Team).filter(Team.id == away_team_id).first()
        
        if not home_team or not away_team:
            return {"success": False, "error": "Team not found"}
        
        # API-Football endpoint (example - adjust based on actual API)
        url = f"https://v3.football.api-sports.io/fixtures/headtohead"
        headers = {
            "x-apisports-key": api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        params = {
            "h2h": f"{home_team_id}-{away_team_id}"
        }
        
        verify_ssl = getattr(settings, 'VERIFY_SSL', True)
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=verify_ssl)
        response.raise_for_status()
        
        data = response.json()
        matches = data.get("response", [])
        
        if not matches:
            logger.info(f"No H2H matches found for teams {home_team_id} vs {away_team_id}")
            return {"success": False, "error": "No matches found"}
        
        # Calculate statistics
        matches_played = len(matches)
        draws = 0
        total_goals = 0
        
        for match in matches:
            home_goals = match.get("goals", {}).get("home", 0)
            away_goals = match.get("goals", {}).get("away", 0)
            
            if home_goals == away_goals:
                draws += 1
            
            total_goals += home_goals + away_goals
        
        avg_goals = total_goals / matches_played if matches_played > 0 else 0
        draw_rate = draws / matches_played if matches_played > 0 else 0.0
        
        # Validate H2H consistency
        context = f" (home_team_id={home_team_id}, away_team_id={away_team_id})"
        is_valid, error = DrawStructuralValidator.validate_h2h_consistency(
            matches_played, draws, draw_rate, context
        )
        if not is_valid:
            logger.error(f"Invalid H2H stats: {error}")
            return {"success": False, "error": error}
        
        # Insert or update
        existing = db.query(H2HDrawStats).filter(
            H2HDrawStats.team_home_id == home_team_id,
            H2HDrawStats.team_away_id == away_team_id
        ).first()
        
        if existing:
            existing.matches_played = matches_played
            existing.draw_count = draws
            existing.avg_goals = float(avg_goals)
        else:
            h2h = H2HDrawStats(
                team_home_id=home_team_id,
                team_away_id=away_team_id,
                matches_played=matches_played,
                draw_count=draws,
                avg_goals=float(avg_goals)
            )
            db.add(h2h)
        
        db.commit()
        
        logger.info(f"Ingested H2H stats: {home_team_id} vs {away_team_id} - {matches_played} matches, {draws} draws")
        
        return {
            "success": True,
            "matches_played": matches_played,
            "draw_count": draws,
            "avg_goals": float(avg_goals)
        }
    
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting H2H stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_h2h_csv(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    h2h_data: Dict
) -> Path:
    """
    Save CSV file with H2H statistics for a single team pair.
    Used for single H2H ingestion (not batch).
    
    Args:
        db: Database session
        home_team_id: Home team ID
        away_team_id: Away team ID
        h2h_data: Dictionary with H2H statistics
    
    Returns:
        Path to saved CSV file
    """
    try:
        # Get team names
        home_team = db.query(Team).filter(Team.id == home_team_id).first()
        away_team = db.query(Team).filter(Team.id == away_team_id).first()
        
        if not home_team or not away_team:
            raise ValueError("Teams not found")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/h2h_stats")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame([{
            "home_team_id": home_team_id,
            "home_team_name": home_team.name,
            "away_team_id": away_team_id,
            "away_team_name": away_team.name,
            "season": h2h_data.get("season", "ALL"),
            "matches_played": h2h_data.get("matches_played", 0),
            "draw_count": h2h_data.get("draw_count", 0),
            "draw_rate": h2h_data.get("draw_rate", 0.0),
            "avg_goals": h2h_data.get("avg_goals", 0.0)
        }])
        
        # Filename format: {home_team_id}_{away_team_id}_{season}_h2h_stats.csv
        season_str = h2h_data.get("season", "ALL")
        filename = f"{home_team_id}_{away_team_id}_{season_str}_h2h_stats.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved H2H stats CSV: {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving H2H stats CSV: {e}", exc_info=True)
        raise


def _save_h2h_csv_batch(
    db: Session,
    league_code: str,
    league_name: str,
    season: str,
    h2h_records: List[Dict]
) -> Path:
    """
    Save CSV file with all H2H statistics for a league/season.
    One CSV file contains all team pairs for that league/season combination.
    
    Args:
        db: Database session
        league_code: League code
        league_name: League name
        season: Season identifier
        h2h_records: List of dictionaries with H2H statistics for all team pairs
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not h2h_records:
            raise ValueError("No H2H records to save")
        
        # Create DataFrame from all records
        df = pd.DataFrame(h2h_records)
        
        # Filename format: {league_code}_{season}_h2h_stats.csv
        filename = f"{league_code}_{season}_h2h_stats.csv"
        
        # Save to both locations
        from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "h2h_stats", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved H2H stats CSV for {league_code} ({season}): {len(h2h_records)} team pairs")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving H2H stats CSV: {e}", exc_info=True)
        raise


def ingest_h2h_from_matches_table(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    season: Optional[str] = None,
    save_csv: bool = True
) -> Dict:
    """
    Calculate H2H statistics from existing matches table.
    
    Args:
        db: Database session
        home_team_id: Home team ID
        away_team_id: Away team ID
        season: Optional season filter (None = all seasons)
        save_csv: Whether to save CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Build query with optional season filter
        if season and season != "ALL":
            query = text("""
                SELECT 
                    COUNT(*) as matches_played,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                    AVG(home_goals + away_goals) as avg_goals
                FROM matches
                WHERE ((home_team_id = :home_id AND away_team_id = :away_id)
                   OR (home_team_id = :away_id AND away_team_id = :home_id))
                   AND season = :season
            """)
            params = {"home_id": home_team_id, "away_id": away_team_id, "season": season}
        else:
            query = text("""
                SELECT 
                    COUNT(*) as matches_played,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                    AVG(home_goals + away_goals) as avg_goals
                FROM matches
                WHERE (home_team_id = :home_id AND away_team_id = :away_id)
                   OR (home_team_id = :away_id AND away_team_id = :home_id)
            """)
            params = {"home_id": home_team_id, "away_id": away_team_id}
        
        result = db.execute(query, params).fetchone()
        
        if not result or result.matches_played == 0:
            return {"success": False, "error": "No matches found"}
        
        # Calculate draw_rate for validation
        draw_rate = (result.draws or 0) / result.matches_played if result.matches_played > 0 else 0.0
        
        # Validate H2H consistency
        context = f" (home_team_id={home_team_id}, away_team_id={away_team_id}, season={season or 'ALL'})"
        is_valid, error = DrawStructuralValidator.validate_h2h_consistency(
            result.matches_played, result.draws or 0, draw_rate, context
        )
        if not is_valid:
            logger.error(f"Invalid H2H stats: {error}")
            return {"success": False, "error": error}
        
        # Insert or update
        existing = db.query(H2HDrawStats).filter(
            H2HDrawStats.team_home_id == home_team_id,
            H2HDrawStats.team_away_id == away_team_id
        ).first()
        
        if existing:
            existing.matches_played = result.matches_played
            existing.draw_count = result.draws or 0
            existing.avg_goals = float(result.avg_goals) if result.avg_goals else None
        else:
            h2h = H2HDrawStats(
                team_home_id=home_team_id,
                team_away_id=away_team_id,
                matches_played=result.matches_played,
                draw_count=result.draws or 0,
                avg_goals=float(result.avg_goals) if result.avg_goals else None
            )
            db.add(h2h)
        
        db.commit()
        
        h2h_result = {
            "success": True,
            "season": season or "ALL",
            "matches_played": result.matches_played,
            "draw_count": result.draws or 0,
            "draw_rate": (result.draws or 0) / result.matches_played if result.matches_played > 0 else 0.0,
            "avg_goals": float(result.avg_goals) if result.avg_goals else None
        }
        
        # Save CSV if requested
        if save_csv:
            try:
                csv_path = _save_h2h_csv(db, home_team_id, away_team_id, h2h_result)
                h2h_result["csv_path"] = str(csv_path)
            except Exception as e:
                logger.warning(f"Failed to save H2H CSV: {e}")
        
        return h2h_result
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating H2H stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_h2h_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest H2H statistics from CSV file in our format.
    
    CSV Format: home_team_id,home_team_name,away_team_id,away_team_name,season,matches_played,draw_count,draw_rate,avg_goals
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['home_team_id', 'away_team_id', 'matches_played', 'draw_count', 'draw_rate']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {"success": False, "error": f"Missing required columns: {missing_cols}"}
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                home_team_id = int(row['home_team_id'])
                away_team_id = int(row['away_team_id'])
                matches_played = int(row['matches_played'])
                draw_count = int(row['draw_count'])
                draw_rate = float(row.get('draw_rate', 0.0))
                avg_goals = float(row.get('avg_goals', 0.0)) if pd.notna(row.get('avg_goals')) else None
                
                # Verify teams exist
                home_team = db.query(Team).filter(Team.id == home_team_id).first()
                away_team = db.query(Team).filter(Team.id == away_team_id).first()
                if not home_team or not away_team:
                    logger.warning(f"Team IDs {home_team_id} or {away_team_id} not found, skipping")
                    errors += 1
                    continue
                
                # Insert or update
                existing = db.query(H2HDrawStats).filter(
                    H2HDrawStats.team_home_id == home_team_id,
                    H2HDrawStats.team_away_id == away_team_id
                ).first()
                
                if existing:
                    existing.matches_played = matches_played
                    existing.draw_count = draw_count
                    existing.avg_goals = avg_goals
                    updated += 1
                else:
                    h2h = H2HDrawStats(
                        team_home_id=home_team_id,
                        team_away_id=away_team_id,
                        matches_played=matches_played,
                        draw_count=draw_count,
                        avg_goals=avg_goals
                    )
                    db.add(h2h)
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing H2H row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested H2H stats from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting H2H stats from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_ingest_h2h_stats(
    db: Session,
    league_codes: List[str] = None,
    season: str = "ALL",
    use_all_leagues: bool = False,
    use_all_seasons: bool = False,
    max_years: int = None,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest H2H statistics for all team pairs in specified leagues.
    
    Args:
        db: Database session
        league_codes: List of league codes to process (None = all)
        season: Season identifier (default: 'ALL' for all seasons, ignored if use_all_seasons=True)
        use_all_leagues: If True, process all leagues
        use_all_seasons: If True, calculate H2H for each season separately
        max_years: Maximum years to look back (only used if use_all_seasons=True)
        save_csv: Whether to save CSV files
    
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
        
        # Get leagues to process
        if use_all_leagues:
            leagues = db.query(League).all()
        elif league_codes:
            leagues = db.query(League).filter(League.code.in_(league_codes)).all()
        else:
            return {"success": False, "error": "No leagues specified"}
        
        logger.info(f"Batch processing H2H stats for {len(leagues)} leagues...")
        
        # Get seasons to process
        seasons_to_process = []
        if use_all_seasons:
            # Get all unique seasons from matches, optionally limited by max_years
            seasons_query = text("""
                SELECT DISTINCT season
                FROM matches
                WHERE season IS NOT NULL AND season != ''
                ORDER BY season DESC
            """)
            all_seasons = [row.season for row in db.execute(seasons_query).fetchall()]
            
            if max_years and max_years > 0:
                seasons_to_process = all_seasons[:max_years]
            else:
                seasons_to_process = all_seasons
            logger.info(f"Processing {len(seasons_to_process)} seasons: {seasons_to_process[:5]}...")
        else:
            # Use single season or ALL
            seasons_to_process = [season if season != "ALL" else None]
        
        # Get all unique team pairs from matches
        for league in leagues:
            try:
                for season_to_process in seasons_to_process:
                    # Collect all H2H records for this league/season to save in one CSV
                    h2h_records_for_csv = []
                    
                    # Get all team pairs that have played matches (with optional season filter)
                    if season_to_process:
                        team_pairs_query = text("""
                            SELECT DISTINCT 
                                LEAST(home_team_id, away_team_id) as team1_id,
                                GREATEST(home_team_id, away_team_id) as team2_id
                            FROM matches
                            WHERE league_id = :league_id AND season = :season
                        """)
                        team_pairs = db.execute(
                            team_pairs_query,
                            {"league_id": league.id, "season": season_to_process}
                        ).fetchall()
                    else:
                        team_pairs_query = text("""
                            SELECT DISTINCT 
                                LEAST(home_team_id, away_team_id) as team1_id,
                                GREATEST(home_team_id, away_team_id) as team2_id
                            FROM matches
                            WHERE league_id = :league_id
                        """)
                        team_pairs = db.execute(
                            team_pairs_query,
                            {"league_id": league.id}
                        ).fetchall()
                    
                    for pair in team_pairs:
                        results["total"] += 1
                        team1_id, team2_id = pair[0], pair[1]
                        
                        try:
                            # Process H2H (saves to database, but not CSV yet - CSV saved in batch)
                            result = ingest_h2h_from_matches_table(
                                db, team1_id, team2_id, season=season_to_process, save_csv=False
                            )
                            
                            if result.get("success"):
                                results["successful"] += 1
                                
                                # Get team names for CSV
                                home_team = db.query(Team).filter(Team.id == team1_id).first()
                                away_team = db.query(Team).filter(Team.id == team2_id).first()
                                
                                # Add to CSV records
                                h2h_records_for_csv.append({
                                    "home_team_id": team1_id,
                                    "home_team_name": home_team.name if home_team else f"Team {team1_id}",
                                    "away_team_id": team2_id,
                                    "away_team_name": away_team.name if away_team else f"Team {team2_id}",
                                    "season": season_to_process or "ALL",
                                    "matches_played": result.get("matches_played", 0),
                                    "draw_count": result.get("draw_count", 0),
                                    "draw_rate": result.get("draw_rate", 0.0),
                                    "avg_goals": result.get("avg_goals", 0.0)
                                })
                                
                                results["details"].append({
                                    "league_code": league.code,
                                    "season": season_to_process or "ALL",
                                    "team1_id": team1_id,
                                    "team2_id": team2_id,
                                    "matches_played": result.get("matches_played", 0),
                                    "success": True
                                })
                            else:
                                results["failed"] += 1
                                results["details"].append({
                                    "league_code": league.code,
                                    "season": season_to_process or "ALL",
                                    "team1_id": team1_id,
                                    "team2_id": team2_id,
                                    "error": result.get("error"),
                                    "success": False
                                })
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to process H2H for {team1_id} vs {team2_id} ({season_to_process or 'ALL'}): {e}")
                            results["details"].append({
                                "league_code": league.code,
                                "season": season_to_process or "ALL",
                                "team1_id": team1_id,
                                "team2_id": team2_id,
                                "error": str(e),
                                "success": False
                            })
                    
                    # Save one CSV file per league/season with all team pairs
                    if save_csv and h2h_records_for_csv:
                        try:
                            csv_path = _save_h2h_csv_batch(
                                db, league.code, league.name, season_to_process or "ALL", h2h_records_for_csv
                            )
                            logger.info(f"Saved H2H CSV for {league.code} ({season_to_process or 'ALL'}): {len(h2h_records_for_csv)} team pairs")
                        except Exception as e:
                            logger.warning(f"Failed to save H2H CSV for {league.code} ({season_to_process or 'ALL'}): {e}")
            except Exception as e:
                logger.error(f"Error processing league {league.code}: {e}")
                continue
        
        logger.info(f"Batch H2H ingestion complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch H2H ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
