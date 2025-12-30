# Add Missing Teams Guide

## Problem
The logs show 9 teams are not found in the database, causing them to use default strengths (1.0, 1.0):
- Norrkoping FK
- IK Sirius
- Excelsior Rotterdam
- Heracles Almelo
- Celta Vigo
- SK Rapid
- SK Sturm Graz
- FK Krasnodar
- FK Spartak Moscow

## Solution Options

### Option 1: Run SQL Script (Recommended)
The easiest way is to run the SQL migration script directly:

```sql
-- Run this in your PostgreSQL database
\i "3_Database_Football_Probability_Engine/migrations/add_missing_teams.sql"
```

Or copy and paste the contents of `add_missing_teams.sql` into your PostgreSQL client.

### Option 2: Use Python Script (Requires DB Credentials)
If you have database credentials set up in your `.env` file:

```bash
cd "2_Backend_Football_Probability_Engine"
python scripts/add_missing_teams.py --dry-run  # Preview
python scripts/add_missing_teams.py             # Actually add
```

**Note**: The Python script requires database connection credentials. If you get connection errors, use Option 1 instead.

## What Gets Added

The script adds:
- **9 missing teams** that appear in your jackpots
- **8 leagues** (if they don't exist): Allsvenskan, Eredivisie, Eerste Divisie, La Liga, Austrian Bundesliga, Russian Premier League, Bundesliga, Premier League
- **Default ratings**: attack_rating=1.0, defense_rating=1.0 (will be updated when model is retrained)

## After Adding Teams

1. **Verify teams are added**:
   ```sql
   SELECT name, canonical_name, league_id 
   FROM teams 
   WHERE name IN ('Norrkoping FK', 'IK Sirius', 'Excelsior Rotterdam', 'Heracles Almelo', 'Celta Vigo', 'SK Rapid', 'SK Sturm Graz', 'FK Krasnodar', 'FK Spartak Moscow');
   ```

2. **Retrain the Poisson model** to calculate proper team strengths:
   - Use the training API or training service
   - This will update attack_rating and defense_rating for all teams

3. **Test probability calculation** - teams should now be found and use model strengths instead of defaults

## Expected Results

After adding teams and retraining:
- ✅ Teams will be found in probability calculations (no more "not found" warnings)
- ✅ Probabilities will be more varied (not uniform)
- ✅ Team strengths will be calculated from historical data

