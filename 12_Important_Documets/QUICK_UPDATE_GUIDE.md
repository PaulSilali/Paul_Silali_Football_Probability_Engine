# Quick Update Guide: Teams and Leagues Tables

## 🚀 Quick Start

### **Update Leagues Table** (avg_draw_rate, home_advantage)

#### **Option 1: Run Batch Script** (Easiest) ✅

```bash
# Navigate to population script directory
cd "15_Football_Data_\02_Db populating_Script"

# Run the update script
UPDATE_LEAGUE_STATISTICS.bat
```

#### **Option 2: Run Python Script**

```bash
cd "15_Football_Data_\02_Db populating_Script"
python update_league_statistics.py --db-url "postgresql://postgres:11403775411@localhost/football_probability_engine"
```

#### **Option 3: Via API** (If backend is running)

```bash
curl -X POST "http://localhost:8000/api/admin/leagues/update-statistics"
```

---

### **Update Teams Table** (attack_rating, defense_rating, home_bias)

#### **Via API** (Recommended) ✅

```bash
# Train the model (this updates teams automatically)
curl -X POST "http://localhost:8000/api/model/train/poisson" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### **Via Python**

```python
from app.db.session import SessionLocal
from app.services.model_training import ModelTrainingService

db = SessionLocal()
service = ModelTrainingService(db)
result = service.train_poisson_model()
print(f"Model trained: {result['version']}")
print(f"Teams updated!")
```

---

## 📋 Complete Workflow

### **Step 1: Update Leagues**

```bash
# Run the batch script
cd "15_Football_Data_\02_Db populating_Script"
UPDATE_LEAGUE_STATISTICS.bat
```

**OR** if you're running the full population:

```bash
# This automatically updates leagues after matches are populated
run_population.bat
```

### **Step 2: Update Teams**

```bash
# Train the model (updates teams automatically)
curl -X POST "http://localhost:8000/api/model/train/poisson" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## ✅ Verify Updates

### **Check Leagues:**

```sql
SELECT code, name, avg_draw_rate, home_advantage 
FROM leagues 
WHERE avg_draw_rate != 0.26 OR home_advantage != 0.35
LIMIT 10;
```

**Expected:** Should show calculated values (not defaults)

### **Check Teams:**

```sql
SELECT name, attack_rating, defense_rating, home_bias, last_calculated
FROM teams 
WHERE last_calculated IS NOT NULL
LIMIT 10;
```

**Expected:** Should show calculated values and timestamps

---

## 🎯 Summary

| What | How | When |
|------|-----|------|
| **Leagues** | Run `UPDATE_LEAGUE_STATISTICS.bat` | After matches are in database |
| **Teams** | Train model via API | After model training |

---

## 📚 Full Documentation

See `HOW_TO_UPDATE_TEAMS_AND_LEAGUES.md` for detailed instructions and troubleshooting.

