# Team Training Status Analysis - 12/01/2026

## Summary

After running the automated pipeline and training a new Poisson model, the system shows that only **1 out of 26 teams** is marked as "trained", despite the model being trained with **24 teams**.

---

## Findings from Logs

### 1. **Model Training Completed Successfully**

From terminal logs (lines 220-267):
- ✅ Poisson model trained: ID=39, version=poisson-20260112-172214
- ✅ Model trained with **24 teams** (line 232: "Estimated strengths for 24 teams")
- ✅ Model has 24 team strengths in `model_weights` (line 414)
- ✅ Blending and Calibration models also trained successfully

### 2. **Team Status Check After Training**

From terminal logs (lines 514-550):
- Active model has **24 teams** in `team_strengths` (line 515)
- But only **1 team** shows as "fully trained" (line 548)
- **25 teams** show as "untrained" (line 549)

### 3. **Jackpot Log Analysis**

From `jackpot_JK-1768238487_20260112_202355_SUMMARY.txt`:
- **Teams Trained: 1** (Team ID: 8993 - Magdeburg)
- **Teams Using DB Ratings: 25**
- **Teams Using Defaults: 0**

### 4. **Team ID Mismatch Issue**

The problem is clear from comparing the logs:

**Before Training (lines 17-43):**
- Magdeburg: ID 8993 ✓ (trained)
- Werder Bremen: ID 8991 ✓ (trained)
- Eintracht Frankfurt: ID 8990 ✓ (trained)

**After Training (lines 521-543):**
- Magdeburg: ID 9310 ✗ (NOT trained - different ID!)
- Werder Bremen: ID 9268 ✓ (trained - different ID!)
- Eintracht Frankfurt: ID 9696 ✗ (NOT trained - different ID!)

**The Issue:**
- The same team names are resolving to **different team IDs** in different contexts
- The model was trained with one set of team IDs
- The jackpot fixtures are using different team IDs for the same teams
- This causes the training status check to fail

---

## Root Cause

The problem is a **team ID mismatch** between:
1. **Training data**: Teams resolved during model training get certain IDs
2. **Jackpot fixtures**: Teams resolved when creating fixtures get different IDs
3. **Status check**: The system checks if fixture team IDs match model team IDs

This happens because:
- `resolve_team_safe()` may create new teams or find existing teams with different IDs
- Teams might have multiple records in the database (duplicates)
- The canonical name matching might not be working correctly in all contexts

---

## Evidence from Logs

### Training Phase:
```
Line 232: Estimated strengths for 24 teams
Line 414: Poisson model has 24 team strengths in model_weights
```

### Probability Calculation:
```
Line 500: Team matching stats: {'found': 0, 'not_found': 0, 'model_strengths': 1, 'db_strengths': 4, 'default_strengths': 21}
Line 502: Teams using default strengths: 21
Line 503: Teams using model strengths: 1
Line 504: Teams using DB strengths: 4
```

### Status Check After Training:
```
Line 515: Active model has 24 teams in team_strengths
Line 548: Trained teams: 1
Line 549: Untrained teams: 25
```

---

## Impact

1. **Only 1 team** (Magdeburg, ID: 8993) is correctly identified as trained
2. **25 teams** are incorrectly marked as untrained, even though they were in the training data
3. **21 teams** are using default strengths instead of model strengths
4. **4 teams** are using DB ratings instead of model strengths

---

## Recommended Fixes

### 1. **Improve Canonical Name Matching**
   - Ensure canonical name matching works in all contexts
   - Add logging to show when canonical name matching is used
   - Verify canonical names are set correctly for all teams

### 2. **Fix Team ID Resolution**
   - Ensure `resolve_team_safe()` returns consistent team IDs
   - Prevent duplicate team creation
   - Use canonical name as primary matching key, not just team name

### 3. **Add Diagnostic Logging**
   - Log which team IDs are in the model's `team_strengths`
   - Log which team IDs are being checked
   - Log when canonical name matching succeeds/fails

### 4. **Database Cleanup**
   - Identify and merge duplicate team records
   - Ensure each team has a unique canonical name
   - Verify team IDs are consistent across fixtures and training data

---

## Next Steps

1. Run the diagnostic script to identify exact team ID mismatches
2. Check for duplicate teams in the database
3. Verify canonical names are set for all teams
4. Fix the team resolution logic to use canonical names consistently
5. Re-run training and verify all teams are correctly identified as trained

---

## Conclusion

The model training completed successfully with 24 teams, but the team status check is failing due to team ID mismatches. The canonical name matching feature exists but may not be working correctly in all contexts. This needs to be fixed to ensure teams are correctly identified as trained after model training.

