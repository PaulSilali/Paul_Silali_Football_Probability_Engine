# Training Error Fix

## Error

```
ValueError: expected a positive input, got 0.0
File: app/services/poisson_trainer.py, line 206
residual = math.log(match['home_goals'] / expected)
```

## Root Cause

When `match['home_goals']` is 0, the calculation `0 / expected = 0.0`, and `math.log(0.0)` raises `ValueError`.

This happens when:
- A match ended 0-0 (draw with no goals)
- A match ended 0-X (away team scored, home team didn't)

## Fix Applied

**File:** `2_Backend_Football_Probability_Engine/app/services/poisson_trainer.py`

**Line 198-212:** Handle zero-goal cases in home advantage calculation

**Before:**
```python
if expected > 0:
    residual = math.log(match['home_goals'] / expected)
    residuals.append(residual)
```

**After:**
```python
if expected > 0:
    home_goals = match['home_goals']
    if home_goals == 0:
        # For zero goals, use log(0.5 / expected) to approximate residual
        # Using 0.5 (half a goal) is more stable than very small epsilon
        residual = math.log(0.5 / expected)
    else:
        residual = math.log(home_goals / expected)
    residuals.append(residual)
```

## Rationale

- **0.5 instead of 1e-10**: More stable and realistic approximation for zero-goal matches
- **Preserves all matches**: Doesn't skip zero-goal matches (which would bias home advantage)
- **Mathematically sound**: `log(0.5 / expected)` approximates the contribution of zero-goal matches

## Testing

After this fix:
- Training should complete successfully
- Home advantage will be estimated correctly even with zero-goal matches
- No more `ValueError` during training

---

**Status:** ✅ **Fixed - Ready for Testing**

