"""
Ingest Expected Goals (xG) data for draw probability modeling

xG data helps predict draw probability by measuring chance quality.
Low xG matches (defensive) tend to have higher draw rates.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models import JackpotFixture, League, Match
from typing import Optional, Dict, List
from datetime import datetime, date
from pathlib import Path
import pandas as pd
import logging
import numpy as np
from app.services.ingestion.draw_structural_validation import (
    DrawStructuralValidator,
    validate_before_insert
)

logger = logging.getLogger(__name__)

# xG draw index calculation parameters
XG_DRAW_BASELINE = 2.5  # Average total xG per match
XG_DRAW_SENSITIVITY = 0.08  # 0.08 per unit deviation from baseline


def calculate_xg_draw_index(xg_total: float) -> float:
    """
    Calculate draw probability adjustment factor based on total xG.
    
    Formula: 1.0 + (baseline - xg_total) * sensitivity
    - Lower xG (defensive match) → higher draw probability
    - Higher xG (attacking match) → lower draw probability
    
    Examples:
    - xg_total=1.5 → index=1.08 (8% boost to draw probability)
    - xg_total=2.5 → index=1.00 (neutral)
    - xg_total=3.5 → index=0.92 (8% reduction)
    
    Args:
        xg_total: Total expected goals (home + away)
    
    Returns:
        Draw adjustment factor (bounded between 0.8 and 1.2)
    """
    if xg_total is None or xg_total < 0:
        return 1.0  # Neutral if missing
    
    index = 1.0 + (XG_DRAW_BASELINE - xg_total) * XG_DRAW_SENSITIVITY
    return float(np.clip(index, 0.8, 1.2))


def ingest_xg_for_fixture(
    db: Session,
    fixture_id: int,
    xg_home: float,
    xg_away: float
) -> Dict:
    """
    Ingest xG data for a single fixture.
    
    Args:
        db: Database session
        fixture_id: Fixture ID
        xg_home: Expected goals for home team
        xg_away: Expected goals for away team
    
    Returns:
        Dict with ingestion result
    """
    try:
        xg_total = xg_home + xg_away
        xg_draw_index = calculate_xg_draw_index(xg_total)
        
        # Check if table exists, create if not
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS match_xg (
                id              SERIAL PRIMARY KEY,
                fixture_id      INTEGER NOT NULL REFERENCES jackpot_fixtures(id) ON DELETE CASCADE,
                xg_home         DOUBLE PRECISION CHECK (xg_home >= 0),
                xg_away         DOUBLE PRECISION CHECK (xg_away >= 0),
                xg_total        DOUBLE PRECISION CHECK (xg_total >= 0),
                xg_draw_index   DOUBLE PRECISION CHECK (xg_draw_index BETWEEN 0.8 AND 1.2),
                recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uix_match_xg_fixture UNIQUE (fixture_id)
            )
        """))
        
        # Insert or update xG data
        db.execute(
            text("""
                INSERT INTO match_xg (fixture_id, xg_home, xg_away, xg_total, xg_draw_index)
                VALUES (:fixture_id, :xg_home, :xg_away, :xg_total, :xg_draw_index)
                ON CONFLICT (fixture_id) DO UPDATE SET
                    xg_home = EXCLUDED.xg_home,
                    xg_away = EXCLUDED.xg_away,
                    xg_total = EXCLUDED.xg_total,
                    xg_draw_index = EXCLUDED.xg_draw_index,
                    recorded_at = now()
            """),
            {
                "fixture_id": fixture_id,
                "xg_home": xg_home,
                "xg_away": xg_away,
                "xg_total": xg_total,
                "xg_draw_index": xg_draw_index
            }
        )
        
        db.commit()
        
        return {
            "success": True,
            "fixture_id": fixture_id,
            "xg_home": xg_home,
            "xg_away": xg_away,
            "xg_total": xg_total,
            "xg_draw_index": xg_draw_index
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to ingest xG data for fixture {fixture_id}: {e}")
        return {
            "success": False,
            "fixture_id": fixture_id,
            "error": str(e)
        }


def ingest_xg_from_csv(
    db: Session,
    csv_path: str
) -> Dict:
    """
    Ingest xG data from CSV file in our format.
    
    CSV Format: match_id,xg_home,xg_away,xg_total,xg_draw_index
    
    Args:
        db: Database session
        csv_path: Path to CSV file
    
    Returns:
        Dict with ingestion statistics
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_cols = ['match_id', 'xg_home', 'xg_away']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {"success": False, "error": f"Missing required columns: {missing_cols}"}
        
        inserted = 0
        updated = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                match_id = int(row['match_id'])
                xg_home = float(row['xg_home']) if pd.notna(row['xg_home']) else 0.0
                xg_away = float(row['xg_away']) if pd.notna(row['xg_away']) else 0.0
                
                # Use xg_total and xg_draw_index from CSV if available, otherwise calculate
                xg_total = float(row.get('xg_total', xg_home + xg_away)) if pd.notna(row.get('xg_total')) else (xg_home + xg_away)
                xg_draw_index = float(row.get('xg_draw_index', calculate_xg_draw_index(xg_total))) if pd.notna(row.get('xg_draw_index')) else calculate_xg_draw_index(xg_total)
                
                # Verify match exists
                from app.db.models import Match
                match = db.query(Match).filter(Match.id == match_id).first()
                if not match:
                    logger.warning(f"Match ID {match_id} not found, skipping")
                    errors += 1
                    continue
                
                # Insert or update in match_xg_historical
                from sqlalchemy import text
                existing = db.execute(
                    text("""
                        SELECT id FROM match_xg_historical 
                        WHERE match_id = :match_id
                    """),
                    {"match_id": match_id}
                ).fetchone()
                
                if existing:
                    db.execute(
                        text("""
                            UPDATE match_xg_historical 
                            SET xg_home = :xg_home,
                                xg_away = :xg_away,
                                xg_total = :xg_total,
                                xg_draw_index = :xg_draw_index
                            WHERE match_id = :match_id
                        """),
                        {
                            "match_id": match_id,
                            "xg_home": xg_home,
                            "xg_away": xg_away,
                            "xg_total": xg_total,
                            "xg_draw_index": xg_draw_index
                        }
                    )
                    updated += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO match_xg_historical 
                            (match_id, xg_home, xg_away, xg_total, xg_draw_index)
                            VALUES (:match_id, :xg_home, :xg_away, :xg_total, :xg_draw_index)
                        """),
                        {
                            "match_id": match_id,
                            "xg_home": xg_home,
                            "xg_away": xg_away,
                            "xg_total": xg_total,
                            "xg_draw_index": xg_draw_index
                        }
                    )
                    inserted += 1
                
            except Exception as e:
                logger.warning(f"Error processing xG row: {e}")
                errors += 1
                continue
        
        db.commit()
        
        logger.info(f"Ingested xG data from CSV: {inserted} inserted, {updated} updated, {errors} errors")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting xG data from CSV: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_xg_for_match(
    db: Session,
    match_id: int,
    xg_home: float,
    xg_away: float
) -> Dict:
    """
    Ingest xG data for a historical match.
    
    Args:
        db: Database session
        match_id: Match ID
        xg_home: Expected goals for home team
        xg_away: Expected goals for away team
    
    Returns:
        Dict with ingestion result
    """
    try:
        xg_total = xg_home + xg_away
        xg_draw_index = calculate_xg_draw_index(xg_total)
        
        # Check if table exists, create if not
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS match_xg_historical (
                id              SERIAL PRIMARY KEY,
                match_id        BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                xg_home         DOUBLE PRECISION CHECK (xg_home >= 0),
                xg_away         DOUBLE PRECISION CHECK (xg_away >= 0),
                xg_total        DOUBLE PRECISION CHECK (xg_total >= 0),
                xg_draw_index   DOUBLE PRECISION CHECK (xg_draw_index BETWEEN 0.8 AND 1.2),
                recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uix_match_xg_historical_match UNIQUE (match_id)
            )
        """))
        
        # Insert or update xG data
        db.execute(
            text("""
                INSERT INTO match_xg_historical (match_id, xg_home, xg_away, xg_total, xg_draw_index)
                VALUES (:match_id, :xg_home, :xg_away, :xg_total, :xg_draw_index)
                ON CONFLICT (match_id) DO UPDATE SET
                    xg_home = EXCLUDED.xg_home,
                    xg_away = EXCLUDED.xg_away,
                    xg_total = EXCLUDED.xg_total,
                    xg_draw_index = EXCLUDED.xg_draw_index,
                    recorded_at = now()
            """),
            {
                "match_id": match_id,
                "xg_home": xg_home,
                "xg_away": xg_away,
                "xg_total": xg_total,
                "xg_draw_index": xg_draw_index
            }
        )
        
        db.commit()
        
        return {
            "success": True,
            "match_id": match_id,
            "xg_home": xg_home,
            "xg_away": xg_away,
            "xg_total": xg_total,
            "xg_draw_index": xg_draw_index
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to ingest xG data for match {match_id}: {e}")
        return {
            "success": False,
            "match_id": match_id,
            "error": str(e)
        }


def batch_ingest_xg_from_matches(
    db: Session,
    league_ids: Optional[List[int]] = None,
    seasons: Optional[List[str]] = None,
    max_years: Optional[int] = None
) -> Dict:
    """
    Batch ingest xG data from matches table.
    
    Note: This function expects xG data to be pre-calculated or imported.
    For now, it creates placeholder entries based on actual goals (as proxy).
    In production, xG data should come from external sources (Understat, FBref, Opta).
    
    Args:
        db: Database session
        league_ids: List of league IDs to process (None = all)
        seasons: List of seasons to process (None = all)
        max_years: Maximum years back to process (None = all)
    
    Returns:
        Dict with batch ingestion statistics
    """
    results = {
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "total_processed": 0
    }
    
    try:
        # Build query for matches
        query = """
            SELECT m.id, m.league_id, m.home_goals, m.away_goals, m.match_date
            FROM matches m
            WHERE 1=1
        """
        params = {}
        
        if league_ids:
            query += " AND m.league_id = ANY(:league_ids)"
            params["league_ids"] = league_ids
        
        if seasons:
            query += " AND m.season = ANY(:seasons)"
            params["seasons"] = seasons
        
        if max_years:
            cutoff_date = date.today().replace(year=date.today().year - max_years)
            query += " AND m.match_date >= :cutoff_date"
            params["cutoff_date"] = cutoff_date
        
        query += " ORDER BY m.match_date DESC"
        
        matches = db.execute(text(query), params).fetchall()
        results["total_processed"] = len(matches)
        
        logger.info(f"Processing {len(matches)} matches for xG data ingestion")
        
        xg_records = []
        
        for match in matches:
            try:
                match_id = match.id
                home_goals = match.home_goals or 0
                away_goals = match.away_goals or 0
                
                # Use actual goals as proxy for xG (in production, use real xG data)
                # Add some noise to simulate xG (xG is typically 0.8-1.2x actual goals)
                # This is a placeholder - real implementation should use external xG sources
                import random
                xg_home = max(0, home_goals * (0.9 + random.random() * 0.3))
                xg_away = max(0, away_goals * (0.9 + random.random() * 0.3))
                
                result = ingest_xg_for_match(db, match_id, xg_home, xg_away)
                
                if result["success"]:
                    results["successful"] += 1
                    xg_records.append({
                        "match_id": match_id,
                        "xg_home": xg_home,
                        "xg_away": xg_away,
                        "xg_total": xg_home + xg_away,
                        "xg_draw_index": result["xg_draw_index"]
                    })
                else:
                    results["failed"] += 1
                    logger.warning(f"Failed to ingest xG for match {match_id}: {result.get('error')}")
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Error processing match {match.id}: {e}")
                db.rollback()
        
        # Save CSV file
        if xg_records:
            try:
                backend_root = Path(__file__).parent.parent.parent
                csv_dir = backend_root / "data" / "1_data_ingestion" / "Draw_structural" / "xG_Data"
                csv_dir.mkdir(parents=True, exist_ok=True)
                
                # Group by league and season for CSV files
                league_season_data = {}
                for record in xg_records:
                    match_info = db.execute(
                        text("SELECT league_id, season FROM matches WHERE id = :match_id"),
                        {"match_id": record["match_id"]}
                    ).fetchone()
                    
                    if match_info:
                        league_id = match_info.league_id
                        season = match_info.season
                        key = f"{league_id}_{season}"
                        
                        if key not in league_season_data:
                            league_season_data[key] = []
                        league_season_data[key].append(record)
                
                # Save CSV files per league/season
                for key, records in league_season_data.items():
                    df = pd.DataFrame(records)
                    league_id, season = key.split("_", 1)
                    
                    # Get league code
                    league_info = db.execute(
                        text("SELECT code FROM leagues WHERE id = :league_id"),
                        {"league_id": int(league_id)}
                    ).fetchone()
                    
                    league_code = league_info.code if league_info else f"L{league_id}"
                    filename = f"{league_code}_{season}_xg_data.csv"
                    filepath = csv_dir / filename
                    
                    df.to_csv(filepath, index=False)
                    logger.info(f"Saved xG CSV to: {filepath.absolute()}")
                
            except Exception as e:
                logger.error(f"Failed to save xG CSV files: {e}")
        
        logger.info(f"xG batch ingestion complete: {results['successful']} successful, {results['failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch xG ingestion: {e}")
        db.rollback()
        return results


def _save_xg_csv_batch(
    db: Session,
    xg_records: List[Dict],
    league_code: str,
    season: str
) -> Optional[Path]:
    """
    Save xG data to CSV file.
    
    Args:
        db: Database session
        xg_records: List of xG records
        league_code: League code
        season: Season string
    
    Returns:
        Path to saved CSV file or None
    """
    if not xg_records:
        return None
    
    try:
        df = pd.DataFrame(xg_records)
        filename = f"{league_code}_{season}_xg_data.csv"
        
        # Save to both locations
        from app.services.ingestion.draw_structural_utils import save_draw_structural_csv
        ingestion_path, cleaned_path = save_draw_structural_csv(
            df, "xG_Data", filename, save_to_cleaned=True
        )
        
        logger.info(f"Saved xG CSV: {filename}")
        return ingestion_path
    except Exception as e:
        logger.error(f"Failed to save xG CSV: {e}")
        return None

