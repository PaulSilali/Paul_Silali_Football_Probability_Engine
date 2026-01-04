# Draw Structural Features - Integration Status & Model Impact

## Overview

This document details which Draw Structural features are integrated into the model pipeline and how they affect each model type.

---

## ✅ Integration Status

### Fully Integrated Features

| Feature | Database Table | Used In | Status |
|---------|---------------|---------|--------|
| **League Priors** | `league_draw_priors` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **H2H Stats** | `h2h_draw_stats` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **Elo Ratings** | `team_elo` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **Weather** | `match_weather`, `match_weather_historical` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **Referee** | `referee_stats` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **Rest Days** | `team_rest_days`, `team_rest_days_historical` | `draw_features.py` → `probabilities.py` | ✅ Active |
| **Odds Movement** | `odds_movement`, `odds_movement_historical` | `draw_features.py` → `probabilities.py` | ✅ Active |

### Not Integrated Features

| Feature | Database Table | Status | Notes |
|---------|---------------|--------|-------|
| **xG Data** | ❌ No table | ❌ Not Integrated | No ingestion or usage implemented |
| **League Structure** | `league_structure` | ⚠️ Data Only | Stored but not used in draw adjustment |

---

## 🎯 Model Impact Analysis

### 1. Poisson / Dixon-Coles Model

**Purpose:** Team strength model for goal expectations

**Training:**
- ❌ **Draw structural features are NOT used during training**
- Training uses only historical match results (goals scored/conceded)
- Team strengths (attack/defense) are learned from match outcomes only

**Inference:**
- ✅ **Draw structural features ARE used AFTER base probabilities are calculated**
- Applied in `probabilities.py` after Poisson/Dixon-Coles base probabilities
- Only adjusts draw probability; home/away probabilities are renormalized proportionally

**Impact:** ⚠️ **Indirect** - Draw structural features modify predictions but don't affect model training

---

### 2. Odds Blending Model

**Purpose:** Learn a global trust weight between model and market

**Training:**
- ❌ **Draw structural features are NOT used during training**
- Training uses only:
  - Model probabilities (from Poisson/Dixon-Coles)
  - Market probabilities (from odds)
  - Historical outcomes

**Inference:**
- ✅ **Draw structural features ARE used AFTER blending**
- Applied in `probabilities.py` after odds blending step
- Blending happens first, then draw structural adjustment

**Impact:** ⚠️ **Indirect** - Draw structural features modify predictions but don't affect blending weights

---

### 3. Calibration Model

**Purpose:** Marginal isotonic calibration for probability correctness

**Training:**
- ❌ **Draw structural features are NOT used during training**
- Training uses only:
  - Base model probabilities (Poisson or Blended)
  - Historical outcomes
  - Calibration curves are learned per outcome type (home/draw/away)

**Inference:**
- ✅ **Draw structural features ARE used AFTER calibration**
- Applied in `probabilities.py` after calibration step
- Calibration happens first, then draw structural adjustment

**Impact:** ⚠️ **Indirect** - Draw structural features modify predictions but don't affect calibration curves

---

### 4. Draw Model

**Purpose:** Dedicated draw probability model with Poisson, Dixon-Coles, and market blending

**Training:**
- ❌ **Draw structural features are NOT used during training**
- Training uses only:
  - Poisson draw probability
  - Dixon-Coles draw probability
  - Market implied draw probability
  - Historical draw outcomes

**Inference:**
- ✅ **Draw structural features ARE used AFTER draw model**
- Applied in `probabilities.py` after draw model calculation
- Draw model provides base draw probability, then structural adjustment is applied

**Impact:** ⚠️ **Indirect** - Draw structural features modify predictions but don't affect draw model weights

---

## 📊 Integration Flow

### Prediction Pipeline (Inference Time)

```
1. Load Team Strengths (from Poisson model)
   ↓
2. Calculate Base Probabilities (Poisson/Dixon-Coles)
   P_home_base, P_draw_base, P_away_base
   ↓
3. [Optional] Odds Blending
   Blend model probabilities with market odds
   ↓
4. [Optional] Calibration
   Apply isotonic calibration curves
   ↓
5. ✅ DRAW STRUCTURAL ADJUSTMENT ← Applied Here
   ├─ League Prior (from league_draw_priors)
   ├─ Elo Symmetry (from team_elo)
   ├─ H2H Factor (from h2h_draw_stats)
   ├─ Weather Factor (from match_weather)
   ├─ Fatigue Factor (from team_rest_days)
   ├─ Referee Factor (from referee_stats)
   └─ Odds Drift Factor (from odds_movement)
   
   Multiplier = league_prior × elo_symmetry × h2h_factor × 
                weather_factor × fatigue_factor × referee_factor × 
                odds_drift_factor
   
   P_draw_adj = clip(P_draw_base × multiplier, 0.12, 0.38)
   P_home_adj, P_away_adj = renormalize(P_home_base, P_away_base)
   ↓
6. Temperature Scaling
   Soften probabilities to reduce overconfidence
   ↓
7. Final Probabilities
   P_home_final, P_draw_final, P_away_final
```

### Training Pipeline

```
1. Load Historical Matches
   ↓
2. Estimate Team Strengths (MLE)
   - Uses only: goals scored/conceded, match dates
   - No draw structural features
   ↓
3. Calculate Training Metrics
   - Brier Score, Log Loss, Accuracy
   - Uses only: predicted probabilities vs actual outcomes
   ↓
4. Save Model
   - Team strengths (attack/defense)
   - Model parameters (rho, home_advantage, xi)
   - No draw structural features stored
```

---

## 🔍 Code Locations

### Draw Structural Features Module
**File:** `2_Backend_Football_Probability_Engine/app/features/draw_features.py`

**Key Functions:**
- `compute_draw_components()` - Computes all structural signals
- `adjust_draw_probability()` - Applies draw adjustment with renormalization
- `DrawComponents` - Data class for component storage

### Integration Point
**File:** `2_Backend_Football_Probability_Engine/app/api/probabilities.py`

**Location:** Lines 370-414

```python
# DRAW STRUCTURAL ADJUSTMENT
from app.features.draw_features import compute_draw_components, adjust_draw_probability

draw_components = compute_draw_components(
    db=db,
    fixture_id=fixture_obj.id,
    league_id=getattr(fixture_obj, 'league_id', None),
    home_team_id=getattr(fixture_obj, 'home_team_id', None),
    away_team_id=getattr(fixture_obj, 'away_team_id', None),
    match_date=None
)

p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
    p_home_base=base_probs.home,
    p_draw_base=base_probs.draw,
    p_away_base=base_probs.away,
    draw_multiplier=draw_components.total()
)
```

---

## ⚠️ Important Notes

### 1. Training vs Inference
- **Training:** Draw structural features are **NOT** used during model training
- **Inference:** Draw structural features **ARE** used during prediction
- This means:
  - Model training metrics (Log Loss, Brier Score) don't reflect draw structural adjustments
  - Draw structural features are post-processing adjustments, not learned parameters

### 2. Draw-Only Adjustment
- **Only draw probability is directly modified**
- Home and away probabilities are **never independently boosted or penalized**
- Home/away probabilities change only through **renormalization** to maintain sum = 1.0

### 3. Missing Features
- **xG Data:** Not implemented (no ingestion, no database table, no usage)
- **League Structure:** Data is ingested and stored, but not used in draw adjustment calculations

### 4. Bounds & Safety
- Draw multiplier is bounded: `[0.75, 1.35]`
- Draw probability is bounded: `[0.12, 0.38]`
- All components default to `1.0` (neutral) if data is missing

---

## 📈 Expected Impact

### On Model Performance
- **Training Metrics:** No direct impact (features not used during training)
- **Prediction Quality:** Expected improvement in draw probability accuracy
- **Calibration:** May improve draw probability calibration, but not measured separately

### On Prediction Accuracy
- **Draw Predictions:** Expected improvement (structural signals inform draw likelihood)
- **Home/Away Predictions:** Minimal impact (only renormalization, not direct adjustment)

---

## 🚀 Recommendations

### 1. Integrate xG Data
- Create database table for xG data
- Implement ingestion service
- Add xG factor to `draw_features.py`
- Use xG to inform draw probability (e.g., low xG matches → higher draw probability)

### 2. Use League Structure
- Leverage `league_structure` table data
- Use total teams, relegation zones to inform draw priors
- Consider league competitiveness metrics

### 3. Training Integration (Future)
- Consider using draw structural features during training
- Could improve model calibration
- Would require significant refactoring of training pipeline

### 4. Metrics & Monitoring
- Track draw structural component contributions
- Monitor which features are most impactful
- A/B test with/without draw structural adjustments

---

## ✅ Summary

| Model Type | Training Impact | Inference Impact | Status |
|------------|----------------|------------------|--------|
| **Poisson/Dixon-Coles** | ❌ None | ✅ Post-processing | Active |
| **Odds Blending** | ❌ None | ✅ Post-processing | Active |
| **Calibration** | ❌ None | ✅ Post-processing | Active |
| **Draw Model** | ❌ None | ✅ Post-processing | Active |

**Conclusion:** Draw structural features are **fully integrated at inference time** but **not used during training**. They act as post-processing adjustments to improve draw probability predictions without affecting model training or learned parameters.

