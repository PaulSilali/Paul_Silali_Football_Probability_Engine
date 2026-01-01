# Database Table Population Analysis

## Deep Scan Results: Why Tables Are Empty

---

## 1. `training_runs` Table

### ✅ **IS POPULATED** - But may be empty if no training has run

**Who Populates It:**
- `ModelTrainingService` in `app/services/model_training.py`

**When It's Populated:**
1. **Before Training Starts** (Line 80-88):
   ```python
   training_run = TrainingRun(
       run_type='poisson',
       status=ModelStatus.training,
       started_at=datetime.utcnow(),
       date_from=date_from,
       date_to=date_to,
   )
   self.db.add(training_run)
   self.db.flush()
   ```

2. **After Training Completes** (Lines 279-287):
   ```python
   training_run.model_id = model.id
   training_run.status = ModelStatus.active
   training_run.completed_at = training_completed_utc
   training_run.match_count = len(match_data)
   training_run.brier_score = metrics['brierScore']
   training_run.log_loss = metrics['logLoss']
   training_run.validation_accuracy = metrics.get('overallAccuracy', 65.0)
   training_run.temperature = temp_result['temperature']
   ```

**Why It Might Be Empty:**
- ❌ **No training has been run yet** - Most likely reason
- ❌ Training failed before creating the record (unlikely, as it's created first)
- ❌ Database transaction rolled back
- ❌ Wrong database connection

**How to Populate:**
1. Run model training via ML Training page
2. Or call `/api/model/train` API endpoint
3. Training runs are created automatically when training starts

**Status:** ✅ **Working as designed** - Empty because no training has completed yet

---

## 2. `team_h2h_stats` Table

### ⚠️ **LAZY POPULATION** - Only populated when needed

**Who Populates It:**
- `compute_h2h_stats()` function in `app/services/h2h_service.py`

**When It's Populated:**
- **On-demand** when ticket generation needs H2H data
- Called from `ticket_generation_service.py` (line 77-82):
  ```python
  h2h = get_h2h_stats(self.db, home_team_id, away_team_id)
  if not h2h:
      # Compute and cache if not found
      h2h = compute_h2h_stats(self.db, home_team_id, away_team_id, league_id)
  ```

**How It Works:**
1. `get_h2h_stats()` checks if H2H stats exist in cache
2. If not found, `compute_h2h_stats()` calculates from `matches` table
3. Results are stored in `team_h2h_stats` for future use
4. Only computed for pairs with >= 8 meetings and within 5 years

**Why It's Empty:**
- ✅ **This is normal** - H2H stats are computed lazily
- Only populated when:
  - Ticket generation is triggered
  - A specific team pair is requested
  - The pair meets criteria (>= 8 meetings, within 5 years)

**How to Populate:**
1. **Automatic:** Generate tickets for a jackpot (will populate as needed)
2. **Manual:** Create a script to precompute all H2H stats:
   ```python
   from app.services.h2h_service import compute_h2h_stats
   # Loop through all team pairs and compute
   ```

**Status:** ✅ **Working as designed** - Lazy loading is intentional

---

## 3. `team_features` Table

### ❌ **NOT IMPLEMENTED** - No code populates this table

**Who Should Populate It:**
- **Feature Calculation Service** (does not exist)

**Current Status:**
- ✅ Table exists in database schema
- ✅ Model defined in `app/db/models.py` (lines 132-163)
- ❌ **No service or code populates it**
- ❌ Not used anywhere in the codebase

**What It's Supposed to Store:**
- Rolling goal statistics (last 5, 10, 20 matches)
- Win rates and draw rates
- Home/away splits
- League position
- Rest days

**Why It's Empty:**
- ❌ **Feature calculation service was never implemented**
- This was planned but not built

**How to Populate (If Needed):**
1. Create a feature calculation service
2. Calculate rolling statistics from `matches` table
3. Store snapshots in `team_features` table
4. Run periodically or on-demand

**Status:** ❌ **Not implemented** - Table exists but unused

---

## 4. `league_stats` Table

### ❌ **NOT IMPLEMENTED** - No code populates this table

**Who Should Populate It:**
- **League Statistics Service** (does not exist)

**Current Status:**
- ✅ Table exists in database schema
- ❌ **No model defined in `app/db/models.py`**
- ❌ **No service or code populates it**
- ❌ Not used anywhere in the codebase

**What It's Supposed to Store:**
- League-level baseline statistics per season
- Home win rate, draw rate, away win rate
- Average goals per match
- Home advantage factor

**Why It's Empty:**
- ❌ **League statistics service was never implemented**
- This was planned but not built

**How to Populate (If Needed):**
1. Create a league statistics service
2. Calculate statistics from `matches` table grouped by league and season
3. Store in `league_stats` table
4. Run periodically or on-demand

**Status:** ❌ **Not implemented** - Table exists but unused

---

## Summary Table

| Table | Status | Who Populates | When | Why Empty? |
|-------|--------|---------------|------|------------|
| **training_runs** | ✅ Working | `ModelTrainingService` | When training starts | No training run yet |
| **team_h2h_stats** | ✅ Working | `h2h_service.compute_h2h_stats()` | On-demand (lazy) | Normal - populated when needed |
| **team_features** | ❌ Not Implemented | None | Never | Feature service not built |
| **league_stats** | ❌ Not Implemented | None | Never | League stats service not built |

---

## Recommendations

### 1. **training_runs** - ✅ No Action Needed
- This will populate automatically when you run training
- If you've trained but it's still empty, check:
  - Database connection
  - Transaction commits
  - Training actually completed

### 2. **team_h2h_stats** - ✅ No Action Needed (Optional Precomputation)
- Working as designed (lazy loading)
- Optional: Create a script to precompute all H2H stats for faster ticket generation

### 3. **team_features** - ⚠️ Optional Implementation
- Not critical for current functionality
- Would be useful for advanced features
- Can be implemented later if needed

### 4. **league_stats** - ⚠️ Optional Implementation
- Not critical for current functionality
- Would be useful for league-specific baselines
- Can be implemented later if needed

---

## Quick Fix: Precompute H2H Stats

If you want to populate `team_h2h_stats` proactively, create a script:

```python
# scripts/precompute_h2h_stats.py
from app.db.session import SessionLocal
from app.db.models import Team, Match
from app.services.h2h_service import compute_h2h_stats

db = SessionLocal()

# Get all unique team pairs from matches
teams = db.query(Team).all()
team_ids = [t.id for t in teams]

pairs_computed = 0
for i, home_id in enumerate(team_ids):
    for away_id in team_ids[i+1:]:
        # Check if they've met
        matches = db.query(Match).filter(
            ((Match.home_team_id == home_id) & (Match.away_team_id == away_id)) |
            ((Match.home_team_id == away_id) & (Match.away_team_id == home_id))
        ).count()
        
        if matches >= 8:  # Only compute if >= 8 meetings
            compute_h2h_stats(db, home_id, away_id)
            pairs_computed += 1

print(f"Computed H2H stats for {pairs_computed} team pairs")
```

---

## Conclusion

- **training_runs**: Empty because no training has run (normal)
- **team_h2h_stats**: Empty because lazy loading (normal, will populate when needed)
- **team_features**: Empty because not implemented (optional feature)
- **league_stats**: Empty because not implemented (optional feature)

**Action Required:** None for current functionality. All tables that are needed are either working or will populate automatically when used.

