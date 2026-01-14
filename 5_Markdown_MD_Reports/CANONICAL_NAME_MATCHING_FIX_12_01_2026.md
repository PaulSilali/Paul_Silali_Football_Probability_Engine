# Canonical Name Matching Fix - 12/01/2026

## Summary

Fixed canonical name matching to ensure teams are correctly identified as trained even when team IDs differ between training data and jackpot fixtures.

---

## Problem

After training a model with 24 teams, only 1 team was correctly identified as "trained" because:
1. **Team ID Mismatch**: The same teams had different IDs in training data vs. jackpot fixtures
2. **Missing Canonical Name Matching**: The probability calculation only checked by team ID, not by canonical name
3. **Incomplete Matching Logic**: Canonical name matching existed in `automated_pipeline.py` but not in `probabilities.py`

---

## Solution

### 1. **Added Canonical Name Mapping in Probability Calculation**

**File**: `app/api/probabilities.py`

- Built a `team_strengths_by_canonical_name` mapping from the model's `team_strengths`
- Added canonical name lookup in `get_team_strength_for_fixture()` function
- Checks canonical name if team ID lookup fails

**Code Changes**:
```python
# Build canonical_name mapping from team_strengths_dict for better matching
team_strengths_by_canonical_name = {}
if team_strengths_dict:
    for team_id_str, strength_data in team_strengths_dict.items():
        try:
            team_id_int = int(team_id_str) if isinstance(team_id_str, str) else team_id_str
            team_from_model = db.query(Team).filter(Team.id == team_id_int).first()
            if team_from_model and team_from_model.canonical_name:
                canonical = team_from_model.canonical_name.lower()
                team_strengths_by_canonical_name[canonical] = {
                    'strengths': strength_data,
                    'team_id': team_id_int
                }
        except (ValueError, TypeError):
            continue
```

**Matching Logic**:
```python
# Try canonical name matching if ID didn't match
if canonical_name and canonical_name in team_strengths_by_canonical_name:
    match_info = team_strengths_by_canonical_name[canonical_name]
    strengths = match_info['strengths']
    matched_team_id = match_info['team_id']
    logger.info(f"✓ Found team {team_id} ('{canonical_name}') in model strengths via canonical name match (model team_id: {matched_team_id})")
    return (TeamStrength(...), "model")
```

### 2. **Enhanced Logging in Automated Pipeline**

**File**: `app/services/automated_pipeline.py`

- Added logging to show when canonical name matching is used
- Shows match method (ID vs. canonical name) in status messages
- Logs canonical name mapping count

**Code Changes**:
```python
matched_by_id = (team_id in team_strengths or str(team_id) in team_strengths)
matched_by_canonical = (canonical_name and canonical_name in team_strengths_by_name)
is_in_poisson = matched_by_id or matched_by_canonical

match_method = "ID" if matched_by_id else "canonical name"
logger.info(f"✓ Team '{team_name}' (ID: {team_id}, canonical: '{canonical_name}') is validated and fully trained (Poisson + Calibration) [matched by {match_method}]")
```

---

## How It Works

### Matching Priority:

1. **Team ID Match** (integer key)
   - Check if `team_id` exists in `team_strengths_dict`
   
2. **Team ID Match** (string key)
   - Check if `str(team_id)` exists in `team_strengths_dict`

3. **Canonical Name Match** (NEW)
   - If ID match fails, check if team's `canonical_name` (lowercased) exists in `team_strengths_by_canonical_name`
   - If found, use the strengths from the matched team

4. **Database Ratings** (fallback)
   - If no match found, use database ratings or defaults

---

## Benefits

1. **Resolves Team ID Mismatches**: Teams are correctly identified as trained even when IDs differ
2. **Better Team Matching**: Uses canonical names as a reliable matching key
3. **Improved Logging**: Shows exactly how teams were matched (ID vs. canonical name)
4. **Consistent Behavior**: Both `automated_pipeline.py` and `probabilities.py` now use the same matching logic

---

## Expected Results

After this fix:
- **More teams should be identified as trained** (not just 1 out of 24)
- **Teams using model strengths** should increase significantly
- **Logs will show** when canonical name matching is used
- **Jackpot logs will show** more teams with "trained" status

---

## Testing

To verify the fix works:

1. **Check Logs**: Look for messages like:
   ```
   ✓ Found team 9013 ('magdeburg') in model strengths via canonical name match (model team_id: 8993)
   ```

2. **Check Jackpot Log**: Should show more teams as "trained" instead of "database"

3. **Check Status Check**: Should show more teams as "fully trained" in pipeline status

---

## Files Modified

1. `app/api/probabilities.py`
   - Added canonical name mapping
   - Added canonical name matching in `get_team_strength_for_fixture()`
   - Enhanced logging

2. `app/services/automated_pipeline.py`
   - Enhanced logging to show match method
   - Added canonical name mapping count logging

---

## Conclusion

This fix ensures that teams are correctly identified as trained even when there are team ID mismatches between training data and fixtures. The canonical name serves as a reliable matching key that works across different team ID assignments.

