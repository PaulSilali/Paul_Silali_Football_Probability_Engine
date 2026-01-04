# Jackpot Probability Computation & Validation Workflow

## 📋 Overview

This document explains the complete workflow for importing jackpot results, computing probabilities, and moving to validation.

---

## 🔄 Complete Workflow

### **Step 1: Import Jackpot Results**

**Location:** Data Ingestion Page → "Jackpot Results" Tab

**Input Format:**
```csv
Match,HomeTeam,AwayTeam,Result
1,Rotherham,Peterborough,2
2,Oldham,Chesterfield,X
3,Mansfield,Bradford City,1
...
```

**What Happens:**
1. ✅ User pastes CSV data
2. ✅ System parses CSV and extracts:
   - Match numbers
   - Home team names
   - Away team names
   - Actual results (1/X/2 or H/D/A)
3. ✅ **Automatically creates jackpot** with fixtures
4. ✅ Saves to `saved_probability_results` table with:
   - `jackpot_id`: Auto-generated (e.g., `JK-1735123456`)
   - `actual_results`: `{"1": "2", "2": "X", "3": "1", ...}`
   - `selections`: Placeholder selections for Set A
   - `total_fixtures`: Number of matches

**Status:** `"imported"` (has actual results, no probabilities computed yet)

---

### **Step 2: Compute Probabilities**

**Location:** Data Ingestion Page → "Jackpot Results" Tab → "Compute" Button

**What Happens:**
1. ✅ System checks if jackpot exists (should exist from Step 1)
2. ✅ Calls `/api/probabilities/{jackpot_id}/probabilities`
3. ✅ Model calculates probabilities for all sets (A-G):
   - Poisson/Dixon-Coles base probabilities
   - Draw structural adjustments (League Priors, Elo, H2H, Weather, etc.)
   - Temperature scaling
   - Odds blending (if market odds available)
   - Calibration (if calibration model exists)
4. ✅ Generates selections for each set based on highest probability
5. ✅ Updates `saved_probability_results` with:
   - `selections`: `{"A": {"1": "1", "2": "X", ...}, "B": {...}, ...}`
   - `scores`: Calculated after validation

**Status:** `"probabilities_computed"` (probabilities calculated, ready for validation)

---

### **Step 3: View Validation**

**Location:** Data Ingestion Page → "Jackpot Results" Tab → "View Validation" Button

**OR**

**Location:** Jackpot Validation Page (`/jackpot-validation`)

**What Happens:**
1. ✅ Loads saved results with actual outcomes
2. ✅ Loads computed probabilities for the jackpot
3. ✅ Compares predictions vs actual results for each set (A-G)
4. ✅ Calculates metrics:
   - **Accuracy**: `correct_predictions / total_matches`
   - **Brier Score**: Average squared error
   - **Log Loss**: Average negative log-likelihood
   - **Per-outcome breakdown**: Home/Draw/Away accuracy
5. ✅ Displays:
   - Per-match comparison table
   - Performance metrics per set
   - Analytics charts (trends, outcome breakdown, confidence vs accuracy)
   - Set comparison

**Status:** `"validated"` (has actual results AND scores calculated)

---

### **Step 4: Export to Training (Optional)**

**Location:** Jackpot Validation Page → "Export to Training" Button

**What Happens:**
1. ✅ Exports validation data to `validation_results` table
2. ✅ Stores metrics per set:
   - `total_matches`
   - `correct_predictions`
   - `accuracy`
   - `brier_score`
   - `log_loss`
   - `home_correct`, `home_total`
   - `draw_correct`, `draw_total`
   - `away_correct`, `away_total`
3. ✅ Marks as `exported_to_training = TRUE`
4. ✅ Can be used for:
   - Model retraining
   - Calibration improvement
   - Performance tracking

---

## 🎯 UI Features

### **Data Ingestion Page**

**"Imported Jackpots" Table:**
- **Jackpot ID**: Auto-generated ID
- **Date**: Import date
- **Matches**: Number of fixtures
- **Status**: 
  - `Pending`: No actual results
  - `Imported`: Has actual results, no probabilities
  - `Probabilities Computed`: Probabilities calculated
  - `Validated`: Has scores/metrics
- **Correct**: `correct/total` (if validated)
- **Actions**:
  - **"Compute"** button: Compute probabilities (if not computed)
  - **"View Validation"** button: Navigate to validation page (if computed)

**"Validation Flow" Alert:**
- Link to navigate directly to Jackpot Validation page

---

### **Jackpot Validation Page**

**Features:**
- **Jackpot Selector**: Dropdown to select jackpot
- **Set Selector**: Filter by probability set (A-G)
- **Aggregate Mode**: View all jackpots or selected one
- **Metrics Display**:
  - Accuracy percentage
  - Brier Score
  - Log Loss
  - Correct predictions count
- **Analytics Charts**:
  - Performance trend over time
  - Outcome breakdown (predicted vs actual)
  - Confidence vs accuracy
  - Set comparison
- **Export Options**:
  - Export selected validation
  - Export all validations

---

## 📊 Database Tables

### **`jackpots`**
- Stores jackpot metadata
- Created automatically during import

### **`jackpot_fixtures`**
- Stores fixtures for each jackpot
- Links to `jackpots.id`
- Contains: `home_team`, `away_team`, `odds_home`, `odds_draw`, `odds_away`

### **`saved_probability_results`**
- Stores imported results and computed selections
- Fields:
  - `jackpot_id`: Reference to jackpot
  - `actual_results`: `{"1": "X", "2": "1", ...}`
  - `selections`: `{"A": {"1": "1", ...}, "B": {...}, ...}`
  - `scores`: `{"A": {"correct": 10, "total": 15}, ...}`

### **`validation_results`**
- Stores exported validation metrics
- Fields:
  - `jackpot_id`: Reference to jackpot
  - `set_type`: Probability set (A-G)
  - `total_matches`, `correct_predictions`, `accuracy`
  - `brier_score`, `log_loss`
  - `home_correct`, `draw_correct`, `away_correct`
  - `exported_to_training`: Boolean flag

---

## 🔧 API Endpoints

### **Import Results**
```
POST /api/probabilities/{jackpot_id}/save-result
Body: {
  name: string,
  description: string,
  selections: Record<string, Record<string, string>>,
  actual_results: Record<string, string>
}
```

### **Create Jackpot**
```
POST /api/jackpots
Body: {
  fixtures: Array<{
    id: string,
    homeTeam: string,
    awayTeam: string,
    odds: {home: number, draw: number, away: number}
  }>
}
Response: {
  id: string,  // Auto-generated jackpot_id
  fixtures: [...],
  createdAt: string
}
```

### **Compute Probabilities**
```
GET /api/probabilities/{jackpot_id}/probabilities
Response: {
  probabilitySets: {
    A: Array<{homeWinProbability, drawProbability, awayWinProbability}>,
    B: [...],
    ...
  },
  fixtures: [...]
}
```

### **Get Imported Jackpots**
```
GET /api/probabilities/imported-jackpots
Response: {
  jackpots: Array<{
    id: string,
    jackpotId: string,
    date: string,
    matches: number,
    status: 'pending' | 'imported' | 'validated',
    correctPredictions?: number
  }>
}
```

### **Export Validation**
```
POST /api/probabilities/validation/export
Body: {
  validation_ids: string[]  // Format: "savedResultId-setId"
}
```

---

## ✅ Status Flow

```
Import Results
    ↓
Status: "imported"
    ↓
Compute Probabilities
    ↓
Status: "probabilities_computed"
    ↓
View Validation (scores calculated)
    ↓
Status: "validated"
    ↓
Export to Training (optional)
    ↓
exported_to_training = TRUE
```

---

## 🎯 Key Points

1. **Automatic Jackpot Creation**: When importing results, the system automatically creates the jackpot and fixtures, so you don't need to create them separately.

2. **Team Names Preserved**: Team names from CSV are stored in `jackpot_fixtures`, so probabilities can be computed correctly.

3. **Multiple Sets**: Probabilities are computed for all sets (A-G), allowing comparison of different strategies.

4. **Validation Metrics**: After computing probabilities, you can view detailed validation metrics comparing predictions vs actual results.

5. **Export for Training**: Validation data can be exported to improve model calibration and performance.

---

## 🚀 Next Steps

After completing validation:

1. **Review Performance**: Check which probability set performed best
2. **Export to Training**: Export validation data for model improvement
3. **Retrain Calibration**: Use exported data to retrain calibration model
4. **Iterate**: Import more jackpot results and repeat the process

---

## 📝 Notes

- **Jackpot ID Format**: Auto-generated as `JK-{timestamp}` (e.g., `JK-1735123456`)
- **Result Format**: Accepts both `1/X/2` and `H/D/A`, converts to `1/X/2` internally
- **Selections**: Generated automatically based on highest probability, but can be manually adjusted
- **Scores**: Calculated automatically when viewing validation page

