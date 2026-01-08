#!/usr/bin/env python3
"""
Import Data from SQL Export Files
==================================
Imports data from DBeaver SQL export files into the new database schema.

This script:
- Reads SQL INSERT statements from export files
- Maps old IDs to new IDs (leagues, teams, models)
- Uses ON CONFLICT to prevent duplicates
- Preserves foreign key relationships

Usage:
    python import_from_sql_exports.py --export-dir "C:\Users\Admin\Desktop\Exported_Football _DB"
"""

import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SQLExportImporter:
    """Import data from SQL export files"""
    
    def __init__(self, db_url: str, export_dir: Path):
        self.db_url = db_url
        self.export_dir = Path(export_dir)
        self.conn = None
        self.cur = None
        
        # ID mapping tables (in-memory)
        self.league_id_map: Dict[int, int] = {}
        self.team_id_map: Dict[int, int] = {}
        self.model_id_map: Dict[int, int] = {}
    
    def connect(self):
        """Connect to database"""
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        logger.info("Connected to database")
    
    def close(self):
        """Close database connection"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def parse_insert_statement(self, sql_line: str) -> Optional[Dict]:
        """Parse a single INSERT statement line"""
        # Pattern: INSERT INTO table (cols) VALUES (vals);
        pattern = r"INSERT INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
        match = re.search(pattern, sql_line, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        columns = [c.strip().strip('"') for c in match.group(2).split(',')]
        values_str = match.group(3)
        
        # Parse values (handle NULL, strings, numbers, enums)
        values = []
        current_value = ""
        in_quotes = False
        quote_char = None
        
        for char in values_str:
            if char in ("'", '"') and (not current_value or current_value[-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current_value += char
            elif char == ',' and not in_quotes:
                values.append(self._parse_value(current_value.strip()))
                current_value = ""
            else:
                current_value += char
        
        if current_value:
            values.append(self._parse_value(current_value.strip()))
        
        return {
            'table': table_name,
            'columns': columns,
            'values': values
        }
    
    def _parse_value(self, value_str: str):
        """Parse a single value from SQL"""
        value_str = value_str.strip()
        
        if value_str.upper() == 'NULL':
            return None
        if value_str.startswith("'") and value_str.endswith("'"):
            # String value
            return value_str[1:-1].replace("''", "'")
        if value_str.startswith('::'):
            # Type cast (e.g., 'H'::public.match_result)
            return value_str.split('::')[0].strip("'\"")
        try:
            # Try integer
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
    
    def import_leagues(self, sql_file: Path):
        """Import leagues and create ID mapping"""
        logger.info(f"Importing leagues from {sql_file.name}...")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract INSERT statements
        insert_pattern = r"INSERT INTO\s+public\.leagues[^;]+;"
        matches = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)
        
        imported = 0
        for match in matches:
            # Parse each INSERT statement
            parsed = self.parse_insert_statement(match)
            if not parsed or parsed['table'] != 'leagues':
                continue
            
            # Find column indices
            col_map = {col: i for i, col in enumerate(parsed['columns'])}
            
            # Extract values
            old_id = parsed['values'][col_map.get('id', 0)]
            code = parsed['values'][col_map.get('code', 1)]
            name = parsed['values'][col_map.get('name', 2)]
            country = parsed['values'][col_map.get('country', 3)]
            tier = parsed['values'][col_map.get('tier', 4)] or 1
            avg_draw_rate = parsed['values'][col_map.get('avg_draw_rate', 5)] or 0.26
            home_advantage = parsed['values'][col_map.get('home_advantage', 6)] or 0.35
            is_active = parsed['values'][col_map.get('is_active', 7)]
            
            # Insert or update league
            self.cur.execute("""
                INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    tier = EXCLUDED.tier,
                    avg_draw_rate = EXCLUDED.avg_draw_rate,
                    home_advantage = EXCLUDED.home_advantage,
                    is_active = EXCLUDED.is_active,
                    updated_at = now()
                RETURNING id
            """, (code, name, country, tier, avg_draw_rate, home_advantage, is_active))
            
            new_id = self.cur.fetchone()['id']
            self.league_id_map[old_id] = new_id
            imported += 1
        
        self.conn.commit()
        logger.info(f"Imported {imported} leagues, created {len(self.league_id_map)} ID mappings")
    
    def import_teams(self, sql_file: Path):
        """Import teams and create ID mapping"""
        logger.info(f"Importing teams from {sql_file.name}...")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract INSERT statements (handle multi-line)
        insert_pattern = r"INSERT INTO\s+public\.teams[^;]+;"
        matches = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)
        
        imported = 0
        for match in matches:
            # Split by VALUES to handle multiple rows
            if 'VALUES' not in match:
                continue
            
            # Extract column names
            cols_match = re.search(r'\(([^)]+)\)', match.split('VALUES')[0])
            if not cols_match:
                continue
            
            columns = [c.strip().strip('"') for c in cols_match.group(1).split(',')]
            col_map = {col: i for i, col in enumerate(columns)}
            
            # Extract all value rows
            values_section = match.split('VALUES')[1].strip().rstrip(';')
            
            # Split by ),( to get individual rows
            rows = re.split(r'\),\s*\(', values_section)
            rows[0] = rows[0].lstrip('(')
            rows[-1] = rows[-1].rstrip(')')
            
            for row_str in rows:
                row_str = '(' + row_str + ')'
                parsed = self.parse_insert_statement(f"INSERT INTO teams (dummy) VALUES {row_str}")
                if not parsed:
                    continue
                
                values = parsed['values']
                
                # Map values to columns
                old_id = values[col_map.get('id', 0)]
                old_league_id = values[col_map.get('league_id', 1)]
                name = values[col_map.get('name', 2)]
                canonical_name = values[col_map.get('canonical_name', 3)]
                attack_rating = values[col_map.get('attack_rating', 4)] or 1.0
                defense_rating = values[col_map.get('defense_rating', 5)] or 1.0
                home_bias = values[col_map.get('home_bias', 6)] or 0.0
                last_calculated = values[col_map.get('last_calculated', 7)]
                alternative_names = values[col_map.get('alternative_names', 10)]
                
                # Map league_id
                new_league_id = self.league_id_map.get(old_league_id)
                if not new_league_id:
                    logger.warning(f"League ID {old_league_id} not found in mapping, skipping team {name}")
                    continue
                
                # Insert or update team
                self.cur.execute("""
                    INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias, last_calculated, alternative_names)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_name, league_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        attack_rating = EXCLUDED.attack_rating,
                        defense_rating = EXCLUDED.defense_rating,
                        home_bias = EXCLUDED.home_bias,
                        last_calculated = EXCLUDED.last_calculated,
                        alternative_names = EXCLUDED.alternative_names,
                        updated_at = now()
                    RETURNING id
                """, (new_league_id, name, canonical_name, attack_rating, defense_rating, home_bias, last_calculated, alternative_names))
                
                new_id = self.cur.fetchone()['id']
                self.team_id_map[old_id] = new_id
                imported += 1
        
        self.conn.commit()
        logger.info(f"Imported {imported} teams, created {len(self.team_id_map)} ID mappings")
    
    def import_models(self, sql_file: Path):
        """Import models and create ID mapping"""
        logger.info(f"Importing models from {sql_file.name}...")
        
        # Similar implementation to import_leagues
        # Extract INSERT statements, parse, insert with ON CONFLICT
        # Map model IDs
        
        logger.info("Models import not yet implemented - use manual SQL import")
    
    def import_calibration_data(self, sql_file: Path):
        """Import calibration data (map model_id and league_id)"""
        logger.info(f"Importing calibration data from {sql_file.name}...")
        
        # Similar implementation
        # Map model_id and league_id using mapping tables
        # Use ON CONFLICT to prevent duplicates
        
        logger.info("Calibration data import not yet implemented - use manual SQL import")
    
    def run(self):
        """Run full import process"""
        try:
            self.connect()
            
            # Step 1: Import leagues (creates ID mapping)
            leagues_file = self.export_dir / 'leagues_202601081444.sql'
            if leagues_file.exists():
                self.import_leagues(leagues_file)
            else:
                logger.warning(f"Leagues file not found: {leagues_file}")
            
            # Step 2: Import teams (uses league mapping)
            teams_file = self.export_dir / 'teams_202601081444.sql'
            if teams_file.exists():
                self.import_teams(teams_file)
            else:
                logger.warning(f"Teams file not found: {teams_file}")
            
            # Step 3: Import other tables
            # (models, calibration_data, etc.)
            
            logger.info("Import completed successfully")
            
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            self.conn.rollback()
            raise
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description='Import data from SQL export files')
    parser.add_argument(
        '--export-dir',
        type=str,
        default=r'C:\Users\Admin\Desktop\Exported_Football _DB',
        help='Directory containing SQL export files'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default='postgresql://postgres:postgres@localhost/football_probability_engine',
        help='Database connection URL'
    )
    
    args = parser.parse_args()
    
    importer = SQLExportImporter(args.db_url, args.export_dir)
    importer.run()


if __name__ == '__main__':
    main()

