# Data Download Verification Report - 12/01/2026

## Summary of Findings

### ✅ **Guide Section "Why Teams Still Show Need Training" (Lines 191-194)**

**Status**: ✅ **ACCURATE** - The section correctly identifies possible issues:
1. Model Not Activated ✅ Fixed with `expire_all()`
2. Session Cache ✅ Fixed with `expire_all()`
3. Team IDs Mismatch (check logs)
4. Model Not Committed (check training logs)
5. **NEW**: Teams Not in Training Data (need more historical data)

**Recommendation**: Section is correct. Added one more possible issue (#5).

---

### ❌ **xG Data and League Priors (Lines 135-150)**

**Status**: ✅ **CORRECT - These are OPTIONAL, not required**

#### **xG Data**
- **Required for Probability Calculation**: ❌ **NO**
- **Impact if Missing**: Draw structural adjustments use fallback values
- **Action**: Can ignore if probabilities are working

#### **League Priors**
- **Required for Probability Calculation**: ❌ **NO**
- **Impact if Missing**: System uses default draw rate (~25%) or hardcoded defaults per league
- **Fallback**: Code has hardcoded defaults in `draw_prior.py` (E0: 0.08, SP1: 0.10, etc.)
- **Action**: Can ignore if probabilities are working, but accuracy may be slightly lower

#### **Historical Match Data**
- **Required for Probability Calculation**: ✅ **YES** (needed for model training)
- **When Downloaded**: During automated pipeline run (Step 3)
- **Action**: Ensure pipeline runs before calculating probabilities

**Conclusion**: ✅ **No need to download xG or league priors** - they're optional enhancements. System works without them.

---

### ⚠️ **Team Injuries Table**

**Status**: ⚠️ **Table is empty** (as reported)

**Impact**:
- Injuries are **OPTIONAL** for probability calculation
- System will still calculate probabilities without injury data
- Injury data improves accuracy but is not required

**How Injuries Are Downloaded**:
- Automatically downloaded during probability calculation **IF**:
  1. API-Football API key is configured (`API_FOOTBALL_KEY` in settings)
  2. Injury data is missing for the fixture
  3. Both home and away team IDs are available

**To Enable Injury Downloads**:
1. Set `API_FOOTBALL_KEY` in environment variables or config
2. System will automatically download injuries when calculating probabilities

**Action**: 
- If you have API-Football key: Set it and injuries will auto-download
- If you don't have key: Can ignore - probabilities work without injuries

---

## ✅ **Data That IS Automatically Downloaded**

The following data **IS** automatically downloaded during probability calculation:

1. **Weather Data** ✅
   - Auto-downloaded if missing
   - Source: Open-Meteo API (free, no key needed)

2. **Rest Days** ✅
   - Auto-calculated if missing
   - Source: Calculated from matches table

3. **Team Form** ✅
   - Auto-calculated on-the-fly
   - Source: Calculated from matches table

4. **Odds Movement** ✅
   - Auto-tracked if missing
   - Source: Current odds from fixture

5. **Injuries** ✅ (if API key set)
   - Auto-downloaded if missing and API key configured
   - Source: API-Football

---

## 📊 **Testing Data Downloads**

To test if data has been downloaded for 12/01/2026:

### **Option 1: Check Database Directly**

```sql
-- Check team injuries
SELECT COUNT(*) FROM team_injuries;
SELECT MIN(created_at), MAX(created_at) FROM team_injuries;

-- Check match weather
SELECT COUNT(*) FROM match_weather;
SELECT MIN(created_at), MAX(created_at) FROM match_weather;

-- Check rest days
SELECT COUNT(*) FROM team_rest_days;
SELECT MIN(created_at), MAX(created_at) FROM team_rest_days;

-- Check fixtures on 12/01/2026
SELECT COUNT(*) FROM matches WHERE match_date = '2026-01-12';
SELECT COUNT(*) FROM matches WHERE match_date = '2026-01-11';
```

### **Option 2: Run Test Script**

```bash
python scripts/test_data_downloads_12_01_2026.py
```

---

## 🎯 **Recommendations**

1. ✅ **xG Data**: Ignore - not required
2. ✅ **League Priors**: Ignore - has fallbacks
3. ⚠️ **Team Injuries**: 
   - If you have API-Football key: Set it to enable auto-download
   - If you don't: Can ignore - probabilities work without it
4. ✅ **Weather/Rest Days/Form**: Already auto-downloaded (if missing)
5. ✅ **Historical Match Data**: Ensure pipeline runs before calculating probabilities

---

## ✅ **Conclusion**

**System is working correctly**. The following are **OPTIONAL** and not required:
- ❌ xG Data
- ❌ League Priors (has fallbacks)
- ❌ Team Injuries (optional enhancement)

**Required data** is automatically downloaded:
- ✅ Weather (if missing)
- ✅ Rest Days (if missing)
- ✅ Team Form (calculated)
- ✅ Odds Movement (if missing)
- ✅ Historical Match Data (during pipeline)

**Action Required**: None, unless you want to enable injury downloads (requires API key).

