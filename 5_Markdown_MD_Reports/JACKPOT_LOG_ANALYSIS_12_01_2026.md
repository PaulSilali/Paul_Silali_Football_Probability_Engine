# Jackpot Log Analysis - 12/01/2026

## Most Recent Jackpot: JK-1768239524

**Timestamp**: 2026-01-12T20:39:57.165382  
**Model**: calibration-20260112-203942 (ID: 44)

---

## Summary

### ✅ Improvements
- **Teams Trained: 2** (up from 1 in previous jackpot)
  - Team ID: 8993 (Magdeburg)
  - Team ID: 9268 (Werder Bremen)

### ⚠️ Issues Found

1. **Probability Source Mismatch**:
   - **From Trained Model: 0 (0.0%)** ❌
   - **From DB Ratings: 13 (100.0%)** 
   - **From Defaults: 0 (0.0%)**

   **Problem**: Even though 2 teams are marked as "trained" with `strength_source: "model"`, the summary shows 0% from trained model. This suggests a counting/aggregation issue in the jackpot logger.

2. **Still Low Team Training Coverage**:
   - Only **2 out of 26 teams** (7.7%) are identified as trained
   - **24 teams** still using database ratings
   - Model was trained with **24 teams**, so we should see more matches

3. **Canonical Name Matching**:
   - No evidence in logs that canonical name matching is being used
   - Need to verify if canonical names are set correctly for all teams

---

## Data Ingestion Status

✅ **Good**:
- Weather: 13/13 fixtures (100%)
- Rest Days: 13/13 fixtures (100%)
- Team Form: 3/13 fixtures (23%)

❌ **Missing**:
- Injuries: 0/13 fixtures (0%) - Expected if API key not working or no injury data available
- Odds Movement: 0/13 fixtures (0%)

---

## Teams Status

### Trained Teams (2):
1. **Team ID: 8993** (Magdeburg) - Fixture 2, Away Team
2. **Team ID: 9268** (Werder Bremen) - Fixture 11, Home Team

### Teams Using DB Ratings (24):
- All other teams are using database ratings instead of model strengths

---

## Recommendations

### 1. **Fix Probability Source Counting**
   - The jackpot logger's probability source calculation is incorrect
   - It should count fixtures where at least one team uses model strengths as "From Trained Model"
   - Currently showing 0% even though 2 teams are using model strengths

### 2. **Investigate Canonical Name Matching**
   - Check if canonical names are set for all teams in the database
   - Verify canonical name matching is actually being triggered
   - Add more logging to show when canonical name matching succeeds

### 3. **Check Team ID Consistency**
   - Verify why only 2 teams match when model has 24 teams
   - Check if there are duplicate teams with different IDs
   - Ensure canonical names are consistent across team records

### 4. **Verify Model Training**
   - Confirm which team IDs are actually in the model's `team_strengths`
   - Compare with fixture team IDs to identify mismatches
   - Use the diagnostic script to find exact ID differences

---

## Next Steps

1. Run diagnostic script to identify team ID mismatches
2. Fix probability source counting in jackpot logger
3. Verify canonical names are set for all teams
4. Check if canonical name matching is working correctly
5. Investigate why only 2/24 teams match

---

## Conclusion

The canonical name matching fix has been implemented, but we're only seeing 2 teams matched (up from 1). The probability source counting is also incorrect. Further investigation is needed to:
- Verify canonical names are set correctly
- Ensure canonical name matching is working
- Fix the probability source aggregation logic

