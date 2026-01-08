#!/usr/bin/env python3
"""
Standalone script to update team ratings (attack_rating, defense_rating, home_bias)
by training the Poisson model.
"""
import sys
import os
import argparse
import logging

# Add parent directory to path to import from backend
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, '..', '..', '2_Backend_Football_Probability_Engine')
backend_dir = os.path.normpath(backend_dir)
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.model_training import ModelTrainingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_team_ratings(db_url: str):
    """Update team ratings by training the model"""
    try:
        # Create database connection
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            logger.info("Training Poisson model to update team ratings...")
            logger.info("This may take several minutes depending on match data size...")
            
            service = ModelTrainingService(db)
            
            # Train model (this will automatically update teams table)
            result = service.train_poisson_model()
            
            logger.info(f"✅ Model training completed!")
            logger.info(f"   Model Version: {result.get('version', 'N/A')}")
            logger.info(f"   Model ID: {result.get('modelId', 'N/A')}")
            logger.info(f"   Matches Used: {result.get('matchCount', 'N/A')}")
            logger.info(f"   Training Run ID: {result.get('trainingRunId', 'N/A')}")
            logger.info(f"✅ Team ratings updated in teams table")
            
        except Exception as e:
            logger.error(f"❌ Error during model training: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error updating team ratings: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Starting team ratings update script...", flush=True)
    parser = argparse.ArgumentParser(
        description="Update team ratings (attack_rating, defense_rating, home_bias) by training the model"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default="postgresql://postgres:11403775411@localhost/football_probability_engine",
        help="Database connection URL"
    )
    
    args = parser.parse_args()
    
    print(f"Database URL: {args.db_url}", flush=True)
    print("Starting model training (this may take several minutes)...", flush=True)
    
    update_team_ratings(args.db_url)
    
    print("Script completed.", flush=True)

