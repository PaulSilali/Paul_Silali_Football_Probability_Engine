# How to Update Teams and Leagues Tables

## 📋 Overview

This guide explains how to update the `teams` and `leagues` tables with the newly implemented features:

1. **Leagues Table**: Update `avg_draw_rate` and `home_advantage` from match data
2. **Teams Table**: Update `attack_rating`, `defense_rating`, and `home_bias` from model training

---

## 🏆 Option 1: Update Leagues Table

### **Method A: Automatic (During Database Population)** ✅ Recommended

When you run the database population script, league statistics are **automatically calculated** after matches are populated.

```bash
# Navigate to the population script directory
cd "15_Football_Data_\02_Db populating_Script"

# Run the population script
python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
```

**What happens:**
1. Matches are populated
2. `update_league_statistics()` is automatically called
3. All leagues with match data get updated `avg_draw_rate` and `home_advantage`

---

### **Method B: Manual (Via API)** 🔧

If you want to update leagues **without re-running the full population**:

```bash
# Update all leagues
curl -X POST "http://localhost:8000/api/admin/leagues/update-statistics"

# Or update a specific league
curl -X POST "http://localhost:8000/api/admin/leagues/update-statistics?league_code=E0"
```

**Using Python:**
```python
import requests

# Update all leagues
response = requests.post("http://localhost:8000/api/admin/leagues/update-statistics")
print(response.json())

# Update specific league
response = requests.post(
    "http://localhost:8000/api/admin/leagues/update-statistics",
    params={"league_code": "E0"}
)
print(response.json())
```

**Using Python (Direct Service):**
```python
from app.db.session import SessionLocal
from app.services.league_statistics import LeagueStatisticsService

db = SessionLocal()
service = LeagueStatisticsService(db)

# Update all leagues
count = service.update_all_leagues()
print(f"Updated {count} leagues")

# Update specific league
service.update_league_by_code("E0")
```

---

### **Method C: SQL Direct Update** 💻

If you prefer SQL:

```sql
-- Update all leagues
UPDATE leagues l
SET 
    avg_draw_rate = COALESCE((
        SELECT AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END)::NUMERIC(5,4)
        FROM matches m
        WHERE m.league_id = l.id
            AND m.result IS NOT NULL
            AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
    ), 0.26),
    
    home_advantage = COALESCE((
        SELECT AVG(m.home_goals - m.away_goals)::NUMERIC(5,4)
        FROM matches m
        WHERE m.league_id = l.id
            AND m.home_goals IS NOT NULL
            AND m.away_goals IS NOT NULL
            AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
    ), 0.35),
    
    updated_at = now()
WHERE EXISTS (
    SELECT 1 FROM matches m WHERE m.league_id = l.id
);
```

---

## ⚽ Option 2: Update Teams Table

### **Method A: Run Model Training** ✅ Recommended

The teams table (`attack_rating`, `defense_rating`, `home_bias`) is updated **automatically when you train the model**.

**Step 1: Train the Model**

```bash
# Via API
curl -X POST "http://localhost:8000/api/model/train/poisson" \
  -H "Content-Type: application/json" \
  -d '{
    "leagues": null,
    "seasons": null,
    "date_from": null,
    "date_to": null
  }'
```

**Or using Python:**
```python
from app.db.session import SessionLocal
from app.services.model_training import ModelTrainingService

db = SessionLocal()
service = ModelTrainingService(db)

# Train model (this will update teams table automatically)
result = service.train_poisson_model()
print(result)
```

**What happens:**
1. Model is trained on match data
2. Team strengths are calculated
3. `teams.attack_rating`, `teams.defense_rating`, and `teams.home_bias` are updated
4. `teams.last_calculated` is set to training timestamp

---

### **Method B: SQL Direct Update** 💻

If you want to manually update specific teams (not recommended, but possible):

```sql
-- Example: Update a specific team
UPDATE teams
SET 
    attack_rating = 1.5,
    defense_rating = 0.9,
    home_bias = 0.12,
    last_calculated = now()
WHERE id = 1;
```

**Note:** This is not recommended because values should come from model training, not manual input.

---

## 🔄 Complete Update Workflow

### **Scenario 1: Fresh Database Population**

```bash
# Step 1: Extract data
cd "15_Football_Data_\01_extruction_Script"
python extract_football_data.py

# Step 2: Populate database (includes league statistics update)
cd "..\02_Db populating_Script"
python populate_database.py --csv "..\01_extruction_Script\output\matches_extracted.csv" --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"

# Step 3: Train model (updates teams table)
# Via API or Python (see Method A above)
```

**Result:**
- ✅ Leagues have calculated `avg_draw_rate` and `home_advantage`
- ✅ Teams have calculated `attack_rating`, `defense_rating`, and `home_bias`

---

### **Scenario 2: Update Existing Database**

If you already have data in the database:

```bash
# Step 1: Update leagues (if new matches were added)
curl -X POST "http://localhost:8000/api/admin/leagues/update-statistics"

# Step 2: Retrain model (updates teams)
curl -X POST "http://localhost:8000/api/model/train/poisson" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## ✅ Verification

### **Check Leagues Table:**

```sql
-- View updated leagues
SELECT 
    code,
    name,
    avg_draw_rate,
    home_advantage,
    updated_at
FROM leagues
WHERE avg_draw_rate != 0.26 OR home_advantage != 0.35
ORDER BY code
LIMIT 20;
```

**Expected:** Leagues should have calculated values (not defaults 0.26/0.35)

---

### **Check Teams Table:**

```sql
-- View updated teams
SELECT 
    id,
    name,
    attack_rating,
    defense_rating,
    home_bias,
    last_calculated
FROM teams
WHERE last_calculated IS NOT NULL
ORDER BY last_calculated DESC
LIMIT 20;
```

**Expected:** Teams should have:
- `attack_rating` != 1.0 (calculated value)
- `defense_rating` != 1.0 (calculated value)
- `home_bias` != 0.0 (calculated value)
- `last_calculated` IS NOT NULL (timestamp)

---

### **Via API:**

```bash
# Check league statistics
curl "http://localhost:8000/api/admin/leagues/statistics?league_code=E0"

# Check team (via teams API if available)
curl "http://localhost:8000/api/teams?league_code=E0"
```

---

## 📊 Quick Reference

| Table | Column | How to Update | When |
|-------|--------|---------------|------|
| **leagues** | `avg_draw_rate` | Run population script OR API | After matches are populated |
| **leagues** | `home_advantage` | Run population script OR API | After matches are populated |
| **teams** | `attack_rating` | Train model | After model training |
| **teams** | `defense_rating` | Train model | After model training |
| **teams** | `home_bias` | Train model | After model training |
| **teams** | `last_calculated` | Train model | After model training |

---

## 🚨 Troubleshooting

### **Leagues Still Have Default Values**

**Problem:** `avg_draw_rate = 0.26` and `home_advantage = 0.35` for all leagues

**Solution:**
1. Check if matches exist: `SELECT COUNT(*) FROM matches;`
2. Check if matches have results: `SELECT COUNT(*) FROM matches WHERE result IS NOT NULL;`
3. Run update manually: `POST /api/admin/leagues/update-statistics`

---

### **Teams Still Have Default Values**

**Problem:** `attack_rating = 1.0`, `defense_rating = 1.0`, `home_bias = 0.0`

**Solution:**
1. Check if model was trained: `SELECT * FROM models WHERE model_type = 'poisson' AND status = 'active';`
2. Train model: `POST /api/model/train/poisson`
3. Check training logs for errors

---

### **No Matches Found Error**

**Problem:** "No matches found for league X"

**Solution:**
- League has no match data in the last 5 years
- This is expected for new/empty leagues
- League will keep default values

---

## 📝 Example Scripts

### **Python Script to Update Everything:**

```python
#!/usr/bin/env python3
"""
Update teams and leagues tables
"""
from app.db.session import SessionLocal
from app.services.league_statistics import LeagueStatisticsService
from app.services.model_training import ModelTrainingService

def update_all():
    db = SessionLocal()
    
    try:
        # Step 1: Update leagues
        print("Updating league statistics...")
        league_service = LeagueStatisticsService(db)
        count = league_service.update_all_leagues()
        print(f"✅ Updated {count} leagues")
        
        # Step 2: Train model (updates teams)
        print("\nTraining model (this will update teams)...")
        training_service = ModelTrainingService(db)
        result = training_service.train_poisson_model()
        print(f"✅ Model trained: {result.get('version')}")
        print(f"✅ Teams updated: {result.get('matchCount')} matches used")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_all()
```

**Save as:** `update_tables.py` and run:
```bash
python update_tables.py
```

---

## 🎯 Summary

### **To Update Leagues:**
1. ✅ Run `populate_database.py` (automatic)
2. ✅ OR call `POST /api/admin/leagues/update-statistics` (manual)

### **To Update Teams:**
1. ✅ Train the model via API or Python (automatic)
2. ✅ Teams are updated during training completion

### **Recommended Workflow:**
1. Populate database → Leagues updated automatically
2. Train model → Teams updated automatically

---

## 📚 Related Documentation

- **League Statistics Deep Scan**: `12_Important_Documets/LEAGUE_STATISTICS_DEEP_SCAN.md`
- **Team Ratings Update**: `12_Important_Documets/TEAM_RATINGS_UPDATE_IMPLEMENTATION.md`
- **Implementation Summary**: `12_Important_Documets/IMPLEMENTATION_SUMMARY_LEAGUE_STATISTICS.md`

