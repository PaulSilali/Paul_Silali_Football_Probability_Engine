"""
Batch ingestion service for team injuries data
Note: Injuries typically need to be manually entered or fetched from external APIs
This service provides batch processing capabilities for injury data
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import TeamInjuries, Match, League, Team, JackpotFixture
from app.services.injury_tracking import record_team_injuries, calculate_injury_severity
from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
from typing import Dict, List, Optional
from datetime import date
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def batch_ingest_team_injuries_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest team injuries from CSV file.
    
    CSV Format: league_code,season,match_date,home_team,away_team,
                home_key_players_missing,home_injury_severity,home_attackers_missing,home_midfielders_missing,home_defenders_missing,home_goalkeepers_missing,home_notes,
                away_key_players_missing,away_injury_severity,away_attackers_missing,away_midfielders_missing,away_defenders_missing,away_goalkeepers_missing,away_notes
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['league_code', 'season', 'match_date', 'home_team', 'away_team']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {"success": False, "error": f"Missing required columns: {missing_cols}"}
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                league_code = str(row['league_code']).strip()
                season = str(row['season']).strip()
                match_date = pd.to_datetime(row['match_date']).date()
                home_team_name = str(row['home_team']).strip()
                away_team_name = str(row['away_team']).strip()
                
                # Find league
                league = db.query(League).filter(League.code == league_code).first()
                if not league:
                    logger.warning(f"League {league_code} not found, skipping")
                    errors += 1
                    continue
                
                # Find teams
                from app.services.team_resolver import resolve_team_safe
                home_team = resolve_team_safe(db, home_team_name, league.id)
                away_team = resolve_team_safe(db, away_team_name, league.id)
                if not home_team or not away_team:
                    logger.warning(f"Teams {home_team_name} or {away_team_name} not found, skipping")
                    errors += 1
                    continue
                
                # Find match (for historical matches) or fixture
                match = db.query(Match).filter(
                    Match.league_id == league.id,
                    Match.season == season,
                    Match.match_date == match_date,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id
                ).first()
                
                # For fixtures, we need to find the fixture
                fixture = None
                if not match:
                    # Try to find fixture
                    fixture = db.query(JackpotFixture).join(
                        db.query(League).filter(League.id == league.id)
                    ).filter(
                        JackpotFixture.home_team_id == home_team.id,
                        JackpotFixture.away_team_id == away_team.id
                    ).first()
                
                # Extract injury data for home team
                home_key_players = int(row.get('home_key_players_missing', 0)) if pd.notna(row.get('home_key_players_missing')) else 0
                home_severity = float(row.get('home_injury_severity', 0)) if pd.notna(row.get('home_injury_severity')) else None
                home_attackers = int(row.get('home_attackers_missing', 0)) if pd.notna(row.get('home_attackers_missing')) else 0
                home_midfielders = int(row.get('home_midfielders_missing', 0)) if pd.notna(row.get('home_midfielders_missing')) else 0
                home_defenders = int(row.get('home_defenders_missing', 0)) if pd.notna(row.get('home_defenders_missing')) else 0
                home_gks = int(row.get('home_goalkeepers_missing', 0)) if pd.notna(row.get('home_goalkeepers_missing')) else 0
                home_notes = str(row.get('home_notes', '')) if pd.notna(row.get('home_notes')) else None
                
                # Calculate severity if not provided
                if home_severity is None:
                    home_severity = calculate_injury_severity(
                        home_key_players, home_attackers, home_midfielders, home_defenders, home_gks
                    )
                
                # Extract injury data for away team
                away_key_players = int(row.get('away_key_players_missing', 0)) if pd.notna(row.get('away_key_players_missing')) else 0
                away_severity = float(row.get('away_injury_severity', 0)) if pd.notna(row.get('away_injury_severity')) else None
                away_attackers = int(row.get('away_attackers_missing', 0)) if pd.notna(row.get('away_attackers_missing')) else 0
                away_midfielders = int(row.get('away_midfielders_missing', 0)) if pd.notna(row.get('away_midfielders_missing')) else 0
                away_defenders = int(row.get('away_defenders_missing', 0)) if pd.notna(row.get('away_defenders_missing')) else 0
                away_gks = int(row.get('away_goalkeepers_missing', 0)) if pd.notna(row.get('away_goalkeepers_missing')) else 0
                away_notes = str(row.get('away_notes', '')) if pd.notna(row.get('away_notes')) else None
                
                # Calculate severity if not provided
                if away_severity is None:
                    away_severity = calculate_injury_severity(
                        away_key_players, away_attackers, away_midfielders, away_defenders, away_gks
                    )
                
                # For fixtures, record injuries
                if fixture:
                    # Record home team injuries
                    home_result = record_team_injuries(
                        db,
                        home_team.id,
                        fixture.id,
                        home_key_players,
                        home_severity,
                        home_attackers,
                        home_midfielders,
                        home_defenders,
                        home_gks,
                        home_notes
                    )
                    
                    if home_result.get("success"):
                        if home_result.get("action") == "created":
                            inserted += 1
                        else:
                            updated += 1
                    
                    # Record away team injuries
                    away_result = record_team_injuries(
                        db,
                        away_team.id,
                        fixture.id,
                        away_key_players,
                        away_severity,
                        away_attackers,
                        away_midfielders,
                        away_defenders,
                        away_gks,
                        away_notes
                    )
                    
                    if away_result.get("success"):
                        if away_result.get("action") == "created":
                            inserted += 1
                        else:
                            updated += 1
                else:
                    logger.warning(f"Match/fixture not found for {league_code} {season} {match_date} {home_team_name} vs {away_team_name}, skipping")
                    errors += 1
                    continue
                
            except Exception as e:
                logger.warning(f"Error processing injuries row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested injuries from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting injuries from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_ingest_team_injuries_for_fixtures(
    db: Session,
    fixture_ids: List[int] = None,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    save_csv: bool = True
) -> Dict:
    """
    Batch export/ingest team injuries for jackpot fixtures.
    Note: This function exports existing injury data to CSV format.
    For actual injury data, you need to manually enter or fetch from external APIs.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs to process (optional)
        league_codes: List of league codes to process (if fixture_ids not provided)
        use_all_leagues: If True, process all leagues (if fixture_ids not provided)
        save_csv: Whether to save CSV files
    
    Returns:
        Dict with batch processing statistics
    """
    try:
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
                # JackpotFixture has league_id column directly, no need to join
                query = query.filter(JackpotFixture.league_id.in_(league_ids))
            fixtures = query.all()
        else:
            return {"success": False, "error": "No fixtures specified"}
        
        results["total"] = len(fixtures)
        
        injury_records = []
        
        for fixture in fixtures:
            try:
                if not fixture.home_team_id or not fixture.away_team_id:
                    results["skipped"] += 1
                    continue
                
                # Get existing injury records
                home_injuries = db.query(TeamInjuries).filter(
                    TeamInjuries.fixture_id == fixture.id,
                    TeamInjuries.team_id == fixture.home_team_id
                ).first()
                
                away_injuries = db.query(TeamInjuries).filter(
                    TeamInjuries.fixture_id == fixture.id,
                    TeamInjuries.team_id == fixture.away_team_id
                ).first()
                
                # Get team names
                home_team = db.query(Team).filter(Team.id == fixture.home_team_id).first()
                away_team = db.query(Team).filter(Team.id == fixture.away_team_id).first()
                
                # Get league code
                league_code = "UNKNOWN"
                if fixture.league_id:
                    league = db.query(League).filter(League.id == fixture.league_id).first()
                    if league:
                        league_code = league.code
                
                # Get fixture date
                fixture_date = None
                if hasattr(fixture, 'match_date') and fixture.match_date:
                    fixture_date = fixture.match_date
                elif fixture.jackpot and fixture.jackpot.kickoff_date:
                    fixture_date = fixture.jackpot.kickoff_date
                
                # Track if this fixture has any injuries
                fixture_has_injuries = False
                
                # Export home team injuries
                if home_injuries:
                    injury_records.append({
                        "fixture_id": fixture.id,
                        "league_code": league_code,
                        "match_date": fixture_date.isoformat() if fixture_date else None,
                        "team_id": fixture.home_team_id,
                        "team_name": home_team.name if home_team else f"Team {fixture.home_team_id}",
                        "is_home": True,
                        "key_players_missing": home_injuries.key_players_missing,
                        "injury_severity": home_injuries.injury_severity,
                        "attackers_missing": home_injuries.attackers_missing,
                        "midfielders_missing": home_injuries.midfielders_missing,
                        "defenders_missing": home_injuries.defenders_missing,
                        "goalkeepers_missing": home_injuries.goalkeepers_missing,
                        "notes": home_injuries.notes
                    })
                    results["successful"] += 1
                    fixture_has_injuries = True
                
                # Export away team injuries
                if away_injuries:
                    injury_records.append({
                        "fixture_id": fixture.id,
                        "league_code": league_code,
                        "match_date": fixture_date.isoformat() if fixture_date else None,
                        "team_id": fixture.away_team_id,
                        "team_name": away_team.name if away_team else f"Team {fixture.away_team_id}",
                        "is_home": False,
                        "key_players_missing": away_injuries.key_players_missing,
                        "injury_severity": away_injuries.injury_severity,
                        "attackers_missing": away_injuries.attackers_missing,
                        "midfielders_missing": away_injuries.midfielders_missing,
                        "defenders_missing": away_injuries.defenders_missing,
                        "goalkeepers_missing": away_injuries.goalkeepers_missing,
                        "notes": away_injuries.notes
                    })
                    results["successful"] += 1
                    fixture_has_injuries = True
                
                # If fixture has no injuries, count as skipped
                if not fixture_has_injuries:
                    results["skipped"] += 1
                
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"Failed to export injuries for fixture {fixture.id}: {e}", exc_info=True)
        
        # Save CSV if requested
        if save_csv and injury_records:
            try:
                df = pd.DataFrame(injury_records)
                filename = f"fixtures_team_injuries_{len(fixtures)}_fixtures.csv"
                ingestion_path, cleaned_path = save_draw_structural_csv(
                    df, "Team_Injuries", filename, save_to_cleaned=True
                )
                logger.info(f"Saved Team Injuries CSV for fixtures: {len(injury_records)} records")
            except Exception as e:
                logger.warning(f"Failed to save Team Injuries CSV: {e}")
        
        return {
            "success": True,
            **results,
            "message": f"Processed {results['total']} fixtures. {results['successful']} injury records exported, {results['skipped']} skipped (no injuries), {results['failed']} failed."
        }
    
    except Exception as e:
        logger.error(f"Error in batch team injuries export for fixtures: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_team_injuries_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    injury_records: List[Dict]
) -> Path:
    """
    Save CSV file with team injuries data for all matches in a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        injury_records: List of dictionaries with injury data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not injury_records:
            raise ValueError("No injury records to save")
        
        # Create DataFrame from all records
        df = pd.DataFrame(injury_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "team_id", "team_name", "is_home",
                "key_players_missing", "injury_severity", "attackers_missing", "midfielders_missing",
                "defenders_missing", "goalkeepers_missing", "notes"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_team_injuries.csv
        filename = f"{league_code}_{season}_team_injuries.csv"
        
        # Save to both locations
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "Team_Injuries", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved batch team injuries CSV for {league_code} ({season}): {len(injury_records)} records")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving batch team injuries CSV: {e}", exc_info=True)
        raise

