# Timestamp Tracking Logs - Implementation Guide

## Overview

Comprehensive logging has been added to track timestamp updates throughout the training and display pipeline. This helps diagnose when timestamps don't update correctly after retraining.

## Logging Points

### 1. **Backend - Training Completion** ✅

**Location:** `app/services/model_training.py`

**When:** Model training completes successfully

**Logs:**
- Training completion time (UTC and Local)
- Model version and ID
- Temperature learned (for Poisson/Blending)
- Final model status with stored timestamp
- Temperature in model_weights

**Example Log Output:**
```
=== POISSON MODEL TRAINING COMPLETION ===
Training completed at UTC: 2026-01-01T13:49:00.123456
Training completed at Local: 2026-01-01T14:49:00.123456
Model version: poisson-20260101-134900
Temperature learned: 1.250
Temperature Log Loss: 1.185
Model created with ID: 42
Model training_completed_at stored: 2026-01-01T13:49:00.123456
=== POISSON MODEL TRAINING FINAL STATUS ===
Model ID: 42
Model version: poisson-20260101-134900
Status: active
training_completed_at (UTC): 2026-01-01T13:49:00.123456
Training run completed_at (UTC): 2026-01-01T13:49:00.123456
Metrics - Brier: 0.8050, Log Loss: 1.4260
Temperature in model_weights: 1.25
```

### 2. **Backend - Model Status API** ✅

**Location:** `app/api/model.py` - `get_model_status()`

**When:** Frontend requests model status

**Logs:**
- Request time (UTC and Local)
- Which models were found (Poisson, Blending, Calibration)
- Model IDs and versions
- training_completed_at timestamps (UTC and Local)
- What timestamps are being sent in response

**Example Log Output:**
```
=== GET MODEL STATUS REQUEST ===
Request time (UTC): 2026-01-01T13:50:00.123456
Request time (Local): 2026-01-01T14:50:00.123456
Poisson model found: poisson-20260101-134900
  - ID: 42
  - training_completed_at (UTC): 2026-01-01T13:49:00.123456
  - training_completed_at (Local): 2026-01-01T14:49:00.123456
Blending model found: blending-20260101-134900
  - ID: 43
  - training_completed_at (UTC): 2026-01-01T13:49:30.123456
  - training_completed_at (Local): 2026-01-01T14:49:30.123456
Poisson trainedAt in response: 2026-01-01T13:49:00.123456
Blending trainedAt in response: 2026-01-01T13:49:30.123456
=== MODEL STATUS RESPONSE SENT ===
```

### 3. **Frontend - Model Status Loading** ✅

**Location:** `1_Frontend_Football_Probability_Engine/src/pages/MLTraining.tsx` - `loadModelStatus()`

**When:** Frontend loads or refreshes model status

**Logs:**
- When status loading starts
- Response received confirmation
- Raw timestamp from API
- Formatted timestamp for display
- Previous timestamp (to detect changes)
- Whether timestamp changed

**Example Console Output:**
```
[MLTraining] Loading model status from backend...
[MLTraining] Model status response received: {success: true, hasData: true, timestamp: "2026-01-01T13:50:00.123Z"}
[MLTraining] Poisson model timestamp received: {
  raw: "2026-01-01T13:49:00.123456",
  formatted: "Jan 1, 1:49 PM",
  previous: "Jan 1, 10:48 AM",
  changed: true
}
[MLTraining] Model status updated successfully
```

### 4. **Frontend - Timestamp Formatting** ✅

**Location:** `1_Frontend_Football_Probability_Engine/src/pages/MLTraining.tsx` - `formatDateTime()`

**When:** Timestamp is formatted for display

**Logs:**
- Input timestamp string
- Parsed ISO string
- Formatted display string
- Local time representation
- Errors if date parsing fails

**Example Console Output:**
```
[MLTraining] Formatting timestamp: {
  input: "2026-01-01T13:49:00.123456",
  parsed: "2026-01-01T13:49:00.123Z",
  formatted: "Jan 1, 1:49 PM",
  localTime: "1/1/2026, 1:49:00 PM"
}
```

### 5. **Frontend - Training Completion** ✅

**Location:** `1_Frontend_Football_Probability_Engine/src/pages/MLTraining.tsx` - `pollTaskStatus()`

**When:** Training task completes

**Logs:**
- Training completion detected
- Current time when refresh starts
- Model status refresh completion

**Example Console Output:**
```
[MLTraining] Training completed, refreshing model status...
[MLTraining] Current time: 2026-01-01T13:49:00.123Z
[MLTraining] Model status refresh complete
```

## How to Use These Logs

### Step 1: Check Backend Logs

After retraining, check backend logs for:
```
=== POISSON MODEL TRAINING COMPLETION ===
=== BLENDING MODEL TRAINING COMPLETION ===
=== CALIBRATION MODEL TRAINING COMPLETION ===
```

**Verify:**
- ✅ Training completed successfully
- ✅ `training_completed_at` was set correctly
- ✅ Timestamp matches your retraining time (13:49 PM)

### Step 2: Check API Response Logs

When frontend requests status, check for:
```
=== GET MODEL STATUS REQUEST ===
```

**Verify:**
- ✅ Correct models are found
- ✅ `training_completed_at` timestamps are correct
- ✅ Timestamps are sent in API response

### Step 3: Check Frontend Console

Open browser Developer Tools (F12) → Console tab

**Look for:**
```
[MLTraining] Loading model status from backend...
[MLTraining] Poisson model timestamp received: {...}
[MLTraining] Formatting timestamp: {...}
```

**Verify:**
- ✅ Timestamp received from API
- ✅ Timestamp formatted correctly
- ✅ Timestamp changed from previous value

## Troubleshooting Guide

### Issue: Timestamp shows old time after retraining

**Check Logs:**

1. **Backend Training Logs:**
   ```
   === POISSON MODEL TRAINING COMPLETION ===
   Training completed at UTC: [CHECK THIS TIME]
   ```
   - ✅ If time is correct → Training completed successfully
   - ❌ If time is wrong → Training didn't complete or timestamp wasn't set

2. **Backend API Logs:**
   ```
   === GET MODEL STATUS REQUEST ===
   training_completed_at (UTC): [CHECK THIS TIME]
   ```
   - ✅ If time is correct → Backend has correct timestamp
   - ❌ If time is wrong → Database issue or wrong model selected

3. **Frontend Console:**
   ```
   [MLTraining] Poisson model timestamp received: {
     raw: "[CHECK THIS]",
     previous: "[CHECK THIS]",
     changed: [true/false]
   }
   ```
   - ✅ If `raw` is correct but `changed: false` → UI didn't update
   - ❌ If `raw` is wrong → API response issue
   - ❌ If `raw` is null/undefined → Model not found

### Issue: Timestamp format is wrong

**Check Frontend Console:**
```
[MLTraining] Formatting timestamp: {
  input: "[CHECK]",
  formatted: "[CHECK]",
  localTime: "[CHECK]"
}
```

**Common Issues:**
- Timezone mismatch → Check `localTime` vs expected
- Invalid date → Check for parsing errors
- Format wrong → Check `formatted` output

## Log Locations

### Backend Logs
- **File:** Backend console output or log file
- **Format:** Python logging (INFO level)
- **Search for:** `===`, `training_completed_at`, `MODEL TRAINING COMPLETION`

### Frontend Logs
- **Location:** Browser Developer Tools → Console tab
- **Format:** `console.log()` statements
- **Search for:** `[MLTraining]`

## Expected Log Flow

### Successful Training and Display:

1. **Training Completes:**
   ```
   === POISSON MODEL TRAINING COMPLETION ===
   Training completed at UTC: 2026-01-01T13:49:00.123456
   Model training_completed_at stored: 2026-01-01T13:49:00.123456
   ```

2. **Frontend Requests Status:**
   ```
   === GET MODEL STATUS REQUEST ===
   Poisson model found: poisson-20260101-134900
   training_completed_at (UTC): 2026-01-01T13:49:00.123456
   Poisson trainedAt in response: 2026-01-01T13:49:00.123456
   ```

3. **Frontend Receives and Formats:**
   ```
   [MLTraining] Poisson model timestamp received: {
     raw: "2026-01-01T13:49:00.123456",
     formatted: "Jan 1, 1:49 PM",
     changed: true
   }
   ```

4. **UI Displays:**
   ```
   Last: Jan 1, 1:49 PM
   ```

## Summary

With these logs, you can track:
- ✅ When training completes and timestamp is set
- ✅ What timestamp is stored in database
- ✅ What timestamp is sent by API
- ✅ What timestamp is received by frontend
- ✅ How timestamp is formatted
- ✅ Whether timestamp changed from previous value

This makes it easy to identify where in the chain the timestamp update fails.

