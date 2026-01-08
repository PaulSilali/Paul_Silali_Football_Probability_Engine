#!/usr/bin/env python3
"""
Football Data Extraction Script
================================
Extracts match data from Football.TXT format files and converts to structured format
for database ingestion.

Supports:
- All *-master folders (england-master, deutschland-master, etc.)
- Multiple seasons per league
- Half-time scores extraction
- Team name normalization
- Deduplication at extraction level

Output: CSV files ready for database import with proper deduplication
"""

import re
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FootballTXTParser:
    """Parser for Football.TXT format files"""
    
    # Date patterns (multiple formats)
    DATE_PATTERNS = [
        r'(\w{3})\s+(\w{3})/(\d{1,2})\s+(\d{4})',  # Fri Aug/16 2024
        r'\[(\w{3})\s+(\d{1,2})\.(\d{1,2})\.\]',   # [Sat Aug/19]
        r'(\w{3})\s+(\d{1,2})\.(\d{1,2})\.',       # Sat 19.8.
    ]
    
    # Match line patterns
    MATCH_PATTERN = re.compile(
        r'(\d{1,2}\.\d{2})?\s*'  # Optional time
        r'([A-Za-z0-9\s&\-\.\'\(\)]+?)\s+'  # Home team
        r'v\s+'  # 'v' separator
        r'([A-Za-z0-9\s&\-\.\'\(\)]+?)\s+'  # Away team
        r'(\d{1,2})-(\d{1,2})'  # Score
        r'(?:\s+\((\d{1,2})-(\d{1,2})\))?'  # Optional half-time score
    )
    
    # Alternative pattern for different formats (e.g., Italy)
    MATCH_PATTERN_ALT = re.compile(
        r'(\d{1,2}\.\d{2})?\s*'  # Optional time
        r'([A-Za-z0-9\s&\-\.\'\(\)]+?)\s+'  # Home team
        r'(\d{1,2})-(\d{1,2})'  # Score
        r'(?:\s+\((\d{1,2})-(\d{1,2})\))?\s+'  # Optional half-time score
        r'([A-Za-z0-9\s&\-\.\'\(\)]+?)$'  # Away team (at end)
    )
    
    MONTH_MAP = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.current_date = None
        self.current_season = None
        self.current_league = None
        
    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name for matching"""
        # Remove extra whitespace
        name = ' '.join(team_name.split())
        # Remove common suffixes/prefixes that vary
        name = name.replace(' FC', '').replace(' AFC', '').replace(' United', ' Utd')
        name = name.replace(' City', '').replace(' Town', '')
        return name.strip()
    
    def parse_date(self, date_str: str, year: Optional[int] = None) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None
            
        # Try different patterns
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if len(match.groups()) == 4:  # Fri Aug/16 2024
                        day_name, month_str, day, year_str = match.groups()
                        month = self.MONTH_MAP.get(month_str[:3])
                        if month:
                            return datetime(int(year_str), month, int(day))
                    elif len(match.groups()) == 3:  # [Sat 19.8.]
                        day_name, day, month = match.groups()
                        if year:
                            return datetime(year, int(month), int(day))
                except (ValueError, KeyError):
                    continue
        return None
    
    def parse_match_line(self, line: str) -> Optional[Dict]:
        """Parse a single match line"""
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('=') or line.startswith('»'):
            return None
        
        # Try primary pattern
        match = self.MATCH_PATTERN.search(line)
        if match:
            time_str, home_team, away_team, home_goals, away_goals, ht_home, ht_away = match.groups()
            return {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'home_goals': int(home_goals),
                'away_goals': int(away_goals),
                'ht_home_goals': int(ht_home) if ht_home else None,
                'ht_away_goals': int(ht_away) if ht_away else None,
                'time': time_str.strip() if time_str else None
            }
        
        # Try alternative pattern (Italy format)
        match = self.MATCH_PATTERN_ALT.search(line)
        if match:
            time_str, home_team, home_goals, away_goals, ht_home, ht_away, away_team = match.groups()
            return {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'home_goals': int(home_goals),
                'away_goals': int(away_goals),
                'ht_home_goals': int(ht_home) if ht_home else None,
                'ht_away_goals': int(ht_away) if ht_away else None,
                'time': time_str.strip() if time_str else None
            }
        
        return None
    
    def extract_season_from_path(self, file_path: Path) -> Optional[str]:
        """Extract season from file path"""
        # Try to find season in path (e.g., 2024-25, 2023-24)
        parts = file_path.parts
        for part in parts:
            # Match season format YYYY-YY (e.g., 2024-25)
            if re.match(r'^\d{4}-\d{2}$', part):
                return part
            # Match filename format YYYY_XX.txt and extract season
            if re.match(r'^(\d{4})_\w+\.txt$', part):
                year = re.match(r'^(\d{4})_\w+\.txt$', part).group(1)
                return f"{year}-{str(int(year) + 1)[2:]}"
            # Match single year format (e.g., 2024, 2025)
            if re.match(r'^\d{4}$', part) and 2000 <= int(part) <= 2100:
                year = int(part)
                return f"{year}-{str(year + 1)[2:]}"
        return None
    
    def extract_league_code_from_path(self, file_path: Path) -> Optional[str]:
        """Extract league code from file path with comprehensive mapping"""
        file_name = file_path.name.lower()
        parent = file_path.parent.name.lower()
        grandparent = file_path.parent.parent.name.lower() if len(file_path.parts) > 2 else ''
        
        # England
        if 'premierleague' in file_name or '1-premierleague' in file_name:
            return 'E0'
        elif 'championship' in file_name or '2-championship' in file_name:
            return 'E1'
        elif 'league1' in file_name or '3-league1' in file_name:
            return 'E2'
        elif 'league2' in file_name or '4-league2' in file_name:
            return 'E3'
        elif 'nationalleague' in file_name or '5-nationalleague' in file_name:
            return 'E4'
        elif 'facup' in file_name:
            return 'FA'
        elif 'eflcup' in file_name:
            return 'EFL'
        
        # Germany
        elif 'bundesliga' in file_name and '2' not in file_name and '3' not in file_name and 'regionalliga' not in file_name:
            return 'D1'
        elif 'bundesliga2' in file_name or '2-bundesliga' in file_name:
            return 'D2'
        elif 'liga3' in file_name or '3-liga' in file_name:
            return 'D3'
        elif 'cup.txt' in file_name and 'deutschland' in grandparent:
            return 'DFB'
        
        # Italy
        elif 'seriea' in file_name or '1-seriea' in file_name:
            return 'I1'
        elif 'serieb' in file_name or '2-serieb' in file_name:
            return 'I2'
        elif 'seriec' in file_name or '3-seriec' in file_name:
            return 'I3'
        elif 'cup.txt' in file_name and 'italy' in grandparent:
            return 'COI'
        
        # France
        elif 'ligue1' in file_name or 'fr1' in file_name:
            return 'F1'
        elif 'ligue2' in file_name or 'fr2' in file_name:
            return 'F2'
        elif 'frcup' in file_name:
            return 'FC'
        
        # Belgium
        elif 'be1' in file_name:
            return 'B1'
        elif 'becup' in file_name:
            return 'BC'
        
        # Champions League / Europe
        elif 'cl.txt' in file_name or 'clq.txt' in file_name:
            return 'CL'
        elif 'el.txt' in file_name or 'elq.txt' in file_name:
            return 'EL'
        elif 'conf.txt' in file_name or 'confq.txt' in file_name:
            return 'CONF'
        
        # Europe-master countries (by filename pattern)
        elif file_name.endswith('_nl1.txt') or ('nl1' in file_name and 'netherlands' in grandparent):
            return 'N1'
        elif file_name.endswith('_nl2.txt') or ('nl2' in file_name and 'netherlands' in grandparent):
            return 'N2'
        elif file_name.endswith('_pt1.txt') or ('pt1' in file_name and 'portugal' in grandparent):
            return 'P1'
        elif file_name.endswith('_pt2.txt') or ('pt2' in file_name and 'portugal' in grandparent):
            return 'P2'
        elif file_name.endswith('_sco1.txt') or ('sco1' in file_name and 'scotland' in grandparent):
            return 'SC0'
        elif file_name.endswith('_tr1.txt') or ('tr1' in file_name and 'turkey' in grandparent):
            return 'T1'
        elif file_name.endswith('_gr1.txt') or ('gr1' in file_name and 'greece' in grandparent):
            return 'G1'
        elif file_name.endswith('_ru1.txt') or ('ru1' in file_name and 'russia' in grandparent):
            return 'RUS1'
        elif file_name.endswith('_cz1.txt') or ('cz1' in file_name and 'czech' in grandparent):
            return 'CZE1'
        elif file_name.endswith('_cz2.txt') or ('cz2' in file_name and 'czech' in grandparent):
            return 'CZE2'
        elif file_name.endswith('_dk1.txt') or ('dk1' in file_name and 'denmark' in grandparent):
            return 'DK1'
        elif file_name.endswith('_dk2.txt') or ('dk2' in file_name and 'denmark' in grandparent):
            return 'DK2'
        elif file_name.endswith('_pl1.txt') or ('pl1' in file_name and 'poland' in grandparent):
            return 'PL1'
        elif file_name.endswith('_pl2.txt') or ('pl2' in file_name and 'poland' in grandparent):
            return 'PL2'
        elif file_name.endswith('_ro1.txt') or ('ro1' in file_name and 'romania' in grandparent):
            return 'RO1'
        elif file_name.endswith('_hr1.txt') or ('hr1' in file_name and 'croatia' in grandparent):
            return 'CRO1'
        elif file_name.endswith('_hu1.txt') or ('hu1' in file_name and 'hungary' in grandparent):
            return 'HU1'
        elif file_name.endswith('_ua1.txt') or ('ua1' in file_name and 'ukraine' in grandparent):
            return 'UKR1'
        elif file_name.endswith('_rs1.txt') or ('rs1' in file_name and 'serbia' in grandparent):
            return 'SRB1'
        
        # South America
        elif file_name.endswith('_ar1.txt') or ('ar1' in file_name and 'argentina' in grandparent):
            return 'ARG1'
        elif file_name.endswith('_br1.txt') or ('br1' in file_name and 'brazil' in grandparent):
            return 'BRA1'
        elif file_name.endswith('_br2.txt') or ('br2' in file_name and 'brazil' in grandparent):
            return 'BRA2'
        elif file_name.endswith('_co1.txt') or ('co1' in file_name and 'colombia' in grandparent):
            return 'COL1'
        elif 'copal' in file_name or 'copa-libertadores' in grandparent:
            return 'CLIB'
        elif 'copas' in file_name:
            return 'CSUD'
        
        # World-master
        elif file_name.endswith('_mls.txt') or ('mls' in file_name and 'major-league-soccer' in grandparent):
            return 'USA1'
        elif file_name.endswith('_mx1.txt') or ('mx1' in file_name and 'mexico' in grandparent):
            return 'MEX1'
        elif file_name.endswith('_mx2') or ('mx2' in file_name and 'mexico' in grandparent):
            return 'MEX2'
        elif 'concacafcl' in file_name:
            return 'CONCACAF'
        elif file_name.endswith('_cn1.txt') or ('cn1' in file_name and 'china' in grandparent):
            return 'CHN1'
        elif file_name.endswith('_jp1.txt') or ('jp1' in file_name and 'japan' in grandparent):
            return 'JPN1'
        elif file_name.endswith('_au1.txt') or ('au1' in file_name and 'australia' in grandparent):
            return 'AUS1'
        elif file_name.endswith('_eg1.txt') or ('eg1' in file_name and 'egypt' in grandparent):
            return 'EG1'
        elif file_name.endswith('_ma1.txt') or ('ma1' in file_name and 'morocco' in grandparent):
            return 'MA1'
        elif file_name.endswith('_dz1.txt') or ('dz1' in file_name and 'algeria' in grandparent):
            return 'DZ1'
        elif file_name.endswith('_ng1.txt') or ('ng1' in file_name and 'nigeria' in grandparent):
            return 'NG1'
        elif 'cafcl' in file_name:
            return 'CAFCL'
        elif file_name.endswith('_il1.txt') or ('il1' in file_name and 'israel' in grandparent):
            return 'IL1'
        elif file_name.endswith('_sa1.txt') or ('sa1' in file_name and 'saudi' in grandparent):
            return 'SA1'
        elif file_name.endswith('_za1.txt') or ('za1' in file_name and 'south-africa' in grandparent):
            return 'ZA1'
        
        # Try to infer from parent directory structure
        if 'england' in grandparent or 'england' in parent:
            return 'E0'  # Default to Premier League
        elif 'deutschland' in grandparent or 'germany' in grandparent:
            return 'D1'
        elif 'italy' in grandparent or 'italy' in parent:
            return 'I1'
        elif 'france' in grandparent or 'france' in parent:
            return 'F1'
        elif 'belgium' in grandparent or 'belgium' in parent:
            return 'B1'
        elif 'champions-league' in grandparent:
            return 'CL'
        elif 'europe' in grandparent:
            # Try to infer from country folder name
            country_map = {
                'netherlands': 'N1', 'portugal': 'P1', 'spain': 'SP1',
                'scotland': 'SC0', 'turkey': 'T1', 'greece': 'G1',
                'russia': 'RUS1', 'czech-republic': 'CZE1', 'denmark': 'DK1',
                'poland': 'PL1', 'romania': 'RO1', 'croatia': 'CRO1'
            }
            for country, code in country_map.items():
                if country in parent:
                    return code
        elif 'south-america' in grandparent:
            if 'argentina' in parent:
                return 'ARG1'
            elif 'brazil' in parent:
                return 'BRA1'
            elif 'colombia' in parent:
                return 'COL1'
        elif 'world' in grandparent or 'world-master' in grandparent:
            if 'major-league-soccer' in parent or 'north-america' in parent:
                return 'USA1'
            elif 'mexico' in parent:
                return 'MEX1'
            elif 'china' in parent:
                return 'CHN1'
            elif 'japan' in parent:
                return 'JPN1'
            elif 'australia' in parent:
                return 'AUS1'
        
        return None
    
    def parse_file(self, file_path: Path) -> List[Dict]:
        """Parse a single Football.TXT file"""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return matches
        
        # Extract metadata
        season = self.extract_season_from_path(file_path)
        league_code = self.extract_league_code_from_path(file_path)
        
        # Extract year from season for date parsing
        year = None
        if season:
            year_match = re.match(r'(\d{4})', season)
            if year_match:
                year = int(year_match.group(1))
        
        current_date = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#') or line.startswith('='):
                # Check for date in header
                if 'Date' in line and year:
                    date_match = re.search(r'(\w{3})\s+(\w{3})/(\d{1,2})\s+(\d{4})', line)
                    if date_match:
                        month_str = date_match.group(2)
                        month = self.MONTH_MAP.get(month_str[:3])
                        if month:
                            year = int(date_match.group(4))
                continue
            
            # Try to parse date line
            parsed_date = self.parse_date(line, year)
            if parsed_date:
                current_date = parsed_date
                continue
            
            # Try to parse match line
            match_data = self.parse_match_line(line)
            if match_data and current_date:
                match_data['match_date'] = current_date
                match_data['season'] = season
                match_data['league_code'] = league_code
                match_data['source_file'] = str(file_path)
                matches.append(match_data)
        
        return matches


class DataExtractor:
    """Main extraction orchestrator"""
    
    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = FootballTXTParser(self.data_dir)
        
        # Deduplication tracking
        self.seen_matches = set()  # (date, home_team, away_team, league_code)
        
    def find_txt_files(self) -> List[Path]:
        """Find all Football.TXT files"""
        txt_files = []
        for master_dir in self.data_dir.glob('*-master'):
            # Skip leagues-master (metadata only, no match data files)
            if master_dir.name == 'leagues-master':
                logger.debug(f"Skipping {master_dir.name} (metadata only)")
                continue
            for txt_file in master_dir.rglob('*.txt'):
                # Skip README, LICENSE, NOTES files
                if txt_file.name.lower() in ['readme.md', 'license.md', 'notes.md', 'readme.txt', 'license.txt', 'notes.txt']:
                    continue
                # Skip metadata files from leagues-master subdirectories
                if txt_file.name.endswith('.leagues.txt') or txt_file.name.endswith('.seasons.txt'):
                    continue
                txt_files.append(txt_file)
        return sorted(txt_files)
    
    def deduplicate_match(self, match: Dict) -> bool:
        """Check if match is duplicate"""
        key = (
            match['match_date'].date(),
            match['home_team'].lower().strip(),
            match['away_team'].lower().strip(),
            match.get('league_code', '')
        )
        if key in self.seen_matches:
            return False
        self.seen_matches.add(key)
        return True
    
    def extract_all(self) -> Dict[str, int]:
        """Extract all data from Football.TXT files"""
        stats = {
            'files_processed': 0,
            'matches_extracted': 0,
            'matches_duplicated': 0,
            'leagues_found': set(),
            'seasons_found': set()
        }
        
        all_matches = []
        txt_files = self.find_txt_files()
        
        logger.info(f"Found {len(txt_files)} .txt files to process")
        
        for txt_file in txt_files:
            try:
                matches = self.parser.parse_file(txt_file)
                stats['files_processed'] += 1
                
                for match in matches:
                    if self.deduplicate_match(match):
                        all_matches.append(match)
                        stats['matches_extracted'] += 1
                        # Add league code (filter out None)
                        league_code = match.get('league_code') or 'UNKNOWN'
                        if league_code:
                            stats['leagues_found'].add(league_code)
                        # Add season (filter out None)
                        season = match.get('season')
                        if season:
                            stats['seasons_found'].add(season)
                    else:
                        stats['matches_duplicated'] += 1
                
                if stats['files_processed'] % 100 == 0:
                    logger.info(f"Processed {stats['files_processed']} files, extracted {stats['matches_extracted']} matches")
                    
            except Exception as e:
                logger.error(f"Error processing {txt_file}: {e}")
                continue
        
        # Convert sets to lists for JSON serialization (filter out None values)
        stats['leagues_found'] = sorted([x for x in stats['leagues_found'] if x is not None])
        stats['seasons_found'] = sorted([x for x in stats['seasons_found'] if x is not None])
        
        # Write to CSV
        self.write_matches_csv(all_matches)
        
        # Write statistics
        self.write_statistics(stats)
        
        return stats
    
    def write_matches_csv(self, matches: List[Dict]):
        """Write matches to CSV file"""
        csv_path = self.output_dir / 'matches_extracted.csv'
        
        fieldnames = [
            'match_date', 'season', 'league_code',
            'home_team', 'away_team',
            'home_goals', 'away_goals',
            'ht_home_goals', 'ht_away_goals',
            'result', 'is_draw',
            'match_time', 'venue',
            'source_file', 'ingestion_batch_id',
            'matchday', 'round_name'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for match in matches:
                # Calculate result
                home_goals = match['home_goals']
                away_goals = match['away_goals']
                
                if home_goals > away_goals:
                    result = 'H'
                elif home_goals < away_goals:
                    result = 'A'
                else:
                    result = 'D'
                
                row = {
                    'match_date': match['match_date'].strftime('%Y-%m-%d'),
                    'season': match.get('season', ''),
                    'league_code': match.get('league_code', ''),
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'ht_home_goals': match.get('ht_home_goals') or '',
                    'ht_away_goals': match.get('ht_away_goals') or '',
                    'result': result,
                    'is_draw': '1' if result == 'D' else '0',
                    'match_time': match.get('match_time') or '',  # May not be in source
                    'venue': match.get('venue') or '',  # May not be in source
                    'source_file': match.get('source_file', ''),
                    'ingestion_batch_id': match.get('ingestion_batch_id') or '',  # Generated during ingestion
                    'matchday': match.get('matchday') or '',  # May not be in source
                    'round_name': match.get('round_name') or ''  # May not be in source
                }
                writer.writerow(row)
        
        logger.info(f"Written {len(matches)} matches to {csv_path}")
    
    def write_statistics(self, stats: Dict):
        """Write extraction statistics"""
        stats_path = self.output_dir / 'extraction_statistics.json'
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str)
        
        logger.info(f"Extraction statistics written to {stats_path}")
        logger.info(f"Summary: {stats['matches_extracted']} matches from {stats['files_processed']} files")
        logger.info(f"Leagues: {len(stats['leagues_found'])}")
        logger.info(f"Seasons: {len(stats['seasons_found'])}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract Football.TXT data')
    parser.add_argument(
        '--data-dir',
        type=str,
        default='15_Football_Data_',
        help='Base directory containing *-master folders'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='15_Football_Data_/01_extruction_Script/output',
        help='Output directory for extracted CSV files'
    )
    
    args = parser.parse_args()
    
    extractor = DataExtractor(args.data_dir, args.output_dir)
    stats = extractor.extract_all()
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Matches extracted: {stats['matches_extracted']}")
    print(f"Duplicates skipped: {stats['matches_duplicated']}")
    print(f"Leagues found: {len(stats['leagues_found'])}")
    print(f"Seasons found: {len(stats['seasons_found'])}")
    print(f"\nOutput directory: {args.output_dir}")


if __name__ == '__main__':
    main()

