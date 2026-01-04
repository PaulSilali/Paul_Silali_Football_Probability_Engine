"""
Ingest league structure metadata (size, relegation zones, promotion zones)
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import League
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Default league structure mappings (can be enhanced with API scraping)
# Format: (total_teams, relegation_zones, promotion_zones, playoff_zones)
DEFAULT_LEAGUE_STRUCTURE = {
    'E0': (20, 3, 3, 0),  # Premier League
    'E1': (24, 3, 3, 4),  # Championship (3 auto + 4 playoff)
    'E2': (24, 4, 4, 4),  # League One
    'E3': (24, 4, 4, 4),  # League Two
    'SP1': (20, 3, 3, 0),  # La Liga
    'SP2': (22, 4, 4, 0),  # La Liga 2
    'D1': (18, 2, 2, 1),  # Bundesliga (2 auto + 1 playoff)
    'D2': (18, 3, 3, 0),  # 2. Bundesliga
    'I1': (20, 3, 3, 0),  # Serie A
    'I2': (20, 4, 4, 0),  # Serie B
    'F1': (18, 3, 3, 0),  # Ligue 1
    'F2': (20, 4, 4, 0),  # Ligue 2
    'N1': (18, 0, 0, 0),  # Eredivisie (no relegation in some seasons)
    'P1': (18, 3, 3, 0),  # Primeira Liga
    'SC0': (12, 1, 1, 0),  # Scottish Premiership
    'SC1': (10, 1, 1, 0),  # Scottish Championship
    'SC2': (10, 1, 1, 0),  # Scottish League One
    'SC3': (10, 1, 1, 0),  # Scottish League Two
    'B1': (16, 2, 2, 0),  # Pro League
    'T1': (20, 4, 4, 0),  # Super Lig
    'G1': (14, 2, 2, 0),  # Super League 1
    'A1': (12, 2, 2, 0),  # Austrian Bundesliga
    'SW1': (12, 2, 2, 0),  # Swiss Super League
    'DK1': (12, 2, 2, 0),  # Danish Superliga
    'SWE1': (16, 2, 2, 0),  # Allsvenskan
    'NO1': (16, 2, 2, 0),  # Eliteserien
    'FIN1': (12, 2, 2, 0),  # Veikkausliiga
    'PL1': (18, 3, 3, 0),  # Ekstraklasa
    'RO1': (16, 2, 2, 0),  # Liga 1
    'RUS1': (16, 2, 2, 0),  # Premier League
    'CZE1': (16, 2, 2, 0),  # First League
    'CRO1': (10, 1, 1, 0),  # Prva HNL
    'SRB1': (16, 2, 2, 0),  # SuperLiga
    'UKR1': (16, 2, 2, 0),  # Premier League
    'IRL1': (10, 1, 1, 0),  # Premier Division
    'ARG1': (28, 4, 4, 0),  # Primera Division
    'BRA1': (20, 4, 4, 0),  # Serie A
    'MEX1': (18, 3, 3, 0),  # Liga MX
    'USA1': (29, 0, 0, 0),  # MLS (no relegation)
    'CHN1': (16, 2, 2, 0),  # Super League
    'JPN1': (20, 3, 3, 0),  # J-League
    'KOR1': (12, 1, 1, 0),  # K League 1
    'AUS1': (12, 0, 0, 0),  # A-League (no relegation)
}


def _save_league_structure_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    structure_records: List[Dict]
) -> Path:
    """
    Save CSV file with league structure data for a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        structure_records: List of dictionaries with structure data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not structure_records:
            raise ValueError("No structure records to save")
        
        # Create directory structure
        base_dir = Path("data/1_data_ingestion/Draw_structural/League_structure")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DataFrame from all records
        df = pd.DataFrame(structure_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "total_teams", "relegation_zones", 
                "promotion_zones", "playoff_zones"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_league_structure.csv
        filename = f"{league_code}_{season}_league_structure.csv"
        csv_path = base_dir / filename
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved batch league structure CSV for {league_code} ({season}): {len(structure_records)} records -> {csv_path}")
        return csv_path
    
    except Exception as e:
        logger.error(f"Error saving batch league structure CSV: {e}", exc_info=True)
        raise


def ingest_league_structure(
    db: Session,
    league_code: str,
    season: str,
    total_teams: Optional[int] = None,
    relegation_zones: Optional[int] = None,
    promotion_zones: Optional[int] = None,
    playoff_zones: Optional[int] = None,
    save_csv: bool = True
) -> Dict:
    """
    Ingest league structure metadata for a specific league and season.
    
    Args:
        db: Database session
        league_code: League code (e.g., 'E0')
        season: Season identifier (e.g., '2425')
        total_teams: Total number of teams (if None, uses default)
        relegation_zones: Number of relegation zones (if None, uses default)
        promotion_zones: Number of promotion zones (if None, uses default)
        playoff_zones: Number of playoff zones (if None, uses default)
        save_csv: Whether to save CSV file
    
    Returns:
        Dict with ingestion result
    """
    try:
        # Get league
        league = db.query(League).filter(League.code == league_code).first()
        if not league:
            return {"success": False, "error": f"League {league_code} not found"}
        
        # Get default structure if not provided
        if league_code in DEFAULT_LEAGUE_STRUCTURE:
            default_total, default_relegation, default_promotion, default_playoff = DEFAULT_LEAGUE_STRUCTURE[league_code]
            total_teams = total_teams or default_total
            relegation_zones = relegation_zones if relegation_zones is not None else default_relegation
            promotion_zones = promotion_zones if promotion_zones is not None else default_promotion
            playoff_zones = playoff_zones if playoff_zones is not None else default_playoff
        else:
            # Use provided values or defaults
            total_teams = total_teams or 20
            relegation_zones = relegation_zones if relegation_zones is not None else 3
            promotion_zones = promotion_zones if promotion_zones is not None else 3
            playoff_zones = playoff_zones if playoff_zones is not None else 0
        
        # Insert or update league structure
        insert_query = text("""
            INSERT INTO league_structure 
            (league_id, season, total_teams, relegation_zones, promotion_zones, playoff_zones, created_at, updated_at)
            VALUES (:league_id, :season, :total_teams, :relegation_zones, :promotion_zones, :playoff_zones, NOW(), NOW())
            ON CONFLICT (league_id, season) DO UPDATE SET
                total_teams = EXCLUDED.total_teams,
                relegation_zones = EXCLUDED.relegation_zones,
                promotion_zones = EXCLUDED.promotion_zones,
                playoff_zones = EXCLUDED.playoff_zones,
                updated_at = NOW()
        """)
        
        db.execute(insert_query, {
            "league_id": league.id,
            "season": season,
            "total_teams": total_teams,
            "relegation_zones": relegation_zones,
            "promotion_zones": promotion_zones,
            "playoff_zones": playoff_zones
        })
        db.commit()
        
        logger.info(f"Ingested league structure for {league_code} ({season}): {total_teams} teams, {relegation_zones} relegation, {promotion_zones} promotion")
        
        result = {
            "success": True,
            "league_code": league_code,
            "season": season,
            "total_teams": total_teams,
            "relegation_zones": relegation_zones,
            "promotion_zones": promotion_zones,
            "playoff_zones": playoff_zones
        }
        
        # Save CSV if requested
        if save_csv:
            try:
                csv_path = _save_league_structure_csv_batch(
                    db, league_code, season, [result]
                )
                result["csv_path"] = str(csv_path)
            except Exception as e:
                logger.warning(f"Failed to save league structure CSV: {e}")
        
        return result
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting league structure: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def batch_ingest_league_structure(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest league structure for specified leagues and seasons.
    
    Args:
        db: Database session
        league_codes: List of league codes to process
        use_all_leagues: If True, process all leagues
        season: Specific season to process
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
        
        logger.info(f"Batch processing league structure for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    results["total"] += 1
                    
                    # Get structure data
                    structure_result = ingest_league_structure(
                        db=db,
                        league_code=league.code,
                        season=season_filter or "all",
                        save_csv=False  # Will save batch CSV instead
                    )
                    
                    if structure_result.get("success"):
                        results["successful"] += 1
                        
                        # Collect for batch CSV
                        structure_records = [{
                            "league_code": league.code,
                            "season": season_filter or "all",
                            "total_teams": structure_result.get("total_teams"),
                            "relegation_zones": structure_result.get("relegation_zones"),
                            "promotion_zones": structure_result.get("promotion_zones"),
                            "playoff_zones": structure_result.get("playoff_zones")
                        }]
                        
                        # Save CSV for this league/season combination
                        if save_csv:
                            try:
                                csv_path = _save_league_structure_csv_batch(
                                    db, league.code, season_filter or "all", structure_records
                                )
                                logger.info(f"Saved League Structure CSV for {league.code} ({season_filter or 'all'}): 1 record")
                            except Exception as e:
                                logger.warning(f"Failed to save League Structure CSV for {league.code} ({season_filter or 'all'}): {e}")
                    else:
                        results["failed"] += 1
                        logger.warning(f"Failed to ingest league structure for {league.code} ({season_filter}): {structure_result.get('error')}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    results["failed"] += 1
                    continue
        
        logger.info(f"Batch league structure ingestion complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch league structure ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

