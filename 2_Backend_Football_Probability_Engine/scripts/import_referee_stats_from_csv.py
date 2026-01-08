"""
Script to import referee statistics from CSV files into the database.

This script scans the data ingestion folder for referee stats CSV files and imports them
into the referee_stats table.

Usage:
    python scripts/import_referee_stats_from_csv.py
"""
import sys
from pathlib import Path
import pandas as pd
import logging
from sqlalchemy.orm import Session

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import RefereeStats

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_referee_csv_files(data_dir: Path) -> list[Path]:
    """
    Find all referee stats CSV files in the data directory.
    
    Args:
        data_dir: Base data directory
        
    Returns:
        List of CSV file paths
    """
    referee_dir = data_dir / "1_data_ingestion" / "Draw_structural" / "Referee"
    
    if not referee_dir.exists():
        logger.warning(f"Referee stats directory not found: {referee_dir}")
        # Try cleaned data directory as fallback
        cleaned_dir = data_dir / "2_Cleaned_data" / "Draw_structural" / "Referee"
        if cleaned_dir.exists():
            logger.info(f"Using cleaned data directory instead: {cleaned_dir}")
            referee_dir = cleaned_dir
        else:
            return []
    
    csv_files = list(referee_dir.glob("*_referee_stats.csv"))
    logger.info(f"Found {len(csv_files)} referee stats CSV files")
    return sorted(csv_files)


def import_referee_csv_file(db: Session, csv_path: Path) -> dict:
    """
    Import a single referee stats CSV file into the database.
    
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
        required_cols = ['referee_id', 'referee_name', 'matches', 'avg_cards', 'avg_penalties', 'draw_rate']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns in {csv_path.name}: {missing_cols}")
            return {
                "success": False,
                "error": f"Missing columns: {missing_cols}",
                "processed": 0,
                "inserted": 0,
                "updated": 0,
                "errors": 0
            }
        
        inserted = 0
        updated = 0
        errors = 0
        skipped = 0
        
        for idx, row in df.iterrows():
            try:
                referee_id = int(row['referee_id'])
                referee_name = str(row['referee_name']) if pd.notna(row['referee_name']) else None
                matches = int(row['matches']) if pd.notna(row['matches']) else 0
                avg_cards = float(row['avg_cards']) if pd.notna(row['avg_cards']) else None
                avg_penalties = float(row['avg_penalties']) if pd.notna(row['avg_penalties']) else None
                draw_rate = float(row['draw_rate']) if pd.notna(row['draw_rate']) else None
                
                # Validate data
                if matches < 0:
                    logger.warning(f"Invalid matches count ({matches}) for referee_id {referee_id}, skipping")
                    errors += 1
                    continue
                
                if draw_rate is not None and (draw_rate < 0 or draw_rate > 1):
                    logger.warning(f"Invalid draw_rate ({draw_rate}) for referee_id {referee_id}, skipping")
                    errors += 1
                    continue
                
                if avg_cards is not None and avg_cards < 0:
                    logger.warning(f"Invalid avg_cards ({avg_cards}) for referee_id {referee_id}, skipping")
                    errors += 1
                    continue
                
                if avg_penalties is not None and avg_penalties < 0:
                    logger.warning(f"Invalid avg_penalties ({avg_penalties}) for referee_id {referee_id}, skipping")
                    errors += 1
                    continue
                
                # Check if record already exists
                existing = db.query(RefereeStats).filter(
                    RefereeStats.referee_id == referee_id
                ).first()
                
                if existing:
                    # Update existing record
                    existing.referee_name = referee_name
                    existing.matches = matches
                    existing.avg_cards = avg_cards
                    existing.avg_penalties = avg_penalties
                    existing.draw_rate = draw_rate
                    updated += 1
                else:
                    # Insert new record
                    referee = RefereeStats(
                        referee_id=referee_id,
                        referee_name=referee_name,
                        matches=matches,
                        avg_cards=avg_cards,
                        avg_penalties=avg_penalties,
                        draw_rate=draw_rate
                    )
                    db.add(referee)
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
    """Main function to import all referee stats CSV files."""
    # Get data directory (assuming script is in scripts/ folder)
    script_dir = Path(__file__).parent
    backend_root = script_dir.parent
    data_dir = backend_root / "data"
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    # Find all CSV files
    csv_files = find_referee_csv_files(data_dir)
    
    if not csv_files:
        logger.warning("No referee stats CSV files found!")
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
            result = import_referee_csv_file(db, csv_file)
            
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
        total_records = db.query(RefereeStats).count()
        logger.info(f"Total referee records in database: {total_records}")
        
    except Exception as e:
        logger.error(f"Critical error during import: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

