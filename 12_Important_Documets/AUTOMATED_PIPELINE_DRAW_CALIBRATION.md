# Draw Calibration in Automated Pipeline

## ✅ **ADDED: Draw Calibration as Optional Step**

The automated pipeline now includes **draw calibration** as an optional 4th step in the training pipeline.

---

## Training Pipeline Flow

```
Step 1: Train Poisson Model (75%)
  ↓ Estimates team strengths, base probabilities
  
Step 2: Train Blending Model (80%)
  ↓ Combines Poisson predictions with market odds
  
Step 3: Train Calibration Model (90%)
  ↓ Calibrates all three outcomes (H/D/A)
  
Step 4: Train Draw Calibration Model (92%) [OPTIONAL]
  ↓ Specialized calibration for draw probabilities only
  ↓ Requires 500+ historical predictions with actual results
  
Result: Full Pipeline with Draw Calibration (95%)
```

---

## Draw Calibration Explained

### What It Does:
- **Specialized calibration** for draw probabilities only
- Uses **isotonic regression** to calibrate P(Draw)
- **Does NOT** touch home/away probabilities
- Focuses specifically on improving draw probability accuracy

### Why It's Optional:
- Requires **500+ historical predictions** with actual results
- Needs predictions from past jackpots that have been resolved
- May not be available for new systems or leagues
- Pipeline continues successfully even if draw calibration fails

### When It Runs:
- ✅ Runs automatically if sufficient data is available
- ⚠️ Skips gracefully if insufficient data
- ⚠️ Skips if no active draw model found
- ✅ Logs warning but doesn't fail the pipeline

---

## Code Implementation

### In Automated Pipeline:
```python
# Step 4: Train draw calibration model (optional)
try:
    draw_calibration_result = self.training_service.train_draw_calibration_model(
        leagues=list(league_codes) if league_codes else None,
        task_id=draw_calibration_task_id
    )
    logger.info("✓ Draw calibration model trained successfully")
except Exception as draw_e:
    # Draw calibration is optional - log but don't fail
    logger.warning(f"⚠ Draw calibration skipped: {draw_e}")
    if "Insufficient" in str(draw_e):
        logger.info("Requires 500+ predictions with actual results")
```

---

## Pipeline Metadata

The pipeline metadata includes draw calibration status:

```json
{
  "training_stats": {
    "poisson": {...},
    "blending": {...},
    "calibration": {...},
    "draw_calibration": {
      "model_id": 126,
      "version": "draw-calibration-20250108-123700"
    },
    "final_model_id": 125,
    "final_version": "calibration-20250108-123600",
    "pipeline": "full"
  }
}
```

**If Draw Calibration Skipped:**
```json
{
  "draw_calibration": {
    "skipped": true,
    "error": "Insufficient draw samples for calibration (min 500, got 123)",
    "note": "Requires 500+ predictions with actual results"
  }
}
```

---

## Requirements

### For Draw Calibration to Run:
1. ✅ **500+ predictions** with draw probabilities
2. ✅ **Actual results** from resolved matches
3. ✅ **Active draw model** in database
4. ✅ **Historical data** from past jackpots

### If Requirements Not Met:
- ⚠️ Draw calibration is **skipped**
- ✅ Pipeline **continues successfully**
- ✅ Other models (Poisson, Blending, Calibration) still trained
- ✅ Warning logged but no failure

---

## Benefits

### When Draw Calibration Runs:
- ✅ **Improved draw probability accuracy**
- ✅ **Better calibrated draw predictions**
- ✅ **Specialized focus** on draw outcomes
- ✅ **Complements** general calibration

### When Draw Calibration Skips:
- ✅ Pipeline still completes successfully
- ✅ Other models provide good predictions
- ✅ Can be added later when data is available

---

## Progress Updates

```
75% - Training Poisson model...
80% - Training blending model...
90% - Training calibration model...
92% - Training draw calibration model...
95% - Full pipeline trained: calibration-20250108-123600 (with draw calibration)
```

**If Draw Calibration Skips:**
```
92% - Training draw calibration model...
⚠ Draw calibration skipped: Insufficient draw samples...
95% - Full pipeline trained: calibration-20250108-123600
```

---

## Draw Model vs Draw Calibration

### Draw Model:
- **Deterministic** - doesn't need training
- Computes P(Draw) from Poisson outputs at inference time
- Uses structural adjustments (rest days, form, etc.)

### Draw Calibration:
- **Trained model** - uses isotonic regression
- Calibrates P(Draw) predictions to match actual frequencies
- Requires historical predictions with actual results
- **Optional** enhancement to improve accuracy

---

## Summary

✅ **Draw calibration added to automated pipeline**

- ✅ Runs as optional 4th step
- ✅ Requires 500+ predictions with results
- ✅ Skips gracefully if data unavailable
- ✅ Improves draw probability accuracy when available
- ✅ Doesn't fail pipeline if skipped

**Result:** Full pipeline with specialized draw calibration when data is available

