# Injury Input Frontend Guide

## ✅ **IMPLEMENTED: Frontend Injury Input Interface**

The frontend now includes a complete interface for recording team injuries that adjusts probability calculations.

---

## How to Use Injury Input

### 1. **Access Injury Input**

In the **Probability Output** page:
- Each fixture displays an **injury icon** (⚠️) next to each team name
- Click the icon to open the injury input dialog for that team

### 2. **Injury Input Dialog**

The dialog includes:

#### **Quick Input:**
- **Key Players Missing**: Number of key/star players missing (0-10)
- **Injury Severity**: Slider from 0% to 100% (overall impact)

#### **Position-Specific Injuries (Optional):**
- **Attackers Missing** (0-5)
- **Midfielders Missing** (0-5)
- **Defenders Missing** (0-5)
- **Goalkeepers Missing** (0-2)

#### **Notes:**
- Free text field for additional injury details
- Example: "Star striker injured, expected return in 2 weeks"

### 3. **Auto-Calculation**

- If you fill position-specific injuries, severity is **auto-calculated**
- Severity calculation weights:
  - Goalkeepers: 1.0x impact
  - Key Players: 0.8x impact
  - Midfielders: 0.4x impact
  - Attackers/Defenders: 0.3x impact

### 4. **Impact Preview**

The dialog shows:
- **Estimated team strength reduction** based on injuries
- **Warning** if critical injuries detected (>70% severity)

### 5. **Saving Injuries**

- Click **"Save Injuries"** to record
- Injuries are saved to the database
- Probabilities are automatically recalculated with injury adjustments
- Page refreshes to show updated probabilities

---

## API Endpoints

### Record Injuries
```
POST /api/draw-ingestion/injuries
Body: {
  team_id: number,
  fixture_id: number,
  key_players_missing?: number,
  injury_severity?: number,  // 0.0-1.0
  attackers_missing?: number,
  midfielders_missing?: number,
  defenders_missing?: number,
  goalkeepers_missing?: number,
  notes?: string
}
```

### Get Injuries
```
GET /api/draw-ingestion/injuries/{fixture_id}/{team_id}
```

### Batch Record Injuries
```
POST /api/draw-ingestion/injuries/batch
Body: {
  injuries: [
    { team_id, fixture_id, ... },
    ...
  ]
}
```

---

## How Injuries Affect Probabilities

### Team Strength Adjustment:
- Injuries reduce team strength before probability calculation
- Impact is proportional to severity:
  - **0-30%**: Minor impact (~5% strength reduction)
  - **30-70%**: Moderate impact (~10-15% strength reduction)
  - **70-100%**: Critical impact (~15-25% strength reduction)

### Probability Recalculation:
- After saving injuries, probabilities are recalculated
- Home/Away/Draw probabilities adjust based on:
  - Home team injuries → Favors away team
  - Away team injuries → Favors home team
  - Both teams injured → May favor draw

---

## Frontend Components

### InjuryInput Component
**Location:** `src/components/InjuryInput.tsx`

**Features:**
- ✅ Loads existing injury data when opened
- ✅ Auto-calculates severity from positions
- ✅ Real-time impact preview
- ✅ Form validation
- ✅ Error handling with toast notifications

### Integration Points

**ProbabilityOutput Page:**
- Injury icons next to team names
- Dialog state management
- Auto-refresh after saving

---

## Example Workflow

1. **View Probabilities**
   - Navigate to Probability Output page
   - See fixtures with current probabilities

2. **Record Injuries**
   - Click injury icon next to "Arsenal"
   - Enter: 2 key players missing, severity 60%
   - Add notes: "Striker and midfielder injured"
   - Click "Save Injuries"

3. **See Updated Probabilities**
   - Page refreshes automatically
   - Arsenal's win probability decreases
   - Opponent's win probability increases
   - Draw probability may increase

---

## Data Persistence

- Injuries are saved to `team_injuries` table
- Linked to specific `fixture_id` and `team_id`
- Updates existing record if already exists
- Persists across page reloads

---

## Best Practices

1. **Record injuries before calculating probabilities** for most accurate results
2. **Use position-specific injuries** when available for better severity calculation
3. **Add notes** for context (return dates, player names, etc.)
4. **Update injuries** if new information becomes available
5. **Clear injuries** by setting all fields to 0 if players return

---

## Troubleshooting

### Injury icon not showing:
- Check that fixture has `fixtureIdNum` and `teamId` in fixture data
- Verify backend API includes `homeTeamId` and `awayTeamId` in response

### Injuries not affecting probabilities:
- Ensure injuries are saved successfully (check toast notification)
- Verify probabilities are recalculated after saving
- Check backend logs for injury adjustment application

### Can't load existing injuries:
- Check that fixture_id and team_id are correct
- Verify database connection
- Check API endpoint `/draw-ingestion/injuries/{fixture_id}/{team_id}`

---

## Summary

✅ **Complete injury input interface implemented**

- ✅ Frontend dialog component
- ✅ API endpoints for CRUD operations
- ✅ Auto-calculation of severity
- ✅ Impact preview
- ✅ Integration with probability calculations
- ✅ Data persistence

**Result:** Users can easily record team injuries and see their impact on probability calculations in real-time.

