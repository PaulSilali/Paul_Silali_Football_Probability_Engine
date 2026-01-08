# Final Deep Scan Analysis - Database Migration Strategy

## Executive Summary

**RECOMMENDATION: HYBRID APPROACH**
- ✅ **BORROW** valuable computed data (models, calibration_data, league_draw_priors, etc.)
- ✅ **RE-INGEST** matches/teams/leagues to get new columns and ensure data quality
- ✅ **PRESERVE** foreign key relationships where possible

---

## 1. What's Missing from Old Database

### **New Columns in Schema (Not in Old DB)**

#### **Matches Table:**
- ✅ `ht_home_goals` - Half-time goals (NULL in old DB)
- ✅ `ht_away_goals` - Half-time goals (NULL in old DB)
- ✅ `match_time` - Kickoff time (NULL in old DB)
- ✅ `venue` - Stadium name (NULL in old DB)
- ✅ `source_file` - Source file path (NULL in old DB)
- ✅ `ingestion_batch_id` - Batch tracking (NULL in old DB)
- ✅ `matchday` - Matchday number (NULL in old DB)
- ✅ `round_name` - Round name (NULL in old DB)
- ✅ `total_goals` - Computed column (auto-generated)
- ✅ `goal_difference` - Computed column (auto-generated)
- ✅ `is_draw` - Computed column (auto-generated)

#### **Teams Table:**
- ✅ `alternative_names` - Array of alternative names (NULL in old DB)

#### **Training Runs Table:**
- ✅ `avg_entropy` - Average entropy (NULL in old DB)
- ✅ `p10_entropy` - 10th percentile entropy (NULL in old DB)
- ✅ `p90_entropy` - 90th percentile entropy (NULL in old DB)
- ✅ `temperature` - Temperature parameter (NULL in old DB)
- ✅ `alpha_mean` - Mean alpha (NULL in old DB)

---

## 2. Duplicate Prevention Mechanisms

### **Current Implementation (populate_database.py)**

#### **1. Database-Level Constraints:**
```sql
-- Leagues
CONSTRAINT uix_league UNIQUE (code)

-- Teams
CONSTRAINT uix_team_league UNIQUE (canonical_name, league_id)

-- Matches
CONSTRAINT uix_match UNIQUE (home_team_id, away_team_id, match_date)

-- League Draw Priors
CONSTRAINT uix_league_draw_prior UNIQUE (league_id, season)

-- H2H Stats
CONSTRAINT uix_h2h_draw_pair UNIQUE (team_home_id, team_away_id)
```

#### **2. ON CONFLICT DO UPDATE:**
- ✅ **Leagues:** Updates name, country if code exists
- ✅ **Teams:** Updates name if canonical_name + league_id exists
- ✅ **Matches:** Updates scores if same teams + date exists
- ✅ **Derived Stats:** Updates calculated values

#### **3. DISTINCT ON in SQL:**
```sql
SELECT DISTINCT ON (r.match_date, r.home_team, r.away_team, r.league_code)
    r.*
FROM staging.matches_raw r
ORDER BY r.match_date, r.home_team, r.away_team, r.league_code, r.source_file
```
- Prevents duplicates at staging level before insertion

#### **4. Team Name Normalization:**
- `normalize_team_name()` function ensures consistent matching
- Canonical names prevent "Man Utd" vs "Manchester United" duplicates

---

## 3. What Can Be Borrowed (Safe to Import)

### **✅ SAFE TO BORROW (No Schema Changes)**

1. **Models** (`models`)
   - ✅ Model weights, training metadata
   - ✅ Unique by version
   - ⚠️ Need to map model_id if IDs change

2. **Calibration Data** (`calibration_data`)
   - ✅ Isotonic regression curves
   - ⚠️ Need to map model_id

3. **League Draw Priors** (`league_draw_priors`)
   - ✅ Historical draw rates per league/season
   - ⚠️ Need to map league_id

4. **H2H Draw Stats** (`h2h_draw_stats`)
   - ✅ Head-to-head statistics
   - ⚠️ Need to map team_id

5. **Team Elo** (`team_elo`)
   - ✅ Elo ratings over time
   - ⚠️ Need to map team_id

6. **Referee Stats** (`referee_stats`)
   - ✅ Referee statistics
   - ✅ No dependencies

7. **League Structure** (`league_structure`)
   - ✅ League metadata
   - ⚠️ Need to map league_id

8. **Jackpots & Fixtures** (`jackpots`, `jackpot_fixtures`)
   - ✅ User-created jackpots
   - ⚠️ Need to map team_id, league_id

9. **Saved Templates** (`saved_jackpot_templates`, `saved_probability_results`)
   - ✅ User data
   - ✅ No dependencies

10. **Training Runs** (`training_runs`)
    - ✅ Training history
    - ⚠️ Need to map model_id
    - ⚠️ Missing entropy columns (will be NULL)

---

## 4. What Should Be Re-Ingested

### **❌ RE-INGEST (Has New Columns or Better Data Quality)**

1. **Matches** (`matches`)
   - ❌ Missing new columns (ht_home_goals, match_time, venue, etc.)
   - ❌ Better to re-extract from source files
   - ✅ Can preserve IDs if needed (but not recommended)

2. **Teams** (`teams`)
   - ❌ Missing `alternative_names` column
   - ❌ Better to re-extract for normalization
   - ⚠️ IDs will change (need mapping)

3. **Leagues** (`leagues`)
   - ⚠️ Can borrow, but re-ingestion ensures consistency
   - ✅ IDs will change (need mapping)

---

## 5. Data Accuracy Concerns

### **Potential Issues in Old DB:**

1. **Team Name Inconsistencies:**
   - Old DB: `'Man United'` → canonical: `'man'` (WRONG!)
   - New normalization: `'manchester united'` → canonical: `'manchester united'`
   - **Impact:** Team matching will fail

2. **Missing Half-Time Scores:**
   - Old DB: All `ht_home_goals` = NULL
   - New schema: Can extract from source files
   - **Impact:** Loss of valuable data for analysis

3. **Missing Source Tracking:**
   - Old DB: No `source_file` or `ingestion_batch_id`
   - New schema: Full traceability
   - **Impact:** Cannot track data lineage

4. **League Statistics:**
   - Old DB: `avg_draw_rate` and `home_advantage` calculated
   - New schema: Can recalculate from matches
   - **Impact:** Should recalculate for accuracy

---

## 6. Recommended Strategy

### **OPTION A: Full Re-Ingestion (RECOMMENDED)**

**Pros:**
- ✅ All new columns populated
- ✅ Better data quality (normalized team names)
- ✅ Full source tracking
- ✅ No ID mapping complexity

**Cons:**
- ❌ Lose computed data (models, calibration)
- ❌ Takes time to re-extract

**Steps:**
1. Run new schema
2. Re-extract from Football.TXT files
3. Re-populate matches/teams/leagues
4. Re-train models (or import from old DB separately)

---

### **OPTION B: Hybrid Approach (BEST OF BOTH)**

**Pros:**
- ✅ Preserve valuable computed data
- ✅ Get new columns for matches
- ✅ Best data quality

**Cons:**
- ⚠️ Complex ID mapping
- ⚠️ Need careful migration

**Steps:**
1. Run new schema
2. **BORROW:** models, calibration_data, league_draw_priors (with ID mapping)
3. **RE-INGEST:** matches, teams, leagues (to get new columns)
4. **UPDATE:** Foreign keys in borrowed tables

---

## 7. ID Mapping Strategy

If borrowing data, need to map:

```sql
-- Old ID → New ID mappings
CREATE TEMP TABLE id_mappings (
    table_name TEXT,
    old_id INTEGER,
    new_id INTEGER
);

-- Example: Map leagues
INSERT INTO id_mappings (table_name, old_id, new_id)
SELECT 'leagues', old.id, new.id
FROM old_db.leagues old
JOIN new_db.leagues new ON old.code = new.code;

-- Example: Map teams
INSERT INTO id_mappings (table_name, old_id, new_id)
SELECT 'teams', old.id, new.id
FROM old_db.teams old
JOIN new_db.teams new 
    ON old.canonical_name = new.canonical_name
    AND old.league_id = (SELECT new_id FROM id_mappings WHERE old_id = old.league_id);
```

---

## 8. Final Recommendation

### **✅ RECOMMENDED: Hybrid Approach**

1. **Run new schema** (`3_Database_Football_Probability_Engine.sql`)
2. **Borrow valuable data** using `MIGRATE_FROM_OLD_DB.sql` (see separate script)
3. **Re-ingest matches/teams/leagues** using `populate_database.py`
4. **Update foreign keys** in borrowed tables
5. **Recalculate statistics** using `update_league_statistics.py`

**Why:**
- Preserves trained models and calibration curves
- Gets new columns and better data quality
- Maintains data integrity

---

## 9. Tables Summary

| Table | Borrow? | Re-Ingest? | Reason |
|-------|---------|------------|--------|
| `leagues` | ⚠️ | ✅ | Better to re-ingest for consistency |
| `teams` | ❌ | ✅ | Missing `alternative_names`, better normalization |
| `matches` | ❌ | ✅ | Missing 11 new columns |
| `models` | ✅ | ❌ | Valuable trained models |
| `calibration_data` | ✅ | ❌ | Valuable calibration curves |
| `league_draw_priors` | ✅ | ⚠️ | Can borrow, but better to recalculate |
| `h2h_draw_stats` | ✅ | ⚠️ | Can borrow, but better to recalculate |
| `team_elo` | ✅ | ⚠️ | Can borrow, but better to recalculate |
| `referee_stats` | ✅ | ❌ | No dependencies |
| `league_structure` | ✅ | ❌ | Static metadata |
| `jackpots` | ✅ | ❌ | User data |
| `jackpot_fixtures` | ✅ | ⚠️ | Need team_id mapping |
| `saved_jackpot_templates` | ✅ | ❌ | User data |
| `saved_probability_results` | ✅ | ❌ | User data |
| `training_runs` | ✅ | ❌ | Training history (missing entropy columns) |

---

## 10. Next Steps

1. ✅ Review this analysis
2. ✅ Decide: Full re-ingestion OR Hybrid
3. ✅ If Hybrid: Run `MIGRATE_FROM_OLD_DB.sql`
4. ✅ Re-ingest matches/teams/leagues
5. ✅ Update foreign keys
6. ✅ Recalculate statistics
7. ✅ Verify data integrity

