# End-to-End Production Test Suite

## Overview

This comprehensive test suite runs the **complete production pipeline** from data ingestion to backtesting with **real production data**. It tests all stages sequentially and only proceeds if each stage succeeds.

## Test Stages

### Stage 1: Data Ingestion
- Downloads real data for all configured leagues
- Tests all data sources:
  - `football-data.co.uk` (CSV)
  - `football-data.org` (API)
  - `OpenFootball` (TXT/JSON)
- Automatically removes data sources that don't work
- Ingests both:
  - **Historical Match & Odds Data** → `data/1_data_ingestion/Historical Match_Odds_Data/`
  - **Draw Structural Data** → `data/1_data_ingestion/Draw_structural/`
    - League Priors
    - H2H Stats
    - Elo Ratings
    - Weather
    - Referee
    - Rest Days
    - Odds Movement
- Verifies table population: `matches`, `teams`, `leagues`, `league_draw_priors`, `h2h_draw_stats`, `team_elo`

### Stage 2: Data Cleaning & ETL
- Verifies cleaning is integrated into ingestion pipeline
- Checks cleaned data storage: `data/2_Cleaned_data/Historical Match_Odds_Data/`
- Validates data quality

### Stage 3: Model Training
- Trains **Poisson Model** (Dixon-Coles)
- Trains **Blending Model** (Model + Market odds)
- Trains **Calibration Model** (Isotonic regression)
- Verifies models stored in `models` table

### Stage 4: Probability Generation
- Creates jackpots from extracted image data (5 jackpots, 75 fixtures)
- Generates probabilities for all sets (A-G)
- Stores predictions in `predictions` table

### Stage 5: Validation & Backtesting
- Validates jackpots with actual results
- Checks validation tables: `validation_results`, `calibration_data`
- Prepares for model fine-tuning

## File Organization

### Production Data (NO "test" in names)
- **Raw Data**: `data/1_data_ingestion/Historical Match_Odds_Data/`
- **Draw Data**: `data/1_data_ingestion/Draw_structural/`
- **Cleaned Data**: `data/2_Cleaned_data/Historical Match_Odds_Data/`
- **Cleaned Draw Data**: `data/2_Cleaned_data/Draw_structural/`

### Test Scripts
- **Test Script**: `Test_Scripts/end_to_end_production_test.py`
- **Test Results**: `Test_Scripts/test_results/e2e_test_YYYYMMDD_HHMMSS.json`

## Usage

### Prerequisites
1. Database is running and accessible
2. Backend API is running on `http://localhost:8000`
3. Environment variables configured (`.env` file)

### Run the Test

```bash
cd 2_Backend_Football_Probability_Engine
python Test_Scripts/end_to_end_production_test.py
```

### Reset Database (Optional)

Before running the test, you can reset all tables to zero:

```sql
-- Reset all tables (CAUTION: This deletes all data!)
TRUNCATE TABLE matches, teams, leagues, predictions, models, 
  league_draw_priors, h2h_draw_stats, team_elo, 
  match_weather, referee_stats, team_rest_days, odds_movement CASCADE;
```

## Test Behavior

### Sequential Execution
- Each stage **only runs if previous stage succeeds**
- If Stage 1 fails, Stages 2-5 are skipped
- Test stops at first failure

### Data Source Testing
- Tests all 3 data sources for each league
- Uses first working source
- Removes logic for sources that consistently fail
- Reports working/failed sources in results

### Production-Level
- **No test session folders** for ingestion/cleaning/training
- All data stored in production folders
- Real data downloads (not mock data)
- Actual database operations

## Expected Results

### Successful Run
```
✅ Stage 1: Data Ingestion - 20+ leagues ingested
✅ Stage 2: Data Cleaning - Verified
✅ Stage 3: Model Training - All models trained
✅ Stage 4: Probability Generation - Probabilities generated
✅ Stage 5: Validation & Backtesting - Tables checked
```

### Table Population (After Stage 1)
- `matches`: 1000+ records
- `teams`: 100+ records
- `leagues`: 20+ records
- `league_draw_priors`: 1+ records
- `h2h_draw_stats`: 1+ records
- `team_elo`: 20+ records

### Model Training (After Stage 3)
- `models`: 3+ records (Poisson, Blending, Calibration)
- All models with `status = 'active'`

### Predictions (After Stage 4)
- `predictions`: 15+ records (one per jackpot fixture)
- `jackpots`: 1+ records
- `jackpot_fixtures`: 15+ records

## Troubleshooting

### Stage 1 Fails
- **Check**: Database connection, API availability
- **Check**: Data source URLs are accessible
- **Check**: League codes are correct
- **Solution**: Review `data_source_status` in results JSON

### Stage 3 Fails
- **Check**: At least 100 matches in database
- **Check**: Matches have valid odds data
- **Solution**: Run Stage 1 with more leagues/seasons

### Stage 4 Fails
- **Check**: Active model exists in database
- **Check**: Teams can be resolved (team_resolver)
- **Solution**: Ensure Stage 3 completed successfully

## Results JSON Structure

```json
{
  "stage1_data_ingestion": {
    "success": true,
    "ingested_leagues": ["E0", "E1", ...],
    "failed_leagues": [],
    "working_sources": {
      "football-data.co.uk": ["E0", "E1", ...],
      "football-data.org": ["SWE1", ...],
      "OpenFootball": ["ARG1", ...]
    },
    "table_counts": {
      "matches": 1234,
      "teams": 150,
      ...
    }
  },
  "stage2_data_cleaning": {...},
  "stage3_model_training": {...},
  "stage4_probability_generation": {...},
  "stage5_validation_backtesting": {...},
  "test_metadata": {
    "start_time": "...",
    "end_time": "...",
    "duration_seconds": 1234.56
  }
}
```

## Continuous Testing

To run continuously until all stages pass:

```bash
while true; do
  python Test_Scripts/end_to_end_production_test.py
  if [ $? -eq 0 ]; then
    echo "All stages passed!"
    break
  fi
  echo "Retrying in 60 seconds..."
  sleep 60
done
```

## Notes

- **Production Data**: All ingested data is stored in production folders (not test sessions)
- **Real Downloads**: Uses actual data sources (not mocks)
- **Database Operations**: All operations write to real database
- **No Test Prefixes**: Files saved without "test" in names
- **Sequential**: Stages run one at a time, not in parallel

