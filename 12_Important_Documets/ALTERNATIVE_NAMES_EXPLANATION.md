# Teams Table: alternative_names Column Explanation

## 📋 Purpose

The `alternative_names` column in the `teams` table is a **TEXT[] array** (PostgreSQL array type) that stores alternative/variant names for each team. This column is designed to improve team name matching across different data sources.

---

## 🎯 Why It Exists

### **Problem: Team Name Variations**

Different data sources use different team name formats:

| Source | Team Name Variant |
|--------|------------------|
| Football-Data.co.uk | "Man United" |
| API Provider | "Manchester United" |
| Historical Data | "Man Utd" |
| User Input | "Man United FC" |

Without `alternative_names`, the system might:
- Create duplicate team records
- Fail to match teams correctly
- Miss historical data connections

### **Solution: Alternative Names Array**

The `alternative_names` column stores all known variations of a team's name, allowing the system to:
- ✅ Match teams across different data sources
- ✅ Prevent duplicate team creation
- ✅ Improve team resolution accuracy
- ✅ Support fuzzy matching algorithms

---

## 📊 Database Schema

```sql
ALTER TABLE teams
ADD COLUMN IF NOT EXISTS alternative_names TEXT[];

COMMENT ON COLUMN teams.alternative_names IS 'Array of alternative team names for matching';

-- Create GIN index for fast array searches
CREATE INDEX IF NOT EXISTS idx_teams_alternative_names 
ON teams USING GIN(alternative_names);
```

**Column Type:** `TEXT[]` (PostgreSQL array of text)

**Index:** GIN (Generalized Inverted Index) for fast array containment searches

---

## 🔍 How It Works

### **Example Data:**

```sql
-- Team record
id: 1
name: "Manchester United"
canonical_name: "manchester united"
alternative_names: ARRAY['Man United', 'Man Utd', 'Manchester United FC', 'Man U', 'MUFC']
```

### **Query Examples:**

```sql
-- Find team by alternative name
SELECT * FROM teams 
WHERE 'Man United' = ANY(alternative_names);

-- Find team by any name (name, canonical_name, or alternative_names)
SELECT * FROM teams 
WHERE name = 'Manchester United'
   OR canonical_name = 'manchester united'
   OR 'Man United' = ANY(alternative_names);
```

---

## 🛠️ Current Implementation Status

### **❌ NOT Currently Populated**

**Current State:**
- Column exists in database schema
- Index is created
- **No automatic population logic exists**
- Values are `NULL` for all teams

**Location of Schema:**
- `15_Football_Data_/02_Db populating_Script/schema_enhancements.sql` (lines 80-87)

---

## 💡 Recommended Implementation

### **Option 1: Extract from Match Data** (Recommended)

During database population, extract all unique team name variations from match data:

```python
def populate_team_alternative_names(self):
    """Extract and populate alternative names from match data"""
    logger.info("Populating team alternative names...")
    
    # Get all unique team name variations from matches
    self.cur.execute("""
        WITH team_variations AS (
            SELECT DISTINCT
                t.id as team_id,
                t.canonical_name,
                m.home_team as team_name
            FROM matches m
            JOIN teams t ON t.id = m.home_team_id
            WHERE m.home_team IS NOT NULL
            
            UNION
            
            SELECT DISTINCT
                t.id as team_id,
                t.canonical_name,
                m.away_team as team_name
            FROM matches m
            JOIN teams t ON t.id = m.away_team_id
            WHERE m.away_team IS NOT NULL
        )
        UPDATE teams t
        SET alternative_names = (
            SELECT ARRAY_AGG(DISTINCT tv.team_name)
            FROM team_variations tv
            WHERE tv.team_id = t.id
                AND tv.team_name != t.name
                AND tv.team_name != t.canonical_name
        )
        WHERE EXISTS (
            SELECT 1 FROM team_variations tv WHERE tv.team_id = t.id
        )
    """)
    
    self.conn.commit()
    logger.info("Team alternative names populated")
```

### **Option 2: Manual Configuration**

Create a configuration file with known team name variations:

```json
{
  "manchester united": [
    "Man United",
    "Man Utd",
    "Manchester United FC",
    "Man U",
    "MUFC"
  ],
  "liverpool": [
    "Liverpool FC",
    "LFC",
    "The Reds"
  ]
}
```

### **Option 3: Use Team Resolver Service**

Enhance the existing `team_resolver.py` to:
1. Detect name variations during team resolution
2. Automatically add to `alternative_names` when found
3. Use for future matching

---

## 🔧 Usage in Team Resolution

### **Current Team Resolution** (`app/services/team_resolver.py`)

The team resolver currently uses:
- `canonical_name` (normalized)
- `name` (display name)

**Enhancement:** Add `alternative_names` to the search:

```python
def resolve_team_with_alternatives(
    db: Session,
    team_name: str,
    league_id: Optional[int] = None
) -> Optional[Team]:
    """Resolve team using name, canonical_name, or alternative_names"""
    
    # Normalize input
    canonical_input = normalize_team_name(team_name)
    
    # Build query
    query = db.query(Team)
    
    if league_id:
        query = query.filter(Team.league_id == league_id)
    
    # Search in name, canonical_name, or alternative_names
    teams = query.filter(
        or_(
            Team.name.ilike(f"%{team_name}%"),
            Team.canonical_name == canonical_input,
            Team.alternative_names.contains([team_name]),
            Team.alternative_names.contains([canonical_input])
        )
    ).all()
    
    # Return best match
    if teams:
        return teams[0]
    
    return None
```

---

## 📈 Benefits

1. **Improved Matching:** Better team name resolution across data sources
2. **Reduced Duplicates:** Prevents creating duplicate team records
3. **Data Quality:** Maintains consistency across different data feeds
4. **User Experience:** Handles various input formats from users
5. **Historical Data:** Links historical matches with different naming conventions

---

## 🚀 Next Steps

1. **Implement Population Logic:**
   - Add to `populate_database.py` after teams are populated
   - Extract variations from match data
   - Store in `alternative_names` array

2. **Enhance Team Resolver:**
   - Update `team_resolver.py` to use `alternative_names`
   - Add fuzzy matching with alternative names

3. **Add Maintenance Endpoint:**
   - Create API endpoint to refresh alternative names
   - Allow manual addition of known variations

4. **Documentation:**
   - Document known team name variations
   - Create mapping file for common leagues

---

## 📚 Related Files

- **Schema Enhancement**: `15_Football_Data_/02_Db populating_Script/schema_enhancements.sql` (lines 80-87)
- **Team Resolver**: `2_Backend_Football_Probability_Engine/app/services/team_resolver.py`
- **Database Population**: `15_Football_Data_/02_Db populating_Script/populate_database.py`
- **Team Model**: `2_Backend_Football_Probability_Engine/app/db/models.py` (Team class)

---

## ⚠️ Important Notes

1. **Array Type:** PostgreSQL arrays require special handling in queries
2. **Index Performance:** GIN index enables fast searches but adds write overhead
3. **Data Quality:** Alternative names should be normalized/canonicalized
4. **Maintenance:** Regular updates needed as new data sources are added
5. **Case Sensitivity:** Consider case-insensitive matching in queries

---

## ✅ Summary

**Purpose:** Store team name variations for improved matching across data sources

**Status:** Column exists but is NOT currently populated

**Priority:** MEDIUM - Improves data quality and matching accuracy

**Recommendation:** Implement Option 1 (extract from match data) as part of database population process

