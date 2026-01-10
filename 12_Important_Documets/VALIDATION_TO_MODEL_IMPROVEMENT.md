# Validation to Model Improvement: Current State & Recommendations

## Current State: What Happens After Validation?

### ✅ What Works Now

1. **Backtesting/Validation Process:**
   - Select saved jackpot result with actual outcomes ✅
   - System loads real probabilities calculated for that jackpot ✅
   - Compare predictions against actual outcomes automatically ✅
   - Analyze which probability set performed best ✅

2. **Validation Export:**
   - `/api/probabilities/validation/export` endpoint exists ✅
   - Stores validation results in `ValidationResult` table ✅
   - Calculates accuracy, Brier score, log loss ✅
   - Tracks performance per probability set (A, B, C, etc.) ✅

### ❌ What's Missing: Feedback Loop

**Currently, validation results are NOT automatically used to improve model accuracy.**

## How Models Are Currently Trained

### 1. **Poisson Model Training**
- **Data Source:** Historical matches from `matches` table
- **Method:** Uses actual match results (goals, outcomes)
- **Improvement:** ✅ Automatically improves as more match data is ingested

### 2. **Blending Model Training**
- **Data Source:** Historical matches from `matches` table
- **Method:** Optimizes blend weight (alpha) between Poisson predictions and market odds
- **Improvement:** ✅ Automatically improves as more match data is ingested

### 3. **Calibration Model Training**
- **Data Source:** Historical matches from `matches` table
- **Method:** Fits isotonic regression on model predictions vs actual outcomes
- **Improvement:** ✅ Automatically improves as more match data is ingested
- **❌ Does NOT use:** `ValidationResult` data from validation exports

## The Gap: Validation Results Are Stored But Not Used

### Current Flow:
```
1. User creates jackpot → Calculates probabilities
2. User saves results → Stores in SavedProbabilityResult
3. User enters actual results → Updates SavedProbabilityResult
4. User exports validation → Stores in ValidationResult table
5. ❌ STOP - Validation data is stored but NOT used for training
```

### What Should Happen:
```
1-4. Same as above
5. ✅ Validation data feeds back into calibration training
6. ✅ Model accuracy improves based on real-world predictions
7. ✅ Next jackpot predictions are more accurate
```

---

## Why This Matters

### Current Limitation:
- **Models train on historical match data** (what happened in past matches)
- **But NOT on your actual predictions** (how well your probability sets performed)

### The Problem:
- Historical match data ≠ Your prediction performance
- Your probability sets (A, B, C, etc.) may perform differently than raw model outputs
- Validation results show which sets work best, but models don't learn from this

### Example:
- **Set A** (conservative) might have 70% accuracy
- **Set B** (aggressive) might have 65% accuracy
- **Set C** (balanced) might have 75% accuracy
- **Current system:** Doesn't learn that Set C is best
- **Improved system:** Would adjust calibration to favor Set C's approach

---

## Recommended Solution: Validation-Based Calibration Retraining

### Option 1: Automatic Retraining (Recommended)

**When:** After accumulating N validation results (e.g., 50+ matches)

**How:**
1. Monitor `ValidationResult` table for new exports
2. When threshold reached, trigger calibration retraining
3. Use validation data to improve calibration curves
4. Create new calibration model version
5. Activate new model automatically

**Implementation:**
```python
def train_calibration_from_validation(
    self,
    base_model_id: Optional[int] = None,
    min_validation_matches: int = 50
) -> Dict:
    """
    Retrain calibration model using ValidationResult data.
    
    Uses actual prediction performance from validation exports
    instead of just historical match data.
    """
    # Query ValidationResult table
    validation_results = self.db.query(ValidationResult).filter(
        ValidationResult.exported_to_training == True,
        ValidationResult.model_id == base_model_id
    ).all()
    
    # Extract predictions and actuals from validation data
    # Retrain calibration curves
    # Create new calibration model
```

### Option 2: Manual Retraining Endpoint

**When:** User explicitly requests retraining

**How:**
1. Add endpoint: `POST /api/models/retrain-calibration-from-validation`
2. User selects validation results to include
3. System retrains calibration model
4. User can compare old vs new model performance

**Implementation:**
```python
@router.post("/models/retrain-calibration-from-validation")
async def retrain_calibration_from_validation(
    validation_ids: Optional[List[int]] = None,
    use_all_validation: bool = False,
    db: Session = Depends(get_db)
):
    """
    Retrain calibration model using validation results.
    
    This creates a feedback loop: validation → model improvement → better predictions
    """
```

### Option 3: Hybrid Approach (Best)

**Combine both:**
- **Automatic:** Retrain when threshold reached
- **Manual:** Allow user to trigger retraining anytime
- **Smart:** Weight recent validation results more heavily

---

## Implementation Plan

### Phase 1: Use Validation Data in Calibration Training

**File:** `app/services/model_training.py`

**Changes:**
1. Modify `train_calibration_model()` to optionally use `ValidationResult` data
2. Add parameter: `use_validation_data: bool = False`
3. When enabled, query `ValidationResult` table for prediction/actual pairs
4. Use this data to supplement or replace historical match data

**Benefits:**
- Models learn from your actual prediction performance
- Calibration improves based on real-world results
- Better accuracy for future predictions

### Phase 2: Automatic Retraining Trigger

**File:** `app/services/automated_pipeline.py` or new `app/services/model_improvement.py`

**Changes:**
1. Monitor `ValidationResult` table
2. When new validation exported, check if threshold reached
3. Automatically trigger calibration retraining
4. Compare new model vs old model performance
5. Activate new model if it's better

**Benefits:**
- Continuous improvement without manual intervention
- Models stay up-to-date with latest performance data

### Phase 3: Validation Analytics Dashboard

**File:** New `app/api/validation_analytics.py`

**Features:**
- Show which probability sets perform best
- Track accuracy trends over time
- Compare model versions
- Visualize calibration improvements

**Benefits:**
- User can see impact of validation-based improvements
- Data-driven decision making

---

## Current Workaround: Manual Process

### Until automatic feedback is implemented:

1. **Export Validation Results:**
   ```bash
   POST /api/probabilities/validation/export
   {
     "validation_ids": ["1-A", "2-B", "3-C"]
   }
   ```

2. **Review Validation Performance:**
   - Check `ValidationResult` table for accuracy metrics
   - Identify which probability sets perform best
   - Note patterns (e.g., Set C always best)

3. **Manually Retrain Models:**
   ```bash
   POST /api/models/train/calibration
   {
     "base_model_id": 12,
     "leagues": ["E0", "SP1"],
     "seasons": ["2425"]
   }
   ```

4. **Convert Jackpot Results to Training Data:**
   ```bash
   POST /api/jackpots/{jackpot_id}/convert-to-training-data
   ```
   - This adds jackpot results to `matches` table
   - Next model training will include this data
   - **This is the current way to improve models**

---

## Summary

### Current State:
- ✅ Validation works: You can compare predictions vs actual results
- ✅ Validation export works: Results stored in `ValidationResult` table
- ❌ **No automatic feedback:** Validation data not used to improve models
- ⚠️ **Manual workaround:** Convert jackpot results to matches table

### Recommended Improvement:
- ✅ **Add validation-based calibration retraining**
- ✅ **Automatic retraining when threshold reached**
- ✅ **Manual retraining endpoint for user control**
- ✅ **Analytics dashboard to track improvements**

### Impact:
- **Better accuracy:** Models learn from your actual prediction performance
- **Continuous improvement:** System gets better over time automatically
- **Data-driven:** Decisions based on real-world results, not just historical matches

---

## Next Steps

1. **Short-term:** Use jackpot-to-training-data conversion (already implemented)
2. **Medium-term:** Implement validation-based calibration retraining
3. **Long-term:** Add automatic retraining triggers and analytics dashboard

**Priority:** Medium-High (significantly improves model accuracy over time)

