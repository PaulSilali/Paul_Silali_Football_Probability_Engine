"""
Script to import H2H statistics from CSV files into the database.

This script scans the cleaned data folder for H2H stats CSV files and imports them
into the h2h_draw_stats table.

Usage:
    python scripts/import_h2h_stats_from_csv.py
"""
import sys
from pathlib import Path
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import Team, H2HDrawStats, League
from app.services.ingestion.ingest_h2h_stats import ingest_h2h_from_csv
from app.services.ingestion.draw_structural_validation import DrawStructuralValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_h2h_csv_files(data_dir: Path) -> list[Path]:
    """
    Find all H2H stats CSV files in the cleaned data directory.
    
    Args:
        data_dir: Base data directory
        
    Returns:
        List of CSV file paths
    """
    cleaned_dir = data_dir / "2_Cleaned_data" / "Draw_structural" / "h2h_stats"
    
    if not cleaned_dir.exists():
        logger.warning(f"H2H stats directory not found: {cleaned_dir}")
        # Try ingestion directory as fallback
        ingestion_dir = data_dir / "1_data_ingestion" / "Draw_structural" / "h2h_stats"
        if ingestion_dir.exists():
            logger.info(f"Using ingestion directory instead: {ingestion_dir}")
            cleaned_dir = ingestion_dir
        else:
            return []
    
    csv_files = list(cleaned_dir.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} H2H stats CSV files")
    return sorted(csv_files)


def import_h2h_csv_file(db: Session, csv_path: Path) -> dict:
    """
    Import a single H2H stats CSV file into the database.
    
    Args:
        db: Database session
        csv_path: Path to CSV file
        
    Returns:
        Dict with import statistics
    """
    try:
        logger.info(f"Processing CSV file: {csv_path.name}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['home_team_id', 'away_team_id', 'matches_played', 'draw_count']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns in {csv_path.name}: {missing_cols}")
            return {"success": False, "error": f"Missing columns: {missing_cols}", "processed": 0, "inserted": 0, "updated": 0, "errors": 0}
        
        inserted = 0
        updated = 0
        errors = 0
        skipped = 0
        
        for idx, row in df.iterrows():
            try:
                home_team_id = int(row['home_team_id'])
                away_team_id = int(row['away_team_id'])
                matches_played = int(row['matches_played'])
                draw_count = int(row['draw_count'])
                draw_rate = float(row.get('draw_rate', 0.0)) if pd.notna(row.get('draw_rate')) else 0.0
                avg_goals = float(row.get('avg_goals', 0.0)) if pd.notna(row.get('avg_goals')) else None
                
                # Validate H2H stats
                context = f" (home_team_id={home_team_id}, away_team_id={away_team_id})"
                is_valid, error_msg = DrawStructuralValidator.validate_h2h_consistency(
                    matches_played, draw_count, draw_rate, context
                )
                if not is_valid:
                    logger.warning(f"Invalid H2H stats for teams {home_team_id} vs {away_team_id}: {error_msg}")
                    errors += 1
                    continue
                
                # Verify teams exist
                home_team = db.query(Team).filter(Team.id == home_team_id).first()
                away_team = db.query(Team).filter(Team.id == away_team_id).first()
                if not home_team or not away_team:
                    logger.warning(f"Team IDs {home_team_id} or {away_team_id} not found in database, skipping")
                    skipped += 1
                    continue
                
                # Check if record already exists
                existing = db.query(H2HDrawStats).filter(
                    H2HDrawStats.team_home_id == home_team_id,
                    H2HDrawStats.team_away_id == away_team_id
                ).first()
                
                if existing:
                    # Update existing record
                    existing.matches_played = matches_played
                    existing.draw_count = draw_count
                    existing.avg_goals = avg_goals
                    updated += 1
                else:
                    # Insert new record
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
                logger.error(f"Error processing row {idx} in {csv_path.name}: {e}", exc_info=True)
                errors += 1
                continue
        
        # Commit all changes for this file
        db.commit()
        
        logger.info(f"✓ {csv_path.name}: {inserted} inserted, {updated} updated, {skipped} skipped, {errors} errors")
        
        return {
            "success": True,
            "file": csv_path.name,
            "processed": len(df),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing CSV file {csv_path.name}: {e}", exc_info=True)
        return {"success": False, "file": csv_path.name, "error": str(e)}


def main():
    """Main function to import all H2H stats CSV files."""
    # Get data directory (assuming script is in scripts/ folder)
    script_dir = Path(__file__).parent
    backend_root = script_dir.parent
    data_dir = backend_root / "data"
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    # Find all CSV files
    csv_files = find_h2h_csv_files(data_dir)
    
    if not csv_files:
        logger.warning("No H2H stats CSV files found!")
        return
    
    # Initialize database session
    db = SessionLocal()
    
    try:
        total_stats = {
            "total_files": len(csv_files),
            "successful_files": 0,
            "failed_files": 0,
            "total_inserted": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "total_errors": 0
        }
        
        logger.info(f"Starting import of {len(csv_files)} CSV files...")
        
        # Process each CSV file
        for csv_file in csv_files:
            result = import_h2h_csv_file(db, csv_file)
            
            if result.get("success"):
                total_stats["successful_files"] += 1
                total_stats["total_inserted"] += result.get("inserted", 0)
                total_stats["total_updated"] += result.get("updated", 0)
                total_stats["total_skipped"] += result.get("skipped", 0)
                total_stats["total_errors"] += result.get("errors", 0)
            else:
                total_stats["failed_files"] += 1
                total_stats["total_errors"] += 1
        
        # Print summary
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total files processed: {total_stats['total_files']}")
        logger.info(f"Successful: {total_stats['successful_files']}")
        logger.info(f"Failed: {total_stats['failed_files']}")
        logger.info(f"Total records inserted: {total_stats['total_inserted']}")
        logger.info(f"Total records updated: {total_stats['total_updated']}")
        logger.info(f"Total records skipped: {total_stats['total_skipped']}")
        logger.info(f"Total errors: {total_stats['total_errors']}")
        logger.info("=" * 60)
        
        # Verify database population
        total_records = db.query(H2HDrawStats).count()
        logger.info(f"Total H2H records in database: {total_records}")
        
    except Exception as e:
        logger.error(f"Critical error during import: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

