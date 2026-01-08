# Pipeline Data Download Explained

## What Does "Downloading Data for 20 Teams" Mean?

When the automated pipeline says **"Downloading data for 20 teams"**, it means:

### 1. **Historical Data Download**
- The pipeline downloads **past match results** (historical data) from external sources (football-data.co.uk API)
- It downloads the **last 7 seasons** by default (e.g., 2025/26, 2024/25, 2023/24, etc.)
- This is **NOT future data** - it's historical match results that already happened

### 2. **Why Download Data?**

The pipeline downloads data for teams that:

#### **Missing Teams** (Don't exist in database)
- New teams you're adding to your jackpot
- Teams that haven't been added to the database yet
- Example: If you add "Auckland FC" but it doesn't exist in your database

#### **Untrained Teams** (Exist but lack sufficient data)
- Teams that exist in the database but have **less than 10 matches** of historical data
- Teams that need more historical matches for accurate model training
- Example: A team with only 5 matches needs more data to train properly

### 3. **What Data Gets Downloaded?**

For each team needing data, the pipeline downloads:
- **All matches** from their league for the last 7 seasons
- Historical match results (home team, away team, scores, dates)
- Match statistics (goals, cards, etc.)
- Odds data (if available)

**Example:**
- If you have 20 teams from Spanish La Liga (SP1) that need data
- The pipeline downloads **all SP1 matches** for seasons: 2526, 2425, 2324, 2223, 2122, 2021, 1920
- This might be **2,660 matches** (380 matches × 7 seasons)

### 4. **How Is This Data Used for Training?**

When the model trains, it uses **ALL available historical data** in your database:

```
Model Training Process:
├── Query ALL matches from database
├── Filter by date window (last 4 years by default)
├── Include BOTH:
│   ├── Previously existing historical data ✅
│   └── Newly downloaded historical data ✅
└── Train on combined dataset
```

**Important Points:**
- ✅ **Old historical data IS used** - it's not replaced or ignored
- ✅ **Newly downloaded data is ADDED** to existing data
- ✅ **Model trains on the COMBINED dataset** (old + new)
- ✅ **More data = Better training** (more matches = more accurate team strengths)

### 5. **Example Scenario**

**Before Pipeline:**
```
Database has:
- Real Madrid: 500 matches ✅ (enough data)
- Barcelona: 450 matches ✅ (enough data)
- Auckland FC: 0 matches ❌ (needs data)
- Sydney FC: 3 matches ❌ (needs more data)
```

**Pipeline Downloads:**
- Downloads all AUS1 (Australian League) matches for last 7 seasons
- Adds ~2,660 matches to database
- Now Auckland FC and Sydney FC have historical data

**After Pipeline:**
```
Database has:
- Real Madrid: 500 matches ✅
- Barcelona: 450 matches ✅
- Auckland FC: 380 matches ✅ (newly downloaded)
- Sydney FC: 380 matches ✅ (newly downloaded)
```

**Model Training:**
- Trains on **ALL 1,710 matches** (500 + 450 + 380 + 380)
- Uses both old and new data together
- Learns team strengths from complete historical dataset

### 6. **Why Download League-Wide Data?**

The pipeline downloads **entire league seasons**, not just individual team matches, because:

1. **Team Strengths are Relative** - To calculate team strengths accurately, you need matches between all teams in the league
2. **More Context** - Seeing how teams perform against various opponents improves accuracy
3. **Efficiency** - Downloading entire seasons is faster than individual team lookups
4. **Completeness** - Ensures you have all relevant historical context

### 7. **Training Window**

The model uses a **sliding time window** for training:

- **Default:** Last 4 years of matches
- **Configurable:** Can be adjusted (3-5 years recommended)
- **Recent Data Weighted More:** More recent matches have slightly more influence

**Example:**
- Today: January 8, 2026
- Training Window: January 8, 2022 - January 8, 2026
- Uses all matches in this 4-year period

### 8. **Summary**

| Question | Answer |
|----------|--------|
| **Is old historical data used?** | ✅ YES - All existing data is used |
| **Do we download new data?** | ✅ YES - But it's historical (past matches), not future |
| **What data is downloaded?** | Historical match results from last 7 seasons |
| **Why download?** | Teams need more historical matches for accurate training |
| **What gets trained on?** | ALL historical data combined (old + newly downloaded) |
| **Is data replaced?** | ❌ NO - New data is ADDED to existing data |

### 9. **Visual Flow**

```
┌─────────────────────────────────────────────────────────┐
│  Your Jackpot: 20 Teams                                │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Check Team Status                                     │
│  ├─ 5 teams: Have enough data ✅                        │
│  ├─ 10 teams: Missing from database ❌                 │
│  └─ 5 teams: Exist but < 10 matches ❌                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Download Historical Data                              │
│  ├─ Download last 7 seasons                            │
│  ├─ For leagues: SP1, AUS1, etc.                      │
│  └─ Adds ~2,660 matches to database                   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Model Training                                        │
│  ├─ Query ALL matches from database                    │
│  ├─ Filter: Last 4 years                               │
│  ├─ Include: Old data + New data                       │
│  └─ Train on: Combined dataset (~5,000 matches)        │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Calculate Probabilities                               │
│  └─ Using trained model with team strengths           │
└─────────────────────────────────────────────────────────┘
```

### 10. **Key Takeaways**

1. **"Downloading data"** = Downloading **historical match results** (past seasons)
2. **Old data is NOT replaced** - New data is **added** to existing data
3. **Model trains on ALL data** - Both old and newly downloaded historical matches
4. **More data = Better accuracy** - More historical matches improve team strength calculations
5. **League-wide downloads** - Downloads entire league seasons for better context

---

**Bottom Line:** The pipeline ensures all teams have sufficient historical data for accurate model training. It downloads past match results and adds them to your existing database. The model then trains on the complete historical dataset to calculate accurate team strengths and probabilities.

