# Complete Leagues List - Current Status

## ❌ **No, the SQL schema list is NOT complete**

The SQL schema only includes **5 leagues**, but the frontend shows **10 leagues** available for download.

---

## Current Leagues in SQL Schema

**File:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql` (lines 590-596)

```sql
INSERT INTO leagues (code, name, country, home_advantage) VALUES
    ('E0', 'Premier League', 'England', 0.35),
    ('SP1', 'La Liga', 'Spain', 0.30),
    ('D1', 'Bundesliga', 'Germany', 0.32),
    ('I1', 'Serie A', 'Italy', 0.28),
    ('F1', 'Ligue 1', 'France', 0.33)
ON CONFLICT (code) DO NOTHING;
```

**Total: 5 leagues** ❌ **INCOMPLETE**

---

## Leagues Shown in Frontend

**File:** `1_Frontend_Football_Probability_Engine/src/pages/DataIngestion.tsx` (lines 99-109)

```typescript
const initialDataSources: DataSource[] = [
  { id: '1', name: 'Premier League', leagues: ['E0'], ... },
  { id: '2', name: 'Championship', leagues: ['E1'], ... },        // ❌ Missing
  { id: '3', name: 'La Liga', leagues: ['SP1'], ... },
  { id: '4', name: 'Bundesliga', leagues: ['D1'], ... },
  { id: '5', name: 'Serie A', leagues: ['I1'], ... },
  { id: '6', name: 'Ligue 1', leagues: ['F1'], ... },
  { id: '7', name: 'League One', leagues: ['E2'], ... },           // ❌ Missing
  { id: '8', name: 'League Two', leagues: ['E3'], ... },            // ❌ Missing
  { id: '9', name: 'Eredivisie', leagues: ['N1'], ... },          // ❌ Missing
  { id: '10', name: 'Primeira Liga', leagues: ['P1'], ... },       // ❌ Missing
];
```

**Total: 10 leagues** (5 missing from SQL schema)

---

## Missing Leagues from SQL Schema

| Code | League Name | Country | Tier | Status |
|------|-------------|---------|------|--------|
| `E1` | Championship | England | 2 | ❌ Missing |
| `E2` | League One | England | 3 | ❌ Missing |
| `E3` | League Two | England | 4 | ❌ Missing |
| `N1` | Eredivisie | Netherlands | 1 | ❌ Missing |
| `P1` | Primeira Liga | Portugal | 1 | ❌ Missing |

---

## Are Leagues Updated/Created During Download?

### ❌ **NO - Leagues are NOT created or updated during download**

**Code Location:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py` (lines 67-72)

```python
# Get league
league = self.db.query(League).filter(
    League.code == league_code
).first()

if not league:
    raise ValueError(f"League not found: {league_code}")
```

**What happens:**
1. System looks up league by `code` (e.g., `'E0'`)
2. If league **doesn't exist**, ingestion **FAILS** with error
3. League must exist **BEFORE** downloading data
4. Leagues are **NOT** created automatically during download

---

## How Leagues Are Created

### Option 1: SQL Schema Seed Data
- **File:** `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`
- **When:** Run during database initialization
- **Current:** Only 5 leagues

### Option 2: Python Function
- **File:** `2_Backend_Football_Probability_Engine/app/services/data_ingestion.py`
- **Function:** `create_default_leagues()`
- **When:** Called via `POST /api/data/init-leagues` endpoint
- **Problem:** Uses **wrong codes** (`EPL`, `LaLiga` instead of `E0`, `SP1`)

### Option 3: Manual SQL Insert
- Run SQL INSERT statements manually
- Most reliable method

---

## Complete List of Leagues (Recommended)

Based on frontend and football-data.co.uk availability:

```sql
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active) VALUES
    -- Top 5 European Leagues
    ('E0', 'Premier League', 'England', 1, 0.26, 0.35, TRUE),
    ('SP1', 'La Liga', 'Spain', 1, 0.25, 0.30, TRUE),
    ('D1', 'Bundesliga', 'Germany', 1, 0.24, 0.32, TRUE),
    ('I1', 'Serie A', 'Italy', 1, 0.27, 0.28, TRUE),
    ('F1', 'Ligue 1', 'France', 1, 0.26, 0.33, TRUE),
    
    -- English Lower Tiers
    ('E1', 'Championship', 'England', 2, 0.27, 0.33, TRUE),
    ('E2', 'League One', 'England', 3, 0.28, 0.32, TRUE),
    ('E3', 'League Two', 'England', 4, 0.29, 0.31, TRUE),
    
    -- Additional European Leagues
    ('N1', 'Eredivisie', 'Netherlands', 1, 0.25, 0.31, TRUE),
    ('P1', 'Primeira Liga', 'Portugal', 1, 0.26, 0.34, TRUE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    country = EXCLUDED.country,
    tier = EXCLUDED.tier,
    avg_draw_rate = EXCLUDED.avg_draw_rate,
    home_advantage = EXCLUDED.home_advantage,
    is_active = EXCLUDED.is_active;
```

**Total: 10 leagues** ✅ **COMPLETE**

---

## Issues Found

### 1. **Incomplete SQL Schema**
- Only 5 leagues in SQL schema
- Frontend expects 10 leagues
- Downloads will fail for missing leagues

### 2. **Wrong League Codes in Python Function**
- `create_default_leagues()` uses `'EPL'`, `'LaLiga'` instead of `'E0'`, `'SP1'`
- These codes don't match football-data.co.uk format
- Will cause ingestion failures

### 3. **No Auto-Creation During Download**
- Leagues must exist before download
- No automatic league creation
- Missing leagues cause download failures

---

## Recommendations

### ✅ **Immediate Fix: Update SQL Schema**

Add missing leagues to `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql`:

```sql
-- Add missing leagues
INSERT INTO leagues (code, name, country, tier, avg_draw_rate, home_advantage, is_active) VALUES
    ('E1', 'Championship', 'England', 2, 0.27, 0.33, TRUE),
    ('E2', 'League One', 'England', 3, 0.28, 0.32, TRUE),
    ('E3', 'League Two', 'England', 4, 0.29, 0.31, TRUE),
    ('N1', 'Eredivisie', 'Netherlands', 1, 0.25, 0.31, TRUE),
    ('P1', 'Primeira Liga', 'Portugal', 1, 0.26, 0.34, TRUE)
ON CONFLICT (code) DO NOTHING;
```

### ✅ **Fix Python Function**

Update `create_default_leagues()` to use correct codes:

```python
default_leagues = [
    {"code": "E0", "name": "Premier League", "country": "England", "tier": 1},
    {"code": "E1", "name": "Championship", "country": "England", "tier": 2},
    {"code": "SP1", "name": "La Liga", "country": "Spain", "tier": 1},
    {"code": "D1", "name": "Bundesliga", "country": "Germany", "tier": 1},
    {"code": "I1", "name": "Serie A", "country": "Italy", "tier": 1},
    {"code": "F1", "name": "Ligue 1", "country": "France", "tier": 1},
    {"code": "E2", "name": "League One", "country": "England", "tier": 3},
    {"code": "E3", "name": "League Two", "country": "England", "tier": 4},
    {"code": "N1", "name": "Eredivisie", "country": "Netherlands", "tier": 1},
    {"code": "P1", "name": "Primeira Liga", "country": "Portugal", "tier": 1},
]
```

### ✅ **Optional: Add Auto-Creation**

Add league auto-creation in `ingest_csv()`:

```python
# Get or create league
league = self.db.query(League).filter(
    League.code == league_code
).first()

if not league:
    # Auto-create league if it doesn't exist
    league = League(
        code=league_code,
        name=f"League {league_code}",  # Default name
        country="Unknown",
        tier=1,
        is_active=True
    )
    self.db.add(league)
    self.db.flush()
    logger.warning(f"Auto-created league: {league_code}")
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Is SQL schema list complete?** | ❌ **NO** - Only 5 leagues, frontend shows 10 |
| **Are leagues updated during download?** | ❌ **NO** - Leagues must exist before download |
| **Are leagues created during download?** | ❌ **NO** - Download fails if league doesn't exist |
| **What happens if league missing?** | ❌ **Download fails** with `ValueError: League not found` |

**Action Required:** Update SQL schema to include all 10 leagues shown in frontend.

