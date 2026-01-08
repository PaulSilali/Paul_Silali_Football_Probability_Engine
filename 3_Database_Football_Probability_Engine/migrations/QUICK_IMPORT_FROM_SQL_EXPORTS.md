# Quick Import Guide - SQL Export Files

## Your Situation
- ✅ You have SQL export files in `C:\Users\Admin\Desktop\Exported_Football _DB`
- ✅ Database has been deleted, only SQL files remain
- ✅ Need to import valuable data (models, calibration, user data)

---

## Simple Solution: Use pgAdmin's Import Feature

### **Step 1: Import Tables WITHOUT Foreign Keys First**

These tables have no dependencies and can be imported directly:

#### **1. Import Jackpots (No Dependencies)**
```sql
-- Open jackpots_202601081444.sql in pgAdmin
-- Modify: Remove 'id' column, add ON CONFLICT
-- Execute

INSERT INTO jackpots (jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at)
SELECT 
    jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at
FROM (
    VALUES
        ('JK-1767544221', 'anonymous', 'ODI Bets', NULL, 'draft', 'v2.4.1', '2026-01-04 19:30:21.8007+03', '2026-01-04 19:30:21.8007+03')
    -- Copy-paste more from your export file
) AS old(jackpot_id, user_id, name, kickoff_date, status, model_version, created_at, updated_at)
ON CONFLICT (jackpot_id) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    updated_at = now();
```

#### **2. Import Saved Templates (No Dependencies)**
```sql
-- Open saved_jackpot_templates_202601081444.sql
-- Remove 'id' column, add ON CONFLICT
-- Execute

INSERT INTO saved_jackpot_templates (user_id, name, description, fixtures, fixture_count, created_at, updated_at)
SELECT 
    user_id, name, description, fixtures::jsonb, fixture_count, created_at, updated_at
FROM (
    -- Copy-paste VALUES from your export file (remove 'id')
) AS old(...)
ON CONFLICT DO NOTHING;  -- No unique constraint, but safe to skip duplicates
```

#### **3. Import Referee Stats (No Dependencies)**
```sql
-- Open referee_stats_202601081444.sql
-- Remove 'id' column, add ON CONFLICT
-- Execute

INSERT INTO referee_stats (referee_id, referee_name, matches, avg_cards, avg_penalties, draw_rate, updated_at)
SELECT 
    referee_id, referee_name, matches, avg_cards, avg_penalties, draw_rate, updated_at
FROM (
    -- Copy-paste VALUES from your export file (remove 'id')
) AS old(...)
ON CONFLICT (referee_id) DO UPDATE SET
    referee_name = EXCLUDED.referee_name,
    matches = EXCLUDED.matches,
    avg_cards = EXCLUDED.avg_cards,
    avg_penalties = EXCLUDED.avg_penalties,
    draw_rate = EXCLUDED.draw_rate,
    updated_at = now();
```

---

### **Step 2: Import Tables WITH Foreign Keys (After Re-Ingesting Core Data)**

**IMPORTANT:** Do this AFTER re-ingesting matches/teams/leagues, so IDs are available.

#### **1. Import Models (After Schema is Ready)**
```sql
-- Open models_202601081444.sql
-- Remove 'id' column
-- Execute

INSERT INTO models (
    version, model_type, status,
    training_started_at, training_completed_at,
    training_matches, training_leagues, training_seasons,
    decay_rate, blend_alpha,
    brier_score, log_loss, draw_accuracy, overall_accuracy,
    model_weights, created_at, updated_at
)
SELECT 
    version, model_type, status::model_status,
    training_started_at, training_completed_at,
    training_matches, training_leagues::jsonb, training_seasons::jsonb,
    decay_rate, blend_alpha,
    brier_score, log_loss, draw_accuracy, overall_accuracy,
    model_weights::jsonb, created_at, updated_at
FROM (
    -- Copy-paste VALUES from your export file (remove 'id')
) AS old(...)
ON CONFLICT (version) DO UPDATE SET
    model_type = EXCLUDED.model_type,
    status = EXCLUDED.status,
    training_completed_at = EXCLUDED.training_completed_at,
    model_weights = EXCLUDED.model_weights,
    updated_at = now();
```

#### **2. Import Calibration Data (After Models are Imported)**
```sql
-- Open calibration_data_202601081444.sql
-- Map model_id and league_id using subqueries

INSERT INTO calibration_data (
    model_id, league_id, outcome_type,
    predicted_prob_bucket, actual_frequency, sample_count, created_at
)
SELECT 
    (SELECT id FROM models WHERE version = 'v2.4.1') as model_id,  -- Use your model version
    NULL as league_id,  -- Or map: (SELECT id FROM leagues WHERE code = 'E0')
    outcome_type::match_result,
    predicted_prob_bucket,
    actual_frequency,
    sample_count,
    created_at
FROM (
    -- Copy-paste VALUES from your export file (remove 'id', map model_id/league_id)
) AS old(model_id, league_id, outcome_type, predicted_prob_bucket, actual_frequency, sample_count, created_at)
ON CONFLICT (model_id, league_id, outcome_type, predicted_prob_bucket) DO UPDATE SET
    actual_frequency = EXCLUDED.actual_frequency,
    sample_count = EXCLUDED.sample_count;
```

---

## Recommended Workflow

### **Phase 1: Run Schema**
```sql
-- In pgAdmin
-- File → Open → 3_Database_Football_Probability_Engine.sql
-- Execute (F5)
```

### **Phase 2: Import Simple Tables (No Dependencies)**
1. ✅ Import `jackpots` (no dependencies)
2. ✅ Import `saved_jackpot_templates` (no dependencies)
3. ✅ Import `saved_probability_results` (no dependencies)
4. ✅ Import `referee_stats` (no dependencies)

### **Phase 3: Re-Ingest Core Data**
```bash
cd "15_Football_Data_/01_extruction_Script"
python extract_football_data.py --data-dir .. --output-dir output

cd "../02_Db populating_Script"
python populate_database.py --csv ../01_extruction_Script/output/matches_extracted.csv
```

### **Phase 4: Import Tables with Foreign Keys**
1. ✅ Import `models` (after schema ready)
2. ✅ Import `calibration_data` (after models imported)
3. ✅ Import `league_draw_priors` (after leagues re-ingested)
4. ✅ Import `h2h_draw_stats` (after teams re-ingested)
5. ✅ Import `team_elo` (after teams re-ingested)
6. ✅ Import `league_structure` (after leagues re-ingested)
7. ✅ Import `jackpot_fixtures` (after teams/leagues re-ingested)

---

## Quick Reference: What to Import When

| Table | When to Import | Dependencies |
|-------|----------------|--------------|
| `jackpots` | ✅ Phase 2 | None |
| `saved_jackpot_templates` | ✅ Phase 2 | None |
| `saved_probability_results` | ✅ Phase 2 | None |
| `referee_stats` | ✅ Phase 2 | None |
| `models` | ✅ Phase 4 | None (but better after schema) |
| `calibration_data` | ✅ Phase 4 | models, leagues |
| `league_draw_priors` | ✅ Phase 4 | leagues |
| `h2h_draw_stats` | ✅ Phase 4 | teams |
| `team_elo` | ✅ Phase 4 | teams |
| `league_structure` | ✅ Phase 4 | leagues |
| `jackpot_fixtures` | ✅ Phase 4 | teams, leagues, jackpots |

---

## Tips

1. **Use pgAdmin's Query Tool:**
   - Open SQL file
   - Copy INSERT statements
   - Modify to remove 'id' and add ON CONFLICT
   - Execute

2. **For Large Files:**
   - Use `\i` command in psql: `\i C:\Users\Admin\Desktop\Exported_Football _DB\jackpots_202601081444.sql`
   - Or use the Python script: `import_from_sql_exports.py`

3. **Test First:**
   - Import one table at a time
   - Verify data after each import
   - Check foreign key relationships

---

## Files Created

1. ✅ `import_from_sql_exports.py` - Automated import script
2. ✅ `IMPORT_SQL_EXPORTS_SIMPLE.sql` - Simple template
3. ✅ `QUICK_IMPORT_FROM_SQL_EXPORTS.md` - This guide
4. ✅ `INGESTION_AND_MIGRATION_GUIDE.md` - Complete guide

