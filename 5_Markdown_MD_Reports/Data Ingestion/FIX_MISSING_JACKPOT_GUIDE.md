# Fix Missing Jackpot Error: JK-2024-1236 Not Found

## 🚨 Problem

You're getting a `404 Not Found` error when trying to access jackpot `JK-2024-1236`:

```
GET http://localhost:8000/api/probabilities/JK-2024-1236/probabilities 404 (Not Found)
Error: Jackpot JK-2024-1236 not found
```

## 🔍 Root Cause

This happens when:
1. **`saved_probability_results`** table has a record with `jackpot_id = 'JK-2024-1236'`
2. **`jackpots`** table does NOT have a matching entry with `jackpot_id = 'JK-2024-1236'`
3. Frontend tries to access probabilities for this jackpot, but backend can't find it

**Why this happens:**
- Jackpot IDs are auto-generated as `JK-{timestamp}` (e.g., `JK-1735123456`)
- If an old import used a different ID format (`JK-2024-1236`), it won't match
- Or the jackpot was deleted but `saved_probability_results` still references it

---

## ✅ Solution Options

### **Option 1: Run Diagnostic Script (Recommended First Step)**

Run the diagnostic SQL script to understand the situation:

```bash
psql -U your_user -d your_database -f "3_Database_Football_Probability_Engine/migrations/fix_missing_jackpot.sql"
```

This will:
1. ✅ Check if `JK-2024-1236` exists in `saved_probability_results`
2. ✅ List recent jackpots to find the correct ID
3. ✅ Identify all missing jackpot references
4. ✅ Provide options to fix

---

### **Option 2: Find the Correct Jackpot ID**

If the jackpot exists with a different ID:

**Step 1:** Find recent jackpots:
```sql
SELECT jackpot_id, name, created_at, 
       (SELECT COUNT(*) FROM jackpot_fixtures WHERE jackpot_id = jackpots.id) as fixture_count
FROM jackpots
ORDER BY created_at DESC
LIMIT 10;
```

**Step 2:** Match by creation date or name:
```sql
-- Find saved result
SELECT jackpot_id, name, created_at, total_fixtures
FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236';

-- Find matching jackpot by date/name
SELECT j.jackpot_id, j.name, j.created_at
FROM jackpots j
WHERE j.created_at::date = (
    SELECT created_at::date 
    FROM saved_probability_results 
    WHERE jackpot_id = 'JK-2024-1236'
)
ORDER BY j.created_at DESC;
```

**Step 3:** Update `saved_probability_results` to use correct ID:
```sql
UPDATE saved_probability_results
SET jackpot_id = 'JK-CORRECT-ID'  -- Replace with actual correct ID
WHERE jackpot_id = 'JK-2024-1236';
```

---

### **Option 3: Create Missing Jackpot Entry**

If the jackpot truly doesn't exist, create it:

**Step 1:** Run the auto-fix script (included in `fix_missing_jackpot.sql`):
```sql
-- This creates the jackpot entry automatically
-- See STEP 4 in fix_missing_jackpot.sql
```

**Step 2:** Add fixtures manually (if missing):
```sql
-- Get the saved result to see what fixtures are needed
SELECT actual_results, total_fixtures
FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236';

-- Add fixtures (you'll need team names from original import)
INSERT INTO jackpot_fixtures (jackpot_id, match_order, home_team, away_team, odds_home, odds_draw, odds_away)
VALUES (
    (SELECT id FROM jackpots WHERE jackpot_id = 'JK-2024-1236'),
    1,
    'Home Team Name',  -- Replace with actual team name
    'Away Team Name',  -- Replace with actual team name
    2.0, 3.0, 2.5  -- Default odds, adjust as needed
);
-- Repeat for each fixture (match_order 1, 2, 3, ...)
```

---

### **Option 4: Delete Orphaned Saved Result**

If the jackpot data is no longer needed:

```sql
-- Delete the saved result that references missing jackpot
DELETE FROM saved_probability_results
WHERE jackpot_id = 'JK-2024-1236';
```

**⚠️ Warning:** This will permanently delete the saved result data.

---

## 🔧 Quick Fix Script

Here's a quick SQL script to automatically fix the issue:

```sql
-- Quick fix: Create missing jackpot if saved result exists
DO $$
DECLARE
    saved_result RECORD;
    new_jackpot_id VARCHAR := 'JK-2024-1236';
    new_jackpot_record_id INTEGER;
BEGIN
    -- Get the saved result
    SELECT * INTO saved_result
    FROM saved_probability_results
    WHERE jackpot_id = new_jackpot_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- If saved result exists and jackpot doesn't exist, create it
    IF saved_result.id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM jackpots WHERE jackpot_id = new_jackpot_id) THEN
            INSERT INTO jackpots (jackpot_id, user_id, name, status, model_version, created_at, updated_at)
            VALUES (
                new_jackpot_id,
                saved_result.user_id,
                saved_result.name,
                'draft',
                saved_result.model_version,
                saved_result.created_at,
                NOW()
            )
            RETURNING id INTO new_jackpot_record_id;
            
            RAISE NOTICE 'Created jackpot % with ID %', new_jackpot_id, new_jackpot_record_id;
            RAISE NOTICE 'WARNING: You need to add fixtures for this jackpot manually!';
        ELSE
            RAISE NOTICE 'Jackpot % already exists', new_jackpot_id;
        END IF;
    ELSE
        RAISE NOTICE 'No saved_probability_results found for jackpot_id %', new_jackpot_id;
    END IF;
END $$;
```

---

## 📋 Step-by-Step Troubleshooting

### **1. Check Current State**

```sql
-- Check if saved result exists
SELECT * FROM saved_probability_results WHERE jackpot_id = 'JK-2024-1236';

-- Check if jackpot exists
SELECT * FROM jackpots WHERE jackpot_id = 'JK-2024-1236';

-- Check for similar jackpots
SELECT jackpot_id, created_at FROM jackpots 
WHERE created_at::date = CURRENT_DATE - INTERVAL '1 day'
ORDER BY created_at DESC;
```

### **2. Identify the Issue**

- ✅ **Saved result exists, jackpot doesn't** → Use Option 3 (Create Missing Jackpot)
- ✅ **Both exist but ID mismatch** → Use Option 2 (Update saved result)
- ✅ **Saved result doesn't exist** → The error is from somewhere else, check frontend code

### **3. Apply Fix**

Choose the appropriate option above and run the SQL commands.

### **4. Verify Fix**

```sql
-- Verify jackpot exists
SELECT j.jackpot_id, COUNT(jf.id) as fixture_count
FROM jackpots j
LEFT JOIN jackpot_fixtures jf ON j.id = jf.jackpot_id
WHERE j.jackpot_id = 'JK-2024-1236'
GROUP BY j.jackpot_id;

-- Verify saved result can find jackpot
SELECT spr.jackpot_id, j.jackpot_id as jackpot_db_id
FROM saved_probability_results spr
LEFT JOIN jackpots j ON spr.jackpot_id = j.jackpot_id
WHERE spr.jackpot_id = 'JK-2024-1236';
```

---

## 🚀 Prevention

To prevent this issue in the future:

1. **Always use the jackpot ID returned from `createJackpot()` API**
2. **Don't manually set jackpot IDs** - let the backend generate them
3. **Verify jackpot exists** before saving probability results
4. **Use transactions** when creating jackpot + saving results together

---

## 📝 Related Files

- **Diagnostic Script:** `3_Database_Football_Probability_Engine/migrations/fix_missing_jackpot.sql`
- **Import Code:** `1_Frontend_Football_Probability_Engine/src/pages/DataIngestion.tsx` (lines 918-966)
- **Backend API:** `2_Backend_Football_Probability_Engine/app/api/jackpots.py` (line 389)

---

## 💡 Need Help?

If the issue persists:

1. **Check backend logs** for jackpot creation errors
2. **Verify database connection** is working
3. **Check if jackpot was deleted** accidentally
4. **Review import process** to ensure jackpot is created before saving results

