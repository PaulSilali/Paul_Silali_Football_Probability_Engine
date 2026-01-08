# League Statistics Deep Scan: avg_draw_rate and home_advantage

## 🔍 Executive Summary

**CRITICAL FINDING:** The `leagues` table columns `avg_draw_rate` and `home_advantage` are **NOT being calculated** from match data in the backend. They remain at default values (0.26 and 0.35) or are manually set.

---

## 📊 Current State Analysis

### **1. Database Population Script** (`populate_database.py`)

**Location:** `15_Football_Data_/02_Db populating_Script/populate_database.py`

**Current Implementation (Lines 287-348):**

```python
def populate_leagues(self):
    """Populate leagues table from staging data"""
    # Only inserts/updates: code, name, country
    # DOES NOT calculate avg_draw_rate or home_advantage
    
    self.cur.execute("""
        INSERT INTO leagues (code, name, country, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            country = EXCLUDED.country,
            updated_at = now()
    """, (code, name, country))
```

**What's Missing:**
- ❌ No calculation of `avg_draw_rate` from match results
- ❌ No calculation of `home_advantage` from match results
- ❌ Values remain at database defaults (0.26 and 0.35)

---

### **2. Exported Data Analysis** (`leagues_202601081311.sql`)

**Total Leagues:** 88 leagues

**Issues Found:**

#### **Issue 1: Inconsistent Values**
Many leagues have different `avg_draw_rate` and `home_advantage` values, but these appear to be manually set or from an unknown source:

| League Code | Name | avg_draw_rate | home_advantage | Status |
|------------|------|---------------|----------------|--------|
| `E0` | Premier League | 0.26 | 0.35 | ✅ Default |
| `SP1` | La Liga | 0.25 | 0.30 | ⚠️ Different |
| `I1` | Serie A | 0.27 | 0.28 | ⚠️ Different |
| `D1` | Bundesliga | 0.24 | 0.32 | ⚠️ Different |
| `F1` | Ligue 1 | 0.26 | 0.33 | ⚠️ Different |
| `E1` | Championship | 0.27 | 0.33 | ⚠️ Different |
| `E2` | League One | 0.28 | 0.32 | ⚠️ Different |
| `E3` | League Two | 0.29 | 0.31 | ⚠️ Different |

#### **Issue 2: Unknown Leagues with Defaults**
Many leagues with code like `'FC'`, `'MA1'`, `'P2'`, `'N2'`, `'BC'`, etc. have:
- `name = code` (not properly mapped)
- `country = 'Unknown'`
- `avg_draw_rate = 0.26` (default)
- `home_advantage = 0.35` (default)

**Examples:**
```sql
('FC','FC','Unknown',1,0.26,0.35,...)
('MA1','MA1','Unknown',1,0.26,0.35,...)
('P2','P2','Unknown',1,0.26,0.35,...)
```

#### **Issue 3: Duplicate League Codes**
Some leagues appear multiple times with different names:

| Code | Name 1 | Name 2 | Issue |
|------|--------|--------|-------|
| `EPL` | Premier League | - | Should be `E0` |
| `LALIGA` | La Liga | - | Should be `SP1` |
| `BUNDESLIGA` | Bundesliga | - | Should be `D1` |
| `ALLSVENSKAN` | Allsvenskan | - | Duplicate of `SWE1` |

---

## 🔧 How These Values SHOULD Be Calculated

### **1. avg_draw_rate Calculation**

**Formula:**
```sql
avg_draw_rate = COUNT(CASE WHEN result = 'D' THEN 1 END) / COUNT(*)
```

**SQL Implementation:**
```sql
UPDATE leagues l
SET avg_draw_rate = (
    SELECT 
        AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END)::NUMERIC(5,4)
    FROM matches m
    WHERE m.league_id = l.id
        AND m.result IS NOT NULL
        AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'  -- Last 5 years
    GROUP BY m.league_id
)
WHERE EXISTS (
    SELECT 1 FROM matches m WHERE m.league_id = l.id
);
```

**Python Implementation:**
```python
def calculate_league_draw_rate(db: Session, league_id: int) -> float:
    """Calculate avg_draw_rate from match results"""
    from datetime import datetime, timedelta
    from app.db.models import Match, MatchResult
    
    # Get matches from last 5 years
    cutoff_date = datetime.now() - timedelta(days=5*365)
    
    matches = db.query(Match).filter(
        Match.league_id == league_id,
        Match.result.isnot(None),
        Match.match_date >= cutoff_date
    ).all()
    
    if not matches:
        return 0.26  # Default if no matches
    
    draws = sum(1 for m in matches if m.result == MatchResult.D)
    draw_rate = draws / len(matches)
    
    return float(draw_rate)
```

---

### **2. home_advantage Calculation**

**Formula:**
```sql
home_advantage = AVG(home_goals - away_goals)  -- Average goal difference for home teams
```

**SQL Implementation:**
```sql
UPDATE leagues l
SET home_advantage = (
    SELECT 
        AVG(m.home_goals - m.away_goals)::NUMERIC(5,4)
    FROM matches m
    WHERE m.league_id = l.id
        AND m.home_goals IS NOT NULL
        AND m.away_goals IS NOT NULL
        AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'  -- Last 5 years
    GROUP BY m.league_id
)
WHERE EXISTS (
    SELECT 1 FROM matches m WHERE m.league_id = l.id
);
```

**Python Implementation:**
```python
def calculate_league_home_advantage(db: Session, league_id: int) -> float:
    """Calculate home_advantage from match results"""
    from datetime import datetime, timedelta
    from app.db.models import Match
    
    # Get matches from last 5 years
    cutoff_date = datetime.now() - timedelta(days=5*365)
    
    matches = db.query(Match).filter(
        Match.league_id == league_id,
        Match.home_goals.isnot(None),
        Match.away_goals.isnot(None),
        Match.match_date >= cutoff_date
    ).all()
    
    if not matches:
        return 0.35  # Default if no matches
    
    goal_diffs = [
        m.home_goals - m.away_goals 
        for m in matches
    ]
    
    home_advantage = sum(goal_diffs) / len(goal_diffs)
    
    # Clamp to reasonable range [0.1, 0.6]
    return max(0.1, min(0.6, float(home_advantage)))
```

---

## 🚨 Problems Identified

### **Problem 1: No Automatic Calculation**

**Current Behavior:**
- `populate_leagues()` only sets `code`, `name`, `country`
- `avg_draw_rate` and `home_advantage` remain at defaults (0.26, 0.35)
- No backend service calculates these from match data

**Impact:**
- Model training uses incorrect league parameters
- Probability calculations are less accurate
- League-specific characteristics are ignored

---

### **Problem 2: Inconsistent Data in Database**

**From Exported SQL:**
- Some leagues have manually set values (SP1: 0.25/0.30, I1: 0.27/0.28)
- Many leagues have defaults (0.26/0.35)
- Unknown leagues have defaults but no match data

**Questions:**
- Where did the non-default values come from?
- Are they manually set?
- Are they from an old calculation that's no longer running?

---

### **Problem 3: No Update Mechanism**

**Missing:**
- No scheduled job to recalculate league statistics
- No trigger to update when new matches are added
- No API endpoint to refresh league statistics

---

## ✅ Recommended Solution

### **Option 1: Add to Database Population Script** (Recommended)

**Modify `populate_database.py`:**

```python
def populate_leagues(self):
    """Populate leagues table from staging data"""
    # ... existing code to insert/update leagues ...
    
    # NEW: Calculate and update league statistics
    self.update_league_statistics()

def update_league_statistics(self):
    """Calculate and update avg_draw_rate and home_advantage for all leagues"""
    logger.info("Calculating league statistics...")
    
    self.cur.execute("""
        UPDATE leagues l
        SET 
            avg_draw_rate = COALESCE((
                SELECT AVG(CASE WHEN m.result = 'D' THEN 1.0 ELSE 0.0 END)::NUMERIC(5,4)
                FROM matches m
                WHERE m.league_id = l.id
                    AND m.result IS NOT NULL
                    AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
                GROUP BY m.league_id
            ), 0.26),  -- Default if no matches
            
            home_advantage = COALESCE((
                SELECT AVG(m.home_goals - m.away_goals)::NUMERIC(5,4)
                FROM matches m
                WHERE m.league_id = l.id
                    AND m.home_goals IS NOT NULL
                    AND m.away_goals IS NOT NULL
                    AND m.match_date >= CURRENT_DATE - INTERVAL '5 years'
                GROUP BY m.league_id
            ), 0.35),  -- Default if no matches
            
            updated_at = now()
        WHERE EXISTS (
            SELECT 1 FROM matches m WHERE m.league_id = l.id
        )
    """)
    
    self.conn.commit()
    logger.info("League statistics updated")
```

---

### **Option 2: Create Separate Service** (Better for Production)

**Create `app/services/league_statistics.py`:**

```python
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models import League, Match, MatchResult
import logging

logger = logging.getLogger(__name__)

class LeagueStatisticsService:
    """Service for calculating and updating league statistics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def update_all_leagues(self):
        """Update statistics for all leagues"""
        leagues = self.db.query(League).all()
        
        for league in leagues:
            self.update_league(league.id)
        
        self.db.commit()
        logger.info(f"Updated statistics for {len(leagues)} leagues")
    
    def update_league(self, league_id: int):
        """Update statistics for a single league"""
        league = self.db.query(League).filter(League.id == league_id).first()
        if not league:
            return
        
        # Calculate from last 5 years of matches
        cutoff_date = datetime.now() - timedelta(days=5*365)
        
        matches = self.db.query(Match).filter(
            Match.league_id == league_id,
            Match.match_date >= cutoff_date
        ).all()
        
        if not matches:
            logger.debug(f"No matches found for league {league.code}, keeping defaults")
            return
        
        # Calculate avg_draw_rate
        draws = sum(1 for m in matches if m.result == MatchResult.D)
        league.avg_draw_rate = draws / len(matches) if matches else 0.26
        
        # Calculate home_advantage
        valid_matches = [
            m for m in matches 
            if m.home_goals is not None and m.away_goals is not None
        ]
        
        if valid_matches:
            goal_diffs = [m.home_goals - m.away_goals for m in valid_matches]
            home_advantage = sum(goal_diffs) / len(goal_diffs)
            # Clamp to reasonable range
            league.home_advantage = max(0.1, min(0.6, home_advantage))
        else:
            league.home_advantage = 0.35  # Default
        
        logger.debug(
            f"League {league.code}: "
            f"draw_rate={league.avg_draw_rate:.3f}, "
            f"home_advantage={league.home_advantage:.3f}"
        )
```

**Add to API endpoint:**

```python
# app/api/admin.py
@router.post("/admin/leagues/update-statistics")
def update_league_statistics(db: Session = Depends(get_db)):
    """Update league statistics from match data"""
    service = LeagueStatisticsService(db)
    service.update_all_leagues()
    return {"status": "success", "message": "League statistics updated"}
```

---

### **Option 3: Database Trigger** (Advanced)

**Create trigger to auto-update when matches are inserted:**

```sql
CREATE OR REPLACE FUNCTION update_league_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update avg_draw_rate
    UPDATE leagues
    SET avg_draw_rate = (
        SELECT AVG(CASE WHEN result = 'D' THEN 1.0 ELSE 0.0 END)
        FROM matches
        WHERE league_id = NEW.league_id
            AND result IS NOT NULL
            AND match_date >= CURRENT_DATE - INTERVAL '5 years'
    )
    WHERE id = NEW.league_id;
    
    -- Update home_advantage
    UPDATE leagues
    SET home_advantage = (
        SELECT AVG(home_goals - away_goals)
        FROM matches
        WHERE league_id = NEW.league_id
            AND home_goals IS NOT NULL
            AND away_goals IS NOT NULL
            AND match_date >= CURRENT_DATE - INTERVAL '5 years'
    )
    WHERE id = NEW.league_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_league_stats_on_match_insert
AFTER INSERT ON matches
FOR EACH ROW
EXECUTE FUNCTION update_league_statistics();
```

**Note:** This may be too expensive for high-volume inserts. Consider batch updates instead.

---

## 📋 Implementation Checklist

- [ ] **Add calculation logic** to `populate_database.py` or create separate service
- [ ] **Test calculation** with sample match data
- [ ] **Verify accuracy** by comparing with known league statistics
- [ ] **Add logging** to track when statistics are updated
- [ ] **Add API endpoint** for manual refresh (if using Option 2)
- [ ] **Document** the calculation method and time window (5 years)
- [ ] **Update existing leagues** in database with calculated values
- [ ] **Add validation** to ensure values are in reasonable ranges

---

## 🎯 Expected Results After Implementation

### **Before:**
```sql
SELECT code, name, avg_draw_rate, home_advantage 
FROM leagues 
WHERE code = 'E0';
-- Returns: E0, Premier League, 0.26, 0.35 (defaults)
```

### **After:**
```sql
SELECT code, name, avg_draw_rate, home_advantage 
FROM leagues 
WHERE code = 'E0';
-- Returns: E0, Premier League, 0.265, 0.342 (calculated from matches)
```

---

## 📚 Related Files

- **Database Population**: `15_Football_Data_/02_Db populating_Script/populate_database.py` (lines 287-348)
- **Database Schema**: `3_Database_Football_Probability_Engine/3_Database_Football_Probability_Engine.sql` (lines 128-141)
- **League Model**: `2_Backend_Football_Probability_Engine/app/db/models.py` (lines 52-68)
- **Exported Data**: `c:\Users\Admin\Desktop\Exported_Football _DB\leagues_202601081311.sql`

---

## ⚠️ Critical Issues Summary

1. **❌ No Calculation**: `avg_draw_rate` and `home_advantage` are NOT calculated from match data
2. **❌ Default Values**: Most leagues use defaults (0.26, 0.35) regardless of actual match data
3. **❌ Inconsistent Data**: Some leagues have different values (source unknown)
4. **❌ No Update Mechanism**: No way to refresh statistics when new matches are added
5. **❌ Impact on Model**: Model training uses incorrect league parameters

---

## ✅ Recommendation

**Implement Option 1** (add to `populate_database.py`) as a quick fix, then **migrate to Option 2** (separate service) for better maintainability and API access.

**Priority:** HIGH - These values directly affect model accuracy and probability calculations.

