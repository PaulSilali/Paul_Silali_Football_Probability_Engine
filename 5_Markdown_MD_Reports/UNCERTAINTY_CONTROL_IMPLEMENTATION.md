# Uncertainty Control Implementation Summary

## Overview

This document summarizes the implementation of uncertainty control mechanisms to improve Log Loss and prevent overconfidence in probability predictions.

## Components Implemented

### 1. Core Modules

#### `app/models/uncertainty.py`
- **Temperature Scaling**: Softens probabilities to reduce overconfidence
- **Entropy Calculation**: Computes Shannon entropy of distributions
- **Entropy-Weighted Alpha**: Adaptive blending based on model uncertainty

#### `app/models/temperature_optimizer.py`
- **Temperature Learning**: Grid search to find optimal temperature on validation set
- **Safety Constraints**: Temperature clamped to [1.0, 1.5]
- **Validation-Only Learning**: No data leakage

#### `app/services/entropy_monitor.py`
- **Entropy Monitoring**: Tracks entropy drift over time
- **Status Detection**: Warns on entropy collapse
- **Production Monitoring**: Ready for alerting

### 2. Integration Points

#### `app/api/probabilities.py`
- **Temperature Scaling Applied**: Before blending (Set B)
- **Entropy-Weighted Blending**: Replaces fixed alpha
- **Metadata Exposed**: entropy, alphaEffective, temperature in API response

#### `app/services/model_training.py`
- **Poisson Training**: Learns temperature on validation set
- **Blending Training**: Learns temperature on validation set
- **Entropy Tracking**: Collects entropy metrics during training
- **Model Storage**: Temperature stored in model_weights

#### `app/models/probability_sets.py`
- **Blending v2**: Entropy-weighted alpha support
- **Backward Compatible**: Optional parameter (defaults to True)

### 3. Database Changes

#### Migration: `add_entropy_metrics.sql`
- Added columns to `training_runs`:
  - `avg_entropy`: Average normalized entropy
  - `p10_entropy`: 10th percentile
  - `p90_entropy`: 90th percentile
  - `temperature`: Learned temperature parameter
  - `alpha_mean`: Mean effective alpha

#### Model Updates
- `TrainingRun` model updated with new fields
- Indexes created for monitoring queries

## Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Poisson Log Loss | 1.426 | ~1.15-1.20 | ↓ 0.23-0.28 |
| Blending Log Loss | 1.750 | ~1.10-1.15 | ↓ 0.60-0.65 |
| Calibrated Log Loss | ~1.00 | ~0.95-0.98 | ↓ 0.02-0.05 |
| Entropy Collapse | Frequent | Rare | Significant |

## How It Works

### Temperature Scaling

1. **During Training**:
   - Validation predictions collected
   - Grid search finds optimal temperature (1.0-1.4)
   - Temperature stored in model_weights

2. **During Prediction**:
   - Base probabilities from Poisson model
   - Temperature applied: `p' = p^(1/T) / sum(p^(1/T))`
   - Softened probabilities used for blending

### Entropy-Weighted Blending

1. **Calculate Model Entropy**:
   - Normalize entropy to [0, 1]
   - High entropy = uncertain model
   - Low entropy = overconfident model

2. **Adaptive Alpha**:
   - `alpha_eff = clamp(base_alpha * normalized_entropy, 0.15, 0.75)`
   - Low entropy → lower alpha → trust market more
   - High entropy → higher alpha → trust model more

3. **Blend**:
   - `P = alpha_eff * P_model + (1 - alpha_eff) * P_market`

## Usage

### Training

Temperature is automatically learned during model training:

```python
# Poisson training
service.train_poisson_model(leagues=["E0"], seasons=["2324"])

# Blending training
service.train_blending_model(poisson_model_id=123)
```

Temperature is stored in `model.model_weights['temperature']`.

### Prediction

Temperature and entropy-weighted blending are automatically applied:

```python
# API call
GET /api/probabilities/{jackpot_id}/probabilities

# Response includes metadata for Set B:
{
  "setB": {
    "homeWinProbability": 45.2,
    "entropy": 1.523,
    "alphaEffective": 0.42,
    "temperature": 1.25
  }
}
```

## Monitoring

### Entropy Drift

Check entropy status during training:

```python
from app.services.entropy_monitor import summarize_entropy

summary = summarize_entropy(entropies)
# Returns: {
#   "avg_entropy": 0.71,
#   "p10_entropy": 0.45,
#   "p90_entropy": 0.92,
#   "status": "ok"  # or "warning" or "critical"
# }
```

### Alert Rules

- **Warning**: avg_entropy < 0.45
- **Critical**: avg_entropy < 0.35
- **Action**: Disable blending retrain if critical

## Safety Guarantees

1. **Temperature ≥ 1.0**: Never sharpens probabilities
2. **Temperature ≤ 1.5**: Prevents excessive flattening
3. **Alpha ∈ [0.15, 0.75]**: Bounded blending weights
4. **Validation-Only Learning**: No data leakage
5. **Deterministic**: Same inputs → same outputs

## Testing

After implementation, verify:

1. **Temperature Learning**:
   - Check `model.model_weights['temperature']` after training
   - Should be between 1.0 and 1.5

2. **Entropy-Weighted Blending**:
   - Check `alphaEffective` in Set B responses
   - Should vary based on model uncertainty

3. **Log Loss Improvement**:
   - Compare before/after training runs
   - Should see ~0.2-0.6 improvement

## Next Steps

1. **Run Database Migration**:
   ```sql
   \i migrations/add_entropy_metrics.sql
   ```

2. **Retrain Models**:
   - Retrain Poisson model (learns temperature)
   - Retrain Blending model (learns temperature)
   - Retrain Calibration model (uses softened probabilities)

3. **Monitor**:
   - Check entropy metrics in training_runs
   - Set up alerts for entropy collapse
   - Track Log Loss improvements

## Files Modified

- `app/models/uncertainty.py` (NEW)
- `app/models/temperature_optimizer.py` (NEW)
- `app/services/entropy_monitor.py` (NEW)
- `app/api/probabilities.py` (MODIFIED)
- `app/services/model_training.py` (MODIFIED)
- `app/models/probability_sets.py` (MODIFIED)
- `app/db/models.py` (MODIFIED)
- `3_Database_Football_Probability_Engine/migrations/add_entropy_metrics.sql` (NEW)
- `5_Markdown_MD_Reports/PROBABILITY_OUTPUT_CONTRACT_V2.md` (NEW)

## References

- `PROBABILITY_OUTPUT_CONTRACT_V2.md`: Output contract specification
- `BLENDING_AND_CALIBRATION_IMPLEMENTATION.md`: Original blending implementation
- `MODEL_TRAINING_CONTRACT.md`: Training methodology

