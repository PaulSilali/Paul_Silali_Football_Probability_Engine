# API Key and Injuries Fix - 12/01/2026

## Summary

Fixed multiple issues related to data tracking flags and team ID matching.

---

## ✅ Fixes Applied

### 1. **Weather Tracking Flag** ✅
- **Problem**: `weather_downloaded` flag was not set when weather already existed or was successfully downloaded
- **Fix**: 
  - Set `weather_downloaded = True` when weather already exists in database
  - Set `weather_downloaded = True` when weather is successfully downloaded
  - Set `weather_error` when download fails
- **Location**: `app/api/probabilities.py` lines 663-702 (both occurrences)

### 2. **Rest Days Tracking Flag** ✅
- **Problem**: `rest_days_calculated` flag was not set when rest days already existed
- **Fix**: Set `rest_days_calculated = True` when rest days already exist in database
- **Location**: `app/api/probabilities.py` lines 713-744 (both occurrences)

### 3. **Injuries Tracking Flag** ✅
- **Problem**: `injuries_downloaded` flag was not set when injuries already existed or were successfully downloaded
- **Fix**: 
  - Set `injuries_downloaded = True` when injuries already exist in database
  - Set `injuries_downloaded = True` when injuries are successfully downloaded
  - Set `injuries_error` when download fails
- **Location**: `app/api/probabilities.py` lines 756-799 (both occurrences)

### 4. **Odds Movement Tracking Flag** ✅
- **Problem**: `odds_tracked` flag was not set when odds movement already existed
- **Fix**: 
  - Set `odds_tracked = True` when odds movement already exists in database
  - Set `odds_tracked = True` when odds movement is successfully tracked
  - Set `odds_error` when tracking fails
- **Location**: `app/api/probabilities.py` lines 801-832 (both occurrences)

### 5. **Team ID Mismatch Fix** ✅
- **Problem**: Teams in jackpot have different IDs than teams in training data, causing "untrained" status even after training
- **Root Cause**: Training status check only used team IDs, but same team name can have different IDs
- **Fix**: 
  - Added `team_strengths_by_name` mapping using canonical_name
  - Check training status by both ID and canonical_name
  - This allows matching teams even if they have different IDs
- **Location**: `app/services/automated_pipeline.py` lines 61-81

---

## 🔍 API Key Configuration

### Current Status
- **API Key Location**: `app/config.py` lines 175-181
- **Behavior**: 
  1. First checks if `API_FOOTBALL_KEY` is set in settings
  2. If not, checks environment variable `API_FOOTBALL_KEY`
  3. If still not set, uses hardcoded fallback: `b41227796150918ad901f64b9bdf3b76`
- **Hardcoded Key**: `b41227796150918ad901f64b9bdf3b76` (line 181)

### Recommendation
- **For Development**: Hardcoded key is acceptable
- **For Production**: 
  - Remove hardcoded key
  - Require API key to be set in environment variables or `.env` file
  - Document in README or deployment guide

### How to Set Your Own API Key
1. Get API key from RapidAPI: https://rapidapi.com/api-sports/api/api-football
2. Add to `.env` file:
   ```
   API_FOOTBALL_KEY=your_api_key_here
   ```
3. Or set as environment variable:
   ```bash
   export API_FOOTBALL_KEY=your_api_key_here
   ```

---

## 🧪 Testing

### Test Script Created
- **File**: `scripts/test_injuries_download_12_01_2026.py`
- **Purpose**: Verify API key configuration and injuries download functionality
- **Tests**:
  1. API key configuration
  2. Injuries in database
  3. Injury download functionality

### How to Run Test
```bash
cd "2_Backend_Football_Probability_Engine"
python scripts/test_injuries_download_12_01_2026.py
```

---

## 📊 Expected Behavior After Fixes

### Weather Tracking
- ✅ `weather_downloaded = True` when weather exists in database
- ✅ `weather_downloaded = True` when weather is successfully downloaded
- ✅ `weather_error` set when download fails
- ✅ Jackpot log shows correct weather status

### Rest Days Tracking
- ✅ `rest_days_calculated = True` when rest days exist in database
- ✅ `rest_days_calculated = True` when rest days are successfully calculated
- ✅ `rest_days_error` set when calculation fails
- ✅ Jackpot log shows correct rest days status

### Injuries Tracking
- ✅ `injuries_downloaded = True` when injuries exist in database
- ✅ `injuries_downloaded = True` when injuries are successfully downloaded
- ✅ `injuries_error` set when download fails
- ✅ Jackpot log shows correct injuries status
- ✅ Injuries saved to `team_injuries` table

### Odds Movement Tracking
- ✅ `odds_tracked = True` when odds movement exists in database
- ✅ `odds_tracked = True` when odds movement is successfully tracked
- ✅ `odds_error` set when tracking fails
- ✅ Jackpot log shows correct odds movement status

### Team Training Status
- ✅ Teams matched by both ID and canonical_name
- ✅ Teams show as "trained" if they match by either ID or name
- ✅ Reduces false "untrained" status due to ID mismatches

---

## 📝 Files Modified

1. **`app/api/probabilities.py`**
   - Fixed weather tracking (2 occurrences)
   - Fixed rest days tracking (2 occurrences)
   - Fixed injuries tracking (2 occurrences)
   - Fixed odds movement tracking (2 occurrences)

2. **`app/services/automated_pipeline.py`**
   - Added canonical_name matching for team training status
   - Builds `team_strengths_by_name` mapping from model's team_strengths

3. **`scripts/test_injuries_download_12_01_2026.py`** (New)
   - Test script to verify API key and injuries download

---

## ⚠️ Notes

1. **API Key Hardcoded**: The hardcoded API key is a fallback. For production, remove it and require environment variable.

2. **Team ID Mismatch**: The canonical_name matching should help, but if teams truly have different canonical names, they will still show as untrained. This is expected behavior.

3. **Injuries Download**: Injuries are only downloaded if:
   - API key is configured (not empty)
   - Injury data is missing for the fixture
   - Both home and away team IDs are available

4. **Database Table**: Injuries are stored in `team_injuries` table with columns:
   - `team_id` (references teams.id)
   - `fixture_id` (references jackpot_fixtures.id)
   - `key_players_missing`
   - `injury_severity`
   - `attackers_missing`, `midfielders_missing`, `defenders_missing`, `goalkeepers_missing`
   - `notes`
   - `recorded_at`

---

## ✅ Verification Checklist

- [x] Weather tracking flag fixed
- [x] Rest days tracking flag fixed
- [x] Injuries tracking flag fixed
- [x] Odds movement tracking flag fixed
- [x] Team ID mismatch fix (canonical_name matching)
- [x] Test script created
- [x] Documentation created
- [ ] Test script executed (manual)
- [ ] Verify injuries are downloading to database (manual)

---

## 🔄 Next Steps

1. Run test script to verify API key and injuries download
2. Test probability calculation and verify tracking flags in jackpot log
3. Check if team training status is more accurate with canonical_name matching
4. Consider removing hardcoded API key for production deployment

