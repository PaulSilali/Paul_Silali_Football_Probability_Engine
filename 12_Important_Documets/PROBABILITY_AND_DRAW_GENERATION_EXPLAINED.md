# Probability & Draw Generation: Complete Architecture

## 📊 Overview

This document explains how probabilities are generated and how draw probabilities are enhanced using database tables and trained models in the Football Probability Engine.

---

## 🔄 Complete Probability Generation Pipeline

### **Step-by-Step Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BASE MODEL (Dixon-Coles/Poisson)                            │
│    Input: Team strengths (attack_rating, defense_rating)       │
│    Output: P(Home), P(Draw), P(Away)                           │
│    Tables: teams (attack_rating, defense_rating)               │
│            models (model_weights: team_strengths)              │
│    ⚠️ NOTE: Ratings must be trained first via model training!  │
│       Default value is 1.0 (all teams equal)                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. DRAW PRIOR INJECTION                                        │
│    Adjusts: Draw probability using league-specific rates        │
│    Tables: leagues (avg_draw_rate)                              │
│            draw_prior.py (hardcoded league priors)              │
│    Formula: P(Draw) *= (1 + league_draw_prior)                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. DRAW STRUCTURAL ADJUSTMENT ⭐                                │
│    Adjusts: Draw probability using ALL structural signals       │
│    Tables: league_draw_priors, team_elo, h2h_draw_stats,       │
│            match_weather, referee_stats, team_rest_days,       │
│            odds_movement, match_xg, league_structure           │
│    Formula: P(Draw)_adj = P(Draw)_base × multiplier            │
│    Multiplier = league_prior × elo_symmetry × h2h × weather × │
│                 fatigue × referee × odds_drift × xg_factor     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. TEMPERATURE SCALING                                         │
│    Softens probabilities to reduce overconfidence               │
│    Tables: models (model_weights: temperature)                  │
│            training_runs (temperature)                          │
│    Formula: P_scaled = P^(1/temperature) / Σ(P^(1/temperature))│
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. ODDS BLENDING (if market odds available)                     │
│    Blends model probabilities with market odds                  │
│    Tables: jackpot_fixtures (odds_home, odds_draw, odds_away)   │
│    Formula: P_blended = α × P_model + (1-α) × P_market         │
│    Where α = entropy_weighted_alpha (prevents overconfidence)   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. CALIBRATION (if calibration model exists)                    │
│    Applies isotonic regression calibration curves               │
│    Tables: calibration_data (predicted_prob_bucket,            │
│                            actual_frequency)                    │
│            models (model_type='calibration')                    │
│    Formula: P_calibrated = isotonic_regression(P_predicted)    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. PROBABILITY SETS GENERATION                                  │
│    Creates multiple probability sets (A-J)                      │
│    Sets A-C: Use draw_model.py (Poisson + Dixon-Coles + Market) │
│    Sets D-G: Heuristic adjustments (draw boost, entropy, etc.)  │
│    Tables: predictions (stores final probabilities)              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. FINAL STORAGE                                                │
│    Stores all probabilities in predictions table                  │
│    Tables: predictions (prob_home, prob_draw, prob_away,       │
│                      draw_components, expected_home_goals, etc.) │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Tables & Their Roles

### **1. Core Model Tables**

#### **`models`**
- **Purpose**: Stores trained model metadata and parameters
- **Key Columns**:
  - `model_type`: 'dixon-coles', 'blending', 'calibration'
  - `model_weights`: JSONB containing:
    - `team_strengths`: {team_id: {attack_rating, defense_rating}}
    - `temperature`: Learned temperature parameter (1.0-1.5)
    - `decay_rate`: Time decay parameter (xi)
    - `blend_alpha`: Model vs market weight
- **Usage**: Loads team strengths and model parameters for base probability calculation

#### **`teams`**
- **Purpose**: Team registry with strength parameters
- **Key Columns**:
  - `attack_rating`: Attack strength α (log scale, ~1.0 average)
  - `defense_rating`: Defense strength β (log scale, ~1.0 average)
  - `canonical_name`: Normalized name for matching
  - `last_calculated`: Timestamp of last training update (NULL = not trained)
- **Usage**: Provides team strengths for Dixon-Coles model
- **⚠️ IMPORTANT**: Ratings are **calculated through model training**, not manually set
  - Default value is 1.0 (all teams equal)
  - Training uses historical matches to estimate strengths
  - See `TEAM_RATINGS_ANALYSIS.md` for details

#### **`matches`**
- **Purpose**: Historical match results (training data)
- **Key Columns**:
  - `home_goals`, `away_goals`: Actual match results
  - `result`: 'H', 'D', or 'A'
  - `odds_home`, `odds_draw`, `odds_away`: Closing odds
- **Usage**: Used for model training and validation

---

### **2. Draw Structural Tables**

#### **`league_draw_priors`**
- **Purpose**: Historical draw rates per league/season
- **Key Columns**:
  - `league_id`: Foreign key to leagues
  - `season`: Season identifier (e.g., '2023-24')
  - `draw_rate`: Observed draw rate (0.0-1.0)
  - `sample_size`: Number of matches used
- **Usage**: Provides league-specific draw baseline
- **Formula**: `league_prior = draw_rate / 0.26` (normalized to baseline)
- **Bounds**: [0.9, 1.2]

#### **`team_elo`**
- **Purpose**: Team Elo ratings over time
- **Key Columns**:
  - `team_id`: Foreign key to teams
  - `date`: Date of rating
  - `elo_rating`: Elo rating (typically 1000-2000)
- **Usage**: Calculates Elo symmetry factor
- **Formula**: `elo_symmetry = exp(-|home_elo - away_elo| / 160.0)`
- **Logic**: Closer ratings → higher draw probability
- **Bounds**: [0.8, 1.2]

#### **`h2h_draw_stats`**
- **Purpose**: Head-to-head draw statistics between team pairs
- **Key Columns**:
  - `team_home_id`, `team_away_id`: Team pair
  - `matches_played`: Total historical meetings
  - `draw_count`: Number of draws
- **Usage**: Adjusts draw probability based on historical H2H draw rate
- **Formula**: `h2h_factor = (draw_count / matches_played) / 0.26`
- **Requirement**: Minimum 4 matches
- **Bounds**: [0.9, 1.15]

#### **`match_weather`**
- **Purpose**: Weather conditions at match time
- **Key Columns**:
  - `fixture_id`: Foreign key to jackpot_fixtures
  - `temperature`: Temperature in Celsius
  - `rainfall`: Rainfall in mm
  - `wind_speed`: Wind speed in km/h
  - `weather_draw_index`: Pre-calculated draw adjustment (0.95-1.10)
- **Usage**: Adjusts draw probability based on weather
- **Logic**: Adverse weather (rain, wind) → higher draw probability
- **Bounds**: [0.95, 1.10]

#### **`referee_stats`**
- **Purpose**: Referee behavioral statistics
- **Key Columns**:
  - `referee_id`: Unique referee identifier
  - `avg_cards`: Average cards per match
  - `avg_penalties`: Average penalties per match
  - `draw_rate`: Observed draw rate in matches officiated
- **Usage**: Adjusts draw probability based on referee control
- **Formula**: `referee_factor = 1.0 + (1.0 / max(1.0, avg_cards + avg_penalties)) * 0.08`
- **Logic**: Low control (high cards/penalties) → lower draw probability
- **Bounds**: [0.95, 1.10]

#### **`team_rest_days`**
- **Purpose**: Team rest days and congestion data
- **Key Columns**:
  - `team_id`: Foreign key to teams
  - `fixture_id`: Foreign key to jackpot_fixtures
  - `rest_days`: Days of rest before fixture
  - `is_midweek`: Whether match is midweek (Tue-Thu)
- **Usage**: Adjusts draw probability based on fatigue
- **Formula**: `fatigue_factor = 1.0 + max(0, 4 - rest_days) * 0.04`
- **Logic**: Less rest → higher draw probability (fatigue)
- **Bounds**: [0.9, 1.12]

#### **`odds_movement`**
- **Purpose**: Odds movement data for draw probability
- **Key Columns**:
  - `fixture_id`: Foreign key to jackpot_fixtures
  - `draw_open`: Opening draw odds
  - `draw_close`: Closing draw odds
  - `draw_delta`: Change in draw odds (close - open)
- **Usage**: Adjusts draw probability based on market movement
- **Formula**: `odds_drift_factor = 1.0 + draw_delta * 0.15`
- **Logic**: Positive delta (odds increased) → higher draw probability
- **Bounds**: [0.9, 1.15]

#### **`match_xg`**
- **Purpose**: Expected Goals (xG) data for fixtures
- **Key Columns**:
  - `fixture_id`: Foreign key to jackpot_fixtures
  - `xg_home`, `xg_away`: Expected goals for each team
  - `xg_total`: Total expected goals (xg_home + xg_away)
  - `xg_draw_index`: Pre-calculated draw adjustment (0.8-1.2)
- **Usage**: Adjusts draw probability based on expected goal quality
- **Formula**: `xg_draw_index = 1.0 + (2.5 - xg_total) * 0.08`
- **Logic**: Lower xG (defensive match) → higher draw probability
- **Bounds**: [0.8, 1.2]

#### **`league_structure`**
- **Purpose**: League structural metadata
- **Key Columns**:
  - `league_id`: Foreign key to leagues
  - `season`: Season identifier
  - `total_teams`: Number of teams in league
  - `relegation_zones`: Number of relegation positions
  - `promotion_zones`: Number of promotion positions
- **Usage**: Enhances league draw prior with structural context
- **Formula**: 
  - `team_factor = 1.0 + (total_teams - 20) * 0.005`
  - `relegation_factor = 1.0 + (relegation_zones / 3.0) * 0.02`
  - `structure_multiplier = team_factor * relegation_factor`
- **Logic**: Larger leagues, more relegation zones → slightly higher draw rates
- **Bounds**: [0.95, 1.05]

---

### **3. Calibration Tables**

#### **`calibration_data`**
- **Purpose**: Isotonic regression calibration curves
- **Key Columns**:
  - `model_id`: Foreign key to models
  - `league_id`: League (optional, NULL = global)
  - `outcome_type`: 'H', 'D', or 'A'
  - `predicted_prob_bucket`: Probability bin (e.g., 0.05, 0.10, 0.15)
  - `actual_frequency`: Observed frequency in bucket
- **Usage**: Applies calibration to predicted probabilities
- **Formula**: `P_calibrated = isotonic_regression(P_predicted)`
- **Logic**: Maps predicted probabilities to actual frequencies

---

### **4. Storage Tables**

#### **`predictions`**
- **Purpose**: Stores final predicted probabilities
- **Key Columns**:
  - `fixture_id`: Foreign key to jackpot_fixtures
  - `model_id`: Foreign key to models
  - `set_type`: 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'
  - `prob_home`, `prob_draw`, `prob_away`: Final probabilities
  - `draw_components`: JSONB with draw adjustment breakdown
  - `expected_home_goals`, `expected_away_goals`: λ_home, λ_away
  - `model_prob_home`, `model_prob_draw`, `model_prob_away`: Pre-blending
  - `market_prob_home`, `market_prob_draw`, `market_prob_away`: Market-implied
  - `blend_weight`: Alpha used for blending
- **Usage**: Stores all probability sets for each fixture

---

## 🧮 Mathematical Formulas

### **1. Base Probability Calculation (Dixon-Coles)**

```python
# Expected goals
λ_home = home_attack × away_defense × home_advantage
λ_away = away_attack × home_defense

# Score probability
P(home_goals=h, away_goals=a) = τ(h, a, ρ) × Poisson(h, λ_home) × Poisson(a, λ_away)

# Where τ is the Dixon-Coles adjustment:
τ(0, 0, ρ) = 1 - λ_home × λ_away × ρ
τ(0, 1, ρ) = 1 + λ_home × ρ
τ(1, 0, ρ) = 1 + λ_away × ρ
τ(1, 1, ρ) = 1 - ρ
τ(h, a, ρ) = 1 otherwise

# Match outcome probabilities
P(Home) = Σ P(h, a) for h > a
P(Draw) = Σ P(h, a) for h == a
P(Away) = Σ P(h, a) for h < a
```

### **2. Draw Structural Adjustment**

```python
# Calculate all components
league_prior = league_draw_priors.draw_rate / 0.26  # Normalized to baseline
elo_symmetry = exp(-|home_elo - away_elo| / 160.0)
h2h_factor = (h2h_draw_stats.draw_count / matches_played) / 0.26
weather_factor = match_weather.weather_draw_index
fatigue_factor = 1.0 + max(0, 4 - rest_days) * 0.04
referee_factor = 1.0 + (1.0 / max(1.0, avg_cards + avg_penalties)) * 0.08
odds_drift_factor = 1.0 + draw_delta * 0.15
xg_factor = match_xg.xg_draw_index

# Total multiplier
multiplier = league_prior × elo_symmetry × h2h_factor × weather_factor ×
             fatigue_factor × referee_factor × odds_drift_factor × xg_factor
multiplier = clip(multiplier, 0.75, 1.35)

# Adjust draw probability
P(Draw)_adjusted = clip(P(Draw)_base × multiplier, 0.12, 0.38)

# Renormalize home/away
remaining_prob = 1.0 - P(Draw)_adjusted
scale = remaining_prob / (P(Home)_base + P(Away)_base)
P(Home)_final = P(Home)_base × scale
P(Away)_final = P(Away)_base × scale
```

### **3. Temperature Scaling**

```python
# Temperature scaling (softens probabilities)
P_scaled[i] = P[i]^(1/temperature) / Σ(P[j]^(1/temperature))

# Where temperature is learned during training (typically 1.0-1.5)
# Higher temperature = softer probabilities (less confident)
```

### **4. Odds Blending**

```python
# Entropy-weighted alpha (prevents overconfident models from dominating)
normalized_entropy = entropy(P_model) / log2(3)  # Normalize to [0, 1]
alpha_effective = clip(base_alpha × normalized_entropy, 0.15, 0.75)

# Blend probabilities
P_blended = alpha_effective × P_model + (1 - alpha_effective) × P_market
```

### **5. Calibration**

```python
# Isotonic regression calibration
P_calibrated = isotonic_regression(P_predicted, calibration_data)

# Where calibration_data maps predicted buckets to actual frequencies
# Example: If predicted=0.25 and calibration shows actual=0.28, then P_calibrated=0.28
```

---

## 🔍 Example Calculation

### **Input Data**

- **Teams**: Manchester United (home) vs Liverpool (away)
- **Team Strengths**: MU attack=1.2, defense=0.9; LIV attack=1.3, defense=0.8
- **League**: Premier League (E0)
- **Elo Ratings**: MU=1650, LIV=1680
- **H2H**: 50 matches, 12 draws (24% draw rate)
- **Weather**: Rainy (weather_draw_index=1.05)
- **Rest Days**: MU=3 days, LIV=4 days (avg=3.5)
- **Referee**: Low control (avg_cards=4.5)
- **Odds Movement**: Draw odds increased by 0.1
- **xG**: Low xG match (xg_draw_index=1.08)

### **Step-by-Step Calculation**

1. **Base Probabilities (Dixon-Coles)**
   ```
   λ_home = 1.2 × 0.8 × 1.35 = 1.296
   λ_away = 1.3 × 0.9 = 1.17
   P(Home) = 0.42
   P(Draw) = 0.25
   P(Away) = 0.33
   ```

2. **Draw Prior Injection**
   ```
   League prior (E0) = 0.08
   P(Draw) = 0.25 × (1 + 0.08) = 0.27
   ```

3. **Draw Structural Adjustment**
   ```
   league_prior = 0.26 / 0.26 = 1.0 (baseline)
   elo_symmetry = exp(-|1650-1680| / 160) = exp(-0.1875) = 0.829
   h2h_factor = (12/50) / 0.26 = 0.24 / 0.26 = 0.923
   weather_factor = 1.05
   fatigue_factor = 1.0 + max(0, 4-3.5) * 0.04 = 1.02
   referee_factor = 1.0 + (1.0 / 4.5) * 0.08 = 1.018
   odds_drift_factor = 1.0 + 0.1 * 0.15 = 1.015
   xg_factor = 1.08
   
   multiplier = 1.0 × 0.829 × 0.923 × 1.05 × 1.02 × 1.018 × 1.015 × 1.08
              = 1.01 (clipped to bounds)
   
   P(Draw)_adjusted = 0.27 × 1.01 = 0.273
   ```

4. **Temperature Scaling** (temperature=1.2)
   ```
   P_scaled = temperature_scale([0.42, 0.273, 0.33], 1.2)
   P(Home) = 0.41
   P(Draw) = 0.28
   P(Away) = 0.31
   ```

5. **Odds Blending** (if market odds available)
   ```
   Market odds: Home=2.5, Draw=3.2, Away=2.8
   Market probs: [0.40, 0.31, 0.36]
   
   normalized_entropy = 0.95 (high uncertainty)
   alpha_effective = 0.6 × 0.95 = 0.57
   
   P_blended = 0.57 × [0.41, 0.28, 0.31] + 0.43 × [0.40, 0.31, 0.36]
             = [0.406, 0.293, 0.301]
   ```

6. **Calibration** (if calibration model exists)
   ```
   P_calibrated = isotonic_regression(P_blended, calibration_data)
   Final: P(Home)=0.41, P(Draw)=0.30, P(Away)=0.29
   ```

---

## 📈 How Models Are Trained

### **Training Process**

1. **Load Historical Data**
   - From `matches` table
   - Filter by league, season, date range

2. **Calculate Team Strengths**
   - Use Dixon-Coles maximum likelihood estimation
   - Optimize attack_rating and defense_rating for each team
   - Store in `models.model_weights.team_strengths`

3. **Learn Temperature Parameter**
   - Optimize temperature to minimize log loss
   - Store in `models.model_weights.temperature`

4. **Train Calibration Model**
   - Build isotonic regression curves per outcome type
   - Store in `calibration_data` table

5. **Store Model**
   - Save model metadata in `models` table
   - Record training run in `training_runs` table

---

## 🎯 Key Takeaways

1. **Base probabilities** come from Dixon-Coles model using team strengths
2. **Draw probabilities** are enhanced through multiple structural adjustments
3. **All adjustments** are deterministic (no ML training required)
4. **Calibration** is optional and learned from historical data
5. **Multiple probability sets** (A-J) are generated for different use cases
6. **Everything is stored** in `predictions` table for auditability

---

## 📚 Related Files

- **Probability Calculation**: `2_Backend_Football_Probability_Engine/app/api/probabilities.py`
- **Draw Features**: `2_Backend_Football_Probability_Engine/app/features/draw_features.py`
- **Dixon-Coles Model**: `2_Backend_Football_Probability_Engine/app/models/dixon_coles.py`
- **Draw Model**: `2_Backend_Football_Probability_Engine/app/models/draw_model.py`
- **Model Training**: `2_Backend_Football_Probability_Engine/app/services/model_training.py`
- **Database Schema**: `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
- **Team Ratings Analysis**: `15_Football_Data_/TEAM_RATINGS_ANALYSIS.md` ⭐ **READ THIS FIRST**

