# Frontend Pipeline Integration Guide

## 🎯 Overview

The frontend now automatically checks for missing teams or missing training data during jackpot input, and when you click "Calculate Probabilities", it will:
1. Check team validation and training status
2. Download missing data (if needed)
3. Retrain the model (if needed)
4. Create the jackpot and calculate probabilities

All of this happens automatically with a progress dialog showing real-time status.

---

## ✅ What's New

### **1. Enhanced Team Validation**

Teams are now validated with **training status** checking:

- ✅ **Validated** - Team exists in database
- ✅ **Trained** - Team has model training data
- ⚠️ **Need Training** - Team exists but no training data
- ❌ **Not Found** - Team doesn't exist in database

**Visual Indicators:**
- Green checkmark (✓) = Validated
- Blue sparkles (✨) = Trained
- Yellow warning (⚠️) = Needs training
- Red warning (⚠️) = Not found

### **2. Validation Summary Banner**

A banner at the top of the jackpot input page shows:
- Number of validated teams
- Number of trained teams
- Number of teams needing training
- Number of teams not found
- Number of teams currently validating

**Example:**
```
✓ 12 validated  ✨ 10 trained  ⚠️ 2 need training  ⚠️ 0 not found
```

### **3. Automated Pipeline Execution**

When you click **"Calculate Probabilities"**:

1. **Status Check** (0-10%)
   - Checks all teams for validation and training status
   - Identifies missing teams or untrained teams

2. **Pipeline Execution** (10-90%)
   - If teams are missing or untrained:
     - Creates missing teams in database
     - Downloads historical match data
     - Retrains the model
   - Shows progress for each step

3. **Jackpot Creation** (90-100%)
   - Creates the jackpot
   - Navigates to probability output page

### **4. Progress Dialog**

A modal dialog shows:
- **Progress bar** (0-100%)
- **Current phase** (e.g., "Downloading data...", "Retraining model...")
- **Pipeline steps** with status:
  - ✓ Completed steps (green checkmark)
  - ⚠️ Failed steps (red warning)
  - ⏳ Running steps (spinner)
  - ⊘ Skipped steps (gray X)

---

## 🎨 User Interface

### **Validation Summary Banner**

Located at the top of the jackpot input page:

```tsx
✓ 12 validated  ✨ 10 trained  ⚠️ 2 need training
```

### **Progress Dialog**

Shown automatically when pipeline runs:

```
┌─────────────────────────────────────┐
│ Preparing Data Pipeline             │
├─────────────────────────────────────┤
│ Progress: 45%                       │
│ ████████████░░░░░░░░░░░░░░░░░░░░░░░ │
│                                     │
│ Current Step:                       │
│ Retraining model...                 │
│                                     │
│ Pipeline Steps:                     │
│ ✓ Status check                      │
│ ✓ Create teams                      │
│ ⏳ Download data                    │
│ ⏳ Train model                      │
│ ⊘ Recompute probabilities           │
└─────────────────────────────────────┘
```

---

## 🔄 Flow Diagram

```
User enters fixtures
    ↓
Teams validated as user types
    ↓
Validation summary shown
    ↓
User clicks "Calculate Probabilities"
    ↓
┌─────────────────────────────┐
│ Check team status           │
│ - Validated?                │
│ - Trained?                  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Pipeline needed?            │
│ - Missing teams?            │
│ - Untrained teams?          │
└─────────────────────────────┘
    ↓ YES
┌─────────────────────────────┐
│ Run Pipeline                │
│ 1. Create missing teams     │
│ 2. Download data            │
│ 3. Retrain model            │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Create Jackpot              │
│ Navigate to Probability      │
│ Output page                 │
└─────────────────────────────┘
```

---

## 📊 API Integration

### **New API Methods**

**1. Enhanced Team Validation**
```typescript
apiClient.validateTeamName(teamName, leagueId?, checkTraining?)
// Returns: { isValid, isTrained, strengthSource, ... }
```

**2. Check Teams Status**
```typescript
apiClient.checkTeamsStatus(teamNames, leagueId?)
// Returns: { validated_teams, missing_teams, trained_teams, untrained_teams, ... }
```

**3. Run Pipeline**
```typescript
apiClient.runPipeline({
  team_names: string[],
  auto_download: boolean,
  auto_train: boolean,
  auto_recompute: boolean,
  max_seasons: number
})
// Returns: { taskId, status, message }
```

**4. Get Pipeline Status**
```typescript
apiClient.getPipelineStatus(taskId)
// Returns: { status, progress, phase, steps, ... }
```

---

## 🎯 User Experience

### **Before Pipeline Integration**

1. User enters fixtures
2. Some teams show warnings (not validated)
3. User clicks "Calculate Probabilities"
4. Probabilities calculated with default strengths (less accurate)

### **After Pipeline Integration**

1. User enters fixtures
2. Teams validated automatically (with training status)
3. Validation summary shows:
   - ✓ Validated teams
   - ✨ Trained teams
   - ⚠️ Teams needing training
4. User clicks "Calculate Probabilities"
5. **Pipeline runs automatically** (if needed):
   - Downloads missing data
   - Retrains model
   - Shows progress dialog
6. Probabilities calculated with **trained strengths** (more accurate)

---

## ⚙️ Configuration

### **Pipeline Options**

The pipeline runs with these defaults:
- `auto_download: true` - Automatically download missing data
- `auto_train: true` - Automatically retrain model
- `auto_recompute: false` - Don't recompute probabilities (will be computed on probability page)
- `max_seasons: 7` - Download last 7 seasons

### **Polling Interval**

Pipeline status is polled every **2 seconds** with a **5-minute timeout**.

---

## 🚨 Error Handling

### **Pipeline Failures**

If pipeline fails:
1. Error toast notification shown
2. User asked: "Do you want to continue anyway?"
3. If yes: Continue with jackpot creation (may use default strengths)
4. If no: Cancel operation

### **Network Errors**

- Validation errors: Teams marked as invalid, user can correct
- Pipeline errors: Shown in progress dialog, user can retry
- Status polling errors: Timeout after 5 minutes

---

## 📝 Example Scenarios

### **Scenario 1: All Teams Validated and Trained**

```
User enters: Arsenal, Chelsea, Liverpool
Validation: ✓ All validated, ✨ All trained
Click "Calculate Probabilities"
→ Pipeline skipped (no missing data)
→ Jackpot created immediately
→ Navigate to probability output
```

### **Scenario 2: Some Teams Need Training**

```
User enters: Arsenal, New Team, Liverpool
Validation: ✓ 2 validated, ✨ 1 trained, ⚠️ 1 need training
Click "Calculate Probabilities"
→ Pipeline runs:
  ✓ Create "New Team"
  ✓ Download data for New Team's league
  ✓ Retrain model
→ Jackpot created
→ Navigate to probability output
```

### **Scenario 3: Teams Not Found**

```
User enters: Arsenal, Unknown Team, Liverpool
Validation: ✓ 2 validated, ⚠️ 1 not found
Click "Calculate Probabilities"
→ Pipeline runs:
  ✓ Create "Unknown Team" (if league known)
  ✓ Download data
  ✓ Retrain model
→ Jackpot created
→ Navigate to probability output
```

---

## 🎯 Benefits

✅ **Automatic** - No manual intervention needed

✅ **Transparent** - Progress shown in real-time

✅ **Accurate** - Probabilities use trained strengths

✅ **User-Friendly** - Clear visual indicators

✅ **Error-Resilient** - Handles failures gracefully

---

## 📚 Related Documentation

- [Automated Pipeline Guide](./AUTOMATED_PIPELINE_GUIDE.md) - Backend pipeline details
- [Validation vs Model Training](./VALIDATION_VS_MODEL_TRAINING.md) - Understanding validation
- [Model Training Impact](./MODEL_TRAINING_IMPACT_ON_PROBABILITIES.md) - Why training matters

---

## 🔍 Technical Details

### **State Management**

```typescript
// Pipeline state
const [pipelineDialogOpen, setPipelineDialogOpen] = useState(false);
const [pipelineStatus, setPipelineStatus] = useState<'idle' | 'checking' | 'running' | 'completed' | 'failed'>('idle');
const [pipelineProgress, setPipelineProgress] = useState(0);
const [pipelinePhase, setPipelinePhase] = useState('');
const [pipelineSteps, setPipelineSteps] = useState<Record<string, any>>({});
const [pipelineTaskId, setPipelineTaskId] = useState<string | null>(null);
```

### **Validation Summary**

```typescript
const validationSummary = useMemo(() => {
  // Counts: validTeams, invalidTeams, validatingTeams, 
  //         unvalidatedTeams, trainedTeams, untrainedTeams
}, [fixtures]);
```

---

## ✅ Summary

The frontend now provides a **seamless experience** where:
1. Teams are validated **automatically** as you type
2. Training status is checked **in real-time**
3. Missing data is downloaded **automatically** when needed
4. Model is retrained **automatically** when needed
5. Progress is shown **transparently** in a dialog
6. Probabilities are calculated with **trained strengths** for maximum accuracy

**No manual steps required!** 🎉

