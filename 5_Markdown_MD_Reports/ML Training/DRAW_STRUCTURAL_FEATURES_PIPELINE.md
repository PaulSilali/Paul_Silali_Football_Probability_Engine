# Draw Structural Features in the Probability Pipeline

## 📊 Complete Probability Calculation Pipeline

### **Step-by-Step Flow**

```
1. BASE PROBABILITIES (Poisson/Dixon-Coles)
   ↓
   Calculate: P(Home), P(Draw), P(Away) from team strengths
   Uses: λ_home, λ_away, rho, home_advantage
   ↓

2. DRAW PRIOR INJECTION
   ↓
   Adjusts: Draw probability using league-specific draw rates
   Uses: Hardcoded league draw priors (from draw_prior.py)
   ↓

3. ✅ DRAW STRUCTURAL ADJUSTMENT ← YOUR NEW FEATURES HERE
   ↓
   Adjusts: Draw probability using ALL structural signals
   Uses: 
   - League Priors (from league_draw_priors table)
   - Elo Symmetry (from team_elo table)
   - H2H Stats (from h2h_draw_stats table)
   - Weather (from match_weather table)
   - Referee (from referee_stats table)
   - Rest Days (from team_rest_days table)
   - Odds Movement (from odds_movement table)
   - xG Data (from match_xg table) ← NEW!
   - League Structure (enhances league prior) ← NEW!
   ↓
   Formula: P(Draw)_adjusted = P(Draw)_base × multiplier
   Multiplier = league_prior × elo_symmetry × h2h × weather × 
                fatigue × referee × odds_drift × xg_factor
   Bounded: [0.75, 1.35]
   ↓

4. TEMPERATURE SCALING
   ↓
   Softens probabilities to reduce overconfidence
   ↓

5. ODDS BLENDING (if market odds available)
   ↓
   Blends model probabilities with market odds
   ↓

6. CALIBRATION (if calibration model exists)
   ↓
   Applies isotonic regression calibration curves
   ↓

7. DRAW MODEL (Optional - for Set A, B, C)
   ↓
   Calculates: P(Draw) = 0.55 × Poisson + 0.30 × Dixon-Coles + 0.15 × Market
   Note: This is SEPARATE from draw structural adjustment
   ↓

8. FINAL PROBABILITIES
   ↓
   P(Home)_final, P(Draw)_final, P(Away)_final
```

---

## 🎯 Where Draw Structural Features Are Applied

### **Location in Code**

**File:** `2_Backend_Football_Probability_Engine/app/api/probabilities.py`

**Lines:** 370-414

**Position:** **AFTER** Draw Prior Injection, **BEFORE** Temperature Scaling

### **Integration Point**

```python
# Step 1: Base probabilities from Poisson/Dixon-Coles
base_probs = calculate_match_probabilities(...)

# Step 2: Draw prior injection (hardcoded league priors)
adjusted_home, adjusted_draw, adjusted_away = inject_draw_prior(...)

# Step 3: ✅ DRAW STRUCTURAL ADJUSTMENT ← YOUR FEATURES
draw_components = compute_draw_components(
    db=db,
    fixture_id=fixture_obj.id,
    league_id=...,
    home_team_id=...,
    away_team_id=...
)

p_home_adj, p_draw_adj, p_away_adj = adjust_draw_probability(
    p_home_base=base_probs.home,
    p_draw_base=base_probs.draw,
    p_away_base=base_probs.away,
    draw_multiplier=draw_components.total()  # ← All features combined here
)

# Step 4: Temperature scaling
model_probs_scaled = temperature_scale(...)

# Step 5: Odds blending
blended_probs = blend_probabilities(...)

# Step 6: Calibration
calibrated_probs = apply_calibration(...)
```

---

## 🔍 Draw Model vs Draw Structural Features

### **Draw Model** (Deterministic, No Training)

**What it does:**
- Calculates P(Draw) from Poisson outputs
- Uses: λ_home, λ_away, rho, market odds
- Formula: `P(Draw) = 0.55 × Poisson + 0.30 × Dixon-Coles + 0.15 × Market`
- **Used in:** Probability Sets A, B, C (for display/explainability)

**When it's used:**
- When market odds are available
- For generating probability sets
- For explainability (shows draw components)

**Location:** `app/models/draw_model.py`

---

### **Draw Structural Features** (Post-Processing Adjustment)

**What it does:**
- Adjusts P(Draw) using contextual signals
- Uses: League priors, Elo, H2H, Weather, Referee, Rest Days, Odds Movement, xG, League Structure
- Formula: `P(Draw)_adjusted = P(Draw)_base × multiplier`
- **Applied to:** ALL probability sets (A, B, C, D, E, F, G)

**When it's used:**
- For EVERY prediction calculation
- After base probabilities are calculated
- Before temperature scaling and blending

**Location:** `app/features/draw_features.py`

---

## 📈 How They Work Together

### **Example Calculation**

```
1. Base Poisson/Dixon-Coles: P(Draw) = 0.25

2. Draw Prior Injection: P(Draw) = 0.26 (league-specific adjustment)

3. ✅ Draw Structural Adjustment:
   - League Prior: 1.05 (league has 27% draw rate vs 26% baseline)
   - Elo Symmetry: 1.10 (teams are very close in rating)
   - H2H: 1.08 (these teams draw often)
   - Weather: 1.02 (rainy conditions)
   - Referee: 0.98 (referee allows more goals)
   - Rest Days: 1.05 (teams are fatigued)
   - Odds Movement: 1.03 (draw odds increased)
   - xG: 1.08 (low xG = defensive match)
   
   Multiplier = 1.05 × 1.10 × 1.08 × 1.02 × 0.98 × 1.05 × 1.03 × 1.08
              = 1.42 (clipped to 1.35 max)
   
   P(Draw)_adjusted = 0.26 × 1.35 = 0.351 (clipped to 0.38 max)
   
   Final: P(Draw) = 0.35 (35%)

4. Temperature Scaling: P(Draw) = 0.33 (softened)

5. Odds Blending: P(Draw) = 0.34 (blended with market)

6. Calibration: P(Draw) = 0.35 (calibrated)
```

---

## 🎯 Key Differences

| Aspect | Draw Model | Draw Structural Features |
|--------|-----------|-------------------------|
| **Purpose** | Calculate base P(Draw) | Adjust P(Draw) with context |
| **Inputs** | λ_home, λ_away, rho, odds | League priors, Elo, H2H, Weather, etc. |
| **When Applied** | Optional (for Sets A, B, C) | Always (for all sets) |
| **Training Required** | ❌ No (deterministic) | ❌ No (deterministic) |
| **Location** | `draw_model.py` | `draw_features.py` |
| **Order** | Can be used in probability sets | Applied BEFORE sets generation |

---

## ✅ Summary

**Draw Structural Features come in at Step 3** of the pipeline:

1. ✅ **After** base Poisson/Dixon-Coles probabilities
2. ✅ **After** draw prior injection
3. ✅ **Before** temperature scaling
4. ✅ **Before** odds blending
5. ✅ **Before** calibration

**They enhance the draw probability** by incorporating:
- Historical patterns (League Priors, H2H)
- Team context (Elo Symmetry)
- Match context (Weather, Referee, Rest Days)
- Market signals (Odds Movement)
- Quality metrics (xG Data)
- League structure (League Structure)

**The Draw Model** (Poisson + Dixon-Coles + Market) is a **separate calculation** that can be used for explainability, but the **Draw Structural Features** are the ones that actually adjust the final probabilities used in predictions.

