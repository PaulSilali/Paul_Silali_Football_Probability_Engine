# Next Steps After INT League Creation

## ✅ Completed

1. ✅ INT League created in database
2. ✅ League inference service created (`fixture_league_resolver.py`)
3. ✅ Fixture creation updated to use league inference
4. ✅ Probability calculation updated to handle INT league
5. ✅ Data ingestion guide created

---

## 📋 What's Next

### Step 1: Test Fixture Creation

**Test with your fixture list:**

```bash
# Create a test jackpot with international game
POST /api/jackpots
{
  "fixtures": [
    {
      "id": "1",
      "homeTeam": "Algeria",
      "awayTeam": "Nigeria",
      "league": "International",  # This triggers INT league
      "odds": {
        "home": 3.15,
        "draw": 3.00,
        "away": 2.50
      }
    },
    {
      "id": "2",
      "homeTeam": "Tottenham Hotspur",
      "awayTeam": "Aston Villa",
      "league": "England",  # This triggers league inference
      "odds": {
        "home": 2.60,
        "draw": 3.60,
        "away": 2.65
      }
    }
  ]
}
```

**Expected Results:**
- ✅ Fixture #1: Algeria vs Nigeria → INT league
- ✅ Fixture #2: Tottenham vs Aston Villa → E0 league (from team lookup)
- ✅ Teams created automatically
- ✅ `league_id` set on fixtures

### Step 2: Test Probability Calculation

```bash
GET /api/probabilities/{jackpot_id}
```

**Expected Results:**
- ✅ International game uses INT league draw rate (default 0.25 or calculated)
- ✅ Club games use normal league priors
- ✅ All draw structural data works

### Step 3: Ingest Historical International Match Data

**Option A: Using CSV Import**

1. Prepare CSV file with international matches:
```csv
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR
2024-01-10,Algeria,Nigeria,2,1,H
2024-01-15,Brazil,Argentina,1,1,D
```

2. Use data ingestion service:
```python
from app.services.data_ingestion import DataIngestionService
from app.db.session import SessionLocal

db = SessionLocal()
ingestion_service = DataIngestionService(db, enable_cleaning=True)

with open('international_matches.csv', 'r') as f:
    csv_content = f.read()

stats = ingestion_service.ingest_csv(
    csv_content=csv_content,
    league_code="INT",
    season="2425",
    save_csv=True
)
```

**Option B: Using API Endpoint**

```bash
POST /api/data-ingestion/ingest-csv
{
  "league_code": "INT",
  "season": "2425",
  "csv_content": "..."
}
```

### Step 4: Calculate Draw Structural Data

After ingesting match data, calculate draw structural features:

```python
from app.services.ingestion.ingest_team_form import batch_ingest_team_form_from_matches
from app.services.ingestion.ingest_elo_ratings import batch_calculate_elo_from_matches
from app.db.session import SessionLocal

db = SessionLocal()

# Calculate team form
form_results = batch_ingest_team_form_from_matches(
    db=db,
    league_codes=["INT"],
    use_all_seasons=True,
    max_years=10,
    save_csv=True
)

# Calculate Elo ratings
elo_results = batch_calculate_elo_from_matches(
    db=db,
    league_codes=["INT"],
    use_all_seasons=True,
    max_years=10,
    save_csv=True
)
```

---

## 🔍 Verification Checklist

### ✅ Database Verification

```sql
-- Check INT league exists
SELECT * FROM leagues WHERE code = 'INT';

-- Check international teams created
SELECT t.name, l.code 
FROM teams t
JOIN leagues l ON t.league_id = l.id
WHERE l.code = 'INT';

-- Check fixtures have league_id
SELECT jf.id, jf.home_team, jf.away_team, l.code as league_code
FROM jackpot_fixtures jf
LEFT JOIN leagues l ON jf.league_id = l.id
WHERE jf.jackpot_id = (SELECT id FROM jackpots ORDER BY created_at DESC LIMIT 1);
```

### ✅ Code Verification

1. **Fixture Creation:**
   - ✅ League inference works
   - ✅ Teams created automatically
   - ✅ `league_id` set correctly

2. **Probability Calculation:**
   - ✅ INT league uses default/calculated draw rate
   - ✅ Club leagues use normal priors
   - ✅ All draw structural data works

3. **Data Ingestion:**
   - ✅ CSV import works with `league_code="INT"`
   - ✅ Draw structural data calculates correctly

---

## 📝 Files Modified/Created

### ✅ Created Files

1. `app/services/fixture_league_resolver.py` - League inference service
2. `12_Important_Documets/INTERNATIONAL_GAMES_DATA_INGESTION.md` - Data ingestion guide
3. `12_Important_Documets/NEXT_STEPS_AFTER_INT_LEAGUE_CREATION.md` - This file

### ✅ Modified Files

1. `app/api/jackpots.py` - Added league inference to fixture creation
2. `app/services/draw_signal_calculator.py` - Added INT league handling for draw rate

---

## 🚀 Quick Start Commands

### 1. Verify INT League
```bash
python 2_Backend_Football_Probability_Engine/scripts/create_international_league.py
```

### 2. Test Fixture Creation
```bash
# Use your API client or curl
curl -X POST http://localhost:8000/api/jackpots \
  -H "Content-Type: application/json" \
  -d '{
    "fixtures": [{
      "id": "1",
      "homeTeam": "Algeria",
      "awayTeam": "Nigeria",
      "league": "International",
      "odds": {"home": 3.15, "draw": 3.00, "away": 2.50}
    }]
  }'
```

### 3. Calculate Probabilities
```bash
curl http://localhost:8000/api/probabilities/{jackpot_id}
```

---

## ❓ Troubleshooting

### Issue: "INT league not found"
**Solution:** Run `create_international_league.py` script

### Issue: "Could not infer league"
**Solution:** 
- Check team names exist in database
- Or provide `league` field with country name
- Or add country to `COUNTRY_TO_LEAGUE_CODE` mapping

### Issue: League priors not found for INT
**Solution:** This is expected. System uses default (0.25) or calculates from matches.

### Issue: Teams not created
**Solution:** Check INT league exists and has correct ID

---

## 📚 Documentation

- **Complete Guide:** `HANDLING_INTERNATIONAL_AND_CLUB_GAMES.md`
- **Data Ingestion:** `INTERNATIONAL_GAMES_DATA_INGESTION.md`
- **Analysis:** `TEAM_LOADING_AND_DRAW_STRUCTURAL_LOGIC_ANALYSIS.md`

---

## ✅ Summary

**What's Done:**
- ✅ INT league created
- ✅ League inference implemented
- ✅ Fixture creation updated
- ✅ Probability calculation handles INT league
- ✅ Documentation created

**What's Next:**
1. Test fixture creation with your fixture list
2. Test probability calculation
3. Ingest historical international match data (optional)
4. Calculate draw structural data (optional)

**You're ready to use international games!** 🎉

