"""
Ingest team Elo ratings from ClubElo or similar sources
"""
import pandas as pd
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import Team, TeamElo, League
from typing import Optional, Dict, List
from datetime import date, datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def ingest_elo_from_clubelo_csv(
    db: Session,
    csv_path: str,
    league_code: Optional[str] = None
) -> Dict:
    """
    Ingest Elo ratings from ClubElo CSV file.
    
    Args:
        db: Database session
        csv_path: Path to ClubElo CSV file
        league_code: Optional league code to filter teams
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Read CSV (ClubElo format: ClubID, From, To, Elo)
        df = pd.read_csv(csv_path)
        
        # Map ClubElo team IDs to our team IDs (requires mapping table or name matching)
        # For now, assume CSV has team names or IDs that can be matched
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                # Try to match team by name or ID
                team = None
                
                if 'TeamName' in row:
                    # Match by name
                    team = db.query(Team).filter(
                        Team.canonical_name.ilike(f"%{row['TeamName']}%")
                    ).first()
                elif 'ClubID' in row:
                    # If we have a mapping table, use it
                    # For now, skip or use name matching
                    pass
                
                if not team:
                    errors += 1
                    continue
                
                # Parse date
                from_date = pd.to_datetime(row.get('From', row.get('Date', date.today())))
                elo_rating = float(row.get('Elo', row.get('Rating', 1500)))
                
                # Check if exists
                existing = db.query(TeamElo).filter(
                    TeamElo.team_id == team.id,
                    TeamElo.date == from_date.date()
                ).first()
                
                if existing:
                    existing.elo_rating = elo_rating
                    updated += 1
                else:
                    elo = TeamElo(
                        team_id=team.id,
                        date=from_date.date(),
                        elo_rating=elo_rating
                    )
                    db.add(elo)
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing Elo row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested Elo ratings: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting Elo ratings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_elo_from_api(
    db: Session,
    team_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Ingest Elo rating for a single team from API.
    
    Args:
        db: Database session
        team_id: Team ID
        api_key: API key (optional)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            return {"success": False, "error": "Team not found"}
        
        # Example API call (adjust based on actual API)
        # This is a placeholder - actual implementation depends on API
        if not api_key:
            from app.config import settings
            api_key = getattr(settings, 'ELO_API_KEY', None)
        
        if not api_key:
            return {"success": False, "error": "API key not configured"}
        
        # API call would go here
        # For now, return placeholder
        return {"success": False, "error": "API integration not implemented"}
    
    except Exception as e:
        logger.error(f"Error ingesting Elo from API: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_elo_csv(
    db: Session,
    team_id: int,
    elo_data: List[Dict]
) -> Path:
    """
    Save CSV file with Elo ratings for a single team.
    
    Args:
        db: Database session
        team_id: Team ID
        elo_data: List of dictionaries with Elo rating data
    
    Returns:
        Path to saved CSV file
    """
    try:
        # Get team name
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise ValueError("Team not found")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/Elo_Rating")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame(elo_data)
        
        # Filename format: {team_id}_{team_name}_elo_ratings.csv
        safe_team_name = team.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_team_name = ''.join(c for c in safe_team_name if c.isalnum() or c in ('_', '-'))
        filename = f"{team_id}_{safe_team_name}_elo_ratings.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved Elo ratings CSV: {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving Elo ratings CSV: {e}", exc_info=True)
        raise


def _save_elo_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    elo_records: List[Dict]
) -> Path:
    """
    Save CSV file with Elo ratings for all teams in a league/season.
    One CSV file contains all teams for that league/season combination.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        elo_records: List of dictionaries with Elo ratings for all teams
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not elo_records:
            raise ValueError("No Elo records to save")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/Elo_Rating")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame from all records
        df = pd.DataFrame(elo_records)
        
        # Add team names for readability
        team_ids = list(set(df['team_id'].tolist()))
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        team_name_map = {team.id: team.name for team in teams}
        df['team_name'] = df['team_id'].map(team_name_map)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "team_id", "team_name", "date", "elo_rating"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_elo_ratings.csv
        filename = f"{league_code}_{season}_elo_ratings.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved batch Elo ratings CSV for {league_code} ({season}): {len(elo_records)} records -> {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving batch Elo ratings CSV: {e}", exc_info=True)
        raise


def calculate_elo_from_matches(
    db: Session,
    team_id: int,
    initial_elo: float = 1500.0,
    k_factor: float = 32.0,
    save_csv: bool = True
) -> Dict:
    """
    Calculate Elo ratings from match history.
    
    Args:
        db: Database session
        team_id: Team ID
        initial_elo: Starting Elo rating
        k_factor: Elo K-factor
    
    Returns:
        Dict with calculation statistics
    """
    try:
        from sqlalchemy import text
        from app.db.models import Match, MatchResult
        
        # Get all matches for this team
        matches = db.execute(
            text("""
                SELECT 
                    match_date,
                    home_team_id,
                    away_team_id,
                    home_goals,
                    away_goals,
                    result
                FROM matches
                WHERE home_team_id = :team_id OR away_team_id = :team_id
                ORDER BY match_date ASC
            """),
            {"team_id": team_id}
        ).fetchall()
        
        if not matches:
            return {"success": False, "error": "No matches found"}
        
        # Calculate Elo progression
        current_elo = initial_elo
        ratings = []
        
        for match in matches:
            is_home = match.home_team_id == team_id
            opponent_id = match.away_team_id if is_home else match.home_team_id
            
            # Get opponent's Elo at this date
            opponent_elo = db.execute(
                text("""
                    SELECT elo_rating
                    FROM team_elo
                    WHERE team_id = :opponent_id
                      AND date <= :match_date
                    ORDER BY date DESC
                    LIMIT 1
                """),
                {"opponent_id": opponent_id, "match_date": match.match_date}
            ).fetchone()
            
            opponent_elo_rating = opponent_elo.elo_rating if opponent_elo else initial_elo
            
            # Calculate expected score
            expected_score = 1 / (1 + 10 ** ((opponent_elo_rating - current_elo) / 400))
            
            # Determine actual score
            if match.result == 'D':
                actual_score = 0.5
            elif (is_home and match.result == 'H') or (not is_home and match.result == 'A'):
                actual_score = 1.0
            else:
                actual_score = 0.0
            
            # Update Elo
            current_elo = current_elo + k_factor * (actual_score - expected_score)
            
            # Store rating
            ratings.append({
                "date": match.match_date,
                "elo": current_elo
            })
        
        # Insert ratings
        inserted = 0
        for rating in ratings:
            existing = db.query(TeamElo).filter(
                TeamElo.team_id == team_id,
                TeamElo.date == rating["date"]
            ).first()
            
            if not existing:
                elo = TeamElo(
                    team_id=team_id,
                    date=rating["date"],
                    elo_rating=rating["elo"]
                )
                db.add(elo)
                inserted += 1
        
        db.commit()
        
        result = {
            "success": True,
            "inserted": inserted,
            "final_elo": current_elo,
            "ratings_count": len(ratings)
        }
        
        # Save CSV if requested
        if save_csv and ratings:
            try:
                # Prepare data for CSV
                elo_data = [{"date": r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]), 
                            "elo_rating": r["elo"]} for r in ratings]
                csv_path = _save_elo_csv(db, team_id, elo_data)
                result["csv_path"] = str(csv_path)
            except Exception as e:
                logger.warning(f"Failed to save Elo CSV: {e}")
        
        return result
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating Elo from matches: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_calculate_elo_from_matches(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch calculate Elo ratings for all teams in specified leagues and seasons.
    
    Args:
        db: Database session
        league_codes: List of league codes to process (None = all)
        use_all_leagues: If True, process all leagues
        season: Specific season to process (e.g., "2324")
        use_all_seasons: If True, process all available seasons
        max_years: Maximum years back if use_all_seasons is True
        save_csv: Whether to save CSV files
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        from app.services.data_ingestion import get_seasons_list
        
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
        
        # Determine seasons to process
        if use_all_seasons:
            seasons = get_seasons_list(max_years)
        elif season:
            seasons = [season]
        else:
            seasons = [None]  # Process all seasons
        
        logger.info(f"Batch processing Elo ratings for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Get teams from matches in this league/season
                    if season_filter:
                        teams_query = text("""
                            SELECT DISTINCT team_id
                            FROM (
                                SELECT home_team_id as team_id FROM matches 
                                WHERE league_id = :league_id AND season = :season
                                UNION
                                SELECT away_team_id as team_id FROM matches 
                                WHERE league_id = :league_id AND season = :season
                            ) t
                        """)
                        teams_params = {"league_id": league.id, "season": season_filter}
                    else:
                        teams_query = text("""
                            SELECT DISTINCT team_id
                            FROM (
                                SELECT home_team_id as team_id FROM matches WHERE league_id = :league_id
                                UNION
                                SELECT away_team_id as team_id FROM matches WHERE league_id = :league_id
                            ) t
                        """)
                        teams_params = {"league_id": league.id}
                    
                    teams = db.execute(teams_query, teams_params).fetchall()
                    
                    if not teams:
                        continue
                    
                    # Collect Elo records for this league/season
                    elo_records = []
                    
                    for team_row in teams:
                        team_id = team_row[0]
                        results["total"] += 1
                        
                        try:
                            # Calculate Elo for this team (filtered by season if specified)
                            result = calculate_elo_from_matches(
                                db, team_id, save_csv=False  # Don't save individual CSVs
                            )
                            
                            if result.get("success"):
                                # Get Elo ratings for this season if season filter is applied
                                if season_filter:
                                    elo_query = text("""
                                        SELECT date, elo_rating
                                        FROM team_elo
                                        WHERE team_id = :team_id
                                          AND date >= (
                                              SELECT MIN(match_date) FROM matches 
                                              WHERE league_id = :league_id AND season = :season
                                          )
                                          AND date <= (
                                              SELECT MAX(match_date) FROM matches 
                                              WHERE league_id = :league_id AND season = :season
                                          )
                                        ORDER BY date ASC
                                    """)
                                    elo_params = {"team_id": team_id, "league_id": league.id, "season": season_filter}
                                else:
                                    elo_query = text("""
                                        SELECT date, elo_rating
                                        FROM team_elo
                                        WHERE team_id = :team_id
                                        ORDER BY date ASC
                                    """)
                                    elo_params = {"team_id": team_id}
                                
                                elo_rows = db.execute(elo_query, elo_params).fetchall()
                                
                                for elo_row in elo_rows:
                                    elo_records.append({
                                        "league_code": league.code,
                                        "season": season_filter or "all",
                                        "team_id": team_id,
                                        "date": elo_row.date.isoformat() if hasattr(elo_row.date, "isoformat") else str(elo_row.date),
                                        "elo_rating": float(elo_row.elo_rating)
                                    })
                                
                                results["successful"] += 1
                                results["details"].append({
                                    "league_code": league.code,
                                    "season": season_filter or "all",
                                    "team_id": team_id,
                                    "final_elo": result.get("final_elo"),
                                    "ratings_count": result.get("ratings_count", 0),
                                    "success": True
                                })
                            else:
                                results["failed"] += 1
                                results["details"].append({
                                    "league_code": league.code,
                                    "season": season_filter or "all",
                                    "team_id": team_id,
                                    "error": result.get("error"),
                                    "success": False
                                })
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to calculate Elo for team {team_id}: {e}")
                            results["details"].append({
                                "league_code": league.code,
                                "season": season_filter or "all",
                                "team_id": team_id,
                                "error": str(e),
                                "success": False
                            })
                    
                    # Save CSV for this league/season combination
                    if save_csv and elo_records:
                        try:
                            csv_path = _save_elo_csv_batch(db, league.code, season_filter or "all", elo_records)
                            logger.info(f"Saved Elo CSV for {league.code} ({season_filter or 'all'}): {len(elo_records)} records")
                        except Exception as e:
                            logger.warning(f"Failed to save Elo CSV for {league.code} ({season_filter or 'all'}): {e}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        logger.info(f"Batch Elo calculation complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch Elo calculation: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

