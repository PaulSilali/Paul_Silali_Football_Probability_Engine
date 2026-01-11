# Model Retraining Question - ANSWER

**Question:** "Will I need to retrain the models after all these new changes before I test the jackpot games and results?"

**Answer:** ❌ **NO - You do NOT need to retrain models**

---

## Why No Retraining is Needed

### What Changed (Doesn't Affect Models)

1. **Decision Intelligence Layer** ✅
   - **What it is:** Post-generation filtering/validation
   - **Impact on models:** NONE
   - **Why:** Filters tickets AFTER probabilities are calculated

2. **Ticket Archetypes** ✅
   - **What it is:** Constraints on ticket generation
   - **Impact on models:** NONE
   - **Why:** Limits which tickets are generated, doesn't change probabilities

3. **Portfolio Optimization** ✅
   - **What it is:** Selection from generated tickets
   - **Impact on models:** NONE
   - **Why:** Chooses best tickets, doesn't change probability calculations

4. **xG Confidence Propagation** ✅
   - **What it is:** Additional metadata field
   - **Impact on models:** NONE
   - **Why:** Calculated from existing xG values, doesn't change core probabilities

5. **Dixon-Coles Gating** ✅
   - **What it is:** Conditional application of DC adjustment
   - **Impact on models:** MINIMAL
   - **Why:** Still uses same DC formula, just applies conditionally

### What Didn't Change (Core Models)

1. **Probability Calculation Formulas** ❌
   - Dixon-Coles Poisson model: UNCHANGED
   - Probability aggregation: UNCHANGED
   - Calibration: UNCHANGED

2. **Model Training Algorithms** ❌
   - Team strength estimation: UNCHANGED
   - Parameter optimization: UNCHANGED

3. **Team Strength Parameters** ❌
   - Attack/defense ratings: UNCHANGED
   - Home advantage: UNCHANGED

---

## For Historical Backtest

### Current Approach (Recommended)

✅ **Use current models** - They're the same as before

**Why this is acceptable:**
- Probability calculations haven't changed
- Models are still valid for historical matches
- This is a validation test, not a production prediction

**Limitation to note:**
- Models may have been trained on data that includes some of these matches
- This is acceptable for validation (we're testing DI effectiveness, not model accuracy)

### Alternative Approach (If Needed)

If you want to be extra careful:

1. **Use models as they were at the time** (if you have version history)
2. **Retrain excluding these matches** (if you want true out-of-sample)
3. **Use a separate validation set** (if you have one)

**But this is NOT necessary** for validating Decision Intelligence effectiveness.

---

## What the Backtest Actually Tests

The backtest validates:

1. ✅ **Decision Intelligence improves outcomes** (vs baseline)
2. ✅ **Rejected tickets perform worse** (vs accepted)
3. ✅ **Archetypes create distinct behaviors** (per archetype)

It does NOT test:
- ❌ Model accuracy (that's separate)
- ❌ Probability calibration (that's separate)
- ❌ Team strength estimation (that's separate)

---

## Recommendation

**For your historical backtest:**

1. ✅ **Use current models** - No retraining needed
2. ✅ **Note the limitation** - Models may have seen some of these matches
3. ✅ **Focus on DI comparison** - Baseline vs DI, not absolute accuracy
4. ✅ **Document assumptions** - Be transparent about methodology

**After backtest:**

- If results are good → Production deployment
- If results need tuning → Adjust DI thresholds (not models)
- If models need improvement → That's a separate task

---

## Summary

| Component | Changed? | Need Retraining? |
|-----------|----------|------------------|
| Probability Models | ❌ No | ❌ No |
| Decision Intelligence | ✅ Yes | ❌ No (post-generation) |
| Ticket Archetypes | ✅ Yes | ❌ No (constraints) |
| Portfolio Optimization | ✅ Yes | ❌ No (selection) |
| xG Confidence | ✅ Yes | ❌ No (metadata) |
| DC Gating | ✅ Yes | ❌ No (conditional) |

**Final Answer:** ❌ **NO RETRAINING NEEDED**

Proceed with historical backtest using current models.

---

**Last Updated:** 2026-01-11

