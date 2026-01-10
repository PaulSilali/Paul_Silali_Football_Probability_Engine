"""
Convert Jackpot Fixtures with Results to Match Records for Training

This allows using historical jackpot predictions with actual results
as training data for the model.
"""
from sqlalchemy.orm import Session
from app.db.models import (
    JackpotFixture, Jackpot, Match, League, Team, MatchResult
)
from datetime import datetime, date
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def convert_jackpot_to_matches(
    db: Session,
    jackpot_id: str,
    season: Optional[str] = None,
    match_date: Optional[date] = None,
    skip_existing: bool = True
) -> Dict:
    """
    Convert jackpot fixtures with results to Match records for training
    
    Args:
        db: Database session
        jackpot_id: Jackpot ID string
        season: Season identifier (e.g., '2425'). If None, inferred from match_date
        match_date: Match date. If None, uses jackpot kickoff_date or created_at
        skip_existing: Skip fixtures that already have corresponding matches
    
    Returns:
        Dict with conversion statistics
    """
    # Get jackpot
    jackpot = db.query(Jackpot).filter(Jackpot.jackpot_id == jackpot_id).first()
    if not jackpot:
        return {
            "success": False,
            "error": f"Jackpot {jackpot_id} not found"
        }
    
    # Get fixtures with results
    fixtures = db.query(JackpotFixture).filter(
        JackpotFixture.jackpot_id == jackpot.id,
        JackpotFixture.actual_result.isnot(None)  # Only fixtures with results
    ).all()
    
    if not fixtures:
        return {
            "success": False,
            "error": f"No fixtures with results found for jackpot {jackpot_id}"
        }
    
    # Determine match date
    if not match_date:
        match_date = jackpot.kickoff_date or jackpot.created_at.date()
    
    # Determine season if not provided
    if not season:
        # Infer season from match_date (e.g., 2024-01-10 -> 2425)
        year = match_date.year
        month = match_date.month
        if month >= 8:  # August onwards = start of new season
            season = f"{str(year)[2:]}{str(year + 1)[2:]}"
        else:  # January-July = end of previous season
            season = f"{str(year - 1)[2:]}{str(year)[2:]}"
    
    results = {
        "success": True,
        "jackpot_id": jackpot_id,
        "total_fixtures": len(fixtures),
        "converted": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": []
    }
    
    for fixture in fixtures:
        try:
            # Check if match already exists
            if skip_existing:
                existing_match = db.query(Match).filter(
                    Match.league_id == fixture.league_id,
                    Match.season == season,
                    Match.match_date == match_date,
                    Match.home_team_id == fixture.home_team_id,
                    Match.away_team_id == fixture.away_team_id
                ).first()
                
                if existing_match:
                    logger.debug(f"Match already exists for fixture {fixture.id}, skipping")
                    results["skipped"] += 1
                    continue
            
            # Validate required fields
            if not fixture.league_id:
                results["errors"] += 1
                results["error_details"].append(
                    f"Fixture {fixture.id}: Missing league_id"
                )
                continue
            
            if not fixture.home_team_id or not fixture.away_team_id:
                results["errors"] += 1
                results["error_details"].append(
                    f"Fixture {fixture.id}: Missing team_ids"
                )
                continue
            
            if not fixture.actual_result:
                results["errors"] += 1
                results["error_details"].append(
                    f"Fixture {fixture.id}: Missing actual_result"
                )
                continue
            
            # Get goals from actual result
            home_goals = fixture.actual_home_goals
            away_goals = fixture.actual_away_goals
            
            # If goals not provided, infer from result
            if home_goals is None or away_goals is None:
                if fixture.actual_result == MatchResult.H:
                    home_goals = 1
                    away_goals = 0
                elif fixture.actual_result == MatchResult.A:
                    home_goals = 0
                    away_goals = 1
                else:  # Draw
                    home_goals = 0
                    away_goals = 0
                logger.warning(
                    f"Fixture {fixture.id}: Goals not provided, inferred from result: "
                    f"{home_goals}-{away_goals}"
                )
            
            # Create match record
            match = Match(
                league_id=fixture.league_id,
                season=season,
                match_date=match_date,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                home_goals=home_goals,
                away_goals=away_goals,
                result=fixture.actual_result,
                # Store reference to original jackpot fixture
                # (could add jackpot_fixture_id column if needed)
            )
            
            db.add(match)
            results["converted"] += 1
            
            logger.info(
                f"Converted fixture {fixture.id} ({fixture.home_team} vs {fixture.away_team}) "
                f"to match record"
            )
            
        except Exception as e:
            results["errors"] += 1
            error_msg = f"Fixture {fixture.id}: {str(e)}"
            results["error_details"].append(error_msg)
            logger.error(error_msg, exc_info=True)
    
    # Commit all matches
    try:
        db.commit()
        logger.info(
            f"Successfully converted {results['converted']} fixtures to matches "
            f"for jackpot {jackpot_id}"
        )
    except Exception as e:
        db.rollback()
        results["success"] = False
        results["error"] = f"Failed to commit matches: {str(e)}"
        logger.error(results["error"], exc_info=True)
    
    return results


def batch_convert_jackpots_to_matches(
    db: Session,
    jackpot_ids: Optional[List[str]] = None,
    use_all_jackpots: bool = False,
    skip_existing: bool = True
) -> Dict:
    """
    Convert multiple jackpots to match records
    
    Args:
        db: Database session
        jackpot_ids: List of jackpot IDs to convert (None = all)
        use_all_jackpots: Convert all jackpots with results
        skip_existing: Skip fixtures that already have matches
    
    Returns:
        Dict with batch conversion statistics
    """
    # Get jackpots to convert
    if use_all_jackpots:
        # Get all jackpots that have fixtures with results
        jackpots = db.query(Jackpot).join(JackpotFixture).filter(
            JackpotFixture.actual_result.isnot(None)
        ).distinct().all()
        jackpot_ids = [j.jackpot_id for j in jackpots]
    
    if not jackpot_ids:
        return {
            "success": False,
            "error": "No jackpots specified"
        }
    
    batch_results = {
        "success": True,
        "total_jackpots": len(jackpot_ids),
        "converted_jackpots": 0,
        "total_matches": 0,
        "skipped_matches": 0,
        "errors": 0,
        "jackpot_results": []
    }
    
    for jackpot_id in jackpot_ids:
        try:
            result = convert_jackpot_to_matches(
                db=db,
                jackpot_id=jackpot_id,
                skip_existing=skip_existing
            )
            
            batch_results["jackpot_results"].append({
                "jackpot_id": jackpot_id,
                **result
            })
            
            if result.get("success"):
                batch_results["converted_jackpots"] += 1
                batch_results["total_matches"] += result.get("converted", 0)
                batch_results["skipped_matches"] += result.get("skipped", 0)
            else:
                batch_results["errors"] += 1
                
        except Exception as e:
            batch_results["errors"] += 1
            batch_results["jackpot_results"].append({
                "jackpot_id": jackpot_id,
                "success": False,
                "error": str(e)
            })
            logger.error(f"Error converting jackpot {jackpot_id}: {e}", exc_info=True)
    
    return batch_results

