# Validation-Based Calibration Retraining - Implementation Complete ✅

## Overview

**Implemented:** Automatic and manual retraining of calibration models using validation results to improve probability accuracy.

**Location:** 
- **Backend:** `app/services/model_training.py` - `train_calibration_from_validation()` method
- **API:** `app/api/probabilities.py` - `/validation/retrain-calibration` endpoint
- **Frontend:** `src/pages/JackpotValidation.tsx` - "Retrain Calibration Model" button

---

## What Was Implemented

### 1. ✅ Backend: Validation-Based Calibration Training

**File:** `app/services/model_training.py`

**Method:** `train_calibration_from_validation()`

**Features:**
- Trains calibration model using `ValidationResult` data (not just historical matches)
- Uses actual prediction performance from validation exports
- Creates feedback loop: validation → model improvement → better predictions
- Requires minimum 50 validation matches (configurable)
- Supports filtering by validation result IDs or using all exported validations

**How It Works:**
1. Loads validation results from `ValidationResult` table
2. For each validation, gets predictions from `Prediction` table
3. Matches predictions with actual results from `SavedProbabilityResult`
4. Trains isotonic regression calibrator on prediction/actual pairs
5. Creates new calibration model version
6. Archives old calibration model

---

### 2. ✅ API Endpoint: Manual Retraining

**Endpoint:** `POST /api/probabilities/validation/retrain-calibration`

**Request:**
```json
{
  "validation_result_ids": [1, 2, 3],  // Optional: specific validation IDs
  "use_all_validation": true,          // Use all exported validations
  "base_model_id": 12,                 // Optional: specific base model
  "min_validation_matches": 50         // Minimum matches required
}
```

**Response:**
```json
{
  "success": true,
  "message": "Calibration model retrained successfully using 150 validation matches",
  "data": {
    "modelId": 15,
    "version": "calibration-validation-20260109-120000",
    "metrics": {
      "brierScore": 0.1234,
      "logLoss": 0.5678
    },
    "matchCount": 150,
    "validationResultCount": 10,
    "trainingRunId": 42
  }
}
```

---

### 3. ✅ Automatic Retraining After Export

**File:** `app/api/probabilities.py` - `export_validation_to_training()` endpoint

**Behavior:**
- After exporting validation data, system checks total exported matches
- If ≥ 50 matches exported, **automatically retrains** calibration model
- Non-blocking: Export succeeds even if auto-retraining fails
- Returns info about auto-retraining in response

**Response includes:**
```json
{
  "auto_retrained": true,
  "auto_retrain_result": {...},
  "total_validation_matches": 150
}
```

---

### 4. ✅ Frontend: Retrain Button

**Location:** `JackpotValidation.tsx` page

**Button:** "Retrain Calibration Model" (next to Export buttons)

**Features:**
- Manual retraining trigger
- Shows loading state during retraining
- Displays success/error messages
- Auto-refreshes page after successful retraining
- Disabled during export operations

**UI Location:**
- **Section:** "Export Validation Data to Training" card
- **Position:** Right side, next to "Export All to Training" button
- **Style:** Accent color, outline variant

---

## How to Use

### Method 1: Automatic Retraining (Recommended)

1. **Export Validation Data:**
   - Go to **Jackpot Validation** page
   - Click **"Export All to Training"**
   - System automatically retrains if ≥ 50 matches exported

2. **Check Results:**
   - Toast notification shows if auto-retraining occurred
   - New calibration model version created automatically
   - Old model archived

### Method 2: Manual Retraining

1. **Export Validation Data:**
   - Export validation results (any amount)

2. **Retrain Manually:**
   - Click **"Retrain Calibration Model"** button
   - System retrains using all exported validation data
   - Requires minimum 50 matches (configurable)

3. **Monitor Progress:**
   - Button shows loading state
   - Success message displays new model version
   - Page auto-refreshes to show updated model

---

## UI Location

### Where to Find the Retrain Button:

**Page:** `Jackpot Validation` (Navigation: **Validation** → **Jackpot Validation**)

**Section:** "Export Validation Data to Training" card

**Position:** 
- Right side of the card
- Next to "Export Selected" and "Export All to Training" buttons
- Button text: **"Retrain Calibration Model"**
- Icon: RefreshCw (circular arrows)

**Visual:**
```
┌─────────────────────────────────────────────────────────┐
│ Export Validation Data to Training                     │
│                                                         │
│ [Export Selected] [Export All] [Retrain Calibration]   │
│                                    ↑                    │
│                         This button                     │
└─────────────────────────────────────────────────────────┘
```

---

## Workflow

### Complete Validation → Improvement Cycle:

```
1. Create Jackpot → Calculate Probabilities
   ↓
2. Save Results → Store predictions
   ↓
3. Enter Actual Results → Update saved results
   ↓
4. Export Validation → Store in ValidationResult table
   ↓
5. ✅ AUTO-RETRAIN (if ≥ 50 matches)
   OR
   ✅ MANUAL RETRAIN (click button)
   ↓
6. New Calibration Model Created
   ↓
7. Next Predictions Use Improved Model
   ↓
8. Better Accuracy Over Time
```

---

## Technical Details

### Data Flow:

1. **Validation Export:**
   - `SavedProbabilityResult` → `ValidationResult` table
   - Stores: predictions, actuals, accuracy, Brier score, log loss

2. **Retraining:**
   - `ValidationResult` → Load predictions from `Prediction` table
   - Match with actual results from `SavedProbabilityResult`
   - Train isotonic regression calibrator
   - Create new `Model` record (type: 'calibration')
   - Store calibration curves in `CalibrationData` table

3. **Model Activation:**
   - New calibration model automatically set to `active`
   - Old calibration model set to `archived`
   - Next probability calculations use new model

### Requirements:

- **Minimum Matches:** 50 (configurable via `min_validation_matches`)
- **Data Required:**
  - Validation results exported (`exported_to_training = True`)
  - Predictions stored in `Prediction` table
  - Actual results in `SavedProbabilityResult.actual_results`

---

## Benefits

### ✅ Automatic Improvement:
- Models learn from your actual prediction performance
- No manual intervention needed (after initial export)
- Continuous improvement as more validation data accumulates

### ✅ Better Accuracy:
- Calibration based on real-world predictions (not just historical matches)
- Models adapt to your specific use case
- Probability sets that perform best get better calibration

### ✅ Data-Driven:
- Decisions based on actual results
- Track which probability sets work best
- Measure improvement over time

---

## Configuration

### Adjust Auto-Retraining Threshold:

**File:** `app/api/probabilities.py`

**Line:** ~1930

**Change:**
```python
auto_retrain_threshold = 50  # Change this value
```

### Adjust Manual Retraining Minimum:

**Frontend:** `JackpotValidation.tsx`

**Change:**
```typescript
min_validation_matches: 50  // In handleRetrainCalibration
```

**Backend:** `app/api/probabilities.py`

**Change:**
```python
min_validation_matches: int = Body(50, embed=True)
```

---

## Testing

### Test Automatic Retraining:

1. Export validation data with ≥ 50 matches
2. Check response for `auto_retrained: true`
3. Verify new calibration model created
4. Check model version starts with `calibration-validation-`

### Test Manual Retraining:

1. Export any amount of validation data
2. Click "Retrain Calibration Model" button
3. Verify success message
4. Check new model version in database

### Verify Model Improvement:

1. Note accuracy before retraining
2. Retrain calibration model
3. Create new jackpot with same teams
4. Compare probabilities (should be more calibrated)
5. Check accuracy after retraining

---

## Troubleshooting

### Issue: "Insufficient validation matches"

**Solution:** Export more validation results or lower `min_validation_matches`

### Issue: "No validation results found"

**Solution:** Export validation data first using "Export All to Training"

### Issue: "Predictions count mismatch"

**Solution:** Ensure predictions were saved when probabilities were calculated. Re-calculate probabilities for the jackpot.

### Issue: Auto-retraining not triggering

**Solution:** 
- Check total exported matches: `SELECT SUM(total_matches) FROM validation_results WHERE exported_to_training = TRUE;`
- Must be ≥ 50 for auto-retraining
- Check logs for errors

---

## Summary

✅ **Backend:** Validation-based calibration training method implemented
✅ **API:** Manual retraining endpoint added
✅ **Auto-Retrain:** Automatic retraining after export (≥ 50 matches)
✅ **Frontend:** Retrain button added to Jackpot Validation page
✅ **UI Location:** "Export Validation Data to Training" card, right side

**Result:** Models now automatically improve based on your actual prediction performance! 🎉

