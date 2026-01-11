# Where to Load Jackpot Match Results and Odds

**Date:** 2026-01-11

---

## Summary

There are **two main places** to load jackpot data:

1. **Odds** - Entered when creating jackpots
2. **Results** - Entered after matches complete

---

## 1. Loading Odds

### Location: **Jackpot Input Page** (`/jackpot-input`)

**How to Load:**
1. Navigate to **"Jackpot Input"** in sidebar
2. Enter fixtures with odds:
   - Home Team, Away Team
   - **Odds**: Home, Draw, Away (required)
3. Click **"Calculate Probabilities"**

**What Happens:**
- Odds are saved to `jackpot_fixtures.odds_home`, `odds_draw`, `odds_away`
- Used for:
  - Market blending
  - EV calculations
  - Market disagreement analysis

**Note:** If odds are not provided, defaults are used (2.0, 3.0, 2.5)

---

## 2. Loading Results (Actual Match Outcomes)

### Location: **Data Ingestion Page** → **"Jackpot Results" Tab** (`/data-ingestion`)

**How to Load:**

1. Navigate to **"Data Ingestion"** page
2. Click **"Jackpot Results"** tab
3. Paste CSV data in format:
   ```csv
   Match,HomeTeam,AwayTeam,Result,OddsHome,OddsDraw,OddsAway
   1,Union Berlin,Freiburg,D,2.1,3.2,3.5
   2,Leipzig,Stuttgart,H,1.8,3.5,4.2
   3,Nottingham,Man United,D,3.0,3.1,2.4
   ...
   ```

   **Note:** Odds columns (`OddsHome`, `OddsDraw`, `OddsAway`) are **optional**. If omitted, default odds (2.0, 3.0, 2.5) will be used.

4. Click **"Import Results"** button

**CSV Format:**
- **Match**: Match number (1, 2, 3, ...) - **Required**
- **HomeTeam**: Home team name - **Required**
- **AwayTeam**: Away team name - **Required**
- **Result**: `H`/`1` (Home), `D`/`X` (Draw), `A`/`2` (Away) - **Required**
- **OddsHome**: Home win odds (e.g., 2.1) - **Optional** (default: 2.0)
- **OddsDraw**: Draw odds (e.g., 3.2) - **Optional** (default: 3.0)
- **OddsAway**: Away win odds (e.g., 3.5) - **Optional** (default: 2.5)

**Alternative column names for odds:**
- `HomeOdds`, `DrawOdds`, `AwayOdds`
- `OddsH`, `OddsD`, `OddsA`
- `H`, `D`, `A` (if no other columns conflict)

**What Happens:**
1. System parses CSV and extracts:
   - Match numbers, teams, results (required)
   - Odds (optional - if provided, uses them; otherwise defaults to 2.0, 3.0, 2.5)
2. Creates jackpot with fixtures in `jackpots` table
3. Stores odds in `jackpot_fixtures.odds_home`, `odds_draw`, `odds_away` columns
4. Results saved to `saved_probability_results.actual_results` (JSON format)
5. Status: `"imported"` (ready for probability computation)

**After Import:**
- Click **"Compute"** button to calculate probabilities
- Results are then available for:
  - Validation
  - Calibration
  - Market disagreement analysis
  - Backtesting

---

## 3. Alternative: Update Results in Jackpot Validation

### Location: **Jackpot Validation Page** (`/jackpot-validation`)

**How to Update:**
1. Navigate to **"Jackpot Validation"** page
2. Select a jackpot
3. Update actual results per match
4. Click **"Save Validation"**

**Use Case:**
- Update results after matches complete
- Correct errors in imported results
- Validate predictions against actual outcomes

---

## Database Storage

### Odds Storage
**Table:** `jackpot_fixtures`
- `odds_home` (DOUBLE PRECISION, NOT NULL) - Stored when jackpot is created
- `odds_draw` (DOUBLE PRECISION, NOT NULL) - Stored when jackpot is created
- `odds_away` (DOUBLE PRECISION, NOT NULL) - Stored when jackpot is created

**How Odds Are Used:**
- **Market blending**: Odds converted to market-implied probabilities for blending with model probabilities
- **EV calculations**: Used in Decision Intelligence to calculate Expected Value (EV) for each pick
- **Market disagreement analysis**: Compares model probabilities vs market-implied probabilities
- **Calibration**: Historical odds + results used to fit calibration curves

### Results Storage
**Table:** `jackpot_fixtures`
- `actual_result` (ENUM: 'H', 'D', 'A')
- `actual_home_goals` (INTEGER, optional)
- `actual_away_goals` (INTEGER, optional)

**Also stored in:** `saved_probability_results`
- `actual_results` (JSON): `{"1": "2", "2": "X", "3": "1", ...}`

---

## For Calibration System

**To use results + odds for calibration:**

1. **Load Results:**
   - Use Data Ingestion → Jackpot Results tab
   - Import CSV with results

2. **Ensure Odds are Present:**
   - If creating new jackpot: Enter odds in Jackpot Input
   - If importing: Odds default to (2.0, 3.0, 2.5) - can be updated later

3. **Compute Probabilities:**
   - Click "Compute" in Data Ingestion page
   - This creates `prediction_snapshot` records

4. **Fit Calibration:**
   - Navigate to **"Calibration Management"** page
   - Use `calibration_dataset` view (combines `prediction_snapshot` + `jackpot_fixtures`)
   - Fit calibration curves from historical data

---

## Quick Reference

| Data Type | Where to Load | Page | Tab/Section |
|-----------|---------------|------|-------------|
| **Odds** | Jackpot Input | `/jackpot-input` | Main form |
| **Results** | Data Ingestion | `/data-ingestion` | "Jackpot Results" tab |
| **Update Results** | Jackpot Validation | `/jackpot-validation` | Main validation form |

---

## Example Workflow

1. **Create Jackpot with Odds:**
   - Go to `/jackpot-input`
   - Enter 13 fixtures with odds
   - Click "Calculate Probabilities"

2. **After Matches Complete:**
   - Go to `/data-ingestion` → "Jackpot Results" tab
   - Paste CSV with results
   - Click "Import Jackpot"
   - Click "Compute" to calculate probabilities

3. **For Calibration:**
   - Go to `/calibration-management`
   - Fit calibration using historical data
   - Activate calibration version

---

## Important Notes

- **Odds can be provided in CSV** (recommended for accuracy) or will default to (2.0, 3.0, 2.5)
- **Results are required** when importing jackpot results (that's the purpose of this import)
- **Both odds and results** are needed for:
  - Market disagreement analysis
  - Calibration fitting
  - Backtesting
  - Threshold learning
  - EV-weighted scoring in Decision Intelligence

**Best Practice:** Always include odds in your CSV import for accurate market blending and calibration. If you don't have historical odds, the system will use defaults, but this may reduce accuracy for market disagreement analysis.

---

**Last Updated:** 2026-01-11

