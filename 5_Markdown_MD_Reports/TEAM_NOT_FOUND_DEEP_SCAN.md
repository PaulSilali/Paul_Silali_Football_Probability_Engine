# Deep Scan: What Happens When a Team is Not Found

## Case Study: "MK Dons" vs "Milton Keynes Dons"

### 📋 **Scenario**
- **User Input:** "MK Dons"
- **Database Name:** "Milton Keynes Dons F.C."
- **League:** League Two (E3)
- **Location:** 4th in Football League Two

---

## 🔍 **Step-by-Step Flow**

### **1. Frontend Validation (Jackpot Input Page)**

**Location:** `1_Frontend_Football_Probability_Engine/src/pages/JackpotInput.tsx`

**What Happens:**
1. User types "MK Dons" in team input field
2. After 500ms debounce, frontend calls `apiClient.validateTeamName("MK Dons")`
3. Backend endpoint: `POST /api/validation/team`
4. Backend calls `validate_team_name(db, "MK Dons", league_id=None)`

**Validation Process:**
```python
# app/services/team_resolver.py
def validate_team_name(db, team_name, league_id):
    result = resolve_team(db, "MK Dons", league_id, min_similarity=0.7)
    
    if result:
        team, score = result
        return {
            "isValid": True,
            "normalizedName": team.canonical_name,
            "confidence": score
        }
    else:
        suggestions = suggest_team_names(db, "MK Dons", league_id, limit=5)
        return {
            "isValid": False,
            "suggestions": suggestions  # e.g., ["Milton Keynes Dons", "Milton Keynes", ...]
        }
```

**Result:**
- ❌ **Validation FAILS** (similarity < 0.7)
- ✅ **Shows suggestions:** ["Milton Keynes Dons", "Milton Keynes", ...]
- ⚠️ **Frontend displays:** Red border + warning icon with tooltip

---

### **2. Team Name Normalization**

**Location:** `app/services/team_resolver.py` → `normalize_team_name()`

**Process:**
```python
def normalize_team_name(name: str) -> str:
    # 1. Convert to lowercase
    normalized = name.lower().strip()  # "MK Dons" → "mk dons"
    
    # 2. Remove common suffixes
    suffixes = [" fc", " cf", " bc", " ac", " united", " utd", " city", " town"]
    # "Milton Keynes Dons F.C." → "milton keynes dons" (removes " f.c.")
    
    # 3. Remove special characters
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    
    # 4. Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()
```

**Normalized Names:**
- **Input:** "MK Dons" → **Normalized:** `"mk dons"`
- **Database:** "Milton Keynes Dons F.C." → **Normalized:** `"milton keynes dons"`

---

### **3. Similarity Calculation**

**Location:** `app/services/team_resolver.py` → `similarity_score()`

**Process:**
```python
def similarity_score(name1: str, name2: str) -> float:
    norm1 = normalize_team_name(name1)  # "mk dons"
    norm2 = normalize_team_name(name2)   # "milton keynes dons"
    
    # Check exact match
    if norm1 == norm2:
        return 1.0  # ❌ Not equal
    
    # Check aliases (TEAM_ALIASES dict)
    # ❌ "MK Dons" not in aliases for "Milton Keynes Dons"
    
    # Use SequenceMatcher for fuzzy matching
    from difflib import SequenceMatcher
    score = SequenceMatcher(None, "mk dons", "milton keynes dons").ratio()
    # Result: ~0.35 (35% similarity)
```

**Similarity Score:**
- **"mk dons" vs "milton keynes dons"** ≈ **0.35** (35%)
- **Minimum threshold:** 0.7 (70%)
- **Result:** ❌ **BELOW THRESHOLD** → Team not found

**Why So Low?**
- "MK" and "Milton Keynes" are completely different strings
- SequenceMatcher compares character sequences
- Only "dons" matches, but it's a small part of the string
- Abbreviations don't match well with full names

---

### **4. Team Resolution Failure**

**Location:** `app/services/team_resolver.py` → `resolve_team()`

**Process:**
```python
def resolve_team(db, team_name, league_id, min_similarity=0.7):
    teams = db.query(Team).filter(Team.league_id == league_id).all()
    
    matches = []
    for team in teams:
        score1 = similarity_score("MK Dons", team.canonical_name)
        score2 = similarity_score("MK Dons", team.name)
        best_score = max(score1, score2)
        
        if best_score >= 0.7:  # ❌ 0.35 < 0.7
            matches.append((team, best_score))
    
    if not matches:
        return None  # ❌ Returns None
    
    return matches[0]
```

**Result:**
- ❌ **No matches found** (all scores < 0.7)
- Returns `None`

---

### **5. Probability Calculation (When Team Not Found)**

**Location:** `app/api/probabilities.py` → `get_team_strength_for_fixture()`

**Process:**
```python
def get_team_strength_for_fixture(team_name: str, team_id_from_fixture: Optional[int] = None):
    # Try to find team in database
    team = resolve_team_safe(db, "MK Dons")
    
    if team:
        # ✅ Team found - use model/database strengths
        return TeamStrength(team_id=team.id, attack=1.2, defense=0.9)
    else:
        # ❌ Team not found
        logger.warning(f"Team 'MK Dons' not found in database (fuzzy match failed), using default strengths (1.0, 1.0)")
        
        # FALLBACK: Use default strengths
        return TeamStrength(
            team_id=0,  # No team ID
            attack=1.0,   # Default attack rating
            defense=1.0   # Default defense rating
        )
```

**Default Strengths:**
- **Attack Rating:** `1.0` (average)
- **Defense Rating:** `1.0` (average)
- **Team ID:** `0` (no team in database)

---

### **6. Probability Calculation with Default Strengths**

**Location:** `app/models/poisson.py` → `calculate_match_probabilities()`

**What Happens:**
```python
# Both teams have default strengths (1.0, 1.0)
home_strength = TeamStrength(team_id=0, attack=1.0, defense=1.0)
away_strength = TeamStrength(team_id=0, attack=1.0, defense=1.0)

# Calculate expected goals
home_expected = home_strength.attack * away_strength.defense * home_advantage
away_expected = away_strength.attack * home_strength.defense

# With default strengths (1.0, 1.0):
home_expected = 1.0 * 1.0 * 1.35 = 1.35 goals
away_expected = 1.0 * 1.0 = 1.0 goals

# Calculate probabilities using Poisson distribution
# Result: ≈ 33% Home, 33% Draw, 33% Away (UNIFORM)
```

**Result:**
- **Home Win Probability:** ≈ 0.33 (33%)
- **Draw Probability:** ≈ 0.34 (34%)
- **Away Win Probability:** ≈ 0.33 (33%)
- **Entropy:** ≈ 1.58 (maximum uncertainty)

**Why Uniform?**
- Both teams have identical strengths (1.0, 1.0)
- Only home advantage creates slight difference
- Probabilities become nearly uniform
- **No meaningful prediction** - just equal chances

---

### **7. Impact on Probability Sets**

**Location:** `app/models/probability_sets.py`

**All Probability Sets (A-G) are affected:**

| Set | Description | Impact |
|-----|-------------|--------|
| **A** | Pure Model | Uniform probabilities (≈33% each) |
| **B** | Market-Aware Blending | Blends uniform model with market odds |
| **C** | Market-Dominant | Mostly market odds (still affected) |
| **D** | Draw-Boosted | Uniform + draw boost |
| **E** | Entropy-Penalized | Uniform (high entropy) |
| **F** | Kelly-Weighted | Uniform probabilities |
| **G** | Ensemble | Average of all sets (still uniform) |

**Result:**
- ❌ **All probability sets become inaccurate**
- ❌ **No meaningful prediction** - just equal chances
- ❌ **User gets misleading probabilities**

---

## 📊 **Summary: Complete Flow**

```
User Input: "MK Dons"
    ↓
Frontend Validation
    ↓
❌ Validation FAILS (similarity < 0.7)
    ↓
Shows suggestions: ["Milton Keynes Dons", ...]
    ↓
User submits anyway (or corrects name)
    ↓
Backend Probability Calculation
    ↓
resolve_team_safe("MK Dons") → None
    ↓
Uses default strengths: (1.0, 1.0)
    ↓
Calculate probabilities
    ↓
Result: ≈ 33% Home, 34% Draw, 33% Away
    ↓
❌ UNIFORM PROBABILITIES (no meaningful prediction)
```

---

## ⚠️ **Problems Identified**

### **1. Abbreviation Matching Fails**
- **"MK Dons"** vs **"Milton Keynes Dons"** = 35% similarity
- **Threshold:** 70% required
- **Result:** Team not found

### **2. No Alias Support for MK Dons**
- `TEAM_ALIASES` dict doesn't include:
  ```python
  "milton keynes dons": ["mk dons", "mk", "milton keynes"]
  ```

### **3. Silent Failure**
- Backend uses defaults without warning user
- Probabilities become uniform
- User doesn't know predictions are meaningless

### **4. Default Strengths Too Generic**
- All teams get (1.0, 1.0)
- No league-specific defaults
- No historical data fallback

---

## ✅ **Solutions**

### **1. Add Alias Support**
```python
# app/services/team_resolver.py
TEAM_ALIASES = {
    # ... existing aliases ...
    "milton keynes dons": ["mk dons", "mk", "milton keynes", "mk dons fc"],
}
```

### **2. Lower Similarity Threshold for Abbreviations**
- Detect abbreviations (e.g., "MK" = "Milton Keynes")
- Use special matching for known abbreviations
- Or: Lower threshold to 0.5 for League Two teams

### **3. Better Default Strengths**
- Use league-average strengths instead of (1.0, 1.0)
- Use historical data if available
- Use team position in league table

### **4. Warning System**
- Frontend already warns (✅ implemented)
- Backend should also log warnings
- Return warnings in API response

---

## 🔧 **Recommended Fix**

**Add to `TEAM_ALIASES` in `app/services/team_resolver.py`:**

```python
TEAM_ALIASES = {
    # ... existing aliases ...
    
    # League Two
    "milton keynes dons": ["mk dons", "mk", "milton keynes", "mk dons fc"],
    "afc wimbledon": ["wimbledon", "afc w"],
    "newport county": ["newport", "newport c"],
    "notts county": ["notts", "notts c"],
    "tranmere rovers": ["tranmere", "tranmere r"],
    # ... add more League Two teams ...
}
```

**This will:**
- ✅ Match "MK Dons" → "Milton Keynes Dons" with 95% confidence
- ✅ Return correct team from database
- ✅ Use actual team strengths from model
- ✅ Generate accurate probabilities

---

## 📝 **Current Behavior Summary**

| Stage | Input | Result |
|-------|-------|--------|
| **Frontend Validation** | "MK Dons" | ❌ Invalid (shows suggestions) |
| **Team Resolution** | "MK Dons" | ❌ Not found (similarity 35% < 70%) |
| **Team Strengths** | Not found | ✅ Default (1.0, 1.0) |
| **Probability Calculation** | Default strengths | ❌ Uniform (≈33% each) |
| **User Experience** | Submits anyway | ❌ Gets meaningless probabilities |

---

## 🎯 **Conclusion**

When "MK Dons" is entered instead of "Milton Keynes Dons":
1. ✅ **Frontend validation catches it** (shows warning + suggestions)
2. ❌ **If user submits anyway**, backend fails to match
3. ❌ **Uses default strengths** (1.0, 1.0)
4. ❌ **Generates uniform probabilities** (≈33% each)
5. ❌ **User gets meaningless predictions**

**The fix:** Add "MK Dons" to `TEAM_ALIASES` for "Milton Keynes Dons"

