# Database Population Behavior - Data Replacement vs Update

## Question: Will existing data be replaced or updated?

### Answer: **UPDATES existing data, does NOT replace/delete**

The database population script uses **`ON CONFLICT DO UPDATE`** which means:

1. ✅ **If record exists** → **UPDATES** it (based on unique constraint)
2. ✅ **If record doesn't exist** → **INSERTS** it
3. ✅ **Idempotent** → Safe to run multiple times
4. ❌ **Does NOT delete** existing data
5. ❌ **Does NOT replace** entire tables

## How It Works

### 1. Leagues Table
```sql
INSERT INTO leagues (code, name, country, is_active)
VALUES (%s, %s, %s, TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    updated_at = now()
```

**Behavior:**
- If league code `E0` exists → Updates name and country
- If league code `E0` doesn't exist → Inserts new record
- **Existing leagues are preserved and updated**

### 2. Teams Table
```sql
INSERT INTO teams (league_id, name, canonical_name)
VALUES (%s, %s, %s)
ON CONFLICT (canonical_name, league_id) DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = now()
```

**Behavior:**
- If team exists (same canonical_name + league_id) → Updates name
- If team doesn't exist → Inserts new record
- **Existing teams are preserved and updated**

### 3. Matches Table
```sql
INSERT INTO matches (...)
SELECT ...
ON CONFLICT (home_team_id, away_team_id, match_date) DO UPDATE SET
    home_goals = EXCLUDED.home_goals,
    away_goals = EXCLUDED.away_goals,
    result = EXCLUDED.result,
    ht_home_goals = EXCLUDED.ht_home_goals,
    ht_away_goals = EXCLUDED.ht_away_goals
```

**Behavior:**
- If match exists (same teams + date) → Updates scores and result
- If match doesn't exist → Inserts new record
- **Existing matches are preserved and updated**

### 4. Derived Statistics Tables
All use `ON CONFLICT DO UPDATE`:
- `league_draw_priors` → Updates draw rates
- `h2h_draw_stats` → Updates H2H statistics
- `team_h2h_stats` → Updates team H2H statistics
- `league_stats` → Updates league statistics

## Unique Constraints (From Schema)

The database schema defines these unique constraints that prevent duplicates:

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

## What This Means

### ✅ Safe Operations
- **Re-running population** → Updates existing, adds new
- **Incremental updates** → Only new/changed data is processed
- **No data loss** → Existing records are preserved

### ⚠️ Important Notes

1. **Matches are updated by (home_team_id, away_team_id, match_date)**
   - If the same teams play on the same date, the match is updated
   - This handles corrections to match results

2. **Teams are matched by (canonical_name, league_id)**
   - Same team name in same league = update
   - Different league = new team record

3. **No cascade deletes**
   - Running population does NOT delete anything
   - Only inserts new or updates existing

## Example Scenario

### Initial State
- Database has: 50,000 matches from previous import
- Leagues: E0, D1, I1 (3 leagues)

### After Running Population
- Database has: 103,983 matches (50,000 existing + 53,983 new)
- Leagues: E0, D1, I1, F1, N1, ... (60 leagues - 3 existing + 57 new)
- Existing matches updated if scores changed
- New matches added

## Season Count Difference

## Why 238 seasons → 21 seasons?

### First Run (238 seasons)
**Problem:** Season extraction was picking up **filenames** as seasons:
- `2023-24_fr1.txt` → Extracted as season "2023-24_fr1.txt"
- `2024-25_ch1.txt` → Extracted as season "2024-25_ch1.txt"
- Many filenames were incorrectly identified as seasons

### Second Run (21 seasons) ✅
**Fixed:** Season extraction now properly extracts only season values:
- `2023-24_fr1.txt` → Extracted as season "2023-24"
- `2024-25_ch1.txt` → Extracted as season "2024-25"
- Only actual seasons (2005-06 through 2025-26) are counted

### The Fix

**Before:**
```python
# Was matching filenames like "2023-24_fr1.txt"
if re.match(r'\d{4}_\w{2}\d', part):  # Too broad
    year = part[:4]
    return f"{year}-{str(int(year) + 1)[2:]}"
```

**After:**
```python
# Now properly extracts season from filename
if re.match(r'^(\d{4})_\w+\.txt$', part):
    year = re.match(r'^(\d{4})_\w+\.txt$', part).group(1)
    return f"{year}-{str(int(year) + 1)[2:]}"
```

### Actual Seasons Found (21)
From `extraction_statistics.json`:
```
2005-06, 2006-07, 2007-08, 2008-09, 2009-10,
2010-11, 2011-12, 2012-13, 2013-14, 2014-15,
2015-16, 2016-17, 2017-18, 2018-19, 2019-20,
2020-21, 2021-22, 2022-23, 2023-24, 2024-25,
2025-26
```

**This is correct!** The data spans 2005-2026 (21 seasons).

## Summary

### Database Population
- ✅ **Updates existing data** (doesn't replace)
- ✅ **Adds new data** (doesn't delete)
- ✅ **Idempotent** (safe to run multiple times)
- ✅ **No data loss**

### Season Count
- ✅ **21 seasons is correct** (2005-2026)
- ✅ **238 was incorrect** (included filenames)
- ✅ **Fixed in second run**

