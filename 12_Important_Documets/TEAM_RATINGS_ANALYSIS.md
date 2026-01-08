# Team Ratings Analysis: attack_rating & defense_rating

## 🔍 Current Database State

### **Findings from SQL Export Analysis**

1. **All teams have `attack_rating = 1.0` and `defense_rating = 1.0`**
   - This is the **DEFAULT value** set in the schema
   - These are **placeholder values**, not actual calculated strengths
   - `last_calculated` is `NULL` for all teams, confirming no training has occurred

2. **Leagues table is populated correctly**
   - 88 leagues with proper codes, names, countries
   - `avg_draw_rate` values are set (0.22-0.29 range)
   - `home_advantage` values are set (0.26-0.38 range)
   - Some leagues have "Unknown" country (data quality issue, but not critical)

3. **Teams table has 3,800+ teams**
   - Teams are properly linked to leagues
   - `canonical_name` is normalized correctly
   - All teams are ready for training, but ratings haven't been calculated yet

---

## 📊 Where Do attack_rating & defense_rating Come From?

### **Source: Model Training (Dixon-Coles Maximum Likelihood Estimation)**

The ratings are **NOT** manually set. They are **calculated** through a training process that:

1. **Uses Historical Match Data**
   - Loads matches from `matches` table
   - Analyzes goals scored/conceded by each team
   - Considers home/away context

2. **Applies Dixon-Coles Model**
   - Uses Maximum Likelihood Estimation (MLE)
   - Iteratively optimizes team strengths to best fit historical results
   - Normalizes so mean attack_rating = 1.0 and mean defense_rating = 1.0

3. **Updates Database**
   - Stores calculated ratings in `teams.attack_rating` and `teams.defense_rating`
   - Updates `teams.last_calculated` timestamp
   - Stores full model in `models.model_weights`

---

## 🧮 How Training Works

### **Mathematical Process**

```python
# Step 1: Initialize all teams with attack=1.0, defense=1.0
# Step 2: For each match in training data:
#   - Calculate expected goals: λ_home, λ_away
#   - Compare to actual goals scored
#   - Adjust team strengths to minimize prediction error

# Iterative update formula:
for each match:
    λ_home = home_attack × away_defense × home_advantage
    λ_away = away_attack × home_defense
    
    # Update attack ratings
    home_attack_new = (home_goals_observed) / (λ_home_expected)
    away_attack_new = (away_goals_observed) / (λ_away_expected)
    
    # Update defense ratings
    home_defense_new = (away_goals_conceded) / (λ_away_expected)
    away_defense_new = (home_goals_conceded) / (λ_home_expected)

# Step 3: Normalize (mean = 1.0)
attack_ratings = attack_ratings / mean(attack_ratings)
defense_ratings = defense_ratings / mean(defense_ratings)
```

### **Example Calculation**

**Before Training:**
- Manchester City: attack=1.0, defense=1.0
- Burnley: attack=1.0, defense=1.0

**After Training (hypothetical):**
- Manchester City: attack=1.35, defense=0.85 (strong attack, weak defense)
- Burnley: attack=0.75, defense=1.15 (weak attack, strong defense)

**Interpretation:**
- City scores 35% more goals than average
- City concedes 15% fewer goals than average
- Burnley scores 25% fewer goals than average
- Burnley concedes 15% more goals than average

---

## ⚠️ Why All Ratings Are 1.0

### **Root Cause: No Model Training Has Been Run**

The database has:
- ✅ Teams populated (3,800+ teams)
- ✅ Leagues populated (88 leagues)
- ✅ Matches populated (103,983 matches from your extraction)
- ❌ **Model training NOT run** (ratings still at defaults)

### **What This Means**

1. **Probability calculations will be inaccurate**
   - All teams treated as equal strength
   - No differentiation between strong/weak teams
   - Draw probabilities will be uniform

2. **Training is required before predictions**
   - Must run model training service
   - Uses historical matches to calculate strengths
   - Updates all team ratings

---

## ✅ How to Fix: Train the Model

### **Step 1: Verify Match Data**

```sql
-- Check if you have enough match data
SELECT 
    league_id,
    COUNT(*) as match_count,
    MIN(match_date) as earliest_match,
    MAX(match_date) as latest_match
FROM matches
GROUP BY league_id
ORDER BY match_count DESC;
```

**Minimum Requirements:**
- At least 100 matches per league for reliable training
- Multiple seasons of data preferred
- Both home and away matches for each team

### **Step 2: Run Model Training**

**Option A: Via Backend API**
```python
# Use the model training service
from app.services.model_training import ModelTrainingService

service = ModelTrainingService(db)
result = service.train_dixon_coles_model(
    leagues=['E0', 'SP1', 'D1', 'I1', 'F1'],  # Top leagues
    seasons=['2020-21', '2021-22', '2022-23', '2023-24'],
    date_from='2020-08-01',
    date_to='2024-05-31'
)
```

**Option B: Via Training Script**
```bash
# Check if training script exists
python -m app.services.model_training --help
```

**Option C: Manual SQL (NOT RECOMMENDED)**
- Training requires complex iterative optimization
- Use the training service instead

### **Step 3: Verify Training Results**

```sql
-- Check if ratings were updated
SELECT 
    name,
    attack_rating,
    defense_rating,
    last_calculated
FROM teams
WHERE league_id = 1  -- Premier League
ORDER BY attack_rating DESC
LIMIT 10;

-- Should show:
-- - attack_rating != 1.0 (for most teams)
-- - defense_rating != 1.0 (for most teams)
-- - last_calculated IS NOT NULL
```

---

## 📈 Expected Results After Training

### **Typical Rating Ranges**

- **Attack Rating**: 0.6 - 1.5
  - 0.6 = Very weak attack (relegation teams)
  - 1.0 = Average attack
  - 1.5 = Very strong attack (top teams)

- **Defense Rating**: 0.7 - 1.3
  - 0.7 = Very weak defense (leaky teams)
  - 1.0 = Average defense
  - 1.3 = Very strong defense (top teams)

### **Example: Premier League After Training**

```
Team                Attack    Defense
----------------------------------------
Manchester City     1.35      0.85
Liverpool           1.30      0.90
Arsenal             1.25      0.95
Chelsea             1.15      1.00
Tottenham           1.10      1.05
... (average teams) ...
Sheffield United    0.75      1.20
Burnley             0.70      1.25
```

---

## 🔧 Database Schema Validation

### **Leagues Table: ✅ GOOD**

**Issues Found:**
- Some leagues have `country='Unknown'` (minor data quality issue)
- Some league codes are non-standard (e.g., 'FC', 'MA1', 'P2')
- Most major leagues are correctly identified

**Recommendations:**
- Update `country` for leagues with 'Unknown'
- Standardize league codes if possible
- Not critical for functionality

### **Teams Table: ✅ GOOD (Structure), ⚠️ NEEDS TRAINING**

**Structure:**
- ✅ All required columns present
- ✅ Foreign keys to leagues correct
- ✅ `canonical_name` normalized properly
- ✅ Unique constraints working

**Data:**
- ⚠️ All `attack_rating = 1.0` (default, needs training)
- ⚠️ All `defense_rating = 1.0` (default, needs training)
- ⚠️ All `last_calculated = NULL` (confirms no training)

**Action Required:**
- **Run model training** to calculate actual ratings

---

## 📝 Summary

### **Current State**
1. ✅ Database structure is correct
2. ✅ Teams and leagues are populated
3. ✅ Match data is available (103,983 matches)
4. ❌ **Team ratings are at default values (1.0)**
5. ❌ **Model training has not been run**

### **What Needs to Happen**
1. **Run model training** using historical match data
2. **Update team ratings** in database
3. **Verify ratings** are reasonable (not all 1.0)
4. **Test probability calculations** with trained model

### **Impact on Probability Generation**
- **Without training**: All teams treated equally → inaccurate probabilities
- **With training**: Teams have realistic strengths → accurate probabilities
- **Draw probabilities**: Will be more accurate with proper team strengths

---

## 🚀 Next Steps

1. **Verify match data is sufficient**
   ```sql
   SELECT COUNT(*) FROM matches;  -- Should be 103,983+
   ```

2. **Run model training**
   - Use `ModelTrainingService.train_dixon_coles_model()`
   - Or backend API endpoint for training

3. **Verify training results**
   ```sql
   SELECT 
       COUNT(*) as total_teams,
       COUNT(CASE WHEN attack_rating != 1.0 THEN 1 END) as trained_teams,
       AVG(attack_rating) as avg_attack,
       AVG(defense_rating) as avg_defense
   FROM teams;
   ```

4. **Update documentation** with training results

---

## 📚 Related Files

- **Training Service**: `2_Backend_Football_Probability_Engine/app/services/model_training.py`
- **Poisson Trainer**: `2_Backend_Football_Probability_Engine/app/services/poisson_trainer.py`
- **Database Schema**: `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
- **Probability Generation**: `15_Football_Data_/PROBABILITY_AND_DRAW_GENERATION_EXPLAINED.md`

