"""
Football Data Cleaning Pipeline
Implements recommendations from DATA_QUALITY_DEEP_ANALYSIS.md
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict
import warnings

warnings.filterwarnings('ignore')


class FootballDataCleaner:
    """
    Comprehensive cleaning pipeline for football match data
    """
    
    def __init__(self, missing_threshold: float = 0.5):
        """
        Initialize cleaner
        
        Args:
            missing_threshold: Percentage threshold for dropping columns (default: 0.5 = 50%)
        """
        self.missing_threshold = missing_threshold
        self.columns_dropped = []
        self.rows_removed = 0
        self.stats = {}
    
    def clean(self, df: pd.DataFrame, phase: str = "full") -> pd.DataFrame:
        """
        Main cleaning pipeline
        
        Args:
            df: Input DataFrame
            phase: "critical" (Phase 1) or "full" (Phase 1 + 2)
        
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        
        print("=" * 80)
        print("FOOTBALL DATA CLEANING PIPELINE")
        print("=" * 80)
        print(f"\nInitial shape: {df_clean.shape[0]:,} rows × {df_clean.shape[1]} columns")
        
        # Phase 1: Critical Cleaning
        df_clean = self._phase1_critical_cleaning(df_clean)
        
        # Phase 2: Enhancement (if requested)
        if phase == "full":
            df_clean = self._phase2_enhancement(df_clean)
        
        print("\n" + "=" * 80)
        print("CLEANING COMPLETE")
        print("=" * 80)
        print(f"\nFinal shape: {df_clean.shape[0]:,} rows × {df_clean.shape[1]} columns")
        print(f"Columns dropped: {len(self.columns_dropped)}")
        print(f"Rows removed: {self.rows_removed:,}")
        print(f"Data retention: {(len(df_clean) / len(df) * 100):.2f}%")
        
        return df_clean
    
    def _phase1_critical_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 1: Critical cleaning operations
        - Drop columns with >50% missing
        - Convert Date to datetime
        - Remove invalid dates
        - Remove rows with missing critical columns
        """
        print("\n" + "-" * 80)
        print("PHASE 1: CRITICAL CLEANING")
        print("-" * 80)
        
        # 1. Drop columns with >threshold missing values
        print("\n1. Dropping columns with >50% missing values...")
        missing_pct = df.isnull().sum() / len(df)
        cols_to_drop = missing_pct[missing_pct > self.missing_threshold].index.tolist()
        
        if cols_to_drop:
            self.columns_dropped = cols_to_drop
            df = df.drop(columns=cols_to_drop)
            print(f"   ✓ Dropped {len(cols_to_drop)} columns:")
            for col in cols_to_drop[:10]:  # Show first 10
                print(f"     - {col} ({missing_pct[col]:.1f}% missing)")
            if len(cols_to_drop) > 10:
                print(f"     ... and {len(cols_to_drop) - 10} more")
        else:
            print("   ✓ No columns to drop")
        
        # 2. Convert Date to datetime
        print("\n2. Converting Date column to datetime...")
        if 'Date' in df.columns:
            initial_rows = len(df)
            df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
            invalid_dates = df['Date'].isna().sum()
            df = df[df['Date'].notna()]
            removed = initial_rows - len(df)
            self.rows_removed += removed
            print(f"   ✓ Converted Date to datetime")
            if removed > 0:
                print(f"   ✓ Removed {removed:,} rows with invalid dates")
        else:
            print("   ⚠️  Date column not found")
        
        # 3. Remove rows with missing critical columns
        print("\n3. Removing rows with missing critical columns...")
        critical_cols = []
        for col in ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']:
            if col in df.columns:
                critical_cols.append(col)
        
        if critical_cols:
            initial_rows = len(df)
            df = df.dropna(subset=critical_cols)
            removed = initial_rows - len(df)
            self.rows_removed += removed
            print(f"   ✓ Checked critical columns: {', '.join(critical_cols)}")
            if removed > 0:
                print(f"   ✓ Removed {removed:,} rows with missing critical data")
        else:
            print("   ⚠️  Critical columns not found")
        
        # 4. Validate data ranges
        print("\n4. Validating data ranges...")
        issues = []
        
        if 'FTHG' in df.columns:
            invalid_goals_h = df[(df['FTHG'] < 0) | (df['FTHG'] > 20)]
            if len(invalid_goals_h) > 0:
                issues.append(f"FTHG: {len(invalid_goals_h)} invalid values")
        
        if 'FTAG' in df.columns:
            invalid_goals_a = df[(df['FTAG'] < 0) | (df['FTAG'] > 20)]
            if len(invalid_goals_a) > 0:
                issues.append(f"FTAG: {len(invalid_goals_a)} invalid values")
        
        if 'B365H' in df.columns:
            invalid_odds = df[(df['B365H'] < 1.0) | (df['B365H'] > 100.0)]
            if len(invalid_odds) > 0:
                issues.append(f"B365H: {len(invalid_odds)} invalid odds")
        
        if issues:
            print(f"   ⚠️  Found issues: {', '.join(issues)}")
        else:
            print("   ✓ All values within valid ranges")
        
        return df
    
    def _phase2_enhancement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 2: Data enhancement
        - Impute medium missing values
        - Create derived features
        - Calculate probabilities
        """
        print("\n" + "-" * 80)
        print("PHASE 2: DATA ENHANCEMENT")
        print("-" * 80)
        
        # 1. Impute medium missing values (10-50%)
        print("\n1. Imputing medium missing values...")
        missing_pct = df.isnull().sum() / len(df)
        medium_missing = missing_pct[(missing_pct > 0.1) & (missing_pct <= 0.5)].index.tolist()
        
        imputed_count = 0
        for col in medium_missing:
            if df[col].dtype in ['int64', 'float64']:
                # Numeric: impute with median
                median_val = df[col].median()
                if pd.notna(median_val):
                    df[col] = df[col].fillna(median_val)
                    imputed_count += 1
            elif df[col].dtype == 'object':
                # Categorical: impute with mode
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val[0])
                    imputed_count += 1
        
        if imputed_count > 0:
            print(f"   ✓ Imputed {imputed_count} columns")
        else:
            print("   ✓ No columns needed imputation")
        
        # 2. Create derived features
        print("\n2. Creating derived features...")
        features_created = []
        
        # Total goals
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            df['TotalGoals'] = df['FTHG'] + df['FTAG']
            features_created.append('TotalGoals')
        
        # Goal difference
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            df['GoalDifference'] = df['FTHG'] - df['FTAG']
            features_created.append('GoalDifference')
        
        # Match result
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            df['Result'] = df.apply(
                lambda row: 'H' if row['FTHG'] > row['FTAG'] 
                else 'A' if row['FTHG'] < row['FTAG'] else 'D', 
                axis=1
            )
            features_created.append('Result')
        
        # Implied probabilities from odds
        if all(col in df.columns for col in ['B365H', 'B365D', 'B365A']):
            df['ImpliedProbHome'] = 1 / df['B365H']
            df['ImpliedProbDraw'] = 1 / df['B365D']
            df['ImpliedProbAway'] = 1 / df['B365A']
            df['Overround'] = (df['ImpliedProbHome'] + 
                             df['ImpliedProbDraw'] + 
                             df['ImpliedProbAway']) - 1.0
            features_created.extend(['ImpliedProbHome', 'ImpliedProbDraw', 
                                   'ImpliedProbAway', 'Overround'])
        
        # Date features
        if 'Date' in df.columns and df['Date'].dtype == 'datetime64[ns]':
            df['Year'] = df['Date'].dt.year
            df['Month'] = df['Date'].dt.month
            df['DayOfWeek'] = df['Date'].dt.dayofweek
            df['DayName'] = df['Date'].dt.day_name()
            features_created.extend(['Year', 'Month', 'DayOfWeek', 'DayName'])
        
        if features_created:
            print(f"   ✓ Created {len(features_created)} features:")
            for feat in features_created[:10]:
                print(f"     - {feat}")
            if len(features_created) > 10:
                print(f"     ... and {len(features_created) - 10} more")
        else:
            print("   ⚠️  Could not create features (missing required columns)")
        
        return df
    
    def get_cleaning_report(self) -> Dict:
        """
        Get cleaning statistics report
        """
        return {
            'columns_dropped': len(self.columns_dropped),
            'columns_dropped_list': self.columns_dropped,
            'rows_removed': self.rows_removed,
            'stats': self.stats
        }


def clean_football_data(
    df: pd.DataFrame, 
    phase: str = "full",
    missing_threshold: float = 0.5
) -> pd.DataFrame:
    """
    Convenience function for cleaning football data
    
    Args:
        df: Input DataFrame
        phase: "critical" or "full"
        missing_threshold: Threshold for dropping columns (0.0-1.0)
    
    Returns:
        Cleaned DataFrame
    """
    cleaner = FootballDataCleaner(missing_threshold=missing_threshold)
    return cleaner.clean(df, phase=phase)


# Example usage
if __name__ == "__main__":
    # Example: Load and clean data
    print("Football Data Cleaning Pipeline")
    print("=" * 80)
    print("\nUsage:")
    print("  from data_cleaning_pipeline import clean_football_data")
    print("  df_clean = clean_football_data(df, phase='full')")
    print("\nPhases:")
    print("  'critical' - Phase 1 only (drop columns, convert dates)")
    print("  'full' - Phase 1 + Phase 2 (includes feature engineering)")

