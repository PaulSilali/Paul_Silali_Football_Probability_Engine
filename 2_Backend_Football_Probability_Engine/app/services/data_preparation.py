"""
Data Preparation Service for Model Training
Combines cleaned data per league and exports to CSV/Parquet for training
"""
import pandas as pd
import numpy as np
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False
    logger.warning("pyarrow not installed. Parquet export disabled. Install with: pip install pyarrow")


class DataPreparationService:
    """
    Service for preparing cleaned data for model training
    - Combines all seasons per league
    - Exports to CSV and Parquet formats
    - Optimized for training workflows
    """
    
    def __init__(self, db: Session, output_dir: Optional[Path] = None):
        """
        Initialize data preparation service
        
        Args:
            db: Database session
            output_dir: Output directory for cleaned files (default: data/2_Cleaned_data)
        """
        self.db = db
        
        if output_dir is None:
            backend_root = Path(__file__).parent.parent.parent
            output_dir = backend_root / "data" / "2_Cleaned_data"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_league_data(
        self,
        league_code: str,
        format: str = "both",  # "csv", "parquet", or "both"
        apply_cleaning: bool = True
    ) -> Dict[str, any]:
        """
        Prepare cleaned data for a specific league
        
        Combines all seasons into one file per league
        
        Args:
            league_code: League code (e.g., 'E0')
            format: Output format ("csv", "parquet", or "both")
            apply_cleaning: Apply Phase 1 cleaning if loading from files
        
        Returns:
            Dictionary with file paths and statistics
        """
        from app.db.models import League, Match
        
        # Get league
        league = self.db.query(League).filter(League.code == league_code).first()
        if not league:
            raise ValueError(f"League not found: {league_code}")
        
        logger.info(f"Preparing data for league: {league.name} ({league_code})")
        
        # Load all matches for this league from database
        matches = self.db.query(Match).filter(
            Match.league_id == league.id
        ).order_by(Match.match_date.asc()).all()
        
        if not matches:
            logger.warning(f"No matches found in database for league {league_code}, trying to load from CSV files...")
            # Try loading from batch CSV files
            df = self._load_from_batch_csv_files(league_code, league.name)
            if df is None or len(df) == 0:
                logger.warning(f"No matches found for league {league_code}")
                return {
                    "league_code": league_code,
                    "league_name": league.name,
                    "matches_count": 0,
                    "files_created": []
                }
        else:
            # Convert to DataFrame
            df = self._matches_to_dataframe(matches, league_code)
        
        # Apply cleaning if requested
        if apply_cleaning:
            from app.services.data_cleaning import DataCleaningService
            from app.config import settings
            cleaner = DataCleaningService(missing_threshold=0.5, enable_cleaning=True)
            # Use Phase 2 cleaning (includes Phase 1 + outlier-based features)
            cleaning_phase = getattr(settings, 'DATA_CLEANING_PHASE', 'phase2')
            logger.info(f"Applying data cleaning with phase: {cleaning_phase}")
            df, _ = cleaner.clean_csv_content(
                df.to_csv(index=False),
                return_stats=False,
                phase=cleaning_phase  # Use phase2 to include all features
            )
            # Re-parse cleaned CSV
            df = pd.read_csv(io.StringIO(df))
        
        # Prepare filename
        league_name_safe = league.name.replace(' ', '_').replace('/', '_')
        league_name_safe = ''.join(c for c in league_name_safe if c.isalnum() or c in ('_', '-'))
        base_filename = f"{league_code}_{league_name_safe}_all_seasons"
        
        files_created = []
        
        # Determine date column name (could be 'Date' from CSV or 'match_date' from DB)
        date_col = 'Date' if 'Date' in df.columns else ('match_date' if 'match_date' in df.columns else None)
        
        # Ensure date column is datetime for isoformat()
        date_start = None
        date_end = None
        if date_col and date_col in df.columns and len(df) > 0:
            try:
                # Convert to datetime if it's not already
                if df[date_col].dtype == 'object' or (len(df) > 0 and isinstance(df[date_col].iloc[0], str)):
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # Get min/max after filtering out NaT values
                valid_dates = df[date_col].dropna()
                if len(valid_dates) > 0:
                    date_start = valid_dates.min()
                    date_end = valid_dates.max()
                    # Convert to ISO format if it's a datetime object
                    if hasattr(date_start, 'isoformat'):
                        date_start = date_start.isoformat()
                    if hasattr(date_end, 'isoformat'):
                        date_end = date_end.isoformat()
            except Exception as e:
                logger.warning(f"Error processing date range for {league_code}: {e}")
        
        stats = {
            "league_code": league_code,
            "league_name": league.name,
            "matches_count": len(df),
            "seasons": sorted(df['season'].unique().tolist()) if 'season' in df.columns else [],
            "date_range": {
                "start": date_start,
                "end": date_end
            },
            "files_created": files_created
        }
        
        # Export to CSV
        if format in ["csv", "both"]:
            csv_path = self.output_dir / f"{base_filename}.csv"
            df.to_csv(csv_path, index=False)
            files_created.append(str(csv_path))
            logger.info(f"Exported CSV: {csv_path} ({len(df)} rows)")
        
        # Export to Parquet
        if format in ["parquet", "both"] and HAS_PARQUET:
            parquet_path = self.output_dir / f"{base_filename}.parquet"
            df.to_parquet(parquet_path, index=False, compression='snappy')
            files_created.append(str(parquet_path))
            
            # Get file sizes
            csv_size = csv_path.stat().st_size if format in ["csv", "both"] else 0
            parquet_size = parquet_path.stat().st_size
            
            logger.info(
                f"Exported Parquet: {parquet_path} ({len(df)} rows, "
                f"CSV: {csv_size/1024/1024:.2f}MB, Parquet: {parquet_size/1024/1024:.2f}MB, "
                f"Compression: {(1 - parquet_size/csv_size)*100:.1f}%"
            )
        
        stats["files_created"] = files_created
        return stats
    
    def prepare_all_leagues(
        self,
        format: str = "both",
        apply_cleaning: bool = True
    ) -> Dict[str, any]:
        """
        Prepare cleaned data for all leagues
        
        Args:
            format: Output format ("csv", "parquet", or "both")
            apply_cleaning: Apply Phase 1 cleaning
        
        Returns:
            Summary statistics
        """
        from app.db.models import League
        
        leagues = self.db.query(League).all()
        
        results = []
        total_matches = 0
        
        for league in leagues:
            try:
                stats = self.prepare_league_data(
                    league.code,
                    format=format,
                    apply_cleaning=apply_cleaning
                )
                results.append(stats)
                total_matches += stats["matches_count"]
            except Exception as e:
                logger.error(f"Error preparing data for {league.code}: {e}", exc_info=True)
                results.append({
                    "league_code": league.code,
                    "league_name": league.name,
                    "error": str(e)
                })
        
        return {
            "total_leagues": len(leagues),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "total_matches": total_matches,
            "leagues": results,
            "output_directory": str(self.output_dir)
        }
    
    def _matches_to_dataframe(self, matches: List, league_code: str) -> pd.DataFrame:
        """
        Convert Match objects to DataFrame
        
        Args:
            matches: List of Match objects
            league_code: League code for reference
        
        Returns:
            DataFrame with match data
        """
        data = []
        for match in matches:
            data.append({
                'Date': match.match_date.isoformat() if match.match_date else None,
                'Div': league_code,
                'HomeTeam': match.home_team.name if match.home_team else None,
                'AwayTeam': match.away_team.name if match.away_team else None,
                'FTHG': match.home_goals,
                'FTAG': match.away_goals,
                'FTR': match.result.value if match.result else None,
                'AvgH': match.odds_home,
                'AvgD': match.odds_draw,
                'AvgA': match.odds_away,
                'season': match.season,
                'league_id': match.league_id,
                'home_team_id': match.home_team_id,
                'away_team_id': match.away_team_id,
                'prob_home_market': match.prob_home_market,
                'prob_draw_market': match.prob_draw_market,
                'prob_away_market': match.prob_away_market,
            })
        
        df = pd.DataFrame(data)
        
        # Convert Date to datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        return df
    
    def load_training_data(
        self,
        league_codes: Optional[List[str]] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        min_matches_per_team: int = 10,
        source: str = "database"  # "database" or "file"
    ) -> pd.DataFrame:
        """
        Load training data for model training
        
        Args:
            league_codes: List of league codes (None = all leagues)
            min_date: Minimum match date
            max_date: Maximum match date
            min_matches_per_team: Minimum matches required per team
            source: "database" (recommended) or "file" (from 2_Cleaned_data)
        
        Returns:
            DataFrame ready for model training
        """
        if source == "database":
            return self._load_from_database(
                league_codes, min_date, max_date, min_matches_per_team
            )
        else:
            return self._load_from_files(
                league_codes, min_date, max_date, min_matches_per_team
            )
    
    def _load_from_database(
        self,
        league_codes: Optional[List[str]],
        min_date: Optional[datetime],
        max_date: Optional[datetime],
        min_matches_per_team: int
    ) -> pd.DataFrame:
        """
        Load training data from database (RECOMMENDED - fastest)
        
        Database is optimized with indexes for fast queries
        """
        from app.db.models import League, Match
        
        query = self.db.query(Match)
        
        # Filter by leagues
        if league_codes:
            leagues = self.db.query(League).filter(League.code.in_(league_codes)).all()
            league_ids = [l.id for l in leagues]
            query = query.filter(Match.league_id.in_(league_ids))
        
        # Filter by date range
        if min_date:
            query = query.filter(Match.match_date >= min_date.date())
        if max_date:
            query = query.filter(Match.match_date <= max_date.date())
        
        # Load matches
        matches = query.order_by(Match.match_date.asc()).all()
        
        logger.info(f"Loaded {len(matches)} matches from database")
        
        # Convert to DataFrame
        df = self._matches_to_dataframe(matches, "ALL")
        
        # Filter teams with minimum matches
        if min_matches_per_team > 0:
            home_counts = df['home_team_id'].value_counts()
            away_counts = df['away_team_id'].value_counts()
            team_counts = (home_counts + away_counts).fillna(0)
            
            valid_teams = team_counts[team_counts >= min_matches_per_team].index.tolist()
            df = df[
                df['home_team_id'].isin(valid_teams) &
                df['away_team_id'].isin(valid_teams)
            ]
            
            logger.info(
                f"Filtered to {len(df)} matches with teams having >= {min_matches_per_team} matches"
            )
        
        return df
    
    def _load_from_files(
        self,
        league_codes: Optional[List[str]],
        min_date: Optional[datetime],
        max_date: Optional[datetime],
        min_matches_per_team: int
    ) -> pd.DataFrame:
        """
        Load training data from cleaned files
        
        Useful for offline training or when database is unavailable
        """
        dfs = []
        
        # Find all league files
        if league_codes:
            files = []
            for code in league_codes:
                csv_file = self.output_dir / f"{code}_*.csv"
                parquet_file = self.output_dir / f"{code}_*.parquet"
                files.extend(list(self.output_dir.glob(f"{code}_*.csv")))
                files.extend(list(self.output_dir.glob(f"{code}_*.parquet")))
        else:
            files = list(self.output_dir.glob("*_all_seasons.csv")) + \
                   list(self.output_dir.glob("*_all_seasons.parquet"))
        
        for file_path in files:
            try:
                if file_path.suffix == '.parquet' and HAS_PARQUET:
                    df = pd.read_parquet(file_path)
                else:
                    df = pd.read_csv(file_path)
                
                # Convert Date to datetime
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                
                # Filter by date range
                if min_date and 'Date' in df.columns:
                    df = df[df['Date'] >= min_date]
                if max_date and 'Date' in df.columns:
                    df = df[df['Date'] <= max_date]
                
                dfs.append(df)
                logger.info(f"Loaded {len(df)} matches from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        if not dfs:
            raise ValueError("No data files found")
        
        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter teams with minimum matches
        if min_matches_per_team > 0:
            home_counts = combined_df['home_team_id'].value_counts()
            away_counts = combined_df['away_team_id'].value_counts()
            team_counts = (home_counts + away_counts).fillna(0)
            
            valid_teams = team_counts[team_counts >= min_matches_per_team].index.tolist()
            combined_df = combined_df[
                combined_df['home_team_id'].isin(valid_teams) &
                combined_df['away_team_id'].isin(valid_teams)
            ]
        
        logger.info(f"Combined {len(combined_df)} total matches from {len(dfs)} files")
        return combined_df
    
    def _load_from_batch_csv_files(self, league_code: str, league_name: str) -> Optional[pd.DataFrame]:
        """
        Load data from batch CSV files in data/1_data_ingestion/batch_* folders
        
        Args:
            league_code: League code (e.g., "E0")
            league_name: League name (e.g., "Premier League")
        
        Returns:
            DataFrame with all matches from CSV files, or None if no files found
        """
        import glob
        from pathlib import Path
        
        # Find batch folders matching the league
        batch_dir = Path("data/1_data_ingestion")
        if not batch_dir.exists():
            logger.warning(f"Batch directory {batch_dir} does not exist")
            return None
        
        # Find all batch folders that contain this league's CSV files
        # Pattern: batch_*_{league_name}/
        league_name_safe = league_name.replace(' ', '_').replace('/', '_')
        league_name_safe = ''.join(c for c in league_name_safe if c.isalnum() or c in ('_', '-'))
        
        # Try to find batch folders
        batch_folders = []
        for folder in batch_dir.iterdir():
            if folder.is_dir() and folder.name.startswith("batch_") and league_name_safe in folder.name:
                batch_folders.append(folder)
        
        # Also search for CSV files with the league code pattern
        csv_files = []
        for folder in batch_dir.iterdir():
            if folder.is_dir() and folder.name.startswith("batch_"):
                # Look for CSV files matching league code
                pattern = f"{league_code}_*.csv"
                found_files = list(folder.glob(pattern))
                csv_files.extend(found_files)
        
        if not csv_files:
            logger.warning(f"No CSV files found for league {league_code} in batch folders")
            return None
        
        # Load all CSV files
        dfs = []
        for csv_file in csv_files:
            try:
                # Try pandas read_csv with error handling for malformed files
                try:
                    # pandas >= 2.0
                    df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='utf-8')
                except TypeError:
                    # pandas < 2.0
                    try:
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='utf-8')
                    except Exception:
                        # Try with latin-1 encoding
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='latin-1')
            except Exception as e1:
                # Try with different encoding
                try:
                    try:
                        df = pd.read_csv(csv_file, on_bad_lines='skip', encoding='latin-1')
                    except TypeError:
                        df = pd.read_csv(csv_file, error_bad_lines=False, warn_bad_lines=False, encoding='latin-1')
                except Exception as e2:
                    logger.error(f"Error loading {csv_file}: {e1} and {e2}")
                    continue  # Skip this file and continue with next
                
                # Extract season from filename (e.g., E0_1920.csv -> 1920)
                season = csv_file.stem.split('_')[-1] if '_' in csv_file.stem else None
                
                # Keep original column names (Date, HomeTeam, AwayTeam, etc.) to match _matches_to_dataframe format
                # Add season column
                if season:
                    df['season'] = season
                
                # Parse date - keep original 'Date' column name
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
                
                # Filter out invalid dates
                df = df[df['Date'].notna()]
                
                # Filter out rows with missing critical data (using original column names)
                df = df[df['HomeTeam'].notna() & df['AwayTeam'].notna()]
                df = df[df['FTHG'].notna() & df['FTAG'].notna()]
                
                if len(df) > 0:
                    dfs.append(df)
                    logger.info(f"Loaded {len(df)} matches from {csv_file.name}")
            except Exception as e:
                logger.error(f"Error loading {csv_file}: {e}", exc_info=True)
                continue
        
        if not dfs:
            logger.warning(f"No valid data loaded from CSV files for league {league_code}")
            return None
        
        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by date (using original 'Date' column name)
        if 'Date' in combined_df.columns:
            combined_df = combined_df.sort_values('Date')
        
        logger.info(f"Loaded {len(combined_df)} total matches from {len(dfs)} CSV files for league {league_code}")
        return combined_df


def prepare_training_data(
    db: Session,
    league_codes: Optional[List[str]] = None,
    output_format: str = "both"
) -> Dict:
    """
    Convenience function to prepare training data
    
    Args:
        db: Database session
        league_codes: List of league codes (None = all)
        output_format: "csv", "parquet", or "both"
    
    Returns:
        Preparation statistics
    """
    service = DataPreparationService(db)
    
    if league_codes:
        results = []
        for code in league_codes:
            results.append(service.prepare_league_data(code, format=output_format))
        return {"leagues": results}
    else:
        return service.prepare_all_leagues(format=output_format)

