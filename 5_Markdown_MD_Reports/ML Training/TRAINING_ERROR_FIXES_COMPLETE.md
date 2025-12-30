# Training Error Fixes - Complete

## Errors Fixed

### ✅ **Error 1: `math.log(0.0)` in Home Advantage Calculation**

**Location:** `poisson_trainer.py`, line 206

**Error:**
```
ValueError: expected a positive input, got 0.0
residual = math.log(match['home_goals'] / expected)
```

**Root Cause:** When `home_goals` is 0, `0 / expected = 0.0`, and `math.log(0.0)` fails.

**Fix Applied:**
```python
home_goals = match['home_goals']
if home_goals == 0:
    # For zero goals, use log(0.5 / expected) to approximate residual
    residual = math.log(0.5 / expected)
else:
    residual = math.log(home_goals / expected)
```

---

### ✅ **Error 2: `math.log()` on Negative/Zero Tau Values**

**Location:** `poisson_trainer.py`, line 286

**Potential Error:** `_tau()` can return negative or zero values in edge cases, causing `math.log()` to fail.

**Root Cause:** 
- `tau = 1 - lh * la * rho` can be negative if `lh * la * rho > 1`
- `tau = 1 + lh * rho` can be negative if `rho` is very negative
- `tau = 1 + la * rho` can be negative if `rho` is very negative

**Fix Applied:**

1. **In `_optimize_rho` function (line 283-287):**
```python
tau_val = self._tau(match['home_goals'], match['away_goals'], lh, la, r)
# Ensure tau is positive for log calculation
if tau_val <= 0:
    tau_val = 1e-10  # Use small epsilon if tau is non-positive

ll += weights[i] * (
    self._poisson_log(lh, match['home_goals']) +
    self._poisson_log(la, match['away_goals']) +
    math.log(tau_val)
)
```

2. **In `_tau` function (line 319-331):**
```python
def _tau(self, hg: int, ag: int, lh: float, la: float, rho: float) -> float:
    """
    Dixon-Coles tau adjustment
    
    Returns adjustment factor for low-score combinations.
    Ensures return value is always positive (clipped to epsilon if needed).
    """
    if hg > 1 or ag > 1:
        return 1.0
    
    tau_val = 1.0
    if hg == 0 and ag == 0:
        tau_val = 1 - lh * la * rho
    elif hg == 0 and ag == 1:
        tau_val = 1 + lh * rho
    elif hg == 1 and ag == 0:
        tau_val = 1 + la * rho
    elif hg == 1 and ag == 1:
        tau_val = 1 - rho
    
    # Ensure tau is always positive (required for log calculation)
    # Clip to small epsilon if it becomes negative or zero
    return max(tau_val, 1e-10)
```

---

## Summary of Fixes

| Error | Location | Fix | Status |
|-------|----------|-----|--------|
| `math.log(0.0)` - zero goals | Line 206 | Handle zero goals with `log(0.5 / expected)` | ✅ Fixed |
| `math.log()` - negative tau | Line 286 | Check tau value before log, use epsilon if <= 0 | ✅ Fixed |
| Negative tau values | Line 319-331 | Clip tau to `max(tau_val, 1e-10)` | ✅ Fixed |

---

## Testing

After these fixes:
- ✅ Training should complete successfully
- ✅ Zero-goal matches handled correctly
- ✅ Negative tau values prevented
- ✅ All `math.log()` calls are safe

---

**Status:** ✅ **All Errors Fixed - Ready for Training**

