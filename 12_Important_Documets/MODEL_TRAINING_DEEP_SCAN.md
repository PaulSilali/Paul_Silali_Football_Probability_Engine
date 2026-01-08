# Model Training Deep Scan: Team Ratings Update Logic

## 🔍 Critical Finding

**The `teams` table is NEVER updated during model training!**

Team ratings (`attack_rating`, `defense_rating`, `last_calculated`) remain at default values (1.0, 1.0, NULL) even after training completes.

---

## 📊 How Model Training Actually Works

### **Step 1: Training Process** (`model_training.py` → `train_poisson_model()`)

```python
# Line 202: Calculate team strengths
team_strengths, home_advantage, rho, training_metadata = trainer.estimate_team_strengths(match_data)

# team_strengths format:
# {
#   team_id: {
#     'attack': 1.35,  # Calculated value
#     'defense': 0.85  # Calculated value
#   },
#   ...
# }

# Line 287-303: Store in model_weights JSONB
model_weights = {
    'team_strengths': cleaned_team_strengths,  # ← Stored here
    'home_advantage': float(home_advantage),
    'rho': float(rho),
    'temperature': float(temp_result['temperature']),
    ...
}

# Line 315-330: Save to models table
model = Model(
    version=version,
    model_type='poisson',
    model_weights=model_weights  # ← JSONB column
)
self.db.add(model)
self.db.commit()
```

**Key Points:**
- ✅ Team strengths ARE calculated correctly
- ✅ Team strengths ARE stored in `models.model_weights['team_strengths']`
- ❌ **Team strengths are NOT stored in `teams.attack_rating` or `teams.defense_rating`**
- ❌ **`teams.last_calculated` is NOT updated**

---

### **Step 2: Team Strength Calculation** (`poisson_trainer.py` → `estimate_team_strengths()`)

```python
# Lines 66-277: Iterative Maximum Likelihood Estimation

# Initialize all teams with attack=1.0, defense=1.0
attack = np.ones(n_teams)
defense = np.ones(n_teams)

# Iterative update (lines 129-243):
for iteration in range(max_iterations):
    # Calculate expected goals
    lambda_home[i] = math.exp(attack[home_idx] - defense[away_idx] + home_advantage)
    lambda_away[i] = math.exp(attack[away_idx] - defense[home_idx])
    
    # Update attack strengths
    new_attack[home_idx] += match['home_goals'] * weight
    attack_denom[home_idx] += lambda_home[i] * weight
    
    # Update defense strengths
    new_defense[home_idx] += match['away_goals'] * weight
    defense_denom[home_idx] += lambda_away[i] * weight
    
    # Normalize (mean = 1.0)
    attack /= np.mean(attack)
    defense /= np.mean(defense)

# Lines 247-253: Convert to dictionary
team_strengths = {}
for idx, team_id in enumerate(team_ids):
    team_strengths[team_id] = {
        'attack': float(attack[idx]),
        'defense': float(defense[idx])
    }

# Return (NOT stored in database here)
return team_strengths, float(home_advantage), float(rho), metadata
```

**Key Points:**
- ✅ Uses iterative proportional fitting (IPF) algorithm
- ✅ Applies time decay weights (recent matches weighted more)
- ✅ Normalizes so mean attack = 1.0, mean defense = 1.0
- ✅ Returns dictionary format
- ❌ **Does NOT update database** (returns values only)

---

### **Step 3: Where Team Strengths Are Stored**

**Location 1: `models.model_weights` (JSONB column)** ✅ **USED**

```sql
SELECT model_weights->'team_strengths' 
FROM models 
WHERE model_type = 'poisson' AND status = 'active';
```

**Example:**
```json
{
  "team_strengths": {
    "1": {"attack": 1.35, "defense": 0.85},
    "2": {"attack": 0.75, "defense": 1.15},
    ...
  },
  "home_advantage": 0.35,
  "rho": -0.13,
  "temperature": 1.2
}
```

**Location 2: `teams.attack_rating` and `teams.defense_rating`** ❌ **NOT UPDATED**

```sql
SELECT attack_rating, defense_rating, last_calculated 
FROM teams 
WHERE id = 1;
-- Returns: 1.0, 1.0, NULL (default values, never updated)
```

---

## 🔄 How Probabilities Are Calculated

### **Priority Order** (`probabilities.py` → `get_team_strength_for_fixture()`)

```python
# Lines 309-391: Team strength resolution logic

def get_team_strength_for_fixture(team_name, team_id):
    # PRIORITY 1: Check model_weights['team_strengths'] (from trained model)
    if team_id in team_strengths_dict:  # ← From model.model_weights
        strengths = team_strengths_dict[team_id]
        return TeamStrength(
            attack=strengths.get('attack', 1.0),
            defense=strengths.get('defense', 1.0)
        )
    
    # PRIORITY 2: Check teams table (fallback)
    if team_id in team_cache:
        team_data = team_cache[team_id]
        return TeamStrength(
            attack=team_data.get('attack_rating', 1.0),  # ← From teams table
            defense=team_data.get('defense_rating', 1.0)  # ← From teams table
        )
    
    # PRIORITY 3: Default (1.0, 1.0)
    return TeamStrength(attack=1.0, defense=1.0)
```

**Key Points:**
- ✅ **System works correctly** - uses model_weights first
- ⚠️ **Fallback to teams table** - but teams table has default values
- ⚠️ **Teams not in model** - will use default 1.0 from teams table

---

## ⚠️ Missing Functionality

### **What Should Happen (But Doesn't)**

After model training completes, the code should:

```python
# THIS CODE DOES NOT EXIST IN model_training.py

# After training completes (around line 358):
# Update teams table with calculated ratings
for team_id, strengths in team_strengths.items():
    team = db.query(Team).filter(Team.id == team_id).first()
    if team:
        team.attack_rating = strengths['attack']
        team.defense_rating = strengths['defense']
        team.last_calculated = datetime.utcnow()
        db.add(team)

db.commit()
```

**Why This Is Missing:**
- Design decision: Store ratings in model JSONB only
- Teams table is treated as "reference data" not "calculated data"
- Model versioning: Different models can have different ratings for same team

---

## 📈 Impact Analysis

### **✅ What Works**

1. **Probability calculations work correctly**
   - Uses `model.model_weights['team_strengths']`
   - Trained ratings are used for predictions

2. **Model versioning works**
   - Each model version has its own team strengths
   - Can compare different model versions

3. **Training is reproducible**
   - Model stores training data hash
   - Can retrain with same data

### **❌ What Doesn't Work**

1. **Direct team queries are inaccurate**
   ```sql
   -- This query will show all teams as equal (attack_rating = 1.0)
   SELECT name, attack_rating, defense_rating 
   FROM teams 
   WHERE attack_rating > 1.2;
   -- Returns: 0 rows (should return strong teams)
   ```

2. **Teams table is misleading**
   - Shows default values (1.0, 1.0) even after training
   - `last_calculated` is NULL for all teams
   - No way to know which teams have been trained

3. **Fallback behavior is suboptimal**
   - Teams not in model use default 1.0
   - Should use teams table if it had actual values

4. **No way to query "strongest teams"**
   - Can't query teams table for top attackers/defenders
   - Must query model JSONB (complex, slow)

---

## 🔧 Recommended Fix

### **Option 1: Update Teams Table After Training** (Recommended)

Add this code to `model_training.py` after line 358:

```python
# Update teams table with calculated ratings
logger.info("Updating teams table with calculated ratings...")
updated_count = 0
for team_id, strengths in team_strengths.items():
    try:
        team = self.db.query(Team).filter(Team.id == team_id).first()
        if team:
            team.attack_rating = float(strengths.get('attack', 1.0))
            team.defense_rating = float(strengths.get('defense', 1.0))
            team.last_calculated = training_completed_utc
            updated_count += 1
    except Exception as e:
        logger.warning(f"Could not update team {team_id}: {e}")

self.db.commit()
logger.info(f"Updated {updated_count} teams with calculated ratings")
```

**Pros:**
- Teams table reflects actual trained values
- Enables direct SQL queries
- Improves fallback behavior
- Better for reporting/analytics

**Cons:**
- Overwrites previous model's ratings
- Only stores latest model's ratings
- Loses model versioning in teams table

### **Option 2: Keep Current Design** (Status Quo)

**Pros:**
- Model versioning preserved
- Each model has its own ratings
- No data loss

**Cons:**
- Teams table is misleading
- Can't query teams directly
- Poor developer experience

### **Option 3: Hybrid Approach** (Best of Both)

Update teams table with latest model's ratings, but also keep model-specific ratings in JSONB:

```python
# Update teams table (latest model only)
for team_id, strengths in team_strengths.items():
    team = self.db.query(Team).filter(Team.id == team_id).first()
    if team:
        team.attack_rating = float(strengths.get('attack', 1.0))
        team.defense_rating = float(strengths.get('defense', 1.0))
        team.last_calculated = training_completed_utc
        # Also store model_id that these ratings came from
        team.last_model_id = model.id  # (would need to add this column)

# Keep model-specific ratings in model_weights (for versioning)
model.model_weights['team_strengths'] = team_strengths
```

**Pros:**
- Teams table has actual values (for queries)
- Model versioning preserved (in model_weights)
- Best of both worlds

**Cons:**
- Slightly more complex
- Requires schema change (add `last_model_id`)

---

## 📝 Current Code Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ 1. MODEL TRAINING (model_training.py)                       │
│    train_poisson_model()                                    │
│    ↓                                                         │
│    PoissonTrainer.estimate_team_strengths()                 │
│    ↓                                                         │
│    Returns: {team_id: {attack, defense}}                    │
│    ↓                                                         │
│    Stores in: models.model_weights['team_strengths'] ✅     │
│    Updates: teams.attack_rating ❌ (NOT DONE)              │
│    Updates: teams.defense_rating ❌ (NOT DONE)              │
│    Updates: teams.last_calculated ❌ (NOT DONE)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PROBABILITY CALCULATION (probabilities.py)               │
│    calculate_probabilities()                                │
│    ↓                                                         │
│    Loads: model.model_weights['team_strengths'] ✅           │
│    Uses: team_strengths_dict[team_id] ✅                    │
│    Fallback: teams.attack_rating (if not in model) ⚠️      │
│    (But teams table has defaults, so fallback = 1.0)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Conclusion

**Current State:**
- ✅ Model training calculates team strengths correctly
- ✅ Team strengths are stored in `models.model_weights` (JSONB)
- ✅ Probability calculations use trained strengths
- ❌ **Teams table is never updated** (remains at defaults)
- ❌ **No way to query teams directly** for strength rankings

**Recommendation:**
Add code to update `teams.attack_rating`, `teams.defense_rating`, and `teams.last_calculated` after training completes. This enables:
- Direct SQL queries on team strengths
- Better fallback behavior
- Improved developer experience
- Accurate reporting/analytics

**Implementation:**
Add the update code to `model_training.py` after line 358 (after model is committed but before returning results).

---

## 📚 Related Files

- **Model Training**: `2_Backend_Football_Probability_Engine/app/services/model_training.py` (lines 105-420)
- **Poisson Trainer**: `2_Backend_Football_Probability_Engine/app/services/poisson_trainer.py` (lines 66-277)
- **Probability Calculation**: `2_Backend_Football_Probability_Engine/app/api/probabilities.py` (lines 309-391)
- **Database Models**: `2_Backend_Football_Probability_Engine/app/db/models.py` (Team model)

