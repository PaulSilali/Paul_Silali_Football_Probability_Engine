# Handling Missing Teams in Jackpot Input

## 🚨 What Happens When Teams Are Missing?

When you input jackpot teams and see **"4 teams not found"**, here's what's happening:

### **Visual Indicators:**
- ⚠️ **Red border** around team name input field
- ⚠️ **Red warning icon** (triangle with exclamation mark)
- 📊 **Status bar** shows: "X teams not found"

### **Impact on Probability Calculation:**
- ❌ **Missing teams use default strengths**: `attack_rating = 1.0`, `defense_rating = 1.0`
- ⚠️ **Uniform probabilities**: Matches with missing teams will have approximately equal probabilities (≈33% each outcome)
- 📉 **Reduced accuracy**: Predictions will be less accurate for matches involving missing teams

---

## ✅ What You Can Do

### **Option 1: Use Team Suggestions (Recommended)**

The system provides **fuzzy matching suggestions** when teams are not found:

1. **Hover over the warning icon** next to the team name
2. **View suggestions** - up to 3 similar team names from the database
3. **Click a suggestion** to replace the team name
4. **Or manually type** the suggested name

**Example:**
- You typed: `"SC Sao Joao de Ver"`
- Suggestions shown: `["Sao Joao de Ver", "SC Sao Joao", "Sao Joao Ver"]`
- Click suggestion → Team name updated → Validation passes ✅

---

### **Option 2: Check Team Name Spelling**

Common issues:
- **Extra spaces**: `"SC Sao Joao de Ver"` vs `"Sao Joao de Ver"`
- **Abbreviations**: `"Man Utd"` vs `"Manchester United"`
- **FC/SC prefixes**: `"FC Arsenal"` vs `"Arsenal"`
- **City names**: `"Manchester City"` vs `"Man City"`

**Try:**
- Remove prefixes (FC, SC, etc.)
- Use full team names
- Check for typos

---

### **Option 3: Add Missing Teams to Database**

If teams are genuinely missing (not just spelling issues), you can add them:

#### **Method A: Using SQL Script (Quick)**

1. **Identify missing teams** from the validation summary
2. **Create SQL script** or use existing migration:
   ```sql
   -- Example: Add missing team
   INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
   SELECT id, 'SC Sao Joao de Ver', 'sc sao joao de ver', 1.0, 1.0, 0.0
   FROM leagues WHERE code = 'PORTUGAL_LEAGUE'  -- Adjust league code
   ON CONFLICT (canonical_name, league_id) DO NOTHING;
   ```

3. **Run in PostgreSQL**:
   ```bash
   psql -U your_user -d your_database -f add_missing_teams.sql
   ```

#### **Method B: Using Python Script**

```bash
cd "2_Backend_Football_Probability_Engine"
python scripts/add_missing_teams.py --dry-run  # Preview changes
python scripts/add_missing_teams.py             # Actually add teams
```

**Note:** Requires database credentials in `.env` file.

#### **Method C: Manual Database Entry**

1. **Open PostgreSQL client** (pgAdmin, DBeaver, etc.)
2. **Find the league** for the missing team:
   ```sql
   SELECT id, code, name FROM leagues WHERE name LIKE '%Portugal%';
   ```
3. **Insert team**:
   ```sql
   INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
   VALUES (
     (SELECT id FROM leagues WHERE code = 'PORTUGAL_LEAGUE'),
     'SC Sao Joao de Ver',
     'sc sao joao de ver',  -- lowercase, no special chars
     1.0,  -- default attack
     1.0,  -- default defense
     0.0   -- default home bias
   );
   ```

---

### **Option 4: Continue with Default Strengths (Not Recommended)**

You can proceed with missing teams, but:
- ⚠️ **Probabilities will be uniform** (≈33% each)
- ⚠️ **Less accurate predictions**
- ⚠️ **May affect overall jackpot accuracy**

**When this is acceptable:**
- Testing the system
- Quick probability checks
- Teams are very obscure/rare

---

## 🔍 How to Identify Missing Teams

### **In the UI:**

1. **Look for red warning icons** next to team names
2. **Check validation summary** at the top:
   - ✅ "30 teams validated" (green)
   - ⚠️ "4 teams not found" (red)
3. **Hover over warning icons** to see which teams are missing

### **In the Backend Logs:**

When calculating probabilities, check logs for:
```
Team "SC Sao Joao de Ver" not found, using default strengths (1.0, 1.0)
```

---

## 📋 Step-by-Step: Fix Missing Teams

### **Scenario: 4 Teams Not Found**

1. **Identify the 4 teams:**
   - Look at red warning icons in the fixtures table
   - Note down exact team names

2. **Check suggestions:**
   - Hover over each warning icon
   - See if suggestions match your intended team
   - If yes → Click suggestion to fix

3. **If no good suggestions:**
   - Verify team name spelling
   - Check if team exists in database:
     ```sql
     SELECT name, canonical_name FROM teams 
     WHERE canonical_name LIKE '%sao%joao%';
     ```

4. **Add missing teams:**
   - Use SQL script (Method A above)
   - Or Python script (Method B above)
   - Or manual entry (Method C above)

5. **Refresh validation:**
   - Click **"Validate All Teams"** button
   - Teams should now be found ✅

---

## 🎯 Best Practices

### **Before Adding Teams:**

1. ✅ **Check suggestions first** - Often it's just a spelling issue
2. ✅ **Verify team exists** - Confirm team name is correct
3. ✅ **Identify league** - Teams must belong to a league
4. ✅ **Use canonical format** - Lowercase, no special chars

### **After Adding Teams:**

1. ✅ **Retrain model** - To calculate proper team strengths
2. ✅ **Verify in database** - Confirm teams were added correctly
3. ✅ **Test probability calculation** - Check if teams are now found

---

## 📊 Impact on Probability Calculation

### **With Missing Teams:**

```
Team A (found): attack=1.2, defense=0.9
Team B (missing): attack=1.0, defense=1.0  ← Default strengths

Result: Probabilities ≈ 40% Home, 30% Draw, 30% Away
```

### **After Adding Teams:**

```
Team A (found): attack=1.2, defense=0.9
Team B (found): attack=1.1, defense=1.0  ← Model-calculated strengths

Result: Probabilities ≈ 45% Home, 28% Draw, 27% Away
```

**Difference:** More accurate probabilities based on actual team strengths.

---

## 🚀 Quick Reference

| Action | When to Use | Impact |
|--------|-------------|--------|
| **Use Suggestions** | Team name is close to existing team | ✅ Quick fix, no DB changes |
| **Fix Spelling** | Typo or formatting issue | ✅ Quick fix, no DB changes |
| **Add to Database** | Team genuinely missing | ✅ Permanent fix, requires DB access |
| **Continue Anyway** | Testing or quick check | ⚠️ Less accurate, uniform probabilities |

---

## 💡 Tips

1. **Common Missing Teams:**
   - Lower league teams
   - Recently promoted/relegated teams
   - Teams from less common leagues
   - Teams with unusual naming conventions

2. **Prevention:**
   - Use team name autocomplete (if available)
   - Import teams from historical data first
   - Regularly update team database

3. **Validation:**
   - Always click **"Validate All Teams"** before calculating probabilities
   - Check validation summary before proceeding
   - Fix missing teams before calculation for best accuracy

---

## 📝 Example: Fixing 4 Missing Teams

**Step 1:** Identify teams
- `SC Sao Joao de Ver`
- `Amarante FC`
- `Hellas Verona`
- `CD Leganes`

**Step 2:** Check suggestions
- `SC Sao Joao de Ver` → Suggestions: `["Sao Joao de Ver"]` ✅
- `Amarante FC` → No suggestions ❌
- `Hellas Verona` → Suggestions: `["Hellas Verona FC"]` ✅
- `CD Leganes` → Suggestions: `["Leganes"]` ✅

**Step 3:** Fix using suggestions
- Click `"Sao Joao de Ver"` → Fixed ✅
- Click `"Hellas Verona FC"` → Fixed ✅
- Click `"Leganes"` → Fixed ✅

**Step 4:** Add remaining team (`Amarante FC`)
```sql
INSERT INTO teams (league_id, name, canonical_name, attack_rating, defense_rating, home_bias)
SELECT id, 'Amarante FC', 'amarante fc', 1.0, 1.0, 0.0
FROM leagues WHERE code = 'PORTUGAL_LEAGUE'
ON CONFLICT (canonical_name, league_id) DO NOTHING;
```

**Step 5:** Validate again
- Click **"Validate All Teams"**
- All teams should now be found ✅

---

## 🆘 Still Having Issues?

If teams are still not found after trying suggestions and adding to database:

1. **Check canonical name format:**
   - Must be lowercase
   - No special characters
   - Matches `normalize_team_name()` function output

2. **Verify league assignment:**
   - Team must belong to a league
   - League must exist in database

3. **Check database connection:**
   - Ensure backend can connect to database
   - Verify team was actually inserted

4. **Review backend logs:**
   - Check for team resolution errors
   - Verify fuzzy matching is working

---

## 📚 Related Documentation

- `ADD_MISSING_TEAMS_GUIDE.md` - Detailed guide for adding teams
- `TEAM_VALIDATION_IMPLEMENTATION.md` - How team validation works
- `JACKPOT_PROBABILITY_COMPUTATION_WORKFLOW.md` - Complete workflow

