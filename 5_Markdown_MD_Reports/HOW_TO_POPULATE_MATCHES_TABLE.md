# How to Populate the Empty Matches Table

Your `matches` table is currently empty. Here's how to populate it with historical match data.

## Quick Start Options

### Option 1: Batch Download (Recommended)
**Download multiple leagues/seasons at once**

**Endpoint:** `POST /api/data/batch-download`

**Request Body:**
```json
{
  "source": "football-data.co.uk",
  "leagues": [
    {"code": "E0", "season": "all"},
    {"code": "E1", "season": "all"},
    {"code": "SP1", "season": "all"},
    {"code": "D1", "season": "all"},
    {"code": "I1", "season": "all"},
    {"code": "F1", "season": "all"}
  ]
}
```

**What it does:**
- Downloads last 7 seasons for each league
- Inserts/updates matches in the database
- Returns batch numbers and statistics

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/data/batch-download" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "football-data.co.uk",
    "leagues": [
      {"code": "E0", "season": "all"},
      {"code": "SP1", "season": "all"}
    ]
  }'
```

---

### Option 2: Single League/Season Download
**Download one league at a time**

**Endpoint:** `POST /api/data/refresh`

**Query Parameters:**
- `source`: `football-data.co.uk`
- `league_code`: League code (e.g., `E0`, `SP1`, `D1`)
- `season`: Season code (e.g., `2324` for 2023-24) or `all` for last 7 seasons

**Example:**
```bash
curl -X POST "http://localhost:8000/api/data/refresh?source=football-data.co.uk&league_code=E0&season=all"
```

**Available League Codes:**
- `E0` - Premier League (England)
- `E1` - Championship (England)
- `SP1` - La Liga (Spain)
- `D1` - Bundesliga (Germany)
- `I1` - Serie A (Italy)
- `F1` - Ligue 1 (France)
- `N1` - Eredivisie (Netherlands)
- `B1` - Jupiler Pro League (Belgium)
- And many more...

---

### Option 3: Using Python Script
**Run ingestion programmatically**

Create a script `populate_matches.py`:

```python
from app.db.session import SessionLocal
from app.services.data_ingestion import DataIngestionService
from app.config import settings

def populate_matches():
    db = SessionLocal()
    try:
        service = DataIngestionService(
            db,
            enable_cleaning=settings.ENABLE_DATA_CLEANING
        )
        
        # Download Premier League - last 7 seasons
        stats = service.ingest_from_football_data(
            league_code="E0",
            season="all",  # Downloads last 7 seasons
            save_csv=True
        )
        
        print(f"Downloaded: {stats}")
        
    finally:
        db.close()

if __name__ == "__main__":
    populate_matches()
```

Run it:
```bash
cd 2_Backend_Football_Probability_Engine
python populate_matches.py
```

---

## Season Codes

**Format:** `YYXX` where:
- `YY` = Start year (e.g., `23` for 2023)
- `XX` = End year (e.g., `24` for 2024)

**Examples:**
- `2324` = 2023-24 season
- `2223` = 2022-23 season
- `2122` = 2021-22 season
- `all` = Last 7 seasons (default)
- `last7` = Last 7 seasons
- `last10` = Last 10 seasons

---

## What Happens During Ingestion

1. **Downloads CSV** from football-data.co.uk
2. **Parses match data** (teams, scores, odds, dates)
3. **Resolves team names** to database teams (creates teams if needed)
4. **Inserts new matches** or **updates existing matches**
5. **Saves CSV files** to `data/1_data_ingestion/` folder (backup)
6. **Logs ingestion** in `ingestion_logs` table

---

## Verify Matches Were Inserted

**Check via SQL:**
```sql
SELECT COUNT(*) FROM matches;
SELECT league_id, season, COUNT(*) 
FROM matches 
GROUP BY league_id, season 
ORDER BY season DESC;
```

**Check via API:**
```bash
GET /api/data/league-stats
```

---

## Troubleshooting

### "No matches found" Error
- **Cause:** Matches table is empty
- **Solution:** Run data ingestion first (see above)

### "League not found" Error
- **Cause:** League doesn't exist in `leagues` table
- **Solution:** Initialize leagues first:
  ```bash
  POST /api/data/init-leagues
  ```

### "Teams not resolved" Warnings
- **Cause:** Team names from source don't match database teams
- **Solution:** Team aliases are being used, but some teams may need manual mapping
- **Impact:** Those matches are skipped (not inserted)

### 404 Errors for Some Seasons
- **Cause:** Data not available for that league/season on football-data.co.uk
- **Solution:** Try different seasons or use Football-Data.org API (requires API key)

---

## Recommended Initial Setup

1. **Initialize leagues:**
   ```bash
   POST /api/data/init-leagues
   ```

2. **Download major leagues (last 7 seasons):**
   ```json
   POST /api/data/batch-download
   {
     "source": "football-data.co.uk",
     "leagues": [
       {"code": "E0", "season": "all"},
       {"code": "SP1", "season": "all"},
       {"code": "D1", "season": "all"},
       {"code": "I1", "season": "all"},
       {"code": "F1", "season": "all"}
     ]
   }
   ```

3. **Verify data:**
   ```bash
   GET /api/data/league-stats
   ```

4. **Then run draw priors ingestion:**
   ```bash
   POST /api/draw-ingestion/league-priors
   {
     "league_code": "E0",
     "season": "ALL"
   }
   ```

---

## Expected Results

After successful ingestion, you should see:
- ✅ Matches in `matches` table
- ✅ Teams in `teams` table (auto-created)
- ✅ Ingestion logs in `ingestion_logs` table
- ✅ CSV files in `data/1_data_ingestion/` folder

**Typical numbers:**
- Premier League (E0): ~380 matches per season × 7 seasons = ~2,660 matches
- La Liga (SP1): ~380 matches per season × 7 seasons = ~2,660 matches
- Total for 5 major leagues: ~13,000+ matches

---

## Next Steps

Once matches are populated:
1. ✅ Run draw priors ingestion (will now find matches)
2. ✅ Calculate team strengths
3. ✅ Generate predictions
4. ✅ Use for model training

