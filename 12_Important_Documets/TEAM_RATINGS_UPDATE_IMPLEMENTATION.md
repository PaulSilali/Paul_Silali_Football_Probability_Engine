# Team Ratings Update Implementation

## ✅ Implementation Complete

The `teams` table is now updated with calculated `attack_rating`, `defense_rating`, and `home_bias` values after model training completes.

---

## 📝 Changes Made

### **File Modified**: `2_Backend_Football_Probability_Engine/app/services/model_training.py`

1. **Added Team Import** (Line 12):
   ```python
   from app.db.models import Model, ModelStatus, TrainingRun, Match, League, Team
   ```

2. **Added Team Update Logic** (After line 358):
   - Updates `teams.attack_rating` with calculated attack strength
   - Updates `teams.defense_rating` with calculated defense strength
   - Updates `teams.home_bias` with team-specific home advantage bias
   - Updates `teams.last_calculated` with training completion timestamp
   - Handles extremely small defense values (safeguard against numerical precision issues)

3. **Added Home Bias Calculation Method** (`_calculate_team_home_bias`):
   - Calculates team-specific home bias by comparing home vs away performance
   - Requires minimum 10 home and 10 away matches for reliable calculation
   - Returns bias value in range [-0.2, +0.2] relative to global home advantage

---

## 🔧 Implementation Details

### **Update Logic Flow**

```python
# After model is committed (line 358)
# 1. Iterate through all team_strengths from training
for team_id, strengths in team_strengths.items():
    # 2. Query team from database
    team = self.db.query(Team).filter(Team.id == team_id_int).first()
    
    # 3. Extract attack and defense values
    attack_value = float(strengths.get('attack', 1.0))
    defense_value = float(strengths.get('defense', 1.0))
    
    # 4. Apply safeguard for extremely small defense values
    if defense_value < 1e-10:
        defense_value = 0.01  # Minimum threshold
    
    # 5. Calculate team-specific home bias
    home_bias_value = self._calculate_team_home_bias(
        team_id_int, 
        match_data, 
        home_advantage
    )
    
    # 6. Update team record
    team.attack_rating = attack_value
    team.defense_rating = defense_value
    team.home_bias = home_bias_value
    team.last_calculated = training_completed_utc

# 7. Commit updates
self.db.commit()
```

### **Home Bias Calculation**

The `_calculate_team_home_bias` method calculates team-specific home advantage by:

1. **Collecting Match Data**: Separates home and away matches for each team
2. **Calculating Performance**: Computes average goal differential for home vs away matches
3. **Deriving Bias**: Calculates the difference in performance (home_gd - away_gd) / 2.0
4. **Clipping Range**: Constrains bias to [-0.2, +0.2] relative to global home advantage

```python
def _calculate_team_home_bias(
    self, 
    team_id: int, 
    match_data: List[Dict],
    global_home_advantage: float
) -> float:
    """
    Calculate team-specific home bias by comparing home vs away performance.
    
    Returns:
        Team-specific home bias (deviation from global home advantage)
        Range: typically -0.2 to +0.2 (relative to global 0.35)
    """
    # Requires minimum 10 home and 10 away matches
    # Returns 0.0 if insufficient data
    
    home_gd = avg(home_goals - away_goals for home matches)
    away_gd = avg(away_goals - home_goals for away matches)
    
    performance_diff = (home_gd - away_gd) / 2.0
    home_bias = max(-0.2, min(0.2, performance_diff))
    
    return home_bias
```

**Example:**
- Team with strong home record: `home_bias = +0.15` (effective home advantage = 0.35 + 0.15 = 0.50)
- Team with similar home/away: `home_bias = 0.0` (uses global 0.35)
- Team with weak home record: `home_bias = -0.10` (effective home advantage = 0.35 - 0.10 = 0.25)

### **Key Features**

1. **Idempotent**: Can be run multiple times safely
2. **Error Handling**: Continues updating other teams if one fails
3. **Logging**: Comprehensive logging of update process
4. **Safeguard**: Handles extremely small defense values (see below)

---

## ⚠️ Defense Value Issue

### **Problem Identified**

The provided JSON snippet shows defense values that are extremely small (effectively zero):

```json
{
  "1": {
    "attack": 2.297837357964623,
    "defense": 0.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008938995806888702
  }
}
```

### **Possible Causes**

1. **Numerical Precision Issue**: The iterative proportional fitting algorithm may be producing values that are too small due to floating-point precision limits.

2. **Normalization Issue**: The defense normalization (mean = 1.0) might be causing issues if some teams have very high expected goals conceded.

3. **Training Data Issue**: If the training data has imbalanced goal distributions, the algorithm might converge to extreme values.

4. **Algorithm Issue**: The defense calculation in `poisson_trainer.py` (lines 166-188) might have a bug:
   ```python
   # Defense update formula:
   defense[idx] = new_defense[idx] / defense_denom[idx]
   ```
   If `defense_denom` is very large (high expected goals), defense becomes very small.

### **Safeguard Implemented**

The implementation includes a safeguard that sets a minimum defense value of `0.01` if the calculated value is less than `1e-10`:

```python
if defense_value < 1e-10:
    logger.warning(f"Team {team_id_int} ({team.name}) has extremely small defense value ({defense_value}), setting to minimum 0.01")
    defense_value = 0.01
```

This prevents:
- Division by zero errors in probability calculations
- Invalid probability distributions
- Numerical instability

### **Recommendation for Further Investigation**

1. **Check Training Data**: Verify that the training data has balanced goal distributions
2. **Review Algorithm**: Investigate the defense calculation in `poisson_trainer.py` (lines 166-188)
3. **Add Logging**: Add more detailed logging during training to track defense values
4. **Consider Alternative Normalization**: The current normalization (mean = 1.0) might need adjustment

---

## 📊 Expected Behavior After Implementation

### **Before Training**
```sql
SELECT id, name, attack_rating, defense_rating, home_bias, last_calculated 
FROM teams 
WHERE id = 1;
-- Returns: 1, 'Brighton', 1.0, 1.0, 0.0, NULL
```

### **After Training**
```sql
SELECT id, name, attack_rating, defense_rating, home_bias, last_calculated 
FROM teams 
WHERE id = 1;
-- Returns: 1, 'Brighton', 2.297, 0.01, 0.12, '2026-01-08 12:00:00'
```

### **Benefits**

1. **Direct SQL Queries**: Can now query teams by strength
   ```sql
   SELECT name, attack_rating 
   FROM teams 
   WHERE attack_rating > 1.5 
   ORDER BY attack_rating DESC;
   ```

2. **Better Fallback**: Probability calculation fallback now uses actual trained values instead of defaults

3. **Reporting**: Can generate reports on team strengths without querying JSONB

4. **Analytics**: Enables team strength analytics and visualizations

---

## 🔍 Verification Steps

1. **Run Model Training**: Execute the training process
2. **Check Logs**: Look for "Updating teams table with calculated ratings..." message
3. **Query Database**: Verify that `teams.attack_rating`, `teams.defense_rating`, and `teams.last_calculated` are updated
4. **Check for Warnings**: Look for warnings about extremely small defense values

### **SQL Verification Query**

```sql
-- Check updated teams
SELECT 
    id, 
    name, 
    attack_rating, 
    defense_rating, 
    home_bias,
    last_calculated,
    CASE 
        WHEN last_calculated IS NOT NULL THEN 'Updated'
        ELSE 'Not Updated'
    END AS status
FROM teams
ORDER BY last_calculated DESC NULLS LAST
LIMIT 20;
```

### **Query Teams by Home Bias**

```sql
-- Teams with strongest home advantage
SELECT 
    name, 
    home_bias,
    (0.35 + home_bias) AS effective_home_advantage
FROM teams
WHERE last_calculated IS NOT NULL
ORDER BY home_bias DESC
LIMIT 10;

-- Teams with weakest home advantage
SELECT 
    name, 
    home_bias,
    (0.35 + home_bias) AS effective_home_advantage
FROM teams
WHERE last_calculated IS NOT NULL
ORDER BY home_bias ASC
LIMIT 10;
```

---

## 📚 Related Files

- **Model Training**: `2_Backend_Football_Probability_Engine/app/services/model_training.py` (lines 358-405)
- **Poisson Trainer**: `2_Backend_Football_Probability_Engine/app/services/poisson_trainer.py` (lines 166-188)
- **Database Models**: `2_Backend_Football_Probability_Engine/app/db/models.py` (Team model, lines 71-92)
- **Deep Scan Report**: `12_Important_Documets/MODEL_TRAINING_DEEP_SCAN.md`

---

## 🎯 Summary

✅ **Implementation Complete**: Teams table is now updated after training  
✅ **Attack Rating**: Updated with calculated attack strength  
✅ **Defense Rating**: Updated with calculated defense strength  
✅ **Home Bias**: Updated with team-specific home advantage bias  
✅ **Safeguard Added**: Handles extremely small defense values  
⚠️ **Issue Identified**: Defense values are extremely small (needs investigation)  
📝 **Next Steps**: Investigate defense calculation algorithm and training data

### **What Gets Updated**

| Column | Source | Description |
|--------|--------|-------------|
| `attack_rating` | `team_strengths[team_id]['attack']` | Attack strength from Poisson model |
| `defense_rating` | `team_strengths[team_id]['defense']` | Defense strength from Poisson model |
| `home_bias` | `_calculate_team_home_bias()` | Team-specific home advantage deviation |
| `last_calculated` | `training_completed_utc` | Timestamp of last training completion |

