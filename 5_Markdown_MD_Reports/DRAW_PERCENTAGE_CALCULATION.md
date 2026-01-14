# Draw Percentage Calculation - Complete Guide

## Quick Answer

Draw percentage is calculated through **multiple steps**:

1. **Base Calculation**: Sum of all equal scores (0-0, 1-1, 2-2, etc.) from Poisson/Dixon-Coles model
2. **Draw Prior Injection**: Boost by league-specific factor (typically 8-10%)
3. **Temperature Scaling**: Soften overconfident probabilities
4. **Set-Specific Adjustments**: Some sets boost draw further (Set D: +15%)
5. **Calibration**: Final correction via isotonic regression

---

## Step-by-Step Calculation

### Step 1: Base Draw Probability (Dixon-Coles Model)

**File:** `app/models/dixon_coles.py` - `calculate_match_probabilities()`

**Formula:**
```
P(Draw) = Σ P(x, x) for x = 0 to max_goals (typically 8)
```

**What This Means:**
- Calculate probability of each equal score (0-0, 1-1, 2-2, ..., 8-8)
- Sum all equal score probabilities
- This gives the **base draw probability**

**Code:**
```python
prob_draw = 0.0
for h in range(max_goals + 1):  # h = 0 to 8
    for a in range(max_goals + 1):  # a = 0 to 8
        if h == a:  # Equal scores
            prob = score_joint_probability(h, a, lambda_home, lambda_away, rho)
            prob_draw += prob
```

**Example:**
- P(0-0) = 0.08
- P(1-1) = 0.12
- P(2-2) = 0.05
- P(3-3) = 0.01
- ... (higher scores negligible)
- **Base P(Draw) = 0.08 + 0.12 + 0.05 + 0.01 + ... = 0.26 (26%)**

---

### Step 2: Draw Prior Injection (Fix Structural Underestimation)

**File:** `app/models/draw_prior.py` - `inject_draw_prior()`

**Problem:** Poisson models systematically **underestimate** draw probabilities

**Solution:** Inject league-specific draw prior

**Formula:**
```
adjusted_draw = base_draw * (1.0 + draw_prior_league)
```

**League-Specific Priors:**
- **E0 (Premier League):** 8% boost
- **SP1 (La Liga):** 10% boost
- **I1 (Serie A):** 9% boost
- **D1 (Bundesliga):** 7% boost
- **F1 (Ligue 1):** 8% boost
- **Default:** 8% boost

**Example:**
- Base draw: **26%**
- League: E0 (Premier League, 8% prior)
- Adjusted draw: 26% × 1.08 = **28.08%**

**Then Renormalize:**
- Total = Home + Adjusted_Draw + Away
- Final draw = Adjusted_Draw / Total

**Code:**
```python
adjusted_draw = draw_prob * (1.0 + draw_prior)  # E.g., 0.26 * 1.08 = 0.2808
total = home_prob + adjusted_draw + away_prob
final_draw = adjusted_draw / total  # Renormalize
```

---

### Step 3: Temperature Scaling (Reduce Overconfidence)

**File:** `app/models/uncertainty.py` - `temperature_scale()`

**Purpose:** Soften overconfident probabilities

**Formula:**
```
P_i' = P_i^(1/T) / Σ P_j^(1/T)
```

**Where:**
- T = temperature (typically 1.15-1.30, learned from training)
- Lower T = sharper probabilities
- Higher T = softer probabilities

**Effect on Draw:**
- If draw is **underestimated** → temperature scaling **increases** it slightly
- If draw is **overestimated** → temperature scaling **decreases** it slightly
- Generally **preserves relative ordering**

**Example:**
- Before: Home=45%, Draw=28%, Away=27%
- Temperature: 1.2
- After: Home=43%, Draw=29%, Away=28% (slightly more balanced)

---

### Step 4: Set-Specific Adjustments

**File:** `app/models/probability_sets.py` - `generate_all_probability_sets()`

Different probability sets apply different logic:

#### Set A: Pure Model
- Uses draw from Step 3 (draw prior + temperature)
- **No additional adjustment**

#### Set B: Market-Aware (Entropy-Weighted)
- Blends model draw with market draw
- **Formula:**
  ```
  blended_draw = alpha_eff * model_draw + (1 - alpha_eff) * market_draw
  ```
- **alpha_eff** = entropy-weighted (higher entropy → more model weight)

#### Set C: Market-Dominant
- **Heavily weighted toward market**
- Market draw typically **lower** than model draw

#### Set D: Draw-Boosted ⭐
- **Additional 15% boost** on top of adjusted draw
- **Formula:**
  ```
  boosted_draw = min(draw * 1.15, 0.95)  # Cap at 95%
  ```
- **Best for draw coverage**

#### Set E: Entropy-Penalized
- Penalizes low-entropy (overconfident) predictions
- May **reduce** draw if model is too confident

#### Set F: Kelly-Weighted
- Uses Kelly criterion for optimal betting
- Draw adjusted based on expected value

#### Set G: Ensemble
- Averages across multiple sets
- Draw is **average** of other sets

---

### Step 5: Calibration (Final Correction)

**File:** `app/models/calibration.py` - `calibrate_probabilities()`

**Purpose:** Correct systematic bias via isotonic regression

**Method:**
1. **Marginal Calibration**: Calibrate Home, Draw, Away **independently**
2. **Joint Renormalization**: Apply simplex-constrained smoothing
3. **Ensure**: Probabilities sum to 1.0

**Effect on Draw:**
- If model **underestimates** draws → calibration **increases** draw
- If model **overestimates** draws → calibration **decreases** draw
- **Fine-tuning** based on historical performance

**Example:**
- Before calibration: Home=40%, Draw=28%, Away=32%
- After calibration: Home=39%, Draw=29%, Away=32%
- Draw **increased** by 1% (calibration detected underestimation)

---

## Complete Flow Diagram

```
1. Calculate Expected Goals (λ_home, λ_away)
   ↓
2. Base Draw Probability
   P(Draw) = Σ P(x, x) for x = 0 to 8
   Example: 26%
   ↓
3. Draw Prior Injection
   adjusted_draw = 26% × 1.08 = 28.08%
   (League: E0, 8% prior)
   ↓
4. Temperature Scaling
   Soften probabilities (T = 1.2)
   Example: 28.08% → 28.5%
   ↓
5. Set-Specific Adjustment
   - Set A: 28.5% (no change)
   - Set B: Blend with market (e.g., 27%)
   - Set D: 28.5% × 1.15 = 32.8% (boosted)
   ↓
6. Calibration
   Final correction via isotonic regression
   Example: 28.5% → 29.0% (calibrated)
   ↓
7. Final Draw Percentage
   Displayed on Probability Output page
```

---

## Example Calculation

### Match: Arsenal vs Liverpool

**Inputs:**
- λ_home = 1.8 (expected home goals)
- λ_away = 1.6 (expected away goals)
- League: E0 (Premier League)
- Temperature: 1.2
- Market odds: Home=2.5, Draw=3.4, Away=2.8

**Step 1: Base Draw**
```
P(0-0) = 0.082
P(1-1) = 0.118
P(2-2) = 0.042
P(3-3) = 0.008
... (higher scores negligible)
Base P(Draw) = 0.082 + 0.118 + 0.042 + 0.008 = 0.250 (25.0%)
```

**Step 2: Draw Prior Injection**
```
League: E0 (8% prior)
Adjusted draw = 25.0% × 1.08 = 27.0%
```

**Step 3: Temperature Scaling**
```
Temperature: 1.2
After scaling: 27.0% → 27.3%
```

**Step 4: Set-Specific**
- **Set A:** 27.3%
- **Set B:** Blend with market (27.3% × 0.6 + 29.4% × 0.4) = 28.1%
- **Set D:** 27.3% × 1.15 = 31.4%

**Step 5: Calibration**
- **Set A:** 27.3% → 27.8% (calibrated)
- **Set B:** 28.1% → 28.5% (calibrated)
- **Set D:** 31.4% → 31.2% (calibrated)

**Final Result:**
- **Set A:** 27.8%
- **Set B:** 28.5%
- **Set D:** 31.2%

---

## Key Formulas Summary

### 1. Base Draw (Dixon-Coles)
```
P(Draw) = Σ_{x=0}^{max_goals} P(x, x | λ_home, λ_away, ρ)
```

### 2. Draw Prior Injection
```
adjusted_draw = base_draw × (1.0 + draw_prior_league)
```

### 3. Temperature Scaling
```
P_i' = P_i^(1/T) / Σ P_j^(1/T)
```

### 4. Set D Boost
```
boosted_draw = min(draw × 1.15, 0.95)
```

### 5. Calibration
```
calibrated_draw = isotonic_regression(draw, historical_outcomes)
```

---

## Why Multiple Steps?

### Problem: Poisson Underestimation

**Raw Poisson models** systematically underestimate draws because:
1. **Independence assumption** (goals are not truly independent)
2. **Low-score correlation** (0-0 and 1-1 are more likely than Poisson predicts)
3. **League-specific bias** (different leagues have different draw rates)

### Solution: Multi-Layer Correction

1. **Dixon-Coles** → Fixes low-score correlation (ρ parameter)
2. **Draw Prior** → Fixes league-specific bias
3. **Temperature** → Reduces overconfidence
4. **Calibration** → Fine-tunes based on historical performance

---

## Which Set Has Highest Draw?

**Set D (Draw-Boosted)** always has the **highest draw percentage** because:
- Uses all adjustments (draw prior, temperature, calibration)
- **Plus** additional 15% boost
- Designed for **maximum draw coverage**

**Order (typically):**
1. **Set D:** Highest (draw-boosted)
2. **Set B:** High (entropy-weighted blend)
3. **Set A:** Medium (pure model)
4. **Set C:** Lower (market-dominant)
5. **Set E:** Variable (entropy-penalized)

---

## Summary

| Step | What It Does | Typical Impact |
|------|--------------|----------------|
| **1. Base Calculation** | Sum equal scores | 20-25% |
| **2. Draw Prior** | League-specific boost | +2-3% |
| **3. Temperature** | Soften probabilities | ±0.5% |
| **4. Set Adjustment** | Set-specific logic | ±0-5% |
| **5. Calibration** | Final correction | ±1% |
| **Final** | Displayed percentage | 25-35% |

**Final draw percentage** you see on the Probability Output page is the result of **all 5 steps** applied in sequence.

---

## Code Locations

- **Base Calculation:** `app/models/dixon_coles.py` - `calculate_match_probabilities()`
- **Draw Prior:** `app/models/draw_prior.py` - `inject_draw_prior()`
- **Temperature:** `app/models/uncertainty.py` - `temperature_scale()`
- **Set Logic:** `app/models/probability_sets.py` - `generate_all_probability_sets()`
- **Calibration:** `app/models/calibration.py` - `calibrate_probabilities()`
- **Main Flow:** `app/api/probabilities.py` - `calculate_probabilities()`

---

## Verification

### How to Verify Calculation:

1. **Check Draw Prior:**
   - Draw should be **higher** than raw Poisson (typically +2-3%)
   - League-specific differences (E0 vs SP1)

2. **Check Set D:**
   - Set D should have **highest draw** (15% boost)
   - Should be ~3-5% higher than Set A

3. **Check Calibration:**
   - Draw should be **calibrated** (matches historical frequency)
   - Should be **stable** across similar matches

---

## Conclusion

Draw percentage is **not a simple calculation**—it's the result of a **sophisticated multi-step process** that:

1. ✅ Calculates base probability from goal expectations
2. ✅ Fixes structural underestimation via draw priors
3. ✅ Reduces overconfidence via temperature scaling
4. ✅ Applies set-specific adjustments
5. ✅ Fine-tunes via calibration

The final percentage you see is **statistically sound** and **calibrated** to match historical draw frequencies.






