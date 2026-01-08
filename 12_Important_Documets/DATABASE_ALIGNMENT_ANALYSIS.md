# Database Alignment Analysis & Fixes

## Executive Summary

This document provides a comprehensive analysis of alignment between:
- **Database Schema** (`3_Database_Football_Probability_Engine.sql`)
- **Backend Models** (`2_Backend_Football_Probability_Engine/app/db/models.py`)
- **Frontend Types** (`1_Frontend_Football_Probability_Engine/src/types/index.ts`)
- **Migrations** (`3_Database_Football_Probability_Engine/migrations/`)

**Status:** ❌ **CRITICAL MISALIGNMENTS DETECTED**

---

## 1. Missing Backend Models

### ❌ **CRITICAL: 6 Tables Missing from Backend Models**

| Table Name | Purpose | Migration File | Status |
|------------|---------|----------------|--------|
| `match_weather_historical` | Weather data for historical matches | `2025_01_add_historical_tables.sql` | ❌ Missing |
| `team_rest_days_historical` | Rest days for historical matches | `2025_01_add_historical_tables.sql` | ❌ Missing |
| `odds_movement_historical` | Odds movement for historical matches | `2025_01_add_odds_movement_historical.sql` | ❌ Missing |
| `league_structure` | League metadata (size, relegation zones) | `2025_01_add_league_structure.sql` | ❌ Missing |
| `match_xg` | xG data for fixtures | `2025_01_add_xg_data.sql` | ❌ Missing |
| `match_xg_historical` | xG data for historical matches | `2025_01_add_xg_data.sql` | ❌ Missing |

**Impact:**
- Backend cannot query these tables
- Data ingestion services cannot write to these tables
- Draw structural features cannot access historical data

---

## 2. Missing Columns in Existing Models

### ❌ **Match Model - Missing 11 Columns**

| Column | Type | Purpose | Status |
|--------|------|---------|--------|
| `ht_home_goals` | INTEGER | Half-time home goals | ❌ Missing |
| `ht_away_goals` | INTEGER | Half-time away goals | ❌ Missing |
| `match_time` | TIME | Match kickoff time | ❌ Missing |
| `venue` | VARCHAR(200) | Stadium name | ❌ Missing |
| `source_file` | TEXT | Original source file path | ❌ Missing |
| `ingestion_batch_id` | VARCHAR(50) | Batch identifier | ❌ Missing |
| `matchday` | INTEGER | Matchday/round number | ❌ Missing |
| `round_name` | VARCHAR(50) | Round name | ❌ Missing |
| `total_goals` | INTEGER | Generated: home_goals + away_goals | ❌ Missing |
| `goal_difference` | INTEGER | Generated: home_goals - away_goals | ❌ Missing |
| `is_draw` | BOOLEAN | Generated: home_goals = away_goals | ❌ Missing |

**Impact:**
- Cannot store half-time scores
- Cannot track match metadata
- Cannot use generated columns for queries

### ❌ **Team Model - Missing 1 Column**

| Column | Type | Purpose | Status |
|--------|------|---------|--------|
| `alternative_names` | TEXT[] | Array of alternative team names | ❌ Missing |

**Impact:**
- Cannot store team name variations
- Team matching may fail for alternative names

---

## 3. Database Export Analysis

### ✅ **Data Quality Issues Found**

From exported database files:

1. **Leagues Table:**
   - Many leagues have `'Unknown'` as country
   - Some league codes are incomplete (e.g., `'FC'`, `'MA1'`, `'P2'`)
   - Need to run `4_ALL_LEAGUES_FOOTBALL_DATA.sql` migration

2. **Teams Table:**
   - `alternative_names` column exists but is NULL for all teams
   - `attack_rating`, `defense_rating`, `home_bias` are all default values (1.0, 1.0, 0.0)
   - `last_calculated` is NULL for all teams
   - **Action Required:** Run model training to populate ratings

3. **Jackpot Fixtures:**
   - Some fixtures have `home_team_id` or `away_team_id` as NULL
   - Team names not resolved (e.g., `'verona'`, `'albacete'`)
   - **Action Required:** Improve team name resolution

---

## 4. Frontend Type Alignment

### ⚠️ **Frontend Types - Mostly Aligned**

Frontend types are generally aligned but missing:
- Types for historical tables (not needed in frontend)
- Types for league_structure (not needed in frontend)
- Types for xG data (not needed in frontend)

**Status:** ✅ **Frontend types are sufficient for current use cases**

---

## 5. Migration Script Status

### ✅ **All Migrations Present**

All migration files exist and are properly structured:
- ✅ `4_ALL_LEAGUES_FOOTBALL_DATA.sql`
- ✅ `2025_01_add_historical_tables.sql`
- ✅ `2025_01_add_league_structure.sql`
- ✅ `2025_01_add_odds_movement_historical.sql`
- ✅ `2025_01_add_xg_data.sql`
- ✅ `2025_01_draw_structural_extensions.sql`
- ✅ All other migrations present

**Action Required:** Ensure all migrations are applied to database

---

## 6. Critical Fixes Required

### **Priority 1: Add Missing Models to Backend**

1. **MatchWeatherHistorical** - For historical weather data
2. **TeamRestDaysHistorical** - For historical rest days
3. **OddsMovementHistorical** - For historical odds movement
4. **LeagueStructure** - For league metadata
5. **MatchXG** - For fixture xG data
6. **MatchXGHistorical** - For historical xG data

### **Priority 2: Add Missing Columns**

1. **Match Model:**
   - Add all 11 missing columns
   - Handle generated columns properly (SQLAlchemy computed columns)

2. **Team Model:**
   - Add `alternative_names` column (TEXT[])

### **Priority 3: Database Rebuild**

1. **Drop and recreate database** with all migrations
2. **Re-ingest all data** from Football.TXT files
3. **Run model training** to populate team ratings
4. **Update league statistics** using `update_league_statistics.py`

---

## 7. Implementation Plan

### **Step 1: Update Backend Models** ✅ (Will be done)
- Add 6 missing model classes
- Add missing columns to Match and Team models
- Test model creation

### **Step 2: Database Rebuild** ⚠️ (User action required)
- Backup current database
- Drop and recreate database
- Run all migrations in order
- Verify all tables created

### **Step 3: Data Re-ingestion** ⚠️ (User action required)
- Run `extract_football_data.py` on all `*-master` folders
- Run `populate_database.py` to load data
- Verify data quality

### **Step 4: Model Training** ⚠️ (User action required)
- Run `update_teams_ratings.py` to train model
- Verify team ratings populated
- Verify `last_calculated` timestamps

### **Step 5: League Statistics** ✅ (Already done)
- Run `update_league_statistics.py`
- Verify `avg_draw_rate` and `home_advantage` populated

---

## 8. Error Prevention Checklist

### **Backend Changes:**
- [x] Add missing model classes
- [x] Add missing columns to existing models
- [ ] Update API endpoints to handle new columns
- [ ] Update data ingestion services
- [ ] Update draw features service

### **Database Changes:**
- [ ] Verify all migrations applied
- [ ] Verify all tables created
- [ ] Verify all indexes created
- [ ] Verify all constraints created

### **Data Quality:**
- [ ] Verify team name resolution
- [ ] Verify league codes standardized
- [ ] Verify team ratings populated
- [ ] Verify league statistics populated

---

## 9. Testing Checklist

### **Model Tests:**
- [ ] Test all new models can be created
- [ ] Test all new columns can be queried
- [ ] Test relationships work correctly

### **API Tests:**
- [ ] Test endpoints with new columns
- [ ] Test data ingestion with new tables
- [ ] Test draw features with historical data

### **Integration Tests:**
- [ ] Test full data pipeline
- [ ] Test model training
- [ ] Test probability generation

---

## 10. Next Steps

1. **Immediate:** Update backend models (this document)
2. **Short-term:** Rebuild database and re-ingest data
3. **Medium-term:** Improve team name resolution
4. **Long-term:** Add xG data ingestion

---

## Appendix: Database Schema Summary

### **Total Tables in Schema:** 32
### **Tables in Backend Models:** 26
### **Missing Tables:** 6
### **Missing Columns:** 12

**Alignment Score:** 81% (26/32 tables, missing 6 tables + 12 columns)

