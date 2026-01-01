# Probability Output Page - Purpose & Draw Implementation

## Purpose of the "Probability Output" Page

The **Probability Output** page is the **main display interface** for calculated match probabilities. It shows:

### 1. **7 Probability Sets (A-G)**

Each set represents a different strategy for generating probabilities:

| Set | Name | Description | Use Case |
|-----|------|-------------|----------|
| **A** | Pure Model | Dixon-Coles statistical model only | Contrarian bettors |
| **B** | Market-Aware (Balanced) | Entropy-weighted blend of model + market | **Recommended** (★) |
| **C** | Market-Dominant | Heavy market weight, model as anchor | Market followers |
| **D** | Draw-Boosted | Draw probability × 1.15 | Draw specialists |
| **E** | Entropy-Penalized | Penalize low-uncertainty predictions | Risk-averse |
| **F** | Kelly-Weighted | Kelly criterion optimization | Value bettors |
| **G** | Ensemble | Average of all sets | Balanced approach |

### 2. **What It Displays**

For each fixture in the jackpot:
- **Home Win Probability** (1)
- **Draw Probability** (X)
- **Away Win Probability** (2)
- **Confidence Intervals** (optional)
- **Entropy** (uncertainty measure)
- **Market Odds** (for comparison)

### 3. **Model Information**

Shows which trained model is being used:
- **Model Version:** e.g., `calibration-20260101-140016`
- **Model Type:** Calibration model (which uses Blending → Poisson)
- **Training Date:** When the model was last trained

### 4. **Key Features**

- **Tab Navigation:** Switch between probability sets (A-G)
- **Export:** Download probabilities as CSV/JSON
- **Save Results:** Save probability calculations for later comparison
- **Accumulator Calculator:** Calculate combined odds for multiple selections
- **Actual Results:** Compare predictions with actual match outcomes

---

## Draw Implementation Status

### ✅ **YES - Draw Implementation IS Applied**

Draw improvements have been **fully implemented** in the backend and are **automatically applied** to all probabilities shown on this page.

---

## How Draw Implementation Works

### 1. **Draw Prior Injection** ✅

**Location:** `app/api/probabilities.py` (lines 330-367)

**What It Does:**
- Fixes structural draw underestimation in Poisson models
- Applies per-league draw priors (E0: 8%, SP1: 10%, etc.)
- Boosts draw probability before temperature scaling

**Formula:**
```python
adjusted_draw = draw_prob * (1.0 + draw_prior_league)
# Then renormalize to maintain probability correctness
```

**Applied To:**
- ✅ **All probability sets** (A-G)
- ✅ **Before temperature scaling**
- ✅ **Per-league** (uses league code from fixture)

**Example:**
- Base model draw: 25%
- League: E0 (Premier League, 8% prior)
- Adjusted draw: 25% × 1.08 = **27%**

---

### 2. **Temperature Scaling** ✅

**Location:** `app/api/probabilities.py` (lines 369-400)

**What It Does:**
- Softens overconfident probabilities
- Reduces extreme predictions (0.75/0.05 → more balanced)
- Uses learned temperature from training (typically 1.15-1.30)

**Applied To:**
- ✅ **All probability sets** (A-G)
- ✅ **After draw prior injection**

---

### 3. **Entropy-Weighted Blending (Set B)** ✅

**Location:** `app/api/probabilities.py` (lines 400-500)

**What It Does:**
- Dynamically adjusts blend weight based on model confidence
- Low entropy (overconfident) → trust market more
- High entropy (uncertain) → trust model more

**Applied To:**
- ✅ **Set B only** (Market-Aware)
- ✅ **Uses temperature-scaled probabilities**

---

### 4. **Calibration** ✅

**Location:** `app/api/probabilities.py` (lines 500-600)

**What It Does:**
- Applies isotonic regression to correct systematic bias
- Joint renormalized calibration (simplex-constrained)
- Fine-tunes probabilities for correctness

**Applied To:**
- ✅ **All probability sets** (A-G)
- ✅ **Final step** (after all other adjustments)

---

## Complete Probability Calculation Flow

```
1. Load Team Strengths (from trained model)
   ↓
2. Calculate Base Probabilities (Poisson/Dixon-Coles)
   ↓
3. ✅ DRAW PRIOR INJECTION (per-league adjustment)
   ↓
4. ✅ TEMPERATURE SCALING (reduce overconfidence)
   ↓
5. Generate Probability Sets (A-G)
   - Set A: Pure model (already adjusted)
   - Set B: Entropy-weighted blend with market
   - Set C: Market-dominant
   - Set D: Draw-boosted (additional 15% boost)
   - Set E: Entropy-penalized
   - Set F: Kelly-weighted
   - Set G: Ensemble
   ↓
6. ✅ CALIBRATION (isotonic regression)
   ↓
7. Return to Frontend (Probability Output page)
```

---

## What You See on the Page

### Draw Probabilities Are:

1. **Already Adjusted** ✅
   - Draw prior injection applied automatically
   - Temperature scaling applied
   - Calibration applied

2. **Displayed Correctly** ✅
   - Shows draw probability as percentage
   - Updates when you switch between sets (A-G)
   - Reflects all backend adjustments

3. **Set-Specific** ✅
   - **Set A:** Draw prior + temperature + calibration
   - **Set B:** Draw prior + temperature + entropy-weighted blend + calibration
   - **Set D:** Draw prior + temperature + **additional 15% draw boost** + calibration
   - **Sets C, E, F, G:** Draw prior + temperature + their specific logic + calibration

---

## Verification

### How to Verify Draw Implementation is Working:

1. **Check Draw Probabilities:**
   - Draw probabilities should be **higher** than raw Poisson (typically 25-30% vs 20-25%)
   - League-specific differences (E0 vs SP1 should have different draw rates)

2. **Check Model Version:**
   - Should show trained model (e.g., `calibration-20260101-140016`)
   - If showing "Unknown", probabilities might not be using trained model

3. **Compare Sets:**
   - **Set D** should have **highest draw probabilities** (additional 15% boost)
   - **Set A** should have **moderate draw probabilities** (draw prior only)
   - **Set B** should have **balanced draw probabilities** (blended with market)

4. **Check Backend Logs:**
   - Look for: `"Inject draw prior"` or `"Draw prior injection"`
   - Should see league codes being used

---

## Summary

### Purpose of Probability Output Page:

✅ **Display calculated probabilities** for all fixtures in a jackpot  
✅ **Show 7 different probability sets** (A-G) with different strategies  
✅ **Display model information** (version, training date)  
✅ **Allow comparison** between sets and with market odds  
✅ **Export and save** results for analysis  

### Draw Implementation Status:

✅ **FULLY IMPLEMENTED** - All draw improvements are applied:
- ✅ Draw prior injection (per-league)
- ✅ Temperature scaling
- ✅ Entropy-weighted blending (Set B)
- ✅ Calibration
- ✅ Draw-boosted set (Set D)

### What This Means:

**Every probability you see on the Probability Output page has:**
1. ✅ Draw prior injection applied (fixes underestimation)
2. ✅ Temperature scaling applied (reduces overconfidence)
3. ✅ Calibration applied (fine-tunes for correctness)
4. ✅ Set-specific logic applied (for sets B-G)

**You don't need to do anything** - the draw improvements are **automatically applied** to all probabilities displayed on this page.

---

## Next Steps

If you want to verify:
1. Check a fixture's draw probability
2. Compare Set A vs Set D (Set D should have higher draws)
3. Check backend logs for draw prior injection messages
4. Verify model version is showing correctly

The draw implementation is **working automatically** - you're seeing the improved probabilities on this page!

