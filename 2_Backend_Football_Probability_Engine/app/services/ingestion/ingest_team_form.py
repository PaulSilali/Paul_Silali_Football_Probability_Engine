"""
Batch ingestion service for team form data
Calculates and stores team form for matches in specified leagues and seasons
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError
from app.db.models import TeamForm, TeamFormHistorical, Match, League, Team, JackpotFixture
from app.services.team_form_calculator import calculate_team_form
from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
from app.services.ingestion.draw_structural_logging import write_draw_structural_log
from typing import Dict, List, Optional
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import logging
import time

logger = logging.getLogger(__name__)


def batch_ingest_team_form_from_matches(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True,
    matches_count: int = 5
) -> Dict:
    """
    Batch ingest team form from historical matches.
    Now includes comprehensive logging to 01_logs folders.
    """
    """
    Batch ingest team form for matches in specified leagues and seasons.
    
    Args:
        db: Database session
        league_codes: List of league codes to process
        use_all_leagues: If True, process all leagues
        season: Specific season to process
        use_all_seasons: If True, process all available seasons
        max_years: Maximum years back if use_all_seasons is True
        save_csv: Whether to save CSV files
        matches_count: Number of recent matches to consider for form calculation
    
    Returns:
        Dict with batch processing statistics
    """
    start_time = time.time()
    try:
        from app.services.data_ingestion import get_seasons_list
        
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": [],
            "csv_files_saved": [],
            "db_records_inserted": 0,
            "db_records_updated": 0,
            "errors": [],
            "warnings": []
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
        
        logger.info(f"Batch processing team form for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Check if table exists
        try:
            db.execute(text("SELECT 1 FROM team_form_historical LIMIT 1"))
            logger.info("✓ team_form_historical table exists")
        except Exception as e:
            logger.error(f"✗ team_form_historical table does NOT exist! Please run the migration first. Error: {e}")
            return {
                "success": False,
                "error": f"Table 'team_form_historical' does not exist. Please run migration: 3_Database_Football_Probability_Engine/migrations/add_team_form_historical.sql"
            }
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Ensure clean transaction state
                    try:
                        db.rollback()
                    except:
                        pass
                    
                    # Get matches for this league/season
                    if season_filter:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id AND season = :season
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id, "season": season_filter}
                    else:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id}
                    
                    matches = db.execute(matches_query, matches_params).fetchall()
                    
                    if not matches:
                        continue
                    
                    # Collect form records for this league/season
                    form_records = []
                    
                    for match in matches:
                        match_id = match.id
                        match_date = match.match_date
                        home_team_id = match.home_team_id
                        away_team_id = match.away_team_id
                        results["total"] += 1
                        
                        try:
                            # Get team names
                            home_team = db.query(Team).filter(Team.id == home_team_id).first()
                            away_team = db.query(Team).filter(Team.id == away_team_id).first()
                            
                            # Calculate form for home team
                            home_form = calculate_team_form(
                                db, 
                                home_team_id, 
                                match_date, 
                                matches_count=matches_count
                            )
                            
                            # Calculate form for away team
                            away_form = calculate_team_form(
                                db, 
                                away_team_id, 
                                match_date, 
                                matches_count=matches_count
                            )
                            
                            # Save to database (team_form_historical table for historical matches)
                            # Batch commits for better performance
                            if home_form:
                                # Check if record already exists
                                existing_home = db.query(TeamFormHistorical).filter(
                                    TeamFormHistorical.match_id == match_id,
                                    TeamFormHistorical.team_id == home_team_id
                                ).first()
                                
                                if existing_home:
                                    # Update existing record
                                    existing_home.matches_played = home_form.matches_played
                                    existing_home.wins = home_form.wins
                                    existing_home.draws = home_form.draws
                                    existing_home.losses = home_form.losses
                                    existing_home.goals_scored = home_form.goals_scored
                                    existing_home.goals_conceded = home_form.goals_conceded
                                    existing_home.points = home_form.points
                                    existing_home.form_rating = home_form.form_rating
                                    existing_home.attack_form = home_form.attack_form
                                    existing_home.defense_form = home_form.defense_form
                                    existing_home.last_match_date = home_form.last_match_date
                                    existing_home.calculated_at = func.now()
                                else:
                                    # Create new record
                                    db.add(TeamFormHistorical(
                                        match_id=match_id,
                                        team_id=home_team_id,
                                        matches_played=home_form.matches_played,
                                        wins=home_form.wins,
                                        draws=home_form.draws,
                                        losses=home_form.losses,
                                        goals_scored=home_form.goals_scored,
                                        goals_conceded=home_form.goals_conceded,
                                        points=home_form.points,
                                        form_rating=home_form.form_rating,
                                        attack_form=home_form.attack_form,
                                        defense_form=home_form.defense_form,
                                        last_match_date=home_form.last_match_date
                                    ))
                            
                            if away_form:
                                # Check if record already exists
                                existing_away = db.query(TeamFormHistorical).filter(
                                    TeamFormHistorical.match_id == match_id,
                                    TeamFormHistorical.team_id == away_team_id
                                ).first()
                                
                                if existing_away:
                                    # Update existing record
                                    existing_away.matches_played = away_form.matches_played
                                    existing_away.wins = away_form.wins
                                    existing_away.draws = away_form.draws
                                    existing_away.losses = away_form.losses
                                    existing_away.goals_scored = away_form.goals_scored
                                    existing_away.goals_conceded = away_form.goals_conceded
                                    existing_away.points = away_form.points
                                    existing_away.form_rating = away_form.form_rating
                                    existing_away.attack_form = away_form.attack_form
                                    existing_away.defense_form = away_form.defense_form
                                    existing_away.last_match_date = away_form.last_match_date
                                    existing_away.calculated_at = func.now()
                                else:
                                    # Create new record
                                    db.add(TeamFormHistorical(
                                        match_id=match_id,
                                        team_id=away_team_id,
                                        matches_played=away_form.matches_played,
                                        wins=away_form.wins,
                                        draws=away_form.draws,
                                        losses=away_form.losses,
                                        goals_scored=away_form.goals_scored,
                                        goals_conceded=away_form.goals_conceded,
                                        points=away_form.points,
                                        form_rating=away_form.form_rating,
                                        attack_form=away_form.attack_form,
                                        defense_form=away_form.defense_form,
                                        last_match_date=away_form.last_match_date
                                    ))
                            
                            # Commit after processing both teams for this match (batch commit)
                            if home_form or away_form:
                                try:
                                    db.commit()
                                    # Count successful saves and track DB updates
                                    if home_form:
                                        results["successful"] += 1
                                        if existing_home:
                                            results["db_records_updated"] += 1
                                        else:
                                            results["db_records_inserted"] += 1
                                    if away_form:
                                        results["successful"] += 1
                                        if existing_away:
                                            results["db_records_updated"] += 1
                                        else:
                                            results["db_records_inserted"] += 1
                                except IntegrityError as e:
                                    db.rollback()
                                    # Check if it's a duplicate key error (record already exists)
                                    if 'uix_team_form_historical_match_team' in str(e.orig):
                                        # Record already exists, skip (not a real error - can happen on re-runs)
                                        logger.debug(f"Form record already exists for match {match_id}, skipping")
                                        # Don't count as failed, just skip
                                        if home_form:
                                            results["skipped"] += 1
                                        if away_form:
                                            results["skipped"] += 1
                                    else:
                                        error_msg = f"Integrity error saving form to database for match {match_id}: {e}"
                                        results["errors"].append(error_msg)
                                        logger.error(error_msg, exc_info=True)
                                        if home_form:
                                            results["failed"] += 1
                                        if away_form:
                                            results["failed"] += 1
                                except Exception as e:
                                    db.rollback()
                                    error_msg = f"Failed to save form to database for match {match_id}: {e}"
                                    results["errors"].append(error_msg)
                                    logger.error(error_msg, exc_info=True)
                                    if home_form:
                                        results["failed"] += 1
                                    if away_form:
                                        results["failed"] += 1
                            
                            # Add to CSV records (always add to CSV even if DB save failed)
                            # Note: CSV records are added separately from DB tracking
                            if home_form:
                                form_records.append({
                                    "league_code": league.code,
                                    "season": season_filter or "all",
                                    "match_date": match_date.isoformat() if hasattr(match_date, "isoformat") else str(match_date),
                                    "team_id": home_team_id,
                                    "team_name": home_team.name if home_team else f"Team {home_team_id}",
                                    "is_home": True,
                                    "matches_played": home_form.matches_played,
                                    "wins": home_form.wins,
                                    "draws": home_form.draws,
                                    "losses": home_form.losses,
                                    "goals_scored": home_form.goals_scored,
                                    "goals_conceded": home_form.goals_conceded,
                                    "points": home_form.points,
                                    "form_rating": home_form.form_rating,
                                    "attack_form": home_form.attack_form,
                                    "defense_form": home_form.defense_form,
                                    "last_match_date": home_form.last_match_date.isoformat() if home_form.last_match_date else None
                                })
                            
                            if away_form:
                                form_records.append({
                                    "league_code": league.code,
                                    "season": season_filter or "all",
                                    "match_date": match_date.isoformat() if hasattr(match_date, "isoformat") else str(match_date),
                                    "team_id": away_team_id,
                                    "team_name": away_team.name if away_team else f"Team {away_team_id}",
                                    "is_home": False,
                                    "matches_played": away_form.matches_played,
                                    "wins": away_form.wins,
                                    "draws": away_form.draws,
                                    "losses": away_form.losses,
                                    "goals_scored": away_form.goals_scored,
                                    "goals_conceded": away_form.goals_conceded,
                                    "points": away_form.points,
                                    "form_rating": away_form.form_rating,
                                    "attack_form": away_form.attack_form,
                                    "defense_form": away_form.defense_form,
                                    "last_match_date": away_form.last_match_date.isoformat() if away_form.last_match_date else None
                                })
                            
                            results["total"] += 1
                            
                        except Exception as e:
                            error_msg = f"Failed to calculate form for match {match_id}: {e}"
                            results["errors"].append(error_msg)
                            results["failed"] += 1
                            results["total"] += 1
                            logger.warning(error_msg)
                    
                    # Save CSV for this league/season combination
                    if save_csv and form_records:
                        try:
                            csv_path = _save_team_form_csv_batch(db, league.code, season_filter or "all", form_records)
                            csv_filename = csv_path.name if csv_path else f"{league.code}_{season_filter or 'all'}_team_form.csv"
                            results["csv_files_saved"].append(f"{csv_filename} ({len(form_records)} records)")
                            logger.info(f"Saved Team Form CSV for {league.code} ({season_filter or 'all'}): {len(form_records)} records")
                        except Exception as e:
                            error_msg = f"Failed to save Team Form CSV for {league.code} ({season_filter or 'all'}): {e}"
                            results["warnings"].append(error_msg)
                            logger.warning(error_msg)
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        execution_time = time.time() - start_time
        results["execution_time_seconds"] = execution_time
        results["total"] = results["successful"] + results["failed"] + results["skipped"]
        results["success"] = results["failed"] == 0
        
        logger.info(f"Batch team form ingestion complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        # Write comprehensive log to 01_logs folders
        try:
            log_summary = {
                "success": results["success"],
                "total": results["total"],
                "successful": results["successful"],
                "failed": results["failed"],
                "skipped": results["skipped"],
                "csv_files_saved": results.get("csv_files_saved", []),
                "db_records_inserted": results.get("db_records_inserted", 0),
                "db_records_updated": results.get("db_records_updated", 0),
                "errors": results.get("errors", []),
                "warnings": results.get("warnings", []),
                "execution_time_seconds": execution_time,
                "details": results.get("details", [])
            }
            write_draw_structural_log("Team_Form", log_summary)
        except Exception as log_error:
            logger.warning(f"Failed to write ingestion log: {log_error}", exc_info=True)
        
        return {
            "success": results["success"],
            **results,
            "message": f"Processed {results['total']} matches. {results['successful']} form records calculated, {results['failed']} failed."
        }
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error in batch team form ingestion: {e}", exc_info=True)
        
        # Write error log
        try:
            error_summary = {
                "success": False,
                "total": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "errors": [str(e)],
                "execution_time_seconds": execution_time
            }
            write_draw_structural_log("Team_Form", error_summary)
        except:
            pass
        
        return {"success": False, "error": str(e)}


def batch_ingest_team_form_for_fixtures(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    save_csv: bool = True,
    matches_count: int = 5
) -> Dict:
    """
    Batch ingest team form for jackpot fixtures.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        save_csv: Whether to save CSV files
        matches_count: Number of recent matches to consider for form calculation
    
    Returns:
        Dict with batch processing statistics
    """
    try:
        from app.services.team_form_service import calculate_and_store_team_form
        
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0
        }
        
        # Get fixtures to process
        if fixture_ids:
            fixtures = db.query(JackpotFixture).filter(JackpotFixture.id.in_(fixture_ids)).all()
        elif use_all_leagues or league_codes:
            query = db.query(JackpotFixture)
            if league_codes:
                from app.db.models import League
                leagues = db.query(League).filter(League.code.in_(league_codes)).all()
                league_ids = [l.id for l in leagues]
                query = query.join(League).filter(League.id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        form_records = []
        
        for fixture in fixtures:
            try:
                if not fixture.home_team_id or not fixture.away_team_id:
                    results["skipped"] += 1
                    continue
                
                # Get fixture date
                fixture_date = None
                if hasattr(fixture, 'match_date') and fixture.match_date:
                    fixture_date = fixture.match_date
                elif hasattr(fixture, 'jackpot') and fixture.jackpot and fixture.jackpot.kickoff_date:
                    fixture_date = fixture.jackpot.kickoff_date
                
                # Calculate and store form for home team
                home_result = calculate_and_store_team_form(
                    db,
                    fixture.home_team_id,
                    fixture.id,
                    fixture_date,
                    matches_count
                )
                
                if home_result.get("success"):
                    results["successful"] += 1
                    form_metrics = home_result.get("form_metrics", {})
                    form_records.append({
                        "fixture_id": fixture.id,
                        "team_id": fixture.home_team_id,
                        "is_home": True,
                        **form_metrics
                    })
                else:
                    results["failed"] += 1
                
                # Calculate and store form for away team
                away_result = calculate_and_store_team_form(
                    db,
                    fixture.away_team_id,
                    fixture.id,
                    fixture_date,
                    matches_count
                )
                
                if away_result.get("success"):
                    results["successful"] += 1
                    form_metrics = away_result.get("form_metrics", {})
                    form_records.append({
                        "fixture_id": fixture.id,
                        "team_id": fixture.away_team_id,
                        "is_home": False,
                        **form_metrics
                    })
                else:
                    results["failed"] += 1
                
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"Failed to calculate form for fixture {fixture.id}: {e}")
        
        # Save CSV if requested
        if save_csv and form_records:
            try:
                # Group by league if possible
                df = pd.DataFrame(form_records)
                filename = f"fixtures_team_form_{len(fixtures)}_fixtures.csv"
                ingestion_path, cleaned_path = save_draw_structural_csv(
                    df, "Team_Form", filename, save_to_cleaned=True
                )
                logger.info(f"Saved Team Form CSV for fixtures: {len(form_records)} records")
            except Exception as e:
                logger.warning(f"Failed to save Team Form CSV: {e}")
        
        return {
            "success": True,
            **results,
            "message": f"Processed {results['total']} fixtures. {results['successful']} form records calculated, {results['failed']} failed."
        }
    
    except Exception as e:
        logger.error(f"Error in batch team form ingestion for fixtures: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_team_form_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    form_records: List[Dict]
) -> Path:
    """
    Save CSV file with team form data for all matches in a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        form_records: List of dictionaries with form data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not form_records:
            raise ValueError("No form records to save")
        
        # Create DataFrame from all records
        df = pd.DataFrame(form_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "team_id", "team_name", "is_home",
                "matches_played", "wins", "draws", "losses", "goals_scored", "goals_conceded",
                "points", "form_rating", "attack_form", "defense_form", "last_match_date"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_team_form.csv
        filename = f"{league_code}_{season}_team_form.csv"
        
        # Save to both locations
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "Team_Form", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved batch team form CSV for {league_code} ({season}): {len(form_records)} records")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving batch team form CSV: {e}", exc_info=True)
        raise

