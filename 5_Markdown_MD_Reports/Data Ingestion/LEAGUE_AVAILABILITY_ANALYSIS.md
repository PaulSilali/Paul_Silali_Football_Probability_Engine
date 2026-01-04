# League Availability Analysis - Football-Data.co.uk

## Summary

**Total Leagues in System:** 43  
**Successfully Downloading:** 26 leagues  
**No Data Available:** 17 leagues  
**Extra Leagues (2012+ only):** 11 leagues (some work, some don't)

---

## ✅ Working Leagues (26)

### Main Leagues (22 divisions - Full historical data)
- **England:** E0, E1, E2, E3
- **Spain:** SP1, SP2
- **Germany:** D1, D2
- **Italy:** I1, I2
- **France:** F1, F2
- **Netherlands:** N1
- **Portugal:** P1
- **Scotland:** SC0, SC1, SC2, SC3
- **Belgium:** B1
- **Turkey:** T1
- **Greece:** G1
- **Austria:** A1
- **Switzerland:** SW1
- **Denmark:** DK1
- **Norway:** NO1
- **Poland:** PL1

---

## ⚠️ Extra Leagues - Limited Availability (2012/13 onwards)

Based on football-data.co.uk documentation, these "Extra Leagues" are available from **2012/13 season onwards** (not 10 seasons back like main leagues).

### Extra Leagues That Work (5)
- **Austria:** A1 ✅ (Works - already in main list)
- **Switzerland:** SW1 ✅ (Works - already in main list)
- **Denmark:** DK1 ✅ (Works - already in main list)
- **Norway:** NO1 ✅ (Works - already in main list)
- **Poland:** PL1 ✅ (Works - already in main list)

### Extra Leagues That Don't Work (11)
These are listed on football-data.co.uk but return 404 errors:
- **Sweden:** SWE1 ❌ (Allsvenskan - listed but no data)
- **Finland:** FIN1 ❌ (Veikkausliiga - listed but no data)
- **Romania:** RO1 ❌ (Liga 1 - listed but no data)
- **Russia:** RUS1 ❌ (Premier League - listed but no data)
- **Ireland:** IRL1 ❌ (Premier Division - listed but no data)
- **Argentina:** ARG1 ❌ (Primera Division - listed but no data)
- **Brazil:** BRA1 ❌ (Serie A - listed but no data)
- **Mexico:** MEX1 ❌ (Liga MX - listed but no data)
- **USA:** USA1 ❌ (MLS - listed but no data)
- **China:** CHN1 ❌ (Super League - listed but no data)
- **Japan:** JPN1 ❌ (J-League - listed but no data)

**Note:** These may have been discontinued, moved, or the league codes may be incorrect.

---

## ❌ Leagues Not Listed on Football-Data.co.uk (6)

These leagues are **NOT** in the Extra Leagues list on football-data.co.uk:

- **Czech Republic:** CZE1 ❌ (First League - not listed)
- **Croatia:** CRO1 ❌ (Prva HNL - not listed)
- **Serbia:** SRB1 ❌ (SuperLiga - not listed)
- **Ukraine:** UKR1 ❌ (Premier League - not listed)
- **South Korea:** KOR1 ❌ (K League 1 - not listed)
- **Australia:** AUS1 ❌ (A-League - not listed)

**Action Required:** These should be removed from the system or marked as unavailable.

---

## 🔧 Code Updates Applied

### 1. Extra Leagues Season Limiting
- Updated `ingest_all_seasons()` to only try seasons from 2012/13 onwards for Extra Leagues
- Prevents attempting to download data that doesn't exist

### 2. Download Log Improvements
- Now distinguishes between:
  - ✅ Successful downloads (with data)
  - ⚠️ No data available (all 404s, 0 records)
  - ❌ Failed downloads (exceptions)

### 3. Alternative URL Patterns
- Added fallback URL patterns for Extra Leagues (though most use standard pattern)

---

## 📋 Recommendations

### Option 1: Remove Unavailable Leagues (Recommended)
Remove the 17 leagues that don't have data from the frontend and database:
- 11 Extra Leagues that return 404
- 6 Leagues not listed on football-data.co.uk

**Result:** System will only show 26 working leagues

### Option 2: Mark as Unavailable
Keep leagues in the system but:
- Mark them as "Data Not Available" in the UI
- Disable download buttons for these leagues
- Show a tooltip explaining why

### Option 3: Find Alternative Data Sources
For the 17 unavailable leagues, integrate alternative data sources:
- **Football-Data.org API** (requires API key, limited free tier)
- **Understat** (xG data, some leagues)
- **Other free/open data sources**

---

## 📊 Current Status

| Category | Count | Status |
|----------|-------|--------|
| Working Leagues | 26 | ✅ Active |
| Extra Leagues (No Data) | 11 | ⚠️ Listed but 404 |
| Not Listed Leagues | 6 | ❌ Should Remove |
| **Total** | **43** | |

---

## 🔍 Verification Steps

To verify league availability:
1. Visit: `https://www.football-data.co.uk/{country}m.php`
2. Check if league data files are available
3. Verify league codes match football-data.co.uk format
4. Test URL: `https://www.football-data.co.uk/mmz4281/2425/{LEAGUE_CODE}.csv`

---

## 📝 Notes

- **Main Leagues:** Available from 1993/94 onwards (25+ seasons)
- **Extra Leagues:** Available from 2012/13 onwards (12+ seasons)
- **URL Pattern:** `https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv`
- **Data Format:** CSV files, updated twice weekly (Sunday & Wednesday nights)

