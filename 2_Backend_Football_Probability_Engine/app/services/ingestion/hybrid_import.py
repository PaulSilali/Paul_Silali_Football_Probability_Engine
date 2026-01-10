"""
Hybrid CSV-First Import Utility

This module implements a hybrid approach for importing draw structural data:
1. First, try to import from existing CSV files (fast)
2. Then, check what's missing in the database
3. Finally, calculate missing data from matches table

This provides the best of both worlds: speed when CSV files exist, completeness when they don't.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd

logger = logging.getLogger(__name__)


def find_csv_files(
    data_type: str,
    league_code: Optional[str] = None,
    season: Optional[str] = None,
    base_dir: Optional[Path] = None
) -> List[Path]:
    """
    Find CSV files for a specific data type.
    
    Args:
        data_type: One of 'league_priors', 'elo_ratings', 'h2h_stats', 'league_structure',
                   'odds_movement', 'referee_stats', 'rest_days', 'xg_data', 'weather'
        league_code: Optional league code filter (e.g., 'E0', 'SP1')
        season: Optional season filter (e.g., '2425', '2324')
        base_dir: Base directory to search (defaults to backend root)
    
    Returns:
        List of CSV file paths
    """
    if base_dir is None:
        # Go up from app/services/ingestion to backend root
        base_dir = Path(__file__).parent.parent.parent.parent
    
    # Map data types to folder names
    folder_map = {
        'league_priors': 'League_Priors',
        'elo_ratings': 'Elo_Rating',
        'h2h_stats': 'h2h_stats',
        'league_structure': 'League_structure',
        'odds_movement': 'Odds_Movement',
        'referee_stats': 'Referee',
        'rest_days': 'Rest_Days',
        'xg_data': 'XG Data',  # Fixed: folder name is "XG Data" (capital X, space)
        'weather': 'Weather'
    }
    
    folder_name = folder_map.get(data_type)
    if not folder_name:
        logger.warning(f"Unknown data type: {data_type}")
        return []
    
    # Check both ingestion and cleaned data folders
    ingestion_dir = base_dir / "data" / "1_data_ingestion" / "Draw_structural" / folder_name
    cleaned_dir = base_dir / "data" / "2_Cleaned_data" / "Draw_structural" / folder_name
    
    csv_files = []
    
    for directory in [ingestion_dir, cleaned_dir]:
        if directory.exists():
            # Build pattern
            if league_code and season:
                pattern = f"{league_code}_{season}_*.csv"
            elif league_code:
                pattern = f"{league_code}_*.csv"
            elif season:
                pattern = f"*_{season}_*.csv"
            else:
                pattern = "*.csv"
            
            csv_files.extend(list(directory.glob(pattern)))
    
    # Remove duplicates (same file in both locations)
    csv_files = list(set(csv_files))
    
    logger.info(f"Found {len(csv_files)} CSV files for {data_type} (league={league_code}, season={season})")
    return csv_files


def check_missing_data(
    db: Session,
    data_type: str,
    league_codes: Optional[List[str]] = None,
    seasons: Optional[List[str]] = None
) -> List[Dict]:
    """
    Check what data is missing in the database.
    
    Args:
        db: Database session
        data_type: One of the data types
        league_codes: Optional list of league codes to check
        seasons: Optional list of seasons to check
    
    Returns:
        List of dicts with missing data info: [{"league_code": "E0", "season": "2425"}, ...]
    """
    from app.db.models import League
    
    missing = []
    
    # Get leagues to check
    if league_codes:
        leagues = db.query(League).filter(League.code.in_(league_codes)).all()
    else:
        leagues = db.query(League).all()
    
    # Map data types to table queries
    if data_type == 'league_priors':
        from app.db.models import LeagueDrawPrior
        for league in leagues:
            existing = db.query(LeagueDrawPrior).filter(
                LeagueDrawPrior.league_id == league.id
            ).all()
            existing_seasons = {p.season for p in existing}
            if seasons:
                missing_seasons = set(seasons) - existing_seasons
            else:
                # Check what seasons have matches but no priors
                from app.db.models import Match
                match_seasons = {m.season for m in db.query(Match.season).filter(
                    Match.league_id == league.id
                ).distinct().all() if m.season}
                missing_seasons = match_seasons - existing_seasons
            
            for season in missing_seasons:
                missing.append({"league_code": league.code, "season": season})
    
    # Similar logic for other data types...
    # For now, return empty list (can be expanded)
    
    return missing


def hybrid_import_league_priors(
    db: Session,
    league_codes: Optional[List[str]] = None,
    seasons: Optional[List[str]] = None,
    use_all_leagues: bool = False,
    use_all_seasons: bool = False,
    max_years: Optional[int] = None,
    save_csv: bool = True
) -> Dict:
    """
    Hybrid import for league draw priors: CSV-first, then calculate missing.
    
    Returns:
        Dict with import statistics
    """
    from app.services.ingestion.ingest_league_draw_priors import (
        ingest_league_draw_priors_from_csv,
        batch_ingest_league_priors
    )
    
    results = {
        "csv_imported": 0,
        "csv_failed": 0,
        "calculated": 0,
        "calculated_failed": 0,
        "details": []
    }
    
    # Step 1: Try to import from CSV files
    logger.info("Step 1: Importing from CSV files...")
    csv_files = find_csv_files('league_priors')
    
    for csv_file in csv_files:
        try:
            # Extract league_code and season from filename
            # Format: {league_code}_{season}_draw_priors.csv
            filename = csv_file.stem
            parts = filename.split('_')
            if len(parts) >= 2:
                league_code = parts[0]
                season = parts[1]
                
                # Check if we should process this file
                if league_codes and league_code not in league_codes:
                    continue
                if seasons and season not in seasons:
                    continue
                
                result = ingest_league_draw_priors_from_csv(
                    db, str(csv_file), league_code, season
                )
                
                if result.get("success"):
                    results["csv_imported"] += 1
                    results["details"].append({
                        "source": "csv",
                        "league_code": league_code,
                        "season": season,
                        "status": "success"
                    })
                else:
                    results["csv_failed"] += 1
                    results["details"].append({
                        "source": "csv",
                        "league_code": league_code,
                        "season": season,
                        "status": "failed",
                        "error": result.get("error")
                    })
        except Exception as e:
            logger.error(f"Error importing CSV {csv_file}: {e}", exc_info=True)
            results["csv_failed"] += 1
    
    # Step 2: Check what's missing and calculate from matches
    logger.info("Step 2: Calculating missing data from matches table...")
    missing = check_missing_data(db, 'league_priors', league_codes, seasons)
    
    if missing:
        # Use batch_ingest_league_priors to calculate missing
        # Filter to only missing league/season combinations
        missing_league_codes = list(set(m["league_code"] for m in missing))
        missing_seasons = list(set(m["season"] for m in missing))
        
        result = batch_ingest_league_priors(
            db,
            league_codes=missing_league_codes if missing_league_codes else league_codes,
            season=None,  # Will use missing_seasons
            use_all_leagues=False,
            use_all_seasons=False,
            max_years=max_years,
            save_csv=save_csv
        )
        
        if result.get("success"):
            results["calculated"] = result.get("successful", 0)
            results["calculated_failed"] = result.get("failed", 0)
        else:
            results["calculated_failed"] = len(missing)
    else:
        logger.info("No missing data found - all data imported from CSV")
    
    results["success"] = True
    results["total_imported"] = results["csv_imported"] + results["calculated"]
    
    return results

