"""
Script to update calibration model to use the latest Poisson model.

When a new Poisson model is trained, the calibration model still references
the old Poisson model. This script updates the calibration model to use
the latest active Poisson model.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import Model, ModelStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_calibration_model(dry_run: bool = False):
    """Update calibration model to use latest Poisson model"""
    db = SessionLocal()
    
    try:
        # Find active calibration model
        calibration_model = db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == "calibration"
        ).order_by(Model.training_completed_at.desc()).first()
        
        if not calibration_model:
            logger.warning("No active calibration model found")
            return
        
        logger.info(f"Found calibration model: {calibration_model.version} (ID: {calibration_model.id})")
        
        # Find latest active Poisson model
        poisson_model = db.query(Model).filter(
            Model.status == ModelStatus.active,
            Model.model_type == "poisson"
        ).order_by(Model.training_completed_at.desc()).first()
        
        if not poisson_model:
            logger.warning("No active Poisson model found")
            return
        
        logger.info(f"Found Poisson model: {poisson_model.version} (ID: {poisson_model.id})")
        
        # Check if calibration model already references this Poisson model
        base_model_id = calibration_model.model_weights.get('base_model_id')
        if base_model_id == poisson_model.id:
            logger.info("Calibration model already references the latest Poisson model")
            return
        
        # Get the blending model that the calibration model references
        if base_model_id:
            base_model = db.query(Model).filter(Model.id == base_model_id).first()
            if base_model and base_model.model_type == "blending":
                logger.info(f"Calibration model references blending model: {base_model.version} (ID: {base_model.id})")
                
                # Check if blending model references the latest Poisson model
                blending_poisson_id = base_model.model_weights.get('poisson_model_id')
                if blending_poisson_id == poisson_model.id:
                    logger.info("Blending model already references the latest Poisson model")
                    return
                
                # Update blending model to reference new Poisson model
                if not dry_run:
                    if base_model.model_weights:
                        base_model.model_weights['poisson_model_id'] = poisson_model.id
                        base_model.model_weights['poisson_model_version'] = poisson_model.version
                        db.commit()
                        logger.info(f"✓ Updated blending model {base_model.version} to reference Poisson model {poisson_model.version}")
                    else:
                        logger.error("Blending model has no model_weights")
                else:
                    logger.info(f"[DRY RUN] Would update blending model {base_model.version} to reference Poisson model {poisson_model.version}")
            else:
                logger.warning(f"Base model (ID: {base_model_id}) is not a blending model or not found")
        else:
            logger.warning("Calibration model has no base_model_id")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update calibration model to use latest Poisson model")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    args = parser.parse_args()
    
    update_calibration_model(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

