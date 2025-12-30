"""
Script to Extract Teams from CSV Files and Create Them in Database

This script:
1. Scans all CSV files in data/1_data_ingestion/batch_*/
2. Extracts unique team names per league
3. Creates teams in the database if they don't exist
4. Uses normalized team names for canonical_name

Usage:
    python scripts/create_teams_from_csv.py
    python scripts/create_teams_from_csv.py --league E0  # Only Premier League
    python scripts/create_teams_from_csv.py --dry-run    # Preview without creating
"""

import sys
import os
from pathlib import Path
import pandas as pd
from collections import defaultdict
from typing import Dict, Set, List
import argparse
import re

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import League, Team
from app.services.team_resolver import normalize_team_name, resolve_team_safe
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_teams_from_csv_files(
    data_dir: Path = Path("data/1_data_ingestion"),
    league_code_filter: str = None
) -> Dict[str, Set[str]]:
    """
    Extract unique team names from all CSV files
    
    Args:
        data_dir: Directory containing batch folders
        league_code_filter: Optional league code to filter (e.g., "E0")
    
    Returns:
        Dictionary mapping league_code -> set of team names
    """
    teams_by_league: Dict[str, Set[str]] = defaultdict(set)
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return teams_by_league
    
    # Find all CSV files in batch folders
    csv_files = []
    for batch_folder in data_dir.iterdir():
        if batch_folder.is_dir() and batch_folder.name.startswith("batch_"):
            csv_files.extend(batch_folder.glob("*.csv"))
    
    logger.info(f"Found {len(csv_files)} CSV files")
    
    for csv_file in csv_files:
        try:
            # Extract league code from filename (e.g., E0_1920.csv -> E0)
            filename_parts = csv_file.stem.split('_')
            if len(filename_parts) < 2:
                continue
            
            league_code = filename_parts[0]
            
            # Filter by league code if specified
            if league_code_filter and league_code != league_code_filter:
                continue
            
            # Read CSV with error handling for malformed files
            try:
                # Try pandas read_csv with error handling
                try:
                    df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='utf-8')
                except TypeError:
                    # pandas < 2.0 doesn't have on_bad_lines
                    df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='utf-8')
            except Exception as e1:
                # Try with different encoding
                try:
                    df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='latin-1')
                except TypeError:
                    df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='latin-1')
                except Exception as e2:
                    logger.warning(f"Skipping {csv_file.name}: CSV parsing failed - {e2}")
                    continue
            
            # Extract team names
            home_teams = []
            away_teams = []
            
            if 'HomeTeam' in df.columns:
                home_teams = df['HomeTeam'].dropna().unique().tolist()
                teams_by_league[league_code].update(home_teams)
            
            if 'AwayTeam' in df.columns:
                away_teams = df['AwayTeam'].dropna().unique().tolist()
                teams_by_league[league_code].update(away_teams)
            
            logger.debug(f"Extracted {len(set(home_teams + away_teams))} unique teams from {csv_file.name}")
            
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
            continue
    
    return teams_by_league


def create_teams_in_database(
    db: SessionLocal,
    teams_by_league: Dict[str, Set[str]],
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Create teams in database
    
    Args:
        db: Database session
        teams_by_league: Dictionary mapping league_code -> set of team names
        dry_run: If True, only preview without creating
    
    Returns:
        Dictionary with creation statistics
    """
    stats = {
        "leagues_processed": 0,
        "teams_created": 0,
        "teams_existing": 0,
        "teams_skipped": 0,
        "errors": 0
    }
    
    for league_code, team_names in teams_by_league.items():
        # Get league from database
        league = db.query(League).filter(League.code == league_code).first()
        
        if not league:
            logger.warning(f"League {league_code} not found in database, skipping")
            stats["teams_skipped"] += len(team_names)
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing league: {league.name} ({league_code})")
        logger.info(f"Found {len(team_names)} unique team names")
        logger.info(f"{'='*60}")
        
        stats["leagues_processed"] += 1
        
        # Track canonical names to prevent duplicates within same league
        seen_canonical_names = set()
        
        for team_name in sorted(team_names):
            team_name = str(team_name).strip()
            
            if not team_name or len(team_name) < 2:
                continue
            
            try:
                # Check if team already exists in database
                existing_team = resolve_team_safe(db, team_name, league.id)
                
                if existing_team:
                    logger.debug(f"  ✓ Team exists: {team_name} -> {existing_team.canonical_name}")
                    stats["teams_existing"] += 1
                    seen_canonical_names.add(existing_team.canonical_name.lower())
                    continue
                
                # Create canonical name - preserve important words like "city", "united"
                # Only remove truly generic suffixes (FC, CF, etc.) but keep meaningful words
                canonical_name = team_name.lower().strip()
                
                # Remove only generic suffixes (FC, CF, etc.) but NOT meaningful words like "city", "united"
                generic_suffixes = [" fc", " cf", " bc", " ac", " fc.", " cf.", " bc.", " ac.", " football club"]
                for suffix in generic_suffixes:
                    if canonical_name.endswith(suffix):
                        canonical_name = canonical_name[:-len(suffix)].strip()
                
                # Remove special characters except spaces, hyphens, and apostrophes
                canonical_name = re.sub(r"[^\w\s'-]", '', canonical_name)
                
                # Normalize whitespace
                canonical_name = re.sub(r'\s+', ' ', canonical_name).strip()
                
                # Handle apostrophes (e.g., "Nott'm Forest" -> "nottm forest")
                canonical_name = canonical_name.replace("'", "")
                
                # Ensure canonical name is meaningful (at least 3 chars)
                if len(canonical_name) < 3:
                    canonical_name = team_name.lower().strip()
                    canonical_name = re.sub(r'[^\w\s-]', '', canonical_name)
                    canonical_name = re.sub(r'\s+', ' ', canonical_name).strip()
                
                # Check if canonical name already seen in this batch
                canonical_lower = canonical_name.lower()
                if canonical_lower in seen_canonical_names:
                    logger.warning(f"  ⚠ Skipping duplicate canonical name: {team_name} -> {canonical_name}")
                    stats["teams_skipped"] += 1
                    continue
                
                # Check if canonical name exists in database
                existing_by_canonical = db.query(Team).filter(
                    Team.league_id == league.id,
                    Team.canonical_name.ilike(canonical_name)
                ).first()
                
                if existing_by_canonical:
                    logger.debug(f"  ✓ Team exists (by canonical): {team_name} -> {existing_by_canonical.canonical_name}")
                    stats["teams_existing"] += 1
                    seen_canonical_names.add(canonical_lower)
                    continue
                
                # Mark as seen
                seen_canonical_names.add(canonical_lower)
                
                if dry_run:
                    logger.info(f"  [DRY RUN] Would create: {team_name} -> {canonical_name}")
                    stats["teams_created"] += 1
                else:
                    team = Team(
                        league_id=league.id,
                        name=team_name,
                        canonical_name=canonical_name
                    )
                    db.add(team)
                    logger.info(f"  ✓ Created: {team_name} -> {canonical_name}")
                    stats["teams_created"] += 1
                    
                    # Commit immediately to avoid batch conflicts
                    try:
                        db.commit()
                    except Exception as commit_error:
                        db.rollback()
                        logger.error(f"  ✗ Error committing team '{team_name}': {commit_error}")
                        stats["errors"] += 1
                        # Remove from seen set so it can be retried
                        seen_canonical_names.discard(canonical_lower)
                        continue
            
            except Exception as e:
                logger.error(f"  ✗ Error creating team '{team_name}': {e}")
                stats["errors"] += 1
                db.rollback()
                continue
        
        logger.info(f"✓ Completed league {league.name}: Created {stats['teams_created']} teams")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Extract teams from CSV files and create them in database"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="Filter by league code (e.g., E0 for Premier League)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without creating teams"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/1_data_ingestion",
        help="Path to data ingestion directory"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Team Extraction and Creation Script")
    logger.info("="*60)
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No teams will be created")
    
    if args.league:
        logger.info(f"📋 Filtering by league: {args.league}")
    
    # Extract teams from CSV files
    logger.info("\n📂 Extracting teams from CSV files...")
    data_dir = Path(args.data_dir)
    teams_by_league = extract_teams_from_csv_files(data_dir, args.league)
    
    if not teams_by_league:
        logger.error("No teams found in CSV files!")
        return
    
    # Display summary
    logger.info("\n📊 Summary:")
    total_teams = 0
    for league_code, team_names in teams_by_league.items():
        logger.info(f"  {league_code}: {len(team_names)} teams")
        total_teams += len(team_names)
    logger.info(f"  Total: {total_teams} unique teams across {len(teams_by_league)} leagues")
    
    # Create teams in database
    logger.info("\n💾 Creating teams in database...")
    db = SessionLocal()
    
    try:
        stats = create_teams_in_database(db, teams_by_league, dry_run=args.dry_run)
        
        # Display final statistics
        logger.info("\n" + "="*60)
        logger.info("📈 Final Statistics:")
        logger.info("="*60)
        logger.info(f"  Leagues processed: {stats['leagues_processed']}")
        logger.info(f"  Teams created: {stats['teams_created']}")
        logger.info(f"  Teams already existing: {stats['teams_existing']}")
        logger.info(f"  Teams skipped: {stats['teams_skipped']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info("="*60)
        
        if args.dry_run:
            logger.info("\n💡 Run without --dry-run to actually create teams")
        else:
            logger.info("\n✅ Teams created successfully!")
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

