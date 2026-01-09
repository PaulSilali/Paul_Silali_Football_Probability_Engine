"""
Calculate and ingest team rest days from fixture schedule
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db.models import TeamRestDays, JackpotFixture, Match, League, Team
from app.services.ingestion.draw_structural_validation import DrawStructuralValidator
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_rest_days_for_fixture(
    db: Session,
    fixture_id: int,
    team_id: int
) -> int:
    """
    Calculate rest days for a team before a fixture.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        team_id: Team ID
    
    Returns:
        Number of rest days
    """
    try:
        # Get fixture date
        fixture = db.query(JackpotFixture).filter(
            JackpotFixture.id == fixture_id
        ).first()
        
        if not fixture:
            return 7  # Default if fixture not found
        
        # Get fixture date (if available in jackpot_fixtures)
        # Otherwise, use kickoff_date from jackpot
        fixture_date = None
        if hasattr(fixture, 'match_date') and fixture.match_date:
            fixture_date = fixture.match_date
        elif hasattr(fixture, 'jackpot') and fixture.jackpot and fixture.jackpot.kickoff_date:
            fixture_date = fixture.jackpot.kickoff_date
        
        if not fixture_date:
            return 7  # Default
        
        # Get previous match for this team
        previous_match = db.execute(
            text("""
                SELECT match_date
                FROM matches
                WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                  AND match_date < :fixture_date
                ORDER BY match_date DESC
                LIMIT 1
            """),
            {"team_id": team_id, "fixture_date": fixture_date}
        ).fetchone()
        
        if not previous_match:
            return 7  # Default if no previous match
        
        # Calculate rest days
        rest_days = (fixture_date - previous_match.match_date).days
        
        return max(0, rest_days)  # Ensure non-negative
    
    except Exception as e:
        logger.warning(f"Error calculating rest days: {e}")
        return 7  # Default


def ingest_rest_days_for_fixture(
    db: Session,
    fixture_id: int,
    home_team_id: Optional[int] = None,
    away_team_id: Optional[int] = None
) -> Dict:
    """
    Ingest rest days for both teams in a fixture.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        home_team_id: Home team ID (optional, will be fetched if not provided)
        away_team_id: Away team ID (optional, will be fetched if not provided)
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        # Get fixture if team IDs not provided
        if not home_team_id or not away_team_id:
            fixture = db.query(JackpotFixture).filter(
                JackpotFixture.id == fixture_id
            ).first()
            
            if fixture:
                home_team_id = fixture.home_team_id or home_team_id
                away_team_id = fixture.away_team_id or away_team_id
                logger.debug(f"Retrieved team IDs from fixture {fixture_id}: home={home_team_id}, away={away_team_id}")
        
        if not home_team_id or not away_team_id:
            logger.warning(f"Team IDs not available for fixture {fixture_id}: home={home_team_id}, away={away_team_id}")
            return {"success": False, "error": f"Team IDs not available: home={home_team_id}, away={away_team_id}"}
        
        # Get fixture date for midweek check
        fixture = db.query(JackpotFixture).filter(
            JackpotFixture.id == fixture_id
        ).first()
        
        fixture_date = None
        if fixture and hasattr(fixture, 'jackpot') and fixture.jackpot:
            fixture_date = fixture.jackpot.kickoff_date
        
        if not fixture_date:
            # Try to get from match_date if available
            fixture_date = getattr(fixture, 'match_date', None) if fixture else None
        
        if not fixture_date:
            fixture_date = date.today()  # Fallback
        
        # Check if midweek (Tue-Thu)
        is_midweek = fixture_date.weekday() in [1, 2, 3]  # Tue, Wed, Thu
        
        # Calculate rest days for both teams
        logger.debug(f"Calculating rest days for fixture {fixture_id}: home_team_id={home_team_id}, away_team_id={away_team_id}")
        home_rest = calculate_rest_days_for_fixture(db, fixture_id, home_team_id)
        away_rest = calculate_rest_days_for_fixture(db, fixture_id, away_team_id)
        logger.debug(f"Calculated rest days: home={home_rest}, away={away_rest}")
        
        # Validate rest days
        context_home = f" (home_team_id={home_team_id}, fixture_id={fixture_id})"
        is_valid, error = DrawStructuralValidator.validate_rest_days(home_rest, context_home)
        if not is_valid:
            logger.warning(f"Invalid home rest days: {error}, using default")
            home_rest = 7  # Default
        
        context_away = f" (away_team_id={away_team_id}, fixture_id={fixture_id})"
        is_valid, error = DrawStructuralValidator.validate_rest_days(away_rest, context_away)
        if not is_valid:
            logger.warning(f"Invalid away rest days: {error}, using default")
            away_rest = 7  # Default
        
        # Insert or update for home team
        existing_home = db.query(TeamRestDays).filter(
            TeamRestDays.team_id == home_team_id,
            TeamRestDays.fixture_id == fixture_id
        ).first()
        
        if existing_home:
            existing_home.rest_days = home_rest
            existing_home.is_midweek = is_midweek
            logger.debug(f"Updated existing rest days record for home team {home_team_id}")
        else:
            home_rest_days = TeamRestDays(
                team_id=home_team_id,
                fixture_id=fixture_id,
                rest_days=home_rest,
                is_midweek=is_midweek
            )
            db.add(home_rest_days)
            logger.debug(f"Added new rest days record for home team {home_team_id}")
        
        # Insert or update for away team
        existing_away = db.query(TeamRestDays).filter(
            TeamRestDays.team_id == away_team_id,
            TeamRestDays.fixture_id == fixture_id
        ).first()
        
        if existing_away:
            existing_away.rest_days = away_rest
            existing_away.is_midweek = is_midweek
            logger.debug(f"Updated existing rest days record for away team {away_team_id}")
        else:
            away_rest_days = TeamRestDays(
                team_id=away_team_id,
                fixture_id=fixture_id,
                rest_days=away_rest,
                is_midweek=is_midweek
            )
            db.add(away_rest_days)
            logger.debug(f"Added new rest days record for away team {away_team_id}")
        
        try:
            db.commit()
            logger.info(f"✓ Successfully ingested rest days for fixture {fixture_id}: home={home_rest}, away={away_rest}, is_midweek={is_midweek}")
            
            return {
                "success": True,
                "home_rest_days": home_rest,
                "away_rest_days": away_rest,
                "is_midweek": is_midweek
            }
        except IntegrityError as e:
            db.rollback()
            # Check if it's a duplicate key error (record already exists)
            if 'uix_team_rest_fixture' in str(e.orig):
                # Record already exists, try to update instead
                logger.debug(f"Rest days record already exists for fixture {fixture_id}, updating instead")
                try:
                    # Refresh and update existing records
                    db.expire_all()
                    existing_home = db.query(TeamRestDays).filter(
                        TeamRestDays.team_id == home_team_id,
                        TeamRestDays.fixture_id == fixture_id
                    ).first()
                    if existing_home:
                        existing_home.rest_days = home_rest
                        existing_home.is_midweek = is_midweek
                    
                    existing_away = db.query(TeamRestDays).filter(
                        TeamRestDays.team_id == away_team_id,
                        TeamRestDays.fixture_id == fixture_id
                    ).first()
                    if existing_away:
                        existing_away.rest_days = away_rest
                        existing_away.is_midweek = is_midweek
                    
                    db.commit()
                    logger.info(f"✓ Updated existing rest days for fixture {fixture_id}: home={home_rest}, away={away_rest}, is_midweek={is_midweek}")
                    return {
                        "success": True,
                        "home_rest_days": home_rest,
                        "away_rest_days": away_rest,
                        "is_midweek": is_midweek,
                        "updated": True
                    }
                except Exception as update_error:
                    db.rollback()
                    logger.warning(f"Failed to update existing rest days for fixture {fixture_id}: {update_error}")
                    # Return success anyway since the data already exists
                    return {
                        "success": True,
                        "home_rest_days": home_rest,
                        "away_rest_days": away_rest,
                        "is_midweek": is_midweek,
                        "skipped": True,
                        "message": "Record already exists"
                    }
            else:
                # Other integrity error
                raise
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting rest days: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_rest_days_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest rest days from CSV file in our format.
    
    CSV Format: league_code,season,match_date,home_team,away_team,home_rest_days,away_rest_days,is_midweek
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['league_code', 'season', 'match_date', 'home_team', 'away_team', 'home_rest_days', 'away_rest_days', 'is_midweek']
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
                home_rest_days = int(row['home_rest_days'])
                away_rest_days = int(row['away_rest_days'])
                is_midweek = bool(row['is_midweek']) if pd.notna(row['is_midweek']) else False
                
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
                
                # Insert or update in team_rest_days_historical (for home team)
                from sqlalchemy import text
                existing_home = db.execute(
                    text("""
                        SELECT id FROM team_rest_days_historical 
                        WHERE match_id = :match_id AND team_id = :team_id
                    """),
                    {"match_id": match.id, "team_id": home_team.id}
                ).fetchone()
                
                if existing_home:
                    db.execute(
                        text("""
                            UPDATE team_rest_days_historical 
                            SET rest_days = :rest_days, is_midweek = :is_midweek
                            WHERE match_id = :match_id AND team_id = :team_id
                        """),
                        {
                            "match_id": match.id,
                            "team_id": home_team.id,
                            "rest_days": home_rest_days,
                            "is_midweek": is_midweek
                        }
                    )
                    updated += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO team_rest_days_historical 
                            (match_id, team_id, rest_days, is_midweek)
                            VALUES (:match_id, :team_id, :rest_days, :is_midweek)
                        """),
                        {
                            "match_id": match.id,
                            "team_id": home_team.id,
                            "rest_days": home_rest_days,
                            "is_midweek": is_midweek
                        }
                    )
                    inserted += 1
                
                # Insert or update (for away team)
                existing_away = db.execute(
                    text("""
                        SELECT id FROM team_rest_days_historical 
                        WHERE match_id = :match_id AND team_id = :team_id
                    """),
                    {"match_id": match.id, "team_id": away_team.id}
                ).fetchone()
                
                if existing_away:
                    db.execute(
                        text("""
                            UPDATE team_rest_days_historical 
                            SET rest_days = :rest_days, is_midweek = :is_midweek
                            WHERE match_id = :match_id AND team_id = :team_id
                        """),
                        {
                            "match_id": match.id,
                            "team_id": away_team.id,
                            "rest_days": away_rest_days,
                            "is_midweek": is_midweek
                        }
                    )
                    updated += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO team_rest_days_historical 
                            (match_id, team_id, rest_days, is_midweek)
                            VALUES (:match_id, :team_id, :rest_days, :is_midweek)
                        """),
                        {
                            "match_id": match.id,
                            "team_id": away_team.id,
                            "rest_days": away_rest_days,
                            "is_midweek": is_midweek
                        }
                    )
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing rest days row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested rest days from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting rest days from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_rest_days_batch(
    db: Session,
    fixture_ids: List[int]
) -> Dict:
    """
    Ingest rest days for multiple fixtures.
    
    Args:
        db: Database session
        fixture_ids: List of fixture IDs
    
    Returns:
        Dict with batch statistics
    """
    success_count = 0
    error_count = 0
    
    for fixture_id in fixture_ids:
        result = ingest_rest_days_for_fixture(db, fixture_id)
        
        if result.get("success"):
            success_count += 1
        else:
            error_count += 1
    
    return {
        "success": True,
        "total": len(fixture_ids),
        "success_count": success_count,
        "error_count": error_count
    }


def _save_rest_days_csv_batch(
    db: Session,
    league_code: str,
    season: str,
    rest_days_records: List[Dict]
) -> Path:
    """
    Save CSV file with rest days data for all matches in a league/season.
    
    Args:
        db: Database session
        league_code: League code
        season: Season identifier
        rest_days_records: List of dictionaries with rest days data
    
    Returns:
        Path to saved CSV file
    """
    try:
        if not rest_days_records:
            raise ValueError("No rest days records to save")
        
        # Create DataFrame from all records
        df = pd.DataFrame(rest_days_records)
        
        # Reorder columns for better readability
        cols = ["league_code", "season", "match_date", "home_team", "away_team",
                "home_rest_days", "away_rest_days", "is_midweek"]
        df = df[[c for c in cols if c in df.columns]]
        
        # Filename format: {league_code}_{season}_rest_days.csv
        filename = f"{league_code}_{season}_rest_days.csv"
        
        # Save to both locations
        from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "Rest_Days", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved batch rest days CSV for {league_code} ({season}): {len(rest_days_records)} records")
        return ingestion_path
    
    except Exception as e:
        logger.error(f"Error saving batch rest days CSV: {e}", exc_info=True)
        raise


def batch_ingest_rest_days_from_matches(
    db: Session,
    league_codes: List[str] = None,
    use_all_leagues: bool = False,
    season: Optional[str] = None,
    use_all_seasons: bool = False,
    max_years: int = 10,
    save_csv: bool = True
) -> Dict:
    """
    Batch ingest rest days for matches in specified leagues and seasons.
    
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
        
        logger.info(f"Batch processing rest days for {len(leagues)} leagues...")
        logger.info(f"Processing {len(seasons)} seasons: {seasons}...")
        
        # Process each league/season combination
        for league in leagues:
            for season_filter in seasons:
                try:
                    # Ensure clean transaction state
                    try:
                        db.rollback()
                    except:
                        pass
                    
                    # Get matches for this league/season
                    if season_filter:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id AND season = :season
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id, "season": season_filter}
                    else:
                        matches_query = text("""
                            SELECT id, match_date, home_team_id, away_team_id
                            FROM matches
                            WHERE league_id = :league_id
                            ORDER BY match_date ASC
                        """)
                        matches_params = {"league_id": league.id}
                    
                    matches = db.execute(matches_query, matches_params).fetchall()
                    
                    if not matches:
                        continue
                    
                    # Collect rest days records for this league/season
                    rest_days_records = []
                    
                    for match in matches:
                        match_id = match.id
                        match_date = match.match_date
                        home_team_id = match.home_team_id
                        away_team_id = match.away_team_id
                        results["total"] += 1
                        
                        try:
                            # Get team names
                            home_team = db.query(Team).filter(Team.id == home_team_id).first()
                            away_team = db.query(Team).filter(Team.id == away_team_id).first()
                            
                            # Calculate rest days
                            # Get previous match for home team
                            prev_home_match = db.execute(
                                text("""
                                    SELECT match_date
                                    FROM matches
                                    WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                                      AND match_date < :match_date
                                    ORDER BY match_date DESC
                                    LIMIT 1
                                """),
                                {"team_id": home_team_id, "match_date": match_date}
                            ).fetchone()
                            
                            # Access match_date from row (handle both Row and tuple)
                            prev_home_date = None
                            if prev_home_match:
                                if hasattr(prev_home_match, 'match_date'):
                                    prev_home_date = prev_home_match.match_date
                                elif hasattr(prev_home_match, '_mapping'):
                                    prev_home_date = prev_home_match._mapping.get('match_date')
                                elif len(prev_home_match) > 0:
                                    prev_home_date = prev_home_match[0]
                            
                            home_rest = (match_date - prev_home_date).days if prev_home_date else 7
                            
                            # Get previous match for away team
                            prev_away_match = db.execute(
                                text("""
                                    SELECT match_date
                                    FROM matches
                                    WHERE (home_team_id = :team_id OR away_team_id = :team_id)
                                      AND match_date < :match_date
                                    ORDER BY match_date DESC
                                    LIMIT 1
                                """),
                                {"team_id": away_team_id, "match_date": match_date}
                            ).fetchone()
                            
                            # Access match_date from row (handle both Row and tuple)
                            prev_away_date = None
                            if prev_away_match:
                                if hasattr(prev_away_match, 'match_date'):
                                    prev_away_date = prev_away_match.match_date
                                elif hasattr(prev_away_match, '_mapping'):
                                    prev_away_date = prev_away_match._mapping.get('match_date')
                                elif len(prev_away_match) > 0:
                                    prev_away_date = prev_away_match[0]
                            
                            away_rest = (match_date - prev_away_date).days if prev_away_date else 7
                            
                            # Check if midweek
                            is_midweek = match_date.weekday() in [1, 2, 3]  # Tue, Wed, Thu
                            
                            # Save to database - create historical rest days table if needed
                            db_saved = False
                            try:
                                # Ensure clean transaction state
                                try:
                                    db.rollback()
                                except:
                                    pass
                                
                                # Try to insert into team_rest_days_historical if it exists
                                insert_query = text("""
                                    INSERT INTO team_rest_days_historical 
                                    (match_id, team_id, rest_days, is_midweek, created_at)
                                    VALUES (:match_id, :team_id, :rest_days, :is_midweek, NOW())
                                    ON CONFLICT (match_id, team_id) DO UPDATE SET
                                        rest_days = EXCLUDED.rest_days,
                                        is_midweek = EXCLUDED.is_midweek,
                                        created_at = NOW()
                                """)
                                
                                # Save home team rest days
                                db.execute(insert_query, {
                                    "match_id": match_id,
                                    "team_id": home_team_id,
                                    "rest_days": max(0, home_rest),
                                    "is_midweek": is_midweek
                                })
                                
                                # Save away team rest days
                                db.execute(insert_query, {
                                    "match_id": match_id,
                                    "team_id": away_team_id,
                                    "rest_days": max(0, away_rest),
                                    "is_midweek": is_midweek
                                })
                                
                                db.commit()
                                db_saved = True
                                logger.debug(f"Successfully saved rest days to database for match {match_id}")
                                
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
                                            CREATE TABLE IF NOT EXISTS team_rest_days_historical (
                                                id SERIAL PRIMARY KEY,
                                                match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                                                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                                                rest_days INTEGER NOT NULL CHECK (rest_days >= 0),
                                                is_midweek BOOLEAN NOT NULL DEFAULT FALSE,
                                                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                                                CONSTRAINT uix_team_rest_historical_match_team UNIQUE (match_id, team_id)
                                            );
                                            CREATE INDEX IF NOT EXISTS idx_team_rest_historical_match ON team_rest_days_historical(match_id);
                                            CREATE INDEX IF NOT EXISTS idx_team_rest_historical_team ON team_rest_days_historical(team_id);
                                            CREATE INDEX IF NOT EXISTS idx_team_rest_historical_days ON team_rest_days_historical(rest_days);
                                        """)
                                        db.execute(create_table_query)
                                        db.commit()
                                        
                                        # Now try insert again
                                        insert_query = text("""
                                            INSERT INTO team_rest_days_historical 
                                            (match_id, team_id, rest_days, is_midweek, created_at)
                                            VALUES (:match_id, :team_id, :rest_days, :is_midweek, NOW())
                                            ON CONFLICT (match_id, team_id) DO UPDATE SET
                                                rest_days = EXCLUDED.rest_days,
                                                is_midweek = EXCLUDED.is_midweek,
                                                created_at = NOW()
                                        """)
                                        
                                        # Save home team rest days
                                        db.execute(insert_query, {
                                            "match_id": match_id,
                                            "team_id": home_team_id,
                                            "rest_days": max(0, home_rest),
                                            "is_midweek": is_midweek
                                        })
                                        
                                        # Save away team rest days
                                        db.execute(insert_query, {
                                            "match_id": match_id,
                                            "team_id": away_team_id,
                                            "rest_days": max(0, away_rest),
                                            "is_midweek": is_midweek
                                        })
                                        
                                        db.commit()
                                        db_saved = True
                                        logger.info(f"Created table and saved rest days to database for match {match_id}")
                                        
                                    except Exception as create_error:
                                        try:
                                            db.rollback()
                                        except:
                                            pass
                                        logger.error(f"Failed to create/save rest days to database for match {match_id}: {create_error}", exc_info=True)
                                else:
                                    logger.error(f"Failed to save rest days to database for match {match_id}: {db_error}", exc_info=True)
                            
                            # Always add to CSV records (even if DB save failed)
                            rest_days_records.append({
                                "league_code": league.code,
                                "season": season_filter or "all",
                                "match_date": match_date.isoformat() if hasattr(match_date, "isoformat") else str(match_date),
                                "home_team": home_team.name if home_team else f"Team {home_team_id}",
                                "away_team": away_team.name if away_team else f"Team {away_team_id}",
                                "home_rest_days": max(0, home_rest),
                                "away_rest_days": max(0, away_rest),
                                "is_midweek": is_midweek
                            })
                            
                            # Only count as successful if database save succeeded
                            if db_saved:
                                results["successful"] += 1
                                logger.debug(f"Successfully saved rest days for match {match_id} to database")
                            else:
                                results["failed"] += 1
                                logger.warning(f"Rest days not saved to database for match {match_id}, but CSV will be saved")
                            
                        except Exception as e:
                            results["failed"] += 1
                            logger.warning(f"Failed to calculate rest days for match {match_id}: {e}")
                    
                    # Save CSV for this league/season combination
                    if save_csv and rest_days_records:
                        try:
                            csv_path = _save_rest_days_csv_batch(db, league.code, season_filter or "all", rest_days_records)
                            logger.info(f"Saved Rest Days CSV for {league.code} ({season_filter or 'all'}): {len(rest_days_records)} records")
                        except Exception as e:
                            logger.warning(f"Failed to save Rest Days CSV for {league.code} ({season_filter or 'all'}): {e}")
                
                except Exception as e:
                    logger.error(f"Error processing league {league.code} season {season_filter}: {e}")
                    continue
        
        logger.info(f"Batch rest days ingestion complete: {results['successful']} successful (saved to DB), {results['failed']} failed out of {results['total']} processed")
        logger.info(f"Database saves: {results['successful']} records saved to team_rest_days_historical table")
        
        return {
            "success": True,
            **results,
            "message": f"Processed {results['total']} matches. {results['successful']} saved to database, {results['failed']} failed."
        }
    
    except Exception as e:
        logger.error(f"Error in batch rest days ingestion: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

