# Models Folder Usage Analysis

## ✅ **YES - All Files Are Used!**

All files in `app/models/` are actively used in the codebase. They form the core prediction pipeline.

---

## 📁 **File Usage Breakdown**

### **1. `dixon_coles.py` ✅ USED**

**Purpose:** Core Dixon-Coles Poisson model for calculating match probabilities

**Used In:**
- ✅ `app/services/poisson_trainer.py` (line 343)
  - Used for calculating validation metrics during training
  - `calculate_match_probabilities()` function
  
- ✅ `app/api/probabilities.py` (line 10)
  - Main prediction endpoint
  - Generates probabilities for fixtures
  - Uses `TeamStrength`, `DixonColesParams`, `calculate_match_probabilities()`
  
- ✅ `app/api/explainability.py` (line 8)
  - Model explainability endpoints
  - Uses `TeamStrength` dataclass
  
- ✅ `app/models/probability_sets.py` (line 8)
  - Uses `MatchProbabilities` dataclass

**Key Functions Used:**
- `calculate_match_probabilities()` - Main prediction function
- `TeamStrength` - Dataclass for team attack/defense
- `DixonColesParams` - Model parameters (rho, home_advantage)
- `MatchProbabilities` - Result dataclass

---

### **2. `calibration.py` ✅ USED**

**Purpose:** Isotonic regression for probability calibration

**Used In:**
- ✅ `app/api/validation.py` (line 11)
  - Validation endpoints
  - Uses `Calibrator`, `compute_calibration_curve()`, `calculate_brier_score()`, `calculate_log_loss()`

**Key Classes/Functions Used:**
- `Calibrator` - Isotonic regression calibrator
- `compute_calibration_curve()` - Calculate calibration curves
- `calculate_brier_score()` - Brier score metric
- `calculate_log_loss()` - Log loss metric

---

### **3. `probability_sets.py` ✅ USED**

**Purpose:** Generate all 7 probability sets (A-G) from base calculations

**Used In:**
- ✅ `app/api/probabilities.py` (line 13)
  - Main prediction endpoint
  - Uses `generate_all_probability_sets()` and `PROBABILITY_SET_METADATA`

**Key Functions Used:**
- `generate_all_probability_sets()` - Creates all 7 probability sets
- `PROBABILITY_SET_METADATA` - Metadata for frontend display
- `blend_probabilities()` - Blend model and market probabilities
- `odds_to_implied_probabilities()` - Convert odds to probabilities

---

## 🔄 **How They Work Together**

### **Prediction Pipeline:**

```
1. User requests prediction
   ↓
2. app/api/probabilities.py
   ↓
3. Load team strengths from database (trained model)
   ↓
4. dixon_coles.py → calculate_match_probabilities()
   ↓
5. probability_sets.py → generate_all_probability_sets()
   ↓
6. Return 7 probability sets (A-G) to user
```

### **Training Pipeline:**

```
1. Train model
   ↓
2. app/services/poisson_trainer.py
   ↓
3. Estimate team strengths
   ↓
4. dixon_coles.py → calculate_match_probabilities() (for validation)
   ↓
5. calibration.py → calculate_brier_score(), calculate_log_loss()
   ↓
6. Save metrics and weights to database
```

### **Validation Pipeline:**

```
1. Validate model
   ↓
2. app/api/validation.py
   ↓
3. calibration.py → compute_calibration_curve()
   ↓
4. calibration.py → calculate_brier_score(), calculate_log_loss()
   ↓
5. Return validation metrics
```

---

## 📊 **Usage Summary**

| File | Status | Used In | Purpose |
|------|--------|---------|---------|
| **`dixon_coles.py`** | ✅ **ACTIVE** | probabilities.py, poisson_trainer.py, explainability.py, probability_sets.py | Core prediction calculations |
| **`calibration.py`** | ✅ **ACTIVE** | validation.py | Calibration and metrics |
| **`probability_sets.py`** | ✅ **ACTIVE** | probabilities.py | Generate 7 probability sets |

---

## 🎯 **Key Dependencies**

### **`dixon_coles.py` depends on:**
- `numpy` (for calculations)
- Standard library (`math`, `typing`, `dataclasses`)

### **`calibration.py` depends on:**
- `numpy`
- `scikit-learn` (IsotonicRegression, calibration_curve)

### **`probability_sets.py` depends on:**
- `app.models.dixon_coles` (MatchProbabilities)
- Standard library (`math`, `typing`)

---

## ✅ **Conclusion**

**All files in `app/models/` are actively used and essential:**

1. **`dixon_coles.py`** - Core prediction engine ⭐ CRITICAL
2. **`calibration.py`** - Model validation and calibration ⭐ CRITICAL
3. **`probability_sets.py`** - Probability set generation ⭐ CRITICAL

**These files form the mathematical foundation of the prediction system.**

---

**Status:** ✅ **ALL FILES ARE USED AND ESSENTIAL**

