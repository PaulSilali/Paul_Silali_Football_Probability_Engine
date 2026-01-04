"""
Ingest referee statistics from WorldFootball.net or similar sources
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import RefereeStats, Match, MatchResult, League
from typing import Optional, Dict, List
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _save_referee_csv(
    db: Session,
    referee_id: int,
    referee_data: Dict
) -> Path:
    """
    Save CSV file with referee statistics for a single referee.
    
    Args:
        db: Database session
        referee_id: Referee ID
        referee_data: Dictionary with referee statistics
    
    Returns:
        Path to saved CSV file
    """
    try:
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/Referee")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame([{
            "referee_id": referee_id,
            "referee_name": referee_data.get("referee_name", f"Referee {referee_id}"),
            "matches": referee_data.get("matches", 0),
            "avg_cards": referee_data.get("avg_cards", 0.0),
            "avg_penalties": referee_data.get("avg_penalties", 0.0),
            "draw_rate": referee_data.get("draw_rate", 0.0)
        }])
        
        # Filename format: {referee_id}_referee_stats.csv
        filename = f"{referee_id}_referee_stats.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved referee stats CSV: {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving referee stats CSV: {e}", exc_info=True)
        raise


def _save_referee_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    referee_records: List[Dict]
) -> Path:
    """
    Save CSV file with referee statistics for all referees in a league/season.
    One CSV file contains all referees for that league/season combination.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        referee_records: List of dictionaries with referee statistics
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not referee_records:
            raise ValueError("No referee records to save")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/Referee")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame from all records
        df = pd.DataFrame(referee_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "referee_id", "referee_name", "matches", 
                "avg_cards", "avg_penalties", "draw_rate"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_referee_stats.csv
        filename = f"{league_code}_{season}_referee_stats.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved batch referee stats CSV for {league_code} ({season}): {len(referee_records)} referees -> {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving batch referee stats CSV: {e}", exc_info=True)
        raise


def ingest_referee_stats_from_matches(
    db: Session,
    referee_id: int,
    referee_name: Optional[str] = None,
    save_csv: bool = True
) -> Dict:
    """
    Calculate referee statistics from match history.
    
    Args:
        db: Database session
        referee_id: Referee ID
        referee_name: Referee name (optional)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Check if matches table has referee_id column
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        matches_columns = [col['name'] for col in inspector.get_columns('matches')]
        has_referee_id = 'referee_id' in matches_columns
        has_cards = 'cards' in matches_columns or 'HY' in matches_columns  # Check for yellow cards column
        has_penalties = 'penalties' in matches_columns
        
        if not has_referee_id:
            # If referee_id column doesn't exist, create a placeholder entry
            # This allows the system to work even without referee data in matches
            logger.warning(f"Matches table doesn't have referee_id column. Creating placeholder for referee {referee_id}")
            
            # Create a placeholder entry with default values
            existing = db.query(RefereeStats).filter(
                RefereeStats.referee_id == referee_id
            ).first()
            
            if not existing:
                referee = RefereeStats(
                    referee_id=referee_id,
                    referee_name=referee_name or f"Referee {referee_id}",
                    matches=0,
                    avg_cards=0.0,
                    avg_penalties=0.0,
                    draw_rate=0.26  # Default league average
                )
                db.add(referee)
                db.commit()
                
                return {
                    "success": True,
                    "matches": 0,
                    "avg_cards": 0.0,
                    "avg_penalties": 0.0,
                    "draw_rate": 0.26,
                    "note": "Placeholder entry - matches table doesn't have referee_id column"
                }
            else:
                return {
                    "success": True,
                    "matches": existing.matches,
                    "avg_cards": existing.avg_cards or 0.0,
                    "avg_penalties": existing.avg_penalties or 0.0,
                    "draw_rate": existing.draw_rate or 0.26,
                    "note": "Existing placeholder entry"
                }
        
        # If referee_id exists, try to calculate stats
        query = """
            SELECT 
                COUNT(*) as matches,
                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)::float / COUNT(*) as draw_rate
            FROM matches
            WHERE referee_id = :referee_id
        """
        
        # Add cards/penalties if columns exist
        if has_cards:
            query = query.replace(
                "COUNT(*) as matches,",
                """COUNT(*) as matches,
                    AVG(CASE WHEN HY IS NOT NULL THEN HY ELSE 0 END + 
                        CASE WHEN AY IS NOT NULL THEN AY ELSE 0 END) as avg_cards_penalties,"""
            )
        
        result = db.execute(
            text(query),
            {"referee_id": referee_id}
        ).fetchone()
        
        if not result or result.matches == 0:
            return {"success": False, "error": f"No matches found for referee_id {referee_id}"}
        
        matches = result.matches
        # Handle cards calculation if available
        if hasattr(result, 'avg_cards_penalties') and result.avg_cards_penalties is not None:
            avg_cards = float(result.avg_cards_penalties)
        else:
            avg_cards = 0.0
        draw_rate = float(result.draw_rate) if result.draw_rate else 0.26
        
        # Split cards and penalties (if available separately)
        # For now, assume avg_cards includes both
        avg_penalties = 0.0  # Would need separate calculation if available
        
        # Insert or update
        existing = db.query(RefereeStats).filter(
            RefereeStats.referee_id == referee_id
        ).first()
        
        if existing:
            existing.matches = matches
            existing.avg_cards = float(avg_cards)
            existing.avg_penalties = float(avg_penalties)
            existing.draw_rate = float(draw_rate)
            if referee_name:
                existing.referee_name = referee_name
        else:
            referee = RefereeStats(
                referee_id=referee_id,
                referee_name=referee_name or f"Referee {referee_id}",
                matches=matches,
                avg_cards=float(avg_cards),
                avg_penalties=float(avg_penalties),
                draw_rate=float(draw_rate)
            )
            db.add(referee)
        
        db.commit()
        
        logger.info(f"Ingested referee stats for {referee_id}: {matches} matches, draw_rate={draw_rate:.3f}")
        
        result = {
            "success": True,
            "referee_id": referee_id,
            "referee_name": referee_name or f"Referee {referee_id}",
            "matches": matches,
            "avg_cards": float(avg_cards),
            "avg_penalties": float(avg_penalties),
            "draw_rate": float(draw_rate)
        }
        
        # Save CSV if requested
        if save_csv:
            try:
                csv_path = _save_referee_csv(db, referee_id, result)
                result["csv_path"] = str(csv_path)
            except Exception as e:
                logger.warning(f"Failed to save referee CSV: {e}")
        
        return result
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting referee stats: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_referee_from_api(
    db: Session,
    referee_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Ingest referee statistics from external API.
    
    Args:
        db: Database session
        referee_id: Referee ID
        api_key: API key (optional)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Placeholder for API integration
        # Actual implementation depends on API structure
        if not api_key:
            from app.config import settings
            api_key = getattr(settings, 'REFEREE_API_KEY', None)
        
        if not api_key:
            return {"success": False, "error": "API key not configured"}
        
        # API call would go here
        return {"success": False, "error": "API integration not implemented"}
    
    except Exception as e:
        logger.error(f"Error ingesting referee from API: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_ingest_referee_stats(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest referee statistics for all referees in specified leagues and seasons.
    
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
        
        logger.info(f"Batch processing referee stats for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Check if matches table has referee_id column
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        matches_columns = [col['name'] for col in inspector.get_columns('matches')]
        has_referee_id = 'referee_id' in matches_columns
        
        if not has_referee_id:
            logger.warning("Matches table doesn't have referee_id column. Cannot calculate referee-specific stats.")
            logger.info("Referee stats will be calculated using league-wide averages as placeholders.")
            
            # Create placeholder referee stats based on league-wide draw rates
            referee_records = []
            
            for league in leagues:
                for season_filter in seasons:
                    try:
                        # Calculate league-wide draw rate for this league/season
                        if season_filter:
                            draw_rate_query = text("""
                                SELECT 
                                    COUNT(*) as total_matches,
                                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)::float / COUNT(*) as draw_rate
                                FROM matches
                                WHERE league_id = :league_id AND season = :season
                            """)
                            draw_rate_params = {"league_id": league.id, "season": season_filter}
                        else:
                            draw_rate_query = text("""
                                SELECT 
                                    COUNT(*) as total_matches,
                                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)::float / COUNT(*) as draw_rate
                                FROM matches
                                WHERE league_id = :league_id
                            """)
                            draw_rate_params = {"league_id": league.id}
                        
                        draw_rate_result = db.execute(draw_rate_query, draw_rate_params).fetchone()
                        
                        if draw_rate_result and draw_rate_result.total_matches > 0:
                            league_draw_rate = float(draw_rate_result.draw_rate) if draw_rate_result.draw_rate else 0.26
                            
                            # Create a placeholder referee entry for this league/season
                            # Make referee_id unique per league/season combination
                            # Format: 90000 + (league.id * 1000) + season_number
                            # Season number: convert "2526" -> 0, "2425" -> 1, etc.
                            season_num = 0
                            if season_filter and len(season_filter) == 4:
                                try:
                                    # Convert season like "2526" to a number (0-99)
                                    season_num = int(season_filter[2:4])  # Last 2 digits
                                except:
                                    season_num = 0
                            
                            placeholder_referee_id = 90000 + (league.id * 1000) + season_num
                            
                            referee_records.append({
                                "league_code": league.code,
                                "season": season_filter or "all",
                                "referee_id": placeholder_referee_id,
                                "referee_name": f"League Average ({league.code} {season_filter or 'all'})",
                                "matches": int(draw_rate_result.total_matches),
                                "avg_cards": 0.0,
                                "avg_penalties": 0.0,
                                "draw_rate": league_draw_rate
                            })
                            
                            # Save placeholder to database (unique per league/season)
                            existing = db.query(RefereeStats).filter(
                                RefereeStats.referee_id == placeholder_referee_id
                            ).first()
                            
                            if not existing:
                                referee = RefereeStats(
                                    referee_id=placeholder_referee_id,
                                    referee_name=f"League Average ({league.code} {season_filter or 'all'})",
                                    matches=int(draw_rate_result.total_matches),
                                    avg_cards=0.0,
                                    avg_penalties=0.0,
                                    draw_rate=league_draw_rate
                                )
                                db.add(referee)
                                db.commit()
                            else:
                                # Update existing record
                                existing.matches = int(draw_rate_result.total_matches)
                                existing.draw_rate = league_draw_rate
                                existing.referee_name = f"League Average ({league.code} {season_filter or 'all'})"
                                db.commit()
                            
                            results["successful"] += 1
                            results["total"] += 1
                            
                    except Exception as e:
                        logger.warning(f"Error creating placeholder referee stats for {league.code} ({season_filter}): {e}")
                        results["failed"] += 1
                        continue
                    
                    # Save CSV for this league/season combination
                    if save_csv and referee_records:
                        try:
                            # Filter records for this specific league/season
                            league_season_records = [r for r in referee_records if r["league_code"] == league.code and r["season"] == (season_filter or "all")]
                            if league_season_records:
                                csv_path = _save_referee_csv_batch(db, league.code, season_filter or "all", league_season_records)
                                logger.info(f"Saved Referee CSV for {league.code} ({season_filter or 'all'}): {len(league_season_records)} placeholder entries")
                        except Exception as e:
                            logger.warning(f"Failed to save Referee CSV for {league.code} ({season_filter or 'all'}): {e}")
                    
                    # Clear records for next iteration
                    referee_records = []
            
            logger.info(f"Batch referee stats ingestion complete (placeholders): {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
            
            return {
                "success": True,
                "note": "Matches table doesn't have referee_id column. Created placeholder entries using league-wide draw rates.",
                **results
            }
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Get all unique referees from matches in this league/season
                    if season_filter:
                        referees_query = text("""
                            SELECT DISTINCT referee_id
                            FROM matches
                            WHERE league_id = :league_id 
                              AND season = :season 
                              AND referee_id IS NOT NULL
                        """)
                        referees_params = {"league_id": league.id, "season": season_filter}
                    else:
                        referees_query = text("""
                            SELECT DISTINCT referee_id
                            FROM matches
                            WHERE league_id = :league_id AND referee_id IS NOT NULL
                        """)
                        referees_params = {"league_id": league.id}
                    
                    referees = db.execute(referees_query, referees_params).fetchall()
                    
                    if not referees:
                        continue
                    
                    # Collect referee records for this league/season
                    referee_records = []
                    
                    for ref_row in referees:
                        referee_id = ref_row[0]
                        results["total"] += 1
                        
                        try:
                            # Ingest referee stats (filtered by season if specified)
                            if season_filter:
                                # Calculate stats for this season only
                                stats_query = text("""
                                    SELECT 
                                        COUNT(*) as matches,
                                        SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)::float / COUNT(*) as draw_rate
                                    FROM matches
                                    WHERE referee_id = :referee_id AND season = :season
                                """)
                                stats_params = {"referee_id": referee_id, "season": season_filter}
                            else:
                                stats_query = text("""
                                    SELECT 
                                        COUNT(*) as matches,
                                        SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END)::float / COUNT(*) as draw_rate
                                    FROM matches
                                    WHERE referee_id = :referee_id
                                """)
                                stats_params = {"referee_id": referee_id}
                            
                            stats_result = db.execute(stats_query, stats_params).fetchone()
                            
                            if stats_result and stats_result.matches > 0:
                                # Get referee name from existing record or use default
                                existing_ref = db.query(RefereeStats).filter(
                                    RefereeStats.referee_id == referee_id
                                ).first()
                                
                                referee_name = existing_ref.referee_name if existing_ref else f"Referee {referee_id}"
                                
                                referee_records.append({
                                    "league_code": league.code,
                                    "season": season_filter or "all",
                                    "referee_id": referee_id,
                                    "referee_name": referee_name,
                                    "matches": int(stats_result.matches),
                                    "avg_cards": float(existing_ref.avg_cards) if existing_ref and existing_ref.avg_cards else 0.0,
                                    "avg_penalties": float(existing_ref.avg_penalties) if existing_ref and existing_ref.avg_penalties else 0.0,
                                    "draw_rate": float(stats_result.draw_rate) if stats_result.draw_rate else 0.0
                                })
                                
                                # Also update/insert into database
                                result = ingest_referee_stats_from_matches(
                                    db, referee_id, save_csv=False  # Don't save individual CSVs
                                )
                                
                                if result.get("success"):
                                    results["successful"] += 1
                                else:
                                    results["failed"] += 1
                            else:
                                results["skipped"] += 1
                                
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to process referee {referee_id}: {e}")
                            results["details"].append({
                                "league_code": league.code,
                                "season": season_filter or "all",
                                "referee_id": referee_id,
                                "error": str(e),
                                "success": False
                            })
                    
                    # Save CSV for this league/season combination
                    if save_csv and referee_records:
                        try:
                            csv_path = _save_referee_csv_batch(db, league.code, season_filter or "all", referee_records)
                            logger.info(f"Saved Referee CSV for {league.code} ({season_filter or 'all'}): {len(referee_records)} referees")
                        except Exception as e:
                            logger.warning(f"Failed to save Referee CSV for {league.code} ({season_filter or 'all'}): {e}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        logger.info(f"Batch referee stats ingestion complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch referee stats ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

