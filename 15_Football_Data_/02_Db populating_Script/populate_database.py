#!/usr/bin/env python3
"""
Database Population Script
==========================
Populates PostgreSQL database from extracted Football.TXT data.

Features:
- FK-safe load order (leagues → teams → matches)
- Idempotent operations (ON CONFLICT handling)
- Deduplication at database level
- Team name normalization and matching
- Automatic calculation of derived statistics

Usage:
    python populate_database.py --csv matches_extracted.csv --db-url postgresql://user:pass@host/db
"""

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2 import sql
import argparse
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TeamNameNormalizer:
    """Normalize team names for matching"""
    
    # Common suffixes/prefixes to normalize
    NORMALIZATIONS = {
        ' FC': '',
        ' AFC': '',
        ' United': ' Utd',
        ' City': '',
        ' Town': '',
        ' Rovers': '',
        ' Wanderers': ' W',
        ' Athletic': ' Ath',
        ' Albion': '',
        ' Hotspur': '',
    }
    
    # Common team name variations
    VARIATIONS = {
        'manchester united': ['man utd', 'manchester utd', 'manchester united fc'],
        'manchester city': ['man city', 'manchester city fc'],
        'tottenham hotspur': ['tottenham', 'spurs', 'tottenham hotspur fc'],
        'arsenal': ['arsenal fc'],
        'liverpool': ['liverpool fc'],
        'chelsea': ['chelsea fc'],
        'newcastle united': ['newcastle', 'newcastle utd', 'newcastle united fc'],
    }
    
    @classmethod
    def normalize(cls, team_name: str) -> str:
        """Normalize team name"""
        if not team_name:
            return ''
        
        # Convert to lowercase for matching
        name_lower = team_name.lower().strip()
        
        # Check variations first
        for canonical, variations in cls.VARIATIONS.items():
            if name_lower in variations or name_lower == canonical:
                return canonical.title()
        
        # Apply normalizations
        normalized = team_name
        for old, new in cls.NORMALIZATIONS.items():
            normalized = normalized.replace(old, new)
        
        # Clean up
        normalized = ' '.join(normalized.split())
        return normalized.strip()
    
    @classmethod
    def create_canonical(cls, team_name: str) -> str:
        """Create canonical name for database storage"""
        normalized = cls.normalize(team_name)
        # Remove all non-alphanumeric except spaces
        canonical = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in normalized)
        canonical = ' '.join(canonical.split())
        return canonical.lower()


class DatabasePopulator:
    """Main database population orchestrator"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        self.cur = None
        self.normalizer = TeamNameNormalizer()
        
        # Cache for lookups
        self.league_cache: Dict[str, int] = {}
        self.team_cache: Dict[Tuple[str, int], int] = {}  # (canonical_name, league_id) -> team_id
        
    def connect(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cur = self.conn.cursor()
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def ensure_staging_schema(self):
        """Create staging schema and tables"""
        logger.info("Creating staging schema...")
        
        # Ensure we're not in a transaction for schema creation
        self.conn.commit()
        
        # Create schema
        self.cur.execute("""
            CREATE SCHEMA IF NOT EXISTS staging;
        """)
        self.conn.commit()
        
        # Drop table if exists to ensure clean state
        self.cur.execute("""
            DROP TABLE IF EXISTS staging.matches_raw CASCADE;
        """)
        self.conn.commit()
        
        # Create table
        self.cur.execute("""
            CREATE TABLE staging.matches_raw (
                match_date DATE,
                season VARCHAR(20),
                league_code VARCHAR(10),
                home_team TEXT,
                away_team TEXT,
                home_goals INTEGER,
                away_goals INTEGER,
                ht_home_goals INTEGER,
                ht_away_goals INTEGER,
                result CHAR(1),
                is_draw BOOLEAN,
                match_time TIME,
                venue VARCHAR(200),
                source_file TEXT,
                ingestion_batch_id VARCHAR(50),
                matchday INTEGER,
                round_name VARCHAR(50)
            );
        """)
        
        self.conn.commit()
        
        # Verify table exists
        self.cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'staging' 
                AND table_name = 'matches_raw'
            );
        """)
        exists = self.cur.fetchone()[0]
        if not exists:
            raise RuntimeError("Failed to create staging.matches_raw table")
        
        logger.info("Staging schema and table created successfully")
    
    def load_csv_to_staging(self, csv_path: Path):
        """Load CSV file into staging table"""
        logger.info(f"Loading CSV file: {csv_path}")
        
        # Verify table exists before proceeding
        self.cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'staging' 
                AND table_name = 'matches_raw'
            );
        """)
        if not self.cur.fetchone()[0]:
            raise RuntimeError("staging.matches_raw table does not exist. Schema creation may have failed.")
        
        # Clear staging table
        self.cur.execute("TRUNCATE TABLE staging.matches_raw;")
        self.conn.commit()
        
        # Read CSV with pandas to handle encoding issues
        logger.info("Reading CSV with pandas (handles encoding issues)...")
        try:
            # Try UTF-8 first, fallback to latin-1 or errors='replace'
            df = pd.read_csv(
                csv_path,
                encoding='utf-8',
                encoding_errors='replace',
                dtype={
                    'home_goals': 'Int64',
                    'away_goals': 'Int64',
                    'ht_home_goals': 'Int64',
                    'ht_away_goals': 'Int64',
                    'is_draw': 'Int64'
                },
                na_values=['', 'NULL', 'null', 'None']
            )
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            logger.warning("UTF-8 failed, trying latin-1 encoding")
            df = pd.read_csv(
                csv_path,
                encoding='latin-1',
                dtype={
                    'home_goals': 'Int64',
                    'away_goals': 'Int64',
                    'ht_home_goals': 'Int64',
                    'ht_away_goals': 'Int64',
                    'is_draw': 'Int64'
                },
                na_values=['', 'NULL', 'null', 'None']
            )
        
        # Replace all pandas NA/NaN with None (Python None for SQL NULL)
        df = df.replace({pd.NA: None, pd.NaT: None})
        df = df.where(pd.notna(df), None)
        
        # Convert is_draw to boolean if it's integer
        if 'is_draw' in df.columns:
            df['is_draw'] = df['is_draw'].fillna(0).astype(int).astype(bool)
        
        # Convert all values to Python native types (None instead of pd.NA)
        # This ensures psycopg2 can handle them
        def convert_value(val):
            if pd.isna(val) or val is pd.NA:
                return None
            if isinstance(val, (pd.Int64Dtype, pd.Float64Dtype)):
                return None if pd.isna(val) else val
            return None if val is None or (isinstance(val, float) and pd.isna(val)) else val
        
        # Prepare data rows, converting all NA to None
        data_rows = []
        for _, row in df.iterrows():
            row_tuple = tuple(
                None if pd.isna(val) or val is pd.NA else val
                for val in row.values
            )
            data_rows.append(row_tuple)
        
        # Use execute_values for bulk insert (faster than row-by-row)
        logger.info(f"Inserting {len(df)} rows into staging table...")
        execute_values(
            self.cur,
            """
            INSERT INTO staging.matches_raw (
                match_date, season, league_code,
                home_team, away_team,
                home_goals, away_goals,
                ht_home_goals, ht_away_goals,
                result, is_draw,
                match_time, venue,
                source_file, ingestion_batch_id,
                matchday, round_name
            ) VALUES %s
            """,
            data_rows,
            page_size=1000
        )
        
        self.conn.commit()
        
        # Get count
        self.cur.execute("SELECT COUNT(*) FROM staging.matches_raw;")
        count = self.cur.fetchone()[0]
        logger.info(f"Loaded {count} rows into staging table")
        return count
    
    def populate_leagues(self):
        """Populate leagues table from staging data"""
        logger.info("Populating leagues table...")
        
        # Get distinct leagues from staging
        self.cur.execute("""
            SELECT DISTINCT league_code
            FROM staging.matches_raw
            WHERE league_code IS NOT NULL AND league_code != ''
        """)
        
        league_codes = [row[0] for row in self.cur.fetchall()]
        
        # League code to name mapping (expand as needed)
        league_names = {
            'E0': 'Premier League',
            'E1': 'Championship',
            'E2': 'League One',
            'E3': 'League Two',
            'D1': 'Bundesliga',
            'D2': '2. Bundesliga',
            'D3': '3. Liga',
            'I1': 'Serie A',
            'I2': 'Serie B',
            'F1': 'Ligue 1',
            'F2': 'Ligue 2',
            'B1': 'Pro League',
            'CL': 'UEFA Champions League',
            'EL': 'UEFA Europa League',
            'CONF': 'UEFA Conference League',
        }
        
        country_map = {
            'E0': 'England', 'E1': 'England', 'E2': 'England', 'E3': 'England',
            'D1': 'Germany', 'D2': 'Germany', 'D3': 'Germany',
            'I1': 'Italy', 'I2': 'Italy',
            'F1': 'France', 'F2': 'France',
            'B1': 'Belgium',
            'CL': 'Europe', 'EL': 'Europe', 'CONF': 'Europe',
        }
        
        inserted = 0
        for code in league_codes:
            name = league_names.get(code, code)
            country = country_map.get(code, 'Unknown')
            
            self.cur.execute("""
                INSERT INTO leagues (code, name, country, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    updated_at = now()
                RETURNING id
            """, (code, name, country))
            
            league_id = self.cur.fetchone()[0]
            self.league_cache[code] = league_id
            inserted += 1
        
        self.conn.commit()
        logger.info(f"Populated {inserted} leagues")
        
        # Calculate and update league statistics after matches are populated
        # This will be called after populate_matches() completes
        logger.info("Note: League statistics will be calculated after matches are populated")
    
    def update_league_statistics(self):
        """Calculate and update avg_draw_rate and home_advantage for all leagues"""
        logger.info("Calculating league statistics (avg_draw_rate and home_advantage)...")
        
        try:
            self.cur.execute("""
                UPDATE leagues l
                SET 
                    avg_draw_rate = COALESCE((
                        SELECT AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END)::NUMERIC(5,4)
                        FROM matches m
                        WHERE m.league_id = l.id
                            AND m.result IS NOT NULL
                            AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
                        GROUP BY m.league_id
                    ), 0.26),  -- Default if no matches
                    
                    home_advantage = COALESCE((
                        SELECT AVG(m.home_goals - m.away_goals)::NUMERIC(5,4)
                        FROM matches m
                        WHERE m.league_id = l.id
                            AND m.home_goals IS NOT NULL
                            AND m.away_goals IS NOT NULL
                            AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
                        GROUP BY m.league_id
                    ), 0.35),  -- Default if no matches
                    
                    updated_at = now()
                WHERE EXISTS (
                    SELECT 1 FROM matches m WHERE m.league_id = l.id
                )
            """)
            
            updated_count = self.cur.rowcount
            self.conn.commit()
            logger.info(f"Updated statistics for {updated_count} leagues")
            
            # Log some examples
            self.cur.execute("""
                SELECT code, name, avg_draw_rate, home_advantage
                FROM leagues
                WHERE avg_draw_rate != 0.26 OR home_advantage != 0.35
                ORDER BY code
                LIMIT 10
            """)
            
            examples = self.cur.fetchall()
            if examples:
                logger.info("Sample calculated values:")
                for code, name, draw_rate, home_adv in examples:
                    logger.info(f"  {code} ({name}): draw_rate={draw_rate:.3f}, home_advantage={home_adv:.3f}")
            
        except Exception as e:
            logger.error(f"Error calculating league statistics: {e}")
            self.conn.rollback()
            raise
    
    def populate_teams(self):
        """Populate teams table with deduplication"""
        logger.info("Populating teams table...")
        
        # Get all unique team/league combinations
        self.cur.execute("""
            SELECT DISTINCT 
                league_code,
                home_team as team_name
            FROM staging.matches_raw
            WHERE league_code IS NOT NULL AND home_team IS NOT NULL
            
            UNION
            
            SELECT DISTINCT 
                league_code,
                away_team as team_name
            FROM staging.matches_raw
            WHERE league_code IS NOT NULL AND away_team IS NOT NULL
        """)
        
        team_league_pairs = self.cur.fetchall()
        
        inserted = 0
        updated = 0
        
        for league_code, team_name in team_league_pairs:
            if not team_name or not league_code:
                continue
            
            league_id = self.league_cache.get(league_code)
            if not league_id:
                logger.warning(f"League {league_code} not found, skipping team {team_name}")
                continue
            
            canonical_name = self.normalizer.create_canonical(team_name)
            
            # Insert or update team
            self.cur.execute("""
                INSERT INTO teams (league_id, name, canonical_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (canonical_name, league_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = now()
                RETURNING id
            """, (league_id, team_name, canonical_name))
            
            team_id = self.cur.fetchone()[0]
            self.team_cache[(canonical_name, league_id)] = team_id
            
            if self.cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1
        
        self.conn.commit()
        logger.info(f"Populated teams: {inserted} inserted, {updated} updated")
    
    def populate_matches(self):
        """Populate matches table with deduplication"""
        logger.info("Populating matches table...")
        
        # First, create a function to normalize team names in SQL
        self.cur.execute("""
            CREATE OR REPLACE FUNCTION normalize_team_name(team_text TEXT)
            RETURNS TEXT AS $$
            BEGIN
                -- Remove common suffixes
                team_text := REPLACE(team_text, ' FC', '');
                team_text := REPLACE(team_text, ' AFC', '');
                team_text := REPLACE(team_text, ' United', ' Utd');
                team_text := REPLACE(team_text, ' City', '');
                team_text := REPLACE(team_text, ' Town', '');
                
                -- Remove non-alphanumeric except spaces
                team_text := REGEXP_REPLACE(team_text, '[^a-zA-Z0-9 ]', '', 'g');
                
                -- Normalize whitespace and convert to lowercase
                team_text := LOWER(TRIM(REGEXP_REPLACE(team_text, '\\s+', ' ', 'g')));
                
                RETURN team_text;
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)
        
        # Count how many matches will be processed
        self.cur.execute("""
            SELECT COUNT(*) 
            FROM staging.matches_raw r
            JOIN leagues l ON l.code = r.league_code
            JOIN teams ht ON ht.league_id = l.id 
                AND ht.canonical_name = normalize_team_name(r.home_team)
            JOIN teams at ON at.league_id = l.id 
                AND at.canonical_name = normalize_team_name(r.away_team)
            WHERE r.match_date IS NOT NULL
                AND r.home_goals IS NOT NULL
                AND r.away_goals IS NOT NULL
                AND r.result IS NOT NULL
        """)
        total_matches = self.cur.fetchone()[0]
        self.logger.info(f"Processing {total_matches:,} matches (this may take 5-10 minutes)...")
        self.logger.info("Starting match insertion - please wait, this is a large operation...")
        start_time = datetime.now()
        
        # Now insert matches with proper team matching (including all new columns)
        self.cur.execute("""
            INSERT INTO matches (
                league_id, season, match_date,
                home_team_id, away_team_id,
                home_goals, away_goals, result,
                ht_home_goals, ht_away_goals,
                match_time, venue,
                source, source_file, ingestion_batch_id,
                matchday, round_name
            )
            SELECT
                l.id as league_id,
                COALESCE(
                    NULLIF(r.season, ''),
                    -- Extract season from filename if missing (e.g., 2023-24_hr1.txt -> 2023-24)
                    CASE 
                        WHEN r.source_file ~ '(\\d{4})-(\\d{2})_' THEN 
                            SUBSTRING(r.source_file FROM '(\\d{4}-\\d{2})')
                        WHEN r.source_file ~ '(\\d{4})_' THEN
                            SUBSTRING(r.source_file FROM '(\\d{4})') || '-' || 
                            SUBSTRING(CAST(SUBSTRING(r.source_file FROM '(\\d{4})')::INTEGER + 1 AS TEXT) FROM '..$')
                        ELSE NULL
                    END,
                    -- Fallback: extract from match_date year
                    TO_CHAR(r.match_date, 'YYYY') || '-' || 
                    SUBSTRING(CAST(EXTRACT(YEAR FROM r.match_date)::INTEGER + 1 AS TEXT) FROM '..$')
                ) as season,
                r.match_date,
                ht.id as home_team_id,
                at.id as away_team_id,
                r.home_goals,
                r.away_goals,
                r.result::match_result,
                -- Ensure both HT goals are NULL together (constraint requirement)
                CASE 
                    WHEN (r.ht_home_goals IS NULL OR r.ht_home_goals = 0 OR r.ht_away_goals IS NULL OR r.ht_away_goals = 0) 
                    THEN NULL
                    ELSE r.ht_home_goals
                END as ht_home_goals,
                CASE 
                    WHEN (r.ht_home_goals IS NULL OR r.ht_home_goals = 0 OR r.ht_away_goals IS NULL OR r.ht_away_goals = 0) 
                    THEN NULL
                    ELSE r.ht_away_goals
                END as ht_away_goals,
                r.match_time::TIME,
                r.venue,
                'football-txt-extraction' as source,
                r.source_file,
                r.ingestion_batch_id,
                r.matchday,
                r.round_name
            FROM (
                SELECT DISTINCT ON (r.match_date, r.home_team, r.away_team, r.league_code)
                    r.*
                FROM staging.matches_raw r
                WHERE r.match_date IS NOT NULL
                    AND r.home_goals IS NOT NULL
                    AND r.away_goals IS NOT NULL
                    AND r.result IS NOT NULL
                ORDER BY r.match_date, r.home_team, r.away_team, r.league_code, r.source_file
            ) r
            JOIN leagues l ON l.code = r.league_code
            JOIN teams ht ON ht.league_id = l.id 
                AND ht.canonical_name = normalize_team_name(r.home_team)
            JOIN teams at ON at.league_id = l.id 
                AND at.canonical_name = normalize_team_name(r.away_team)
            WHERE COALESCE(
                    NULLIF(r.season, ''),
                    CASE 
                        WHEN r.source_file ~ '(\\d{4})-(\\d{2})_' THEN 
                            SUBSTRING(r.source_file FROM '(\\d{4}-\\d{2})')
                        WHEN r.source_file ~ '(\\d{4})_' THEN
                            SUBSTRING(r.source_file FROM '(\\d{4})') || '-' || 
                            SUBSTRING(CAST(SUBSTRING(r.source_file FROM '(\\d{4})')::INTEGER + 1 AS TEXT) FROM '..$')
                        ELSE NULL
                    END,
                    TO_CHAR(r.match_date, 'YYYY') || '-' || 
                    SUBSTRING(CAST(EXTRACT(YEAR FROM r.match_date)::INTEGER + 1 AS TEXT) FROM '..$')
                ) IS NOT NULL
            ON CONFLICT (home_team_id, away_team_id, match_date) DO UPDATE SET
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                result = EXCLUDED.result,
                ht_home_goals = EXCLUDED.ht_home_goals,
                ht_away_goals = EXCLUDED.ht_away_goals,
                match_time = EXCLUDED.match_time,
                venue = EXCLUDED.venue,
                source_file = EXCLUDED.source_file,
                ingestion_batch_id = EXCLUDED.ingestion_batch_id,
                matchday = EXCLUDED.matchday,
                round_name = EXCLUDED.round_name
        """)
        
        inserted = self.cur.rowcount
        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Populated {inserted:,} matches successfully in {elapsed:.1f} seconds")
        
        # Check for unmatched teams
        self.cur.execute("""
            SELECT DISTINCT r.home_team, r.league_code
            FROM staging.matches_raw r
            LEFT JOIN leagues l ON l.code = r.league_code
            LEFT JOIN teams ht ON ht.league_id = l.id 
                AND ht.canonical_name = normalize_team_name(r.home_team)
            WHERE ht.id IS NULL AND r.home_team IS NOT NULL
            LIMIT 10
        """)
        
        unmatched = self.cur.fetchall()
        if unmatched:
            logger.warning(f"Found {len(unmatched)} unmatched home teams (showing first 10):")
            for team, league in unmatched:
                logger.warning(f"  - {team} (league: {league})")
        
        self.conn.commit()
        
        self.cur.execute("SELECT COUNT(*) FROM matches WHERE source = 'football-txt-extraction';")
        total_count = self.cur.fetchone()[0]
        logger.info(f"Populated {inserted} matches (total: {total_count})")
    
    def populate_derived_statistics(self):
        """Populate derived statistics tables"""
        logger.info("Populating derived statistics...")
        
        # 1. League draw priors
        self.cur.execute("""
            INSERT INTO league_draw_priors (league_id, season, draw_rate, sample_size)
            SELECT
                league_id,
                season,
                AVG(CASE WHEN result = 'D' THEN 1.0 ELSE 0.0 END) as draw_rate,
                COUNT(*) as sample_size
            FROM matches
            WHERE season IS NOT NULL
            GROUP BY league_id, season
            ON CONFLICT (league_id, season) DO UPDATE SET
                draw_rate = EXCLUDED.draw_rate,
                sample_size = EXCLUDED.sample_size,
                updated_at = now()
        """)
        
        # 2. H2H draw stats
        self.cur.execute("""
            INSERT INTO h2h_draw_stats (
                team_home_id, team_away_id,
                matches_played, draw_count, draw_rate
            )
            SELECT
                home_team_id,
                away_team_id,
                COUNT(*) as matches_played,
                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draw_count,
                AVG(CASE WHEN result = 'D' THEN 1.0 ELSE 0.0 END) as draw_rate
            FROM matches
            GROUP BY home_team_id, away_team_id
            HAVING COUNT(*) >= 3
            ON CONFLICT (team_home_id, team_away_id) DO UPDATE SET
                matches_played = EXCLUDED.matches_played,
                draw_count = EXCLUDED.draw_count,
                draw_rate = EXCLUDED.draw_rate,
                last_updated = now()
        """)
        
        # 3. Team H2H stats (existing table)
        self.cur.execute("""
            INSERT INTO team_h2h_stats (
                team_home_id, team_away_id,
                meetings, draws, draw_rate
            )
            SELECT
                home_team_id,
                away_team_id,
                COUNT(*) as meetings,
                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                AVG(CASE WHEN result = 'D' THEN 1.0 ELSE 0.0 END) as draw_rate
            FROM matches
            GROUP BY home_team_id, away_team_id
            HAVING COUNT(*) >= 3
            ON CONFLICT (team_home_id, team_away_id) DO UPDATE SET
                meetings = EXCLUDED.meetings,
                draws = EXCLUDED.draws,
                draw_rate = EXCLUDED.draw_rate,
                updated_at = now()
        """)
        
        # 4. League stats
        self.cur.execute("""
            INSERT INTO league_stats (
                league_id, season, calculated_at,
                total_matches, home_win_rate, draw_rate, away_win_rate,
                avg_goals_per_match, home_advantage_factor
            )
            SELECT
                league_id,
                season,
                now() as calculated_at,
                COUNT(*) as total_matches,
                AVG(CASE WHEN result = 'H' THEN 1.0 ELSE 0.0 END) as home_win_rate,
                AVG(CASE WHEN result = 'D' THEN 1.0 ELSE 0.0 END) as draw_rate,
                AVG(CASE WHEN result = 'A' THEN 1.0 ELSE 0.0 END) as away_win_rate,
                AVG(home_goals + away_goals) as avg_goals_per_match,
                0.35 as home_advantage_factor  -- Default, can be calculated
            FROM matches
            WHERE season IS NOT NULL
            GROUP BY league_id, season
            ON CONFLICT (league_id, season) DO UPDATE SET
                total_matches = EXCLUDED.total_matches,
                home_win_rate = EXCLUDED.home_win_rate,
                draw_rate = EXCLUDED.draw_rate,
                away_win_rate = EXCLUDED.away_win_rate,
                avg_goals_per_match = EXCLUDED.avg_goals_per_match,
                updated_at = now()
        """)
        
        self.conn.commit()
        logger.info("Derived statistics populated")
    
    def populate_data_source(self):
        """Register data source"""
        logger.info("Registering data source...")
        
        self.cur.execute("""
            INSERT INTO data_sources (name, source_type, status, last_sync_at, record_count)
            VALUES ('football-txt-extraction', 'football-txt', 'fresh', now(), 
                    (SELECT COUNT(*) FROM matches WHERE source = 'football-txt-extraction'))
            ON CONFLICT (name) DO UPDATE SET
                status = 'fresh',
                last_sync_at = now(),
                record_count = (SELECT COUNT(*) FROM matches WHERE source = 'football-txt-extraction'),
                updated_at = now()
        """)
        
        self.conn.commit()
        logger.info("Data source registered")
    
    def generate_report(self) -> Dict:
        """Generate population report"""
        report = {}
        
        # Count matches by league
        self.cur.execute("""
            SELECT l.code, l.name, COUNT(*) as match_count
            FROM matches m
            JOIN leagues l ON l.id = m.league_id
            WHERE m.source = 'football-txt-extraction'
            GROUP BY l.code, l.name
            ORDER BY match_count DESC
        """)
        report['matches_by_league'] = [
            {'code': row[0], 'name': row[1], 'count': row[2]}
            for row in self.cur.fetchall()
        ]
        
        # Total statistics
        self.cur.execute("""
            SELECT 
                COUNT(*) as total_matches,
                COUNT(DISTINCT league_id) as total_leagues,
                COUNT(DISTINCT season) as total_seasons,
                SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as total_draws
            FROM matches
            WHERE source = 'football-txt-extraction'
        """)
        row = self.cur.fetchone()
        report['totals'] = {
            'matches': row[0],
            'leagues': row[1],
            'seasons': row[2],
            'draws': row[3],
            'draw_rate': row[3] / row[0] if row[0] > 0 else 0
        }
        
        return report
    
    def run(self, csv_path: Path):
        """Run full population process"""
        try:
            self.connect()
            self.ensure_staging_schema()
            
            # Phase 0: Load CSV to staging
            self.load_csv_to_staging(csv_path)
            
            # Phase 1: Populate reference tables
            self.populate_leagues()
            self.populate_teams()
            
            # Phase 2: Populate fact tables
            self.populate_matches()
            
            # Phase 2.5: Update league statistics (avg_draw_rate, home_advantage)
            self.update_league_statistics()
            
            # Phase 3: Populate derived statistics
            self.populate_derived_statistics()
            
            # Phase 4: Register data source
            self.populate_data_source()
            
            # Generate report
            report = self.generate_report()
            
            logger.info("\n" + "="*60)
            logger.info("POPULATION COMPLETE")
            logger.info("="*60)
            logger.info(f"Total matches: {report['totals']['matches']}")
            logger.info(f"Total leagues: {report['totals']['leagues']}")
            logger.info(f"Total seasons: {report['totals']['seasons']}")
            logger.info(f"Total draws: {report['totals']['draws']}")
            logger.info(f"Draw rate: {report['totals']['draw_rate']:.2%}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error during population: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Populate database from extracted CSV')
    parser.add_argument(
        '--csv',
        type=str,
        required=True,
        help='Path to extracted matches CSV file'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        required=True,
        help='PostgreSQL connection URL (postgresql://user:pass@host/db)'
    )
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    populator = DatabasePopulator(args.db_url)
    report = populator.run(csv_path)
    
    # Write report to JSON
    report_path = Path(args.csv).parent / 'population_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Report written to {report_path}")


if __name__ == '__main__':
    main()

