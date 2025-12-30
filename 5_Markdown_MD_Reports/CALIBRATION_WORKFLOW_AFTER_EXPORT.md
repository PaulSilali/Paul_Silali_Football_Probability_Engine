# Calibration Workflow After Exporting Validation Data

## 📋 Overview

After exporting validation data to training, the **calibration model needs to be retrained** to incorporate the new validation results. This document explains the complete workflow.

---

## 🔄 Current State After Export

When you click **"Export All to Training"** or **"Export Selected"**:

1. ✅ **Validation data is stored** in `validation_results` table
2. ✅ **Metrics are calculated** (accuracy, Brier score, log loss)
3. ✅ **Marked as exported** (`exported_to_training = TRUE`)
4. ⚠️ **BUT**: The calibration model is **NOT automatically retrained**

---

## 🎯 What Happens Next: Manual Retraining Required

### **Important**: The calibration model does **NOT** automatically use exported validation results.

The current `train_calibration_model()` function uses:
- **Historical `Match` data** from the database
- **Re-calculates predictions** using the base model (Blending/Poisson)
- **Uses actual match outcomes** from `Match.home_goals` and `Match.away_goals`

It does **NOT** currently use:
- ❌ `validation_results` table data
- ❌ Exported validation predictions

---

## 📊 Step-by-Step Workflow

### **Step 1: Export Validation Data** ✅ (Already Done)

You've already completed this:
- Clicked "Export All to Training" or "Export Selected"
- Data stored in `validation_results` table
- `exported_to_training = TRUE`

### **Step 2: Retrain Calibration Model** 🔄 (Required)

**Option A: Via ML Training Page (Recommended)**

1. Navigate to **"ML Training"** page
2. Find the **"Calibration Model"** card
3. Click **"Train Model"** button
4. The system will:
   - Load the active Blending model (or Poisson if no Blending exists)
   - Load historical matches from database
   - Re-calculate predictions using the base model
   - Fit isotonic regression on predictions vs actual outcomes
   - Store calibration curves in `calibration_data` table
   - Create a new active calibration model

**Option B: Via API**

```bash
POST /api/model/train
Content-Type: application/json

{
  "modelType": "calibration",
  "baseModelId": null  // Uses active blending model automatically
}
```

**Option C: Via Full Pipeline Training**

1. Navigate to **"ML Training"** page
2. Click **"Train Full Pipeline"** button
3. This trains: Poisson → Blending → Calibration (in sequence)

---

## 🔍 How Calibration Model Gets Used

### **During Prediction Calculation**

When you click **"Compute Probabilities"** on the Probability Output page:

1. **Load Active Calibration Model**
   - System finds the active `calibration` model
   - Loads calibration curves from `calibration_data` table

2. **Calculate Base Probabilities**
   - Uses Poisson model (team strengths)
   - Applies Dixon-Coles correlation adjustment
   - Blends with market odds (if blending model exists)

3. **Apply Calibration**
   - For each outcome (H/D/A):
     - Takes raw probability (e.g., 0.45 for Home)
     - Applies isotonic regression transformation
     - Gets calibrated probability (e.g., 0.48)
   - Renormalizes so probabilities sum to 1.0

4. **Return Calibrated Probabilities**
   - These are the final probabilities shown in the UI
   - Used for all probability sets (A-G)

### **Code Flow**

```
calculate_probabilities() 
  → Load active calibration model
  → Load calibration curves from calibration_data table
  → Calculate base probabilities (Poisson/Blending)
  → Apply calibrator.calibrate_probabilities()
  → Return calibrated probabilities
```

---

## 📈 When to Retrain Calibration

### **Recommended Frequency**

- **After exporting validation data**: Retrain to incorporate new validation results
- **Monthly**: Regular recalibration to account for model drift
- **After significant changes**: New teams, league structure changes, etc.

### **Trigger Conditions**

Retrain calibration if:
1. ✅ You've exported new validation results
2. ✅ Brier score > 0.20 (poor calibration)
3. ✅ Accuracy < 40% consistently
4. ✅ Significant time has passed since last training (>1 month)
5. ✅ Model performance has degraded

---

## 🔧 Current Limitation & Future Enhancement

### **Current Behavior**

The `train_calibration_model()` function:
- Uses historical `Match` data from database
- Re-calculates predictions using the base model
- Does **NOT** use exported `validation_results` directly

### **Why This Works**

Even though it doesn't use `validation_results` directly:
- The exported validation data helps you **track model performance**
- When you retrain, the system uses **all historical matches** (including recent ones)
- The calibration model learns from the **full historical dataset**
- Recent matches (that you validated) are included in the training data

### **Future Enhancement (Optional)**

To directly use exported validation results:
1. Modify `train_calibration_model()` to:
   - Load `validation_results` where `exported_to_training = TRUE`
   - Extract individual prediction/outcome pairs
   - Use these pairs in addition to historical matches
2. This would require storing individual predictions in `validation_results` or a separate table

---

## ✅ Complete Workflow Summary

```
1. User enters actual results → Saved in saved_probability_results
2. User clicks "Export All to Training" → Stored in validation_results
3. User retrains calibration model → Uses historical Match data
4. New calibration model becomes active → Used in future predictions
5. Next prediction calculation → Uses new calibrated probabilities
```

---

## 🎯 Action Items

**To use your exported validation data:**

1. ✅ **Export completed** (you've done this)
2. 🔄 **Retrain calibration model**:
   - Go to "ML Training" page
   - Click "Train Model" on Calibration Model card
   - OR click "Train Full Pipeline" to retrain everything
3. ✅ **Verify calibration is active**:
   - Check "ML Training" page → Training History
   - Look for latest calibration model with status "Active"
4. ✅ **Test predictions**:
   - Go to "Probability Output" page
   - Click "Compute Probabilities"
   - New predictions will use the retrained calibration model

---

## 📝 Notes

- **Calibration data** (`calibration_data` table) is stored **during calibration training**, not during export
- **Validation results** (`validation_results` table) are for **tracking performance**, not direct calibration training
- The calibration model learns from **all historical matches**, which includes the matches you validated
- Retraining is **manual** - the system doesn't auto-retrain after export

---

## 🔗 Related Files

- **Calibration Training**: `2_Backend_Football_Probability_Engine/app/services/model_training.py` (line 531)
- **Calibration Application**: `2_Backend_Football_Probability_Engine/app/api/probabilities.py` (line ~300)
- **Calibration Model**: `2_Backend_Football_Probability_Engine/app/models/calibration.py`
- **Export Endpoint**: `2_Backend_Football_Probability_Engine/app/api/probabilities.py` (line 646)

