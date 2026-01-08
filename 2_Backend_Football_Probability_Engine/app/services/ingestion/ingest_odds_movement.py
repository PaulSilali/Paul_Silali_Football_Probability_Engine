"""
Ingest odds movement data from Football-Data.org or similar sources
"""
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import OddsMovement, JackpotFixture, League, Match, Team
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging
from app.services.ingestion.draw_structural_validation import (
    DrawStructuralValidator,
    validate_before_insert
)

logger = logging.getLogger(__name__)


def ingest_odds_movement_from_football_data_org(
    db: Session,
    fixture_id: int,
    api_key: Optional[str] = None
) -> Dict:
    """
    Ingest odds movement from Football-Data.org API.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        api_key: API key (optional)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        if not api_key:
            from app.config import settings
            api_key = getattr(settings, 'FOOTBALL_DATA_ORG_KEY', None)
        
        if not api_key:
            return {"success": False, "error": "API key not configured"}
        
        # Get fixture to find external fixture ID
        fixture = db.query(JackpotFixture).filter(
            JackpotFixture.id == fixture_id
        ).first()
        
        if not fixture:
            return {"success": False, "error": "Fixture not found"}
        
        # Football-Data.org API endpoint
        # Note: This requires mapping our fixture_id to external fixture ID
        # For now, use odds from fixture if available
        
        # If fixture has odds, we can track movement over time
        # For initial implementation, store current odds as "close" odds
        if fixture.odds_draw:
            draw_close = float(fixture.odds_draw)
            
            # Try to get opening odds from API or use current as placeholder
            # In production, you'd track opening odds separately
            draw_open = draw_close  # Placeholder - would come from API or historical tracking
            
            draw_delta = draw_close - draw_open
            
            # Validate odds movement
            context = f" (fixture_id={fixture_id})"
            is_valid, error = DrawStructuralValidator.validate_odds_movement(
                draw_open, draw_close, draw_delta, context
            )
            if not is_valid:
                logger.error(f"Invalid odds movement: {error}")
                return {"success": False, "error": error}
            
            # Insert or update
            existing = db.query(OddsMovement).filter(
                OddsMovement.fixture_id == fixture_id
            ).first()
            
            if existing:
                existing.draw_close = draw_close
                existing.draw_delta = draw_delta
            else:
                odds_movement = OddsMovement(
                    fixture_id=fixture_id,
                    draw_open=draw_open,
                    draw_close=draw_close,
                    draw_delta=draw_delta
                )
                db.add(odds_movement)
            
            db.commit()
            
            logger.info(f"Ingested odds movement for fixture {fixture_id}: delta={draw_delta:.3f}")
            
            return {
                "success": True,
                "draw_open": draw_open,
                "draw_close": draw_close,
                "draw_delta": draw_delta
            }
        else:
            return {"success": False, "error": "Fixture has no odds data"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting odds movement: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_odds_movement_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest odds movement from CSV file in our format.
    
    CSV Format: league_code,season,match_date,home_team,away_team,draw_open,draw_close,draw_delta
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['league_code', 'season', 'match_date', 'home_team', 'away_team', 'draw_open', 'draw_close', 'draw_delta']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {"success": False, "error": f"Missing required columns: {missing_cols}"}
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                league_code = str(row['league_code']).strip()
                season = str(row['season']).strip()
                match_date = pd.to_datetime(row['match_date']).date()
                home_team_name = str(row['home_team']).strip()
                away_team_name = str(row['away_team']).strip()
                draw_open = float(row['draw_open'])
                draw_close = float(row['draw_close'])
                draw_delta = float(row.get('draw_delta', draw_close - draw_open))
                
                # Find league
                league = db.query(League).filter(League.code == league_code).first()
                if not league:
                    logger.warning(f"League {league_code} not found, skipping")
                    errors += 1
                    continue
                
                # Find teams
                from app.services.team_resolver import resolve_team_safe
                home_team = resolve_team_safe(db, home_team_name, league.id)
                away_team = resolve_team_safe(db, away_team_name, league.id)
                if not home_team or not away_team:
                    logger.warning(f"Teams {home_team_name} or {away_team_name} not found, skipping")
                    errors += 1
                    continue
                
                # Find match
                match = db.query(Match).filter(
                    Match.league_id == league.id,
                    Match.season == season,
                    Match.match_date == match_date,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id
                ).first()
                
                if not match:
                    logger.warning(f"Match not found: {league_code} {season} {match_date} {home_team_name} vs {away_team_name}, skipping")
                    errors += 1
                    continue
                
                # Insert or update in odds_movement_historical
                from sqlalchemy import text
                existing = db.execute(
                    text("""
                        SELECT id FROM odds_movement_historical 
                        WHERE match_id = :match_id
                    """),
                    {"match_id": match.id}
                ).fetchone()
                
                if existing:
                    db.execute(
                        text("""
                            UPDATE odds_movement_historical 
                            SET draw_open = :draw_open,
                                draw_close = :draw_close,
                                draw_delta = :draw_delta
                            WHERE match_id = :match_id
                        """),
                        {
                            "match_id": match.id,
                            "draw_open": draw_open,
                            "draw_close": draw_close,
                            "draw_delta": draw_delta
                        }
                    )
                    updated += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO odds_movement_historical 
                            (match_id, draw_open, draw_close, draw_delta)
                            VALUES (:match_id, :draw_open, :draw_close, :draw_delta)
                        """),
                        {
                            "match_id": match.id,
                            "draw_open": draw_open,
                            "draw_close": draw_close,
                            "draw_delta": draw_delta
                        }
                    )
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing odds movement row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested odds movement from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting odds movement from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def track_odds_movement(
    db: Session,
    fixture_id: int,
    draw_odds: float
) -> Dict:
    """
    Track odds movement by updating close odds.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        draw_odds: Current draw odds
    
    Returns:
        Dict with tracking statistics
    """
    try:
        existing = db.query(OddsMovement).filter(
            OddsMovement.fixture_id == fixture_id
        ).first()
        
        if existing:
            # Update close odds and recalculate delta
            old_close = existing.draw_close
            existing.draw_close = draw_odds
            if existing.draw_open:
                existing.draw_delta = draw_odds - existing.draw_open
        else:
            # Create new entry (using current odds as both open and close initially)
            odds_movement = OddsMovement(
                fixture_id=fixture_id,
                draw_open=draw_odds,
                draw_close=draw_odds,
                draw_delta=0.0
            )
            db.add(odds_movement)
        
        db.commit()
        
        return {
            "success": True,
            "draw_close": draw_odds,
            "draw_delta": existing.draw_delta if existing else 0.0
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error tracking odds movement: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _save_odds_movement_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    odds_records: List[Dict]
) -> Path:
    """
    Save CSV file with odds movement data for all matches in a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        odds_records: List of dictionaries with odds movement data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not odds_records:
            raise ValueError("No odds movement records to save")
        
        # Create DataFrame from all records
        df = pd.DataFrame(odds_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "home_team", "away_team",
                "draw_open", "draw_close", "draw_delta"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_odds_movement.csv
        filename = f"{league_code}_{season}_odds_movement.csv"
        
        # Save to both locations
        from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "Odds_Movement", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved batch odds movement CSV for {league_code} ({season}): {len(odds_records)} records")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving batch odds movement CSV: {e}", exc_info=True)
        raise


def batch_ingest_odds_movement_from_matches(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest odds movement for matches in specified leagues and seasons.
    
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
        
        logger.info(f"Batch processing odds movement for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Get matches with odds for this league/season
                    if season_filter:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id,
                                   odds_draw, prob_draw_market
                            FROM matches
                            WHERE league_id = :league_id 
                              AND season = :season
                              AND odds_draw IS NOT NULL
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id, "season": season_filter}
                    else:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id,
                                   odds_draw, prob_draw_market
                            FROM matches
                            WHERE league_id = :league_id
                              AND odds_draw IS NOT NULL
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id}
                    
                    matches = db.execute(matches_query, matches_params).fetchall()
                    
                    if not matches:
                        continue
                    
                    # Collect odds movement records for this league/season
                    odds_records = []
                    
                    for match in matches:
                        match_id = match.id
                        match_date = match.match_date
                        home_team_id = match.home_team_id
                        away_team_id = match.away_team_id
                        draw_close = float(match.odds_draw) if match.odds_draw else None
                        results["total"] += 1
                        
                        if not draw_close:
                            results["skipped"] += 1
                            continue
                        
                        try:
                            # Get team names
                            home_team = db.query(Team).filter(Team.id == home_team_id).first()
                            away_team = db.query(Team).filter(Team.id == away_team_id).first()
                            
                            # For now, use current odds as both open and close
                            # In production, you'd track opening odds separately
                            draw_open = draw_close  # Placeholder
                            draw_delta = 0.0  # Would be close - open
                            
                            # Save to database - create historical odds movement table if needed
                            db_saved = False
                            try:
                                # Ensure clean transaction state
                                try:
                                    db.rollback()
                                except:
                                    pass
                                
                                # Try to insert into odds_movement_historical if it exists
                                insert_query = text("""
                                    INSERT INTO odds_movement_historical 
                                    (match_id, draw_open, draw_close, draw_delta, recorded_at)
                                    VALUES (:match_id, :draw_open, :draw_close, :draw_delta, NOW())
                                    ON CONFLICT (match_id) DO UPDATE SET
                                        draw_open = EXCLUDED.draw_open,
                                        draw_close = EXCLUDED.draw_close,
                                        draw_delta = EXCLUDED.draw_delta,
                                        recorded_at = NOW()
                                """)
                                
                                db.execute(insert_query, {
                                    "match_id": match_id,
                                    "draw_open": draw_open,
                                    "draw_close": draw_close,
                                    "draw_delta": draw_delta
                                })
                                
                                db.commit()
                                db_saved = True
                                
                            except Exception as db_error:
                                # Always rollback on error
                                try:
                                    db.rollback()
                                except:
                                    pass
                                
                                # If table doesn't exist, create it
                                if "does not exist" in str(db_error) or "relation" in str(db_error).lower() or "InFailedSqlTransaction" in str(db_error):
                                    try:
                                        # Rollback first to clear any aborted transaction
                                        try:
                                            db.rollback()
                                        except:
                                            pass
                                        
                                        create_table_query = text("""
                                            CREATE TABLE IF NOT EXISTS odds_movement_historical (
                                                id SERIAL PRIMARY KEY,
                                                match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                                                draw_open DOUBLE PRECISION CHECK (draw_open > 1.0),
                                                draw_close DOUBLE PRECISION CHECK (draw_close > 1.0),
                                                draw_delta DOUBLE PRECISION,
                                                recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                                                CONSTRAINT uix_odds_movement_historical_match UNIQUE (match_id)
                                            );
                                            CREATE INDEX IF NOT EXISTS idx_odds_movement_historical_match ON odds_movement_historical(match_id);
                                            CREATE INDEX IF NOT EXISTS idx_odds_movement_historical_delta ON odds_movement_historical(draw_delta);
                                        """)
                                        db.execute(create_table_query)
                                        db.commit()
                                        
                                        # Now try insert again
                                        insert_query = text("""
                                            INSERT INTO odds_movement_historical 
                                            (match_id, draw_open, draw_close, draw_delta, recorded_at)
                                            VALUES (:match_id, :draw_open, :draw_close, :draw_delta, NOW())
                                            ON CONFLICT (match_id) DO UPDATE SET
                                                draw_open = EXCLUDED.draw_open,
                                                draw_close = EXCLUDED.draw_close,
                                                draw_delta = EXCLUDED.draw_delta,
                                                recorded_at = NOW()
                                        """)
                                        
                                        db.execute(insert_query, {
                                            "match_id": match_id,
                                            "draw_open": draw_open,
                                            "draw_close": draw_close,
                                            "draw_delta": draw_delta
                                        })
                                        
                                        db.commit()
                                        db_saved = True
                                        logger.info(f"Created table and saved odds movement to database for match {match_id}")
                                        
                                    except Exception as create_error:
                                        try:
                                            db.rollback()
                                        except:
                                            pass
                                        logger.error(f"Failed to create/save odds movement to database for match {match_id}: {create_error}", exc_info=True)
                                else:
                                    logger.error(f"Failed to save odds movement to database for match {match_id}: {db_error}", exc_info=True)
                            
                            # Always add to CSV records (even if DB save failed)
                            odds_records.append({
                                "league_code": league.code,
                                "season": season_filter or "all",
                                "match_date": match_date.isoformat() if hasattr(match_date, "isoformat") else str(match_date),
                                "home_team": home_team.name if home_team else f"Team {home_team_id}",
                                "away_team": away_team.name if away_team else f"Team {away_team_id}",
                                "draw_open": draw_open,
                                "draw_close": draw_close,
                                "draw_delta": draw_delta
                            })
                            
                            # Only count as successful if database save succeeded
                            if db_saved:
                                results["successful"] += 1
                                logger.debug(f"Successfully saved odds movement for match {match_id} to database")
                            else:
                                results["failed"] += 1
                                logger.warning(f"Odds movement not saved to database for match {match_id}, but CSV will be saved")
                            
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to process odds for match {match_id}: {e}")
                    
                    # Save CSV for this league/season combination
                    if save_csv and odds_records:
                        try:
                            csv_path = _save_odds_movement_csv_batch(db, league.code, season_filter or "all", odds_records)
                            logger.info(f"Saved Odds Movement CSV for {league.code} ({season_filter or 'all'}): {len(odds_records)} records")
                        except Exception as e:
                            logger.warning(f"Failed to save Odds Movement CSV for {league.code} ({season_filter or 'all'}): {e}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        logger.info(f"Batch odds movement ingestion complete: {results['successful']} successful, {results['failed']} failed out of {results['total']} processed")
        
        return {
            "success": True,
            **results
        }
    
    except Exception as e:
        logger.error(f"Error in batch odds movement ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

