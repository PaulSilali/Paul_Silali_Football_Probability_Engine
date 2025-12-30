# Root Cause: Matches Not Being Inserted into Database

## 🔍 **Problem Identified**

When CSV files are downloaded and saved, **matches are NOT being inserted into the database**, even though:
- ✅ CSV files are successfully saved to `data/1_data_ingestion/batch_*/`
- ✅ Data cleaning is applied
- ✅ Ingestion logs are created
- ❌ **But matches table remains empty**

---

## 🐛 **Root Cause**

### **Issue: Teams Must Exist Before Matches Can Be Inserted**

Looking at `app/services/data_ingestion.py`, line 218-224:

```python
home_team = resolve_team_safe(self.db, home_team_name, league.id)
away_team = resolve_team_safe(self.db, away_team_name, league.id)

if not home_team or not away_team:
    stats["skipped"] += 1
    errors.append(f"Teams not found: {home_team_name} vs {away_team_name}")
    continue  # ← SKIPS THE MATCH ENTIRELY
```

**The Problem:**
1. `resolve_team_safe()` searches for teams in the database using fuzzy matching
2. If teams don't exist in the `teams` table, it returns `None`
3. **When teams are not found, the match is SKIPPED** (not inserted)
4. This means **ALL matches get skipped** if teams haven't been created first

---

## 🔎 **Why Teams Might Not Exist**

### **Possible Reasons:**

1. **Teams Table is Empty**
   - Teams need to be created before matches can be inserted
   - There's no automatic team creation during ingestion
   - Teams must be manually created or imported first

2. **Team Name Mismatch**
   - CSV has team names like "Man United"
   - Database expects "Manchester United"
   - Fuzzy matching fails if similarity < 0.7 (default threshold)

3. **League Mismatch**
   - Teams exist but in wrong league
   - `resolve_team_safe` filters by `league_id`
   - If team is in different league, it won't be found

4. **Team Creation Not Implemented**
   - No automatic team creation during ingestion
   - Teams must be pre-populated

---

## ✅ **Solution Options**

### **Option 1: Auto-Create Teams During Ingestion** (RECOMMENDED)

Modify `ingest_csv` to automatically create teams if they don't exist:

```python
# Instead of skipping when team not found:
if not home_team:
    # Create team automatically
    home_team = self._create_team_if_not_exists(
        self.db, 
        home_team_name, 
        league.id
    )

if not away_team:
    away_team = self._create_team_if_not_exists(
        self.db, 
        away_team_name, 
        league.id
    )
```

**Benefits:**
- ✅ Matches get inserted automatically
- ✅ Teams are created as needed
- ✅ No manual intervention required

---

### **Option 2: Pre-Populate Teams**

Create teams before running ingestion:

1. **Extract unique team names from CSV files**
2. **Create teams in database** (one-time setup)
3. **Then run ingestion** - matches will insert successfully

**Benefits:**
- ✅ Clean separation of concerns
- ✅ Can validate team names before ingestion
- ❌ Requires manual step

---

### **Option 3: Lower Similarity Threshold**

Reduce the fuzzy matching threshold in `resolve_team_safe`:

```python
# Current: min_similarity = 0.7 (default)
# Change to: min_similarity = 0.5
```

**Benefits:**
- ✅ More lenient matching
- ❌ Might match wrong teams
- ❌ Doesn't solve missing teams issue

---

## 🔧 **Recommended Fix**

**Implement Option 1: Auto-Create Teams**

Add a method to `DataIngestionService`:

```python
def _create_team_if_not_exists(
    self,
    team_name: str,
    league_id: int
) -> Team:
    """
    Create team if it doesn't exist in database
    
    Args:
        team_name: Team name from CSV
        league_id: League ID
    
    Returns:
        Team object (created or existing)
    """
    # Try to find existing team
    team = resolve_team_safe(self.db, team_name, league_id)
    
    if team:
        return team
    
    # Create new team
    from app.db.models import Team
    team = Team(
        league_id=league_id,
        name=team_name,
        canonical_name=normalize_team_name(team_name)
    )
    self.db.add(team)
    self.db.flush()
    
    logger.info(f"Created new team: {team_name} (canonical: {team.canonical_name})")
    return team
```

Then modify `ingest_csv`:

```python
# Replace this:
home_team = resolve_team_safe(self.db, home_team_name, league.id)
away_team = resolve_team_safe(self.db, away_team_name, league.id)

if not home_team or not away_team:
    stats["skipped"] += 1
    errors.append(f"Teams not found: {home_team_name} vs {away_team_name}")
    continue

# With this:
home_team = self._create_team_if_not_exists(home_team_name, league.id)
away_team = self._create_team_if_not_exists(away_team_name, league.id)
```

---

## 📊 **Current Behavior**

### **What Happens Now:**

1. CSV downloaded ✅
2. CSV cleaned ✅
3. CSV saved to disk ✅
4. Teams looked up in database ❌ (not found)
5. **Matches SKIPPED** ❌
6. Ingestion log created ✅ (but shows 0 inserted)

### **Result:**
- CSV files exist in `data/1_data_ingestion/`
- Database `matches` table is empty
- `ingestion_logs` shows `records_inserted = 0`

---

## 🎯 **Next Steps**

1. **Check Database:**
   ```sql
   SELECT COUNT(*) FROM teams;
   SELECT COUNT(*) FROM matches;
   ```

2. **Check Ingestion Logs:**
   ```sql
   SELECT records_inserted, records_skipped, error_message 
   FROM ingestion_logs 
   ORDER BY id DESC LIMIT 10;
   ```

3. **Implement Auto-Create Teams** (recommended fix)

4. **Re-run Ingestion** to populate database

---

## 📝 **Summary**

**Root Cause:** Matches are skipped when teams don't exist in database.

**Solution:** Auto-create teams during ingestion if they don't exist.

**Impact:** All matches will be inserted successfully, database will be populated.

---

**Status:** 🔴 **ISSUE IDENTIFIED** - Needs fix implementation

