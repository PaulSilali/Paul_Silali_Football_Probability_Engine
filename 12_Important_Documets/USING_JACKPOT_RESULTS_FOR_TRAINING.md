# Using Jackpot Results for Training

## Overview

**YES, you can use old jackpots with results to train the system!**

The system can convert jackpot fixtures with actual results into `Match` records, which are then used for model training.

---

## How It Works

### Current Training Data Source

The model training uses the **`matches` table** as the training data source:
- Historical match data from football-data.co.uk
- Historical match data from Football-Data.org
- **NEW:** Converted jackpot fixtures with results

### Conversion Process

1. **Jackpot Fixtures** → Have `actual_result`, `actual_home_goals`, `actual_away_goals`
2. **Convert to Match Records** → Creates entries in `matches` table
3. **Use for Training** → Model training automatically includes these matches

---

## Prerequisites

### ✅ Required Fields in Jackpot Fixtures

For conversion to work, jackpot fixtures need:
- ✅ `actual_result` (H/D/A) - **Required**
- ✅ `actual_home_goals` - Optional (inferred if missing)
- ✅ `actual_away_goals` - Optional (inferred if missing)
- ✅ `league_id` - **Required** (set automatically during fixture creation)
- ✅ `home_team_id` - **Required** (set automatically during fixture creation)
- ✅ `away_team_id` - **Required** (set automatically during fixture creation)

---

## Usage

### Method 1: Convert Single Jackpot (API)

**Endpoint:** `POST /api/jackpots/{jackpot_id}/convert-to-training-data`

**Request:**
```bash
POST /api/jackpots/JK-1234567890/convert-to-training-data
{
  "season": "2425",  // Optional: inferred if not provided
  "match_date": "2024-01-10",  // Optional: uses jackpot kickoff_date if not provided
  "skip_existing": true  // Skip fixtures that already have matches
}
```

**Response:**
```json
{
  "success": true,
  "message": "Converted 10 fixtures to matches",
  "data": {
    "success": true,
    "jackpot_id": "JK-1234567890",
    "total_fixtures": 10,
    "converted": 10,
    "skipped": 0,
    "errors": 0,
    "error_details": []
  }
}
```

### Method 2: Convert Multiple Jackpots (API)

**Endpoint:** `POST /api/jackpots/convert-multiple-to-training-data`

**Request:**
```bash
POST /api/jackpots/convert-multiple-to-training-data
{
  "jackpot_ids": ["JK-1234567890", "JK-0987654321"],  // Optional: specific jackpots
  "use_all_jackpots": false,  // Or set to true to convert all
  "skip_existing": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Converted 2 jackpots, 20 matches",
  "data": {
    "success": true,
    "total_jackpots": 2,
    "converted_jackpots": 2,
    "total_matches": 20,
    "skipped_matches": 0,
    "errors": 0,
    "jackpot_results": [...]
  }
}
```

### Method 3: Using Python Script

```python
from app.services.jackpot_to_training_data import convert_jackpot_to_matches
from app.db.session import SessionLocal
from datetime import date

db = SessionLocal()

# Convert single jackpot
result = convert_jackpot_to_matches(
    db=db,
    jackpot_id="JK-1234567890",
    season="2425",
    match_date=date(2024, 1, 10),
    skip_existing=True
)

print(f"Converted {result['converted']} fixtures to matches")
print(f"Skipped {result['skipped']} fixtures (already exist)")
print(f"Errors: {result['errors']}")

db.close()
```

---

## Step-by-Step Guide

### Step 1: Ensure Jackpot Has Results

**Check if jackpot fixtures have results:**
```sql
SELECT jf.id, jf.home_team, jf.away_team, 
       jf.actual_result, jf.actual_home_goals, jf.actual_away_goals
FROM jackpot_fixtures jf
JOIN jackpots j ON jf.jackpot_id = j.id
WHERE j.jackpot_id = 'JK-1234567890'
  AND jf.actual_result IS NOT NULL;
```

**Or via API:**
```bash
GET /api/jackpots/JK-1234567890
```

### Step 2: Convert to Match Records

**Via API:**
```bash
POST /api/jackpots/JK-1234567890/convert-to-training-data
```

**Or Python:**
```python
from app.services.jackpot_to_training_data import convert_jackpot_to_matches
from app.db.session import SessionLocal

db = SessionLocal()
result = convert_jackpot_to_matches(db, "JK-1234567890")
db.close()
```

### Step 3: Verify Conversion

**Check matches table:**
```sql
SELECT m.match_date, ht.name as home_team, at.name as away_team,
       m.home_goals, m.away_goals, m.result, m.season
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
WHERE m.season = '2425'  -- Or your season
ORDER BY m.match_date DESC
LIMIT 10;
```

### Step 4: Retrain Model

**The converted matches will automatically be included in training:**

```bash
POST /api/models/train/poisson
{
  "leagues": ["E0", "SP1", "I1"],  // Or None for all leagues
  "seasons": ["2425"],  // Include your converted season
  "base_model_window_years": 4
}
```

**Or use automated pipeline:**
```bash
POST /api/pipeline/run
{
  "team_names": [...],
  "auto_train": true
}
```

---

## Important Notes

### ⚠️ Season Inference

If `season` is not provided:
- System infers from `match_date`
- August onwards → New season (e.g., 2024-08-01 → 2425)
- January-July → Previous season (e.g., 2024-01-10 → 2324)

### ⚠️ Duplicate Prevention

If `skip_existing=True`:
- Checks for existing matches with same `league_id`, `season`, `match_date`, `home_team_id`, `away_team_id`
- Skips conversion if match already exists
- Prevents duplicate training data

### ⚠️ Goals Inference

If `actual_home_goals` or `actual_away_goals` are missing:
- System infers from `actual_result`:
  - H (Home win) → 1-0
  - A (Away win) → 0-1
  - D (Draw) → 0-0
- ⚠️ **Warning:** Inferred goals may not be accurate
- **Recommendation:** Always provide actual goals if available

---

## Example: Complete Workflow

### 1. Create Jackpot with Results

```bash
POST /api/jackpots
{
  "fixtures": [
    {
      "id": "1",
      "homeTeam": "Tottenham",
      "awayTeam": "Aston Villa",
      "league": "England",
      "odds": {"home": 2.60, "draw": 3.60, "away": 2.65}
    }
  ]
}
```

### 2. Calculate Probabilities

```bash
GET /api/probabilities/{jackpot_id}
```

### 3. After Matches Play, Update Results

```bash
PUT /api/jackpots/{jackpot_id}/fixtures/{fixture_id}/result
{
  "actual_result": "H",
  "actual_home_goals": 2,
  "actual_away_goals": 1
}
```

### 4. Convert to Training Data

```bash
POST /api/jackpots/{jackpot_id}/convert-to-training-data
{
  "season": "2425",
  "match_date": "2024-01-10"
}
```

### 5. Retrain Model

```bash
POST /api/models/train/poisson
{
  "seasons": ["2425"]
}
```

---

## Benefits

### ✅ Advantages

1. **More Training Data:**
   - Adds your actual predictions/results to training set
   - Improves model accuracy over time

2. **Real-World Data:**
   - Includes matches you actually predicted
   - Captures real-world patterns

3. **Continuous Learning:**
   - Convert jackpots after each round
   - Model improves with each conversion

4. **Validation:**
   - Compare predictions vs actual results
   - Track model performance over time

---

## Troubleshooting

### Issue: "No fixtures with results found"

**Solution:** Ensure jackpot fixtures have `actual_result` set:
```sql
UPDATE jackpot_fixtures 
SET actual_result = 'H', 
    actual_home_goals = 2, 
    actual_away_goals = 1
WHERE id = {fixture_id};
```

### Issue: "Missing league_id"

**Solution:** Ensure fixtures have `league_id` (set automatically during creation):
```sql
SELECT jf.id, jf.league_id, jf.home_team_id, jf.away_team_id
FROM jackpot_fixtures jf
WHERE jf.jackpot_id = (SELECT id FROM jackpots WHERE jackpot_id = 'JK-1234567890');
```

### Issue: "Match already exists"

**Solution:** This is expected if `skip_existing=True`. Set `skip_existing=False` to overwrite, or check existing matches:
```sql
SELECT * FROM matches 
WHERE league_id = {league_id}
  AND season = '2425'
  AND match_date = '2024-01-10'
  AND home_team_id = {home_team_id}
  AND away_team_id = {away_team_id};
```

---

## Summary

✅ **YES, you can use old jackpots with results for training!**

**Process:**
1. Ensure jackpot fixtures have `actual_result` set
2. Convert jackpot to matches using API or Python
3. Retrain model (converted matches automatically included)
4. Model improves with your real-world data

**API Endpoints:**
- `POST /api/jackpots/{jackpot_id}/convert-to-training-data` - Single jackpot
- `POST /api/jackpots/convert-multiple-to-training-data` - Multiple jackpots

**Python Service:**
- `app/services/jackpot_to_training_data.py`

---

## Next Steps

1. **Check your old jackpots:**
   ```sql
   SELECT j.jackpot_id, COUNT(jf.id) as fixtures_with_results
   FROM jackpots j
   JOIN jackpot_fixtures jf ON j.id = jf.jackpot_id
   WHERE jf.actual_result IS NOT NULL
   GROUP BY j.jackpot_id;
   ```

2. **Convert them:**
   ```bash
   POST /api/jackpots/convert-multiple-to-training-data
   {
     "use_all_jackpots": true,
     "skip_existing": true
   }
   ```

3. **Retrain model:**
   ```bash
   POST /api/models/train/poisson
   ```

Your old jackpot results will now be part of the training data! 🎉

