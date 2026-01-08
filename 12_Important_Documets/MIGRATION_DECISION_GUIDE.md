# Migration Decision Guide

## Quick Decision Tree

```
Do you have valuable trained models?
├─ YES → Use HYBRID APPROACH (borrow models + re-ingest matches)
└─ NO  → Use FULL RE-INGESTION (simpler, better data quality)
```

---

## Option 1: Full Re-Ingestion (RECOMMENDED if no valuable models)

### ✅ Pros:
- **Simplest approach** - No ID mapping complexity
- **Best data quality** - All new columns populated
- **Better normalization** - Improved team name matching
- **Full source tracking** - Complete data lineage

### ❌ Cons:
- **Lose computed data** - Models, calibration curves need retraining
- **Takes time** - Full extraction and population

### Steps:
1. ✅ Run new schema: `3_Database_Football_Probability_Engine.sql`
2. ✅ Re-extract data: `extract_football_data.py`
3. ✅ Re-populate database: `populate_database.py`
4. ✅ Re-train models: `model_training.py`
5. ✅ Update statistics: `update_league_statistics.py`

**Time Estimate:** 2-4 hours

---

## Option 2: Hybrid Approach (RECOMMENDED if you have trained models)

### ✅ Pros:
- **Preserve valuable data** - Models, calibration curves, user data
- **Get new columns** - All enhancements included
- **Best of both worlds** - Quality + preserved work

### ⚠️ Cons:
- **Complex ID mapping** - Need to map old IDs to new IDs
- **More steps** - Migration + re-ingestion + updates

### Steps:
1. ✅ Run new schema: `3_Database_Football_Probability_Engine.sql`
2. ✅ **Borrow data:** Run `MIGRATE_FROM_OLD_DB.sql` (with ID mapping)
3. ✅ Re-ingest matches/teams/leagues: `populate_database.py`
4. ✅ Update foreign keys in borrowed tables
5. ✅ Recalculate statistics: `update_league_statistics.py`

**Time Estimate:** 3-5 hours

---

## What Gets Borrowed vs Re-Ingested

| Data Type | Borrow? | Re-Ingest? | Why |
|-----------|---------|------------|-----|
| **Matches** | ❌ | ✅ | Missing 11 new columns |
| **Teams** | ❌ | ✅ | Missing `alternative_names`, better normalization |
| **Leagues** | ⚠️ | ✅ | Better to re-ingest for consistency |
| **Models** | ✅ | ❌ | Valuable trained models |
| **Calibration** | ✅ | ❌ | Valuable calibration curves |
| **Draw Priors** | ✅ | ⚠️ | Can borrow, but better to recalculate |
| **H2H Stats** | ✅ | ⚠️ | Can borrow, but better to recalculate |
| **Elo Ratings** | ✅ | ⚠️ | Can borrow, but better to recalculate |
| **User Data** | ✅ | ❌ | Jackpots, templates, results |

---

## Duplicate Prevention Mechanisms

### ✅ Already Implemented:

1. **Database Constraints:**
   - `UNIQUE (code)` on leagues
   - `UNIQUE (canonical_name, league_id)` on teams
   - `UNIQUE (home_team_id, away_team_id, match_date)` on matches

2. **ON CONFLICT DO UPDATE:**
   - Updates existing records instead of failing
   - Idempotent operations

3. **DISTINCT ON in SQL:**
   - Prevents duplicates at staging level
   - `SELECT DISTINCT ON (match_date, home_team, away_team, league_code)`

4. **Team Name Normalization:**
   - `normalize_team_name()` function
   - Canonical names prevent variations

---

## Final Recommendation

### **If you have trained models you want to keep:**
→ **Use HYBRID APPROACH** (Option 2)

### **If you don't have valuable models or want fresh start:**
→ **Use FULL RE-INGESTION** (Option 1)

---

## Next Steps

1. ✅ **Decide:** Full re-ingestion OR Hybrid
2. ✅ **Run schema:** `3_Database_Football_Probability_Engine.sql`
3. ✅ **If Hybrid:** Run `MIGRATE_FROM_OLD_DB.sql`
4. ✅ **Re-ingest:** Run `populate_database.py`
5. ✅ **Update stats:** Run `update_league_statistics.py`
6. ✅ **Verify:** Check data integrity

---

## Files Created

1. ✅ `FINAL_DEEP_SCAN_ANALYSIS.md` - Complete analysis
2. ✅ `MIGRATE_FROM_OLD_DB.sql` - Migration script
3. ✅ `MIGRATION_DECISION_GUIDE.md` - This file
4. ✅ `populate_database.py` - Updated with new columns

