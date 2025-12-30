# Model Chain Analysis

## Current Model Status (from Training History)

### Active Models:
1. **Calibration**: `calibration-20251229-132230` (ID: 9) - Active
2. **Blending**: `blending-20251229-132027` (ID: 8) - Active  
3. **Poisson**: `poisson-20251230-034633` (ID: 12) - Active (Latest)

### Archived Models:
- `poisson-20251230-034342` (ID: 11) - Had negative home_advantage (-0.7987)
- `poisson-20251230-033842` (ID: 10)
- `poisson-20251229-094925` (ID: 7) - Old model

## Model Chain Issue

**Problem**: The calibration model (ID: 9) references the blending model (ID: 8), which likely references the **old Poisson model (ID: 7)** instead of the **latest Poisson model (ID: 12)**.

**Impact**: 
- System is using old team strengths
- Old model may have different parameters
- New training improvements aren't being used

## How to Check Model Chain

### Option 1: Run SQL Query
```sql
-- Run: 3_Database_Football_Probability_Engine/migrations/check_model_chain.sql
```

### Option 2: Use Python Script
```bash
python "2_Backend_Football_Probability_Engine/scripts/check_trained_models.py"
```

### Option 3: Use Update Script
```bash
# This will show what needs to be updated
python "2_Backend_Football_Probability_Engine/scripts/update_calibration_model.py" --dry-run

# Actually update
python "2_Backend_Football_Probability_Engine/scripts/update_calibration_model.py"
```

## Fixes Applied

### 1. Negative Home Advantage - FIXED ✅
- Added constraints in `poisson_trainer.py` to clamp `home_advantage` to 0.1-0.6
- Future training will not produce negative values
- Existing models with negative values are clamped during probability calculation

### 2. Model Chain Update - Script Created ✅
- Created `update_calibration_model.py` to update blending model's Poisson reference
- This ensures the calibration model uses the latest Poisson model

## Recommendations

1. **Update Model Chain**:
   ```bash
   python "2_Backend_Football_Probability_Engine/scripts/update_calibration_model.py"
   ```

2. **Retrain Calibration Model** (after updating chain):
   - This will use the latest Poisson model with corrected parameters
   - Will improve calibration quality

3. **Add Missing Teams** (if not done):
   ```sql
   \i "3_Database_Football_Probability_Engine/migrations/add_missing_teams.sql"
   ```

4. **Retrain Poisson Model** (after adding teams):
   - This will calculate proper strengths for newly added teams
   - Will use the fixed home_advantage constraints

## Expected Results After Fixes

- ✅ Latest Poisson model (ID: 12) will be used
- ✅ No negative home_advantage in future training
- ✅ All teams will have proper strengths (after adding missing teams)
- ✅ Better probability variation (less uniform)
- ✅ Improved accuracy and calibration

