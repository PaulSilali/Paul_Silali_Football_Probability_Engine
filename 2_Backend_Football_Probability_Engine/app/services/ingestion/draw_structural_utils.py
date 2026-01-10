"""
Utility functions for draw structural data ingestion
"""
from pathlib import Path
from typing import Tuple, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def save_draw_structural_csv(
    df,
    folder_name: str,
    filename: str,
    save_to_cleaned: bool = True
) -> Tuple[Path, Optional[Path]]:
    """
    Save draw structural CSV file to both locations:
    1. data/1_data_ingestion/Draw_structural/{folder_name}/
    2. data/2_Cleaned_data/Draw_structural/{folder_name}/ (if save_to_cleaned=True)
    
    Args:
        df: pandas DataFrame to save
        folder_name: Subfolder name (e.g., 'Elo_Rating', 'h2h_stats')
        filename: CSV filename (e.g., 'G1_2223_elo_ratings.csv')
        save_to_cleaned: Whether to also save to cleaned_data folder
    
    Returns:
        Tuple of (ingestion_path, cleaned_path) - cleaned_path is None if save_to_cleaned=False
    """
    # Resolve backend root
    backend_root = Path(__file__).parent.parent.parent.parent
    
    # Save to ingestion folder
    ingestion_dir = backend_root / "data" / "1_data_ingestion" / "Draw_structural" / folder_name
    ingestion_dir.mkdir(parents=True, exist_ok=True)
    ingestion_path = ingestion_dir / filename
    df.to_csv(ingestion_path, index=False)
    logger.info(f"Saved to ingestion folder: {ingestion_path.resolve()}")
    
    # Save to cleaned folder (if requested)
    cleaned_path = None
    if save_to_cleaned:
        cleaned_dir = backend_root / "data" / "2_Cleaned_data" / "Draw_structural" / folder_name
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        cleaned_path = cleaned_dir / filename
        df.to_csv(cleaned_path, index=False)
        logger.info(f"Saved to cleaned folder: {cleaned_path.resolve()}")
    
    return ingestion_path, cleaned_path

