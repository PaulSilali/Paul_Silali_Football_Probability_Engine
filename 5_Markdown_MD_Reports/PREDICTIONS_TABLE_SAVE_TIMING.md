# Predictions Table - When Is It Saved?

## Quick Answer

**Current Status:** ❌ **NOT AUTOMATICALLY SAVED**

The `predictions` table is **NOT currently being populated** when probabilities are calculated.

---

## Current Implementation

### What Happens When Probabilities Are Calculated

**File:** `app/api/probabilities.py` - `calculate_probabilities()`

**Flow:**
1. ✅ Calculate probabilities for all fixtures
2. ✅ Apply draw prior injection
3. ✅ Apply temperature scaling
4. ✅ Generate all 7 probability sets (A-G)
5. ✅ Apply calibration
6. ✅ Return probabilities to frontend
7. ❌ **DOES NOT save to `predictions` table**

**Current Code:**
- Probabilities are **calculated** but **not stored** in `predictions` table
- Only returned to frontend via API response
- No database writes for `Prediction` records

---

## What Should Happen (But Doesn't Currently)

### Expected Behavior:

When probabilities are calculated, the system should:

1. **For each fixture:**
   - Create 7 `Prediction` records (one per set A-G)
   - Store probabilities, entropy, expected goals
   - Link to fixture and model

2. **Save to database:**
   - Commit all predictions
   - Enable historical tracking
   - Enable backtesting

### What's Missing:

**File:** `app/api/probabilities.py` (around line 550)

**Missing Code:**
```python
# After generating probability_sets, should save to database:
for fixture_idx, fixture_obj in enumerate(fixtures):
    for set_id, probs in probability_sets.items():
        pred = Prediction(
            fixture_id=fixture_obj.id,
            model_id=model.id,
            set_type=PredictionSet[set_id],
            prob_home=probs.home,
            prob_draw=probs.draw,
            prob_away=probs.away,
            predicted_outcome=MatchResult.H if probs.home > max(probs.draw, probs.away) 
                            else MatchResult.D if probs.draw > probs.away 
                            else MatchResult.A,
            confidence=max(probs.home, probs.draw, probs.away),
            entropy=probs.entropy,
            expected_home_goals=probs.lambda_home,
            expected_away_goals=probs.lambda_away,
            # ... other fields
        )
        db.add(pred)

db.commit()  # Commit all predictions
```

---

## What IS Saved

### 1. **SavedProbabilityResult** ✅

**When:** When user clicks "Save Result" button on Probability Output page

**What:** User selections, actual results, scores per set

**Location:** `saved_probability_results` table

**Endpoint:** `POST /api/probabilities/{jackpot_id}/save-result`

**Contains:**
- Selections (user picks per set)
- Actual results (if entered)
- Scores (correct/total per set)
- Model version
- **NOT the raw probabilities**

---

### 2. **ValidationResult** ✅

**When:** When validation is exported to training

**What:** Aggregated metrics (accuracy, Brier Score, Log Loss) per set

**Location:** `validation_results` table

**Endpoint:** `POST /api/probabilities/validation/export`

**Contains:**
- Total matches
- Correct predictions
- Accuracy, Brier Score, Log Loss
- **NOT individual predictions**

---

## Why Predictions Table Is Empty

### Root Cause:

The `predictions` table was designed to store **individual prediction records** for each fixture and set, but:

1. ❌ **No code saves to it** during probability calculation
2. ❌ **Not used by any current feature**
3. ✅ **Table exists** but is **unused**

### Impact:

- ✅ **System works fine** - Probabilities are calculated and returned
- ❌ **No historical tracking** - Can't see past predictions
- ❌ **No backtesting** - Can't compare predictions vs actuals easily
- ❌ **No audit trail** - Can't track what probabilities were generated

---

## Should We Fix This?

### Benefits of Saving Predictions:

1. **Historical Tracking** ✅
   - See what probabilities were generated for past matches
   - Track model performance over time

2. **Backtesting** ✅
   - Compare predictions vs actual results
   - Calculate metrics retrospectively

3. **Audit Trail** ✅
   - Know which model version generated which predictions
   - Track changes in probability outputs

4. **Analysis** ✅
   - Analyze prediction patterns
   - Identify systematic biases

### Drawbacks:

1. **Database Growth** ⚠️
   - 7 predictions per fixture × many fixtures = large table
   - Need cleanup strategy

2. **Performance** ⚠️
   - Additional database writes
   - Slower probability calculation

3. **Complexity** ⚠️
   - More code to maintain
   - More potential for errors

---

## Recommendation

### Option 1: **Save Predictions Automatically** (Recommended)

**When:** Every time probabilities are calculated

**Implementation:**
- Add prediction saving code after probability calculation
- Save all 7 sets (A-G) for each fixture
- Commit in batch for performance

**Pros:**
- ✅ Complete audit trail
- ✅ Enables backtesting
- ✅ Historical tracking

**Cons:**
- ⚠️ Database growth
- ⚠️ Slightly slower API response

---

### Option 2: **Save Predictions On-Demand** (Alternative)

**When:** Only when user explicitly requests it

**Implementation:**
- Add "Save Predictions" button
- Save only when requested
- Optional feature

**Pros:**
- ✅ No performance impact unless used
- ✅ User controls when to save

**Cons:**
- ❌ Easy to forget to save
- ❌ No automatic audit trail

---

### Option 3: **Keep Current Behavior** (Status Quo)

**When:** Never (current state)

**Pros:**
- ✅ Fastest performance
- ✅ No database growth
- ✅ Simpler code

**Cons:**
- ❌ No historical tracking
- ❌ No backtesting capability
- ❌ No audit trail

---

## Summary

| Question | Answer |
|----------|--------|
| **When is predictions table saved?** | ❌ **NEVER** - Currently not implemented |
| **Is it saved automatically?** | ❌ **NO** |
| **Is it saved on user action?** | ❌ **NO** |
| **Should we implement it?** | ⚠️ **OPTIONAL** - Nice to have, not critical |
| **Impact if empty?** | ✅ **NONE** - System works fine without it |

---

## Next Steps

If you want predictions saved:

1. **I can implement automatic saving** (Option 1)
   - Save after probability calculation
   - All 7 sets per fixture
   - Batch commit for performance

2. **Or implement on-demand saving** (Option 2)
   - Add "Save Predictions" button
   - User controls when to save

3. **Or leave as-is** (Option 3)
   - Current behavior (no saving)
   - System works fine

**Current system works without predictions table** - it's designed for historical tracking and backtesting, which are optional features.

