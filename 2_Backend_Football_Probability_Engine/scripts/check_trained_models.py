"""
Script to check trained models and their relationships.

This script shows:
- All models and their status
- Model chain (Calibration -> Blending -> Poisson)
- Model parameters (home_advantage, rho, etc.)
- Team strengths count
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import Model, ModelStatus
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_models():
    """Check all trained models and their relationships"""
    db = SessionLocal()
    
    try:
        logger.info("=== TRAINED MODELS OVERVIEW ===\n")
        
        # Get all models
        all_models = db.query(Model).order_by(Model.training_completed_at.desc()).all()
        
        logger.info(f"Total models: {len(all_models)}\n")
        
        # Group by type
        poisson_models = [m for m in all_models if m.model_type == 'poisson']
        blending_models = [m for m in all_models if m.model_type == 'blending']
        calibration_models = [m for m in all_models if m.model_type == 'calibration']
        
        logger.info(f"Poisson models: {len(poisson_models)}")
        logger.info(f"Blending models: {len(blending_models)}")
        logger.info(f"Calibration models: {len(calibration_models)}\n")
        
        # Active models
        active_models = [m for m in all_models if m.status == ModelStatus.active]
        logger.info(f"Active models: {len(active_models)}\n")
        
        # Show active models
        logger.info("=== ACTIVE MODELS ===")
        for model in active_models:
            logger.info(f"\n{model.model_type.upper()}: {model.version} (ID: {model.id})")
            logger.info(f"  Status: {model.status.value}")
            logger.info(f"  Trained: {model.training_completed_at}")
            logger.info(f"  Matches: {model.training_matches}")
            logger.info(f"  Brier Score: {model.brier_score}")
            logger.info(f"  Accuracy: {model.overall_accuracy}%")
            
            if model.model_weights:
                if model.model_type == 'poisson':
                    team_strengths = model.model_weights.get('team_strengths', {})
                    home_adv = model.model_weights.get('home_advantage', 'N/A')
                    rho = model.model_weights.get('rho', 'N/A')
                    logger.info(f"  Team Strengths: {len(team_strengths)} teams")
                    logger.info(f"  Home Advantage: {home_adv}")
                    logger.info(f"  Rho: {rho}")
                    
                    # Check for negative home_advantage
                    if isinstance(home_adv, (int, float)) and home_adv < 0:
                        logger.warning(f"  ⚠️  WARNING: Negative home_advantage ({home_adv})!")
                
                elif model.model_type == 'blending':
                    poisson_id = model.model_weights.get('poisson_model_id')
                    blend_alpha = model.model_weights.get('blend_alpha', 'N/A')
                    logger.info(f"  Blend Alpha: {blend_alpha}")
                    if poisson_id:
                        poisson_model = db.query(Model).filter(Model.id == poisson_id).first()
                        if poisson_model:
                            logger.info(f"  References Poisson: {poisson_model.version} (ID: {poisson_id})")
                        else:
                            logger.warning(f"  ⚠️  References missing Poisson model (ID: {poisson_id})")
                    else:
                        logger.warning(f"  ⚠️  No poisson_model_id in model_weights")
                
                elif model.model_type == 'calibration':
                    base_model_id = model.model_weights.get('base_model_id')
                    logger.info(f"  References Base Model ID: {base_model_id}")
                    if base_model_id:
                        base_model = db.query(Model).filter(Model.id == base_model_id).first()
                        if base_model:
                            logger.info(f"  Base Model: {base_model.model_type} - {base_model.version} (ID: {base_model_id})")
                            
                            # If base is blending, check its poisson reference
                            if base_model.model_type == 'blending' and base_model.model_weights:
                                poisson_id = base_model.model_weights.get('poisson_model_id')
                                if poisson_id:
                                    poisson_model = db.query(Model).filter(Model.id == poisson_id).first()
                                    if poisson_model:
                                        logger.info(f"    → Blending references Poisson: {poisson_model.version} (ID: {poisson_id})")
                                    else:
                                        logger.warning(f"    → ⚠️  Blending references missing Poisson (ID: {poisson_id})")
                                else:
                                    logger.warning(f"    → ⚠️  Blending has no poisson_model_id")
                        else:
                            logger.warning(f"  ⚠️  Base model (ID: {base_model_id}) not found")
                    else:
                        logger.warning(f"  ⚠️  No base_model_id in calibration model")
        
        # Show model chain
        logger.info("\n=== MODEL CHAIN (Active) ===")
        calibration = [m for m in active_models if m.model_type == 'calibration']
        if calibration:
            cal = calibration[0]
            logger.info(f"Calibration: {cal.version}")
            
            base_id = cal.model_weights.get('base_model_id') if cal.model_weights else None
            if base_id:
                base = db.query(Model).filter(Model.id == base_id).first()
                if base:
                    logger.info(f"  ↓")
                    logger.info(f"Blending: {base.version}")
                    
                    if base.model_weights:
                        poisson_id = base.model_weights.get('poisson_model_id')
                        if poisson_id:
                            poisson = db.query(Model).filter(Model.id == poisson_id).first()
                            if poisson:
                                logger.info(f"  ↓")
                                logger.info(f"Poisson: {poisson.version} (Status: {poisson.status.value})")
                                
                                # Check if this is the latest
                                latest_poisson = db.query(Model).filter(
                                    Model.model_type == 'poisson'
                                ).order_by(Model.training_completed_at.desc()).first()
                                
                                if poisson.id != latest_poisson.id:
                                    logger.warning(f"  ⚠️  WARNING: Using old Poisson model!")
                                    logger.warning(f"      Latest Poisson: {latest_poisson.version} (ID: {latest_poisson.id})")
                                    logger.warning(f"      Current Poisson: {poisson.version} (ID: {poisson.id})")
                            else:
                                logger.error(f"  ✗ Poisson model (ID: {poisson_id}) not found")
        else:
            logger.info("No active calibration model found")
            # Check for active blending
            blending = [m for m in active_models if m.model_type == 'blending']
            if blending:
                blend = blending[0]
                logger.info(f"Blending: {blend.version}")
                if blend.model_weights:
                    poisson_id = blend.model_weights.get('poisson_model_id')
                    if poisson_id:
                        poisson = db.query(Model).filter(Model.id == poisson_id).first()
                        if poisson:
                            logger.info(f"  ↓")
                            logger.info(f"Poisson: {poisson.version} (Status: {poisson.status.value})")
            else:
                # Check for active poisson
                poisson = [m for m in active_models if m.model_type == 'poisson']
                if poisson:
                    logger.info(f"Poisson: {poisson[0].version}")
        
        # Latest models
        logger.info("\n=== LATEST MODELS (by type) ===")
        latest_poisson = db.query(Model).filter(
            Model.model_type == 'poisson'
        ).order_by(Model.training_completed_at.desc()).first()
        
        latest_blending = db.query(Model).filter(
            Model.model_type == 'blending'
        ).order_by(Model.training_completed_at.desc()).first()
        
        latest_calibration = db.query(Model).filter(
            Model.model_type == 'calibration'
        ).order_by(Model.training_completed_at.desc()).first()
        
        if latest_poisson:
            logger.info(f"Latest Poisson: {latest_poisson.version} (ID: {latest_poisson.id}, Status: {latest_poisson.status.value})")
            if latest_poisson.model_weights:
                home_adv = latest_poisson.model_weights.get('home_advantage', 'N/A')
                if isinstance(home_adv, (int, float)) and home_adv < 0:
                    logger.warning(f"  ⚠️  Negative home_advantage: {home_adv}")
        
        if latest_blending:
            logger.info(f"Latest Blending: {latest_blending.version} (ID: {latest_blending.id}, Status: {latest_blending.status.value})")
        
        if latest_calibration:
            logger.info(f"Latest Calibration: {latest_calibration.version} (ID: {latest_calibration.id}, Status: {latest_calibration.status.value})")
        
        # Recommendations
        logger.info("\n=== RECOMMENDATIONS ===")
        
        # Check if calibration uses latest poisson
        if calibration and latest_poisson:
            cal = calibration[0]
            base_id = cal.model_weights.get('base_model_id') if cal.model_weights else None
            if base_id:
                base = db.query(Model).filter(Model.id == base_id).first()
                if base and base.model_type == 'blending' and base.model_weights:
                    poisson_id = base.model_weights.get('poisson_model_id')
                    if poisson_id != latest_poisson.id:
                        logger.warning("⚠️  Calibration model is using an old Poisson model")
                        logger.info("   Run: python scripts/update_calibration_model.py")
        
        # Check for negative home_advantage
        for model in poisson_models:
            if model.model_weights:
                home_adv = model.model_weights.get('home_advantage')
                if isinstance(home_adv, (int, float)) and home_adv < 0:
                    logger.warning(f"⚠️  Model {model.version} has negative home_advantage: {home_adv}")
                    logger.info("   This will be clamped to 0.35 in probability calculations")
                    logger.info("   Retrain the model to fix this permanently")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    check_models()

