# Fully Trained Status - Calibration Check Fix

## Summary

Updated the "fully trained" status check to include calibration model verification, not just Poisson model.

---

## ✅ Changes Applied

### **Before (Old Behavior)**:
- ❌ Only checked if team is in Poisson model's `team_strengths`
- ❌ Didn't verify if calibration model exists
- ❌ Teams marked as "trained" even if only Poisson model exists (partial pipeline)

### **After (New Behavior)**:
- ✅ Checks if team is in Poisson model's `team_strengths`
- ✅ Also checks if active calibration model exists
- ✅ Teams marked as "fully trained" only if BOTH conditions are met:
  1. Team is in Poisson model
  2. Active calibration model exists

---

## Code Changes

### Location: `app/services/automated_pipeline.py`

#### 1. **Added Calibration Model Check** (lines 60-66)
```python
# Also check for active calibration model (for full pipeline training)
calibration_model = self.db.query(Model).filter(
    Model.model_type == "calibration",
    Model.status == ModelStatus.active
).order_by(Model.training_completed_at.desc()).first()

has_full_pipeline = poisson_model is not None and calibration_model is not None
```

#### 2. **Updated Training Status Logic** (lines 90-112)
```python
# Check if team has training data (by ID or by canonical_name)
# For "fully trained", team must be in Poisson model AND calibration model must exist
is_in_poisson = (
    team_id in team_strengths or 
    str(team_id) in team_strengths or
    (canonical_name and canonical_name in team_strengths_by_name)
)

# Team is "fully trained" if it's in Poisson model AND full pipeline (calibration) exists
is_fully_trained = is_in_poisson and has_full_pipeline
```

#### 3. **Enhanced Logging** (lines 114-123)
- Logs "fully trained" if both Poisson and Calibration exist
- Logs "partial training" if only Poisson exists
- Logs "not trained" if team not in Poisson model

#### 4. **Enhanced Team Details** (lines 129-136)
```python
team_details[team_name] = {
    "team_id": team_id,
    "isValid": True,
    "isTrained": is_fully_trained,  # Only True if both Poisson and Calibration exist
    "isInPoisson": is_in_poisson,  # True if in Poisson model
    "hasFullPipeline": has_full_pipeline,  # True if calibration exists
    "league_code": league_code,
    "league_id": team.league_id
}
```

---

## Behavior

### **Team Status Scenarios**:

1. **Fully Trained** ✅
   - Team is in Poisson model's `team_strengths`
   - Active calibration model exists
   - `isTrained = True`
   - Log: "✓ Team is validated and fully trained (Poisson + Calibration)"

2. **Partial Training** ⚠️
   - Team is in Poisson model's `team_strengths`
   - Active calibration model does NOT exist
   - `isTrained = False` (but `isInPoisson = True`)
   - Log: "⚠ Team is in Poisson model but calibration missing (partial training)"

3. **Not Trained** ❌
   - Team is NOT in Poisson model's `team_strengths`
   - `isTrained = False`
   - Log: "⚠ Team is validated but NOT trained - missing from active Poisson model"

---

## Why This Matters

### **Full Pipeline Training**:
The automated pipeline trains: **Poisson → Blending → Calibration**

- **Poisson Model**: Base model with team strengths
- **Blending Model**: Combines Poisson with market odds
- **Calibration Model**: Calibrates the blended model

### **For Best Predictions**:
- Teams should be in Poisson model (have team strengths)
- Calibration model should exist (for calibrated probabilities)
- Both are required for "fully trained" status

---

## Impact

### **Before Fix**:
- Teams showed as "trained" even if only Poisson model existed
- No indication that calibration was missing
- Users might think pipeline is fully trained when it's not

### **After Fix**:
- Teams only show as "fully trained" if both Poisson and Calibration exist
- Clear indication of partial vs full training
- Better visibility into pipeline completeness

---

## Testing

To verify the fix:

1. **Check team status after training**:
   ```python
   pipeline_service = AutomatedPipelineService(db)
   status = pipeline_service.check_teams_status(team_names, league_id)
   
   # Check if teams are fully trained
   for team_name, details in status['team_details'].items():
       print(f"{team_name}: isTrained={details['isTrained']}, hasFullPipeline={details['hasFullPipeline']}")
   ```

2. **Verify calibration model exists**:
   ```python
   calibration_model = db.query(Model).filter(
       Model.model_type == "calibration",
       Model.status == ModelStatus.active
   ).first()
   
   if calibration_model:
       print(f"Calibration model exists: {calibration_model.version}")
   else:
       print("No active calibration model")
   ```

---

## Files Modified

1. **`app/services/automated_pipeline.py`**
   - Added calibration model check
   - Updated training status logic
   - Enhanced logging and team details

2. **`scripts/test_injuries_download_12_01_2026.py`**
   - Fixed path handling for better cross-platform compatibility

---

## Summary

✅ **"Fully trained" now requires both Poisson AND Calibration models**

- Teams in Poisson model only = Partial training
- Teams in Poisson model + Calibration exists = Fully trained
- Better visibility into pipeline completeness

