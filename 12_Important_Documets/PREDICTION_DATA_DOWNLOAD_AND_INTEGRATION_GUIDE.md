# Prediction Data Download & Integration Guide

## Answers to Your Questions

### 1. During Prediction: Is Match xG & Weather Recent Data Downloaded?

**Answer: YES, but conditionally**

#### Weather Data
- ✅ **Automatically downloaded** during prediction if missing
- Location: `app/api/probabilities.py` lines 707-880
- Process:
  1. Checks if weather exists for fixture
  2. If missing, automatically fetches from Open-Meteo API
  3. Uses fixture date to determine historical vs forecast API
  4. Saves to `match_weather` table
- **API Used**: Open-Meteo (free, no API key needed)
- **Coverage**: Global (uses stadium coordinates or country capital fallback)

#### xG Data
- ⚠️ **NOT automatically downloaded** during prediction
- xG is calculated from team strengths (lambda values) if available
- To populate xG data:
  - Use batch ingestion: `POST /draw-ingestion/xg-data/batch`
  - Or manually ingest via `POST /draw-ingestion/xg-data`
- **Note**: xG data needs to be ingested separately before prediction

### 2. Unknown League Handling: Do We Download League Info?

**Answer: YES, automatically**

#### Current Behavior
- Location: `app/services/data_ingestion.py` lines 264-292
- When a team from an unknown league is encountered:
  1. System attempts to create league automatically
  2. Uses league code mapping for known leagues (E0, SP1, etc.)
  3. Falls back to "Unknown" country if league code not recognized
  4. Creates league entry in `leagues` table

#### League Code Mapping
The system has mappings for:
- ✅ Major European leagues (EPL, La Liga, Serie A, Bundesliga, etc.)
- ✅ Lower tier leagues (Championship, Segunda, etc.)
- ⚠️ Some international leagues may default to "Unknown"

#### To Improve Unknown League Handling
1. Add league codes to mapping in `data_ingestion.py`
2. Or manually create leagues via UI/API before data ingestion

### 3. League Priors Table Empty: How to Fill It?

**Answer: Use batch ingestion endpoint**

#### Current Status
- Table: `league_draw_priors`
- Purpose: Stores historical draw rates per league/season
- Currently empty because it needs to be populated

#### How to Fill League Priors

**Option 1: Batch Import (Recommended)**
```bash
POST /draw-ingestion/league-priors/batch
{
  "use_all_leagues": true,
  "use_all_seasons": true,
  "max_years": 10,
  "league_codes": null
}
```

**Option 2: Individual League**
```bash
POST /draw-ingestion/league-priors
{
  "league_code": "E0",
  "season": "2024-25",
  "csv_path": null  # Will calculate from matches table
}
```

**Option 3: Import All Draw Structural Data**
```bash
POST /draw-ingestion/import-all
{
  "use_all_leagues": true,
  "use_all_seasons": true,
  "max_years": 10
}
```
This includes league priors as step 1.

#### What It Does
- Calculates draw rate from `matches` table
- Formula: `draw_rate = COUNT(draws) / COUNT(total_matches)`
- Stores per league/season combination
- Saves CSV to `data/1_data_ingestion/Draw_structural/League_Priors/`

### 4. UI Location for Team Form & Injuries Ingestion

**Answer: Multiple locations**

#### Team Form
- ✅ **Automatically calculated** during prediction (if missing)
- ✅ **Batch ingestion**: `DrawStructuralIngestion` component
  - Location: `/draw-structural-ingestion` page
  - Tab: "Team Form" (if added) or use batch import-all
- ✅ **API Endpoint**: `POST /draw-ingestion/team-form/batch`

#### Team Injuries
- ✅ **Manual entry**: `InjuryInput` component
  - Location: `ProbabilityOutput` page
  - Triggered by clicking injury icon next to team name
  - Allows per-fixture injury recording
- ✅ **Batch export**: `POST /draw-ingestion/team-injuries/batch`
- ⚠️ **No UI for batch ingestion yet** (can be added)

#### Where to See This Information
1. **Probability Output Page** (`/probability-output`)
   - Shows injury icons next to team names
   - Click to view/edit injuries
   - Form is shown in team strength adjustments

2. **Draw Structural Ingestion Page** (`/draw-structural-ingestion`)
   - Batch import all draw structural data
   - Includes team form in import-all

---

## Integration Guide: Free Data Sources for Team Form & Injuries

### Recommended Integration Strategy

### Phase 1: Team Form Data Sources

#### 1. Football-Data.co.uk (Primary Source)
**Why**: Already integrated, free CSV downloads

**Integration Steps**:
```python
# Already implemented in ingest_team_form.py
# Uses existing matches table to calculate form
# No external API needed - uses historical match data
```

**Fields Mapped**:
- ✅ `matches_played` → Last N matches
- ✅ `wins, draws, losses` → From match results
- ✅ `goals_scored, goals_conceded` → From match scores
- ✅ `points` → Calculated (3*wins + draws)
- ✅ `form_rating` → Normalized (points / max_points)
- ✅ `attack_form` → Goals scored per match (normalized)
- ✅ `defense_form` → Goals conceded per match (inverted)

**Action Required**: ✅ Already implemented

#### 2. API-Football (Freemium - Optional Enhancement)
**Why**: Real-time form stats, better coverage

**Integration Steps**:
1. Create new service: `app/services/ingestion/ingest_team_form_api_football.py`
2. Add API key to environment variables
3. Map API response to schema:
   ```python
   {
     "fixture_id": fixture_id,
     "team_id": team_id,
     "matches_played": form_data["last_5"]["played"],
     "wins": form_data["last_5"]["wins"],
     "draws": form_data["last_5"]["draws"],
     "losses": form_data["last_5"]["loses"],
     "goals_scored": form_data["last_5"]["goals"]["for"],
     "goals_conceded": form_data["last_5"]["goals"]["against"],
     "points": form_data["last_5"]["wins"] * 3 + form_data["last_5"]["draws"]
   }
   ```

**API Endpoint**: `GET /fixtures/form/{team_id}/{league_id}`

**Action Required**: ⚠️ Not implemented - can be added

### Phase 2: Team Injuries Data Sources

#### 1. Transfermarkt (Scraping Required)
**Why**: Comprehensive injury lists, player importance

**Integration Steps**:
1. Create scraper: `app/services/scrapers/transfermarkt_injuries.py`
2. Map to schema:
   ```python
   {
     "key_players_missing": count_key_players_injured(),
     "attackers_missing": count_by_position("Forward"),
     "midfielders_missing": count_by_position("Midfielder"),
     "defenders_missing": count_by_position("Defender"),
     "goalkeepers_missing": count_by_position("Goalkeeper"),
     "injury_severity": calculate_severity(),
     "notes": get_injury_notes()
   }
   ```

**Action Required**: ❌ Not implemented - needs scraping service

#### 2. API-Football (Structured Data)
**Why**: Clean JSON, no scraping

**Integration Steps**:
1. Create service: `app/services/ingestion/ingest_injuries_api_football.py`
2. Use endpoint: `GET /injuries?fixture={fixture_id}`
3. Map response:
   ```python
   {
     "key_players_missing": count_important_players(),
     "attackers_missing": count_by_position("Attacker"),
     "midfielders_missing": count_by_position("Midfielder"),
     "defenders_missing": count_by_position("Defender"),
     "goalkeepers_missing": count_by_position("Goalkeeper"),
     "injury_severity": calculate_from_player_importance(),
     "notes": join_injury_descriptions()
   }
   ```

**Action Required**: ❌ Not implemented - can be added

#### 3. PhysioRoom (Scraping Required)
**Why**: Medical context, severity indicators

**Integration Steps**:
1. Create scraper: `app/services/scrapers/physioroom_injuries.py`
2. Extract severity from injury descriptions
3. Map to `injury_severity` field (0.0-1.0)

**Action Required**: ❌ Not implemented - needs scraping service

---

## Implementation Roadmap

### Immediate (Already Done)
- ✅ Team form calculation from matches table
- ✅ Team form batch ingestion
- ✅ Team injuries manual entry UI
- ✅ Team injuries batch export

### Short Term (Recommended)
1. **Add Team Form UI Tab**
   - Add to `DrawStructuralIngestion.tsx`
   - Show form data summary
   - Allow batch ingestion trigger

2. **Populate League Priors**
   - Run batch import for all leagues
   - Verify data in database

3. **Add xG Auto-Download**
   - Check if xG exists during prediction
   - Auto-fetch if missing (if API available)

### Medium Term (Enhancement)
1. **API-Football Integration**
   - Add API key configuration
   - Create form/injury ingestion services
   - Add to batch import pipeline

2. **Transfermarkt Scraper**
   - Create scraping service
   - Schedule nightly updates
   - Map to injury schema

3. **Enhanced UI**
   - Show form/injury data in probability output
   - Add visual indicators
   - Allow bulk import from CSV

---

## Quick Start: Populate League Priors

### Step 1: Check Current Status
```sql
SELECT COUNT(*) FROM league_draw_priors;
-- If 0, table is empty
```

### Step 2: Run Batch Import
```bash
curl -X POST http://localhost:8000/draw-ingestion/league-priors/batch \
  -H "Content-Type: application/json" \
  -d '{
    "use_all_leagues": true,
    "use_all_seasons": true,
    "max_years": 10
  }'
```

### Step 3: Verify
```sql
SELECT 
  l.code,
  l.name,
  ldp.season,
  ldp.draw_rate,
  ldp.sample_size
FROM league_draw_priors ldp
JOIN leagues l ON ldp.league_id = l.id
ORDER BY l.code, ldp.season;
```

---

## Summary

| Feature | Auto-Download During Prediction? | How to Populate |
|---------|----------------------------------|-----------------|
| **Weather** | ✅ Yes (if missing) | Automatic via Open-Meteo |
| **xG** | ❌ No | Batch ingestion endpoint |
| **Team Form** | ✅ Yes (if missing) | Calculated from matches table |
| **Team Injuries** | ❌ No | Manual entry or batch import |
| **League Info** | ✅ Yes (if unknown) | Auto-created from mapping |
| **League Priors** | ❌ No | Batch ingestion endpoint |

### Next Steps
1. ✅ Run league priors batch import
2. ✅ Verify team form is calculating correctly
3. ⚠️ Consider adding API-Football integration for injuries
4. ⚠️ Add team form/injuries UI tabs for better visibility

