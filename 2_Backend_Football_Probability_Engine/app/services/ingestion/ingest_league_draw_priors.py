"""
Ingest league draw priors from historical CSV data (football-data.co.uk format)

This service calculates historical draw rates per league/season and stores them
in the league_draw_priors table.
"""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import League, LeagueDrawPrior
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def ingest_league_draw_priors_from_csv(
    db: Session,
    csv_path: str,
    league_code: str,
    season: str = "ALL"
) -> dict:
    """
    Ingest league draw priors from CSV file.
    
    Args:
        db: Database session
        csv_path: Path to CSV file (football-data.co.uk format)
        league_code: League code (e.g., 'E0', 'SP1')
        season: Season identifier (default: 'ALL' for all seasons)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Calculate draw rate
        # football-data.co.uk format: FTHG = Full Time Home Goals, FTAG = Full Time Away Goals
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            df['is_draw'] = df['FTHG'] == df['FTAG']
            draw_rate = df['is_draw'].mean()
            sample_size = len(df)
        else:
            logger.error(f"CSV missing required columns (FTHG, FTAG)")
            return {"success": False, "error": "Missing required columns"}
        
        # Get league ID
        league = db.query(League).filter(League.code == league_code).first()
        if not league:
            logger.error(f"League {league_code} not found")
            return {"success": False, "error": f"League {league_code} not found"}
        
        # Insert or update
        existing = db.query(LeagueDrawPrior).filter(
            LeagueDrawPrior.league_id == league.id,
            LeagueDrawPrior.season == season
        ).first()
        
        if existing:
            existing.draw_rate = float(draw_rate)
            existing.sample_size = sample_size
        else:
            prior = LeagueDrawPrior(
                league_id=league.id,
                season=season,
                draw_rate=float(draw_rate),
                sample_size=sample_size
            )
            db.add(prior)
        
        db.commit()
        
        logger.info(f"Ingested draw prior for {league_code} ({season}): {draw_rate:.3f} (n={sample_size})")
        
        return {
            "success": True,
            "league_code": league_code,
            "season": season,
            "draw_rate": float(draw_rate),
            "sample_size": sample_size
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting league draw priors: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_priors_csv(
    db: Session,
    league_code: str,
    league_name: str,
    season: str,
    matches_df: pd.DataFrame
) -> Path:
    """
    Save CSV file with match data used for draw prior calculation.
    
    Args:
        db: Database session
        league_code: League code
        league_name: League name
        season: Season identifier
        matches_df: DataFrame with match data
    
    Returns:
        Path to saved CSV file
    """
    try:
        # Create directory structure: data/1_data_ingestion/Draw_structural/League_Priors
        base_dir = Path("data/1_data_ingestion/Draw_structural/League_Priors")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        safe_league_name = league_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_league_name = ''.join(c for c in safe_league_name if c.isalnum() or c in ('_', '-'))
        
        # Filename format: {league_code}_{season}_draw_priors.csv
        # Example: E0_2324_draw_priors.csv
        filename = f"{league_code}_{season}_draw_priors.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        matches_df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved draw priors CSV: {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving draw priors CSV: {e}", exc_info=True)
        raise


def ingest_from_matches_table(
    db: Session,
    league_code: str,
    season: str = "ALL",
    save_csv: bool = True
) -> dict:
    """
    Calculate league draw priors from existing matches table.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Get league
        league = db.query(League).filter(League.code == league_code).first()
        if not league:
            return {"success": False, "error": f"League {league_code} not found"}
        
        # Query matches
        query = text("""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws
            FROM matches
            WHERE league_id = :league_id
        """)
        
        if season != "ALL":
            query = text("""
                SELECT 
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws
                FROM matches
                WHERE league_id = :league_id AND season = :season
            """)
            params = {"league_id": league.id, "season": season}
        else:
            params = {"league_id": league.id}
        
        result = db.execute(query, params).fetchone()
        
        if result and result.total_matches > 0:
            draw_rate = result.draws / result.total_matches
            
            # Fetch match data for CSV export if save_csv is True
            csv_path = None
            if save_csv:
                try:
                    # Query match details for CSV export
                    if season == "ALL":
                        matches_query = text("""
                            SELECT 
                                m.match_date,
                                ht.name as home_team,
                                at.name as away_team,
                                m.home_goals as FTHG,
                                m.away_goals as FTAG,
                                m.result as FTR
                            FROM matches m
                            JOIN teams ht ON m.home_team_id = ht.id
                            JOIN teams at ON m.away_team_id = at.id
                            WHERE m.league_id = :league_id
                            ORDER BY m.match_date
                        """)
                        matches_params = {"league_id": league.id}
                    else:
                        matches_query = text("""
                            SELECT 
                                m.match_date,
                                ht.name as home_team,
                                at.name as away_team,
                                m.home_goals as FTHG,
                                m.away_goals as FTAG,
                                m.result as FTR
                            FROM matches m
                            JOIN teams ht ON m.home_team_id = ht.id
                            JOIN teams at ON m.away_team_id = at.id
                            WHERE m.league_id = :league_id AND m.season = :season
                            ORDER BY m.match_date
                        """)
                        matches_params = {"league_id": league.id, "season": season}
                    
                    matches_result = db.execute(matches_query, matches_params).fetchall()
                    
                    if matches_result:
                        # Convert to DataFrame
                        matches_data = []
                        for row in matches_result:
                            # Access columns by index (most reliable with text() queries)
                            # Row order: match_date[0], home_team[1], away_team[2], FTHG[3], FTAG[4], FTR[5]
                            match_date = row[0] if len(row) > 0 else None
                            home_team = row[1] if len(row) > 1 else None
                            away_team = row[2] if len(row) > 2 else None
                            fthg = row[3] if len(row) > 3 else None
                            ftag = row[4] if len(row) > 4 else None
                            ftr = row[5] if len(row) > 5 else None
                            
                            matches_data.append({
                                "Date": match_date.strftime("%Y-%m-%d") if match_date else "",
                                "HomeTeam": str(home_team) if home_team else "",
                                "AwayTeam": str(away_team) if away_team else "",
                                "FTHG": int(fthg) if fthg is not None else "",
                                "FTAG": int(ftag) if ftag is not None else "",
                                "FTR": str(ftr.value) if hasattr(ftr, 'value') else (str(ftr) if ftr else ""),
                                "is_draw": 1 if (ftr == "D" or (hasattr(ftr, 'value') and ftr.value == "D") or (isinstance(ftr, str) and ftr.upper() == "D")) else 0
                            })
                        
                        matches_df = pd.DataFrame(matches_data)
                        
                        # Save CSV
                        csv_path = _save_priors_csv(
                            db, league_code, league.name, season, matches_df
                        )
                except Exception as e:
                    logger.warning(f"Failed to save CSV for {league_code} ({season}): {e}")
                    # Don't fail the ingestion if CSV save fails
            
            # Insert or update
            existing = db.query(LeagueDrawPrior).filter(
                LeagueDrawPrior.league_id == league.id,
                LeagueDrawPrior.season == season
            ).first()
            
            if existing:
                existing.draw_rate = float(draw_rate)
                existing.sample_size = result.total_matches
            else:
                prior = LeagueDrawPrior(
                    league_id=league.id,
                    season=season,
                    draw_rate=float(draw_rate),
                    sample_size=result.total_matches
                )
                db.add(prior)
            
            db.commit()
            
            result_dict = {
                "success": True,
                "league_code": league_code,
                "season": season,
                "draw_rate": float(draw_rate),
                "sample_size": result.total_matches
            }
            
            if csv_path:
                result_dict["csv_path"] = str(csv_path)
            
            return result_dict
        else:
            return {"success": False, "error": "No matches found"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating league draw priors: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_ingest_league_priors(
    db: Session,
    league_codes: list[str] = None,
    season: str = "ALL",
    use_all_leagues: bool = False,
    use_all_seasons: bool = False,
    max_years: int = None,
    save_csv: bool = True
) -> dict:
    """
    Batch ingest league draw priors for multiple leagues.
    
    Args:
        db: Database session
        league_codes: List of league codes to process (ignored if use_all_leagues=True)
        season: Season identifier (default: 'ALL' for all seasons, ignored if use_all_seasons=True)
        use_all_leagues: If True, process all leagues that have matches
        use_all_seasons: If True, calculate priors for each season separately
        max_years: Maximum years to look back (only used if use_all_seasons=True)
    
    Returns:
        Dict with batch ingestion statistics
    """
    try:
        results = {
            "success": True,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
            "errors": []
        }
        
        # Get leagues to process
        if use_all_leagues:
            # Get all leagues that have matches
            leagues_query = text("""
                SELECT DISTINCT l.id, l.code, l.name
                FROM leagues l
                JOIN matches m ON l.id = m.league_id
                ORDER BY l.code
            """)
            leagues_result = db.execute(leagues_query).fetchall()
            leagues_to_process = [(row.id, row.code, row.name) for row in leagues_result]
            logger.info(f"Found {len(leagues_to_process)} leagues with matches to process")
        else:
            if not league_codes:
                return {"success": False, "error": "No league codes provided and use_all_leagues is False"}
            
            # Get league IDs for provided codes
            leagues_to_process = []
            for code in league_codes:
                league = db.query(League).filter(League.code == code).first()
                if league:
                    leagues_to_process.append((league.id, league.code, league.name))
                else:
                    results["errors"].append(f"League {code} not found")
                    results["failed"] += 1
        
        if not leagues_to_process:
            return {
                "success": False,
                "error": "No leagues found to process",
                **results
            }
        
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
            
            logger.info(f"Processing {len(seasons_to_process)} seasons: {seasons_to_process}")
        else:
            seasons_to_process = [season]
        
        # Process each league and season combination
        for league_id, league_code, league_name in leagues_to_process:
            for season_to_process in seasons_to_process:
                try:
                    results["processed"] += 1
                    
                    # Query matches for this league and season
                    if season_to_process == "ALL":
                        query = text("""
                            SELECT 
                                COUNT(*) as total_matches,
                                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws
                            FROM matches
                            WHERE league_id = :league_id
                        """)
                        params = {"league_id": league_id}
                    else:
                        query = text("""
                            SELECT 
                                COUNT(*) as total_matches,
                                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws
                            FROM matches
                            WHERE league_id = :league_id AND season = :season
                        """)
                        params = {"league_id": league_id, "season": season_to_process}
                    
                    result = db.execute(query, params).fetchone()
                    
                    if result and result.total_matches > 0:
                        draw_rate = result.draws / result.total_matches
                        
                        # Save CSV if requested
                        csv_path = None
                        if save_csv:
                            try:
                                # Query match details for CSV export
                                if season_to_process == "ALL":
                                    matches_query = text("""
                                        SELECT 
                                            m.match_date,
                                            ht.name as home_team,
                                            at.name as away_team,
                                            m.home_goals as FTHG,
                                            m.away_goals as FTAG,
                                            m.result as FTR
                                        FROM matches m
                                        JOIN teams ht ON m.home_team_id = ht.id
                                        JOIN teams at ON m.away_team_id = at.id
                                        WHERE m.league_id = :league_id
                                        ORDER BY m.match_date
                                    """)
                                    matches_params = {"league_id": league_id}
                                else:
                                    matches_query = text("""
                                        SELECT 
                                            m.match_date,
                                            ht.name as home_team,
                                            at.name as away_team,
                                            m.home_goals as FTHG,
                                            m.away_goals as FTAG,
                                            m.result as FTR
                                        FROM matches m
                                        JOIN teams ht ON m.home_team_id = ht.id
                                        JOIN teams at ON m.away_team_id = at.id
                                        WHERE m.league_id = :league_id AND m.season = :season
                                        ORDER BY m.match_date
                                    """)
                                    matches_params = {"league_id": league_id, "season": season_to_process}
                                
                                matches_result = db.execute(matches_query, matches_params).fetchall()
                                
                                if matches_result:
                                    # Convert to DataFrame
                                    matches_data = []
                                    for row in matches_result:
                                        # Access columns by index (most reliable with text() queries)
                                        # Row order: match_date[0], home_team[1], away_team[2], FTHG[3], FTAG[4], FTR[5]
                                        match_date = row[0] if len(row) > 0 else None
                                        home_team = row[1] if len(row) > 1 else None
                                        away_team = row[2] if len(row) > 2 else None
                                        fthg = row[3] if len(row) > 3 else None
                                        ftag = row[4] if len(row) > 4 else None
                                        ftr = row[5] if len(row) > 5 else None
                                        
                                        matches_data.append({
                                            "Date": match_date.strftime("%Y-%m-%d") if match_date else "",
                                            "HomeTeam": str(home_team) if home_team else "",
                                            "AwayTeam": str(away_team) if away_team else "",
                                            "FTHG": int(fthg) if fthg is not None else "",
                                            "FTAG": int(ftag) if ftag is not None else "",
                                            "FTR": str(ftr.value) if hasattr(ftr, 'value') else (str(ftr) if ftr else ""),
                                            "is_draw": 1 if (ftr == "D" or (hasattr(ftr, 'value') and ftr.value == "D") or (isinstance(ftr, str) and ftr.upper() == "D")) else 0
                                        })
                                    
                                    matches_df = pd.DataFrame(matches_data)
                                    
                                    # Save CSV
                                    csv_path = _save_priors_csv(
                                        db, league_code, league_name, season_to_process, matches_df
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to save CSV for {league_code} ({season_to_process}): {e}")
                                # Don't fail the ingestion if CSV save fails
                        
                        # Insert or update
                        existing = db.query(LeagueDrawPrior).filter(
                            LeagueDrawPrior.league_id == league_id,
                            LeagueDrawPrior.season == season_to_process
                        ).first()
                        
                        if existing:
                            existing.draw_rate = float(draw_rate)
                            existing.sample_size = result.total_matches
                            action = "updated"
                        else:
                            prior = LeagueDrawPrior(
                                league_id=league_id,
                                season=season_to_process,
                                draw_rate=float(draw_rate),
                                sample_size=result.total_matches
                            )
                            db.add(prior)
                            action = "created"
                        
                        db.commit()
                        
                        detail_item = {
                            "league_code": league_code,
                            "league_name": league_name,
                            "season": season_to_process,
                            "draw_rate": float(draw_rate),
                            "sample_size": result.total_matches,
                            "action": action,
                            "success": True
                        }
                        
                        if csv_path:
                            detail_item["csv_path"] = str(csv_path)
                        
                        results["successful"] += 1
                        results["details"].append(detail_item)
                        
                        logger.info(f"✓ {action.capitalize()} prior for {league_code} ({season_to_process}): {draw_rate:.3f} (n={result.total_matches})")
                    else:
                        results["skipped"] += 1
                        results["details"].append({
                            "league_code": league_code,
                            "league_name": league_name,
                            "season": season_to_process,
                            "success": False,
                            "error": "No matches found"
                        })
                        logger.warning(f"⚠ Skipped {league_code} ({season_to_process}): No matches found")
                
                except Exception as e:
                    db.rollback()
                    results["failed"] += 1
                    error_msg = str(e)
                    results["errors"].append(f"{league_code} ({season_to_process}): {error_msg}")
                    results["details"].append({
                        "league_code": league_code,
                        "league_name": league_name,
                        "season": season_to_process,
                        "success": False,
                        "error": error_msg
                    })
                    logger.error(f"✗ Failed {league_code} ({season_to_process}): {error_msg}")
        
        # Set overall success based on results
        if results["failed"] > 0 and results["successful"] == 0:
            results["success"] = False
        elif results["successful"] > 0:
            results["success"] = True
        
        logger.info(f"Batch ingestion complete: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped out of {results['processed']} processed")
        
        return results
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error in batch ingestion: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
            "errors": [str(e)]
        }

