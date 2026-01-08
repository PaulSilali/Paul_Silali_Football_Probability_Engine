# Draw Structural Data Components for Home/Away Probability Adjustment

## ⚠️ CRITICAL PRINCIPLE (Non-Negotiable)

**Draw is NOT an independent outcome. Any draw adjustment MUST affect Home and Away probabilities through redistribution.**

### Why This Matters

If you only boost P(D) and leave P(H) / P(A) unchanged, you:
- ❌ Break probability coherence
- ❌ Inflate total certainty
- ❌ Create false favorites
- ❌ Risk jackpot system failure

### Core Rule

**Any draw-aware system that does not modify Home/Away is structurally incomplete.**

---

## Overview

This document analyzes which draw structural data components can be used to adjust **home/away probabilities** (not just draw probabilities) in the Football Probability Engine.

**Key Distinction:** Components should either:
1. **Modify relative team strength** (direct H/A tilt) - e.g., Elo, Rest Days
2. **Reshape uncertainty/draw mass** (compression/flattening) - e.g., Weather, λ symmetry
3. **Act as priors/rate modifiers** (upstream) - e.g., Elo → Poisson λ, not probability deltas

**NOT:** Direct probability deltas that ignore structural coupling.

---

## ✅ Components That CAN Adjust Home/Away Probabilities

### ⚠️ CRITICAL: Home-Away Compression (Most Important Concept)

**This is the most important draw-aware H/A adjustment and was missing from the original analysis.**

**How It Works:**
- High draw likelihood implies teams are evenly matched
- Neither side dominates
- **Must compress H and A toward each other**

**Adjustment Mechanism:**
```
When draw_signal_high:
    mean = (p_home + p_away) / 2
    p_home = mean + (p_home - mean) * k
    p_away = mean + (p_away - mean) * k
    
Where k ∈ [0.6, 0.9] depending on draw strength
```

**Why Critical:**
- Prevents false favorites
- Prevents jackpot busts
- Reduces overconfident edges
- Maintains probability coherence

**Example:**
- Base: P(H) = 0.50, P(A) = 0.30, P(D) = 0.20
- High draw signal detected
- Compress with k = 0.75
- Adjusted: P(H) = 0.45, P(A) = 0.35, P(D) = 0.20
- **Result:** H/A spread reduced from 0.20 to 0.10

**Current Usage:** ⚠️ **MISSING** - Should be implemented in draw adjustment logic

---

### 1. **Elo Ratings** ⭐⭐⭐⭐⭐
**Impact Level:** Very High (BUT as PRIOR, not direct delta)

**How It Works:**
- Elo ratings measure team strength relative to each other
- **Elo difference** directly indicates which team is stronger
- Stronger team = higher win probability (home or away)

**⚠️ CORRECTED Role:**
- ✅ Elo should modify **expected goal rates** (Poisson λ) or **strength differentials**
- ✅ Elo belongs **upstream** in the model, not as a post-hoc probability shifter
- ❌ Elo should **NOT** directly add ±5-7% probability as a delta

**Correct Usage:**
```
Elo → Strength Prior → Feeds into Poisson λ → Win Expectancy
NOT: Elo → Direct Probability Delta
```

**Example:**
- Home team Elo: 1600
- Away team Elo: 1500
- Elo difference: +100
- **Correct:** Modify λ_home and λ_away based on Elo, then recompute probabilities
- **Wrong:** Add 5% to P(H) and subtract 5% from P(A)

**Current Usage:** ✅ Already calculated and stored in `team_elo` table

---

### 2. **H2H (Head-to-Head) Stats** ⭐⭐
**Impact Level:** Low-Medium (CORRECTED from High)

**⚠️ CRITICAL WARNING:** H2H is **highly dangerous** if treated as a direct H/A shifter.

**Why Dangerous:**
- ❌ Small samples (unreliable)
- ❌ Regime changes (roster turnover)
- ❌ Non-stationary effects (teams evolve)
- ❌ Can create false signals

**Correct Role:**
- ✅ Weak prior only
- ✅ Tie-breaker when Elo is very close
- ✅ Draw-context signal (styles cancelling out)
- ✅ Mostly affects draw likelihood, NOT win direction

**⚠️ CORRECTED Adjustment Mechanism:**
```
Recommended Cap: ≤ 2-3% max influence
Only within last 24 months
Should never exceed Elo influence
```

**Example:**
- Home team wins 70% of H2H matches (but only 5 matches, 2 years ago)
- **Correct:** Very light nudge (1-2%), mostly affects draw probability
- **Wrong:** Large adjustment (10-15%) that overrides Elo

**Current Usage:** ✅ Already calculated and stored in `team_h2h_stats` and `h2h_draw_stats` tables

---

### 3. **Rest Days** ⭐⭐⭐⭐
**Impact Level:** High

**How It Works:**
- Measures fatigue/recovery time between matches
- Teams with more rest days are typically fresher and perform better
- Can significantly impact match outcomes

**Adjustment Mechanism:**
```
Home Win Probability Adjustment:
- If home_rest_days > away_rest_days: Increase home win probability
- If home_rest_days < away_rest_days: Decrease home win probability
- Magnitude based on rest day difference (e.g., 3+ days difference = significant impact)

Away Win Probability Adjustment:
- Inverse of home adjustment
- If away_rest_days > home_rest_days: Increase away win probability
```

**Example:**
- Home team: 7 days rest
- Away team: 3 days rest
- Rest advantage: +4 days for home team
- **Adjustment:** Increase home win probability by 5-8%, decrease away win probability accordingly

**Current Usage:** ✅ Already calculated and stored in `team_rest_days` table

---

### 4. **Weather Conditions** ⭐⭐⭐
**Impact Level:** Medium (CORRECTED from Medium-High)

**⚠️ CORRECTED Understanding:** Weather mostly compresses outcomes, increases randomness, raises draw likelihood.

**How It Works:**
- Extreme weather (rain, wind, cold) increases randomness
- Reduces skill differential
- Favors draw outcomes

**⚠️ CORRECTED Adjustment Mechanism:**
```
Weather should:
- Reduce H/A separation (flatten)
- Increase draw mass
- RARELY flip winner direction
```

**Correct Role:**
- ✅ Compresses H and A toward each other
- ✅ Increases draw probability
- ❌ Should NOT strongly tilt toward one side

**Example:**
- Heavy rain + strong wind
- **Correct:** Flatten H/A (reduce spread), increase draw
- **Wrong:** Strongly favor away team based on playing style

**Current Usage:** ✅ Already calculated and stored in `match_weather` table

---

### 5. **League Structure / Motivation** ⭐⭐
**Impact Level:** Low-Medium (CORRECTED from Medium)

**⚠️ CRITICAL WARNING:** Motivation is real but **unobservable** and can be dangerous.

**How It Works:**
- Teams fighting for promotion/relegation have different motivation levels
- Teams in mid-table with nothing to play for may be less motivated
- End-of-season matches have different dynamics

**⚠️ CORRECTED Role:**
- ✅ Very light nudge only
- ✅ Mostly uncertainty-based
- ✅ Never directional unless extreme (relegation final day)
- ❌ Should NOT be a major factor

**Recommended Cap:**
```
≤ 2-3% max influence
Only in extreme cases (final day, promotion/relegation)
```

**Example:**
- Home team: Safe mid-table (no motivation)
- Away team: Fighting relegation (high motivation)
- **Correct:** Very light adjustment (1-2%), mostly affects draw
- **Wrong:** Large adjustment (3-5%) that overrides team strength

**Current Usage:** ✅ Already calculated and stored in `league_structure` table

---

### 6. **Odds Movement** ⭐⭐
**Impact Level:** Low (CORRECTED from Low-Medium)

**⚠️ CORRECTED Understanding:** Odds movement should affect trust and calibration, rarely change direction.

**How It Works:**
- Market odds reflect public sentiment and insider information
- Significant odds movement can indicate team news (injuries, lineup changes)
- Can be used to calibrate model probabilities

**⚠️ CORRECTED Role:**
- ✅ Affect trust (confidence in model)
- ✅ Affect calibration (blend market vs model)
- ❌ Rarely change winner direction
- ❌ NOT a probability delta

**Correct Usage:**
```
Weight market vs model
NOT a direct probability shifter
```

**Example:**
- Home odds moved from 2.50 to 2.20 (significant decrease)
- **Correct:** Increase weight on market, adjust calibration blend
- **Wrong:** Directly shift probabilities by 2-4%

**Current Usage:** ✅ Already calculated and stored in `odds_movement` table

---

### 7. **XG (Expected Goals) Data** ⭐⭐
**Impact Level:** Low-Medium (CORRECTED from High)

**⚠️ CRITICAL WARNING:** Risk of **double counting** if Poisson model already uses goals/shot data.

**How It Works:**
- XG measures quality of chances created, not just goals scored
- Better predictor of future performance than actual goals
- Can reveal which team is creating better chances

**⚠️ CORRECTED Role:**
- ✅ **Diagnostic** - Check if model aligns with xG
- ✅ **Confidence modifier** - Adjust uncertainty, not direction
- ✅ **Calibration signal** - Fine-tune model, not shift probabilities
- ❌ **NOT** a direct H/A probability adjuster if Poisson already uses goals

**Safe Usage:**
```
Only when xG is external or orthogonal to Poisson inputs
Otherwise → double counting risk
```

**Correct Adjustment Mechanism:**
```
xG should usually:
- Adjust uncertainty (widen confidence intervals)
- Adjust draw mass (redistribute)
- NOT push H/A directly
```

**Example:**
- Home team xG: 2.1
- Away team xG: 1.3
- **If Poisson already uses goals:** Use xG for diagnostic/calibration only
- **If xG is external:** Can use for light adjustment (2-3%), mostly draw mass

**Current Usage:** ✅ Already calculated and stored in `match_xg` table

---

## ⚠️ Components That Primarily Affect Draw Probabilities

### 8. **League Draw Priors** ⭐
**Impact Level:** Low for Home/Away

**How It Works:**
- Measures historical draw rate for a league/season
- Primarily used to adjust draw probability
- Has minimal direct impact on home/away probabilities

**Potential Indirect Impact:**
- If league has high draw rate, it reduces both home and away win probabilities proportionally
- But this is more of a normalization effect than a direct adjustment

**Current Usage:** ✅ Already calculated and stored in `league_draw_priors` table

---

### 9. **Referee Stats** ⭐
**Impact Level:** Very Low (CORRECTED from Low-Medium)

**⚠️ CORRECTED Understanding:** Referee effects are weak, noisy, and often spurious.

**How It Works:**
- Referees with different styles can affect match outcomes
- Strict referees may favor defensive teams
- Some referees show home bias in decisions

**⚠️ CORRECTED Role:**
- ✅ Draw inflation (strict refs → more draws)
- ✅ Slight home bias (if statistically significant)
- ❌ Never decisive
- ❌ Should be minimal influence

**Correct Usage:**
```
Very light adjustment (1-2% max)
Mostly affects draw probability
Rarely affects H/A direction
```

**Example:**
- Referee has 60% home win rate (vs league average 45%)
- **Correct:** Very light adjustment (1%), mostly affects draw
- **Wrong:** Significant adjustment (2-3%) that overrides team strength

**Current Usage:** ✅ Already calculated and stored in `referee_stats` table

---

## 📊 Summary: Components Ranked by Home/Away Impact (CORRECTED)

| Component | Impact on Home/Away | Primary Use Case | Adjustment Magnitude | Correct Role |
|-----------|-------------------|------------------|---------------------|--------------|
| **Home-Away Compression** | ⭐⭐⭐⭐⭐ | Draw-aware H/A redistribution | High (structural) | **MOST IMPORTANT** |
| **Elo Ratings** | ⭐⭐⭐⭐⭐ | Team strength (as PRIOR) | High (upstream) | Modify λ, not deltas |
| **Rest Days** | ⭐⭐⭐⭐ | Fatigue/recovery advantage | Medium-High (3-8%) | Direct H/A tilt |
| **λ Symmetry / Total Goals** | ⭐⭐⭐⭐ | Goal-rate coupling | Medium-High (structural) | Compress H/A |
| **Weather** | ⭐⭐⭐ | Outcome compression | Medium (2-4%) | Flatten H/A |
| **League Structure** | ⭐⭐ | Motivation/context | Low (1-3%) | Light nudge only |
| **Odds Movement** | ⭐⭐ | Market calibration | Low (calibration) | Weight, not delta |
| **H2H Stats** | ⭐⭐ | Weak prior | Low (1-3%) | Tie-breaker only |
| **Referee Stats** | ⭐ | Draw inflation | Very Low (1-2%) | Minimal influence |
| **XG Data** | ⭐⭐ | Diagnostic/calibration | Low (if double-count risk) | Check alignment |
| **League Draw Priors** | ⭐ | Indirect normalization | Low (structural) | Mass redistribution |

---

## 🎯 Recommended Implementation Strategy (CORRECTED)

### **Tier 1: Structural / Safe Components (Implement First)**
1. **Home-Away Compression** ⚠️ **MISSING - MOST CRITICAL**
2. **Elo Ratings** - As strength prior (modify λ, not deltas)
3. **λ Symmetry / Total Goals** - Goal-rate coupling (compress H/A)
4. **Rest Days** - Fatigue advantage (direct H/A tilt)

### **Tier 2: Contextual Components (Implement Second)**
5. **Weather** - Outcome compression (flatten H/A)
6. **League Motivation** - Very light nudge (≤2-3%)
7. **Market Divergence** - Reallocate mass (not direct delta)

### **Tier 3: Very Light Components (Optional)**
8. **H2H Stats** - Weak prior only (≤2-3%, tie-breaker)
9. **Referees** - Minimal influence (mostly draw)
10. **XG Data** - Diagnostic only (if double-count risk)
11. **League Draw Priors** - Structural redistribution

---

## 💡 Key Insights

1. **Elo Ratings** are the most powerful tool for adjusting home/away probabilities
2. **H2H Stats** can reveal team-specific advantages that Elo doesn't capture
3. **Rest Days** can significantly impact match outcomes, especially in congested schedules
4. **XG Data** provides better predictive power than actual goals scored
5. **Weather** and **League Structure** add contextual adjustments
6. **Odds Movement** and **Referee Stats** provide smaller, fine-tuning adjustments

---

## 🔧 Implementation Notes

### **Current State:**
- ✅ All 9 components are already being ingested and stored in the database
- ✅ Data is available for probability adjustment calculations
- ⚠️ **No implementation yet** - Backend is currently being used, so no changes should be made

### **Future Implementation:**
When ready to implement, create a new service:
- `app/services/probability_adjustment.py`
- Use the draw structural data to adjust base home/away probabilities
- Apply adjustments in order of impact (Tier 1 → Tier 2 → Tier 3)
- Ensure adjustments sum to 1.0 (probabilities must be normalized)

---

## 📝 Example Adjustment Formula (CORRECTED - Structurally Sound)

```python
# Pseudo-code (NOT IMPLEMENTED - for reference only)
# ⚠️ CORRECTED: Structural approach, not additive deltas

def adjust_home_away_probabilities(
    base_home_prob: float,
    base_away_prob: float,
    base_draw_prob: float,
    elo_home: float,
    elo_away: float,
    lambda_home: float,  # Poisson λ (from Elo/strength)
    lambda_away: float,  # Poisson λ
    lambda_total: float,  # Total expected goals
    h2h_stats: dict,
    rest_days_home: int,
    rest_days_away: int,
    weather_factor: float,
    market_draw_prob: float,
    league_structure: dict
) -> tuple[float, float, float]:
    """
    CORRECTED: Adjust home/away/draw probabilities based on draw structural data.
    Uses structural approach: modify latent strength → recompute probabilities.
    
    Returns:
        (adjusted_home_prob, adjusted_away_prob, adjusted_draw_prob)
    """
    
    # ============================================================
    # STEP 1: Modify Latent Strength (Upstream)
    # ============================================================
    
    # Elo modifies λ (strength), not probabilities directly
    elo_diff = elo_home - elo_away
    elo_strength_factor = 1.0 + (elo_diff / 400.0) * 0.1  # Convert Elo to λ modifier
    adjusted_lambda_home = lambda_home * elo_strength_factor
    adjusted_lambda_away = lambda_away / elo_strength_factor
    
    # Rest days modify intensity (affects λ)
    rest_advantage = rest_days_home - rest_days_away
    rest_factor = 1.0 + (rest_advantage / 7.0) * 0.05  # Max 5% per week
    adjusted_lambda_home *= rest_factor
    adjusted_lambda_away /= rest_factor
    
    # ============================================================
    # STEP 2: Recompute Base Probabilities from Adjusted λ
    # ============================================================
    
    # Use Poisson/Dixon-Coles to compute probabilities from adjusted λ
    p_home_raw, p_draw_raw, p_away_raw = poisson_probabilities(
        adjusted_lambda_home, 
        adjusted_lambda_away
    )
    
    # ============================================================
    # STEP 3: Apply Draw-Aware Compression (CRITICAL)
    # ============================================================
    
    # Calculate draw signal strength
    draw_signal = calculate_draw_signal(
        lambda_total,
        market_draw_prob,
        weather_factor,
        h2h_stats.get('draw_rate', 0.25)
    )
    
    # CRITICAL: Compress H/A when draw signal is high
    if draw_signal > 0.6:  # High draw likelihood
        mean = (p_home_raw + p_away_raw) / 2
        compression_factor = 0.6 + (1.0 - draw_signal) * 0.3  # k ∈ [0.6, 0.9]
        p_home_compressed = mean + (p_home_raw - mean) * compression_factor
        p_away_compressed = mean + (p_away_raw - mean) * compression_factor
    else:
        p_home_compressed = p_home_raw
        p_away_compressed = p_away_raw
    
    # ============================================================
    # STEP 4: Apply λ Symmetry Adjustment
    # ============================================================
    
    # If λ_home ≈ λ_away, compress further
    lambda_gap = abs(adjusted_lambda_home - adjusted_lambda_away)
    if lambda_gap < 0.3:  # Teams very evenly matched
        gap_factor = np.exp(-2.0 * lambda_gap)  # Exponential compression
        mean = (p_home_compressed + p_away_compressed) / 2
        p_home_compressed = mean + (p_home_compressed - mean) * gap_factor
        p_away_compressed = mean + (p_away_compressed - mean) * gap_factor
    
    # ============================================================
    # STEP 5: Market Divergence → Mass Reallocation
    # ============================================================
    
    # If market sees more draw than model, take mass from stronger side
    if market_draw_prob > p_draw_raw:
        draw_mass_to_add = (market_draw_prob - p_draw_raw) * 0.5  # Blend factor
        if p_home_compressed > p_away_compressed:
            p_home_compressed -= draw_mass_to_add
        else:
            p_away_compressed -= draw_mass_to_add
        p_draw_adjusted = p_draw_raw + draw_mass_to_add
    else:
        p_draw_adjusted = p_draw_raw
    
    # ============================================================
    # STEP 6: Low-Scoring Regime Adjustment
    # ============================================================
    
    # If λ_total < 2.1, flatten H/A tails (reduce extreme outcomes)
    if lambda_total < 2.1:
        flatten_factor = lambda_total / 2.1  # 0.0 to 1.0
        mean = (p_home_compressed + p_away_compressed) / 2
        p_home_compressed = mean + (p_home_compressed - mean) * flatten_factor
        p_away_compressed = mean + (p_away_compressed - mean) * flatten_factor
    
    # ============================================================
    # STEP 7: Very Light Contextual Adjustments
    # ============================================================
    
    # H2H: Very light nudge (≤2-3%)
    h2h_nudge = calculate_h2h_nudge(h2h_stats)  # Capped at 0.02
    if abs(h2h_nudge) < 0.02:  # Safety cap
        p_home_compressed += h2h_nudge
        p_away_compressed -= h2h_nudge
    
    # League motivation: Very light (≤2-3%)
    motivation_nudge = calculate_motivation_nudge(league_structure)  # Capped at 0.02
    if abs(motivation_nudge) < 0.02:  # Safety cap
        p_home_compressed += motivation_nudge
        p_away_compressed -= motivation_nudge
    
    # ============================================================
    # STEP 8: Renormalize (Ensure Probabilities Sum to 1.0)
    # ============================================================
    
    total = p_home_compressed + p_away_compressed + p_draw_adjusted
    adjusted_home_prob = p_home_compressed / total
    adjusted_away_prob = p_away_compressed / total
    adjusted_draw_prob = p_draw_adjusted / total
    
    # Final safety check
    assert abs(adjusted_home_prob + adjusted_away_prob + adjusted_draw_prob - 1.0) < 1e-6
    
    return adjusted_home_prob, adjusted_away_prob, adjusted_draw_prob


def calculate_draw_signal(
    lambda_total: float,
    market_draw_prob: float,
    weather_factor: float,
    h2h_draw_rate: float
) -> float:
    """Calculate draw signal strength (0.0 to 1.0)"""
    signals = []
    
    # Low total goals → high draw signal
    if lambda_total < 2.1:
        signals.append(0.8)
    elif lambda_total < 2.5:
        signals.append(0.6)
    else:
        signals.append(0.4)
    
    # Market sees high draw
    if market_draw_prob > 0.28:
        signals.append(0.7)
    
    # Weather increases randomness
    if weather_factor > 0.6:  # Extreme weather
        signals.append(0.6)
    
    # H2H high draw rate
    if h2h_draw_rate > 0.30:
        signals.append(0.5)
    
    return np.mean(signals) if signals else 0.5
```

### ⚠️ Key Corrections Made:

1. **Structural Approach:** Modify latent strength (λ) → recompute probabilities
2. **Home-Away Compression:** Added as critical step (was missing)
3. **λ Symmetry:** Added goal-rate coupling adjustment
4. **Market Divergence:** Mass reallocation, not direct delta
5. **Safety Caps:** H2H and motivation capped at 2-3%
6. **No Additive Deltas:** Avoids breaking probability coherence

---

## ✅ Conclusion (CORRECTED)

**Yes, draw structural data components CAN and SHOULD adjust home/away probabilities**, but with critical corrections:

### **Most Important (Was Missing):**
1. **Home-Away Compression** ⚠️ **CRITICAL - MUST IMPLEMENT FIRST**
   - When draw signal is high, compress H/A toward each other
   - Prevents false favorites and jackpot busts
   - More important than any other component

### **High Impact (Correctly Used):**
2. **Elo Ratings** (⭐⭐⭐⭐⭐) - As strength PRIOR (modify λ), not direct delta
3. **Rest Days** (⭐⭐⭐⭐) - Direct H/A tilt (fatigue advantage)
4. **λ Symmetry / Total Goals** (⭐⭐⭐⭐) - Goal-rate coupling (compress H/A)

### **Medium Impact (Correctly Used):**
5. **Weather** (⭐⭐⭐) - Outcome compression (flatten H/A)
6. **Market Divergence** (⭐⭐⭐) - Mass reallocation (not direct delta)

### **Low Impact (Correctly Capped):**
7. **H2H Stats** (⭐⭐) - Weak prior only (≤2-3%, tie-breaker)
8. **League Motivation** (⭐⭐) - Very light (≤2-3%, extreme cases only)
9. **XG Data** (⭐⭐) - Diagnostic only (if double-count risk)
10. **Referee Stats** (⭐) - Minimal influence (mostly draw)
11. **Odds Movement** (⭐⭐) - Calibration weight (not delta)

### **Critical Principles:**
- ✅ **Draw adjustments MUST redistribute H/A mass**
- ✅ **Modify latent strength (λ) → recompute probabilities**
- ✅ **Compress H/A when draw signal is high**
- ❌ **Never use additive probability deltas**
- ❌ **Avoid double counting (xG if Poisson uses goals)**
- ❌ **Cap weak signals (H2H, motivation ≤2-3%)**

---

**Note:** This document has been corrected based on probability engineering / jackpot-system best practices. No implementation should be done while the backend is in use.

