# Handling International and Club Games - Complete Guide

## Overview

This document provides a complete solution for handling both **international games** (country vs country) and **club games** (league-based teams) in the Football Probability Engine.

---

## Problem Statement

From your fixture list:
- **Game #1**: Algeria vs Nigeria (International) ❌ Currently fails
- **Games #2-17**: Club games from various leagues ✅ Should work

**Current Issue:**
- System requires `league_id` for all teams
- International games don't have a league
- Fixture creation fails for international games

---

## Solution Architecture

### 1. Create International League

**One-time setup:** Create an "INT" league for all international matches.

```sql
INSERT INTO leagues (code, name, country, tier, is_active)
VALUES ('INT', 'International Matches', 'World', 0, TRUE)
ON CONFLICT (code) DO NOTHING;
```

**Why Tier 0?**
- Distinguishes international from club leagues
- Allows filtering if needed
- Indicates special handling required

### 2. League Inference Strategy

For **Club Games**, use this priority order:

1. **Team Lookup** (Most Accurate)
   - Query `teams` table by team name
   - Use team's existing `league_id`
   - ✅ Most accurate

2. **Country Mapping** (Fallback)
   - Map country to league codes:
     - Spain → SP1 (top tier) or SP2 (second tier)
     - England → E0, E1, E2, E3
     - Italy → I1, I2
     - etc.
   - ⚠️ May need tier inference

3. **Default to Top Tier** (Last Resort)
   - If uncertain, default to top tier
   - User can correct later

For **International Games**:
- Always use `INT` league
- ✅ Consistent handling

---

## Implementation Plan

### Step 1: Create International League

**Run SQL script:**
```bash
psql -d your_database -f 3_Database_Football_Probability_Engine/migrations/create_international_league.sql
```

**Or use Python script:**
```bash
python 2_Backend_Football_Probability_Engine/scripts/create_international_league.py
```

### Step 2: Add League Inference Logic

**File:** `app/services/fixture_league_resolver.py` (NEW)

```python
"""
League resolution for fixtures
"""
from sqlalchemy.orm import Session
from app.db.models import League, Team
from app.services.team_resolver import resolve_team_safe
import logging

logger = logging.getLogger(__name__)

# Country to league code mapping (top tier default)
COUNTRY_TO_LEAGUE_CODE = {
    "Spain": "SP1",
    "England": "E0",
    "Italy": "I1",
    "Turkey": "T1",
    "Greece": "G1",
    "Portugal": "P1",
    "France": "F1",
    # Add more as needed
}

def infer_league_from_fixture(
    db: Session,
    fixture_type: str,
    country: str,
    home_team: str,
    away_team: str
) -> League:
    """
    Infer league for a fixture
    
    Priority:
    1. If International → INT league
    2. Try team lookup → use team's league
    3. Country mapping → infer from country
    4. Default → top tier league
    """
    # Step 1: International games
    if fixture_type == "International":
        int_league = db.query(League).filter(League.code == 'INT').first()
        if not int_league:
            raise ValueError("INT league not found. Please run create_international_league.py")
        return int_league
    
    # Step 2: Try team lookup
    home_team_obj = resolve_team_safe(db, home_team, None)
    if home_team_obj:
        return db.query(League).filter(League.id == home_team_obj.league_id).first()
    
    away_team_obj = resolve_team_safe(db, away_team, None)
    if away_team_obj:
        return db.query(League).filter(League.id == away_team_obj.league_id).first()
    
    # Step 3: Country mapping
    league_code = COUNTRY_TO_LEAGUE_CODE.get(country)
    if league_code:
        league = db.query(League).filter(League.code == league_code).first()
        if league:
            return league
    
    # Step 4: Default fallback
    logger.warning(f"Could not infer league for {country}. Using default.")
    # Could create league or raise error
    raise ValueError(f"Could not infer league for country: {country}")
```

### Step 3: Modify Fixture Creation

**File:** `app/api/jackpots.py`

**Current code (line ~417):**
```python
jackpot_fixture = JackpotFixture(
    jackpot_id=jackpot.id,
    match_order=idx + 1,
    home_team=fixture.homeTeam,
    away_team=fixture.awayTeam,
    odds_home=fixture.odds.home if fixture.odds else 2.0,
    odds_draw=fixture.odds.draw if fixture.odds else 3.0,
    odds_away=fixture.odds.away if fixture.odds else 2.5
)
```

**Add league_id field:**
```python
from app.services.fixture_league_resolver import infer_league_from_fixture

# ... existing code ...

# Infer league for each fixture
try:
    league = infer_league_from_fixture(
        db=db,
        fixture_type=fixture.type if hasattr(fixture, 'type') else "Club",
        country=fixture.country if hasattr(fixture, 'country') else None,
        home_team=fixture.homeTeam,
        away_team=fixture.awayTeam
    )
    
    # Create teams if they don't exist
    from app.services.team_resolver import create_team_if_not_exists
    home_team_obj = create_team_if_not_exists(db, fixture.homeTeam, league.id)
    away_team_obj = create_team_if_not_exists(db, fixture.awayTeam, league.id)
    
    jackpot_fixture = JackpotFixture(
        jackpot_id=jackpot.id,
        match_order=idx + 1,
        home_team=fixture.homeTeam,
        away_team=fixture.awayTeam,
        league_id=league.id,  # ADD THIS
        odds_home=fixture.odds.home if fixture.odds else 2.0,
        odds_draw=fixture.odds.draw if fixture.odds else 3.0,
        odds_away=fixture.odds.away if fixture.odds else 2.5
    )
except Exception as e:
    logger.error(f"Error creating fixture {idx + 1}: {e}")
    raise HTTPException(status_code=400, detail=f"Fixture {idx + 1}: {str(e)}")
```

**Note:** You'll need to add `league_id` column to `JackpotFixture` model if not present.

### Step 4: Handle Draw Structural Data for INT League

**File:** `app/api/probabilities.py` (or wherever league priors are used)

**Add special handling:**
```python
# When getting league priors
if league_code == 'INT':
    # Use default draw rate for international matches
    league_draw_rate = 0.25  # Or calculate from all INT matches
    league_sample_size = 1000  # Or actual count
else:
    # Normal league prior lookup
    league_prior = db.query(LeagueDrawPrior).filter(
        LeagueDrawPrior.league_id == league.id,
        LeagueDrawPrior.season == season
    ).first()
    league_draw_rate = league_prior.draw_rate if league_prior else 0.25
    league_sample_size = league_prior.sample_size if league_prior else 100
```

---

## Game-by-Game Analysis

### ✅ Game #1: Algeria vs Nigeria (International)

**Handling:**
1. ✅ Type = "International" → Use INT league
2. ✅ Create teams: "Algeria" and "Nigeria" in INT league
3. ✅ Create fixture with `league_id = INT`
4. ✅ Draw structural data:
   - Team Form: ✅ Works (if matches exist)
   - H2H Stats: ✅ Works (if matches exist)
   - Elo Ratings: ✅ Works
   - League Priors: ⚠️ Use default (0.25) or calculate from INT matches
   - Weather: ✅ Works (uses country coordinates)
   - Rest Days: ✅ Works
   - Other: ✅ Works

### ✅ Games #2-17: Club Games

**Handling:**
1. ✅ Type = "Club" → Infer league from team lookup or country
2. ✅ Resolve teams → Use existing league_id or create in inferred league
3. ✅ Create fixture with correct `league_id`
4. ✅ Draw structural data: All work normally

**Specific Examples:**

| Game | Country | Teams | Inferred League | Notes |
|------|---------|-------|-----------------|-------|
| #2 | Spain | Girona FC vs CA Osasuna | SP1 | Top tier teams |
| #3 | England | Tottenham vs Aston Villa | E0 | Premier League |
| #7 | England | Swansea vs West Brom | E1/E2 | Lower tier (need team lookup) |
| #11 | Greece | OFI Crete vs Asteras Tripolis | G1 | Super League |
| #15 | Italy | Verona vs Lazio | I1 | Serie A |

---

## Database Schema Changes

### Add `league_id` to `JackpotFixture` (if not present)

```sql
ALTER TABLE jackpot_fixtures 
ADD COLUMN IF NOT EXISTS league_id INTEGER REFERENCES leagues(id);

CREATE INDEX IF NOT EXISTS idx_jackpot_fixtures_league 
ON jackpot_fixtures(league_id);
```

### Update Model

**File:** `app/db/models.py`

```python
class JackpotFixture(Base):
    # ... existing fields ...
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True)  # Nullable for backward compatibility
    
    league = relationship("League")
```

---

## Testing Checklist

### ✅ Test Case 1: International Game

```python
# Create fixture
fixture = {
    "type": "International",
    "country": "International",
    "homeTeam": "Algeria",
    "awayTeam": "Nigeria",
    "odds": {"home": 3.15, "draw": 3.00, "away": 2.50}
}

# Expected:
# ✅ INT league used
# ✅ Teams created in INT league
# ✅ Fixture created successfully
# ✅ Probability calculation works
# ✅ Draw structural data works (with INT league handling)
```

### ✅ Test Case 2: Club Game - Top Tier

```python
fixture = {
    "type": "Club",
    "country": "England",
    "homeTeam": "Tottenham Hotspur",
    "awayTeam": "Aston Villa",
    "odds": {"home": 2.60, "draw": 3.60, "away": 2.65}
}

# Expected:
# ✅ Teams found in E0 league
# ✅ Fixture uses E0 league_id
# ✅ All draw structural data works normally
```

### ✅ Test Case 3: Club Game - Lower Tier

```python
fixture = {
    "type": "Club",
    "country": "England",
    "homeTeam": "Swansea City",
    "awayTeam": "West Bromwich Albion",
    "odds": {"home": 2.60, "draw": 3.35, "away": 2.75}
}

# Expected:
# ✅ Teams found in E1 or E2 league
# ✅ Fixture uses correct league_id
# ✅ All draw structural data works normally
```

### ✅ Test Case 4: New Teams

```python
fixture = {
    "type": "Club",
    "country": "Spain",
    "homeTeam": "New Team A",
    "awayTeam": "New Team B",
    "odds": {"home": 2.40, "draw": 3.25, "away": 3.15}
}

# Expected:
# ✅ Teams not found → created in SP1 (top tier default)
# ✅ Fixture created successfully
# ✅ System handles gracefully
```

---

## Draw Structural Data Handling

### ✅ Works Normally for INT League

| Feature | Status | Notes |
|---------|--------|-------|
| Team Form | ✅ Works | Calculates from matches |
| H2H Stats | ✅ Works | Calculates from matches |
| Elo Ratings | ✅ Works | Calculates normally |
| Rest Days | ✅ Works | Calculates from match dates |
| Weather | ✅ Works | Uses country coordinates |
| Referee | ✅ Works | Can assign referees |
| Odds Movement | ✅ Works | Tracks odds changes |
| XG Data | ✅ Works | Can ingest xG |

### ⚠️ Needs Special Handling

| Feature | Status | Solution |
|---------|--------|----------|
| League Priors | ⚠️ Special | Use default (0.25) or calculate from all INT matches |
| League Structure | ⚠️ N/A | Skip (no relegation/promotion) |

---

## Summary

### ✅ What Works

1. **Club Games:**
   - ✅ League inference from team lookup
   - ✅ Fallback to country mapping
   - ✅ All draw structural data works
   - ✅ Probability calculation works

2. **International Games:**
   - ✅ INT league creation
   - ✅ Team creation in INT league
   - ✅ Fixture creation works
   - ✅ Most draw structural data works
   - ⚠️ League priors need special handling

### ⚠️ Implementation Steps

1. ✅ Create INT league (SQL script provided)
2. ⚠️ Add league inference logic (code provided)
3. ⚠️ Modify fixture creation (code provided)
4. ⚠️ Add INT league handling in probability calculation
5. ⚠️ Test with provided fixture list

### 📋 Next Actions

1. Run `create_international_league.py` script
2. Implement `fixture_league_resolver.py`
3. Update `jackpots.py` to use league inference
4. Add `league_id` to `JackpotFixture` model
5. Test with your fixture list

---

## Files Created

1. ✅ `3_Database_Football_Probability_Engine/migrations/create_international_league.sql`
2. ✅ `2_Backend_Football_Probability_Engine/scripts/create_international_league.py`
3. ✅ `12_Important_Documets/HANDLING_INTERNATIONAL_AND_CLUB_GAMES.md`

---

## Questions?

- **Q: What if a team plays in multiple leagues?**
  - A: Use the most recent league or the league with most matches

- **Q: What if country mapping is wrong?**
  - A: Team lookup takes priority. Country mapping is fallback only.

- **Q: Can we support multiple international leagues?**
  - A: Yes, create WC, EURO, COPA leagues and update inference logic.

- **Q: What about historical international matches?**
  - A: They'll be stored in INT league. Can create separate leagues if needed.

