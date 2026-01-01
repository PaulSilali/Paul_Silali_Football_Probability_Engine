# Training Runs Table Empty - Diagnosis & Fix

## Problem
You've run training many times, but `training_runs` table is still empty.

---

## Root Cause Analysis

### How Training Runs Should Be Created

**File:** `app/services/model_training.py` (lines 80-88)

```python
# ---- CREATE TRAINING RUN FIRST (for audit trail) ----
training_run = TrainingRun(
    run_type='poisson',
    status=ModelStatus.training,
    started_at=datetime.utcnow(),
    date_from=date_from,
    date_to=date_to,
)
self.db.add(training_run)
self.db.flush()  # ← Flush but NOT committed yet
```

**Then after training completes (line 283):**
```python
self.db.commit()  # ← Should commit here
```

### The Problem: Background Thread Database Session

**File:** `app/api/model.py` (lines 189-192)

```python
# Create new DB session for background task
from app.db.session import SessionLocal
background_db = SessionLocal()  # ← New session
service = ModelTrainingService(background_db)
```

**Issue:** The background thread uses a separate database session. If:
1. An exception occurs before `commit()`
2. The session is closed before commit
3. The transaction is rolled back
4. The thread dies before commit

Then the `training_run` record is **lost**.

---

## Why It's Happening

### Most Likely Causes:

1. **Exception Before Commit** ⚠️
   - Training fails with an exception
   - Exception handler might rollback
   - `training_run` is lost

2. **Session Closed Prematurely** ⚠️
   - `background_db.close()` called before commit
   - Transaction rolled back

3. **Thread Dies** ⚠️
   - Background thread crashes
   - Session never commits

4. **Different Database** ⚠️
   - Background session connects to different DB
   - Or wrong connection string

---

## How to Diagnose

### Step 1: Check Backend Logs

Look for these log messages after training:

```
=== POISSON MODEL TRAINING COMPLETION ===
Training completed at UTC: ...
Model training_completed_at stored: ...
=== POISSON MODEL TRAINING FINAL STATUS ===
```

**If you see these:** Training completed, but commit might have failed
**If you don't see these:** Training failed before completion

### Step 2: Check Database Connection

Verify the background thread is using the same database:

```python
# Add this to model_training.py after line 88
logger.info(f"Database URL: {self.db.bind.url}")
logger.info(f"Training run ID after flush: {training_run.id}")
```

### Step 3: Check for Exceptions

Look for exception logs:
```
Training failed: ...
Error: ...
```

---

## Fix: Ensure Commit Happens

### Option 1: Add Explicit Commit in Finally Block

**File:** `app/api/model.py` (modify `run_training` function)

```python
def run_training():
    background_db = None
    try:
        # ... existing code ...
        background_db = SessionLocal()
        service = ModelTrainingService(background_db)
        
        # ... training code ...
        
        # Ensure commit happens
        background_db.commit()
        logger.info("Training completed and committed successfully")
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        if background_db:
            background_db.rollback()
        # ... error handling ...
    finally:
        if background_db:
            background_db.close()
```

### Option 2: Use Context Manager

**File:** `app/api/model.py`

```python
from app.db.session import get_db_context

def run_training():
    try:
        with get_db_context() as background_db:
            service = ModelTrainingService(background_db)
            # ... training code ...
            # Context manager auto-commits on success
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
```

### Option 3: Add Commit After Training Run Creation

**File:** `app/services/model_training.py` (line 88)

```python
self.db.add(training_run)
self.db.flush()
self.db.commit()  # ← ADD THIS: Commit immediately after creation
logger.info(f"Training run created: ID={training_run.id}, type={run_type}")
```

This ensures the training run is saved even if training fails later.

---

## Quick Test

Run this SQL query to check if training runs are being created but not committed:

```sql
-- Check for uncommitted transactions (PostgreSQL)
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Check if training_runs table exists and has any rows
SELECT COUNT(*) FROM training_runs;

-- Check models table to see if training actually completed
SELECT id, version, model_type, training_completed_at 
FROM models 
ORDER BY training_completed_at DESC 
LIMIT 5;
```

If `models` table has entries but `training_runs` is empty, the issue is that training runs are created but not committed.

---

## Importance of Tables

### 1. `team_features` Table

**Importance:** ⚠️ **LOW** - Not used by current system

**What it would store:**
- Rolling goal statistics (last 5, 10, 20 matches)
- Win rates and form
- Home/away splits
- League position

**Current Usage:** ❌ **NONE** - Table exists but no code uses it

**Impact if empty:** ✅ **NONE** - System works fine without it

**When you'd need it:**
- Advanced feature engineering
- Form-based predictions
- Team momentum analysis
- **Not needed for current Poisson/Dixon-Coles model**

---

### 2. `league_stats` Table

**Importance:** ⚠️ **LOW** - Not used by current system

**What it would store:**
- League-level baseline statistics per season
- Home win rate, draw rate, away win rate
- Average goals per match
- Home advantage factor

**Current Usage:** ❌ **NONE** - Table exists but no code uses it

**Impact if empty:** ✅ **NONE** - System works fine without it

**When you'd need it:**
- League-specific draw priors (currently hardcoded)
- League-specific home advantage (currently global)
- League comparison analysis
- **Not needed for current model**

---

## Summary

### `training_runs` Table
- **Status:** ❌ **BROKEN** - Should populate but doesn't
- **Fix:** Add immediate commit after creation (Option 3 above)
- **Impact:** ⚠️ **MEDIUM** - Training history not tracked, but training still works

### `team_features` Table
- **Status:** ❌ **Not implemented**
- **Importance:** ⚠️ **LOW** - Not used by system
- **Action:** None needed - optional feature

### `league_stats` Table
- **Status:** ❌ **Not implemented**
- **Importance:** ⚠️ **LOW** - Not used by system
- **Action:** None needed - optional feature

---

## Recommended Fix

**Priority 1:** Fix `training_runs` population (add commit after creation)

**Priority 2:** Ignore `team_features` and `league_stats` (not needed)

The system works fine without `team_features` and `league_stats`. The only critical issue is `training_runs` not populating, which is a bug that should be fixed.

