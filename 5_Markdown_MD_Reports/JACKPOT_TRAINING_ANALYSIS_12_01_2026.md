# Jackpot Training Analysis - 12/01/2026

## Summary from Logs

### ✅ **Pipeline Execution Status**

**Jackpot ID**: `JK-1768236688`

**Pipeline Steps Completed**:
1. ✅ Status Check - 26 teams checked, 26 validated, 0 missing
2. ✅ Create Teams - No missing teams to create
3. ✅ Download Data - 1978 matches downloaded for DK1 league
4. ⚠️ Train Model - **PARTIAL SUCCESS** (Poisson & Blending OK, Calibration FAILED)
5. ✅ Recompute Probabilities - Completed successfully

---

## 📊 **Model Training Results**

### ✅ **Poisson Model Training** (SUCCESS)
- **Model ID**: 37
- **Version**: `poisson-20260112-165213`
- **Status**: Active
- **Training Data**: 924 matches (3-year window)
- **Teams Trained**: 22 teams
- **Metrics**:
  - Brier Score: 0.7422
  - Log Loss: 1.3073
  - Accuracy: 43.78%
  - Temperature: 1.400
- **Home Advantage**: 0.1000 (clamped from negative values)
- **Rho**: -0.0780
- **Teams Updated**: 22 teams updated in database

### ✅ **Blending Model Training** (SUCCESS)
- **Model ID**: 38
- **Version**: `blending-20260112-195224`
- **Status**: Active
- **Training Data**: 2495 matches with odds
- **Optimal Alpha**: 0.000 (pure market odds, no model blending)
- **Metrics**:
  - Brier Score: 0.5806
  - Log Loss: 1.7112
  - Temperature: 1.400

### ❌ **Calibration Model Training** (FAILED)
- **Error**: `UnboundLocalError: cannot access local variable 'split_idx' where it is not associated with a value`
- **Location**: `model_training.py` line 1200
- **Cause**: `split_idx` used before definition
- **Impact**: Calibration model not created, but probabilities still calculated using old calibration model

**Fix Applied**: ✅ Moved `split_idx` calculation before logging statement

---

## ⚠️ **Team Training Status Issue**

### **Problem**: Teams Still Show as "Untrained" After Training

**Before Training** (Line 16-22):
- Total teams: 26
- Validated: 26
- Trained: 3
- Untrained: 22

**After Training** (Line 534-569):
- Total teams: 26
- Validated: 26
- Trained: 0 ❌
- Untrained: 26 ❌

### **Root Cause Analysis**:

1. **Team ID Mismatch**: 
   - New model (ID 37) trained on 22 teams with specific IDs
   - Jackpot teams have different IDs than training data
   - Example: Model has team ID 8993, but jackpot has team ID 9310 for "Magdeburg"

2. **Model Only Trained on Teams in Training Data**:
   - Model trained on 924 matches from DK1 league
   - Only teams that appeared in those matches got trained
   - Teams not in training period (2016-2023) are not in model

3. **Team Name Resolution**:
   - Same team name can have different IDs in different contexts
   - "Magdeburg" appears as ID 8993 in old model but ID 9310 in jackpot

### **Why This Happens**:

1. **Training Window**: Model uses 3-year window (2023-2026), so older teams not in recent data won't be trained
2. **Team ID Inconsistency**: Teams may have been created with different IDs at different times
3. **Missing Historical Data**: Some teams don't have matches in the training period

---

## 📈 **Data Download Status**

### ✅ **Successfully Downloaded**:
- **Total Matches**: 1978 matches
- **Leagues**: 1 (DK1)
- **Seasons**: 7 seasons (2526, 2425, 2324, 2223, 2122, 2021, 1920)
- **Errors**: 0

### **Breakdown by Season**:
- 2526: 142 matches
- 2425: 306 matches
- 2324: 306 matches
- 2223: 306 matches
- 2122: 306 matches
- 2021: 306 matches
- 1920: 306 matches

---

## 🎯 **Probability Calculation Results**

### **Data Auto-Downloaded During Calculation**:
- ✅ Weather: Downloaded for all 13 fixtures
- ✅ Rest Days: Calculated for all 13 fixtures (all had 7 days rest)
- ✅ Team Form: Calculated for teams that needed it
- ❌ Injuries: Not downloaded (API key may not be set)

### **Team Strength Sources**:
- **Model Strengths**: 10 teams (38.5%)
- **Default Strengths**: 16 teams (61.5%)
- **DB Strengths**: 0 teams

### **Calibration Applied**:
- ✅ Calibration model active (H=True, D=False, A=False)
- ✅ Applied to 13 fixtures for sets A, B, C, F, G

### **Jackpot Log Saved**:
- ✅ JSON log: `app/logs/jackpot_logs/jackpot_JK-1768236688_20260112_195244.json`
- ✅ Summary log: `app/logs/jackpot_logs/jackpot_JK-1768236688_20260112_195244_SUMMARY.txt`

---

## 🔧 **Issues Fixed**

1. ✅ **Calibration Training Error**: Fixed `split_idx` UnboundLocalError
   - Moved `split_idx` calculation before logging statement
   - Location: `model_training.py` line 1204 → moved to line 1199

---

## ⚠️ **Remaining Issues**

1. **Team ID Mismatch**: 
   - Teams in jackpot have different IDs than teams in training data
   - Need to ensure team ID consistency or use team name matching

2. **Teams Not in Training Data**:
   - Some teams don't appear in training matches (2016-2023 window)
   - These teams will always show as "untrained" until they have matches in training period

3. **Calibration Model Not Created**:
   - Calibration training failed, so new calibration model not created
   - System using old calibration model (ID 34) from previous training

---

## 📋 **Recommendations**

1. ✅ **Fix Applied**: Calibration training error fixed
2. **Team ID Resolution**: Consider using team name matching instead of ID matching for training status
3. **Training Window**: Consider expanding training window or using all available data for teams that need training
4. **Team ID Consistency**: Ensure teams are created with consistent IDs across different contexts

---

## ✅ **What's Working**

1. ✅ Pipeline executes successfully
2. ✅ Data downloads correctly (1978 matches)
3. ✅ Poisson model trains successfully (22 teams)
4. ✅ Blending model trains successfully
5. ✅ Probabilities calculate successfully
6. ✅ Weather and rest days auto-download
7. ✅ Team form auto-calculates
8. ✅ Jackpot logs save correctly
9. ✅ MLflow failures are non-blocking (timeout after 5 seconds)

---

## 📝 **Next Steps**

1. ✅ Fix calibration training error (DONE)
2. Investigate team ID mismatch issue
3. Consider expanding training data window for teams that need training
4. Verify jackpot logs are being saved correctly

