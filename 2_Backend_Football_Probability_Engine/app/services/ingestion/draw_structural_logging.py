"""
Logging utility for draw structural data ingestion
Writes logs to 01_logs folders in both ingestion and cleaned data directories
"""
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def write_draw_structural_log(
    data_type: str,
    summary: Dict,
    ingestion_log_dir: Optional[Path] = None,
    cleaned_log_dir: Optional[Path] = None
) -> tuple[Optional[Path], Optional[Path]]:
    """
    Write comprehensive ingestion log for draw structural data.
    
    Args:
        data_type: Type of data (e.g., 'Team_Form', 'Elo_Rating', 'h2h_stats')
        summary: Dictionary containing ingestion summary information
        ingestion_log_dir: Optional path to ingestion logs directory
        cleaned_log_dir: Optional path to cleaned data logs directory
    
    Returns:
        Tuple of (ingestion_log_path, cleaned_log_path) - paths may be None if directories not provided
    """
    # Resolve backend root if paths not provided
    if ingestion_log_dir is None:
        backend_root = Path(__file__).parent.parent.parent.parent
        ingestion_log_dir = backend_root / "data" / "1_data_ingestion" / "Draw_structural" / "01_logs"
    
    if cleaned_log_dir is None:
        backend_root = Path(__file__).parent.parent.parent.parent
        cleaned_log_dir = backend_root / "data" / "2_Cleaned_data" / "Draw_structural" / "01_logs"
    
    # Create log directories
    ingestion_log_dir.mkdir(parents=True, exist_ok=True)
    cleaned_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{data_type}_{timestamp}_INGESTION_LOG.txt"
    
    ingestion_log_path = ingestion_log_dir / log_filename
    cleaned_log_path = cleaned_log_dir / log_filename
    
    # Build comprehensive log content
    log_lines = []
    log_lines.append("=" * 80)
    log_lines.append(f"DRAW STRUCTURAL DATA INGESTION LOG - {data_type.upper()}")
    log_lines.append("=" * 80)
    log_lines.append(f"Data Type: {data_type}")
    log_lines.append(f"Ingestion Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append("")
    
    # Status summary
    log_lines.append("STATUS SUMMARY")
    log_lines.append("-" * 80)
    success = summary.get("success", False)
    status_icon = "✓ SUCCESS" if success else "✗ FAILED"
    log_lines.append(f"Status: {status_icon}")
    log_lines.append(f"Total Processed: {summary.get('total', 0):,}")
    log_lines.append(f"Successful: {summary.get('successful', 0):,}")
    log_lines.append(f"Failed: {summary.get('failed', 0):,}")
    log_lines.append(f"Skipped: {summary.get('skipped', 0):,}")
    log_lines.append("")
    
    # Details section
    if summary.get("details"):
        log_lines.append("DETAILS")
        log_lines.append("-" * 80)
        details = summary.get("details", [])
        for detail in details[:50]:  # Limit to first 50 details
            log_lines.append(f"  - {detail}")
        if len(details) > 50:
            log_lines.append(f"  ... and {len(details) - 50} more entries")
        log_lines.append("")
    
    # Errors section
    if summary.get("errors"):
        log_lines.append("ERRORS")
        log_lines.append("-" * 80)
        errors = summary.get("errors", [])
        for error in errors[:20]:  # Limit to first 20 errors
            log_lines.append(f"  ✗ {error}")
        if len(errors) > 20:
            log_lines.append(f"  ... and {len(errors) - 20} more errors")
        log_lines.append("")
    
    # Warnings section
    if summary.get("warnings"):
        log_lines.append("WARNINGS")
        log_lines.append("-" * 80)
        warnings = summary.get("warnings", [])
        for warning in warnings[:20]:  # Limit to first 20 warnings
            log_lines.append(f"  ⚠ {warning}")
        if len(warnings) > 20:
            log_lines.append(f"  ... and {len(warnings) - 20} more warnings")
        log_lines.append("")
    
    # CSV files saved section
    if summary.get("csv_files_saved"):
        log_lines.append("CSV FILES SAVED")
        log_lines.append("-" * 80)
        csv_files = summary.get("csv_files_saved", [])
        for csv_file in csv_files[:30]:  # Limit to first 30 files
            log_lines.append(f"  ✓ {csv_file}")
        if len(csv_files) > 30:
            log_lines.append(f"  ... and {len(csv_files) - 30} more files")
        log_lines.append("")
    
    # Database updates section
    if summary.get("db_records_inserted") or summary.get("db_records_updated"):
        log_lines.append("DATABASE UPDATES")
        log_lines.append("-" * 80)
        log_lines.append(f"Records Inserted: {summary.get('db_records_inserted', 0):,}")
        log_lines.append(f"Records Updated: {summary.get('db_records_updated', 0):,}")
        log_lines.append("")
    
    # Execution time
    if summary.get("execution_time_seconds"):
        log_lines.append("PERFORMANCE")
        log_lines.append("-" * 80)
        exec_time = summary.get("execution_time_seconds", 0)
        log_lines.append(f"Execution Time: {exec_time:.2f} seconds")
        if summary.get("total", 0) > 0:
            avg_time = exec_time / summary.get("total", 1)
            log_lines.append(f"Average Time per Record: {avg_time:.4f} seconds")
        log_lines.append("")
    
    log_lines.append("=" * 80)
    log_lines.append("END OF LOG")
    log_lines.append("=" * 80)
    
    # Write log content
    log_content = "\n".join(log_lines)
    
    ingestion_log_path.write_text(log_content, encoding='utf-8')
    logger.info(f"Draw structural ingestion log written to: {ingestion_log_path}")
    
    # Also write to cleaned logs directory
    cleaned_log_path.write_text(log_content, encoding='utf-8')
    logger.info(f"Draw structural ingestion log written to: {cleaned_log_path}")
    
    return ingestion_log_path, cleaned_log_path


def write_historical_odds_log(
    download_session_folder: str,
    summary: Dict,
    ingestion_log_dir: Optional[Path] = None,
    cleaned_log_dir: Optional[Path] = None
) -> tuple[Optional[Path], Optional[Path]]:
    """
    Write comprehensive download log for historical match odds data.
    Saves logs to both ingestion and cleaned data 01_logs folders.
    
    Args:
        download_session_folder: The session folder name
        summary: Dictionary containing download summary information
        ingestion_log_dir: Optional path to ingestion logs directory
        cleaned_log_dir: Optional path to cleaned data logs directory
    
    Returns:
        Tuple of (ingestion_log_path, cleaned_log_path)
    """
    # Resolve backend root if paths not provided
    if ingestion_log_dir is None:
        backend_root = Path(__file__).parent.parent.parent.parent
        ingestion_log_dir = backend_root / "data" / "1_data_ingestion" / "Historical Match_Odds_Data" / "01_logs"
    
    if cleaned_log_dir is None:
        backend_root = Path(__file__).parent.parent.parent.parent
        cleaned_log_dir = backend_root / "data" / "2_Cleaned_data" / "Historical Match_Odds_Data" / "01_logs"
    
    # Create log directories
    ingestion_log_dir.mkdir(parents=True, exist_ok=True)
    cleaned_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"Historical_Odds_{download_session_folder}_{timestamp}_LOG.txt"
    
    ingestion_log_path = ingestion_log_dir / log_filename
    cleaned_log_path = cleaned_log_dir / log_filename
    
    # Build comprehensive log content
    log_lines = []
    log_lines.append("=" * 80)
    log_lines.append("HISTORICAL MATCH ODDS DATA DOWNLOAD LOG")
    log_lines.append("=" * 80)
    log_lines.append(f"Session Folder: {download_session_folder}")
    log_lines.append(f"Download Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append("")
    
    # Summary section
    log_lines.append("SUMMARY")
    log_lines.append("-" * 80)
    log_lines.append(f"Total Leagues Attempted: {summary.get('total_leagues', 0)}")
    log_lines.append(f"Successful Downloads: {summary.get('successful', 0)}")
    log_lines.append(f"Failed Downloads: {summary.get('failed', 0)}")
    log_lines.append(f"No Data Available (404s): {summary.get('no_data', 0)}")
    log_lines.append(f"Total Records Processed: {summary.get('total_processed', 0):,}")
    log_lines.append(f"Total Records Inserted: {summary.get('total_inserted', 0):,}")
    log_lines.append(f"Total Records Updated: {summary.get('total_updated', 0):,}")
    log_lines.append(f"Total Records Skipped: {summary.get('total_skipped', 0):,}")
    log_lines.append(f"Total Errors: {summary.get('total_errors', 0)}")
    log_lines.append("")
    
    # Successful downloads
    successful = summary.get('successful_downloads', [])
    if successful:
        log_lines.append("SUCCESSFUL DOWNLOADS")
        log_lines.append("-" * 80)
        for item in successful[:50]:  # Limit to first 50
            league_code = item.get('league_code', 'Unknown')
            season = item.get('season', 'Unknown')
            stats = item.get('stats', {})
            log_lines.append(f"✓ {league_code} - Season: {season}")
            log_lines.append(f"  Records: {stats.get('processed', 0):,} processed, "
                           f"{stats.get('inserted', 0):,} inserted, "
                           f"{stats.get('updated', 0):,} updated")
            if stats.get('errors', 0) > 0:
                log_lines.append(f"  ⚠ Warnings: {stats.get('errors', 0)} errors")
            log_lines.append("")
        if len(successful) > 50:
            log_lines.append(f"... and {len(successful) - 50} more successful downloads")
            log_lines.append("")
    
    # Failed downloads
    failed = summary.get('failed_downloads', [])
    if failed:
        log_lines.append("FAILED DOWNLOADS")
        log_lines.append("-" * 80)
        for item in failed[:30]:  # Limit to first 30
            league_code = item.get('league_code', 'Unknown')
            season = item.get('season', 'Unknown')
            error = item.get('error', 'Unknown error')
            is_404 = item.get('is_404', False)
            status = "⚠ Data Not Available (404)" if is_404 else "✗ ERROR"
            log_lines.append(f"{status} {league_code} - Season: {season}")
            log_lines.append(f"  Error: {error[:200]}")  # Truncate long errors
            log_lines.append("")
        if len(failed) > 30:
            log_lines.append(f"... and {len(failed) - 30} more failed downloads")
            log_lines.append("")
    
    # CSV files saved
    if summary.get('csv_files_saved'):
        log_lines.append("CSV FILES SAVED")
        log_lines.append("-" * 80)
        csv_files = summary.get('csv_files_saved', [])
        for csv_file in csv_files[:30]:
            log_lines.append(f"  ✓ {csv_file}")
        if len(csv_files) > 30:
            log_lines.append(f"  ... and {len(csv_files) - 30} more files")
        log_lines.append("")
    
    log_lines.append("=" * 80)
    log_lines.append("END OF LOG")
    log_lines.append("=" * 80)
    
    # Write log content
    log_content = "\n".join(log_lines)
    
    ingestion_log_path.write_text(log_content, encoding='utf-8')
    logger.info(f"Historical odds download log written to: {ingestion_log_path}")
    
    # Also write to cleaned logs directory
    cleaned_log_path.write_text(log_content, encoding='utf-8')
    logger.info(f"Historical odds download log written to: {cleaned_log_path}")
    
    return ingestion_log_path, cleaned_log_path

