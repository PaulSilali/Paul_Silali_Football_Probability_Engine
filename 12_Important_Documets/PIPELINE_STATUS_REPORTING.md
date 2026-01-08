# Pipeline Status Reporting Guide

## 🎯 Overview

The system now tracks and displays pipeline execution status, showing:
- Whether missing data was downloaded
- Whether models were trained
- Whether probabilities were calculated using new data
- Warnings if data is still missing after pipeline execution

---

## ✅ What's Tracked

### **Pipeline Metadata Stored in Database**

When a pipeline runs, the following information is saved to `jackpots.pipeline_metadata`:

```json
{
  "execution_timestamp": "2024-01-01T10:00:00Z",
  "pipeline_run": true,
  "teams_created": ["New Team"],
  "data_downloaded": true,
  "download_stats": {
    "leagues_downloaded": [{"league_code": "E0", "seasons": ["2324", "2223"]}],
    "total_matches": 1520,
    "errors": []
  },
  "model_trained": true,
  "training_stats": {
    "model_id": 42,
    "model_version": "poisson-20240101-100500"
  },
  "probabilities_calculated_with_new_data": true,
  "status": "completed",
  "errors": []
}
```

---

## 📊 Where Status is Shown

### **1. During Pipeline Execution (Jackpot Input Page)**

**Progress Dialog** shows:
- Current step (e.g., "Downloading data...", "Retraining model...")
- Progress percentage (0-100%)
- Pipeline steps with status indicators:
  - ✓ Completed (green checkmark)
  - ⚠️ Failed (red warning)
  - ⏳ Running (spinner)
  - ⊘ Skipped (gray X)

**Summary After Completion:**
- Number of teams created
- Data downloaded (matches count, leagues)
- Model trained (version)
- ✓ Confirmation that probabilities use newly trained data

### **2. After Loading Jackpot (Probability Output Page)**

**Pipeline Status Banner** shows:
- Teams created count
- Data downloaded (matches, leagues)
- Model trained (version)
- ✓ Confirmation that probabilities use newly trained data
- Execution timestamp
- Any errors/warnings

**Status Check:**
- Automatically checks if teams are still missing/untrained
- Shows warning toast if data is still missing after pipeline

---

## 🔍 How It Works

### **Step 1: Pipeline Execution**

When you click "Calculate Probabilities":

1. **Create Jackpot** (so we have `jackpot_id`)
2. **Check Team Status** → Identify missing/untrained teams
3. **Run Pipeline** (if needed):
   - Create missing teams
   - Download missing data
   - Retrain model
   - **Save metadata to jackpot** (`pipeline_metadata` field)
4. **Navigate to Probability Output**

### **Step 2: Status Display**

**In Progress Dialog:**
- Shows real-time progress
- Displays summary after completion

**In Probability Output:**
- Loads `pipeline_metadata` from jackpot
- Displays status banner
- Checks if data is still missing
- Shows warnings if download/training failed

---

## 🎨 Visual Indicators

### **Success Indicators:**
- ✓ Green checkmark = Completed successfully
- ✨ Blue sparkles = Using newly trained data
- 📊 Stats shown = Data downloaded, model trained

### **Warning Indicators:**
- ⚠️ Yellow warning = Warnings/errors occurred
- ❌ Red warning = Failed or data still missing

### **Status Colors:**
- **Green** = Completed successfully
- **Blue** = In progress or informational
- **Yellow** = Warnings
- **Red** = Failed or errors

---

## 📝 Example Scenarios

### **Scenario 1: Pipeline Successful**

**Progress Dialog Shows:**
```
✓ Status check
✓ Create teams (2 teams created)
✓ Download data (1,520 matches downloaded - E0)
✓ Train model (Version: poisson-20240101-100500)
⊘ Recompute probabilities (skipped)
```

**Probability Output Shows:**
```
Pipeline Execution Summary
✓ 2 teams created
✓ Data downloaded: 1,520 matches (E0)
✓ Model trained: poisson-20240101-100500
✨ Probabilities calculated using newly trained model data
Executed: 1/1/2024, 10:00:00 AM
```

### **Scenario 2: Pipeline Failed**

**Progress Dialog Shows:**
```
✓ Status check
✓ Create teams (2 teams created)
⚠ Download data (Error: Connection timeout)
⚠ Train model (skipped - no data)
```

**Probability Output Shows:**
```
Pipeline Execution Summary
✓ 2 teams created
⚠ Warnings:
  - Error downloading E0 season 2324: Connection timeout
⚠ Download may not have been successful
```

### **Scenario 3: Data Still Missing After Pipeline**

**Probability Output Shows:**
```
⚠ Pipeline Status Warning
2 teams still missing. Download may not have been successful.
```

**Banner Shows:**
```
Pipeline Execution Summary
⚠ Warnings:
  - Error downloading E0 season 2324: Connection timeout
⚠ Data may still be missing
```

---

## 🔄 Reload Behavior

### **When You Reload a Jackpot:**

1. **Load Pipeline Metadata** from `jackpots.pipeline_metadata`
2. **Display Status Banner** with execution summary
3. **Check Current Status**:
   - Re-check team validation/training status
   - Compare with pipeline metadata
   - Show warning if data is still missing

### **If Data is Still Missing:**

- **Warning Toast** appears:
  - "X teams still missing. Download may not have been successful."
  - "X teams still untrained. Model training may not have been successful."

- **Banner Shows**:
  - Pipeline execution summary
  - Errors/warnings from execution
  - Current status check results

---

## ⚙️ Technical Details

### **Database Schema**

```sql
ALTER TABLE jackpots 
ADD COLUMN pipeline_metadata JSONB DEFAULT NULL;
```

### **Metadata Structure**

```typescript
interface PipelineMetadata {
  execution_timestamp: string;
  pipeline_run: boolean;
  teams_created: string[];
  data_downloaded: boolean;
  download_stats: {
    leagues_downloaded: Array<{league_code: string; seasons: string[]}>;
    total_matches: number;
    errors: string[];
  };
  model_trained: boolean;
  training_stats: {
    model_id: number;
    model_version: string;
  } | null;
  probabilities_calculated_with_new_data: boolean;
  status: 'completed' | 'failed';
  errors: string[];
}
```

### **API Endpoints**

**Get Jackpot (includes pipeline_metadata):**
```
GET /api/jackpots/{jackpot_id}
Response: {
  ...jackpot_data,
  pipelineMetadata: {...}
}
```

**Check Teams Status:**
```
POST /api/pipeline/check-status
Request: { team_names: [...], league_id: ... }
Response: {
  validated_teams: [...],
  missing_teams: [...],
  trained_teams: [...],
  untrained_teams: [...]
}
```

---

## 🎯 User Benefits

✅ **Transparency** - See exactly what happened during pipeline execution

✅ **Accountability** - Know if data was downloaded and model was trained

✅ **Reliability** - Detect if pipeline failed or data is still missing

✅ **Confidence** - Know if probabilities use newly trained data

✅ **Debugging** - See errors/warnings to fix issues

---

## 📚 Related Documentation

- [Automated Pipeline Guide](./AUTOMATED_PIPELINE_GUIDE.md) - How pipeline works
- [Frontend Pipeline Integration](./FRONTEND_PIPELINE_INTEGRATION.md) - Frontend implementation
- [Validation vs Model Training](./VALIDATION_VS_MODEL_TRAINING.md) - Understanding validation

---

## ✅ Summary

The system now provides **complete visibility** into pipeline execution:

1. **During Execution** - Progress dialog with real-time status
2. **After Completion** - Summary showing what was done
3. **On Reload** - Status banner with execution summary
4. **Status Check** - Automatic verification if data is still missing
5. **Warnings** - Alerts if download/training failed

**You always know:**
- ✓ Was data downloaded?
- ✓ Was model trained?
- ✓ Are probabilities using new data?
- ⚠️ Is data still missing?

