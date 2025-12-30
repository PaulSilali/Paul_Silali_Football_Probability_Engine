"""
Data Cleaning Service for Football Match Data
Implements Phase 1 Critical Cleaning: Drop columns, convert dates, remove invalid rows
"""
import pandas as pd
import numpy as np
import io
import csv
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataCleaningService:
    """
    Production data cleaning service for football match data
    Implements Phase 1 critical cleaning operations
    """
    
    def __init__(
        self,
        missing_threshold: float = 0.5,
        enable_cleaning: bool = True
    ):
        """
        Initialize cleaning service
        
        Args:
            missing_threshold: Percentage threshold for dropping columns (0.0-1.0)
            enable_cleaning: Enable/disable cleaning (for testing/rollback)
        """
        self.missing_threshold = missing_threshold
        self.enable_cleaning = enable_cleaning
        self.cleaning_stats = {
            'columns_dropped': [],
            'rows_before': 0,
            'rows_after': 0,
            'rows_removed': 0,
            'invalid_dates_removed': 0,
            'missing_critical_removed': 0,
            # Phase 2 stats
            'values_imputed': 0,
            'features_created': [],
            'overround_calculated': 0
        }
    
    def clean_csv_content(
        self,
        csv_content: str,
        return_stats: bool = False,
        phase: str = "phase1"  # "phase1", "phase2", or "both"
    ) -> Tuple[str, Optional[Dict]]:
        """
        Clean CSV content string
        
        Args:
            csv_content: Raw CSV content as string
            return_stats: Whether to return cleaning statistics
            phase: Cleaning phase ("phase1", "phase2", or "both")
        
        Returns:
            Tuple of (cleaned_csv_content, stats_dict)
        """
        if not self.enable_cleaning:
            logger.info("Data cleaning disabled, returning original content")
            return csv_content, None
        
        try:
            # Parse CSV to DataFrame
            df = pd.read_csv(io.StringIO(csv_content))
            self.cleaning_stats['rows_before'] = int(len(df))
            
            logger.info(f"Starting data cleaning: {len(df)} rows × {len(df.columns)} columns (phase: {phase})")
            
            # Apply Phase 1 cleaning (always required)
            df_clean = self._phase1_critical_cleaning(df)
            
            # Apply Phase 2 enhancement if requested
            if phase in ["phase2", "both"]:
                df_clean = self._phase2_enhancement(df_clean)
            
            self.cleaning_stats['rows_after'] = int(len(df_clean))
            self.cleaning_stats['rows_removed'] = int(
                self.cleaning_stats['rows_before'] - self.cleaning_stats['rows_after']
            )
            
            # Convert back to CSV string
            output = io.StringIO()
            df_clean.to_csv(output, index=False, lineterminator='\n')
            cleaned_content = output.getvalue()
            
            logger.info(
                f"Cleaning complete: {len(df_clean)} rows × {len(df_clean.columns)} columns "
                f"({self.cleaning_stats['rows_removed']} rows removed, "
                f"{len(self.cleaning_stats['columns_dropped'])} columns dropped)"
            )
            
            if return_stats:
                # Convert all numpy/pandas types to native Python types for JSON serialization
                stats = {}
                for key, value in self.cleaning_stats.items():
                    if isinstance(value, (list, tuple)):
                        stats[key] = list(value)
                    elif hasattr(value, 'item'):  # numpy scalar (int64, float64, etc.)
                        stats[key] = value.item()
                    elif isinstance(value, (int, float)):
                        stats[key] = int(value) if isinstance(value, float) and value.is_integer() else value
                    else:
                        stats[key] = value
            else:
                stats = None
            return cleaned_content, stats
            
        except Exception as e:
            logger.error(f"Error during data cleaning: {e}", exc_info=True)
            # Return original content on error (fail-safe)
            logger.warning("Returning original CSV content due to cleaning error")
            return csv_content, None
    
    def _phase1_critical_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 1: Critical cleaning operations
        
        1. Drop columns with >threshold missing values
        2. Convert Date to datetime and remove invalid dates
        3. Remove rows with missing critical columns
        """
        df_clean = df.copy()
        
        # 1. Drop columns with >threshold missing values
        df_clean = self._drop_high_missing_columns(df_clean)
        
        # 2. Convert Date to datetime and remove invalid dates
        df_clean = self._clean_date_column(df_clean)
        
        # 3. Remove rows with missing critical columns
        df_clean = self._remove_missing_critical(df_clean)
        
        return df_clean
    
    def _drop_high_missing_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop columns with >threshold missing values
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with high-missing columns removed
        """
        missing_pct = df.isnull().sum() / len(df)
        cols_to_drop = missing_pct[missing_pct > self.missing_threshold].index.tolist()
        
        if cols_to_drop:
            self.cleaning_stats['columns_dropped'] = cols_to_drop
            df_clean = df.drop(columns=cols_to_drop)
            
            logger.info(
                f"Dropped {len(cols_to_drop)} columns with >{self.missing_threshold*100:.0f}% missing: "
                f"{', '.join(cols_to_drop[:10])}"
                f"{'...' if len(cols_to_drop) > 10 else ''}"
            )
            return df_clean
        
        return df
    
    def _clean_date_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Date column to datetime and remove invalid dates
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with cleaned Date column
        """
        if 'Date' not in df.columns:
            logger.warning("Date column not found, skipping date cleaning")
            return df
        
        initial_rows = len(df)
        original_date_col = df['Date'].copy()
        
        # Check if Date is already datetime
        if pd.api.types.is_datetime64_any_dtype(original_date_col):
            logger.debug("Date column is already datetime, skipping conversion")
            parsed_dates = original_date_col
        else:
            # Try multiple date formats
            date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
            parsed_dates = None
            
            for date_format in date_formats:
                try:
                    parsed = pd.to_datetime(original_date_col, format=date_format, errors='coerce')
                    if parsed.notna().sum() > 0:
                        parsed_dates = parsed
                        break
                except:
                    continue
            
            # If no format worked, try auto-detection
            if parsed_dates is None or parsed_dates.isna().all():
                parsed_dates = pd.to_datetime(original_date_col, errors='coerce')
        
        df['Date'] = parsed_dates
        
        # Remove rows with invalid dates
        invalid_dates = df['Date'].isna().sum()
        df_clean = df[df['Date'].notna()].copy()
        
        self.cleaning_stats['invalid_dates_removed'] = invalid_dates
        
        if invalid_dates > 0:
            logger.info(f"Removed {invalid_dates} rows with invalid dates")
        
        return df_clean
    
    def _remove_missing_critical(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove rows with missing critical columns
        
        Critical columns: HomeTeam, AwayTeam, FTHG, FTAG
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with rows missing critical data removed
        """
        # Find critical columns (case-insensitive)
        critical_cols = []
        critical_mapping = {
            'HomeTeam': ['HomeTeam', 'home_team', 'Home'],
            'AwayTeam': ['AwayTeam', 'away_team', 'Away'],
            'FTHG': ['FTHG', 'home_goals', 'HomeGoals'],
            'FTAG': ['FTAG', 'away_goals', 'AwayGoals']
        }
        
        for key, possible_names in critical_mapping.items():
            for col in df.columns:
                if col in possible_names or col.lower() == key.lower():
                    critical_cols.append(col)
                    break
        
        if not critical_cols:
            logger.warning("No critical columns found, skipping critical data removal")
            return df
        
        initial_rows = len(df)
        df_clean = df.dropna(subset=critical_cols)
        removed = initial_rows - len(df_clean)
        
        self.cleaning_stats['missing_critical_removed'] = removed
        
        if removed > 0:
            logger.info(
                f"Removed {removed} rows with missing critical columns: "
                f"{', '.join(critical_cols)}"
            )
        
        return df_clean
    
    def _phase2_enhancement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 2: Enhancement cleaning operations
        
        1. Impute medium missing values (10-50%)
        2. Create derived features (TotalGoals, GoalDifference)
        3. Calculate overround from odds
        4. Extract date features (year, month, day of week)
        
        Args:
            df: Input DataFrame (already Phase 1 cleaned)
        
        Returns:
            DataFrame with Phase 2 enhancements applied
        """
        df_clean = df.copy()
        
        # 1. Impute medium missing values (10-50%)
        df_clean = self._impute_medium_missing(df_clean)
        
        # 2. Create derived features
        df_clean = self._create_derived_features(df_clean)
        
        # 3. Calculate overround and implied probabilities
        df_clean = self._calculate_odds_features(df_clean)
        
        # 4. Extract date features
        df_clean = self._extract_date_features(df_clean)
        
        # 5. Create outlier-based features (from outlier investigation analysis)
        df_clean = self._create_outlier_based_features(df_clean)
        
        return df_clean
    
    def _impute_medium_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Impute missing values for columns with 10-50% missing
        
        Uses median for numeric, mode for categorical
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with imputed values
        """
        df_clean = df.copy()
        imputed_count = 0
        
        missing_pct = df_clean.isnull().sum() / len(df_clean)
        medium_missing_cols = missing_pct[
            (missing_pct >= 0.10) & (missing_pct <= 0.50)
        ].index.tolist()
        
        for col in medium_missing_cols:
            if df_clean[col].isnull().sum() == 0:
                continue
            
            missing_before = df_clean[col].isnull().sum()
            
            # Numeric columns: use median
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                median_val = df_clean[col].median()
                if pd.notna(median_val):
                    df_clean[col].fillna(median_val, inplace=True)
                    imputed_count += missing_before
                    logger.debug(f"Imputed {missing_before} missing values in {col} with median: {median_val}")
            
            # Categorical columns: use mode
            else:
                mode_val = df_clean[col].mode()
                if len(mode_val) > 0:
                    df_clean[col].fillna(mode_val[0], inplace=True)
                    imputed_count += int(missing_before)
                    logger.debug(f"Imputed {missing_before} missing values in {col} with mode: {mode_val[0]}")
        
        self.cleaning_stats['values_imputed'] = int(imputed_count)
        
        if imputed_count > 0:
            logger.info(f"Imputed {imputed_count} missing values across {len(medium_missing_cols)} columns")
        
        return df_clean
    
    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create derived features from existing columns
        
        Features:
        - TotalGoals = FTHG + FTAG
        - GoalDifference = FTHG - FTAG
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with derived features added
        """
        df_clean = df.copy()
        features_created = []
        
        # Find goal columns (case-insensitive)
        home_goals_col = None
        away_goals_col = None
        
        for col in df_clean.columns:
            col_lower = col.lower()
            if col_lower in ['fthg', 'home_goals', 'homegoals', 'hg']:
                home_goals_col = col
            elif col_lower in ['ftag', 'away_goals', 'awaygoals', 'ag']:
                away_goals_col = col
        
        if home_goals_col and away_goals_col:
            # TotalGoals
            if 'TotalGoals' not in df_clean.columns:
                df_clean['TotalGoals'] = (
                    pd.to_numeric(df_clean[home_goals_col], errors='coerce') +
                    pd.to_numeric(df_clean[away_goals_col], errors='coerce')
                )
                features_created.append('TotalGoals')
            
            # GoalDifference
            if 'GoalDifference' not in df_clean.columns:
                df_clean['GoalDifference'] = (
                    pd.to_numeric(df_clean[home_goals_col], errors='coerce') -
                    pd.to_numeric(df_clean[away_goals_col], errors='coerce')
                )
                features_created.append('GoalDifference')
        
        self.cleaning_stats['features_created'] = features_created
        
        if features_created:
            logger.info(f"Created derived features: {', '.join(features_created)}")
        
        return df_clean
    
    def _create_outlier_based_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features based on outlier patterns identified in analysis
        
        Features created:
        1. Mismatch indicators:
           - is_extreme_favorite_home (AvgH > 15)
           - is_extreme_favorite_away (AvgA > 30)
           - is_mismatch (either extreme favorite)
        
        2. High-scoring match indicators:
           - is_high_scoring_match (FTHG > 6 or TotalGoals > 7)
           - is_very_high_scoring (FTHG > 8 or TotalGoals > 9)
        
        3. Draw probability categories:
           - draw_prob_category (low: <0.15, medium: 0.15-0.35, high: >0.35)
        
        4. Extreme odds flags:
           - has_extreme_draw_odds (AvgD > 12)
           - has_extreme_home_odds (AvgH > 15)
           - has_extreme_away_odds (AvgA > 30)
        
        5. Team strength indicators:
           - home_team_strength_category (weak: AvgH>10, medium: 2-10, strong: <2)
           - away_team_strength_category (weak: AvgA>20, medium: 3-20, strong: <3)
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with outlier-based features added
        """
        df_clean = df.copy()
        outlier_features_created = []
        
        # Find odds columns (case-insensitive)
        odds_home_col = None
        odds_draw_col = None
        odds_away_col = None
        prob_draw_col = None
        
        for col in df_clean.columns:
            col_lower = col.lower()
            if col_lower in ['avgh', 'odds_home', 'home_odds', 'oh']:
                odds_home_col = col
            elif col_lower in ['avgd', 'odds_draw', 'draw_odds', 'od']:
                odds_draw_col = col
            elif col_lower in ['avga', 'odds_away', 'away_odds', 'oa']:
                odds_away_col = col
            elif col_lower in ['prob_draw_market', 'prob_draw', 'draw_prob']:
                prob_draw_col = col
        
        # Find goal columns
        home_goals_col = None
        away_goals_col = None
        total_goals_col = None
        
        for col in df_clean.columns:
            col_lower = col.lower()
            if col_lower in ['fthg', 'home_goals', 'homegoals', 'hg']:
                home_goals_col = col
            elif col_lower in ['ftag', 'away_goals', 'awaygoals', 'ag']:
                away_goals_col = col
            elif col_lower == 'totalgoals':
                total_goals_col = col
        
        # 1. Mismatch indicators (based on extreme odds)
        if odds_home_col:
            odds_home = pd.to_numeric(df_clean[odds_home_col], errors='coerce')
            if 'is_extreme_favorite_home' not in df_clean.columns:
                df_clean['is_extreme_favorite_home'] = (odds_home > 15).astype(int)
                outlier_features_created.append('is_extreme_favorite_home')
        
        if odds_away_col:
            odds_away = pd.to_numeric(df_clean[odds_away_col], errors='coerce')
            if 'is_extreme_favorite_away' not in df_clean.columns:
                df_clean['is_extreme_favorite_away'] = (odds_away > 30).astype(int)
                outlier_features_created.append('is_extreme_favorite_away')
        
        if 'is_extreme_favorite_home' in df_clean.columns or 'is_extreme_favorite_away' in df_clean.columns:
            if 'is_mismatch' not in df_clean.columns:
                is_extreme_home = df_clean.get('is_extreme_favorite_home', pd.Series(0, index=df_clean.index))
                is_extreme_away = df_clean.get('is_extreme_favorite_away', pd.Series(0, index=df_clean.index))
                df_clean['is_mismatch'] = ((is_extreme_home == 1) | (is_extreme_away == 1)).astype(int)
                outlier_features_created.append('is_mismatch')
        
        # 2. High-scoring match indicators
        if home_goals_col:
            home_goals = pd.to_numeric(df_clean[home_goals_col], errors='coerce')
            
            if 'is_high_scoring_match' not in df_clean.columns:
                # Check if TotalGoals exists, otherwise calculate it
                if total_goals_col:
                    total_goals = pd.to_numeric(df_clean[total_goals_col], errors='coerce')
                elif away_goals_col:
                    away_goals = pd.to_numeric(df_clean[away_goals_col], errors='coerce')
                    total_goals = home_goals + away_goals
                else:
                    total_goals = pd.Series(0, index=df_clean.index)
                
                # High scoring: FTHG > 6 OR TotalGoals > 7
                df_clean['is_high_scoring_match'] = (
                    (home_goals > 6) | (total_goals > 7)
                ).astype(int)
                outlier_features_created.append('is_high_scoring_match')
            
            if 'is_very_high_scoring' not in df_clean.columns:
                if total_goals_col:
                    total_goals = pd.to_numeric(df_clean[total_goals_col], errors='coerce')
                elif away_goals_col:
                    away_goals = pd.to_numeric(df_clean[away_goals_col], errors='coerce')
                    total_goals = home_goals + away_goals
                else:
                    total_goals = pd.Series(0, index=df_clean.index)
                
                # Very high scoring: FTHG > 8 OR TotalGoals > 9
                df_clean['is_very_high_scoring'] = (
                    (home_goals > 8) | (total_goals > 9)
                ).astype(int)
                outlier_features_created.append('is_very_high_scoring')
        
        # 3. Draw probability categories
        if prob_draw_col:
            prob_draw = pd.to_numeric(df_clean[prob_draw_col], errors='coerce')
            if 'draw_prob_category' not in df_clean.columns:
                df_clean['draw_prob_category'] = pd.cut(
                    prob_draw,
                    bins=[-np.inf, 0.15, 0.35, np.inf],
                    labels=['low', 'medium', 'high'],
                    include_lowest=True
                ).astype(str)
                # Replace NaN with 'unknown'
                df_clean['draw_prob_category'] = df_clean['draw_prob_category'].replace('nan', 'unknown')
                outlier_features_created.append('draw_prob_category')
        
        # 4. Extreme odds flags
        if odds_draw_col:
            odds_draw = pd.to_numeric(df_clean[odds_draw_col], errors='coerce')
            if 'has_extreme_draw_odds' not in df_clean.columns:
                df_clean['has_extreme_draw_odds'] = (odds_draw > 12).astype(int)
                outlier_features_created.append('has_extreme_draw_odds')
        
        if odds_home_col:
            odds_home = pd.to_numeric(df_clean[odds_home_col], errors='coerce')
            if 'has_extreme_home_odds' not in df_clean.columns:
                df_clean['has_extreme_home_odds'] = (odds_home > 15).astype(int)
                outlier_features_created.append('has_extreme_home_odds')
        
        if odds_away_col:
            odds_away = pd.to_numeric(df_clean[odds_away_col], errors='coerce')
            if 'has_extreme_away_odds' not in df_clean.columns:
                df_clean['has_extreme_away_odds'] = (odds_away > 30).astype(int)
                outlier_features_created.append('has_extreme_away_odds')
        
        # 5. Team strength categories
        if odds_home_col:
            odds_home = pd.to_numeric(df_clean[odds_home_col], errors='coerce')
            if 'home_team_strength_category' not in df_clean.columns:
                df_clean['home_team_strength_category'] = pd.cut(
                    odds_home,
                    bins=[-np.inf, 2.0, 10.0, np.inf],
                    labels=['strong', 'medium', 'weak'],
                    include_lowest=True
                ).astype(str)
                df_clean['home_team_strength_category'] = df_clean['home_team_strength_category'].replace('nan', 'unknown')
                outlier_features_created.append('home_team_strength_category')
        
        if odds_away_col:
            odds_away = pd.to_numeric(df_clean[odds_away_col], errors='coerce')
            if 'away_team_strength_category' not in df_clean.columns:
                df_clean['away_team_strength_category'] = pd.cut(
                    odds_away,
                    bins=[-np.inf, 3.0, 20.0, np.inf],
                    labels=['strong', 'medium', 'weak'],
                    include_lowest=True
                ).astype(str)
                df_clean['away_team_strength_category'] = df_clean['away_team_strength_category'].replace('nan', 'unknown')
                outlier_features_created.append('away_team_strength_category')
        
        # Update features_created list
        if outlier_features_created:
            existing_features = self.cleaning_stats.get('features_created', [])
            self.cleaning_stats['features_created'] = existing_features + outlier_features_created
            logger.info(f"Created outlier-based features: {', '.join(outlier_features_created)}")
        
        return df_clean
    
    def _calculate_odds_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate odds-related features
        
        Features:
        - Overround = sum(1/odds) - 1
        - Implied probabilities (if not already present)
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with odds features added
        """
        df_clean = df.copy()
        
        # Find odds columns
        odds_home_col = None
        odds_draw_col = None
        odds_away_col = None
        
        for col in df_clean.columns:
            col_lower = col.lower()
            if col_lower in ['avgh', 'odds_home', 'home_odds', 'oh']:
                odds_home_col = col
            elif col_lower in ['avgd', 'odds_draw', 'draw_odds', 'od']:
                odds_draw_col = col
            elif col_lower in ['avga', 'odds_away', 'away_odds', 'oa']:
                odds_away_col = col
        
        if odds_home_col and odds_draw_col and odds_away_col:
            # Convert to numeric
            odds_home = pd.to_numeric(df_clean[odds_home_col], errors='coerce')
            odds_draw = pd.to_numeric(df_clean[odds_draw_col], errors='coerce')
            odds_away = pd.to_numeric(df_clean[odds_away_col], errors='coerce')
            
            # Calculate overround
            valid_odds = (
                odds_home.notna() & 
                odds_draw.notna() & 
                odds_away.notna() &
                (odds_home > 0) & 
                (odds_draw > 0) & 
                (odds_away > 0)
            )
            
            if 'Overround' not in df_clean.columns:
                overround = np.where(
                    valid_odds,
                    (1/odds_home + 1/odds_draw + 1/odds_away) - 1,
                    np.nan
                )
                df_clean['Overround'] = overround
                self.cleaning_stats['overround_calculated'] = valid_odds.sum()
                logger.info(f"Calculated overround for {valid_odds.sum()} matches")
            
            # Calculate implied probabilities if not present
            prob_cols = ['prob_home_market', 'prob_draw_market', 'prob_away_market']
            if not all(col in df_clean.columns for col in prob_cols):
                total_implied = 1/odds_home + 1/odds_draw + 1/odds_away
                
                if 'prob_home_market' not in df_clean.columns:
                    df_clean['prob_home_market'] = np.where(
                        valid_odds & (total_implied > 0),
                        (1/odds_home) / total_implied,
                        np.nan
                    )
                
                if 'prob_draw_market' not in df_clean.columns:
                    df_clean['prob_draw_market'] = np.where(
                        valid_odds & (total_implied > 0),
                        (1/odds_draw) / total_implied,
                        np.nan
                    )
                
                if 'prob_away_market' not in df_clean.columns:
                    df_clean['prob_away_market'] = np.where(
                        valid_odds & (total_implied > 0),
                        (1/odds_away) / total_implied,
                        np.nan
                    )
                
                logger.info("Calculated implied probabilities from odds")
        
        return df_clean
    
    def _extract_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract date features from Date column
        
        Features:
        - Year
        - Month
        - DayOfWeek (0=Monday, 6=Sunday)
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with date features added
        """
        df_clean = df.copy()
        
        if 'Date' not in df_clean.columns:
            logger.warning("Date column not found, skipping date feature extraction")
            return df_clean
        
        # Ensure Date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_clean['Date']):
            df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')
        
        valid_dates = df_clean['Date'].notna()
        
        if valid_dates.sum() > 0:
            # Year
            if 'Year' not in df_clean.columns:
                df_clean['Year'] = np.where(
                    valid_dates,
                    df_clean['Date'].dt.year,
                    np.nan
                )
            
            # Month
            if 'Month' not in df_clean.columns:
                df_clean['Month'] = np.where(
                    valid_dates,
                    df_clean['Date'].dt.month,
                    np.nan
                )
            
            # DayOfWeek (0=Monday, 6=Sunday)
            if 'DayOfWeek' not in df_clean.columns:
                df_clean['DayOfWeek'] = np.where(
                    valid_dates,
                    df_clean['Date'].dt.dayofweek,
                    np.nan
                )
            
            logger.info(f"Extracted date features (Year, Month, DayOfWeek) for {valid_dates.sum()} matches")
        
        return df_clean
    
    def get_cleaning_stats(self) -> Dict:
        """
        Get cleaning statistics
        
        Returns:
            Dictionary with cleaning statistics
        """
        return self.cleaning_stats.copy()


def clean_csv_content(
    csv_content: str,
    missing_threshold: float = 0.5,
    enable_cleaning: bool = True
) -> Tuple[str, Optional[Dict]]:
    """
    Convenience function for cleaning CSV content
    
    Args:
        csv_content: Raw CSV content as string
        missing_threshold: Percentage threshold for dropping columns
        enable_cleaning: Enable/disable cleaning
    
    Returns:
        Tuple of (cleaned_csv_content, stats_dict)
    """
    cleaner = DataCleaningService(
        missing_threshold=missing_threshold,
        enable_cleaning=enable_cleaning
    )
    return cleaner.clean_csv_content(csv_content, return_stats=True)

