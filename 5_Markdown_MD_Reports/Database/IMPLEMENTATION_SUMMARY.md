# Implementation Summary: Validation Export & Calibration Data Storage

## Overview

This document summarizes the implementation of:
1. **Team Features Importance** - Documentation explaining how team features relate to predictions
2. **Validation Results Export Endpoint** - Backend endpoint to store validation metrics
3. **Calibration Data Storage** - Automatic storage of calibration curves during training

---

## 1. Team Features Importance ✅

### Document Created
**File:** `5_Markdown_MD_Reports/Database/TEAM_FEATURES_IMPORTANCE.md`

### Key Points:
- **Current Status:** Team features are **NOT directly used** in Dixon-Coles predictions
- **Why Important:**
  - **Explainability** - Help users understand predictions
  - **Context** - Provide additional information about teams
  - **Future Models** - Foundation for advanced ML models
  - **Confidence Indicators** - Help assess prediction reliability

### Use Cases:
1. **Explainability Dashboard** - Show why predictions were made
2. **Form-Based Adjustments** - Future enhancement to boost probabilities for teams in good form
3. **Fatigue Modeling** - Future enhancement to adjust based on rest days

---

## 2. Validation Results Export Endpoint ✅

### Endpoint Implemented
**Route:** `POST /api/probabilities/validation/export`  
**File:** `2_Backend_Football_Probability_Engine/app/api/probabilities.py` (lines 352-585)

### Functionality:
- Accepts list of validation IDs in format `"savedResultId-setId"` (e.g., `["2-B", "3-A"]`)
- Loads saved probability results from database
- Re-calculates probabilities for the jackpot to get accurate set probabilities
- Calculates metrics:
  - **Accuracy** - Percentage of correct predictions
  - **Brier Score** - Probability calibration metric
  - **Log Loss** - Multi-class log loss
  - **Outcome Breakdown** - Home/Draw/Away correct/total counts
- Stores results in `validation_results` table
- Marks as `exported_to_training = TRUE`

### Example Request:
```json
{
  "validation_ids": ["2-B", "3-A", "4-C"]
}
```

### Example Response:
```json
{
  "success": true,
  "message": "Successfully exported 3 validation results to training.",
  "data": {
    "exported_count": 3,
    "errors": null
  }
}
```

### Database Storage:
- **Table:** `validation_results`
- **Fields Stored:**
  - `jackpot_id` - Reference to jackpot
  - `set_type` - Which set (A-G) was validated
  - `model_id` - Reference to active model
  - `total_matches`, `correct_predictions`, `accuracy`
  - `brier_score`, `log_loss`
  - `home_correct`, `home_total`, `draw_correct`, `draw_total`, `away_correct`, `away_total`
  - `exported_to_training`, `exported_at`

---

## 3. Calibration Data Storage ✅

### Implementation Location
**File:** `2_Backend_Football_Probability_Engine/app/services/model_training.py` (lines 733-810)

### Functionality:
- During calibration model training, computes calibration curves using `compute_calibration_curve()`
- Stores calibration curve data in `calibration_data` table
- Links calibration data to the trained calibration model
- Stores for each outcome type (H/D/A):
  - **Predicted Probability Buckets** - Bins (0.0, 0.05, 0.10, ..., 1.0)
  - **Observed Frequencies** - Actual frequency in each bucket
  - **Sample Counts** - Number of samples in each bucket

### Database Storage:
- **Table:** `calibration_data`
- **Fields Stored:**
  - `model_id` - Reference to calibration model
  - `league_id` - Optional (currently NULL for global calibration)
  - `outcome_type` - H, D, or A
  - `predicted_prob_bucket` - Probability bin (e.g., 0.05, 0.10, 0.15)
  - `actual_frequency` - Observed frequency in bucket
  - `sample_count` - Number of samples in bucket

### When It Runs:
- Automatically during `train_calibration_model()` execution
- After calibrator is fitted on training data
- Before model is committed to database
- Stores 20 bins per outcome type (H/D/A) = 60 total calibration data entries per model

---

## Testing

### Validation Export Endpoint:
1. Save probability results with actual outcomes in "Probability Output" page
2. Navigate to "Jackpot Validation" page
3. Click "Export Selected" or "Export All to Training"
4. Check `validation_results` table for new entries

### Calibration Data Storage:
1. Train a calibration model via API or UI
2. Check `calibration_data` table for entries linked to the new model
3. Verify 60 entries (20 bins × 3 outcomes) per calibration model

---

## Related Files

### Backend:
- `2_Backend_Football_Probability_Engine/app/api/probabilities.py` - Validation export endpoint
- `2_Backend_Football_Probability_Engine/app/services/model_training.py` - Calibration data storage
- `2_Backend_Football_Probability_Engine/app/db/models.py` - Database models

### Frontend:
- `1_Frontend_Football_Probability_Engine/src/pages/JackpotValidation.tsx` - Export button handlers
- `1_Frontend_Football_Probability_Engine/src/services/api.ts` - API client method

### Documentation:
- `5_Markdown_MD_Reports/Database/TEAM_FEATURES_IMPORTANCE.md` - Team features explanation
- `5_Markdown_MD_Reports/Database/TABLE_POPULATION_GUIDE.md` - Table population guide

---

## Next Steps

### Recommended Enhancements:
1. **Team Features Calculation Service** - Implement automatic calculation of rolling statistics
2. **League-Specific Calibration** - Store calibration curves per league (currently global only)
3. **Validation Analytics** - Use `validation_results` table for analytics dashboard
4. **Calibration Visualization** - Use `calibration_data` table to plot calibration curves

---

## Summary

✅ **Team Features:** Documented importance and use cases  
✅ **Validation Export:** Endpoint implemented and tested  
✅ **Calibration Storage:** Automatic storage during training implemented  

All three components are now functional and ready for use!

