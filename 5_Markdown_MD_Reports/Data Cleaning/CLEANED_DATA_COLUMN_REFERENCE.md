# Cleaned Data Column Reference Guide

## 📊 Current Sample Data Structure

Based on your sample data, here's what columns are currently present:

### ✅ **Base Columns** (Present)
- `Date` - Match date (DD/MM/YYYY format)
- `Div` - League/Division code
- `HomeTeam` - Home team name
- `AwayTeam` - Away team name
- `FTHG` - Full Time Home Goals
- `FTAG` - Full Time Away Goals
- `FTR` - Full Time Result (H/A/D)
- `AvgH` - Average Home Odds
- `AvgD` - Average Draw Odds
- `AvgA` - Average Away Odds

### ✅ **Database Columns** (Present)
- `season` - Season identifier (e.g., 1920, 2021)
- `league_id` - League ID
- `home_team_id` - Home team ID
- `away_team_id` - Away team ID

### ✅ **Calculated Probabilities** (Present)
- `prob_home_market` - Home win probability (from odds)
- `prob_draw_market` - Draw probability (from odds)
- `prob_away_market` - Away win probability (from odds)

---

## 🎯 **Expected Columns After Phase 2 Cleaning**

After running Phase 2 cleaning (with outlier-based features), your data should have **ALL** of the above columns **PLUS** the following:

### 📈 **Phase 2 Derived Features** (Should be added)

#### 1. **Goal-Based Features**
- `TotalGoals` - Sum of FTHG + FTAG
- `GoalDifference` - Difference: FTHG - FTAG

#### 2. **Odds Features**
- `Overround` - Bookmaker margin: (1/AvgH + 1/AvgD + 1/AvgA) - 1

#### 3. **Date Features**
- `Year` - Year extracted from Date (e.g., 2019, 2020)
- `Month` - Month extracted from Date (1-12)
- `DayOfWeek` - Day of week (0=Monday, 6=Sunday)

#### 4. **Outlier-Based Features** (NEW - 11 features)

**Mismatch Indicators:**
- `is_extreme_favorite_home` - Binary (1 if AvgH > 15)
- `is_extreme_favorite_away` - Binary (1 if AvgA > 30)
- `is_mismatch` - Binary (1 if either extreme favorite)

**High-Scoring Indicators:**
- `is_high_scoring_match` - Binary (1 if FTHG > 6 OR TotalGoals > 7)
- `is_very_high_scoring` - Binary (1 if FTHG > 8 OR TotalGoals > 9)

**Draw Probability Category:**
- `draw_prob_category` - Categorical ('low', 'medium', 'high', 'unknown')

**Extreme Odds Flags:**
- `has_extreme_draw_odds` - Binary (1 if AvgD > 12)
- `has_extreme_home_odds` - Binary (1 if AvgH > 15)
- `has_extreme_away_odds` - Binary (1 if AvgA > 30)

**Team Strength Categories:**
- `home_team_strength_category` - Categorical ('strong', 'medium', 'weak', 'unknown')
- `away_team_strength_category` - Categorical ('strong', 'medium', 'weak', 'unknown')

---

## 🔍 **Verification Checklist**

### Your Current Data Has:
- ✅ Base match columns
- ✅ Database IDs
- ✅ Market probabilities
- ❌ **Missing:** TotalGoals
- ❌ **Missing:** GoalDifference
- ❌ **Missing:** Overround
- ❌ **Missing:** Year, Month, DayOfWeek
- ❌ **Missing:** All 11 outlier-based features

### **This means:**
Your data was cleaned with **Phase 1 only** (or before Phase 2 was implemented).

---

## 📋 **Complete Column List (After Phase 2)**

### **Total Expected Columns: ~30-35** (depending on original CSV columns)

1. `Date` - Match date
2. `Div` - League code
3. `HomeTeam` - Home team name
4. `AwayTeam` - Away team name
5. `FTHG` - Home goals
6. `FTAG` - Away goals
7. `FTR` - Full time result
8. `AvgH` - Home odds
9. `AvgD` - Draw odds
10. `AvgA` - Away odds
11. `season` - Season ID
12. `league_id` - League ID
13. `home_team_id` - Home team ID
14. `away_team_id` - Away team ID
15. `prob_home_market` - Home probability
16. `prob_draw_market` - Draw probability
17. `prob_away_market` - Away probability
18. **`TotalGoals`** ⬅️ **Should be added**
19. **`GoalDifference`** ⬅️ **Should be added**
20. **`Overround`** ⬅️ **Should be added**
21. **`Year`** ⬅️ **Should be added**
22. **`Month`** ⬅️ **Should be added**
23. **`DayOfWeek`** ⬅️ **Should be added**
24. **`is_extreme_favorite_home`** ⬅️ **Should be added**
25. **`is_extreme_favorite_away`** ⬅️ **Should be added**
26. **`is_mismatch`** ⬅️ **Should be added**
27. **`is_high_scoring_match`** ⬅️ **Should be added**
28. **`is_very_high_scoring`** ⬅️ **Should be added**
29. **`draw_prob_category`** ⬅️ **Should be added**
30. **`has_extreme_draw_odds`** ⬅️ **Should be added**
31. **`has_extreme_home_odds`** ⬅️ **Should be added**
32. **`has_extreme_away_odds`** ⬅️ **Should be added**
33. **`home_team_strength_category`** ⬅️ **Should be added**
34. **`away_team_strength_category`** ⬅️ **Should be added**

---

## 🔄 **How to Get Complete Phase 2 Features**

### **Option 1: Re-run Data Preparation** (Recommended)
```bash
# Via Frontend
1. Go to "Data Cleaning & ETL" page
2. Click "Run Pipeline" button
3. This will re-process data with Phase 2 cleaning
```

### **Option 2: Re-download Data**
```bash
# Via Frontend
1. Go to "Data Ingestion" page
2. Select leagues/seasons
3. Click "Download Selected"
4. New downloads automatically include Phase 2 features
```

### **Option 3: Backend API**
```python
POST /api/data/prepare-training-data
{
  "league_codes": ["B1", "E0"],
  "format": "both"
}
```

---

## 📊 **Sample Row with All Features**

Here's what a complete row should look like after Phase 2 cleaning:

| Column | Example Value | Notes |
|--------|---------------|-------|
| Date | 26/07/2019 | Original date |
| Div | B1 | League code |
| HomeTeam | Genk | Home team |
| AwayTeam | Kortrijk | Away team |
| FTHG | 2 | Home goals |
| FTAG | 1 | Away goals |
| FTR | H | Result |
| AvgH | 1.38 | Home odds |
| AvgD | 4.94 | Draw odds |
| AvgA | 7.42 | Away odds |
| season | 1920 | Season |
| league_id | 29 | League ID |
| home_team_id | 580 | Home team ID |
| away_team_id | 581 | Away team ID |
| prob_home_market | 0.6824 | Home prob |
| prob_draw_market | 0.1906 | Draw prob |
| prob_away_market | 0.1269 | Away prob |
| **TotalGoals** | **3** | **FTHG + FTAG** |
| **GoalDifference** | **1** | **FTHG - FTAG** |
| **Overround** | **0.045** | **Bookmaker margin** |
| **Year** | **2019** | **From Date** |
| **Month** | **7** | **From Date** |
| **DayOfWeek** | **4** | **Friday** |
| **is_extreme_favorite_home** | **0** | **AvgH=1.38 < 15** |
| **is_extreme_favorite_away** | **0** | **AvgA=7.42 < 30** |
| **is_mismatch** | **0** | **No extreme favorite** |
| **is_high_scoring_match** | **0** | **FTHG=2, TotalGoals=3** |
| **is_very_high_scoring** | **0** | **Not very high** |
| **draw_prob_category** | **medium** | **0.19 is medium** |
| **has_extreme_draw_odds** | **0** | **AvgD=4.94 < 12** |
| **has_extreme_home_odds** | **0** | **AvgH=1.38 < 15** |
| **has_extreme_away_odds** | **0** | **AvgA=7.42 < 30** |
| **home_team_strength_category** | **strong** | **AvgH=1.38 < 2** |
| **away_team_strength_category** | **medium** | **3 ≤ AvgA=7.42 ≤ 20** |

---

## ✅ **Summary**

**Your current data:** Phase 1 cleaned (17 columns)
**Expected data:** Phase 2 cleaned (34+ columns)

**Action needed:** Re-run data preparation pipeline to add Phase 2 features.

---

**Status:** ✅ **Ready to add Phase 2 features**

