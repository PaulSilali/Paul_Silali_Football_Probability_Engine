# Draw Model Implementation

## Overview

This document describes the implementation of a dedicated draw-focused probability model, as specified in the architectural requirements. The draw model provides explicit, auditable draw probability estimation separate from home/away win probabilities.

## Implementation Summary

### 1. Core Draw Model Module (`app/models/draw_model.py`)

**Purpose**: Dedicated module for computing P(Draw) only, using Poisson, Dixon-Coles, and market signals.

**Key Components**:
- `poisson_draw_probability()`: Independent Poisson draw probability
- `dixon_coles_draw_probability()`: Dixon-Coles adjusted draw with low-score correlation
- `market_implied_draw_probability()`: Market-implied draw signal
- `compute_draw_probability()`: Blended final draw probability with safety bounds
- `reconcile_with_draw()`: Redistributes home/away probabilities after draw is fixed

**Configuration**:
- Default weights: 55% Poisson, 30% Dixon-Coles, 15% Market
- Safety bounds: 18% ≤ P(Draw) ≤ 38%

### 2. Database Migration (`migrations/add_draw_model_support.sql`)

**Changes**:
- Adds support for `model_type='draw'` in the models table
- Creates index for faster draw model lookup
- Adds documentation comments

### 3. Probability Calculation Integration

**Modified Files**:
- `app/models/probability_sets.py`: Updated `generate_all_probability_sets()` to accept draw model parameters
- `app/api/probabilities.py`: Integrated draw model into probability calculation pipeline

**Flow**:
1. Calculate base probabilities using Dixon-Coles
2. Extract lambda_home and lambda_away from model
3. Compute draw probability using dedicated draw model
4. Reconcile home/away probabilities to ensure sum-to-one
5. Store draw components for explainability

### 4. Draw-Only Calibration Support

**Added to `app/services/model_training.py`**:
- `train_draw_calibration_model()`: Trains isotonic regression for draw-only calibration
- Uses existing `Calibrator` class with `fit_draw_only()` method

**Added to `app/models/calibration.py`**:
- `fit_draw_only()`: Convenience method for draw-only calibration

### 5. Prediction Model Updates

**Modified `app/db/models.py`**:
- Added `draw_components` JSONB column to `Prediction` model
- Stores: `{"poisson": 0.25, "dixon_coles": 0.27, "market": 0.26}`

### 6. Frontend Updates

**Modified Files**:
- `src/pages/ProbabilityOutput.tsx`: Added draw pressure indicators
- `src/types/index.ts`: Added `drawComponents` to `FixtureProbability` interface

**Features**:
- Draw pressure indicator (⚡) when home ≈ away and draw > 25%
- Tooltip showing draw components breakdown
- Message: "High structural draw likelihood (goal symmetry)"

## Mathematical Interpretation

### When Home ≈ Away Probabilities

**Meaning**: When `|P(Home) - P(Away)| < 5%` and `P(Draw) > 25%`:

1. **Goal symmetry**: Expected goals are approximately equal (λ_home ≈ λ_away)
2. **Draw concentration**: Probability mass concentrates on 0-0, 1-1, 2-2 scores
3. **Structural draw likelihood**: This is not uncertainty, but structural symmetry

**This is exactly where jackpots are won or lost.**

## Usage

### Backend

The draw model is automatically used when:
- Market odds are available
- Lambda values (expected goals) are computed
- `use_draw_model=True` (default) in `generate_all_probability_sets()`

### Frontend

Draw pressure indicators automatically appear when:
- Home and away probabilities are within 5% of each other
- Draw probability exceeds 25%
- Draw components are available in the API response

## Benefits

1. **Improved Calibration**: Draw probabilities are explicitly modeled and calibrated
2. **Explainability**: Draw components (Poisson, Dixon-Coles, Market) are visible
3. **Reduced Bias**: Draw probability is not treated as residual of home/away
4. **Jackpot Stability**: Hard bounds prevent draw inflation/deflation
5. **Auditability**: Full trace of draw probability computation

## Next Steps

1. **Train Draw Model**: Create initial draw model entry in database
2. **Train Draw Calibration**: Run `train_draw_calibration_model()` with historical data
3. **Monitor Performance**: Track draw calibration metrics over time
4. **Frontend Enhancements**: Add draw-specific reliability charts

## Files Modified

### Backend
- `app/models/draw_model.py` (NEW)
- `app/models/probability_sets.py`
- `app/api/probabilities.py`
- `app/services/model_training.py`
- `app/models/calibration.py`
- `app/db/models.py`

### Database
- `migrations/add_draw_model_support.sql` (NEW)

### Frontend
- `src/pages/ProbabilityOutput.tsx`
- `src/types/index.ts`

## Testing

To verify the implementation:

1. **Backend**: Check that draw components are included in API responses
2. **Frontend**: Verify draw pressure indicators appear for symmetric matches
3. **Database**: Confirm `draw_components` column exists in `predictions` table
4. **Calibration**: Run draw-only calibration and verify model creation

## Notes

- The draw model does NOT retrain Poisson/Dixon-Coles models
- Draw probability is computed at inference time, not stored in base models
- Draw components are stored for explainability, not used in training
- Market odds are treated as a signal, never an oracle

