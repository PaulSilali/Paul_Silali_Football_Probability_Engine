# Table Importance Analysis

## Quick Answer

### `team_features` and `league_stats` Tables

**Importance:** ⚠️ **LOW** - Not used by current system

**Impact if empty:** ✅ **NONE** - System works perfectly without them

**Action Required:** ❌ **NONE** - These are optional features that were never implemented

---

## Detailed Analysis

### 1. `team_features` Table

**What It Would Store:**
- Rolling goal statistics (last 5, 10, 20 matches)
- Win rates and form metrics
- Home/away splits
- League position
- Rest days between matches

**Current Usage in Codebase:**
- ❌ **ZERO** - No code references this table
- ❌ No service populates it
- ❌ No queries read from it
- ❌ Not used in probability calculations

**Why It's Not Needed:**
- ✅ **Poisson/Dixon-Coles model** uses team strengths (attack/defense) from training, not rolling stats
- ✅ Team strengths are calculated during model training and stored in `model.model_weights`
- ✅ Form-based features would be redundant - model already captures team quality

**When You'd Need It:**
- Advanced ML models that use form features
- Momentum-based predictions
- Team confidence metrics
- **Not needed for current statistical model**

**Verdict:** 🟢 **SAFE TO IGNORE** - Not critical for system

---

### 2. `league_stats` Table

**What It Would Store:**
- League-level baseline statistics per season
- Home win rate, draw rate, away win rate
- Average goals per match
- Home advantage factor

**Current Usage in Codebase:**
- ❌ **ZERO** - No code references this table
- ❌ No model defined in `app/db/models.py`
- ❌ No service populates it
- ❌ Not used in probability calculations

**Why It's Not Needed:**
- ✅ **Draw priors** are hardcoded in `app/models/draw_prior.py` (LEAGUE_DRAW_PRIORS)
- ✅ **Home advantage** is learned per model, not per league
- ✅ League-specific stats would be nice-to-have but not essential

**When You'd Need It:**
- League-specific draw priors (currently hardcoded)
- League-specific home advantage (currently global)
- League comparison analysis
- **Not needed for current model**

**Verdict:** 🟢 **SAFE TO IGNORE** - Not critical for system

---

## Comparison: What IS Used

### ✅ Tables That ARE Used:

| Table | Used For | Critical? |
|-------|----------|-----------|
| `matches` | Training data, probability calculation | ✅ YES |
| `teams` | Team resolution, team strengths | ✅ YES |
| `leagues` | League filtering, data organization | ✅ YES |
| `models` | Storing trained models | ✅ YES |
| `team_h2h_stats` | Draw eligibility in tickets | ⚠️ OPTIONAL |
| `training_runs` | Training history (currently broken) | ⚠️ NICE-TO-HAVE |

### ❌ Tables That Are NOT Used:

| Table | Status | Impact |
|-------|--------|--------|
| `team_features` | Not implemented | ✅ NONE |
| `league_stats` | Not implemented | ✅ NONE |

---

## System Architecture

### Current Probability Calculation Flow:

```
1. Load team strengths from model.model_weights
   ↓
2. Calculate goal expectations (Poisson)
   ↓
3. Apply Dixon-Coles adjustment
   ↓
4. Temperature scale probabilities
   ↓
5. Blend with market odds (entropy-weighted)
   ↓
6. Apply calibration
   ↓
7. Return probabilities
```

**Notice:** No `team_features` or `league_stats` in this flow!

### Where Features Would Be Used (If Implemented):

**team_features:**
- Would be used in advanced ML models
- Would supplement team strengths with form
- **Not needed for Poisson/Dixon-Coles**

**league_stats:**
- Would replace hardcoded draw priors
- Would provide league-specific baselines
- **Currently using defaults/hardcoded values**

---

## Recommendation

### ✅ Do This:
1. **Fix `training_runs` table** - Should populate (bug fix applied)
2. **Ignore `team_features`** - Not needed for current system
3. **Ignore `league_stats`** - Not needed for current system

### ❌ Don't Worry About:
- Empty `team_features` table
- Empty `league_stats` table
- These tables existing but unused

---

## Summary

| Question | Answer |
|----------|--------|
| **How important is `team_features`?** | ⚠️ **LOW** - Not used at all |
| **How important is `league_stats`?** | ⚠️ **LOW** - Not used at all |
| **Will system break if they're empty?** | ✅ **NO** - System works fine |
| **Should I implement them?** | ⚠️ **OPTIONAL** - Only if you want advanced features |
| **What about `training_runs`?** | ✅ **FIXED** - Will now populate correctly |

**Bottom Line:** `team_features` and `league_stats` are **optional features** that were planned but never implemented. Your system works perfectly without them. The only issue was `training_runs` not populating, which is now fixed.

