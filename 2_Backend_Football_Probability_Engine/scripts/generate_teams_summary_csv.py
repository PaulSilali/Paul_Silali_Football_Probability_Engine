"""
Generate CSV Summary of Teams Created

This script queries the database and generates a CSV file with:
- League code and name
- Teams per league
- Team names and canonical names
- Creation statistics

Usage:
    python scripts/generate_teams_summary_csv.py
    python scripts/generate_teams_summary_csv.py --output teams_summary.csv
"""

import sys
from pathlib import Path
import csv
from datetime import datetime
from sqlalchemy import func

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import League, Team
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_teams_summary_csv(output_file: str = None):
    """
    Generate CSV summary of teams in database
    
    Args:
        output_file: Optional output file path (default: teams_summary_{timestamp}.csv)
    """
    db = SessionLocal()
    
    try:
        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"teams_summary_{timestamp}.csv"
        
        output_path = Path(output_file)
        
        # Get all leagues with team counts
        leagues_with_teams = db.query(
            League.code,
            League.name,
            League.country,
            func.count(Team.id).label('team_count')
        ).join(Team).group_by(
            League.id, League.code, League.name, League.country
        ).order_by(League.code).all()
        
        # Get all teams with league info
        all_teams = db.query(
            Team.id,
            Team.name,
            Team.canonical_name,
            League.code.label('league_code'),
            League.name.label('league_name'),
            League.country,
            Team.created_at
        ).join(League).order_by(
            League.code, Team.canonical_name
        ).all()
        
        # Calculate statistics
        total_teams = len(all_teams)
        total_leagues = len(leagues_with_teams)
        
        logger.info(f"Generating CSV summary...")
        logger.info(f"  Total leagues: {total_leagues}")
        logger.info(f"  Total teams: {total_teams}")
        logger.info(f"  Output file: {output_path}")
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'League Code',
                'League Name',
                'Country',
                'Team ID',
                'Team Name (Raw)',
                'Canonical Name',
                'Created At'
            ])
            
            # Write team data
            for team in all_teams:
                writer.writerow([
                    team.league_code,
                    team.league_name,
                    team.country or '',
                    team.id,
                    team.name,
                    team.canonical_name,
                    team.created_at.isoformat() if team.created_at else ''
                ])
            
            # Write summary section
            writer.writerow([])  # Empty row
            writer.writerow(['=== SUMMARY ==='])
            writer.writerow(['Total Leagues', total_leagues])
            writer.writerow(['Total Teams', total_teams])
            writer.writerow(['Generated At', datetime.now().isoformat()])
            writer.writerow([])  # Empty row
            
            # Write per-league summary
            writer.writerow(['=== TEAMS PER LEAGUE ==='])
            writer.writerow(['League Code', 'League Name', 'Country', 'Team Count'])
            
            for league_code, league_name, country, team_count in leagues_with_teams:
                writer.writerow([
                    league_code,
                    league_name,
                    country or '',
                    team_count
                ])
        
        logger.info(f"✅ CSV file generated successfully: {output_path}")
        logger.info(f"   File size: {output_path.stat().st_size:,} bytes")
        
        return str(output_path)
    
    except Exception as e:
        logger.error(f"Error generating CSV: {e}", exc_info=True)
        return None
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate CSV summary of teams")
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV file path (default: teams_summary_{timestamp}.csv)"
    )
    
    args = parser.parse_args()
    
    result = generate_teams_summary_csv(args.output)
    
    if result:
        logger.info(f"\n✅ Summary CSV generated: {result}")
    else:
        logger.error("\n❌ Failed to generate CSV summary")

