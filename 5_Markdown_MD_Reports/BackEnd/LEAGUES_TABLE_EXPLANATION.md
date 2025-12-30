# Leagues Table - What is Saved

## Overview

The `leagues` table stores **reference data** about football leagues. It does NOT store match data - that goes in the `matches` table. The `leagues` table is used to:

1. **Reference leagues** when ingesting match data
2. **Store league-specific parameters** for model training
3. **Track league metadata** (country, tier, etc.)

---

## Table Schema

```sql
CREATE TABLE leagues (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR NOT NULL UNIQUE,           -- 'E0', 'SP1', etc.
    name            VARCHAR NOT NULL,                   -- 'Premier League'
    country         VARCHAR NOT NULL,                   -- 'England'
    tier            INTEGER DEFAULT 1,                  -- League tier (1 = top tier)
    avg_draw_rate   DOUBLE PRECISION DEFAULT 0.26,     -- Historical average draw rate
    home_advantage  DOUBLE PRECISION DEFAULT 0.35,      -- League-specific home advantage
    is_active       BOOLEAN DEFAULT TRUE,               -- Whether league is currently active
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## What Each Column Stores

### `id` (SERIAL PRIMARY KEY)
- **Purpose:** Unique identifier for each league
- **Example:** `1`, `2`, `3`
- **Auto-generated:** Yes, PostgreSQL auto-increment

### `code` (VARCHAR, UNIQUE)
- **Purpose:** Short code used to identify league in data sources
- **Format:** Usually 2 characters (e.g., 'E0', 'SP1', 'D1')
- **Examples:**
  - `'E0'` = Premier League (England)
  - `'SP1'` = La Liga (Spain)
  - `'D1'` = Bundesliga (Germany)
  - `'I1'` = Serie A (Italy)
  - `'F1'` = Ligue 1 (France)
- **Important:** Must match codes used by football-data.co.uk

### `name` (VARCHAR)
- **Purpose:** Full display name of the league
- **Examples:**
  - `'Premier League'`
  - `'La Liga'`
  - `'Bundesliga'`
  - `'Serie A'`
  - `'Ligue 1'`

### `country` (VARCHAR)
- **Purpose:** Country where the league is based
- **Examples:**
  - `'England'`
  - `'Spain'`
  - `'Germany'`
  - `'Italy'`
  - `'France'`

### `tier` (INTEGER, DEFAULT 1)
- **Purpose:** League tier/level (1 = top tier, 2 = second tier, etc.)
- **Examples:**
  - `1` = Premier League (top tier)
  - `2` = Championship (second tier)
  - `3` = League One (third tier)

### `avg_draw_rate` (DOUBLE PRECISION, DEFAULT 0.26)
- **Purpose:** Historical average draw rate for the league
- **Range:** 0.0 to 1.0 (percentage as decimal)
- **Example:** `0.26` = 26% of matches end in draws
- **Usage:** Used in model calibration and probability calculations

### `home_advantage` (DOUBLE PRECISION, DEFAULT 0.35)
- **Purpose:** League-specific home advantage factor
- **Range:** Typically 0.20 to 0.50 (goals advantage)
- **Example:** `0.35` = Home teams score ~0.35 more goals on average
- **Usage:** Used in Dixon-Coles model for probability calculations

### `is_active` (BOOLEAN, DEFAULT TRUE)
- **Purpose:** Whether the league is currently active/available
- **Values:** `TRUE` or `FALSE`
- **Usage:** Filter active leagues for data ingestion and predictions

### `created_at` (TIMESTAMPTZ)
- **Purpose:** When the league record was created
- **Format:** PostgreSQL timestamp with timezone
- **Example:** `2024-01-15 10:30:00+00`

### `updated_at` (TIMESTAMPTZ)
- **Purpose:** When the league record was last updated
- **Format:** PostgreSQL timestamp with timezone
- **Auto-updated:** Yes, via database trigger

---

## Default Leagues (From SQL Schema)

The database schema includes seed data for major leagues:

```sql
INSERT INTO leagues (code, name, country, home_advantage) VALUES
    ('E0', 'Premier League', 'England', 0.35),
    ('SP1', 'La Liga', 'Spain', 0.30),
    ('D1', 'Bundesliga', 'Germany', 0.32),
    ('I1', 'Serie A', 'Italy', 0.28),
    ('F1', 'Ligue 1', 'France', 0.33)
ON CONFLICT (code) DO NOTHING;
```

**Note:** These use football-data.co.uk codes (`E0`, `SP1`, etc.)

---

## Default Leagues (From Python Code)

The `create_default_leagues()` function creates leagues with different codes:

```python
default_leagues = [
    {"code": "EPL", "name": "Premier League", "country": "England", "tier": 1},
    {"code": "LaLiga", "name": "La Liga", "country": "Spain", "tier": 1},
    {"code": "Bundesliga", "name": "Bundesliga", "country": "Germany", "tier": 1},
    {"code": "SerieA", "name": "Serie A", "country": "Italy", "tier": 1},
    {"code": "Ligue1", "name": "Ligue 1", "country": "France", "tier": 1},
    {"code": "Eredivisie", "name": "Eredivisie", "country": "Netherlands", "tier": 1},
]
```

**⚠️ IMPORTANT:** There's a mismatch between:
- **SQL seed data:** Uses `'E0'`, `'SP1'`, `'D1'` (football-data.co.uk codes)
- **Python function:** Uses `'EPL'`, `'LaLiga'`, `'Bundesliga'` (display names)

**Recommendation:** Use football-data.co.uk codes (`E0`, `SP1`, etc.) to match data source.

---

## How Leagues Are Used

### 1. **Data Ingestion**
When ingesting match data, the system:
- Looks up league by `code` (e.g., `'E0'`)
- Links matches to league via `league_id` foreign key
- Uses league parameters for validation

```python
# In data_ingestion.py
league = self.db.query(League).filter(
    League.code == league_code  # e.g., 'E0'
).first()
```

### 2. **Model Training**
League-specific parameters are used:
- `home_advantage`: Adjusts probability calculations
- `avg_draw_rate`: Calibrates draw predictions
- `tier`: May affect model weights

### 3. **Team Resolution**
When resolving team names, the system:
- Uses `league_id` to scope team searches
- Ensures teams belong to correct league

---

## League Codes Reference

### Football-Data.co.uk Codes (Recommended)

| Code | League Name | Country |
|------|-------------|---------|
| `E0` | Premier League | England |
| `E1` | Championship | England |
| `E2` | League One | England |
| `E3` | League Two | England |
| `SP1` | La Liga | Spain |
| `SP2` | La Liga 2 | Spain |
| `D1` | Bundesliga | Germany |
| `D2` | 2. Bundesliga | Germany |
| `I1` | Serie A | Italy |
| `I2` | Serie B | Italy |
| `F1` | Ligue 1 | France |
| `F2` | Ligue 2 | France |
| `N1` | Eredivisie | Netherlands |
| `P1` | Primeira Liga | Portugal |

---

## Example League Records

```sql
-- Example 1: Premier League
id: 1
code: 'E0'
name: 'Premier League'
country: 'England'
tier: 1
avg_draw_rate: 0.26
home_advantage: 0.35
is_active: true

-- Example 2: La Liga
id: 2
code: 'SP1'
name: 'La Liga'
country: 'Spain'
tier: 1
avg_draw_rate: 0.25
home_advantage: 0.30
is_active: true

-- Example 3: Championship (Second Tier)
id: 3
code: 'E1'
name: 'Championship'
country: 'England'
tier: 2
avg_draw_rate: 0.28
home_advantage: 0.32
is_active: true
```

---

## Important Notes

1. **League codes must match data source:** Use football-data.co.uk codes (`E0`, `SP1`, etc.) for data ingestion to work correctly.

2. **Leagues are reference data:** They don't store match results - those go in the `matches` table.

3. **League parameters affect model:** `home_advantage` and `avg_draw_rate` are used in probability calculations.

4. **Code mismatch issue:** The Python `create_default_leagues()` function uses different codes than the SQL seed data. Consider updating Python function to use football-data.co.uk codes.

5. **Leagues must exist before ingestion:** Match data ingestion will fail if the league doesn't exist in the `leagues` table.

---

## Query Examples

### Get all active leagues
```sql
SELECT code, name, country, tier 
FROM leagues 
WHERE is_active = TRUE 
ORDER BY country, tier;
```

### Get league by code
```sql
SELECT * FROM leagues WHERE code = 'E0';
```

### Update league parameters
```sql
UPDATE leagues 
SET avg_draw_rate = 0.27, home_advantage = 0.36 
WHERE code = 'E0';
```

### Get leagues with most matches
```sql
SELECT l.code, l.name, COUNT(m.id) as match_count
FROM leagues l
LEFT JOIN matches m ON m.league_id = l.id
GROUP BY l.id, l.code, l.name
ORDER BY match_count DESC;
```

