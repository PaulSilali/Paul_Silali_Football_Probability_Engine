"""
Script to review model calibration quality.

This script analyzes saved validation results to assess model calibration
and provides recommendations for retraining.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models import ValidationResult, Model, ModelStatus
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_calibration(db):
    """Analyze calibration metrics from validation results"""
    
    # Get all validation results
    validations = db.query(ValidationResult).all()
    
    if not validations:
        logger.warning("No validation results found in database")
        return
    
    logger.info(f"Found {len(validations)} validation results")
    
    # Group by model
    model_stats = {}
    set_stats = {}
    
    for val in validations:
        model_id = val.model_id or "unknown"
        set_type = val.set_type.value if val.set_type else "unknown"
        
        # Model stats
        if model_id not in model_stats:
            model_stats[model_id] = {
                "count": 0,
                "total_matches": 0,
                "correct": 0,
                "brier_scores": [],
                "log_losses": [],
                "accuracies": []
            }
        
        model_stats[model_id]["count"] += 1
        model_stats[model_id]["total_matches"] += val.total_matches or 0
        model_stats[model_id]["correct"] += val.correct_predictions or 0
        if val.brier_score:
            model_stats[model_id]["brier_scores"].append(val.brier_score)
        if val.log_loss:
            model_stats[model_id]["log_losses"].append(val.log_loss)
        if val.accuracy:
            model_stats[model_id]["accuracies"].append(val.accuracy)
        
        # Set stats
        if set_type not in set_stats:
            set_stats[set_type] = {
                "count": 0,
                "total_matches": 0,
                "correct": 0,
                "brier_scores": [],
                "log_losses": [],
                "accuracies": []
            }
        
        set_stats[set_type]["count"] += 1
        set_stats[set_type]["total_matches"] += val.total_matches or 0
        set_stats[set_type]["correct"] += val.correct_predictions or 0
        if val.brier_score:
            set_stats[set_type]["brier_scores"].append(val.brier_score)
        if val.log_loss:
            set_stats[set_type]["log_losses"].append(val.log_loss)
        if val.accuracy:
            set_stats[set_type]["accuracies"].append(val.accuracy)
    
    # Print model statistics
    logger.info("\n=== MODEL STATISTICS ===")
    for model_id, stats in model_stats.items():
        model = db.query(Model).filter(Model.id == model_id).first() if model_id != "unknown" else None
        model_name = model.version if model else f"Model {model_id}"
        
        avg_brier = sum(stats["brier_scores"]) / len(stats["brier_scores"]) if stats["brier_scores"] else 0
        avg_log_loss = sum(stats["log_losses"]) / len(stats["log_losses"]) if stats["log_losses"] else 0
        avg_accuracy = sum(stats["accuracies"]) / len(stats["accuracies"]) if stats["accuracies"] else 0
        overall_accuracy = (stats["correct"] / stats["total_matches"] * 100) if stats["total_matches"] > 0 else 0
        
        logger.info(f"\n{model_name}:")
        logger.info(f"  Validations: {stats['count']}")
        logger.info(f"  Total matches: {stats['total_matches']}")
        logger.info(f"  Correct predictions: {stats['correct']}")
        logger.info(f"  Overall accuracy: {overall_accuracy:.2f}%")
        logger.info(f"  Average accuracy: {avg_accuracy:.2f}%")
        logger.info(f"  Average Brier score: {avg_brier:.4f}")
        logger.info(f"  Average log loss: {avg_log_loss:.4f}")
        
        # Calibration assessment
        if avg_brier > 0.2:
            logger.warning(f"  ⚠️  High Brier score (>0.2) - Poor calibration")
        elif avg_brier > 0.15:
            logger.warning(f"  ⚠️  Moderate Brier score (>0.15) - Calibration could be improved")
        else:
            logger.info(f"  ✓ Good Brier score (<0.15) - Well calibrated")
        
        if avg_accuracy < 40:
            logger.warning(f"  ⚠️  Low accuracy (<40%) - Model may need retraining")
        elif avg_accuracy < 50:
            logger.warning(f"  ⚠️  Moderate accuracy (<50%) - Consider retraining with more data")
        else:
            logger.info(f"  ✓ Acceptable accuracy (>{avg_accuracy:.1f}%)")
    
    # Print set statistics
    logger.info("\n=== SET STATISTICS ===")
    for set_type, stats in sorted(set_stats.items()):
        avg_brier = sum(stats["brier_scores"]) / len(stats["brier_scores"]) if stats["brier_scores"] else 0
        avg_log_loss = sum(stats["log_losses"]) / len(stats["log_losses"]) if stats["log_losses"] else 0
        avg_accuracy = sum(stats["accuracies"]) / len(stats["accuracies"]) if stats["accuracies"] else 0
        overall_accuracy = (stats["correct"] / stats["total_matches"] * 100) if stats["total_matches"] > 0 else 0
        
        logger.info(f"\nSet {set_type}:")
        logger.info(f"  Validations: {stats['count']}")
        logger.info(f"  Total matches: {stats['total_matches']}")
        logger.info(f"  Correct predictions: {stats['correct']}")
        logger.info(f"  Overall accuracy: {overall_accuracy:.2f}%")
        logger.info(f"  Average accuracy: {avg_accuracy:.2f}%")
        logger.info(f"  Average Brier score: {avg_brier:.4f}")
        logger.info(f"  Average log loss: {avg_log_loss:.4f}")
    
    # Recommendations
    logger.info("\n=== RECOMMENDATIONS ===")
    
    # Check if we have enough validation data
    total_validations = len(validations)
    if total_validations < 10:
        logger.warning("⚠️  Limited validation data (<10 validations). Need more saved results for reliable calibration assessment.")
    
    # Check overall accuracy
    total_matches = sum(s["total_matches"] for s in model_stats.values())
    total_correct = sum(s["correct"] for s in model_stats.values())
    overall_accuracy = (total_correct / total_matches * 100) if total_matches > 0 else 0
    
    if overall_accuracy < 40:
        logger.warning("⚠️  Overall accuracy is low (<40%). Consider:")
        logger.warning("   1. Retraining model with more historical data")
        logger.warning("   2. Reviewing team strength calculations")
        logger.warning("   3. Checking if market odds are up-to-date")
    elif overall_accuracy < 50:
        logger.info("ℹ️  Overall accuracy is moderate (40-50%). This is acceptable for football predictions.")
        logger.info("   Consider retraining if accuracy drops below 40%.")
    else:
        logger.info("✓ Overall accuracy is good (>50%). Model is performing well.")
    
    # Check Brier scores
    all_brier_scores = []
    for stats in model_stats.values():
        all_brier_scores.extend(stats["brier_scores"])
    
    if all_brier_scores:
        avg_brier = sum(all_brier_scores) / len(all_brier_scores)
        if avg_brier > 0.2:
            logger.warning("⚠️  Average Brier score is high (>0.2). Model probabilities are poorly calibrated.")
            logger.warning("   Consider retraining calibration model.")
        elif avg_brier > 0.15:
            logger.info("ℹ️  Average Brier score is moderate (0.15-0.2). Calibration could be improved.")
        else:
            logger.info("✓ Average Brier score is good (<0.15). Probabilities are well calibrated.")


def main():
    """Main function"""
    db = SessionLocal()
    
    try:
        analyze_calibration(db)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

