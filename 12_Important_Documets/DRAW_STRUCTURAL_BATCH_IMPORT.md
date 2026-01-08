# Draw Structural Batch Import - One-Click Import

## ✅ Implementation Complete

All draw structural CSV files are now saved to both locations, and a single endpoint imports all data types in one click.

---

## 📁 File Locations

### Dual Save Locations

All draw structural CSV files are now saved to **both** locations:

1. **Ingestion Folder** (Original):
   ```
   data/1_data_ingestion/Draw_structural/{folder_name}/
   ```

2. **Cleaned Data Folder** (New):
   ```
   data/2_Cleaned_data/Draw_structural/{folder_name}/
   ```

### Folder Structure

```
data/
├── 1_data_ingestion/
│   └── Draw_structural/
│       ├── Elo_Rating/
│       ├── h2h_stats/
│       ├── League_Priors/
│       ├── League_structure/
│       ├── Odds_Movement/
│       ├── Referee/
│       ├── Rest_Days/
│       ├── Weather/
│       └── xG_Data/
│
└── 2_Cleaned_data/
    ├── Draw_structural/          ← NEW
    │   ├── Elo_Rating/
    │   ├── h2h_stats/
    │   ├── League_Priors/
    │   ├── League_structure/
    │   ├── Odds_Movement/
    │   ├── Referee/
    │   ├── Rest_Days/
    │   ├── Weather/
    │   └── xG_Data/
    │
    └── Historical Match_Odds_Data/  ← Already exists
```

---

## 🚀 One-Click Import Endpoint

### Endpoint

**POST** `/draw-ingestion/import-all`

### Description

Imports all draw structural data types in a single request, in the correct order (weather is last).

### Import Order

1. ✅ **League Draw Priors** - Historical draw rates per league/season
2. ✅ **League Structure** - League metadata (teams, relegation zones, etc.)
3. ✅ **Elo Ratings** - Team Elo ratings over time
4. ✅ **H2H Stats** - Head-to-head statistics between teams
5. ✅ **Odds Movement** - Draw odds movement (open/close/delta)
6. ✅ **Referee Stats** - Referee behavioral statistics
7. ✅ **Rest Days** - Team rest days before matches
8. ✅ **XG Data** - Expected goals data
9. ✅ **Weather** - Weather conditions (LAST)

### Request Body

```json
{
  "use_all_leagues": true,
  "use_all_seasons": true,
  "max_years": 10,
  "league_codes": null  // Optional: ["E0", "SP1", "D1"] if use_all_leagues=false
}
```

### Response

```json
{
  "success": true,
  "message": "Import completed: 9 successful, 0 failed",
  "data": {
    "results": {
      "league_priors": {
        "success": true,
        "successful": 43,
        "failed": 0,
        "total": 43
      },
      "league_structure": {
        "success": true,
        "successful": 43,
        "failed": 0
      },
      "elo_ratings": {
        "success": true,
        "successful": 430,
        "failed": 0
      },
      "h2h_stats": {
        "success": true,
        "successful": 167,
        "failed": 0
      },
      "odds_movement": {
        "success": true,
        "successful": 147,
        "failed": 0
      },
      "referee_stats": {
        "success": true,
        "successful": 167,
        "failed": 0
      },
      "rest_days": {
        "success": true,
        "successful": 167,
        "failed": 0
      },
      "xg_data": {
        "success": true,
        "successful": 167,
        "failed": 0
      },
      "weather": {
        "success": true,
        "successful": 2,
        "failed": 0
      }
    },
    "summary": {
      "total_successful": 1332,
      "total_failed": 0,
      "all_completed": true
    }
  }
}
```

---

## 🔧 Implementation Details

### Utility Function

**File:** `app/services/ingestion/draw_structural_utils.py`

**Function:** `save_draw_structural_csv()`

Saves CSV files to both locations automatically:

```python
from app.services.ingestion.draw_structural_utils import save_draw_structural_csv

ingestion_path, cleaned_path = save_draw_structural_csv(
    df, "Elo_Rating", "G1_2223_elo_ratings.csv", save_to_cleaned=True
)
```

### Updated Save Functions

All `_save_*_csv_batch()` functions now use the utility:

- ✅ `ingest_elo_ratings.py::_save_elo_csv_batch()`
- ✅ `ingest_h2h_stats.py::_save_h2h_csv_batch()`
- ✅ `ingest_league_draw_priors.py::_save_priors_csv()`
- ✅ `ingest_league_structure.py::_save_league_structure_csv_batch()`
- ✅ `ingest_odds_movement.py::_save_odds_movement_csv_batch()`
- ✅ `ingest_referee_stats.py::_save_referee_csv_batch()`
- ✅ `ingest_rest_days.py::_save_rest_days_csv_batch()`
- ✅ `ingest_weather.py::_save_weather_csv_batch()`
- ✅ `ingest_xg_data.py::_save_xg_csv_batch()`

---

## 📝 Usage Examples

### Python/API Call

```python
import requests

response = requests.post(
    "http://localhost:8000/api/draw-ingestion/import-all",
    json={
        "use_all_leagues": True,
        "use_all_seasons": True,
        "max_years": 10
    }
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Message: {result['message']}")
```

### cURL

```bash
curl -X POST "http://localhost:8000/api/draw-ingestion/import-all" \
  -H "Content-Type: application/json" \
  -d '{
    "use_all_leagues": true,
    "use_all_seasons": true,
    "max_years": 10
  }'
```

### Frontend Integration

```typescript
const importAllDrawStructural = async () => {
  const response = await fetch('/api/draw-ingestion/import-all', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      use_all_leagues: true,
      use_all_seasons: true,
      max_years: 10
    })
  });
  
  const result = await response.json();
  console.log('Import completed:', result);
};
```

---

## ⚠️ Important Notes

### Prerequisites

Before running the batch import:

1. ✅ **Matches must be populated** - All draw structural data depends on matches existing
2. ✅ **Teams must be populated** - For team name resolution
3. ✅ **Leagues must be populated** - For league code lookup

### Error Handling

- Each data type is imported independently
- If one fails, others continue
- Errors are logged and returned in the response
- Partial success is possible (some data types succeed, others fail)

### Performance

- **Large datasets**: May take several minutes for all leagues/seasons
- **Progress tracking**: Check logs for real-time progress
- **Idempotent**: Safe to run multiple times (uses `ON CONFLICT DO UPDATE`)

### Weather Last

Weather is imported **last** because:
- It requires API calls (Open-Meteo)
- It's the slowest to process
- It's optional (can be skipped if API fails)
- Other data types don't depend on it

---

## ✅ Summary

1. ✅ **Dual Save**: All CSV files saved to both `1_data_ingestion` and `2_Cleaned_data`
2. ✅ **One-Click Import**: Single endpoint imports all 9 data types
3. ✅ **Correct Order**: Weather is imported last
4. ✅ **Error Resilient**: Each data type imports independently
5. ✅ **Idempotent**: Safe to run multiple times

---

## 🎯 Next Steps

1. **Frontend Button**: Add a button in the UI to call `/draw-ingestion/import-all`
2. **Progress Tracking**: Add WebSocket or polling for real-time progress
3. **Selective Import**: Add options to skip specific data types
4. **Scheduling**: Add cron job for automatic daily imports

