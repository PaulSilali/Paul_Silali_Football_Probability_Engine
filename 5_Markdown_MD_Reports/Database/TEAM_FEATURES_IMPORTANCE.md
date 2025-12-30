# Team Features Importance to Final Predictions

## Overview

The `team_features` table stores **rolling statistics** (last 5/10/20 matches) that provide **contextual information** about team form, but are **NOT directly used** in the current Dixon-Coles probability calculation model.

---

## Current Prediction Model (Dixon-Coles)

### What IS Used:
- **Team Strengths** (`attack_rating`, `defense_rating`) - Learned from historical match data
- **Home Advantage** - League-specific parameter
- **Dixon-Coles Parameters** (`rho`, `xi`) - Model parameters
- **Market Odds** - For blending (Sets B, C)

### What is NOT Used (Currently):
- ❌ Rolling statistics (goals_scored_5, win_rate_5, etc.)
- ❌ Recent form indicators
- ❌ Fatigue metrics (avg_rest_days)
- ❌ League position

**Why?** The Dixon-Coles model uses **long-term team strengths** learned from all historical matches (with time decay), not short-term form.

---

## How Team Features COULD Be Important

### 1. **Explainability & Context**
Team features help **explain** why predictions are made:
- "Arsenal has 80% home win rate in last 5 matches" → Context for high home probability
- "Team has conceded 2.5 goals per game in last 10" → Context for low defense rating
- "Team is 3rd in league" → Context for strong attack rating

### 2. **Feature Engineering for Future Models**
Team features could be used in:
- **Advanced ML Models** (XGBoost, Neural Networks)
- **Form-Based Adjustments** (boost predictions for teams in good form)
- **Fatigue Modeling** (adjust probabilities based on rest days)
- **Contextual Features** (league position, recent head-to-head)

### 3. **Model Selection**
Team features could help choose which probability set to use:
- High form variance → Use Set B (balanced)
- Strong recent form → Use Set E (sharp)
- Inconsistent form → Use Set C (market-dominant)

### 4. **Confidence Indicators**
Team features can indicate prediction confidence:
- High form consistency → Higher confidence
- Recent injury/suspension impact → Lower confidence
- League position stability → Higher confidence

---

## Example Use Cases

### Use Case 1: Explainability Dashboard
```python
# Show why Arsenal has 65% home win probability
team_features = get_team_features(arsenal_id, current_date)
display:
  - "Arsenal: 4 wins in last 5 home matches"
  - "Scored 2.2 goals per game (last 10)"
  - "Conceded 0.8 goals per game (last 10)"
  - "Currently 2nd in Premier League"
```

### Use Case 2: Form-Based Adjustment (Future)
```python
# Boost probability if team is in good form
if team_features.win_rate_5 > 0.7:
    adjusted_probability = base_probability * 1.05  # 5% boost
```

### Use Case 3: Fatigue Modeling (Future)
```python
# Reduce probability if team has short rest
if team_features.avg_rest_days < 3:
    adjusted_probability = base_probability * 0.95  # 5% reduction
```

---

## Current Status

| Feature | Used in Predictions? | Stored in DB? | Calculated? |
|---------|---------------------|---------------|-------------|
| **Team Strengths** (attack/defense) | ✅ Yes | ✅ Yes (in models table) | ✅ Yes (during training) |
| **Rolling Goals** (5/10/20 matches) | ❌ No | ✅ Yes (schema exists) | ❌ No |
| **Win Rates** (5/10 matches) | ❌ No | ✅ Yes (schema exists) | ❌ No |
| **Home/Away Splits** | ❌ No | ✅ Yes (schema exists) | ❌ No |
| **Rest Days** | ❌ No | ✅ Yes (schema exists) | ❌ No |
| **League Position** | ❌ No | ✅ Yes (schema exists) | ❌ No |

---

## Recommendation

### Phase 1: Calculate & Store Features (Current Priority)
- Implement `FeatureCalculationService` to calculate rolling statistics
- Store in `team_features` table for explainability
- Use for dashboard/UI context

### Phase 2: Integrate into Predictions (Future)
- Add form-based adjustments to probability sets
- Use features for confidence indicators
- Implement fatigue modeling

### Phase 3: Advanced Models (Future)
- Use features in ML models (XGBoost, Neural Networks)
- Feature engineering for ensemble methods
- Context-aware probability sets

---

## Conclusion

**Team features are NOT currently used in predictions**, but they are **valuable for**:
1. ✅ **Explainability** - Help users understand predictions
2. ✅ **Context** - Provide additional information about teams
3. ✅ **Future Models** - Foundation for advanced ML models
4. ✅ **Confidence Indicators** - Help assess prediction reliability

**Next Step:** Implement feature calculation service to populate `team_features` table.

