# Handling Missing Teams Guide

## 🔴 Problem: Teams Showing Red Exclamation Marks

When teams appear with **red exclamation marks** in the UI, it means they're not found in the database. This prevents:
- Probability calculations
- Match predictions
- Team strength lookups

---

## ✅ Solutions

### **Option 1: Quick Fix - Add Teams via Script (Recommended)**

Use the existing script to add missing teams:

```bash
cd 2_Backend_Football_Probability_Engine
python scripts/add_missing_teams.py
```

**To add specific teams**, edit `scripts/add_missing_teams.py` and add them to the `MISSING_TEAMS` list:

```python
MISSING_TEAMS = [
    # Add your missing teams here
    ("Auckland FC", "A-League", "Australia"),
    ("Vanspor BB", "Super Lig", "Turkey"),
    ("Hawassa Kenema SC", "Ethiopian Premier League", "Ethiopia"),
    ("Saint George FC", "Ethiopian Premier League", "Ethiopia"),
    # ... etc
]
```

**Dry run first** to see what would be added:
```bash
python scripts/add_missing_teams.py --dry-run
```

---

### **Option 2: Add Teams Programmatically**

Create a Python script to add teams:

```python
from app.db.session import SessionLocal
from app.db.models import Team, League
from app.services.team_resolver import create_team_if_not_exists

db = SessionLocal()

# Find league by code or name
league = db.query(League).filter(League.code == "AUS1").first()  # A-League
# OR
league = db.query(League).filter(League.name.ilike("%A-League%")).first()

# Add team
team = create_team_if_not_exists(
    db=db,
    team_name="Auckland FC",
    league_id=league.id
)

db.commit()
db.close()
```

---

### **Option 3: Add Teams via CSV Import**

If you have a CSV file with teams:

```bash
cd 2_Backend_Football_Probability_Engine
python scripts/create_teams_from_csv.py --csv path/to/teams.csv
```

**CSV format:**
```csv
league_code,team_name
AUS1,Auckland FC
T1,Vanspor BB
T1,Boluspor
```

---

### **Option 4: Add Teams via SQL (Direct Database)**

If you know the league ID:

```sql
-- Find league ID first
SELECT id, code, name FROM leagues WHERE code = 'AUS1';

-- Add team (replace league_id with actual ID)
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
VALUES (
    123,  -- Replace with actual league_id
    'Auckland FC',
    'auckland fc',  -- Normalized (lowercase, no special chars)
    1.0,
    1.0,
    0.0
)
ON CONFLICT DO NOTHING;
```

---

## 🔍 Finding Missing Teams

### **Check Which Teams Are Missing**

1. **Via Frontend**: Teams with red exclamation marks are missing
2. **Via API**: Check validation endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/validation/team \
     -H "Content-Type: application/json" \
     -d '{"teamName": "Auckland FC"}'
   ```
3. **Via Database Query**:
   ```sql
   -- Find teams that might match (fuzzy search)
   SELECT name, canonical_name, league_id 
   FROM teams 
   WHERE canonical_name LIKE '%auckland%';
   ```

---

## 📋 Team Name Normalization Rules

Teams are matched using **canonical names**. The normalization process:

1. **Converts to lowercase**: "Auckland FC" → "auckland fc"
2. **Removes common suffixes**: "FC", "CF", "BC", "AC", "United", "City", etc.
3. **Removes special characters**: Only keeps letters, numbers, spaces, hyphens
4. **Normalizes whitespace**: Multiple spaces → single space

**Examples:**
- "Auckland FC" → canonical: "auckland"
- "Manchester United" → canonical: "manchester"
- "Real Madrid CF" → canonical: "real madrid"

---

## ⚠️ Important Notes

### **1. League Must Exist First**
Teams require a valid `league_id`. If the league doesn't exist, create it first:

```python
from app.db.models import League

league = League(
    code="AUS1",
    name="A-League",
    country="Australia",
    tier=1,
    avg_draw_rate=0.23,
    home_advantage=0.26,
    is_active=True
)
db.add(league)
db.commit()
```

### **2. Team Names Must Be Unique Per League**
The database enforces uniqueness: `(canonical_name, league_id)`

### **3. Default Strengths**
New teams get default values:
- `attack_rating`: 1.0
- `defense_rating`: 1.0
- `home_bias`: 0.0

These will be updated when you train the model.

---

## 🚀 Quick Reference

### **Common Missing Teams by League**

**A-League (AUS1):**
- Auckland FC
- Brisbane Roar

**Turkish Super Lig (T1):**
- Vanspor BB
- Boluspor

**Ethiopian Premier League:**
- Hawassa Kenema SC
- Saint George FC

**German Bundesliga (D1):**
- Eintracht Frankfurt
- Borussia Dortmund

---

## 📝 Example: Adding Multiple Teams

```python
from app.db.session import SessionLocal
from app.db.models import League
from app.services.team_resolver import create_team_if_not_exists

db = SessionLocal()

# Teams to add: (team_name, league_code)
teams_to_add = [
    ("Auckland FC", "AUS1"),
    ("Vanspor BB", "T1"),
    ("Boluspor", "T1"),
    ("Hawassa Kenema SC", "ETH1"),  # Adjust league code as needed
    ("Saint George FC", "ETH1"),
]

for team_name, league_code in teams_to_add:
    # Find league
    league = db.query(League).filter(League.code == league_code).first()
    if not league:
        print(f"⚠ League {league_code} not found, skipping {team_name}")
        continue
    
    # Create team
    team = create_team_if_not_exists(db, team_name, league.id)
    print(f"✓ Added/Found: {team_name} (ID: {team.id})")

db.commit()
db.close()
```

---

## 🔧 Troubleshooting

### **Team Still Not Found After Adding**

1. **Check canonical name**: Ensure normalization matches
   ```python
   from app.services.team_resolver import normalize_team_name
   print(normalize_team_name("Auckland FC"))  # Should match DB canonical_name
   ```

2. **Check league ID**: Team must be in correct league
   ```sql
   SELECT t.name, t.canonical_name, l.code, l.name 
   FROM teams t 
   JOIN leagues l ON l.id = t.league_id 
   WHERE t.canonical_name LIKE '%auckland%';
   ```

3. **Check similarity threshold**: Fuzzy matching requires ≥70% similarity
   - If team name is very different, add it manually
   - Or add to `TEAM_ALIASES` in `team_resolver.py`

### **Team Exists But Still Shows Red**

1. **Clear browser cache**
2. **Refresh the page**
3. **Check API response**: Verify team validation endpoint returns `isValid: true`

---

## 📚 Related Files

- **Script**: `2_Backend_Football_Probability_Engine/scripts/add_missing_teams.py`
- **Team Resolver**: `2_Backend_Football_Probability_Engine/app/services/team_resolver.py`
- **API Endpoint**: `2_Backend_Football_Probability_Engine/app/api/validation_team.py`
- **Database Model**: `2_Backend_Football_Probability_Engine/app/db/models.py` (Team class)

---

## 💡 Best Practices

1. **Add teams before creating jackpots** - Prevents validation errors
2. **Use canonical names** - Consistent naming improves matching
3. **Verify league exists** - Teams require valid league_id
4. **Test with dry-run** - Always test before committing changes
5. **Keep team aliases updated** - Add common variations to `TEAM_ALIASES` in `team_resolver.py`

